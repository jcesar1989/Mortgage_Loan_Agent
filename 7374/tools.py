"""
Step 2: The two analysis tools the agent will choose between.

  Tool 1: run_sql(query)
      Runs a read-only SELECT query against loans.db.
      Good for counts, filters, and specific lookups.
      Example question: "How many loans are overdue?"

  Tool 2: summarize_by(group_by, metric, stat, include_paid_off)
      Uses pandas to group the loans by one column and calculate
      a statistic (avg, sum, count, min, max) on another column.
      Example question: "Which region has the highest average balance?"

Both tools return plain Python data (lists/dicts), which the AI model
will later read and explain in ordinary English.
"""

import sqlite3

import pandas as pd

DB_PATH = "loans.db"

# Columns the summary tool is allowed to use (keeps the agent from asking for nonsense)
GROUP_COLUMNS = ["borrower_region", "status"]
METRIC_COLUMNS = ["current_balance", "original_amount", "interest_rate", "days_past_due"]
STATS = ["avg", "sum", "count", "min", "max"]


# ---------------------------------------------------------------------------
# Tool 1: SQL
# ---------------------------------------------------------------------------
def run_sql(query: str) -> dict:
    """Run a read-only SELECT query and return the column names and rows."""
    cleaned = query.strip().rstrip(";")

    # Guardrail 1: only SELECT statements, and only one statement
    if not cleaned.lower().startswith("select"):
        return {"error": "Only SELECT queries are allowed."}
    if ";" in cleaned:
        return {"error": "Only one query at a time is allowed."}

    try:
        # Guardrail 2: open the database in read-only mode
        with sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True) as conn:
            cursor = conn.execute(cleaned)
            columns = [c[0] for c in cursor.description]
            rows = cursor.fetchmany(50)  # Guardrail 3: cap the size of the result
        return {"columns": columns, "rows": [list(r) for r in rows]}
    except sqlite3.Error as e:
        return {"error": f"SQL error: {e}"}


# ---------------------------------------------------------------------------
# Tool 2: Python / pandas summary
# ---------------------------------------------------------------------------
def summarize_by(group_by: str, metric: str, stat: str = "avg",
                 include_paid_off: bool = False) -> dict:
    """Group loans by one column and compute a statistic on another."""
    if group_by not in GROUP_COLUMNS:
        return {"error": f"group_by must be one of {GROUP_COLUMNS}"}
    if metric not in METRIC_COLUMNS:
        return {"error": f"metric must be one of {METRIC_COLUMNS}"}
    if stat not in STATS:
        return {"error": f"stat must be one of {STATS}"}

    with sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True) as conn:
        df = pd.read_sql("SELECT * FROM loans", conn)

    # Paid-off loans have a $0 balance, which would drag averages down,
    # so they are left out unless asked for.
    if not include_paid_off:
        df = df[df["status"] != "Paid Off"]

    pandas_stat = "mean" if stat == "avg" else stat
    result = (df.groupby(group_by)[metric]
                .agg(pandas_stat)
                .round(2)
                .sort_values(ascending=False))

    return {
        "group_by": group_by,
        "metric": metric,
        "stat": stat,
        "include_paid_off": include_paid_off,
        "results": [{group_by: k, f"{stat}_{metric}": v} for k, v in result.items()],
    }
