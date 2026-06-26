# FinSight – Financial Advisor App

A comprehensive personal finance calculator and advisor built with Streamlit and Python.

## Features

- **Profile & Income** — Salary, other income, age, occupation
- **Expenses** — Rent, groceries, utilities, transport, EMIs (multiple), variable costs
- **Investments** — SIP, Stocks, ELSS, PPF, NPS with growth projections
- **Insurance** — Coverage check, policy suggestions based on age, ULIP warnings
- **Savings & Assets** — FD maturity calculator, gold, mutual funds, real estate
- **Dashboard** — Financial health score, donut chart, 50/30/20 benchmark, net worth

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Cloud

1. Push this folder to a GitHub repository
2. Go to https://share.streamlit.io
3. Click **New app** → connect your GitHub repo
4. Set **Main file path** to `app.py`
5. Click **Deploy** — it's live in ~60 seconds!

## Project Structure

```
finance_advisor/
├── app.py            ← Main application (all-in-one)
├── requirements.txt  ← Dependencies
└── README.md
```
