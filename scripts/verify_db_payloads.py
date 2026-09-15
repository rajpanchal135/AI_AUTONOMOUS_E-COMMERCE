import requests
import json
import sqlite3

def run_test_and_verify_db():
    print("1. Calling POST /api/v1/simulation/test-6-agents ...")
    res = requests.post("http://localhost:8001/api/v1/simulation/test-6-agents")
    print(f"API Response HTTP Status: {res.status_code}")
    
    if res.status_code == 200:
        data = res.json()
        print(f"Database Persisted Flag: {data.get('database_persisted')}")
        print(f"Total Agents Tested: {data.get('total_agents_tested')}")
        
    print("\n2. Querying SQLite Database (ecom_ai.db) -> agent_runs table...")
    conn = sqlite3.connect("ecom_ai.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, agent_name, model_id, status, started_at, result
        FROM agent_runs
        ORDER BY started_at DESC
        LIMIT 6
    """)
    rows = cursor.fetchall()
    
    print(f"\nRetrieved {len(rows)} latest agent_runs from Database:\n")
    for row in rows:
        run_id, agent_name, model_id, status, started_at, result_raw = row
        res_dict = json.loads(result_raw) if result_raw else {}
        
        prompt = res_dict.get("gemini_prompt", "")
        response = res_dict.get("gemini_response", "")
        model = res_dict.get("gemini_model", model_id)
        event_payload = res_dict.get("event_payload", {})
        
        print("=" * 80)
        print(f"AGENT: {agent_name.upper()} | Model: {model} | Status: {status}")
        print(f"Started At: {started_at}")
        print(f"Event Payload: {json.dumps(event_payload)[:100]}...")
        print(f"\n[GEMINI PROMPT STORED IN DB]:\n{prompt[:180]}...")
        print(f"\n[GEMINI AI RESPONSE STORED IN DB]:\n{response[:180]}...")
        print("=" * 80 + "\n")

if __name__ == "__main__":
    run_test_and_verify_db()
