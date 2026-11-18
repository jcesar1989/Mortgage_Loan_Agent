"""
Step 3: The agent. A local Llama model (via Ollama) reads a question,
picks one of the two tools, and explains the result in plain English.

Setup (one time):
  1. Install Ollama from https://ollama.com
  2. In a terminal:  ollama pull llama3.1
  3. pip install ollama pandas

Run:
  python agent.py "How many loans are overdue?"
  python agent.py "Which region has the highest average balance?"
"""

import json
import sys

from ollama import chat

from tools import run_sql, summarize_by

MODEL = "llama3.1"

SYSTEM_PROMPT = """You answer questions about a fictional mortgage-loan table using tools.

The SQLite table is named loans and has these columns:
  loan_id (text), borrower_region (text), original_amount (integer),
  current_balance (real), interest_rate (real), origination_date (text, YYYY-MM-DD),
  days_past_due (integer), status (text: 'Current', 'Overdue', or 'Paid Off')

Regions: 'Boston Metro', 'Central MA', 'Western MA', 'North Shore', 'South Shore', 'Cape & Islands'

Use run_sql for counts, filters, and lookups of specific loans.
Use summarize_by for comparing groups (for example, averages by region).

The table contains NOTHING else: no credit scores, borrower names, incomes,
property values, or payment history. If the question asks for information that
is not in the columns above, do NOT call a tool and do NOT substitute a
different column in its place. Reply only that the loans data does not include
that information. For example, "who is the borrower" cannot be answered:
borrowers are anonymous in this data, and a loan's region does not say who
the borrower is.

If the question CAN be answered from the columns above, always call a tool and
never guess numbers. After you get the tool result, explain the answer in one
or two plain-English sentences, using only numbers that appear in the result."""

# Descriptions of the tools that the model reads to decide which one to use
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_sql",
            "description": "Run a read-only SQLite SELECT query against the loans table.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "A single SQLite SELECT statement."}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_by",
            "description": "Group loans by a column and compute a statistic on a numeric column, sorted highest first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "group_by": {"type": "string", "enum": ["borrower_region", "status"]},
                    "metric": {"type": "string", "enum": ["current_balance", "original_amount",
                                                          "interest_rate", "days_past_due"]},
                    "stat": {"type": "string", "enum": ["avg", "sum", "count", "min", "max"]},
                },
                "required": ["group_by", "metric", "stat"],
            },
        },
    },
]

AVAILABLE_TOOLS = {"run_sql": run_sql, "summarize_by": summarize_by}


def ask(question: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    # 1. Ask the model; it should respond with a tool call
    response = chat(model=MODEL, messages=messages, tools=TOOLS)
    messages.append(response.message)

    if not response.message.tool_calls:
        return response.message.content  # model answered without a tool

    # 2. Run each tool the model asked for, and hand the results back
    for call in response.message.tool_calls:
        name = call.function.name
        args = call.function.arguments
        print(f"\n[Tool call] {name}({json.dumps(args)})")

        tool = AVAILABLE_TOOLS.get(name)
        result = tool(**args) if tool else {"error": f"Unknown tool: {name}"}
        print(f"[Tool result] {json.dumps(result)}")

        messages.append({"role": "tool", "tool_name": name, "content": json.dumps(result)})

    # 3. Ask the model to explain the result in plain English.
    # The reminder is a guardrail against hallucination: without it the model
    # will sometimes dress up a wrong or failed tool result as a real answer.
    messages.append({
        "role": "user",
        "content": "Answer using only the tool results above. If a tool returned "
                   "an error, or the question asked for information the results "
                   "do not contain, say explicitly that the loans data does not "
                   "include it. The data never identifies people: if the question "
                   "asked WHO someone is, the only correct answer is that the "
                   "loans data does not identify borrowers. Do not answer a "
                   "different question instead.",
    })
    final = chat(model=MODEL, messages=messages)
    return final.message.content


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "How many loans are overdue?"
    print(f"[Question] {question}")
    print(f"\n[Answer] {ask(question)}")
