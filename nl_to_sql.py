"""
nl_to_sql.py
------------
The GenAI layer: turns a plain-English question into a validated, read-only
SQL query against analytics.db, runs it, and (optionally) writes a one-line
summary of the result.

Two modes:
  1. LLM mode   - if OPENAI_API_KEY (or ANTHROPIC_API_KEY) is set, uses that
                  provider to generate SQL. OpenAI is checked first.
  2. Fallback   - if no key is set, a small pattern-matcher handles a fixed
                  set of common questions, so the dashboard still works on
                  day one before you've wired up an API key.

This split is deliberate: it lets you ship something demoable immediately,
then layer in the "real" GenAI piece as you learn it (see LEARNING_PATH.md).
"""

import os
import re
import sqlite3

import pandas as pd

DB_PATH = "analytics.db"

SCHEMA_DESCRIPTION = """
You have access to a SQLite database with these tables:

customers(customer_id INTEGER, name TEXT, region TEXT, segment TEXT, signup_date TEXT)
    -- region in ('North','South','East','West','Central')
    -- segment in ('New','Regular','VIP')

products(product_id INTEGER, product_name TEXT, category TEXT, price REAL)
    -- category in ('Apparel','Electronics','Home','Beauty','Footwear','Accessories')

orders(order_id INTEGER, customer_id INTEGER, order_date TEXT, status TEXT)
    -- status in ('Completed','Cancelled'); order_date is 'YYYY-MM-DD'

order_items(order_item_id INTEGER, order_id INTEGER, product_id INTEGER,
            quantity INTEGER, unit_price REAL, returned INTEGER)
    -- returned is 0 or 1

reviews(review_id INTEGER, product_id INTEGER, customer_id INTEGER,
        rating INTEGER, review_text TEXT, review_date TEXT)
    -- rating is 1-5. One row per (customer, product) that was actually purchased.
"""

SYSTEM_PROMPT = f"""You are a SQL generator for a SQLite analytics database.

{SCHEMA_DESCRIPTION}

Rules:
- Output ONLY a single valid SQLite SELECT statement. No explanation, no markdown fences.
- Never write INSERT, UPDATE, DELETE, DROP, ALTER, or any statement other than SELECT.
- Prefer clear column aliases (e.g. AS total_revenue) so results are readable.
- Use JOINs across order_items -> orders -> products / customers as needed.
- revenue = quantity * unit_price, only for status = 'Completed' unless asked otherwise.
- If the question is ambiguous, make a reasonable assumption rather than asking for clarification.
"""

# A few examples help the model match this exact schema's naming conventions.
FEW_SHOT_EXAMPLES = [
    (
        "What's our total revenue?",
        "SELECT ROUND(SUM(oi.quantity * oi.unit_price), 2) AS total_revenue "
        "FROM order_items oi JOIN orders o ON oi.order_id = o.order_id "
        "WHERE o.status = 'Completed';",
    ),
    (
        "Which category has the highest return rate?",
        "SELECT p.category, "
        "ROUND(100.0 * SUM(oi.returned) / COUNT(*), 2) AS return_rate_pct "
        "FROM order_items oi JOIN products p ON oi.product_id = p.product_id "
        "GROUP BY p.category ORDER BY return_rate_pct DESC;",
    ),
    (
        "Which category has the best average rating?",
        "SELECT p.category, ROUND(AVG(r.rating), 2) AS avg_rating, COUNT(*) AS n_reviews "
        "FROM reviews r JOIN products p ON r.product_id = p.product_id "
        "GROUP BY p.category ORDER BY avg_rating DESC;",
    ),
]

FORBIDDEN_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|ATTACH|PRAGMA)\b", re.IGNORECASE
)


class GuardrailError(ValueError):
    """Raised when a generated query fails the SELECT-only guardrail."""


def _validate_sql(sql: str) -> str:
    sql = sql.strip().strip(";")
    if not sql.lower().startswith("select"):
        raise GuardrailError(f"Rejected non-SELECT query: {sql[:80]}...")
    if FORBIDDEN_PATTERN.search(sql):
        raise GuardrailError(f"Rejected query containing a forbidden keyword: {sql[:80]}...")
    return sql


def _active_provider() -> str | None:
    """Returns 'openai', 'anthropic', or None. OpenAI takes priority if both are set."""
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    return None


def _llm_available() -> bool:
    return _active_provider() is not None


def _generate_sql_llm(question: str) -> str:
    """Translate the question into SQL using whichever provider's key is set."""
    provider = _active_provider()

    if provider == "openai":
        from openai import OpenAI  # imported lazily so fallback mode has no hard dependency

        client = OpenAI()
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for q, sql in FEW_SHOT_EXAMPLES:
            messages.append({"role": "user", "content": q})
            messages.append({"role": "assistant", "content": sql})
        messages.append({"role": "user", "content": question})

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=300,
            messages=messages,
        )
        raw = response.choices[0].message.content.strip()

    else:  # anthropic
        from anthropic import Anthropic

        client = Anthropic()
        messages = []
        for q, sql in FEW_SHOT_EXAMPLES:
            messages.append({"role": "user", "content": q})
            messages.append({"role": "assistant", "content": sql})
        messages.append({"role": "user", "content": question})

        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        raw = response.content[0].text.strip()

    # strip accidental markdown fences if the model adds them
    raw = re.sub(r"^```sql\s*|\s*```$", "", raw, flags=re.IGNORECASE).strip()
    return raw


def _summarize_llm(question: str, df: pd.DataFrame) -> str:
    provider = _active_provider()
    preview = df.head(10).to_csv(index=False)
    prompt = (
        f"Question: {question}\n\nQuery result (CSV, up to 10 rows):\n{preview}\n\n"
        "Write ONE short sentence answering the question using this data. "
        "Be specific with numbers. No preamble."
    )

    if provider == "openai":
        from openai import OpenAI

        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=120,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()

    else:  # anthropic
        from anthropic import Anthropic

        client = Anthropic()
        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=120,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()


# ---------------------------------------------------------------------------
# Fallback mode: no API key needed. Covers common questions so the dashboard
# is demoable immediately. Add your own patterns here as you extend it.
# ---------------------------------------------------------------------------

FALLBACK_RULES = [
    (
        re.compile(r"total revenue|overall revenue", re.I),
        "SELECT ROUND(SUM(oi.quantity * oi.unit_price), 2) AS total_revenue "
        "FROM order_items oi JOIN orders o ON oi.order_id = o.order_id "
        "WHERE o.status = 'Completed';",
    ),
    (
        re.compile(r"return rate.*categor|categor.*return rate|highest return", re.I),
        "SELECT p.category, "
        "ROUND(100.0 * SUM(oi.returned) / COUNT(*), 2) AS return_rate_pct "
        "FROM order_items oi JOIN products p ON oi.product_id = p.product_id "
        "GROUP BY p.category ORDER BY return_rate_pct DESC;",
    ),
    (
        re.compile(r"top.*product|best.?sell", re.I),
        "SELECT p.product_name, SUM(oi.quantity) AS units_sold "
        "FROM order_items oi JOIN products p ON oi.product_id = p.product_id "
        "JOIN orders o ON oi.order_id = o.order_id WHERE o.status = 'Completed' "
        "GROUP BY p.product_name ORDER BY units_sold DESC LIMIT 5;",
    ),
    (
        re.compile(r"revenue.*region|region.*revenue", re.I),
        "SELECT c.region, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue "
        "FROM order_items oi JOIN orders o ON oi.order_id = o.order_id "
        "JOIN customers c ON o.customer_id = c.customer_id "
        "WHERE o.status = 'Completed' GROUP BY c.region ORDER BY revenue DESC;",
    ),
    (
        re.compile(r"vip|segment", re.I),
        "SELECT c.segment, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue, "
        "COUNT(DISTINCT o.order_id) AS orders "
        "FROM order_items oi JOIN orders o ON oi.order_id = o.order_id "
        "JOIN customers c ON o.customer_id = c.customer_id "
        "WHERE o.status = 'Completed' GROUP BY c.segment ORDER BY revenue DESC;",
    ),
    (
        re.compile(r"rating|review", re.I),
        "SELECT p.category, ROUND(AVG(r.rating), 2) AS avg_rating, COUNT(*) AS n_reviews "
        "FROM reviews r JOIN products p ON r.product_id = p.product_id "
        "GROUP BY p.category ORDER BY avg_rating DESC;",
    ),
]


def _generate_sql_fallback(question: str) -> str:
    for pattern, sql in FALLBACK_RULES:
        if pattern.search(question):
            return sql
    # default: monthly revenue trend, always a safe/interesting answer
    return (
        "SELECT strftime('%Y-%m', o.order_date) AS month, "
        "ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue "
        "FROM order_items oi JOIN orders o ON oi.order_id = o.order_id "
        "WHERE o.status = 'Completed' GROUP BY month ORDER BY month;"
    )


# ---------------------------------------------------------------------------
# Public API used by app.py
# ---------------------------------------------------------------------------

def run_sql(sql: str) -> pd.DataFrame:
    sql = _validate_sql(sql)
    conn = sqlite3.connect(DB_PATH)
    try:
        return pd.read_sql_query(sql, conn)
    finally:
        conn.close()


def answer_question(question: str) -> dict:
    """
    Returns a dict: {"sql": str, "result": DataFrame, "summary": str, "mode": str}
    """
    mode = "llm" if _llm_available() else "fallback"

    if mode == "llm":
        try:
            sql = _generate_sql_llm(question)
            sql = _validate_sql(sql)
            df = run_sql(sql)
            summary = _summarize_llm(question, df)
            return {"sql": sql, "result": df, "summary": summary, "mode": mode}
        except Exception as exc:  # fall back gracefully if the API call fails
            sql = _generate_sql_fallback(question)
            df = run_sql(sql)
            return {
                "sql": sql,
                "result": df,
                "summary": f"(LLM call failed: {exc}. Showing closest fallback query.)",
                "mode": "fallback-after-error",
            }

    sql = _generate_sql_fallback(question)
    df = run_sql(sql)
    return {
        "sql": sql,
        "result": df,
        "summary": "(Fallback mode: pattern-matched query. Add OPENAI_API_KEY (or ANTHROPIC_API_KEY) for free-form NL questions.)",
        "mode": mode,
    }
