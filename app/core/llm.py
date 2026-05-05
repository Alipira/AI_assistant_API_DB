from openai import OpenAI
from typing import List, Dict, Any, Optional
import json
from app.config.config import get_settings
from app.tools.API_tools import ApiTool
from app.core.prompts import get_contextual_prompt
from app.core.date_utils import resolve_date
from app.schema.chat_schema import ToolCall
from app.schema.Auth import AuthContext
from app.core.logging_config import get_logger

settings = get_settings()
logger = get_logger("llm")


class LLMClient:
    """OpenAI client with API tool integration"""
    DATE_BEARING_ACTIONS = {
        "Unit_history",
        "alarm_history",
        "continuing_alarm_history"
    }

    def __init__(self):
        self.client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_api_base
        )
        self.model = settings.openai_model
        self.tools = [ApiTool.get_tool_definition()]

    def chat(
        self,
        user_message: str,
        auth_context: AuthContext,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> tuple[str, List[ToolCall]]:
        """
        Process a chat message with API tool calling.

        Returns:
            tuple: (assistant_message, list_of_tool_calls)
        """
        system_prompt = get_contextual_prompt(user_message)

        messages: List[Dict] = [{"role": "system", "content": system_prompt}]

        # ── conversation history ──────────────────────────────────────────────
        if conversation_history:
            for msg in conversation_history:
                if hasattr(msg, 'role'):
                    messages.append({"role": msg.role, "content": msg.content})
                else:
                    messages.append(msg)

        # ── always append current user message last ───────────────────────────
        messages.append({"role": "user", "content": user_message})

        tool_calls_made: List[ToolCall] = []

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self.tools,
            tool_choice="auto",
            max_tokens=1024,
        )
        logger.debug(f"LLM call model={self.model} prompt_tokens={response.usage.prompt_tokens}")

        max_iterations = 10
        for _ in range(max_iterations):
            assistant_message = response.choices[0].message

            if not assistant_message.tool_calls:
                return assistant_message.content, tool_calls_made

            messages.append(assistant_message)

            for tool_call in assistant_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                logger.info(f"TOOL_CALL fn={function_name} args={function_args}")

                # ── Safety net: pre-resolve dates so the LLM never needs to ──
                # If the LLM passed raw Jalali/Gregorian or natural-language dates,
                # resolve them here before they reach the API layer.
                function_args = self._resolve_dates_in_args(function_args)

                result = self._execute_tool(function_name, function_args, auth_context)

                tool_calls_made.append(ToolCall(
                    tool_name=function_name,
                    arguments=function_args,
                    result=result,
                ))

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
                max_tokens=1024,
            )
            logger.debug(f"LLM call model={self.model} prompt_tokens={response.usage.prompt_tokens}")

        logger.warning(f"MAX_ITERATIONS reached after {max_iterations} loops")
        return "متأسفانه تعداد مراحل از حد مجاز گذشت.", tool_calls_made

    @staticmethod
    def _resolve_dates_in_args(args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pre-resolve FromDate and ToDate in tool arguments before they reach API_tools.
        Handles cases where the LLM passes already-resolved ISO dates (pass-through)
        or natural language / Jalali dates (convert to UTC ISO 8601).

        This is a safety net — date_utils in _Unit_history also resolves dates,
        but having it here means the LLM's tool_call arguments logged are already resolved.
        """
        if args.get("action") not in LLMClient.DATE_BEARING_ACTIONS:
            return args

        resolved = dict(args)

        # Top-level FromDate / ToDate (used by Unit_history)
        for field, position in [("FromDate", "start"), ("ToDate", "end")]:
            raw = resolved.get(field)
            if raw:
                utc, err = resolve_date(str(raw), position=position)
                if utc:
                    logger.debug(f"Date pre-resolved: {field} '{raw}' → {utc}")
                    resolved[field] = utc
                else:
                    logger.warning(f"Date pre-resolve failed: {field} '{raw}' → {err}")
                    # Leave the original value — _Unit_history will handle or report the error

        # Dates nested inside filters{} (used by alarm_history)
        if isinstance(resolved.get("filters"), dict):
            filters = dict(resolved["filters"])
            for field, position in [("FromDate", "start"), ("ToDate", "end")]:
                raw = filters.get(field)
                if raw:
                    utc, err = resolve_date(str(raw), position=position)
                    if utc:
                        filters[field] = utc
                        logger.debug(f"Filter date pre-resolved: {field} '{raw}' → {utc}")
                    else:
                        logger.warning(f"Filter date pre-resolve failed: {field} '{raw}' → {err}")
            resolved["filters"] = filters
        return resolved

    def _execute_tool(self, function_name: str, arguments: Dict[str, Any],
                      auth_context: AuthContext) -> Dict[str, Any]:
        if function_name == "call_backend_api":
            return ApiTool.call_backend_api(
                action=arguments.get("action", ""),
                query=arguments.get("query"),
                unit_id=arguments.get("unit_id"),
                filters=arguments.get("filters"),
                params=arguments.get("params"),
                FromDate=arguments.get("FromDate"),
                ToDate=arguments.get("ToDate"),
                auth_context=auth_context,
                explanation=arguments.get("explanation", ""),
            )
        return {"error": f"Unknown tool: {function_name}"}
