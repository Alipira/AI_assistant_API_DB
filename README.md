# AI Data Chatbot 🤖

A chatbot that answers questions about your PostgreSQL database using OpenAI GPT models with function calling.

## Features

-  Natural language queries to your database
-  Automatic SQL generation with safety checks
-  Schema introspection
-  Tool calling (function calling) for reliable data access
-  FastAPI backend with async support
-  Built-in security (SQL injection prevention, query validation)

## Architecture

```
User Question → FastAPI → OpenAI GPT → Tool Calls → PostgreSQL
                   ↑                         ↓
                   └────── Results ──────────┘
```

## Quick Start

### 1. Prerequisites

- Python 3.9+
- PostgreSQL database
- OpenAI API key

### 2. Installation

```bash
# Clone/create project
mkdir ai-data-chatbot
cd ai-data-chatbot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

Create `.env` file:

```bash
DATABASE_URL=postgresql://username:password@localhost:5432/your_database
OPENAI_API_KEY=sk-your-openai-api-key-here
ENVIRONMENT=development
```

### 4. Setup Database

Run the sample database script:

```bash
psql -U your_username -d your_database -f scripts/init_db.sql
```

This creates sample tables: `users`, `products`, `orders`

### 5. Run the Application

```bash
# Start the server
python app/main.py

# Or use uvicorn directly
uvicorn app.main:app --reload
```

The API will be available at: `http://localhost:8000`

### 6. Test It

**Option A: Interactive API Docs**
- Open: http://localhost:8000/docs
- Try the `/api/chat` endpoint

**Option B: Test Script**
```bash
python scripts/test_chatbot.py
```

**Option C: cURL**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How many users are in the database?"}'
```

## Example Questions

Try asking your chatbot:

- "How many users do we have?"
- "What are the top 5 products by price?"
- "Show me all completed orders"
- "What's the total revenue from orders?"
- "Which users haven't placed any orders?"
- "What's the average order value?"

## API Endpoints

### POST `/api/chat`

Send a message to the chatbot.

**Request:**
```json
{
  "message": "How many users are active?",
  "conversation_id": "optional-conv-id"
}
```

**Response:**
```json
{
  "message": "There are 4 active users in the database.",
  "conversation_id": "conv_123",
  "tool_calls": [
    {
      "tool_name": "query_database",
      "arguments": {
        "query": "SELECT COUNT(*) FROM users WHERE is_active = true"
      },
      "result": {
        "success": true,
        "rows": [{"count": 4}]
      }
    }
  ]
}
```

### GET `/health`

Check API health.

## Security Features

### Built-in SQL Safety

-  Only SELECT queries allowed
-  Blocks: DROP, DELETE, INSERT, UPDATE, ALTER, etc.
-  Prevents multiple statements (semicolon check)
-  Automatic row limits (configurable)
-  Query validation before execution

### Configuration

Edit `app/config.py`:

```python
max_query_rows: int = 1000        # Max rows per query
allowed_schemas: list = ["public"] # Allowed schemas
```

## Project Structure

```
ai-data-chatbot/
├── app/
│   ├── main.py                   # FastAPI entry point
│   ├── config/
│   │   └── config.py             # Configuration
│   ├── api/
│   │   ├── chat.py               # Chat endpoint
│   │   └── health.py             # Health check
│   ├── core/
│   │   ├── date_utils.py         # Resolves any date/time expression
│   │   ├── prompts.py
│   │   ├── logging_config.py     # Logging config to handle logs on consol,and ElasticSearch
│   │   ├── depricate_prompts.py  # Depricated prompts for usign sql tools
│   │   └── llm.py                # OpenAI client + tool calling
│   ├── tools/
│   │   └── sql_tool.py           # Database query tools
│   ├── db/
│   │   └── session.py            # Database connection
│   └── schemas/
│       └── chat.py               # Pydantic models
├── scripts/
│   ├── init_db.sql               # Sample database
│   └── test_chatbot.py           # Test script
├── .env                          # Environment variables
└── requirements.txt
```

## How It Works

1. **User sends a question** via `/api/chat`
2. **LLM analyzes the question** and decides if it needs database access
3. **Tool calls are made**:
   - `get_schema` - Get table/column information
   - `query_database` - Execute SQL queries
4. **Results are processed** by the LLM
5. **Natural language response** is returned to the user

## Next Steps

### Add More Tools

Create new tools in `app/tools/`:

```python
# app/tools/analytics_tool.py
class AnalyticsTool:
    @staticmethod
    def get_tool_definition():
        return {
            "type": "function",
            "function": {
                "name": "calculate_metrics",
                "description": "Calculate business metrics",
                # ...
            }
        }
```

Register in `app/core/llm.py`:
```python
from app.tools.analytics_tool import AnalyticsTool

self.tools = [
    SQLTool.get_tool_definition(),
    SchemaTool.get_tool_definition(),
    AnalyticsTool.get_tool_definition(),  # Add here
]
```

### Add Authentication

```python
# app/api/chat.py
from fastapi import Header, HTTPException

async def verify_token(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid token")
    # Verify token logic here
```

### Add Conversation Memory

Store conversation history in PostgreSQL or Redis for context.

### Add Rate Limiting

```bash
pip install slowapi

# In main.py
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@limiter.limit("20/minute")
async def chat(...):
    ...
```

## Troubleshooting

**Database connection error:**
```bash
# Check PostgreSQL is running
pg_isready

# Test connection
psql -U your_username -d your_database -c "SELECT 1;"
```

**OpenAI API error:**
```bash
# Verify API key
echo $OPENAI_API_KEY

# Test with curl
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

**Import errors:**
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## Production Checklist

- [ ] Change CORS settings in `main.py`
- [ ] Add authentication
- [ ] Add rate limiting
- [ ] Set up monitoring/logging
- [ ] Use environment-specific configs
- [ ] Add database connection pooling
- [ ] Set up HTTPS
- [ ] Review SQL security settings
- [ ] Add request validation
- [ ] Set up error tracking (Sentry, etc.)

## License

MIT

## Support

For issues or questions, please open an issue on GitHub.

---

**Happy chatting with your data!**
