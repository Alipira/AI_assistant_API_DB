# """OpenAI LLM client with DATABASE + API tool integration"""
# from openai import OpenAI
# from sqlalchemy.orm import Session
# from typing import List, Dict, Any
# import json
# from app.config import get_settings
# from app.tools.sql_tool import SQLTool
# from app.tools.schema_tool import SchemaTool
# from app.tools.api_tools import ApiTool, CombinedDataTool
# from app.core.prompts import get_contextual_prompt
# from app.schemas.chat import ToolCall

# settings = get_settings()


# class LLMClient:
#     """OpenAI client with database AND API tool integration"""

#     def __init__(self):
#         self.client = OpenAI(api_key=settings.openai_api_key, base_url='https://api.metisai.ir/openai/v1')
#         self.model = settings.openai_model

#         # Register ALL tools (Database + API)
#         self.tools = [
#             # Database tools
#             SQLTool.get_tool_definition(),
#             SchemaTool.get_tool_definition(),

#             # API tools
#             ApiTool.get_tool_definition(),
#             CombinedDataTool.get_tool_definition(),
#         ]

#     def chat(
#         self,
#         user_message: str,
#         db: Session,
#         conversation_history: List[Dict[str, str]] = None
#     ) -> tuple[str, List[ToolCall]]:
#         """
#         Process chat message with DATABASE + API tool calling

#         Returns:
#             tuple: (assistant_message, list_of_tool_calls)
#         """

#         # Get context-aware system prompt (uses your prompts.py functions!)
#         system_prompt = get_contextual_prompt(user_message)

#         # Build messages
#         messages = [
#             {"role": "system", "content": system_prompt}
#         ]

#         # Add conversation history if provided
#         if conversation_history:
#             messages.extend(conversation_history)

#         messages.append({"role": "user", "content": user_message})

#         # Track tool calls
#         tool_calls_made = []

#         # Initial API call
#         response = self.client.chat.completions.create(
#             model=self.model,
#             messages=messages,
#             tools=self.tools,
#             tool_choice="auto"  # Let GPT decide which tool to use!
#         )

#         # Handle tool calls
#         max_iterations = 100
#         iteration = 0

#         while iteration < max_iterations:
#             iteration += 1
#             assistant_message = response.choices[0].message

#             # Check if there are tool calls
#             if not assistant_message.tool_calls:
#                 # No more tool calls, return final message
#                 return assistant_message.content, tool_calls_made

#             # Add assistant message to conversation
#             messages.append(assistant_message)

#             # Execute each tool call
#             for tool_call in assistant_message.tool_calls:
#                 function_name = tool_call.function.name
#                 function_args = json.loads(tool_call.function.arguments)

#                 # Execute the tool (DB or API)
#                 result = self._execute_tool(function_name, function_args, db)

#                 # Track tool call
#                 tool_calls_made.append(ToolCall(
#                     tool_name=function_name,
#                     arguments=function_args,
#                     result=result
#                 ))

#                 # Add tool result to messages
#                 messages.append({
#                     "role": "tool",
#                     "tool_call_id": tool_call.id,
#                     "content": json.dumps(result)
#                 })

#             # Get next response
#             response = self.client.chat.completions.create(
#                 model=self.model,
#                 messages=messages,
#                 tools=self.tools,
#                 tool_choice="auto"
#             )

#         # Max iterations reached
#         return "متأسفانه تعداد مراحل از حد مجاز گذشت. لطفاً سوال خود را دوباره بپرسید.", tool_calls_made

#     def _execute_tool(
#         self,
#         function_name: str,
#         arguments: Dict[str, Any],
#         db: Session
#     ) -> Dict[str, Any]:
#         """
#         Execute a tool function - supports BOTH database and API tools!
#         """

#         # ═══════════════════════════════════════════════
#         # DATABASE TOOLS
#         # ═══════════════════════════════════════════════

#         if function_name == "query_database":
#             query = arguments.get("query", "")
#             return SQLTool.execute_query(db, query)

#         elif function_name == "get_schema":
#             table_name = arguments.get("table_name")
#             return SchemaTool.get_schema(db, table_name)

#         # ═══════════════════════════════════════════════
#         # API TOOLS
#         # ═══════════════════════════════════════════════

#         elif function_name == "call_backend_api":
#             endpoint = arguments.get("endpoint", "")
#             params = arguments.get("params", {})
#             return ApiTool.call_backend_api(endpoint, params)

#         elif function_name == "get_combined_data":
#             # This is a special tool that combines DB + API
#             # You can implement custom logic here
#             data_needed = arguments.get("data_needed", "")
#             vehicle_id = arguments.get("vehicle_id")

#             results = {
#                 "database_data": {},
#                 "api_data": {},
#                 "combined": True
#             }

#             # Get historical data from DB
#             if vehicle_id:
#                 db_query = f"SELECT * FROM trips WHERE vehicle_id = '{vehicle_id}' ORDER BY trip_date DESC LIMIT 10"
#                 results["database_data"] = SQLTool.execute_query(db, db_query)

#                 # Get current location from API
#                 api_result = ApiTool.call_backend_api(
#                     "/api/vehicles/location",
#                     {"vehicle_id": vehicle_id}
#                 )
#                 results["api_data"] = api_result

#             return results

#         # ═══════════════════════════════════════════════
#         # UNKNOWN TOOL
#         # ═══════════════════════════════════════════════

#         else:
#             return {"error": f"Unknown tool: {function_name}"}




"""OpenAI LLM client with custom base URL support"""
from openai import OpenAI
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import json
from app.config import get_settings
from app.tools.sql_tool import SQLTool
from app.tools.schema_tool import SchemaTool
from app.tools.api_tools import ApiTool
from app.core.prompts import get_contextual_prompt
from app.schemas.chat import ToolCall

settings = get_settings()


class LLMClient:
    """OpenAI client with database AND API tool integration"""

    def __init__(self):
        # Initialize OpenAI client with custom base URL
        self.client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_api_base  # ← Custom endpoint support
        )
        self.model = settings.openai_model

        # Register ALL tools (Database + API)
        self.tools = [
            # Database tools
            SQLTool.get_tool_definition(),
            SchemaTool.get_tool_definition(),

            # API tools
            ApiTool.get_tool_definition(),
        ]

    def chat(
        self,
        user_message: str,
        db: Session,
        conversation_history: List[Dict[str, str]] = None
    ) -> tuple[str, List[ToolCall]]:
        """
        Process chat message with DATABASE + API tool calling

        Returns:
            tuple: (assistant_message, list_of_tool_calls)
        """

        # Get context-aware system prompt
        system_prompt = get_contextual_prompt(user_message)

        # Build messages
        messages = [
            {"role": "system", "content": system_prompt}
        ]

        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)

        messages.append({"role": "user", "content": user_message})

        # Track tool calls
        tool_calls_made = []

        # Initial API call
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self.tools,
            tool_choice="auto"
        )

        # Handle tool calls
        max_iterations = 5
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            assistant_message = response.choices[0].message

            # Check if there are tool calls
            if not assistant_message.tool_calls:
                # No more tool calls, return final message
                return assistant_message.content, tool_calls_made

            # Add assistant message to conversation
            messages.append(assistant_message)

            # Execute each tool call
            for tool_call in assistant_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                # Execute the tool (DB or API)
                result = self._execute_tool(function_name, function_args, db)

                # Track tool call
                tool_calls_made.append(ToolCall(
                    tool_name=function_name,
                    arguments=function_args,
                    result=result
                ))

                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result)
                })

            # Get next response
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools,
                tool_choice="auto"
            )

        # Max iterations reached
        return "متأسفانه تعداد مراحل از حد مجاز گذشت. لطفاً سوال خود را دوباره بپرسید.", tool_calls_made

    def _execute_tool(
        self,
        function_name: str,
        arguments: Dict[str, Any],
        db: Session
    ) -> Dict[str, Any]:
        """Execute a tool function - supports BOTH database and API tools"""

        # Database Tools
        if function_name == "query_database":
            query = arguments.get("query", "")
            return SQLTool.execute_query(db, query)

        elif function_name == "get_schema":
            table_name = arguments.get("table_name")
            return SchemaTool.get_schema(db, table_name)

        # API Tools
        elif function_name == "call_backend_api":
            endpoint = arguments.get("endpoint", "")
            params = arguments.get("params", {})
            return ApiTool.call_backend_api(endpoint, params)

        # Unknown Tool
        else:
            return {"error": f"Unknown tool: {function_name}"}