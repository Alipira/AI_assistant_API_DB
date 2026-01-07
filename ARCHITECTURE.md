# Complete System Architecture
## Overview Diagram
```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER (Farsi Questions)                       │
│         "ماشین 211 کجاست؟"  |  "درآمد این ماه چقدر بود؟"           │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FASTAPI APPLICATION                            │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  POST /api/chat                                               │ │
│  │  - Receives user question                                     │ │
│  │  - Creates DB session                                         │ │
│  │  - Calls LLM Client                                           │ │
│  └────────────────────────┬──────────────────────────────────────┘ │
└───────────────────────────┼─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      LLM CLIENT (app/core/llm.py)                   │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  1. Get contextual prompt (from prompts.py)                   │ │
│  │  2. Detect context: fleet/delivery/monitoring/revenue/etc     │ │
│  │  3. Register ALL tools (Database + API)                       │ │
│  │  4. Send to OpenAI GPT with tools                             │ │
│  └────────────────────────┬──────────────────────────────────────┘ │
└───────────────────────────┼─────────────────────────────────────────┘
                            │
                            ▼
                   ┌────────────────┐
                   │   OpenAI GPT   │
                   │   (gpt-4o)     │
                   │                │
                   │  Analyzes:     │
                   │  • Question    │
                   │  • Context     │
                   │  • Available   │
                   │    tools       │
                   │                │
                   │  Decides:      │
                   │  Which tool(s) │
                   │  to call       │
                   └────┬───────────┘
                        │
              ┌─────────┴─────────┐
              │                   │
              ▼                   ▼

    REAL-TIME DATA          HISTORICAL DATA
    (Use API)               (Use Database)

    ┌─────────────────┐    ┌─────────────────┐
    │   API TOOL      │    │   SQL TOOL      │
    │                 │    │                 │
    │ call_backend_   │    │ query_database  │
    │   api()         │    │                 │
    │                 │    │ get_schema()    │
    └────────┬────────┘    └────────┬────────┘
             │                      │
             ▼                      ▼

    ┌─────────────────┐    ┌─────────────────┐
    │  BACKEND API    │    │  PostgreSQL DB  │
    │                 │    │                 │
    │ • Vehicle GPS   │    │ • trips         │
    │ • Sensors       │    │ • vehicles      │
    │ • Telemetry     │    │ • drivers       │
    │ • Traffic       │    │ • revenue       │
    │ • Alerts        │    │ • costs         │
    └─────────────────┘    └─────────────────┘

             │                      │
             └──────────┬───────────┘
                        │
                        ▼

            ┌───────────────────────┐
            │  TOOL RESULTS         │
            │  (Combined if needed) │
            └───────────┬───────────┘
                        │
                        ▼

                ┌───────────────┐
                │   OpenAI GPT  │
                │               │
                │  Formats:     │
                │  • In Farsi   │
                │  • Per your   │
                │    prompts    │
                │  • With       │
                │    insights   │
                └───────┬───────┘
                        │
                        ▼

            ┌───────────────────────┐
            │  FASTAPI RESPONSE     │
            │                       │
            │  {                    │
            │    "message": "...",  │
            │    "tool_calls": [...] │
            │  }                    │
            └───────────┬───────────┘
                        │
                        ▼

            ┌───────────────────────┐
            │     USER              │
            │  (Farsi Response)     │
            └───────────────────────┘
```

---

## Decision Flow: Which Tool to Use?

```
User Question
    │
    ▼
┌────────────────────────────────────┐
│ Keyword Detection                  │
│ (detect_query_context)             │
└────────┬───────────────────────────┘
         │
         ▼

    کجا / الان / فعلی ?
         │
         ├─ YES → Context: "monitoring"
         │         Tool: call_backend_api
         │         Endpoint: /api/vehicles/location
         │
         └─ NO → Check next keywords
                    │
                    ▼

    دیروز / هفته گذشته / چند سفر ?
         │
         ├─ YES → Context: "delivery" or "fleet"
         │         Tool: query_database
         │         Query: SELECT ... FROM trips
         │
         └─ NO → Check next keywords
                    │
                    ▼

    درآمد / revenue / rpm ?
         │
         ├─ YES → Context: "revenue"
         │         Tool: query_database
         │         Query: SELECT revenue FROM ...
         │
         └─ NO → Default
                 Tool: query_database (safe default)
```

---

## Example Question Flows

### Example 1: Real-Time Location (API)

```
User: "ماشین 211 کجاست؟"
  │
  ▼ detect_query_context()

Keywords found: "ماشین", "کجا"
Context detected: "monitoring"
  │
  ▼ get_contextual_prompt()

System prompt + monitoring context:
"برای داده‌های لحظه‌ای از API استفاده کن"
  │
  ▼ OpenAI GPT decides

Tool selected: call_backend_api
Arguments: {
  "endpoint": "/api/vehicles/location",
  "params": {"vehicle_id": "211"}
}
  │
  ▼ APITool.call_backend_api()

GET http://backend:8080/api/vehicles/location?vehicle_id=211
Response: {
  "latitude": 35.6892,
  "longitude": 51.3890,
  "speed": 80
}
  │
  ▼ OpenAI GPT formats

Final response in Farsi:
"ماشین 211 در حال حاضر در مسیر تهران-قم است..."
```

---

### Example 2: Historical Data (Database)

```
User: "ماشین 211 هفته گذشته چند سفر داشت؟"
  │
  ▼ detect_query_context()

Keywords found: "ماشین", "هفته گذشته", "سفر"
Context detected: "delivery" or "fleet"
  │
  ▼ get_contextual_prompt()

System prompt + fleet/delivery context
  │
  ▼ OpenAI GPT decides

Tool selected: query_database
Arguments: {
  "query": "SELECT COUNT(*) FROM trips WHERE vehicle_id = '211'
            AND trip_date >= NOW() - INTERVAL '7 days'"
}
  │
  ▼ SQLTool.query_database()

Database query executed
Result: {"rows": [{"count": 12}]}
  │
  ▼ OpenAI GPT formats

Final response in Farsi:
"ماشین 211 در هفته گذشته 12 سفر انجام داده است..."
```

---

### Example 3: Combined (API + Database)

```
User: "ماشین 211 کجاست و امروز چند سفر رفته؟"
  │
  ▼ detect_query_context()

Keywords found: "کجا" + "امروز" + "سفر"
Multiple contexts: "monitoring" + "delivery"
  │
  ▼ get_contextual_prompt()

System prompt (may include both contexts)
  │
  ▼ OpenAI GPT decides

Tool 1: call_backend_api (for "کجاست")
Arguments: {
  "endpoint": "/api/vehicles/location",
  "params": {"vehicle_id": "211"}
}

Tool 2: query_database (for "چند سفر")
Arguments: {
  "query": "SELECT COUNT(*) FROM trips WHERE vehicle_id = '211'
            AND DATE(trip_date) = CURRENT_DATE"
}
  │
  ▼ Execute BOTH tools

API result: Current location
DB result: Today's trip count
  │
  ▼ OpenAI GPT combines & formats

Final response in Farsi:
"ماشین 211 در حال حاضر در مسیر تهران-اصفهان است...
امروز 3 سفر تکمیل شده و یک سفر در حال انجام است..."
```

---

## Your Custom Prompts Integration

```
┌─────────────────────────────────────────────────────┐
│            app/core/prompts.py                      │
│  ┌───────────────────────────────────────────────┐ │
│  │  BASE_PROMPT                                  │ │
│  │  ROLE_CONTEXT                                 │ │
│  │  BUSINESS_RULES                               │ │
│  │  METRIC_DEFINITIONS (RPM, CPW, etc.)          │ │
│  │  FORMATTING_REQUIREMENTS (Farsi, currency)    │ │
│  │  RESPONSE_STRUCTURE                           │ │
│  │  SPECIFIC_INSTRUCTIONS (Farsi responses!)     │ │
│  │  CONTEXT_PROMPTS (fleet, monitoring, etc.)    │ │
│  └───────────────────────────────────────────────┘ │
│                                                     │
│  ┌───────────────────────────────────────────────┐ │
│  │  get_contextual_prompt(user_message)          │ │
│  │    │                                           │ │
│  │    ├─ detect_query_context()                  │ │
│  │    │   • Checks Persian + English keywords    │ │
│  │    │   • Returns: monitoring/fleet/etc        │ │
│  │    │                                           │ │
│  │    ├─ get_system_prompt()                     │ │
│  │    │   • Combines all prompt sections         │ │
│  │    │                                           │ │
│  │    └─ Add context-specific guidance           │ │
│  │       • Appends CONTEXT_PROMPTS[context]      │ │
│  └───────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
                          │
                          ▼ Used by

                    LLM Client
          (Sends to OpenAI with every request)
```

---

## File Structure

```
ai-data-chatbot/
│
├── app/
│   ├── main.py                    # FastAPI server
│   ├── config.py                  # settings (database url, api, etc)
│   │
│   ├── api/
│   │   └── chat.py                # Chat endpoint (no changes)
│   │
│   ├── core/
│   │   ├── llm.py                 # Track tools call & conversation history
│   │   └── prompts.py
│   │
│   ├── tools/
│   │   ├── sql_tool.py            # Database queries (existing)
│   │   └── api_tool.py            # API calls
│   │
│   ├── db/
│   │   └── session.py             # Database connection (existing)
│   │
│   └── schemas/
│       └── chat.py                # Request/response models (existing)
│
├── .env
└── requirements.txt
```
