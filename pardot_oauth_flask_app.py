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


@app.route("/get_prospect_ids")
def get_prospect_ids():
    access_token = session.get("access_token")
    if not access_token:
        return jsonify({"error": "Not authenticated"}), 401
    
    # Define the API endpoint and headers
    api_endpoint = "https://pi.pardot.com/api/v5/objects/visitor-page-views"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    # Add any filtering parameters you need
    params = {
        'fields': 'id,url,title,createdAt,visitorId,campaignId,visitId,durationInSeconds,salesforceId'
    }
    
    # Make the API request
    response = requests.get(api_endpoint, headers=headers, params=params)
    if response.status_code != 200:
        return jsonify({"error": "API request failed"}), 500
    
    data = response.json()
    
    # Filter the data to only include records where 'url' contains 'utm_medium=email'
    filtered_data = [record for record in data.get('visitorPageView', []) if 'utm_medium=email' in record.get('url', '')]
    
    # Extract the prospect IDs and limit to first 10
    prospect_ids = [record['visitorId'] for record in filtered_data][:10]
    
    return jsonify(prospect_ids)




if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
