from __future__ import annotations
from typing import Any
from sqlalchemy import text
from sqlalchemy.orm import Session


class SchemaTool:
    """Tool for getting database schema information"""

    @staticmethod
    def get_tool_definition() -> dict[str, Any]:
        """Return OpenAI function definition"""
        return {
            "type": "function",
            "function": {
                "name": "get_schema",
                "description": "Get database schema information including table names and column details. Use this when you need to understand the database structure.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "table_name": {
                            "type": "string",
                            "description": "Optional: specific table name to get details for. If not provided, returns all tables."
                        }
                    }
                }
            }
        }

    @staticmethod
    def get_schema(db: Session, table_name: str = None) -> dict[str, Any]:
        try:
            if table_name:

                # Get columns for specific table
                query = text("""
                    SELECT
                        column_name,
                        data_type,
                        is_nullable,
                        column_default
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    AND table_name = :table_name
                    ORDER BY ordinal_position
                """)
                result = db.execute(query, {"table_name": table_name})
            else:
                # Get all tables
                query = text("""
                    SELECT
                        table_name,
                        (SELECT COUNT(*)
                         FROM information_schema.columns c
                         WHERE c.table_name = t.table_name
                         AND c.table_schema = 'public') as column_count
                    FROM information_schema.tables t
                    WHERE table_schema = 'public'
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                """)
                result = db.execute(query)
            rows = [dict(row._mapping) for row in result]
            return{
                "success": True,
                "data": rows
            }

        except Exception as e:
            return {
                "success": False,
                "Error": e,
                "data": []
            }