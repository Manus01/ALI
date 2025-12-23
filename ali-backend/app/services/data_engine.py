import json
import datetime
import requests
import logging
from google.cloud import firestore

# SDK Imports
try:
    from facebook_business.api import FacebookAdsApi
    from facebook_business.adobjects.adaccount import AdAccount
except ImportError:
    FacebookAdsApi = None

try:
    from google.ads.googleads.client import GoogleAdsClient
except ImportError:
    GoogleAdsClient = None

logger = logging.getLogger(__name__)

class DataEngine:
    def __init__(self, user_id):
        self.db = firestore.Client()
        self.user_id = user_id

    def save_metrics(self, platform, metrics):
        """
        Standardizes and saves metrics to Firestore 'campaign_performance'
        """
        if not metrics:
            print(f"⚠️ No data found for {platform}")
            return

        batch = self.db.batch()
        collection_ref = self.db.collection('users').document(self.user_id).collection('campaign_performance')

        for item in metrics:
            doc_id = f"{platform}_{item['date']}_{item.get('campaign_id', 'unknown')}"
            doc_ref = collection_ref.document(doc_id)
            
            item['platform'] = platform
            item['ingested_at'] = firestore.SERVER_TIMESTAMP
            
            batch.set(doc_ref, item, merge=True)

        batch.commit()
        print(f"✅ Saved {len(metrics)} {platform} records to Firestore.")

    # --- 1. LINKEDIN ADS (REST API) ---
    def fetch_linkedin(self, credentials_json, dry_run=False):
        """
        Verifies keys and fetches data.
        dry_run=True: Tests connection only, saves nothing.
        """
        print(f"🔄 {'Testing' if dry_run else 'Fetching'} LinkedIn Data...")
        creds = json.loads(credentials_json)
        token = creds.get("access_token")
        account = creds.get("ad_account_id") 

        headers = {"Authorization": f"Bearer {token}", "X-Restli-Protocol-Version": "2.0.0"}
        
        # For Dry Run, just check 1 day to be fast
        days_back = 1 if dry_run else 30
        end = datetime.date.today()
        start = end - datetime.timedelta(days=days_back)
        
        url = "https://api.linkedin.com/rest/adAnalyticsV2"
        params = {
            "q": "analytics",
            "pivot": "CAMPAIGN",
            "dateRange.start.day": start.day,
            "dateRange.start.month": start.month,
            "dateRange.start.year": start.year,
            "dateRange.end.day": end.day,
            "dateRange.end.month": end.month,
            "dateRange.end.year": end.year,
            "timeGranularity": "DAILY",
            "accounts[0]": account
        }

        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            error_msg = f"LinkedIn Error {response.status_code}: {response.text}"
            print(f"❌ {error_msg}")
            raise ValueError(error_msg) # Raise so Router knows it failed

        if dry_run:
            print("✅ LinkedIn Connection Verified.")
            return True

        # Process Data (Only if not dry_run)
        data = response.json().get("elements", [])
        clean_data = []
        
        for row in data:
            clean_data.append({
                "date": f"{row['dateRange']['start']['year']}-{row['dateRange']['start']['month']:02d}-{row['dateRange']['start']['day']:02d}",
                "campaign_name": "LinkedIn Campaign", 
                "campaign_id": row['pivotValue'],
                "impressions": row.get('impressions', 0),
                "clicks": row.get('clicks', 0),
                "spend": float(row.get('costInLocalCurrency', 0)),
                "conversions": row.get('externalWebsiteConversions', 0),
                "cpc": 0, 
                "roas": 0
            })
            
        self.save_metrics("linkedin", clean_data)

    # --- 2. META ADS (Facebook SDK) ---
    def fetch_meta(self, credentials_json, dry_run=False):
        """
        dry_run=True: Tests connection only.
        """
        print(f"🔄 {'Testing' if dry_run else 'Fetching'} Meta Ads Data...")
        if not FacebookAdsApi:
            raise ImportError("Facebook SDK not installed.")

        try:
            creds = json.loads(credentials_json)
            access_token = creds.get("access_token")
            ad_account_id = creds.get("ad_account_id")

            FacebookAdsApi.init(access_token=access_token)
            account = AdAccount(ad_account_id)
            
            # Lightweight call for verification
            if dry_run:
                account.api_get(fields=['name', 'account_status'])
                print("✅ Meta Connection Verified.")
                return True

            # Full Ingestion
            fields = ['campaign_name', 'campaign_id', 'impressions', 'clicks', 'spend', 'actions']
            params = {
                'level': 'campaign',
                'date_preset': 'last_30d',
                'time_increment': 1
            }
            insights = account.get_insights(fields=fields, params=params)
            
            clean_data = []
            for i in insights:
                spend = float(i.get('spend', 0))
                clicks = int(i.get('clicks', 0))
                
                clean_data.append({
                    "date": i['date_start'],
                    "campaign_name": i['campaign_name'],
                    "campaign_id": i['campaign_id'],
                    "impressions": int(i.get('impressions', 0)),
                    "clicks": clicks,
                    "spend": spend,
                    "conversions": 0,
                    "cpc": round(spend / clicks, 2) if clicks > 0 else 0
                })
            
            self.save_metrics("meta", clean_data)

        except Exception as e:
            print(f"❌ Meta Error: {e}")
            raise ValueError(f"Meta Auth Failed: {str(e)}")

    # --- 3. GOOGLE ADS (Google SDK) ---
    def fetch_google_ads(self, credentials_json, dry_run=False):
        """
        dry_run=True: Tests connection only.
        """
        print(f"🔄 {'Testing' if dry_run else 'Fetching'} Google Ads Data...")
        if not GoogleAdsClient:
            raise ImportError("Google Ads SDK not installed.")

        try:
            creds = json.loads(credentials_json)
            customer_id = creds.pop("customer_id")
            
            client = GoogleAdsClient.load_from_dict(creds)
            ga_service = client.get_service("GoogleAdsService")

            # Fast query for verification
            query = """
                SELECT campaign.id 
                FROM campaign 
                LIMIT 1
            """
            
            if not dry_run:
                query = """
                    SELECT 
                      segments.date,
                      campaign.id, 
                      campaign.name, 
                      metrics.impressions, 
                      metrics.clicks, 
                      metrics.cost_micros,
                      metrics.conversions
                    FROM campaign 
                    WHERE segments.date DURING LAST_30_DAYS
                """

            # This line will throw exception if auth is bad
            stream = ga_service.search_stream(customer_id=customer_id, query=query)
            
            # Consume one element to ensure stream works
            for batch in stream:
                break 

            if dry_run:
                print("✅ Google Ads Connection Verified.")
                return True

            # Process Full Data
            clean_data = []
            # We need to re-run or iterate fully if we broke out above, 
            # but since dry_run branches logic, we re-run stream for full data:
            stream = ga_service.search_stream(customer_id=customer_id, query=query)
            
            for batch in stream:
                for row in batch.results:
                    spend = row.metrics.cost_micros / 1_000_000
                    clicks = row.metrics.clicks
                    
                    clean_data.append({
                        "date": row.segments.date,
                        "campaign_name": row.campaign.name,
                        "campaign_id": str(row.campaign.id),
                        "impressions": row.metrics.impressions,
                        "clicks": clicks,
                        "spend": round(spend, 2),
                        "conversions": row.metrics.conversions,
                        "cpc": round(spend / clicks, 2) if clicks > 0 else 0
                    })
            
            self.save_metrics("google", clean_data)

        except Exception as e:
            print(f"❌ Google Ads Error: {e}")
            raise ValueError(f"Google Auth Failed: {str(e)}")