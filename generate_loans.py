"""Generate a small FICTIONAL mortgage-loan table and save it to loans.db."""

import random
import sqlite3
from datetime import date, timedelta

import pandas as pd

random.seed(42)  # same data every run
REGIONS = ["Boston Metro", "Central MA", "Western MA", "North Shore", "South Shore", "Cape & Islands"]
TODAY = date(2026, 11, 5)

loans = []
for i in range(1, 101):
    original_amount = random.randint(150, 650) * 1000
    origination_date = TODAY - timedelta(days=random.randint(365, 365 * 15))
    years_paid = (TODAY - origination_date).days / 365
    current_balance = round(original_amount * max(0.05, 1 - years_paid * 0.04), 2)

    roll = random.random()
    if roll < 0.75:
        status, days_past_due = "Current", 0
    elif roll < 0.92:
        status, days_past_due = "Overdue", random.choice([30, 60, 90, 120])
    else:
        status, days_past_due, current_balance = "Paid Off", 0, 0.0

    loans.append({
        "loan_id": f"LN{i:04d}",
        "borrower_region": random.choice(REGIONS),
        "original_amount": original_amount,
        "current_balance": current_balance,
        "interest_rate": round(random.uniform(2.75, 7.5), 3),
        "origination_date": origination_date.isoformat(),
        "days_past_due": days_past_due,
        "status": status,
    })

with sqlite3.connect("loans.db") as conn:
    pd.DataFrame(loans).to_sql("loans", conn, if_exists="replace", index=False)

print("Created loans.db with", len(loans), "fictional loans")
