# Founder BI Agent — Monday.com Integration

> Ask business questions in plain English and get executive-ready insights from live Monday.com data.

**Live demo:** [monday-bi-agent-v6hs6xspnyzpkr2po2fwlu.streamlit.app](https://monday-bi-agent-v6hs6xspnyzpkr2po2fwlu.streamlit.app/)

## What Is This?

Founder BI Agent is a Business Intelligence agent that connects to live Monday.com boards and answers natural-language business questions with verified, deterministic metrics — not LLM guesses.

It combines:

- **LLM-powered query understanding** (LangChain + Groq)
- **Deterministic BI calculations** (pandas)
- **Live data** via the Monday.com GraphQL API
- **FastAPI** backend
- **Streamlit** chat frontend
- **Data cleaning & normalization**
- **Explicit missing-value / data-quality handling**

## Core Capabilities

- Fetches live data from Monday.com boards
- Works with a Deal Funnel (sales pipeline) board and a Work Order Tracker board
- Cleans and normalizes text, numeric, monetary, and date fields
- Dynamically discovers available sectors from the data (no hard-coded sector list)
- Understands natural-language business questions and classifies intent + sector
- Supports pipeline / deal-value questions
- Supports financial, billing, and collections questions
- Supports work-order execution-status questions
- Supports cross-board (pipeline vs. execution) analysis
- Maintains lightweight per-session conversation context for follow-up questions
- Calculates all BI metrics deterministically with pandas — the LLM never invents numbers
- Surfaces missing/unavailable data explicitly instead of treating it as zero
- Generates concise, executive-style natural-language answers

## Architecture

```
User
  → Streamlit Chat Interface
  → FastAPI Backend (main.py)
  → Monday.com Client (GraphQL)
  → Data Cleaning
  → Query Planner (LLM)
  → BI Engine (pandas, deterministic)
  → LLM Response Layer (explanation only)
  → User
```

### Components

| Component | File | Responsibility |
|---|---|---|
| **Streamlit UI** | `app.py` | Chat interface. Sends questions + a session ID to the backend and renders the answer, including any data-quality warnings. |
| **FastAPI Backend** | `main.py` | Exposes `POST /api/chat`; orchestrates the full pipeline for each request. |
| **Monday.com Client** | `Monday_client.py` | Talks to the Monday.com GraphQL API and returns board data as pandas DataFrames. |
| **Data Cleaning** | `cleaner.py` | Cleans and normalizes text, numeric, monetary, and date fields before analysis. |
| **Query Planner** | `query_planner.py` | Uses an LLM to determine intent, relevant sector/board(s), and whether the question needs clarification. |
| **BI Engine** | `bi_engine.py` | Performs all deterministic pandas calculations. The single source of truth for every number in a response. |
| **LLM Response Layer** | (in `main.py`) | Takes the BI Engine's verified metrics and converts them into an executive-style explanation. It is explicitly instructed never to invent or infer numbers. |

**Design rule:** the LLM understands questions and explains results — it never calculates business metrics itself. Every number in a response comes from the BI Engine.

## How It Works

1. **User asks a question** — e.g. *"What is the pipeline looking like for renewable energy?"*
2. **Live data is fetched** from the configured Monday.com boards.
3. **Data is cleaned** and normalized so calculations are reliable.
4. **Available sectors are discovered** directly from the live data (not hard-coded).
5. **The query is understood** — the Query Planner determines intent, target sector, and relevant board(s).
6. **BI calculations run** deterministically in pandas.
7. **Data-quality issues are surfaced** — missing values and unavailable fields are reported rather than silently treated as zero.
8. **The final answer is generated** — verified metrics are handed to the LLM, which returns a concise, executive-style explanation.

## BI Metrics Supported

- Total deals, recorded deal value
- Won / lost deals
- Pipeline stage distribution
- Deal status distribution
- Total work orders
- Contracted value, billed value, collected value
- Outstanding billed value
- Billing percentage, collection percentage
- Execution status distribution
- Cross-board sector analysis (pipeline vs. work-order execution)

## Example Questions

- What is our pipeline looking like?
- What is the pipeline value for renewable energy?
- How many deals have we won / lost?
- What is our total contracted value?
- How much have we billed? How much have we collected?
- What is the outstanding billed amount?
- What is our billing percentage / collection percentage?
- What is the execution status of our work orders?
- How is the pipeline looking for a particular sector?

## Data Quality

Data quality is treated as a first-class concern. The system never assumes missing data means zero.

- Missing deal, contracted, billed, or collected values are explicitly reported
- Missing business fields are identified
- Percentages are not calculated when their denominator is unavailable or zero
- The LLM is instructed to state when a metric is unavailable rather than fill the gap

This prevents misleading business conclusions from incomplete data.

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, Pydantic |
| Data processing | pandas, numpy, openpyxl |
| LLM orchestration | LangChain, langchain-groq |
| LLM | Groq — `openai/gpt-oss-120b` |
| Data source | Monday.com GraphQL API |
| Frontend | Streamlit |
| Deployment | Streamlit Community Cloud (frontend) + Render (FastAPI backend) |

## Project Structure

```
monday-bi-agent/
│
├── app.py              # Streamlit chat frontend
├── main.py             # FastAPI backend (POST /api/chat)
├── Monday_client.py    # Monday.com GraphQL client
├── cleaner.py           # Data cleaning / normalization
├── bi_engine.py         # Deterministic BI calculations
├── query_planner.py     # LLM-based intent/sector planning
├── requirements.txt
├── .gitignore
└── README.md
```

## Monday.com Board Configuration

This agent reads column data by **title**, not by column type or ID — `Monday_client.py` maps every column's title straight into a DataFrame column name. That means your monday.com boards must use the **exact column titles** below for the app to calculate metrics correctly. Any extra columns you add are simply ignored (safe to include for your own tracking).

### Deals board — columns the agent depends on

| Column title (exact) | Used for |
|---|---|
| `Sector/service` | Sector dimension — pipeline filtering & dynamic sector discovery |
| `Deal Stage` | Stage distribution (e.g. "B. Sales Qualified Leads") |
| `Deal Status` | Won/lost counts and status distribution — must contain the literal values `Won` / `Lost` (case-insensitive) for those metrics to be counted |
| `Masked Deal value` | Total and per-sector recorded deal value |
| `Close Date (A)`, `Tentative Close Date`, `Created Date` | Parsed as dates during cleaning |

### Work Order Tracker board — columns the agent depends on

| Column title (exact) | Used for |
|---|---|
| `Sector` | Sector dimension — matched against the Deals board's `Sector/service` for cross-board analysis |
| `Execution Status` | Execution status distribution |
| `Amount in Rupees (Incl of GST) (Masked)` | Total contracted value |
| `Billed Value in Rupees (Incl of GST.) (Masked)` | Total billed value, billing % |
| `Collected Amount in Rupees (Incl of GST.) (Masked)` | Total collected value, collection %, outstanding value |
| `Amount in Rupees (Excl of GST) (Masked)`, `Billed Value in Rupees (Excl of GST.) (Masked)`, `Amount to be billed in Rs. (Exl./Incl. of GST) (Masked)`, `Amount Receivable (Masked)` | Cleaned and available, not currently used in headline metrics |
| `Data Delivery Date`, `Date of PO/LOI`, `Probable Start Date`, `Probable End Date`, `Last invoice date` | Parsed as dates during cleaning |

### Getting your board IDs and API key

1. Import the two source spreadsheets into monday.com as **two separate boards**, matching the column titles above.
2. **Board ID**: open the board in monday.com and copy the numeric ID from the URL (`https://<you>.monday.com/boards/<BOARD_ID>`).
3. **API key**: in monday.com go to your avatar → **Developers** → **My Access Tokens**, and generate a personal API token (v2 API, read access is sufficient — this agent never writes to your boards).
4. Put the board IDs and token into `.env` as shown below (`DEALS_BOARD_ID`, `WORK_ORDERS_BOARD_ID`, `MONDAY_API_KEY`).

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/codehacker4655/monday-bi-agent.git
cd monday-bi-agent
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
DEALS_BOARD_ID=your_deals_board_id
WORK_ORDERS_BOARD_ID=your_work_orders_board_id
GROQ_API_KEY=your_groq_api_key
MONDAY_API_KEY=your_monday_api_key
```

> **Never commit `.env` or expose API keys publicly.** `main.py` will refuse to start if `DEALS_BOARD_ID`, `WORK_ORDERS_BOARD_ID`, or `GROQ_API_KEY` are missing.

### 4. Run the FastAPI backend

```bash
uvicorn main:app --reload
```

The chat endpoint used by the Streamlit UI is:

```
POST /api/chat
Body: { "query": "<question>", "session_id": "<uuid>" }
```

### 5. Run the Streamlit frontend

In a separate terminal:

```bash
streamlit run app.py
```

By default, the UI points at a deployed Render backend URL (editable in the sidebar). To use your local backend instead, set the **Backend Endpoint** field in the sidebar to:

```
http://localhost:8000/api/chat
```

## Design Principles

1. **Verified metrics first** — business numbers come from the BI Engine, not the LLM.
2. **LLM for understanding and explanation only** — used to parse questions, plan analysis, and explain verified results in natural language.
3. **Dynamic data discovery** — sectors are discovered from live data rather than hard-coded.
4. **Explicit data quality** — missing data is surfaced, never silently zeroed.
5. **Lightweight conversation context** — a session stores the last sector/intent so follow-up questions work naturally.

## Limitations

- Depends on the availability of the Monday.com API.
- Answer quality depends on the completeness of the source board data.
- Conversation context is stored in-memory and is lost on backend restart.
- The BI Engine currently supports a defined set of metrics and intents; more advanced analytical questions need additional calculations and planning logic.

## Future Improvements

- More business metrics and more advanced follow-up handling
- Better query planning
- Additional Monday.com boards
- Persistent conversation memory
- More detailed data-quality reporting
- Authentication and access control
- Automated testing
- Improved visual analytics and dashboards

## Summary

Founder BI Agent connects live Monday.com business data with natural-language interaction, keeping a strict separation between:

**Question Understanding → Data Processing → Verified BI Calculations → Natural-Language Explanation**

This keeps business calculations deterministic and auditable while still offering a simple conversational experience for executives.
