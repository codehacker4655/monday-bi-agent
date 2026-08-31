import json
from typing import Optional, Dict, Any, List

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage


class QueryPlanner:
    """
    Converts a user's natural-language BI question into a structured plan.

    The planner does NOT calculate business metrics.
    It only determines:
        - user's intent
        - relevant sector
        - relevant board(s)
        - whether the question is a follow-up
        - whether clarification is required
    """

    def __init__(self, groq_api_key: str):
        if not groq_api_key:
            raise ValueError("GROQ_API_KEY is missing.")

        self.llm = ChatGroq(
            model_name="openai/gpt-oss-120b",
            groq_api_key=groq_api_key,
            temperature=0
        )

    def plan_query(
        self,
        query: str,
        previous_context: Optional[Dict[str, Any]] = None,
        deal_sectors: Optional[List[str]] = None,
        work_order_sectors: Optional[List[str]] = None
    ) -> Dict[str, Any]:

        previous_context = previous_context or {}
        deal_sectors = deal_sectors or []
        work_order_sectors = work_order_sectors or []

        system_prompt = f"""
You are the Query Planner for a Monday.com Business Intelligence Agent.

Your job is to understand the user's business question and convert it
into a structured query plan.

IMPORTANT:
- Do NOT calculate any business numbers.
- Do NOT invent sectors.
- Do NOT invent data.
- Use ONLY the sectors provided below.
- If a sector is not clearly identifiable, return null.
- Use previous conversation context when the user asks a follow-up question.

AVAILABLE SECTORS FROM THE LIVE MONDAY BOARDS:

Deal Funnel sectors:
{json.dumps(deal_sectors)}

Work Order Tracker sectors:
{json.dumps(work_order_sectors)}

PREVIOUS CONVERSATION CONTEXT:
{json.dumps(previous_context)}

SUPPORTED INTENTS:

1. pipeline_health
   Questions about sales pipeline health, number of deals,
   deal stages, deal statuses, open/won/lost deals.

2. pipeline_value
   Questions about deal value or sales pipeline value.

3. financial_summary
   Questions about contracted value, billed value,
   amount to be billed, receivables, or overall financial execution.

4. collections
   Questions about money collected, collection status,
   collection amount, or payments received.

5. execution_status
   Questions about work-order execution,
   completed/in-progress/pending execution, etc.

6. cross_board_analysis
   Questions that compare the sales pipeline and work-order
   execution, especially by sector, or ask for patterns,
   gaps, opportunities, or risks across both datasets.

7. general
   Questions that do not clearly fit the above.

BOARD SELECTION:

- pipeline_health and pipeline_value normally use Deal Funnel.
- financial_summary, collections and execution_status normally use
  Work Order Tracker.
- cross_board_analysis uses both Deal Funnel and Work Order Tracker.
- If the user explicitly asks for a cross-board comparison or an
  overall business view, both boards may be relevant.

FOLLOW-UP RULES:

- If the current question explicitly mentions a sector, use it.
- If the current question uses phrases such as:
  "it", "that", "there", "same sector", "the same one",
  "what about the money", "what about collections",
  use the previous context when appropriate.
- If there is no sector in the current question and no previous sector,
  return null.
- Never invent a sector just to make the question fit.
- A follow-up question should inherit relevant context from the previous
  turn unless the user explicitly changes it.

CLARIFICATION:

Set "needs_clarification" to true when the question is too ambiguous
to determine the requested business information safely.

Examples:

"What about it?" with no useful previous context
should require clarification.

"How is the business doing?"
may require clarification because it could refer to pipeline,
financial execution, collections, or overall business performance.

Return ONLY valid JSON in exactly this structure:

{{
    "intent": ""intent": "pipeline_health | pipeline_value | financial_summary | collections | execution_status | cross_board_analysis | general",",
    "sector": "exact sector from the provided lists or null",
    "boards": ["deal_funnel", "work_order_tracker"],
    "is_follow_up": true,
    "needs_clarification": false,
    "clarification_question": null,
    "reason": "short explanation"
}}
"""

        response = self.llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=query)
        ])

        raw_content = response.content.strip()

        # Handle accidental markdown code fences from the LLM.
        if raw_content.startswith("```"):
            raw_content = raw_content.replace("```json", "", 1)
            raw_content = raw_content.replace("```", "")
            raw_content = raw_content.strip()

        try:
            plan = json.loads(raw_content)

        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Query planner returned invalid JSON: {raw_content}"
            ) from exc

        # -----------------------------
        # Validate intent
        # -----------------------------

        valid_intents = {
            "pipeline_health",
            "pipeline_value",
            "financial_summary",
            "collections",
            "execution_status",
            "cross_board_analysis",
            "general"
        }

        if plan.get("intent") not in valid_intents:
            plan["intent"] = "general"

        # -----------------------------
        # Validate sector
        # -----------------------------

        all_sectors = set(
            deal_sectors + work_order_sectors
        )

        sector = plan.get("sector")

        if sector not in all_sectors:

            # If the model failed to identify a sector,
            # inherit the previous one only when available.
            previous_sector = previous_context.get("sector")

            if previous_sector in all_sectors:
                plan["sector"] = previous_sector

            else:
                plan["sector"] = None

        # -----------------------------
        # Validate boards
        # -----------------------------

        valid_boards = {
            "deal_funnel",
            "work_order_tracker"
        }

        boards = plan.get("boards", [])

        if not isinstance(boards, list):
            boards = []

        plan["boards"] = [
            board
            for board in boards
            if board in valid_boards
        ]

        # If the model doesn't return a board,
        # infer the normal board from the intent.
        if not plan["boards"]:

            if plan["intent"] in {
                "pipeline_health",
                "pipeline_value"
            }:
                plan["boards"] = [
                    "deal_funnel"
                ]

            elif plan["intent"] in {
                "financial_summary",
                "collections",
                "execution_status"
            }:
                plan["boards"] = [
                    "work_order_tracker"
                ]

            else:
                plan["boards"] = [
                    "deal_funnel",
                    "work_order_tracker"
                ]

        # cross_board_analysis ALWAYS needs both boards.
        if plan["intent"] == "cross_board_analysis":
            plan["boards"] = [
                "deal_funnel",
                "work_order_tracker"
            ]

        # -----------------------------
        # Follow-up flag
        # -----------------------------

        plan["is_follow_up"] = bool(
            plan.get("is_follow_up", False)
        )

        # -----------------------------
        # Clarification flag
        # -----------------------------

        plan["needs_clarification"] = bool(
            plan.get("needs_clarification", False)
        )

        if not plan["needs_clarification"]:
            plan["clarification_question"] = None

        return plan