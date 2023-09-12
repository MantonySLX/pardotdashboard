from flask import Flask, redirect, request, jsonify, render_template, session
from requests_oauthlib import OAuth2Session
import os
import requests
import collections

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

import requests

def get_prospects_by_url(access_token):
    api_endpoint = "https://pi.pardot.com/api/v5/objects/visitor-page-views"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Pardot-Business-Unit-Id": "0Uv5A000000PAzxSAG",  # Business Unit ID
    }
    params = {
        "fields": "id,url,title,createdAt,visitorId,campaignId,visitId,durationInSeconds,salesforceId"
    }
    
    response = requests.get(api_endpoint, headers=headers, params=params)
    
    if response.status_code == 200:
        data = response.json()
        # Filter the results where URL is https://saleslabx.com/demo-page/
        filtered_data = [item for item in data.get('data', []) if item.get('url') == 'https://saleslabx.com/demo-page/']
        # Extract the visitor IDs from the filtered data
        visitor_ids = [item.get('visitorId') for item in filtered_data]
        return visitor_ids[:20]  # Limit to first 20
    else:
        return None


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
            data = response.json()
            # Check if the 'result' and 'opportunity' keys exist in the response
            if 'result' in data and 'opportunity' in data['result']:
                # Extract the prospect IDs from the Opportunity records
                prospect_ids = [record.get("prospect_id") for record in data.get("result", {}).get("opportunity", [])]
                return jsonify({"prospect_ids": prospect_ids})
            else:
                return jsonify({"error": "Unexpected data format"}), 400
        else:
            return jsonify({"error": f"Failed to fetch data. Status code: {response.status_code}"}), 400
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500





if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
