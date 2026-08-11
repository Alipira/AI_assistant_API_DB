"""Test script for CHATBOT (not the backend)"""
import requests
import json


def test_chatbot(
    chatbot_url: str = "http://localhost:8000",  # CHATBOT
    backend_url: str = "https://your_url.com"    # backend API
):
    """Test the chatbot with sample queries"""

    print("🤖 AI Data Chatbot Test Suite\n")
    print("=" * 60)
    print(f"Chatbot URL: {chatbot_url}")
    print(f"Backend URL: {backend_url}")
    print("=" * 60)

    # Test 1: Chatbot Health check
    print("\n1. Testing CHATBOT health endpoint...")
    try:
        response = requests.get(f"{chatbot_url}/health", timeout=5)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            try:
                print(f"Response: {json.dumps(response.json(), indent=2)}")
            except Exception as e:
                print(f"Response: {response.text[:200]} and could not parse JSON: {e}")
        else:
            print(f"❌ Chatbot is not responding properly")
            print("Make sure chatbot is running: python app/main.py")
            return

    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to chatbot at {chatbot_url}")
        print("Is chatbot running? Start it with: python app/main.py")
        return
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # Test 2: Backend API check (optional)
    print("\n2. Testing BACKEND API accessibility...")
    try:
        # Try to ping backend (just check if it's reachable)
        response = requests.get(backend_url, timeout=5)
        print(f"Backend Status: {response.status_code}")
        print("✅ Backend API is reachable")
    except Exception as e:
        print(f"⚠️ Backend API not reachable: {e}")
        print("(This is okay if you're only testing database queries)")

    # Test questions
    questions = [
        "لیست متحرک ها را بر اساس نوع متحرک یا ماشین بده",
        "ماشین با پلاک 94 ع 436 کجاست؟",  # Will try to call backend API
        "چند تا ماشین داریم؟",  # Will query database
    ]

    print("\n" + "=" * 60)
    print("Testing chat queries...\n")

    for i, question in enumerate(questions, 1):
        print(f"\n{i}. Question: {question}")
        print("-" * 60)

        try:
            response = requests.post(
                f"{chatbot_url}/api/chat",  # ← CHATBOT endpoint
                json={"message": question},
                headers={"Content-Type": "application/json"},
                timeout=30  # Give it time to process
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Answer: {data['message']}\n")

                # Show tool calls if any
                if data.get('tool_calls'):
                    print("🔧 Tool Calls:")
                    for tool_call in data['tool_calls']:
                        print(f"   - {tool_call['tool_name']}")
                        if tool_call['tool_name'] == 'query_database':
                            query = tool_call['arguments'].get('query', '')
                            print(f"     Query: {query[:100]}...")
                        elif tool_call['tool_name'] == 'call_backend_api':
                            endpoint = tool_call['arguments'].get('endpoint', '')
                            print(f"     Endpoint: {endpoint}")
            else:
                print(f"❌ Error {response.status_code}: {response.text[:200]}")

        except requests.exceptions.Timeout:
            print("❌ Request timed out (took >30 seconds)")
        except requests.exceptions.JSONDecodeError:
            print(f"❌ Response is not JSON: {response.text[:200]}")
        except Exception as e:
            print(f"❌ Error: {e}")

    print("\n" + "=" * 60)
    print("✅ Testing complete!")


if __name__ == "__main__":
    # Run the test
    test_chatbot()
