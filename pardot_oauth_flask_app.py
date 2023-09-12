from datetime import datetime, timedelta
from flask import Flask, redirect, request, jsonify, render_template, session
from requests_oauthlib import OAuth2Session
import xml.etree.ElementTree as ET
import os
import requests

# Setup Flask app and environment variables
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SESSION_TYPE'] = 'filesystem'
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

client_id = "3MVG9vrJTfRxlfl5mE9P222f0lPVcbroMn_i_eLgYtu_MTF2IBouHStVrA5nd5zSJTkSR1AHMe_U5ZUip6Len"
client_secret = "C936BFCFED42379E749DDC26FC3F754082790DF4C83193C3BB8DC27D5885371B"
authorization_base_url = "https://login.salesforce.com/services/oauth2/authorize"
token_url = "https://login.salesforce.com/services/oauth2/token"
redirect_uri = "https://pardotdashboard-7fc843d1f87a.herokuapp.com/callback"

@app.route("/")
def main():
    return render_template('main.html')

@app.route("/auth")
def auth():
    pardot = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=[
        "refresh_token",
        "offline_access",
        "openid",
        "pardot_api",
        "cdp_query_api"
    ])
    authorization_url, state = pardot.authorization_url(authorization_base_url)
    return redirect(authorization_url)

@app.route("/callback", methods=["GET"])
def callback():
    pardot = OAuth2Session(client_id, state=request.args.get("state"), redirect_uri=redirect_uri)
    token = pardot.fetch_token(token_url, client_secret=client_secret, authorization_response=request.url)
    session["access_token"] = token.get("access_token")
    return redirect("/dashboard")

@app.route("/dashboard")
def dashboard():
    average_open_rate = 25.5
    return render_template('dashboard.html', average_open_rate=average_open_rate)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/prospects_from_opportunities")
def prospects_from_opportunities():
    access_token = session.get("access_token")
    if access_token is None:
        return jsonify({"error": "Not authenticated"}), 401
    
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
            
            return jsonify({"prospect_visited_urls": prospect_visited_urls})
        else:
            return jsonify({"error": f"Failed to fetch data. Status code: {response.status_code}, Raw response: {response.text}"}), 400
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
