import os
import json
import time
import random
from datetime import datetime, timedelta
from curl_cffi import requests

# Configure base file system paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORICAL_DIR = os.path.join(BASE_DIR, "data", "historical")
UPCOMING_DIR = os.path.join(BASE_DIR, "data", "upcoming")

# Ensure storage directories exist safely
os.makedirs(HISTORICAL_DIR, exist_ok=True)
os.makedirs(UPCOMING_DIR, exist_ok=True)

def fetch_sofascore_day(target_date: str, sport: str = "football"):
    """
    Connects to SofaScore's backend API gateway using TLS impersonation
    and wraps the request inside the ScrapeOps proxy gateway to bypass data center blocks.
    """
    # Securely integrated active api key
    SCRAPEOPS_API_KEY = "958b2c50-6f47-4529-97f6-e28fcc210663"
    
    # Construct clean target URL destination
    target_url = f"https://sofascore.com{sport}/scheduled-events/{target_date}/inverse"
    
    # Reroute request through ScrapeOps residential proxy engine gateway
    proxy_gateway_url = "https://scrapeops.io"
    
    params = {
        "api_key": SCRAPEOPS_API_KEY,
        "url": target_url,
        "bypass": "cloudflare"  # Enforces aggressive Cloudflare header/cookie manipulation
    }
    
    print(f"[*] Tunneling request through ScrapeOps proxy gateway for date: {target_date}")
    
    try:
        # Keep using curl_cffi for proxy target delivery validation
        response = requests.get(proxy_gateway_url, params=params, impersonate="chrome120", timeout=30)
        
        if response.status_code == 200:
            return response.json().get("events", [])
        elif response.status_code == 403:
            print(f"[-] Proxy Gateway was blocked by Cloudflare (403) for date: {target_date}.")
            return []
        else:
            print(f"[-] Request failed via gateway. Status: {response.status_code}")
            return []
    except Exception as e:
        print(f"[-] Proxy routing layer failure: {e}")
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
                
            # Time normalization
            start_ts = event.get("startTimestamp")
            utc_time = datetime.fromtimestamp(start_ts).strftime('%Y-%m-%d %H:%M:%S') if start_ts else None
            
            # Formulate the feature payload
            match_payload = {
                "match_id": str(event.get("id")),
                "date_utc": utc_time.split(" ")[0] if utc_time else None,
                "time_utc": utc_time.split(" ")[1] if utc_time else None,
                "sport": event.get("sport", {}).get("name"),
                "tournament_id": event.get("tournament", {}).get("id"),
                "tournament_name": event.get("tournament", {}).get("name"),
                "category_country": event.get("tournament", {}).get("category", {}).get("name"),
                
                # Team Features
                "home_team_id": event.get("homeTeam", {}).get("id"),
                "home_team_name": event.get("homeTeam", {}).get("name"),
                "away_team_id": event.get("awayTeam", {}).get("id"),
                "away_team_name": event.get("awayTeam", {}).get("name"),
                
                # Match Context & Status
                "status_type": event.get("status", {}).get("type"),  # finished, notstarted, inprogress
                "status_description": event.get("status", {}).get("description"),
                
                # Ground Truth Data (Only populates if historical/finished)
                "home_score_current": event.get("homeScore", {}).get("current"),
                "away_score_current": event.get("awayScore", {}).get("current"),
                "home_score_period1": event.get("homeScore", {}).get("period1"),
                "away_score_period1": event.get("awayScore", {}).get("period1"),
                
                # Target Verification Flags
                "winner_code": event.get("winnerCode")  # 1 = Home, 2 = Away, 3 = Draw
            }
            
            cleaned_fixtures.append(match_payload)
            
        except Exception as err:
            continue
            
    return cleaned_fixtures

def pipeline_runner():
    today = datetime.now().date()
    
    # 1. BULK HISTORICAL SCRAPING (Collect past 3 days)
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
            
        # Throttling helps optimize API credit allocation pacing
        time.sleep(random.uniform(2.5, 4.5))

    # 2. UPCOMING MATCHES FOR PREDICTIONS (Today and Tomorrow)
    print("\n--- Starting Predictive Future Scrape Component ---")
    for i in range(0, 2):  # 0 = Today, 1 = Tomorrow
        target_date = (today + timedelta(days=i)).isoformat()
        raw_data = fetch_sofascore_day(target_date)
        
        if raw_data:
            clean_data = extract_clean_metadata(raw_data)
            output_file = os.path.join(UPCOMING_DIR, f"{target_date}.json")
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(clean_data, f, indent=2)
            print(f"[+] Saved {len(clean_data)} prospective fixtures to {output_file}")
            
        time.sleep(random.uniform(2.5, 4.5))

if __name__ == "__main__":
    start_time = time.time()
    pipeline_runner()
    print(f"\n[+] Pipeline Run Finished Successfully in {round(time.time() - start_time, 2)}s.")
