import os
from typing import Dict, Any
import math
import numbers

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

from Monday_client import MondayClient
from cleaner import clean_deals_dataframe, clean_work_orders_dataframe
from bi_engine import BIEngine
from query_planner import QueryPlanner

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage


load_dotenv()

app = FastAPI(title="Monday.com Business Intelligence Agent")

DEALS_BOARD_ID = os.getenv("DEALS_BOARD_ID")
WORK_ORDERS_BOARD_ID = os.getenv("WORK_ORDERS_BOARD_ID")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


if not DEALS_BOARD_ID:
    raise RuntimeError("DEALS_BOARD_ID is missing from .env")

if not WORK_ORDERS_BOARD_ID:
    raise RuntimeError("WORK_ORDERS_BOARD_ID is missing from .env")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is missing from .env")


class QueryRequest(BaseModel):
    query: str
    session_id: str


# --------------------------------------------------
# Convert NaN / Infinity into JSON-safe values
# --------------------------------------------------
def sanitize_for_json(obj):
    """
    Recursively convert non-JSON-safe numeric values
    such as NaN and Infinity into None.
    """

    if isinstance(obj, dict):
        return {
            key: sanitize_for_json(value)
            for key, value in obj.items()
        }

    if isinstance(obj, (list, tuple)):
        return [
            sanitize_for_json(value)
            for value in obj
        ]

    # Handle NumPy/Python numeric values
    if isinstance(obj, numbers.Real):
        value = float(obj)

        if math.isnan(value) or math.isinf(value):
            return None

        return value

    return obj


# Stores only the small amount of context needed
# to understand follow-up questions.
conversation_contexts: Dict[str, Dict[str, Any]] = {}


@app.post("/api/chat")
async def process_bi_query(request: QueryRequest):
    try:

        # --------------------------------------------------
        # 1. Fetch live data from Monday.com
        # --------------------------------------------------
        client = MondayClient()

        raw_deals = client.fetch_board_as_dataframe(
            DEALS_BOARD_ID
        )

        raw_wo = client.fetch_board_as_dataframe(
            WORK_ORDERS_BOARD_ID
        )

        # --------------------------------------------------
        # 2. Clean and normalize the data
        # --------------------------------------------------
        deals_df = clean_deals_dataframe(raw_deals)
        wo_df = clean_work_orders_dataframe(raw_wo)

        # --------------------------------------------------
        # 3. Discover actual sectors dynamically
        # --------------------------------------------------
        deal_sectors = (
            deals_df["Sector/service"]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
            .tolist()
            if "Sector/service" in deals_df.columns
            else []
        )

        work_order_sectors = (
            wo_df["Sector"]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
            .tolist()
            if "Sector" in wo_df.columns
            else []
        )

        # --------------------------------------------------
        # 4. Retrieve previous conversation context
        # --------------------------------------------------
        previous_context = conversation_contexts.get(
            request.session_id,
            {}
        )

        # --------------------------------------------------
        # 5. Understand the user's question
        # --------------------------------------------------
        planner = QueryPlanner(GROQ_API_KEY)

        plan = planner.plan_query(
            query=request.query,
            previous_context=previous_context,
            deal_sectors=deal_sectors,
            work_order_sectors=work_order_sectors
        )

        # --------------------------------------------------
        # 6. Handle ambiguous questions
        # --------------------------------------------------
        if plan.get("needs_clarification"):
            return sanitize_for_json({
                "answer": plan.get(
                    "clarification_question",
                    "Could you clarify what information you need?"
                ),
                "plan": plan,
                "pipeline_data": {},
                "financial_data": {}
            })

        sector_target = plan.get("sector")
        intent = plan.get("intent")

        # --------------------------------------------------
        # 7. Run verified BI calculations
        # --------------------------------------------------
        bi = BIEngine(
            deals_df=deals_df,
            wo_df=wo_df
        )

        pipeline_summary = {}
        financial_summary = {}

        if intent in {
            "pipeline_health",
            "pipeline_value"
        }:
            pipeline_summary = bi.get_pipeline_health(
                sector=sector_target
            )

        elif intent in {
            "financial_summary",
            "collections",
            "execution_status"
        }:
            financial_summary = bi.get_financial_execution_summary(
                sector=sector_target
            )

        else:
            # General questions may require both datasets.
            pipeline_summary = bi.get_pipeline_health(
                sector=sector_target
            )

            financial_summary = bi.get_financial_execution_summary(
                sector=sector_target
            )

        # --------------------------------------------------
        # 8. Save context for the next question
        # --------------------------------------------------
        conversation_contexts[request.session_id] = {
            "sector": sector_target,
            "intent": intent,
            "boards": plan.get("boards", [])
        }

        # --------------------------------------------------
        # 9. Generate the final natural-language answer
        # --------------------------------------------------
        llm = ChatGroq(
            model_name="openai/gpt-oss-120b",
            groq_api_key=GROQ_API_KEY,
            temperature=0.1
        )

        system_prompt = """
You are a Monday.com Business Intelligence Agent for executives.

Answer the user's question using ONLY the verified BI metrics
provided below.

IMPORTANT:
- Never invent numbers.
- Never calculate business metrics yourself when the verified
  metrics already provide them.
- Clearly distinguish missing data from zero.
- Mention relevant data-quality caveats.
- If the requested metric is not available, say so.
- Be concise, clear and business-focused.
"""

        user_prompt = f"""
User Question:
{request.query}

Query Plan:
{plan}

Verified Pipeline Metrics:
{pipeline_summary}

Verified Work Order Metrics:
{financial_summary}
"""

        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])

        # --------------------------------------------------
        # 10. Return JSON-safe response
        # --------------------------------------------------
        return sanitize_for_json({
            "answer": response.content,
            "plan": plan,
            "pipeline_data": pipeline_summary,
            "financial_data": financial_summary
        })

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )