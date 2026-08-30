```markdown
# Founder BI Agent — Monday.com Integration

A Business Intelligence agent that connects to live Monday.com boards and answers executive-style business questions across sales pipeline and work-order execution data.

## Overview

The Founder BI Agent combines a natural-language query planner with a deterministic BI calculation layer. 

The LLM is responsible for understanding the user's question and generating the final explanation, while business metrics are calculated from live Monday.com data using deterministic Python/pandas logic.

### Core Capabilities

- Fetches live data from Monday.com using the GraphQL API.
- Works across the Deal Funnel and Work Order Tracker boards.
- Cleans and normalizes text, numeric, monetary, and date fields.
- Dynamically discovers sectors from the live Monday.com boards.
- Understands natural-language business questions.
- Identifies user intent, relevant sector, and relevant board(s).
- Supports pipeline, deal-value, financial, collections, and execution-status questions.
- Supports lightweight conversational context for follow-up questions.
- Calculates BI metrics deterministically using pandas.
- Explicitly surfaces missing-data and data-quality caveats.
- Uses Groq/LangChain to generate concise executive-facing responses.
- Provides a Streamlit chat interface backed by a FastAPI API.

---

## Architecture

```text
                         User
                          |
                          v
                 +------------------+
                 |   Streamlit UI   |
                 |     app.py       |
                 +--------+---------+
                          |
                          | POST /api/chat
                          v
                 +------------------+
                 |  FastAPI Backend |
                 |     main.py      |
                 +--------+---------+
                          |
             +------------+-------------+
             |                          |
             v                          v
     +---------------+          +---------------+
     | MondayClient  |          | QueryPlanner  |
     | GraphQL API   |          | Groq / LLM    |
     +-------+-------+          +---------------+
             |
             v
     +---------------+
     |  cleaner.py   |
     | Data Cleaning |
     +-------+-------+
             |
             v
     +---------------+
     |   BIEngine    |
     | Deterministic |
     |   BI Metrics  |
     +-------+-------+
             |
             +----------------------+
                                    |
                                    v
                           +------------------+
                           | Groq / LangChain |
                           | Final Response   |
                           +------------------+

```
## Project Structure
```text
monday-bi-agent/
│
├── app.py
├── main.py
├── Monday_client.py
├── cleaner.py
├── bi_engine.py
├── query_planner.py
├── requirements.txt
├── .gitignore
└── README.md

```
### File Responsibilities
| File | Responsibility |
|---|---|
| app.py | Streamlit frontend and chat interface |
| main.py | FastAPI backend and overall request orchestration |
| Monday_client.py | Monday.com GraphQL API integration and board data retrieval |
| cleaner.py | Data cleaning and normalization |
| bi_engine.py | Deterministic BI calculations |
| query_planner.py | Natural-language query understanding and planning |
| requirements.txt | Python dependencies |
| .gitignore | Prevents secrets and unnecessary files from being committed |
## Data Flow
 1. The user enters a business question in the Streamlit interface.
 2. Streamlit sends the question and session ID to the FastAPI backend.
 3. The backend fetches live data from the configured Monday.com boards.
 4. The retrieved data is cleaned and normalized.
 5. QueryPlanner identifies:
   * User intent
   * Relevant sector
   * Relevant board(s)
   * Whether the question is a follow-up
   * Whether clarification is required
 6. BIEngine performs deterministic calculations on the relevant data.
 7. The verified metrics are provided to the LLM.
 8. Groq generates a natural-language executive response using the verified metrics.
 9. The API returns the answer together with the query plan and calculated BI data.
## Environment Variables
Create a .env file for local development. **Never commit real API keys or secrets to GitHub.**
```env
MONDAY_API_KEY=your_monday_api_key
DEALS_BOARD_ID=your_deals_board_id
WORK_ORDERS_BOARD_ID=your_work_orders_board_id
GROQ_API_KEY=your_groq_api_key

```
The same variables should be configured as environment variables/secrets in your deployment platform.
## Monday.com Configuration
The application uses two Monday.com boards:
### 1. Deal Funnel
The application dynamically retrieves the board's column IDs and maps them to their human-readable column titles. The BI layer uses the following relevant columns:
 * Sector/service
 * Masked Deal value
 * Deal Stage
 * Deal Status
 * Close Date (A)
 * Tentative Close Date
 * Created Date
### 2. Work Order Tracker
The relevant columns include:
 * Sector
 * Amount in Rupees (Incl of GST) (Masked)
 * Billed Value in Rupees (Incl of GST.) (Masked)
 * Collected Amount in Rupees (Incl of GST.) (Masked)
 * Execution Status
Additional financial and date fields are normalized when present.
### Board IDs
Board IDs are supplied through environment variables to separate configuration from application code:
```env
DEALS_BOARD_ID=your_deals_board_id
WORK_ORDERS_BOARD_ID=your_work_orders_board_id

```
## Query Planner
The Query Planner converts a natural-language business question into a structured plan. It determines:
 * Intent
 * Sector
 * Relevant board(s)
 * Follow-up status
 * Whether clarification is required
### Supported Intents
 * pipeline_health
 * pipeline_value
 * financial_summary
 * collections
 * execution_status
 * general
The planner does not calculate business metrics directly. It uses the sectors discovered dynamically from the live Monday.com boards rather than relying on a hard-coded sector list.
## BI Engine
BIEngine is responsible for deterministic business calculations. This separation is intentional:
```text
LLM
 ↓
Understands question
 ↓
Query Plan
 ↓
BIEngine
 ↓
Verified calculations
 ↓
LLM
 ↓
Executive explanation

```
The LLM is therefore not responsible for independently calculating financial or pipeline metrics.
### Pipeline Metrics
 * Total number of deals
 * Recorded deal value
 * Won deals
 * Lost deals
 * Deal stage distribution
 * Deal status distribution
 * Data-quality caveats
### Work Order Metrics
 * Total work orders
 * Contracted value
 * Billed value
 * Collected value
 * Outstanding billed value
 * Billing percentage
 * Collection percentage
 * Execution status distribution
 * Data-quality caveats
## Data Quality Handling
The application explicitly handles missing and invalid data. Examples include:
 * Missing deal values
 * Missing contracted amounts
 * Missing billed amounts
 * Missing collected amounts
 * Missing status/stage information
 * Invalid numeric values
 * Missing dates
Missing data is not automatically treated as zero when doing so could create a misleading business interpretation. Percentages are also handled safely when their denominator is zero or unavailable.
Distribution values with missing categories are represented as Unknown. This prevents missing values from causing invalid JSON responses while preserving the data-quality signal.
## Conversation Context
The application maintains lightweight session-level context to support follow-up questions. For example:
> **User:** How is the pipeline looking for Renewables?
> **Agent:** [Provides Renewables pipeline metrics]
> **User:** What about collections?
> 
The second question automatically utilizes the previously identified sector (Renewables). Only minimal context required for follow-up understanding is retained.
## Local Setup
### 1. Clone the repository
```bash
git clone [https://github.com/codehacker4655/monday-bi-agent.git](https://github.com/codehacker4655/monday-bi-agent.git)
cd monday-bi-agent

```
### 2. Create a virtual environment
 * **Windows:**
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   
   ```
 * **macOS/Linux:**
   ```bash
   python -m venv venv
   source venv/bin/activate
   
   ```
### 3. Install dependencies
```bash
pip install -r requirements.txt

```
### 4. Configure environment variables
Create a .env file in the root directory:
```env
MONDAY_API_KEY=your_monday_api_key
DEALS_BOARD_ID=your_deals_board_id
WORK_ORDERS_BOARD_ID=your_work_orders_board_id
GROQ_API_KEY=your_groq_api_key

```
## Running the Backend
Start the FastAPI backend:
```bash
uvicorn main:app --reload

```
The backend will run locally at http://localhost:8000. The main endpoint is POST /api/chat.
## Running the Frontend
Open a second terminal, activate the virtual environment, and run:
```bash
streamlit run app.py

```
In the Streamlit sidebar, set the backend endpoint to http://localhost:8000/api/chat.
## API Integration Specification
### Request Example (POST /api/chat)
```json
{
  "query": "How is our pipeline looking for renewables?",
  "session_id": "example-session-id"
}

```
### Response Example
```json
{
  "answer": "Executive response text generated by LLM...",
  "plan": {},
  "pipeline_data": {},
  "financial_data": {}
}

```
## Deployment
The application can be deployed as two distinct cloud services:
### FastAPI Backend (e.g., Render)
Start command:
```bash
uvicorn main:app --host 0.0.0.0 --port $PORT

```
Set environment variables (MONDAY_API_KEY, DEALS_BOARD_ID, WORK_ORDERS_BOARD_ID, GROQ_API_KEY) in the platform's settings.
### Streamlit Frontend (e.g., Streamlit Community Cloud)
Deploy using app.py as the entry point and set the API endpoint URL variable to point to your hosted FastAPI backend domain:
https://<backend-domain>/api/chat
## Design Decisions
 * **Deterministic BI Layer:** Metrics are computed via Python/pandas to eliminate LLM mathematical hallucinations.
 * **Dynamic Sector Discovery:** Sector categories are inferred directly from live board schema values.
 * **Separation of Concerns:** Clear pipeline flow (Data Ingestion \rightarrow Cleaning \rightarrow Intent Planning \rightarrow BI Math \rightarrow LLM Synthesis).
 * **Data Quality Transparency:** Surfaces missing fields explicitly to leadership users rather than masking them as zeros.
## Limitations & Future Roadmap
 * Advanced multi-board relational join features.
 * Automated time-series forecasting and trend metrics.
 * Exportable executive dashboards (PDF/CSV summaries).
 * High-performance caching layer to minimize Monday.com API rate limits.
 * Persistent database storage for long-term conversation history.
## Technology Stack
 * **Python**
 * **FastAPI**
 * **Streamlit**
 * **Pandas & NumPy**
 * **Monday.com GraphQL API**
 * **LangChain & Groq**
 * **Pydantic**
 * **python-dotenv**
```

```
