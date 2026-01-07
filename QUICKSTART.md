# 🚀 Quick Start Guide - AI Data Chatbot

Follow these steps to get your chatbot running in 10 minutes!

## Step 1: Setup Environment (2 min)

```bash
cd ai-data-chatbot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Configure (1 min)

Create `.env` file in the project root:

```
DATABASE_URL=postgresql://your_user:your_password@localhost:5432/your_db
OPENAI_API_KEY=sk-your-openai-api-key
ENVIRONMENT=development
```

**Don't have a database yet?** 
- Install PostgreSQL: https://www.postgresql.org/download/
- Or use a free cloud database: https://neon.tech or https://supabase.com

## Step 3: Setup Database (2 min)

```bash
# Connect to your PostgreSQL database
psql -U your_username -d your_database

# Run the init script
\i scripts/init_db.sql

# Or from command line:
psql -U your_username -d your_database -f scripts/init_db.sql
```

This creates sample tables with test data.

## Step 4: Run the Server (1 min)

```bash
python app/main.py
```

You should see:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Step 5: Test It! (5 min)

### Option A: Web Interface
1. Open: http://localhost:8000/docs
2. Click on `/api/chat` → "Try it out"
3. Enter: `{"message": "How many users are in the database?"}`
4. Click "Execute"

### Option B: Test Script
```bash
# In a new terminal
python scripts/test_chatbot.py
```

### Option C: cURL
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the top 3 most expensive products?"}'
```

## Example Questions to Try

```
"How many users do we have?"
"Show me all products in the Electronics category"
"What's the total revenue from completed orders?"
"Which user has placed the most orders?"
"What's the average product price?"
```

## What's Next?

1. **Connect your real database** - Update `DATABASE_URL` in `.env`
2. **Customize the system prompt** - Edit `app/core/llm.py`
3. **Add security** - See README.md for authentication examples
4. **Add more tools** - Create new tools in `app/tools/`

## Troubleshooting

**Problem: "Connection refused" error**
```bash
# Make sure PostgreSQL is running
pg_isready
# Or: sudo service postgresql start
```

**Problem: "OpenAI API error"**
```bash
# Check your API key
echo $OPENAI_API_KEY
# Make sure it starts with sk-
```

**Problem: "Module not found"**
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## Project Structure

```
ai-data-chatbot/
├── app/
│   ├── main.py          ← Start here
│   ├── core/llm.py      ← OpenAI integration
│   ├── tools/           ← Database tools
│   └── api/chat.py      ← Chat endpoint
├── scripts/
│   ├── init_db.sql      ← Sample database
│   └── test_chatbot.py  ← Test script
└── .env                 ← Your config
```

## Need Help?

- Read the full README.md
- Check the example code in each file
- API docs: http://localhost:8000/docs

Happy building! 🎉
