"""Test the orchestrate/matches endpoint end-to-end."""
import requests, json

# Login
r = requests.post('http://localhost:5000/auth/login', 
    json={'email':'john@test.com','password':'password123'}, timeout=10)
data = r.json()
token = data['access_token']
user_id = data['user_id']
print(f'Logged in as user {user_id}')

# Call orchestrate pipeline
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
print('Calling orchestrate/matches...')
r = requests.post('http://localhost:5000/orchestrate/matches', 
    json={'min_score': 40}, headers=headers, timeout=600)
print(f'STATUS: {r.status_code}')

data = r.json()
if 'error' in data:
    print(f'ERROR: {data["error"]}')
else:
    print(f'Success: {data.get("success")}')
    print(f'Recommendations: {data.get("count")}')
    metrics = data.get('metrics', {})
    print(f'Scores computed: {metrics.get("scores_computed")}')
    print(f'Pipeline duration: {metrics.get("pipeline_duration_ms")}ms')
    
    recs = data.get('recommendations', [])
    for rec in recs[:5]:
        exp = rec.get('explanation', {})
        if isinstance(exp, str):
            try:
                exp = json.loads(exp)
            except:
                pass
        breakdown = exp.get('score_breakdown', {}) if isinstance(exp, dict) else {}
        print(f'  {rec.get("user_name","?")} score={rec.get("score")} '
              f'lifestyle={breakdown.get("lifestyle_score","?")} '
              f'schedule={breakdown.get("schedule_score","?")} '
              f'budget={breakdown.get("budget_score","?")}')

# Also test recommendations endpoint
print(f'\nTesting GET /recommendations/user/{user_id}...')
r = requests.get(f'http://localhost:5000/recommendations/user/{user_id}?min_score=40', 
    headers=headers, timeout=30)
data = r.json()
print(f'STATUS: {r.status_code}')
print(f'Recommendations from DB: {data.get("total")}')
if data.get('recommendations'):
    rec = data['recommendations'][0]
    print(f'  First: match_id={rec.get("match_id")} score={rec.get("match_score")}')
    exp = rec.get('explanation', '{}')
    if isinstance(exp, str):
        try:
            exp = json.loads(exp)
        except:
            exp = {}
    breakdown = exp.get('score_breakdown', {}) if isinstance(exp, dict) else {}
    print(f'  Breakdown: lifestyle={breakdown.get("lifestyle_score","?")} '
          f'schedule={breakdown.get("schedule_score","?")} '
          f'budget={breakdown.get("budget_score","?")}')
