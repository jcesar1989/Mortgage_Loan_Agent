# Mortgage Loan Agent

A small AI agent that answers plain-English questions about a fictional mortgage-loan portfolio. A local Llama model (running through [Ollama](https://ollama.com)) reads your question, decides which of two analysis tools to call, runs it against a SQLite database, and explains the result in ordinary English.

Everything runs locally — no API keys, no cloud services, and all loan data is fictional.

## How it works

```
Your question
     │
     ▼
 agent.py ──► Llama 3.1 (via Ollama) picks a tool
     │
     ├──► run_sql(query)        — read-only SELECT against loans.db
     └──► summarize_by(...)     — pandas group-by statistics
     │
     ▼
 Llama explains the tool result in 1–2 plain-English sentences
```

## Project files

| File | Purpose |
|---|---|
| `generate_loans.py` | Step 1 — creates `loans.db` with 100 fictional loans (seeded, so the data is the same every run) |
| `tools.py` | Step 2 — the two analysis tools the agent chooses between |
| `agent.py` | Step 3 — the agent loop: question → tool call → plain-English answer |
| `tests.py` | Step 4 — tests that verify answers against the database and prove problem cases fail safely |
| `loans.db` | The generated SQLite database |
| `requirements.txt` | Python dependencies |

## Setup (one time)

1. Install [Ollama](https://ollama.com) and pull the model:

   ```
   ollama pull llama3.1
   ```

2. Install the Python dependencies:

   ```
   python -m pip install -r requirements.txt
   ```

3. Generate the database:

   ```
   python generate_loans.py
   ```

## Usage

Ask a question as a command-line argument:

```
python agent.py "How many loans are overdue?"
python agent.py "Which region has the highest average balance?"
python agent.py "What is the average interest rate by status?"
```

Run with no arguments to use the default question ("How many loans are overdue?").

The output shows each step so you can see what the agent did:

```
[Question] How many loans are overdue?

[Tool call] run_sql({"query": "SELECT COUNT(*) FROM loans WHERE status = 'Overdue'"})
[Tool result] {"columns": ["COUNT(*)"], "rows": [[17]]}

[Answer] There are 17 overdue loans in the portfolio.
```

## The data

The `loans` table has 100 fictional mortgages with these columns:

| Column | Type | Notes |
|---|---|---|
| `loan_id` | text | e.g. `LN0042` |
| `borrower_region` | text | Boston Metro, Central MA, Western MA, North Shore, South Shore, Cape & Islands |
| `original_amount` | integer | $150k–$650k |
| `current_balance` | real | $0 for paid-off loans |
| `interest_rate` | real | 2.75%–7.5% |
| `origination_date` | text | YYYY-MM-DD, 1–15 years ago |
| `days_past_due` | integer | 0, 30, 60, 90, or 120 |
| `status` | text | `Current`, `Overdue`, or `Paid Off` |

Roughly 75% of loans are Current, 17% Overdue, and 8% Paid Off.

## The two tools

- **`run_sql(query)`** — runs a read-only SQLite SELECT query. Best for counts, filters, and looking up specific loans.
- **`summarize_by(group_by, metric, stat, include_paid_off)`** — groups loans by `borrower_region` or `status` and computes a statistic (`avg`, `sum`, `count`, `min`, `max`) on a numeric column with pandas. Best for comparing groups. Paid-off loans are excluded by default so their $0 balances don't drag averages down.

## Testing

Results are never trusted just because the model says so — `tests.py` checks them against the database directly and demonstrates problem cases:

```
python tests.py           # fast: tool correctness + problem cases (no model needed)
python tests.py --agent   # also runs 2 end-to-end agent tests (needs Ollama)
```

What it covers:

- **Correctness** — tool results are compared against ground truth computed straight from `loans.db` (a direct SQL count, and a hand-computed pandas group-by).
- **Problem cases** — a `DELETE` query, chained statements (`SELECT 1; DROP TABLE loans`), a nonexistent column, an invalid group-by column, and an invalid statistic are all rejected with an error instead of crashing or changing data.
- **End-to-end (with `--agent`)** — the agent's plain-English answer must contain the true overdue count; after asking the agent to *delete* data, the row count is verified unchanged (in practice the model does attempt a `DELETE` — and the read-only guardrail blocks it); and a question about data the table does not have (average credit score) must be declined, not answered with an invented number.

All 12 tests pass; the script exits nonzero if any fail.

## Guardrails

The agent can't damage the data or run away with huge results:

- Only single `SELECT` statements are allowed — no inserts, updates, deletes, or chained statements.
- The database is opened in read-only mode.
- SQL results are capped at 50 rows.
- `summarize_by` only accepts columns and statistics from fixed allowlists.
- The system prompt tells the model to always use a tool and never guess numbers.
- Missing information is refused, not invented: the prompt tells the model the table contains nothing beyond its eight columns (no credit scores, names, incomes...) and to decline rather than substitute a different column, and a reminder at the explain step tells it to report tool errors plainly instead of dressing them up as answers.
