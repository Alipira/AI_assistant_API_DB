"""Tool for calling api which retrive data from PostgresSql data base"""
import requests
from typing import Dict, Any, Optional
from app.config import get_settings

settings = get_settings()


class ApiTool:
    """Tool for execute the api."""

    @staticmethod
    def get_tool_definition() -> Dict[str, Any]:
        """Return OpenAI function definition"""
        return {
            "type": "function",
            "function": {
                "name": "call_backend_api",
                "description": """Call the backend software API to get real-time data not available in database.
                                Use this for:
                                - Real-time GPS vehicle tracking and location
                                - Live temperature/humidity sensor data from refrigerated trucks
                                - Driver status and availability
                                - Vehicle telematics (speed, fuel level, engine status)
                                - Real-time alerts and notifications
                                Do NOT use this for historical data - use database queries instead.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "endpoint": {
                            "type": "string",
                            "description": """API endpoint to call. Available endpoints:
                                            Vehicle Tracking:
                                            - /api/v1/TrackRecord - Get current location of vehicles along with its speed
                                            - /api/vehicles/status - Get vehicle status (moving, idle, stopped)

                                            Sensors:
                                            - /api/v1/SystemParameter - Get vehicle's Parameter/sensor data, such as humidity, temperature, speed, etc

                                            Operations:
                                            - /api/drivers/status - Get driver availability and status

                                            Alaram:
                                            - /api/v1/Alarm/AlarmsList - Get active system alerts

                                            AlaramLog:
                                            - /api/v1/AlaramLog - Get alaram logs history, if the user have the specific role like admin, use, etc
                                            - /api/v1/AlaramLog/GetContinuingAlarmLogs - Get current/on going alaram logs history"""
                        },
                        "params": {
                            "type": "object",
                            "description": "Query parameters for the API call",
                            "properties": {
                                "AlarmTypeFilters": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "Alarm types for a Vehicle, Available values : 0, 1, 2, 3"
                                },
                                "SearchString": {"type": "string", "description": ""},
                                "PageNumber": {"type": "integer", "description": ""},
                                "PageSize": {"type": "integer", "description": ""},
                                "SearchWord": {"type": "string", "description": ""},
                                "UnitId": {"type": "string", "format": "uuid"},
                                "FromDate": {"type": "string", "format": "date-time", "description": "start time (ISO format)"},
                                "ToDate": {"type": "string", "format": "date-time", "description": "End time (ISO format)"},
                                "IsAdmin": {"type": "boolean", "description": ""},
                                "UserName": {"type": "string", "description": ""}
                            }
                        },
                        "explanation": {
                            "type": "string",
                            "description": "Brief explanation of what data you're requesting and why"
                        }
                    },
                    "required": ["endpoint", "explanation"]
                }
            }
        }

    @staticmethod
    def call_backend_api(
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        method: str = "GET"
    ) -> Dict[str, Any]:
        """
        Call backend API endpoint

        Args:
            endpoint: API endpoint path (e.g., '/api/vehicles/location')
            params: Query parameters or request body
            method: HTTP method (GET, POST, etc.)

        Returns:
            API response data or error
        """

        try:
            # Build full URL
            base_url = settings.backend_api_url.rstrip('/')
            url = f"{base_url}{endpoint}"

            # Prepare headers
            headers = {
                "Content-Type": "application/json",
            }

            # Add authentication if configured
            if settings.backend_api_key:
                headers["Authorization"] = f"Bearer {settings.backend_api_key}"
            elif settings.backend_api_token:
                headers["X-API-Token"] = settings.backend_api_token

            # Make request
            if method.upper() == "GET":
                response = requests.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=settings.api_timeout
                )
            elif method.upper() == "POST":
                response = requests.post(
                    url,
                    json=params,
                    headers=headers,
                    timeout=settings.api_timeout
                )
            else:
                return {
                    "success": False,
                    "error": f"Unsupported HTTP method: {method}"
                }

            # Check response
            response.raise_for_status()

            return {
                "success": True,
                "data": response.json(),
                "status_code": response.status_code,
                "endpoint": endpoint
            }

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "API request timed out. The backend service may be slow or unavailable.",
                "endpoint": endpoint
            }

        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": "Cannot connect to backend API. Please check if the service is running.",
                "endpoint": endpoint
            }

        except requests.exceptions.HTTPError as e:
            return {
                "success": False,
                "error": f"API returned error: {e.response.status_code} - {e.response.text}",
                "status_code": e.response.status_code,
                "endpoint": endpoint
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error calling API: {str(e)}",
                "endpoint": endpoint
            }