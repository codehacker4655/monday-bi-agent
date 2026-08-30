import os
import requests
import pandas as pd
from typing import Dict, Any

MONDAY_API_URL = "https://api.monday.com/v2"


class MondayClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("MONDAY_API_KEY")

        if not self.api_key:
            raise ValueError(
                "MONDAY_API_KEY environment variable is missing."
            )

        self.headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
            "API-Version": "2024-01"
        }

    def execute_query(
        self,
        query: str,
        variables: Dict[str, Any] = None
    ) -> Dict[str, Any]:

        """Execute a GraphQL query with HTTP and GraphQL error handling."""

        response = requests.post(
            MONDAY_API_URL,
            json={
                "query": query,
                "variables": variables
            },
            headers=self.headers,
            timeout=30
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"HTTP Error {response.status_code}: {response.text}"
            )

        data = response.json()

        if "errors" in data:
            raise RuntimeError(
                f"GraphQL API Errors: {data['errors']}"
            )

        return data

    def fetch_board_as_dataframe(
        self,
        board_id: str
    ) -> pd.DataFrame:

        """Fetch all items from a Monday board using cursor pagination."""

        all_items = []
        cursor = None
        has_more = True

        while has_more:

            cursor_param = (
                f', cursor: "{cursor}"'
                if cursor
                else ""
            )

            query = f"""
            query {{
                boards(ids: [{board_id}]) {{
                    columns {{
                        id
                        title
                    }}

                    items_page(limit: 500{cursor_param}) {{
                        cursor

                        items {{
                            id
                            name

                            column_values {{
                                id
                                text
                            }}
                        }}
                    }}
                }}
            }}
            """

            result = self.execute_query(query)

            boards = result.get(
                "data",
                {}
            ).get(
                "boards",
                []
            )

            if not boards:
                break

            col_map = {
                col["id"]: col["title"]
                for col in boards[0].get("columns", [])
            }

            page_data = boards[0].get(
                "items_page",
                {}
            )

            items = page_data.get(
                "items",
                []
            )

            for item in items:

                row = {
                    "Item ID": item["id"],
                    "Item Name": item["name"]
                }

                for col in item.get(
                    "column_values",
                    []
                ):

                    col_title = col_map.get(
                        col["id"],
                        col["id"]
                    )

                    row[col_title] = col.get("text")

                all_items.append(row)

            cursor = page_data.get("cursor")

            has_more = bool(
                cursor and len(items) > 0
            )

        return pd.DataFrame(all_items)