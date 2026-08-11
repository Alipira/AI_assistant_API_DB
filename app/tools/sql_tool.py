from __future__ import annotations

import re

from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Any
from app.config import get_settings

settings = get_settings()


class SQLTool:
    """Tool for executing SQL queries safely"""

    @staticmethod
    def get_tool_definition() -> dict[str, Any]:
        """Return OpenAI function definition"""
        return {
            "type": "function",
            "function": {
                "name": "query_database",
                "description": "Execute a SELECT query on the PostgreSQL database to retrieve data. Use this when the user asks questions about data in the database.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "SQL SELECT query to execute. Only SELECT queries are allowed."
                        },
                        "explanation": {
                            "type": "string",
                            "description": "Brief explanation of what this query does"
                        }
                    },
                    "required": ["query", "explanation"]
                }
            }
        }

    @staticmethod
    def validate_query(query: str) -> tuple[bool, str]:
        """Validate SQL query for safety"""
        query_upper = query.upper().strip()

        # Must be a SELECT query
        if not query_upper.startswith("SELECT"):
            return False, "Only SELECT queries are allowed"

        # Block dangerous keywords
        dangerous_keywords = [
            "DROP", "DELETE", "INSERT", "UPDATE", "ALTER",
            "CREATE", "TRUNCATE", "GRANT", "REVOKE", "EXECUTE"
        ]

        for keyword in dangerous_keywords:
            if re.search(rf'\b{keyword}\b', query_upper):
                return False, f"Keyword '{keyword}' is not allowed"

        # Check for semicolons (prevent multiple statements)
        if ";" in query.rstrip(";"):
            return False, "Multiple statements not allowed"

        return True, "Query validated"

    @staticmethod
    def execute_query(db: Session, query: str) -> dict[str, Any]:
        """Execute SQL query and return results"""

        # Validate query first
        is_valid, message = SQLTool.validate_query(query)
        if not is_valid:
            return {
                "success": False,
                "error": message,
                "rows": [],
                "query": query
            }

        try:
            # Add row limit
            if "LIMIT" not in query.upper():
                query = f"{query.rstrip(';')} LIMIT {settings.max_query_rows}"

            result = db.execute(text(query))
            rows = [dict(row._mapping) for row in result]

            return {
                "success": True,
                "rows": rows,
                "row_count": len(rows),
                "query_executed": query
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "rows": [],
                "query": query
            }
