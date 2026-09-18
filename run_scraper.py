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
    to scrape the complete global inverse catalog for a target date.
    """
    api_url = f"https://sofascore.com{sport}/scheduled-events/{target_date}/inverse"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://sofascore.com",
        "Origin": "https://sofascore.com",
    }
    
    print(f"[*] Querying API for: {target_date}")
    
    try:
        # Impersonating Chrome 120+ to force valid modern TLS handshake fingerprinting
        response = requests.get(api_url, headers=headers, impersonate="chrome120", timeout=15)
        
        if response.status_code == 200:
            return response.json().get("events", [])
        elif response.status_code == 404:
            print(f"[-] No events found or endpoint changed for date: {target_date}")
            return []
        else:
            print(f"[-] API rejected request. HTTP Status: {response.status_code}")
            return []
    except Exception as e:
        print(f"[-] Network connection failed: {e}")
        return []

def extract_clean_metadata(raw_events):
    """
    Normalizes deeply nested UI objects into raw engineering values
    suitable for feature engineering and predictive analysis pipelines.
    """
    cleaned_fixtures = []
    
    for event in raw_events:
        try:
            # Drop low-tier matches without odds or structural tracking parameters
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
            # Gracefully bypass unexpected structural shifts in individual events
            continue
            
    return cleaned_fixtures

def pipeline_runner():
    today = datetime.now().date()
    
    # 1. BULK HISTORICAL SCRAPING (Collect past 3 days to catch up/update results)
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
            
        # Polite throttling inside GitHub runner environments
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
