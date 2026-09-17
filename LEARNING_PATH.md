# Walkthrough — understanding what's already built

The project is finished and verified. This is a guided reading path, not a build plan —
each session is ~1 hour of reading + poking at the running app, not writing new code.

## Session 1 — Run it, understand the schema
- Run `streamlit run app.py` (see README for setup) in fallback mode first — no API key
  needed. Click through the dashboard and every example question in the query box.
- Open `analytics.db` in a SQLite viewer (DB Browser for SQLite, or `sqlite3 analytics.db`
  in a terminal) and look at the 5 tables directly: `customers`, `products`, `orders`,
  `order_items`, `reviews`.
- Read `db_setup.py` top to bottom. Notice `RETURN_RATE_BY_CATEGORY` — the whole dataset
  is generated so that Apparel/Footwear return more *and* rate lower than
  Electronics/Beauty, on purpose. That's why the charts tell a consistent story instead
  of looking like random noise. Being able to explain "I designed the data generation so
  the categories with higher returns also have lower ratings, to mirror a real pattern"
  is a good, specific thing to say in an interview.

## Session 2 — Understand the SQL
- Pick 5 questions from the example list in the dashboard and, for each one, find the
  matching SQL in `nl_to_sql.py` (`FALLBACK_RULES` and `FEW_SHOT_EXAMPLES`). Trace through
  each JOIN by hand: which tables, on what key, why.
- Try writing 3 of your own queries directly against `analytics.db` (not through the app)
  — e.g. "average order value by region" or "top 3 reviewed products." This is the actual
  SQL skill the job postings ask for.

## Session 3 — Understand the GenAI layer
- Read `SYSTEM_PROMPT` and `FEW_SHOT_EXAMPLES` in `nl_to_sql.py` — this is prompt
  engineering in practice: the model is taught your exact schema and naming conventions
  via examples, not just a description.
- Read `_validate_sql()` and the guardrail test result: feeding it `DELETE FROM orders;`
  gets rejected before it ever reaches the database. Understand *why* this matters — an
  LLM turning free text into SQL is a real injection-style risk if ungated, and this is
  a small, concrete defense against it. This is the single most interview-worthy design
  decision in the project.
- If you have an OpenAI (or Anthropic) API key, add it to `.env` and restart the app.
  Ask a handful of questions the fallback rules don't cover and see what SQL comes back
  — compare it mentally to what you'd have written by hand.

## Session 4 — Own the story
- Read through `app.py` and match each chart back to the KPI/SQL query behind it in
  `load_kpis()`.
- Write, in your own words (not from this doc), a 3-sentence description of the project
  you could say out loud in an interview: what it does, what the GenAI layer adds over a
  plain dashboard, and how the guardrail works. That's the actual deliverable of this
  session — not more code.
- Fill in real numbers into the resume bullet drafts in `README.md`.
