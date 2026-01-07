# Complete Guide: Database + API Integration

## 📋 Overview

Your chatbot now has access to **TWO data sources**:

1. **PostgreSQL Database** → Historical data, records, analytics
2. **Backend API** → Real-time data, live tracking, sensors

The LLM will **intelligently decide** which tool to use based on the user's question!

---

## Setup Instructions

### Step 1: Update Configuration

**File: `app/config.py`**

Add these new settings:

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # NEW: Backend API Settings
    backend_api_url: str = "http://localhost:8080"
    backend_api_key: str = ""  # Bearer token
    backend_api_token: str = ""  # Alternative token header
    api_timeout: int = 10
```

### Step 2: Update Environment Variables

**File: `.env`**

Add these lines:

```bash
# Existing settings
DATABASE_URL=postgresql://user:password@localhost:5432/transport_db
OPENAI_API_KEY=sk-your-key-here

# NEW: Backend API Configuration
BACKEND_API_URL=http://your-backend-server:8080
BACKEND_API_KEY=your-api-bearer-token-here
# OR use API_TOKEN instead:
# BACKEND_API_TOKEN=your-api-token-here

# API timeout (seconds)
API_TIMEOUT=10
```

### Step 3: Create API Tool

**File: `app/tools/api_tool.py`**

Copy the complete `api_tool.py` file I created above.

### Step 4: Update LLM Client

**File: `app/core/llm.py`**

Replace with the new version that imports both SQL and API tools:

```python
from app.tools.sql_tool import SQLTool, SchemaTool
from app.tools.api_tool import APITool, CombinedDataTool

class LLMClient:
    def __init__(self):
        self.tools = [
            SQLTool.get_tool_definition(),
            SchemaTool.get_tool_definition(),
            APITool.get_tool_definition(),
            CombinedDataTool.get_tool_definition(),
        ]
```

### Step 5: Update Your Prompts (Already Done!)

Your `get_contextual_prompt()` function in `prompts.py` already works perfectly!
The LLM will use context detection to understand what data source is needed.

---

## 🎯 How It Works

### Intelligent Tool Selection

The LLM automatically chooses the right tool:

| User Question | Tool Used | Reason |
|--------------|-----------|---------|
| "ماشین 211 کجاست؟" | **API** | Real-time location |
| "ماشین 211 دیروز چند سفر داشت؟" | **Database** | Historical data |
| "ماشین 211 کجاست و امروز چند سفر رفته؟" | **Both** | Real-time + Historical |
| "دمای یخچال ماشین X چقدر است؟" | **API** | Live sensor data |
| "میانگین دما در یخچال ماشین X از دیروز تا الان؟" | **API** | Recent sensor history |
| "کل درآمد این ماه چقدر بود؟" | **Database** | Historical analytics |

---

## Example Scenarios

### Scenario 1: Real-Time Vehicle Location

**User Question:**
```
ماشین 211 کجاست؟
```

**What Happens:**
1. LLM detects: Need real-time location
2. Tool selected: `call_backend_api`
3. API called: `GET /api/vehicles/location?vehicle_id=211`
4. Response returned in Farsi

**Response:**
```
ماشین 211 در حال حاضر در مسیر تهران-قم است.

موقعیت جغرافیایی:
• طول جغرافیایی: 51.3890
• عرض جغرافیایی: 35.6892
• سرعت فعلی: 80 کیلومتر بر ساعت
• مقصد: مرکز توزیع قم
• زمان تخمینی رسیدن: 16:30

وضعیت: در حال حرکت با سرعت ثابت
```

---

### Scenario 2: Historical Trip Analysis

**User Question:**
```
ماشین 211 هفته گذشته چند سفر داشت؟
```

**What Happens:**
1. LLM detects: Need historical data
2. Tool selected: `query_database`
3. SQL executed: `SELECT COUNT(*) FROM trips WHERE vehicle_id = '211' AND trip_date >= NOW() - INTERVAL '7 days'`
4. Response returned in Farsi

**Response:**
```
ماشین 211 در هفته گذشته 12 سفر انجام داده است.

تفکیک سفرها:
• سفرهای درون‌شهری: 8 سفر (67%)
• سفرهای برون‌شهری: 4 سفر (33%)

کل کیلومتر طی‌شده: 1,847 کیلومتر
میانگین کیلومتر هر سفر: 154 کیلومتر

مقایسه: +2 سفر نسبت به هفته قبل (+20%)
```

---

### Scenario 3: Combined Data (Database + API)

**User Question:**
```
ماشین 211 کجاست و امروز چند سفر رفته؟
```

**What Happens:**
1. LLM detects: Need BOTH real-time and historical
2. Tools selected: `call_backend_api` + `query_database`
3. API called: Current location
4. SQL executed: Today's trips
5. Combined response returned in Farsi

**Response:**
```
ماشین 211 در حال حاضر در مسیر تهران-اصفهان است (کیلومتر 180).

موقعیت فعلی:
• طول جغرافیایی: 51.2345
• عرض جغرافیایی: 35.1234
• سرعت: 75 کیلومتر بر ساعت

سفرهای امروز (3 سفر تکمیل شده):
1. تهران → قم (08:00-10:30) - 145 کیلومتر
2. قم → کاشان (11:00-13:15) - 198 کیلومتر
3. کاشان → تهران (14:00-16:20) - 215 کیلومتر

سفر فعلی (در حال انجام):
4. تهران → اصفهان (17:30-؟) - ETA: 21:00

کل کیلومتر امروز: 558 کیلومتر (+ 270 کیلومتر در مسیر)
```

---

### Scenario 4: Live Sensor Data

**User Question:**
```
دمای یخچال ماشین به پلاک 458 الان چقدر است؟
```

**What Happens:**
1. LLM detects: Need live sensor data
2. Tool selected: `call_backend_api`
3. API called: `GET /api/sensors/temperature?vehicle_id=458`
4. Response returned in Farsi

**Response:**
```
دمای فعلی یخچال ماشین 458: 3.8 درجه سانتی‌گراد

وضعیت سنسورها:
• دمای محفظه اصلی: 3.8 °C
• دمای محفظه فریزر: -18.2 °C
• رطوبت: 75%

محدوده مجاز: 2-5 °C
وضعیت: نرمال - دما در محدوده ایمن است

آخرین بروزرسانی: 2024-01-15 14:32:15
```

---

### Scenario 5: Sensor History (API with time range)

**User Question:**
```
از دیروز تا الان میانگین دمای یخچال ماشین 458 چقدر بود؟
```

**What Happens:**
1. LLM detects: Need recent sensor history
2. Tool selected: `call_backend_api`
3. API called: `GET /api/sensors/temperature?vehicle_id=458&from_time=yesterday&to_time=now`
4. Response returned in Farsi

**Response:**
```
میانگین دمای یخچال ماشین 458 از دیروز تا الان: 4.2 درجه سانتی‌گراد

آمار دما:
• میانگین: 4.2 °C
• حداکثر: 5.5 °C (ساعت 14:30 دیروز)
• حداقل: 3.2 °C (ساعت 03:00 امروز)
• نوسان: 2.3 °C

توزیع دما:
• 95% زمان: در محدوده 3-5 °C
• 5% زمان: بالاتر از 5 °C

هشدارها: 2 مورد افزایش دما > 5°C (مدت کوتاه، در حد مجاز)
وضعیت کلی: مناسب
```

---

## API Endpoint Configuration

### Backend API Structure (Example)

Your backend software should expose these endpoints:

```
Base URL: http://your-backend:8080

Vehicle Tracking:
GET  /api/vehicles/location?vehicle_id={id}
GET  /api/vehicles/status?vehicle_id={id}
GET  /api/vehicles/telemetry?vehicle_id={id}

Sensors:
GET  /api/sensors/temperature?vehicle_id={id}&from_time={iso}&to_time={iso}
GET  /api/sensors/humidity?vehicle_id={id}
GET  /api/sensors/alerts?vehicle_id={id}

Operations:
GET  /api/routes/traffic?route_id={id}
GET  /api/drivers/status?driver_id={id}
GET  /api/fuel/prices?location={coords}

Alerts:
GET  /api/alerts/active
GET  /api/alerts/critical
```

### Example API Response Format

```json
{
  "success": true,
  "data": {
    "vehicle_id": "211",
    "location": {
      "latitude": 35.6892,
      "longitude": 51.3890,
      "speed": 80,
      "heading": 270
    },
    "status": "moving",
    "timestamp": "2024-01-15T14:30:00Z"
  }
}
```

---

## 🛠️ Testing Your Setup

### Test Script

**File: `scripts/test_api_integration.py`**

```python
import requests
import json

def test_integration():
    base_url = "http://localhost:8000"

    test_cases = [
        {
            "name": "Real-time Location (API)",
            "question": "ماشین 211 کجاست؟",
            "expected_tool": "call_backend_api"
        },
        {
            "name": "Historical Trips (Database)",
            "question": "ماشین 211 هفته گذشته چند سفر داشت؟",
            "expected_tool": "query_database"
        },
        {
            "name": "Combined Data",
            "question": "ماشین 211 کجاست و امروز چند سفر رفته؟",
            "expected_tool": "both"
        },
        {
            "name": "Live Sensors (API)",
            "question": "دمای یخچال ماشین 458 الان چقدر است؟",
            "expected_tool": "call_backend_api"
        }
    ]

    print("Testing Database + API Integration\n")
    print("=" * 70)

    for i, test in enumerate(test_cases, 1):
        print(f"\n{i}. {test['name']}")
        print(f"   Question: {test['question']}")
        print(f"   Expected: {test['expected_tool']}")
        print("-" * 70)

        try:
            response = requests.post(
                f"{base_url}/api/chat",
                json={"message": test["question"]}
            )

            if response.status_code == 200:
                data = response.json()
                print(f"Answer: {data['message'][:200]}...")

                # Show which tools were called
                if data.get('tool_calls'):
                    tools_used = [tc['tool_name'] for tc in data['tool_calls']]
                    print(f"Tools Used: {', '.join(tools_used)}")
                else:
                    print(f"No tools called")
            else:
                print(f"Error {response.status_code}: {response.text[:100]}")

        except Exception as e:
            print(f"Error: {str(e)}")

    print("\n" + "=" * 70)
    print("Testing complete!")

if __name__ == "__main__":
    test_integration()
```

Run: `python scripts/test_api_integration.py`

---

## Decision Matrix: When to Use Which Tool

| Data Type | Freshness | Tool | Example |
|-----------|-----------|------|---------|
| Vehicle location | **Now** | API | کجاست؟ |
| Vehicle location | **Past** | Database | ساعت 10 کجا بود؟ |
| Sensor readings | **Now** | API | دما الان چقدر است؟ |
| Sensor readings | **Range** | API | دیروز تا الان میانگین |
| Trip count | Any | Database | چند سفر داشت؟ |
| Revenue | Any | Database | درآمد چقدر بود؟ |
| Driver status | **Now** | API | راننده کجاست؟ |
| Traffic | **Now** | API | ترافیک چطوره؟ |
| Costs | Any | Database | هزینه‌ها چقدر بود؟ |

---

## Error Handling

### API Unavailable

If your backend API is down:

```
User: ماشین 211 کجاست؟

Response:
متأسفانه در حال حاضر امکان دسترسی به سیستم ردیابی وجود ندارد.
لطفاً چند لحظه دیگر مجدداً تلاش کنید.

خطا: Cannot connect to backend API. Please check if the service is running.
```

### Database Unavailable

If database is down:

```
User: درآمد این ماه چقدر بود؟

Response:
متأسفانه در حال حاضر امکان دسترسی به پایگاه داده وجود ندارد.
لطفاً چند لحظه دیگر مجدداً تلاش کنید.
```

---

## Checklist

Setup Complete:
- [ ] Added API settings to `config.py`
- [ ] Updated `.env` with `BACKEND_API_URL` and `BACKEND_API_KEY`
- [ ] Created `app/tools/api_tool.py`
- [ ] Updated `app/core/llm.py` to include API tools
- [ ] Your `prompts.py` already has `get_contextual_prompt()`
- [ ] Tested with `scripts/test_api_integration.py`

---
