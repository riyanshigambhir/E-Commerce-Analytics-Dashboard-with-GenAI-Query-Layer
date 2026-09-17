# E-Commerce Analytics Dashboard — SQL + GenAI Query Layer

Built to close a specific gap: your resume shows strong ML (return-risk modeling, GNN bot
detection) but nothing demonstrating **SQL, data visualization, or GenAI applied to a
business analytics problem** — three things Accenture's AI & Data Strategy & Consulting
postings ask for repeatedly, and that your current resume doesn't show anywhere.

This project is deliberately scoped for one focused week, not a semester. It pairs with
your existing Return Risk Modeling project (same e-commerce domain), so in an interview
you can say: "I built the ML model for return risk on this data, then separately built a
SQL + dashboard layer with a natural-language query interface on top of it."

## What it is

This is fully built and verified end to end (schema, data, dashboard, NL query box,
guardrail) — nothing left to assemble. Tomorrow is about reading and understanding it,
not building it; use `LEARNING_PATH.md` as a guided walkthrough.

- A synthetic SQLite e-commerce database: customers, products, orders, order_items,
  and reviews (~3,500 orders, ~1,800 reviews, realistic category-level return-rate and
  rating skew — categories that return more also rate lower, on purpose).
- A Streamlit dashboard with 4 KPI cards and 6 charts (revenue by category, return rate
  by category, monthly trend, revenue by customer segment, average rating by category).
- A natural-language query box: type a question in plain English ("Which category has
  the highest return rate?"), it's translated to SQL by an LLM (OpenAI or Anthropic —
  whichever key you set), run against the database, and summarized in one sentence —
  with guardrails so it can only ever run `SELECT` statements (tested: it correctly
  refuses a `DELETE` even if asked).
- A fallback mode with no API key required, so the whole thing runs immediately, with or
  without a key.

## Architecture

```
db_setup.py   -> generates analytics.db (run once)
nl_to_sql.py  -> question -> SQL -> guardrail check -> execute -> (optional) summarize
app.py        -> Streamlit UI: KPIs, charts, NL query box
```

## Setup

```bash
cd sql-genai-dashboard
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

python db_setup.py                # creates analytics.db
streamlit run app.py              # opens the dashboard in your browser
```

The dashboard works immediately in **fallback mode** (no API key needed — a handful of
common questions are pattern-matched to pre-written SQL). To unlock free-form natural
language questions:

```bash
cp .env.example .env
# edit .env, add your OPENAI_API_KEY (or ANTHROPIC_API_KEY)
```

Get an OpenAI key at https://platform.openai.com/api-keys, or an Anthropic key at
https://console.anthropic.com. Only one is needed — if both are set, OpenAI is used.

## Ideas if you want to go further later (all optional — the project is complete without these)

1. **Wire up the LLM mode** with your API key and try questions the fallback rules
   don't cover — watch what SQL Claude generates, and where it gets it wrong.
2. **Add a new metric** — e.g. "customer lifetime value" or "repeat purchase rate" —
   and extend both the dashboard and the NL schema description in `nl_to_sql.py`.
3. **Swap SQLite for Postgres** — you already list PostgreSQL as a skill; running
   this against a real Postgres instance (even locally via Docker) is a natural
   next step and closes the "cloud/production database" gap too.

## Resume bullets (draft — fill in your own numbers once you've run and extended it)

Once you've built and tweaked this, something like:

> Built a SQL-backed analytics dashboard with a GenAI natural-language query layer
> over a synthetic 3,500-order e-commerce dataset (SQLite, Streamlit, Plotly);
> translated plain-English questions into validated SQL via the OpenAI API, with
> guardrails restricting execution to read-only queries.

> Designed a normalized 5-table schema and wrote the SQL powering [N] KPIs and
> [N] visualizations, including category-level return-rate analysis consistent
> with findings from a separate return-risk ML model on the same domain.

Keep it honest — only claim what you actually built/changed, and swap in real
numbers (query count, categories analyzed, etc.) once you've extended it.
