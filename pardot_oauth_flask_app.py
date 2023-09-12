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

@app.route("/find_prospects")
def find_prospects():
    access_token = session.get("access_token")
    if access_token:
        prospects = get_prospects_by_url(access_token)
        if prospects:
            return jsonify({"prospect_ids": prospects})
        else:
            return jsonify({"error": "Could not fetch prospects"}), 400
    else:
        return jsonify({"error": "Not authenticated"}), 401





if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
