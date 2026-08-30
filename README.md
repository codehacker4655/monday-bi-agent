# Founder BI Agent — Monday.com Integration

> Ask business questions in plain English and get executive-ready insights from live Monday.com data.

## What is this?

Founder BI Agent is a Business Intelligence agent that connects to live Monday.com boards and answers business questions using natural language.

The project combines:

- LLM-powered query understanding
- Deterministic BI calculations
- Monday.com GraphQL API
- Streamlit chat interface
- FastAPI backend
- Data cleaning and normalization
- Missing-value and data-quality handling

## Core Capabilities

- Fetches live data from Monday.com boards
- Works with Deal Funnel and Work Order Tracker data
- Cleans and normalizes business data
- Dynamically discovers available sectors
- Understands natural-language business questions
- Identifies user intent and relevant sector
- Supports pipeline and deal-value questions
- Supports financial and collections questions
- Supports work-order execution-status questions
- Maintains lightweight conversation context for follow-up questions
- Calculates BI metrics deterministically using pandas
- Handles missing values explicitly
- Generates concise executive-style answers using an LLM
- Provides a Streamlit chat interface backed by FastAPI

## Architecture

The application follows a simple pipeline:

User
→ Streamlit Chat Interface
→ FastAPI Backend
→ Monday.com Client
→ Data Cleaning
→ Query Planner
→ BI Engine
→ LLM Response
→ User

### Main Components

**Streamlit UI**

Provides the chat interface where users can ask business questions.

**FastAPI Backend**

Receives the user's question and coordinates the complete processing pipeline.

**Monday.com Client**

Connects to Monday.com using the GraphQL API and fetches live board data.

**Data Cleaning**

Cleans and normalizes text, numeric, monetary, and date fields before analysis.

**Query Planner**

Uses an LLM to understand the user's question and determine:

- User intent
- Relevant sector
- Relevant board or boards
- Whether clarification is required

**BI Engine**

Performs deterministic calculations using pandas.

The BI Engine is responsible for verified business metrics such as:

- Total deals
- Recorded deal value
- Won and lost deals
- Pipeline stage distribution
- Deal status distribution
- Total work orders
- Contracted value
- Billed value
- Collected value
- Outstanding billed value
- Billing percentage
- Collection percentage
- Execution status distribution

**LLM Response Layer**

The LLM receives the verified metrics from the BI Engine and converts them into a concise business-friendly explanation.

The LLM is not responsible for calculating the underlying business metrics.

## How It Works

When a user asks a question, the following steps take place:

### 1. User asks a question

Example:

"What is the pipeline looking like for renewable energy?"

### 2. Live Monday.com data is fetched

The backend retrieves the latest data from the configured Monday.com boards.

### 3. Data is cleaned

The raw data is cleaned and normalized so that calculations can be performed reliably.

### 4. Available sectors are discovered

The application checks the actual data to determine which sectors are available.

This avoids relying on a hard-coded sector list.

### 5. Query is understood

The Query Planner analyzes the user's question and identifies the required intent and sector.

### 6. BI calculations are performed

The BI Engine performs deterministic calculations on the cleaned data.

### 7. Data-quality issues are identified

Missing values and unavailable fields are explicitly reported instead of silently treating them as valid zero values.

### 8. Final answer is generated

The verified metrics are passed to the LLM.

The LLM converts those metrics into a concise executive-style response.

## Example Questions

The agent can answer questions such as:

- What is our pipeline looking like?
- What is the pipeline value for renewable energy?
- How many deals have we won?
- How many deals have we lost?
- What is our total contracted value?
- How much have we billed?
- How much have we collected?
- What is the outstanding billed amount?
- What is our billing percentage?
- What is our collection percentage?
- What is the execution status of our work orders?
- How is the pipeline looking for a particular sector?

## Data Quality

Data quality is treated as an important part of the system.

The application does not automatically assume that missing data means zero.

For example:

- Missing deal values are reported
- Missing contracted amounts are reported
- Missing billed amounts are reported
- Missing collected amounts are reported
- Missing business fields are identified
- Percentages are not calculated when their denominator is unavailable or zero

This helps prevent misleading business conclusions.

## Technology Stack

### Backend

- Python
- FastAPI
- Pydantic

### Data Processing

- pandas

### LLM

- LangChain
- Groq
- GPT-OSS 120B

### Data Source

- Monday.com GraphQL API

### Frontend

- Streamlit

### Deployment

- Render

## Project Structure

```text
monday-bi-agent/
│
├── app.py
├── Monday_client.py
├── cleaner.py
├── bi_engine.py
├── query_planner.py
├── requirements.txt
├── .env
└── README.md

Environment Variables

Create a .env file with the required configuration:

DEALS_BOARD_ID=your_deals_board_id
WORK_ORDERS_BOARD_ID=your_work_orders_board_id
GROQ_API_KEY=your_groq_api_key

Do not commit the .env file or expose API keys publicly.

Running the Backend

Install the dependencies:

pip install -r requirements.txt

Start the FastAPI application:

uvicorn app:app --reload

The API endpoint used by the Streamlit interface is:

POST /api/chat

Running the Streamlit Interface

Start the Streamlit application using the project's Streamlit entry file.

The Streamlit interface sends the user's question to the FastAPI backend and displays the generated business response.

Design Principles

1. Verified Metrics First

Business numbers are calculated by the BI Engine rather than generated by the LLM.

2. LLM for Understanding and Explanation

The LLM is primarily used for:

Understanding natural-language questions

Planning the required analysis

Explaining verified results


3. Dynamic Data Discovery

The application discovers sectors directly from the live Monday.com data instead of relying completely on hard-coded values.

4. Explicit Data Quality

Missing data is surfaced to the user so that business decisions are based on transparent information.

5. Lightweight Conversation Context

The application stores limited context for a session so that follow-up questions can refer to the previous sector or intent.

Limitations

The application depends on the availability of the Monday.com API.

The quality of the answers depends on the quality and completeness of the source data.

Conversation context is currently stored in application memory.

The current BI Engine supports a defined set of business metrics and intents.

More advanced analytical questions may require additional BI calculations and query-planning logic.


Future Improvements

Possible future improvements include:

More business metrics

More advanced follow-up question handling

Better query planning

Additional Monday.com boards

Persistent conversation memory

More detailed data-quality reporting

Authentication and access control

Automated testing

Improved visual analytics and dashboards


Summary

Founder BI Agent connects live Monday.com business data with natural-language interaction.

The system separates:

Question Understanding → Data Processing → Verified BI Calculations → Natural-Language Explanation

This separation helps keep business calculations deterministic while still providing a simple conversational experience for executives.

