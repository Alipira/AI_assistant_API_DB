import requests
from typing import Dict, Optional, Any, List
from app.schema.Auth import ActionSpec, AuthContext
from app.config.config import get_settings
from app.core.logging_config import get_logger
from app.core.date_utils import resolve_date_range

logger = get_logger("api_tools")
settings = get_settings()


class ApiTool:

    ACTIONS: Dict[str, ActionSpec] = {
        "vehicle_tracking_current": ActionSpec(
            endpoint="/api/v2/Unit/TrackingUnitsByUnitIds",
            method="GET",
            allowed_params=("unitIds",),
            description=(
                "Get current location of a vehicle or person by name, plate, or ID. "
                "Provide the vehicle or person identifier in params as 'query'. "
                "The tool will find the unitId automatically."
            ),
        ),
        "Unit_history": ActionSpec(
            endpoint="/api/v2/Unit/UnitCoordinatesForTrackingPage",
            method="GET",
            allowed_params=("unitIds", "FromDate", "ToDate"),
            description=(
                "Get the location history of a vehicle or person by name, plate, or ID. "
                "Provide the identifier as 'query', plus FromDate and ToDate as ISO 8601 strings. "
                "The tool will find the unitId automatically."
            ),
        ),
        "sensor_current": ActionSpec(
            endpoint="/api/v2/SystemParameter",
            method="GET",
            allowed_params=("UnitId",),
            description="Get current sensor data for a vehicle (temperature, humidity, speed). Requires UnitId.",
        ),
        "driver_status": ActionSpec(
            endpoint="/api/drivers/status",
            method="GET",
            allowed_params=("SearchString", "PageNumber", "PageSize"),
            description="Get driver availability and status.",
        ),
        "active_alarms": ActionSpec(
            endpoint="/api/v2/Alarm/AlarmsList",
            method="GET",
            allowed_params=("SystemParameterFilters", "HasGeofenceFilter", "SearchString", "PageNumber", "PageSize"),
            description="Get active system alerts.",
        ),
        "alarm_history": ActionSpec(
            endpoint="/api/v2/AlaramLog",
            method="GET",
            allowed_params=("SearchWord", "PageNumber", "PageSize", "FromDate", "ToDate"),
            description="Get alarm logs history.",
        ),
        "continuing_alarm_history": ActionSpec(
            endpoint="/api/v2/AlaramLog/GetContinuingAlarmLogs",
            method="GET",
            allowed_params=("SearchWord", "PageNumber", "PageSize", "FromDate", "ToDate"),
            description="Get current/ongoing alarm logs history.",
        ),
    }

    @staticmethod
    def get_tool_definition() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "call_backend_api",
                "description": (
                    "Call a backend API to get fleet data. "
                    "For vehicle/person current location use action=vehicle_tracking_current and set query to their name, plate, or ID. "
                    "For vehicle/person location history use action=Unit_history and set query to their name, plate, or ID, plus FromDate and ToDate. "
                    "For sensor data use action=sensor_current and set unit_id. "
                    "For alarms use action=active_alarms."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": list(ApiTool.ACTIONS.keys()),
                            "description": "The action to call.",
                        },
                        "query": {
                            "type": "string",
                            "description": (
                                "REQUIRED for vehicle_tracking_current and Unit_history. "
                                "Pass ONLY ONE identifier — either the plate number OR the vehicle/driver name, not both. "
                                "Use the plate number when given (e.g. '91-ع-587-15'). "
                                "Use the name only when no plate is available (e.g. 'سعید شاکری نسب'). "
                                "Never concatenate name and plate together."
                            ),
                        },
                        "unit_id": {
                            "type": "string",
                            "description": (
                                "REQUIRED for sensor_current. "
                                "The unitId returned by a previous vehicle_tracking_current call."
                            ),
                        },
                        "FromDate": {
                            "type": "string",
                            "format": "date-time",
                            "description": (
                                "REQUIRED for Unit_history. "
                                "Start of the time range in ISO 8601 format. "
                                "Example: '2026-04-01T00:00:00Z'"
                            ),
                        },
                        "ToDate": {
                            "type": "string",
                            "format": "date-time",
                            "description": (
                                "REQUIRED for Unit_history. "
                                "End of the time range in ISO 8601 format. "
                                "Example: '2026-04-18T23:59:59Z'"
                            ),
                        },
                        "filters": {
                            "type": "object",
                            "description": (
                                "Optional filters for alarm/driver actions. "
                                "Keys: SearchString, PageNumber, PageSize, FromDate, ToDate, AlarmTypeFilters."
                            ),
                            "additionalProperties": True,
                        },
                        "explanation": {
                            "type": "string",
                            "description": "Brief explanation of what is being requested.",
                        },
                    },
                    "required": ["action", "explanation"],
                    "additionalProperties": False,
                },
            },
        }

    @staticmethod
    def _build_headers(auth_context: AuthContext) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {auth_context.access_token}",
            "X-User-Id": auth_context.user_id,
        }

    @staticmethod
    def _sanitize_params(action: str, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        spec = ApiTool.ACTIONS[action]
        incoming = params or {}
        return {k: v for k, v in incoming.items() if k in spec.allowed_params and v is not None}

    # ─── Step 1: Find unitId from vehicle name/plate/ID ───────────────────────

    @staticmethod
    def _find_unit_id(query: str, auth_context: AuthContext) -> tuple[Optional[str], Optional[Dict]]:
        url = f"{settings.backend_api_url}/api/v2/Unit/All"
        headers = ApiTool._build_headers(auth_context)

        try:
            logger.debug(f"Unit/All → URL={url} SearchWord={query!r}")
            logger.debug(f"Unit/All → Token[:20]={auth_context.access_token[:20]!r} X-User-Id={auth_context.user_id!r}")

            response = requests.get(
                url,
                params={"SearchWord": query},
                headers=headers,
                timeout=settings.api_timeout,
            )

            logger.debug(f"Unit/All → status={response.status_code} body={response.text[:500]!r}")

            if response.status_code in (401, 403):
                logger.warning(f"Unit/All auth rejected status={response.status_code} query={query!r}")
                return None, {"success": False, "error": "شما دسترسی به این داده را ندارید.", "status_code": response.status_code}

            response.raise_for_status()
            data = response.json()

            if isinstance(data, list):
                unit_list = data
            elif isinstance(data, dict):
                unit_list = data.get("data") or data.get("items") or data.get("result") or data.get("units") or []
            else:
                unit_list = []

            if not isinstance(unit_list, list):
                return None, {"success": False, "error": f"فرمت پاسخ API ناشناخته است: {type(unit_list)}"}

            logger.debug(f"Unit/All → count={len(unit_list)}")

            if not unit_list:
                return None, {"success": False, "error": f"هیچ موردی با مشخصه '{query}' یافت نشد."}

            if len(unit_list) > 1:
                choices = "\n".join(
                    f"- {u.get('title') or u.get('firstTitle') or 'نامشخص'} (نوع: {u.get('unitTypeIconName') or u.get('unitType', '؟')})"
                    for u in unit_list[:10]
                )
                return None, {
                    "success": False,
                    "multiple_results": True,
                    "count": len(unit_list),
                    "error": f"چندین مورد با مشخصه '{query}' یافت شد، لطفاً دقیق‌تر مشخص کنید:\n{choices}",
                }

            unit = unit_list[0]
            if not isinstance(unit, dict):
                return None, {"success": False, "error": f"فرمت آیتم ناشناخته: {type(unit)}"}

            unit_id = unit.get("unitId") or unit.get("id")
            if not unit_id:
                logger.debug(f"Unit/All → no id field, keys={list(unit.keys())}")
                return None, {"success": False, "error": f"فیلد 'unitId' در پاسخ API یافت نشد. فیلدهای موجود: {list(unit.keys())}"}

            logger.debug(f"Unit/All → matched id={unit_id} title={unit.get('title')!r}")
            return unit_id, unit

        except requests.exceptions.Timeout:
            return None, {"success": False, "error": "درخواست جستجو با timeout مواجه شد."}
        except requests.exceptions.ConnectionError:
            return None, {"success": False, "error": "اتصال به سرور ممکن نیست."}
        except Exception as e:
            return None, {"success": False, "error": f"خطا در یافتن مورد: {str(e)}"}

    # ─── Step 2a: Get current tracking data ───────────────────────────────────

    @staticmethod
    def _get_tracking(unit_id: str, auth_context: AuthContext) -> tuple[Optional[Dict], Optional[Dict]]:
        """
        Fetch current tracking data for a single unit.
        Uses GET with unitIds as a query param — the backend does not accept a POST body here.
        """
        url = f"{settings.backend_api_url}/api/v2/Unit/TrackingUnitsByUnitIds"
        headers = ApiTool._build_headers(auth_context)
        logger.debug(f"Tracking → GET {url} unitIds={unit_id!r}")

        try:
            response = requests.get(
                url,
                params={"unitIds": unit_id},
                headers=headers,
                timeout=settings.api_timeout,
            )

            logger.debug(f"Tracking → status={response.status_code} body={response.text[:300]!r}")

            if response.status_code in (401, 403):
                logger.warning(f"Tracking auth rejected status={response.status_code}")
                return None, {"success": False, "error": "شما دسترسی به این داده را ندارید.", "status_code": response.status_code}

            response.raise_for_status()

            try:
                data = response.json()
            except Exception as json_err:
                logger.error(f"Tracking → JSON parse failed: {json_err} body={response.text[:300]!r}")
                return None, {"success": False, "error": "پاسخ سرور قابل پردازش نیست."}

            tracking_list = data if isinstance(data, list) else data.get("data", data.get("items", data.get("result", [])))
            logger.debug(f"Tracking → parsed count={len(tracking_list) if isinstance(tracking_list, list) else 1}")

            if not tracking_list:
                return None, {"success": False, "error": "اطلاعات ردیابی برای این مورد موجود نیست."}

            return tracking_list[0] if isinstance(tracking_list, list) else tracking_list, None

        except requests.exceptions.Timeout:
            return None, {"success": False, "error": "درخواست tracking با timeout مواجه شد."}
        except requests.exceptions.ConnectionError:
            return None, {"success": False, "error": "اتصال به سرور ممکن نیست."}
        except Exception as e:
            logger.error(f"Tracking → unexpected error: {e}")
            return None, {"success": False, "error": f"خطا در دریافت موقعیت: {str(e)}"}

    # ─── Step 2b: Get coordinate history ──────────────────────────────────────

    @staticmethod
    def _get_coordinate_history(
        unit_id: str,
        from_date: str,
        to_date: str,
        auth_context: AuthContext,
    ) -> tuple[Optional[List], Optional[Dict]]:
        """
        GET coordinate history from UnitCoordinatesForTrackingPage.

        Actual response structure:
        [
          {
            "unitId": "...",
            "markerTitle": "...",
            "trackCoordinates": [
              {
                "recordId": "...",
                "latitude": 38.04,
                "longitude": 46.23,
                "direction": 285,
                "timestamp": "2026-04-27T11:36:37Z",
                "persianTimestamp": "1405/02/07 - 15:06",
                "parameters": [
                  {"systemParameterTitle": "سرعت", "value": "55", ...},
                  {"systemParameterTitle": "دما",   "value": null, ...},
                  {"systemParameterTitle": "رطوبت", "value": null, ...},
                  {"systemParameterTitle": "سیگنال دریافتی", "value": "عالی", ...}
                ]
              }, ...
            ],
            "logCoordinates": []
          }
        ]
        """
        url = f"{settings.backend_api_url}/api/v2/Unit/UnitCoordinatesForTrackingPage"
        headers = ApiTool._build_headers(auth_context)
        logger.debug(f"History → URL={url} unit_id={unit_id!r} from={from_date!r} to={to_date!r}")

        try:
            response = requests.get(
                url,
                params={"unitIds": unit_id, "FromDate": from_date, "ToDate": to_date},
                headers=headers,
                timeout=settings.api_timeout,
            )

            logger.debug(f"History → status={response.status_code}")

            if response.status_code in (401, 403):
                logger.warning(f"History auth rejected status={response.status_code}")
                return None, {"success": False, "error": "شما دسترسی به این داده را ندارید.", "status_code": response.status_code}

            response.raise_for_status()
            data = response.json()

            # Response is a list of unit objects, each containing trackCoordinates
            raw_list = data if isinstance(data, list) else data.get("data", data.get("items", data.get("result", [])))

            if not raw_list:
                return [], None

            # Return the first unit's record (we queried by single unitId)
            return raw_list[0] if isinstance(raw_list, list) else raw_list, None

        except requests.exceptions.Timeout:
            return None, {"success": False, "error": "درخواست تاریخچه با timeout مواجه شد."}
        except Exception as e:
            return None, {"success": False, "error": f"خطا در دریافت تاریخچه: {str(e)}"}

    # ─── Step 3: Reverse geocode lat/lon to address ────────────────────────────

    @staticmethod
    def _reverse_geocode(lat: float, lon: float) -> Optional[str]:
        try:
            response = requests.get(
                "https://nominatim.shonizcloud.ir/reverse",
                params={"lat": lat, "lon": lon, "format": "json"},
                timeout=5,
                headers={"Accept-Language": "fa"},
            )
            response.raise_for_status()
            data = response.json()
            return data.get("display_name")
        except Exception:
            return None

    # ─── Helper: extract a named parameter from the parameters[] array ─────────

    @staticmethod
    def _get_param_value(parameters: List[Dict], title: str) -> Optional[str]:
        """Extract value from a parameters array by systemParameterTitle."""
        for p in parameters:
            if p.get("systemParameterTitle") == title:
                return p.get("value")
        return None

    # ─── Full chained current tracking call ───────────────────────────────────

    @staticmethod
    def _vehicle_tracking_current(params: Dict[str, Any], auth_context: AuthContext) -> Dict[str, Any]:
        query = params.get("query", "").strip()
        if not query:
            return {"success": False, "error": "query is required. Example: query='سعید شاکری نسب'"}

        unit_id, unit_data = ApiTool._find_unit_id(query, auth_context)
        if unit_id is None:
            return unit_data

        logger.info(f"Tracking current → unit_id={unit_id} query={query!r}")

        tracking, error = ApiTool._get_tracking(unit_id, auth_context)
        if tracking is None:
            return error

        coords = tracking.get("latestTrackRecordCoordinates") or {}
        lat = tracking.get("latitude") or tracking.get("lat") or coords.get("latitude")
        lon = tracking.get("longitude") or tracking.get("lon") or tracking.get("lng") or coords.get("longitude")

        logger.debug(f"Coordinates → lat={lat} lon={lon} unit_id={unit_id}")

        address = None
        if lat and lon:
            address = ApiTool._reverse_geocode(lat, lon)

        unit_type_icon = unit_data.get("unitTypeIconName") or unit_data.get("unitType", "")
        unit_type_category = ApiTool._classify_unit_type(unit_type_icon)
        is_online = tracking.get("isOnline", False)
        last_seen = tracking.get("timestampStatus")

        # Speed is inside markerParameters
        speed = next(
            (p["value"] for p in tracking.get("markerParameters", []) if p.get("systemParameterTitle") == "سرعت"),
            tracking.get("speed"),
        )

        # Distinguish clearly between "found but offline" and "found with location"
        # so the LLM knows not to retry when coordinates are simply unavailable.
        location_available = lat is not None and lon is not None

        return {
            "success": True,
            "location_available": location_available,
            # Clear message for the LLM — avoids pointless retries
            "location_status": (
                "آنلاین و موقعیت در دسترس است" if (is_online and location_available)
                else "آفلاین - آخرین موقعیت ثبت‌شده در دسترس است" if (not is_online and location_available)
                else "آفلاین - هیچ موقعیتی ثبت نشده است"
            ),
            "unit_id": unit_id,
            "unit_info": {
                "name": unit_data.get("title") or unit_data.get("firstTitle"),
                "plate": unit_data.get("secondTitle"),
                "unit_type": unit_type_icon,
                "unit_type_category": unit_type_category,
            },
            "status": {
                "is_online": is_online,
                "last_seen": last_seen,
            },
            "tracking": {
                "latitude": lat,
                "longitude": lon,
                "speed": speed,
                "direction": tracking.get("direction"),
                "timestamp": tracking.get("timestamp") or tracking.get("dateTime"),
            },
            "address": address or (f"lat: {lat}, lon: {lon}" if location_available else None),
        }

    # ─── Full chained history call ─────────────────────────────────────────────

    @staticmethod
    def _Unit_history(params: Dict[str, Any], auth_context: AuthContext) -> Dict[str, Any]:
        """
        2-step location history:
        1. Find unitId from query (name / plate / ID)
        2. Fetch coordinate history and normalise the trackCoordinates array

        Actual API response per record in trackCoordinates:
          latitude, longitude, direction, timestamp, persianTimestamp,
          parameters[]: سرعت, دما, رطوبت, سیگنال دریافتی
        """
        query     = params.get("query", "").strip()
        from_raw  = params.get("FromDate", "").strip()
        to_raw    = params.get("ToDate", "").strip()

        # Validate required fields before any API call
        missing = [f for f, v in [("query", query), ("FromDate", from_raw), ("ToDate", to_raw)] if not v]
        if missing:
            return {
                "success": False,
                "error": (
                    f"فیلدهای زیر برای Unit_history الزامی هستند: {', '.join(missing)}. "
                    "مثال: query='volvo FH12', FromDate='دیروز' یا '1405/02/10' یا '2026-04-18T00:00:00Z', ToDate='امروز'"
                ),
            }

        # Resolve natural language / Jalali / Gregorian dates → UTC ISO 8601
        from_date, to_date, date_err = resolve_date_range(from_raw, to_raw)
        if date_err:
            return {"success": False, "error": date_err}

        logger.debug(f"History → dates resolved: '{from_raw}' → {from_date}, '{to_raw}' → {to_date}")

        # Step 1 — find unitId
        unit_id, unit_data = ApiTool._find_unit_id(query, auth_context)
        if unit_id is None:
            return unit_data

        logger.info(f"History → unit_id={unit_id} query={query!r} from={from_date!r} to={to_date!r}")

        # Step 2 — fetch coordinate history
        unit_record, error = ApiTool._get_coordinate_history(unit_id, from_date, to_date, auth_context)
        if unit_record is None:
            return error

        # unit_record is the first element of the API response list:
        # { "unitId": "...", "markerTitle": "...", "trackCoordinates": [...], "logCoordinates": [...] }
        track_coordinates: List[Dict] = unit_record.get("trackCoordinates", []) if isinstance(unit_record, dict) else []

        if not track_coordinates:
            return {
                "success": True,
                "unit_id": unit_id,
                "unit_info": {
                    "name": unit_data.get("title") or unit_data.get("firstTitle"),
                    "plate": unit_data.get("secondTitle"),
                    "unit_type": unit_data.get("unitTypeIconName") or unit_data.get("unitType", ""),
                },
                "from_date": from_date,
                "to_date": to_date,
                "record_count": 0,
                "coordinates": [],
                "summary": None,
                "message": "هیچ رکورد مسیری برای این بازه زمانی یافت نشد.",
            }

        # Normalise each trackCoordinate record
        # Note: signal parameter title varies by backend config ("سیگنال دریافتی" or "وضعیت سیگنال")
        normalised = []
        for record in track_coordinates:
            parameters = record.get("parameters", [])
            signal = (
                ApiTool._get_param_value(parameters, "سیگنال دریافتی") or
                ApiTool._get_param_value(parameters, "وضعیت سیگنال")
            )
            normalised.append({
                "timestamp": record.get("timestamp"),
                "persian_timestamp": record.get("persianTimestamp"),
                "latitude": record.get("latitude"),
                "longitude": record.get("longitude"),
                "direction": record.get("direction"),
                "speed": ApiTool._get_param_value(parameters, "سرعت"),
                "temperature": ApiTool._get_param_value(parameters, "دما"),
                "humidity": ApiTool._get_param_value(parameters, "رطوبت"),
                "signal": signal,
            })

        # Build a summary — guard against null/non-numeric values
        def _safe_float(v):
            try:
                return float(v) if v is not None else None
            except (ValueError, TypeError):
                return None

        speeds = [s for r in normalised if (s := _safe_float(r["speed"])) is not None]
        temps  = [t for r in normalised if (t := _safe_float(r["temperature"])) is not None]

        summary = {
            "first_seen": normalised[0]["persian_timestamp"],
            "last_seen":  normalised[-1]["persian_timestamp"],
            "first_location": {
                "latitude": normalised[0]["latitude"],
                "longitude": normalised[0]["longitude"],
            },
            "last_location": {
                "latitude": normalised[-1]["latitude"],
                "longitude": normalised[-1]["longitude"],
            },
            "speed_kmh": {
                "min": min(speeds) if speeds else None,
                "max": max(speeds) if speeds else None,
                "avg": round(sum(speeds) / len(speeds), 1) if speeds else None,
            },
            "temperature_c": {
                "min": min(temps) if temps else None,
                "max": max(temps) if temps else None,
                "avg": round(sum(temps) / len(temps), 1) if temps else None,
            } if temps else None,
            "overspeed_records": [
                {"timestamp": r["persian_timestamp"], "speed": r["speed"]}
                for r in normalised if r["speed"] is not None and float(r["speed"]) > 120
            ],
        }

        logger.info(f"History → {len(normalised)} records, speed avg={summary['speed_kmh']['avg']} km/h")

        return {
            "success": True,
            "unit_id": unit_id,
            "unit_info": {
                "name": unit_data.get("title") or unit_data.get("firstTitle"),
                "plate": unit_data.get("secondTitle"),
                "unit_type": unit_data.get("unitTypeIconName") or unit_data.get("unitType", ""),
            },
            "from_date": from_date,
            "to_date": to_date,
            "record_count": len(normalised),
            # summary is the key field — LLM should use this for the answer
            "summary": summary,
            # full coordinates list — LLM can reference specific records if asked
            "coordinates": normalised[:50],  # cap at 50 to keep context window manageable
        }

    @staticmethod
    def _classify_unit_type(unit_type_icon_name: str) -> str:
        name = unit_type_icon_name.strip()
        VEHICLE_TYPES = {"کامیون", "سدان", "وانت", "اتوبوس", "مینی‌بوس", "سنگین", "موتور", "truck", "car", "van"}
        PERSON_TYPES  = {"شخص", "person", "پرسنل", "کارمند", "راننده"}
        if name in VEHICLE_TYPES:
            return "vehicle"
        if name in PERSON_TYPES:
            return "person"
        return "asset"

    # ─── Main dispatcher ───────────────────────────────────────────────────────

    @staticmethod
    def call_backend_api(
        action: str,
        params: Optional[Dict[str, Any]] = None,
        auth_context: Optional[AuthContext] = None,
        explanation: str = "",
        query: Optional[str] = None,
        unit_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        FromDate: Optional[str] = None,
        ToDate: Optional[str] = None,
    ) -> Dict[str, Any]:

        if action not in ApiTool.ACTIONS:
            return {"success": False, "error": f"Unsupported action: {action}"}
        if auth_context is None:
            return {"success": False, "error": "Missing auth context"}

        # ── vehicle_tracking_current ──────────────────────────────────────────
        if action == "vehicle_tracking_current":
            resolved_query = query or (params or {}).get("query") or (params or {}).get("unitId")
            if not resolved_query:
                return {"success": False, "error": "query is required for vehicle_tracking_current."}
            return ApiTool._vehicle_tracking_current({"query": resolved_query}, auth_context)

        # ── Unit_history ──────────────────────────────────────────────────────
        if action == "Unit_history":
            resolved_query = query or (params or {}).get("query")
            resolved_from  = FromDate or (params or {}).get("FromDate") or (filters or {}).get("FromDate")
            resolved_to    = ToDate   or (params or {}).get("ToDate")   or (filters or {}).get("ToDate")
            return ApiTool._Unit_history(
                {"query": resolved_query or "", "FromDate": resolved_from or "", "ToDate": resolved_to or ""},
                auth_context,
            )

        # ── sensor_current ────────────────────────────────────────────────────
        if action == "sensor_current":
            resolved_unit_id = unit_id or (params or {}).get("UnitId") or (params or {}).get("unitId")
            if not resolved_unit_id:
                return {"success": False, "error": "unit_id is required for sensor_current."}
            params = {"UnitId": resolved_unit_id}

        if filters:
            params = filters

        base_url = settings.backend_api_url
        if not base_url:
            return {"success": False, "error": "Backend API URL is not configured"}

        spec = ApiTool.ACTIONS[action]
        clean_params = ApiTool._sanitize_params(action, params)
        url = f"{base_url}{spec.endpoint}"
        headers = ApiTool._build_headers(auth_context)

        logger.debug(f"{spec.method} {url} | params={clean_params}")

        try:
            method = spec.method.upper()
            if method == "GET":
                response = requests.get(url, params=clean_params, headers=headers, timeout=settings.api_timeout)
            elif method == "POST":
                response = requests.post(url, json=clean_params, headers=headers, timeout=settings.api_timeout)
            else:
                return {"success": False, "error": f"Unsupported HTTP method: {spec.method}"}

            if response.status_code in (401, 403):
                logger.warning(f"Auth rejected action={action} status={response.status_code}")
                return {"success": False, "error": "شما دسترسی به این داده را ندارید.", "status_code": response.status_code}

            response.raise_for_status()

            try:
                payload = response.json()
            except Exception:
                payload = {"raw_text": response.text}

            logger.info(f"Success action={action} status={response.status_code}")
            return {"success": True, "data": payload, "status_code": response.status_code, "action": action}

        except requests.exceptions.Timeout:
            return {"success": False, "error": "API request timed out."}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "Cannot connect to backend API."}
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else None
            return {"success": False, "error": f"API error: {status_code}", "status_code": status_code}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {str(e)}"}
