# 🚀 Founder BI Agent — Monday.com Integration

> **Ask business questions in plain English. Get executive-ready insights from live Monday.com data.**

---

## 🎯 What is this?

**Founder BI Agent** is a Business Intelligence agent that connects to live **Monday.com** boards and converts natural-language business questions into verified, data-driven answers.

It combines:

- 🧠 **LLM-powered query understanding**
- 📊 **Deterministic BI calculations**
- 🔗 **Monday.com GraphQL API**
- 💬 **Streamlit chat interface**
- ⚡ **FastAPI backend**
- 🛡️ **Data-quality and missing-value handling**

---

## ✨ Core Capabilities

| Capability | Description |
|---|---|
| 🔗 Live Monday.com Data | Fetches current data directly from Monday.com |
| 📈 Pipeline Intelligence | Analyzes deal pipeline and deal values |
| 💰 Financial Intelligence | Calculates contracted, billed, collected and outstanding amounts |
| 🏗️ Work Order Intelligence | Analyzes work-order execution status |
| 🧠 Natural Language | Ask questions without writing SQL or Python |
| 🎯 Sector Filtering | Dynamically identifies and filters by sector |
| 💬 Follow-up Questions | Maintains lightweight conversation context |
| 🛡️ Verified Metrics | Business calculations are performed deterministically |
| ⚠️ Data Quality | Explicitly surfaces missing or unavailable data |
| 🤖 LLM Explanation | Converts verified metrics into concise executive answers |

---

## 🏗️ Architecture

```mermaid
flowchart LR
    A[👤 User] --> B[💬 Streamlit UI]
    B --> C[⚡ FastAPI API]

    C --> D[🔗 Monday.com Client]
    D --> E[(📊 Deal Funnel)]
    D --> F[(🏗️ Work Order Tracker)]

    E --> G[🧹 Data Cleaning]
    F --> G

    G --> H[🧠 Query Planner]
    H --> I[📊 BI Engine]

    I --> J[✅ Verified Metrics]
    J --> K[🤖 Groq LLM]

    K --> L[💡 Executive Answer]
    L --> B


---

🔄 How It Works

<details>
<summary><b>1️⃣ User asks a question</b></summary>The user enters a natural-language business question through the Streamlit chat interface.

Example:

> "How is our pipeline looking for Renewable Energy?"



</details><details>
<summary><b>2️⃣ Live data is fetched</b></summary>The backend connects to Monday.com through its GraphQL API and retrieves the required board data.

</details><details>
<summary><b>3️⃣ Data is cleaned</b></summary>Raw Monday.com data is normalized before calculations.

This includes handling:

Text fields

Numeric values

Monetary values

Dates

Missing values

Sector names


</details><details>
<summary><b>4️⃣ Query Planner understands the question</b></summary>The LLM determines the user's:

Intent

Relevant sector

Relevant board(s)

Whether clarification is required


</details><details>
<summary><b>5️⃣ BI Engine calculates the metrics</b></summary>The BI Engine performs deterministic calculations using Pandas.

The LLM does not calculate the business metrics.

</details><details>
<summary><b>6️⃣ LLM generates the explanation</b></summary>The verified metrics are passed to the LLM, which converts them into a concise executive-style response.

The LLM is instructed to:

Never invent numbers

Use only verified metrics

Distinguish missing data from zero

Mention important data-quality caveats


</details>
---

📊 Supported Business Questions

📈 Pipeline

Examples:

How is our pipeline looking?

What is the pipeline value for Renewable Energy?

How many deals have we won?

How many deals have been lost?

💰 Financial

Examples:

How much have we billed?

How much have we collected?

What is the outstanding billed amount?

What percentage of the contracted value has been billed?

🏗️ Work Orders

Examples:

How many work orders do we have?

What is the execution status?

How much value has been contracted?

What is the collection percentage?

💬 Follow-up Questions

The application maintains lightweight session context so users can ask follow-up questions.

Example:

User: How is our pipeline for Renewable Energy?

Agent: ...

User: How many of those deals are won?

Agent: ...


---

🧠 Design Philosophy

LLM for Understanding — Code for Truth

A key design principle of this project is:

Natural Language
       ↓
     LLM
       ↓
 Query Plan
       ↓
Deterministic BI
       ↓
Verified Metrics
       ↓
     LLM
       ↓
Executive Answer

The LLM is responsible for understanding and explaining.

The BI layer is responsible for calculating business metrics.

This reduces the risk of the LLM hallucinating financial or pipeline numbers.


---

🛡️ Data Quality

The system explicitly handles incomplete data.

For example:

5 out of 42 deals have missing deal values.

Instead of treating missing values as zero, the system surfaces them as a data-quality caveat.

Percentages are also calculated safely:

If denominator = 0
        ↓
Return None
        ↓
Do not incorrectly report 0%


---

🗂️ Project Structure

monday-bi-agent/
│
├── app.py
├── streamlit_app.py
│
├── Monday_client.py
├── cleaner.py
├── bi_engine.py
├── query_planner.py
│
├── requirements.txt
├── README.md
├── .gitignore
│
└── .env

> 🔐 .env is used for local development and should never be committed to GitHub.




---

🔑 Environment Variables

Create a .env file locally:

MONDAY_API_KEY=your_monday_api_key
DEALS_BOARD_ID=your_deals_board_id
WORK_ORDERS_BOARD_ID=your_work_orders_board_id
GROQ_API_KEY=your_groq_api_key

For production deployment, configure these values as environment variables in the hosting platform.


---

⚙️ Local Setup

1. Clone the repository

git clone https://github.com/codehacker4655/monday-bi-agent.git
cd monday-bi-agent

2. Create a virtual environment

python -m venv venv

Activate it:

Windows

venv\Scripts\activate

macOS/Linux

source venv/bin/activate

3. Install dependencies

pip install -r requirements.txt

4. Configure environment variables

Create .env and add your credentials:

MONDAY_API_KEY=...
DEALS_BOARD_ID=...
WORK_ORDERS_BOARD_ID=...
GROQ_API_KEY=...

5. Start the FastAPI backend

uvicorn app:app --reload

6. Start the Streamlit frontend

streamlit run streamlit_app.py


---

🌐 Deployment

The application can be deployed using a cloud platform such as Render.

Typical architecture:

Streamlit Frontend
        │
        ▼
FastAPI Backend
        │
        ├── Monday.com
        │
        └── Groq

Production secrets should be configured through environment variables rather than committed to the repository.


---

🧪 Example Interaction

👤 User
How is our pipeline looking for Renewable Energy?

🤖 Founder BI Agent

Pipeline analysis for Renewable Energy:

• Total deals: ...
• Recorded pipeline value: ...
• Won deals: ...
• Lost deals: ...

⚠️ Data quality:
Some deals have missing deal values.

The exact figures are calculated from the live Monday.com data.


---

🧰 Technology Stack

Technology	Purpose

🐍 Python	Core application
⚡ FastAPI	Backend API
💬 Streamlit	User interface
📊 Pandas	Deterministic BI calculations
🔗 Monday.com GraphQL API	Live business data
🤖 Groq	LLM inference
🦜 LangChain	LLM integration
☁️ Render	Deployment



---

🔐 Security Notes

API keys are stored as environment variables.

.env should remain in .gitignore.

Secrets should never be hard-coded.

Production credentials should be configured through the deployment platform's secret/environment-variable system.



---

🎯 Key Engineering Decisions

<details>
<summary><b>Why not let the LLM calculate everything?</b></summary>LLMs are useful for interpreting natural-language questions, but deterministic code is more reliable for financial and business calculations.

Therefore:

LLM → intent and explanation

Pandas/BI Engine → calculations

</details><details>
<summary><b>Why dynamically discover sectors?</b></summary>The application reads the actual sector values present in Monday.com instead of relying on a hard-coded list.

This allows the system to adapt when new sectors appear in the boards.

</details><details>
<summary><b>Why explicitly track missing values?</b></summary>Missing data and zero are not the same thing.

For example:

Missing deal value ≠ ₹0 deal value

The system therefore surfaces missing data instead of silently converting it into a misleading business result.

</details>
---

🚀 Future Improvements

Potential future enhancements include:

📅 Advanced date-based analysis

📊 More pipeline KPIs

📈 Trend analysis

🔍 Deeper cross-board relationships

💾 Persistent conversation memory

🧪 Automated test coverage

⚡ Caching for faster responses

📉 Executive dashboards and visualizations

🧠 More advanced query planning



---

👨‍💻 Project

Founder BI Agent — Monday.com Integration

Built as a full-stack AI + Business Intelligence application combining live business data, deterministic analytics, and natural-language interaction.

⭐ If you find the project useful, consider giving the repository a star!
