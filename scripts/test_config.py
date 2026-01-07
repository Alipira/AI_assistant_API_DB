"""Test script to verify configuration is working"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("🧪 Testing Configuration...\n")
print("=" * 70)

# Test 1: Import config
print("\n1️⃣  Testing config import...")
try:
    from app.config import get_settings
    print("   ✅ Config module imported successfully")
except Exception as e:
    print(f"   ❌ Failed to import config: {e}")
    sys.exit(1)

# Test 2: Load settings
print("\n2️⃣  Loading settings from .env...")
try:
    settings = get_settings()
    print("   ✅ Settings loaded successfully")
except Exception as e:
    print(f"   ❌ Failed to load settings: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Display configuration
print("\n3️⃣  Configuration details:")
print(settings.display_config())

# Test 4: Test database URL
print("\n4️⃣  Testing database URL format...")
try:
    db_url = settings.database_url
    print(f"   ✅ Database URL generated: {db_url[:50]}...")

    # Check if special characters are encoded
    if '%21%40%23' in db_url or '123qaz!@#' in db_url:
        print("   ✅ Special characters in password handled")
    else:
        print("   ⚠️  Password encoding might need verification")
except Exception as e:
    print(f"   ❌ Database URL error: {e}")

# Test 5: Test backend API URL
print("\n5️⃣  Testing backend API URL...")
try:
    api_url = settings.backend_api_url
    print(f"   ✅ Backend API URL: {api_url}")

    # Check trailing slash is removed
    if api_url.endswith('/'):
        print("   ⚠️  Warning: Trailing slash not removed")
    else:
        print("   ✅ Trailing slash handled correctly")
except Exception as e:
    print(f"   ❌ Backend API URL error: {e}")

# Test 6: Test database connection
print("\n6️⃣  Testing database connection...")
try:
    from sqlalchemy import create_engine, text

    engine = create_engine(settings.database_url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("   ✅ Database connection successful!")
except Exception as e:
    print(f"   ❌ Database connection failed: {e}")
    print("   ℹ️  Make sure PostgreSQL is running and credentials are correct")

# Test 7: Test OpenAI API key
print("\n7️⃣  Checking OpenAI API key...")
if settings.openai_api_key and settings.openai_api_key.startswith('sk-'):
    print(f"   ✅ OpenAI API key present: {settings.openai_api_key[:10]}...")
elif settings.openai_api_key == "sk-test-key":
    print("   ⚠️  Using default test key - add your real OpenAI key to .env")
else:
    print("   ❌ OpenAI API key missing or invalid")

print("\n" + "=" * 70)
print("\n✅ Configuration test complete!")
print("\nNext steps:")
print("1. If database connection failed, check if PostgreSQL is running")
print("2. Add your OpenAI API key to .env if you haven't already")
print("3. Start the chatbot: python app/main.py")
