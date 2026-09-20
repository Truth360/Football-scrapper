import os
import json
import time
import random
from datetime import datetime, timedelta
from curl_cffi import requests 

### Configure base file system paths

BASE_DIR = os.path.dirname(os.path.abspath(**file**))
DATA_DIR = os.path.join(BASE_DIR, "data")
HISTORICAL_DIR = os.path.join(DATA_DIR, "historical")
UPCOMING_DIR = os.path.join(DATA_DIR, "upcoming") 

### Ensure storage directories exist safely

os.makedirs(HISTORICAL_DIR, exist_ok=True)
os.makedirs(UPCOMING_DIR, exist_ok=True) 

def fetch_sofascore_day(target_date: str, sport: str = "football"):
"""
Queries SofaScore's internal JSON API by tunneling requests through
the ScrapeOps proxy gateway with precise header forwarding.
"""
SCRAPEOPS_API_KEY = "958b2c50-6f47-4529-97f6-e28fcc210663" 

### FIX: Point directly to the internal JSON API endpoint instead of the web UI

target_url = f"https://api.sofascore.com/api/v1/sport/{sport}/scheduled-events/{target_date}"
proxy_gateway_url = "https://proxy.scrapeops.io/v1/" 

### Configure parameters for ScrapeOps to optimize anti-bot mitigation

params = {
"api_key": SCRAPEOPS_API_KEY,
"url": target_url,
"bypass": "cloudflare",
"forward_headers": "true"
} 

### Hardcoded context headers to mirror legitimate client state

headers = {
"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
"Accept": "*/*",
"Accept-Language": "en-US,en;q=0.9",
"Origin": "https://www.sofascore.com",
"Referer": "https://www.sofascore.com/",
"Cache-Control": "no-cache"
} 

print(f"[*] Tunneling request through ScrapeOps proxy gateway for date: {target_date}") 

try: 

### Use curl_cffi for native HTTP/2 + TLS Fingerprint mimicry

response = requests.get(
proxy_gateway_url,
params=params,
headers=headers,
impersonate="chrome120",
timeout=30
) 

if response.status_code == 200: 

### ScrapeOps returns the actual target page content inside its response string

    # If JSON optimization is on, we can safely parse the response text directly
    json_payload = response.json()
    return json_payload.get("events", [])
    
elif response.status_code in:
    print(f"[-] Proxy Gateway rejected by anti-bot layer ({response.status_code}) for date: {target_date}.")
    return []
else:
    print(f"[-] Request failed via gateway. Status: {response.status_code}")
    return []

except Exception as e:
print(f"[-] Proxy routing layer failure or JSON mismatch: {e}")
return []

def extract_clean_metadata(raw_events):
"""
Normalizes deeply nested UI objects into raw engineering values
suitable for feature engineering and predictive analysis pipelines.
"""
cleaned_fixtures = [] 

for event in raw_events:
try:
if not event.get("id"):
continue
    start_ts = event.get("startTimestamp")
    utc_time = datetime.fromtimestamp(start_ts).strftime('%Y-%m-%d %H:%M:%S') if start_ts else None
    
    match_payload = {
        "match_id": str(event.get("id")),
        "date_utc": utc_time.split(" ")[0] if utc_time else None,
        "time_utc": utc_time.split(" ")[1] if utc_time else None,
        "sport": event.get("sport", {}).get("name"),
        "tournament_id": event.get("tournament", {}).get("id"),
        "tournament_name": event.get("tournament", {}).get("name"),
        "category_country": event.get("tournament", {}).get("category", {}).get("name"),
        
        "home_team_id": event.get("homeTeam", {}).get("id"),
        "home_team_name": event.get("homeTeam", {}).get("name"),
        "away_team_id": event.get("awayTeam", {}).get("id"),
        "away_team_name": event.get("awayTeam", {}).get("name"),
        
        "status_type": event.get("status", {}).get("type"), 
        "status_description": event.get("status", {}).get("description"),
        
        "home_score_current": event.get("homeScore", {}).get("current"),
        "away_score_current": event.get("awayScore", {}).get("current"),
        "home_score_period1": event.get("homeScore", {}).get("period1"),
        "away_score_period1": event.get("awayScore", {}).get("period1"),
        
        "winner_code": event.get("winnerCode") 
    }
    
    cleaned_fixtures.append(match_payload)
    
except Exception:
    continue

return cleaned_fixtures

def pipeline_runner():
today = datetime.now().date() 

### 1. BULK HISTORICAL SCRAPING (Collect past 3 days)

print("\n--- Starting Historical Scrape Component ---")
for i in range(1, 4):
target_date = (today - timedelta(days=i)).isoformat()
raw_data = fetch_sofascore_day(target_date) 

if raw_data:
clean_data = extract_clean_metadata(raw_data)
output_file = os.path.join(HISTORICAL_DIR, f"{target_date}.json")
with open(output_file, "w", encoding="utf-8") as f:
json.dump(clean_data, f, indent=2)
print(f"[+] Saved {len(clean_data)} historical entries to {output_file}")

time.sleep(random.uniform(4.0, 7.0))

# 2. UPCOMING MATCHES FOR PREDICTIONS (Today and Tomorrow)

print("\n--- Starting Predictive Future Scrape Component ---")
for i in range(0, 2):
target_date = (today + timedelta(days=i)).isoformat()
raw_data = fetch_sofascore_day(target_date)
if raw_data:
    clean_data = extract_clean_metadata(raw_data)
    output_file = os.path.join(UPCOMING_DIR, f"{target_date}.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(clean_data, f, indent=2)
    print(f"[+] Saved {len(clean_data)} prospective fixtures to {output_file}")
    
time.sleep(random.uniform(4.0, 7.0))

if **name** == "**main**":
start_time = time.time()
pipeline_runner()
print(f"\n[+] Pipeline Run Finished Successfully in {round(time.time() - start_time, 2)}s.")
