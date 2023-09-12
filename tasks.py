from celery import Celery
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# Initialize Celery
celery = Celery('tasks', broker='redis:https://pardotdashboard-7fc843d1f87a.herokuapp.com/')

@celery.task
def fetch_prospects_from_opportunities(access_token):
    try:
        # Calculate the date 6 months ago
        six_months_ago = datetime.now() - timedelta(days=180)
        six_months_ago_str = six_months_ago.strftime('%Y-%m-%d %H:%M:%S')

        # Fetch Opportunities created in the last 6 months using Pardot API
        api_endpoint = "https://pi.pardot.com/api/opportunity/version/4/do/query"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Pardot-Business-Unit-Id": "0Uv5A000000PAzxSAG"  # Your Business Unit ID
        }
        params = {
            "created_after": six_months_ago_str,
            "fields": "id,prospect_id"
        }

        response = requests.get(api_endpoint, headers=headers, params=params)

        if response.status_code == 200:
            tree = ET.ElementTree(ET.fromstring(response.content))
            root = tree.getroot()

            # Initialize a dictionary to store prospect IDs and their visited URLs
            prospect_visited_urls = {}

            for opportunity in root.findall(".//opportunity"):
                opportunity_id = opportunity.find("id").text
                opportunity_created_at = opportunity.find("created_at").text

                for prospect in opportunity.findall(".//prospect"):
                    prospect_id = prospect.find("id").text

                    # Fetch URLs visited by the prospect
                    api_endpoint = f"https://pi.pardot.com/api/visitorActivity/version/3/do/query?prospect_id={prospect_id}"
                    headers = {
                        "Authorization": f"Bearer {access_token}",
                        "Pardot-Business-Unit-Id": "0Uv5A000000PAzxSAG"  # Your Business Unit ID
                    }
                    response = requests.get(api_endpoint, headers=headers)

                    if response.status_code == 200:
                        try:
                            tree = ET.ElementTree(ET.fromstring(response.content))
                            root = tree.getroot()

                            urls = []
                            for activity in root.findall(".//visitor_activity"):
                                timestamp = activity.find("timestamp").text
                                if timestamp < opportunity_created_at:
                                    url = activity.find("details").text
                                    urls.append(url)

                            prospect_visited_urls[prospect_id] = urls[-5:]

                        except ET.ParseError:
                            continue
                    else:
                        continue

            return {"prospect_visited_urls": prospect_visited_urls}
        else:
            return {"error": f"Failed to fetch data. Status code: {response.status_code}, Raw response: {response.text}"}
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}
