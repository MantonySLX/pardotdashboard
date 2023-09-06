from flask import Flask, redirect, request, jsonify, render_template, session, flash
from requests_oauthlib import OAuth2Session
import os
import requests
import collections
from collections import defaultdict
import datetime

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

@app.route("/get-duplicate-email-addresses")
def get_duplicate_email_addresses():
    access_token = session.get("access_token")
    if not access_token:
        return jsonify({"error": "Access token is required"}), 400

    pardot_url = "https://pi.pardot.com/api/v5/objects/prospects"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Pardot-Business-Unit-Id": "0Uv5A000000PAzxSAG"
    }
    response = requests.get(pardot_url, headers=headers)
    data = response.json()

    if isinstance(data, dict) and 'email' in data:
        email_addresses = [data['email']]
    elif isinstance(data, list):
        email_addresses = [prospect['email'] for prospect in data]
    else:
        return jsonify({"error": "Unexpected API response format"}), 500

    duplicates = [item for item, count in collections.Counter(email_addresses).items() if count > 1]
    return jsonify({"duplicate_emails": duplicates})

@app.route("/duplicates")
def show_duplicates():
    return render_template('duplicates.html')

@app.route("/find-qualified-prospects")
def find_qualified_prospects():
    access_token = session.get("access_token")
    if not access_token:
        return jsonify({"error": "Access token is required"}), 400

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Pardot-Business-Unit-Id": "0Uv5A000000PAzxSAG"
    }

    # Calculate the date 90 days ago from today
    ninety_days_ago = (datetime.datetime.now() - datetime.timedelta(days=90)).isoformat()

    # Define the parameters for the query
    params = {
        "fields": "id,visitorId,campaignId",
        "createdAtAfter": ninety_days_ago
    }

    response = requests.get(
        "https://pi.pardot.com/api/v5/objects/visitor-page-views",
        headers=headers,
        params=params
    )
    visitor_page_views_data = response.json()

    if 'values' in visitor_page_views_data:
        qualified_prospects = {
            entry['visitorId']: entry['id']
            for entry in visitor_page_views_data['values']
        }
        flash(f"Step 1: Found {len(qualified_prospects)} qualified prospects.")
    else:
        flash("Step 1: Data key not found in visitor_page_views_data")
        qualified_prospects = {}

    flash(f"Step 3: Found qualified prospects: {qualified_prospects}")

    return jsonify({"qualified_prospects": qualified_prospects})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
