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
import requests
import json

# The Pardot API endpoint for querying visitor activities
visitor_activities_endpoint = "https://ap2.salesforce.com/services/data/v46.0/visitorActivities/query"

# The UTM parameter value to filter for
utm_source = "SLX"

# The type of visitor activity to filter for
activity_type = "Page View"

# The date to start filtering for opportunities created after
opportunity_creation_date = "2023-09-06"

# The number of days to filter for opportunities created within
opportunity_creation_window_days = 90

# Get the visitor activities
response = requests.get(
    visitor_activities_endpoint,
    params={
        "query": "utm_source eq '{}' and activity_type eq '{}'".format(
            utm_source, activity_type
        )
    }
)

if response.status_code == 200:
    visitor_activities = json.loads(response.content)

    # Identify the unique prospect IDs
    prospect_ids = set()
    for visitor_activity in visitor_activities:
        prospect_ids.add(visitor_activity["prospectId"])

    # Check opportunity creation for each prospect ID
    opportunities = []
    for prospect_id in prospect_ids:
        # Get the opportunities associated with the prospect ID
        response = requests.get(
            "https://ap2.salesforce.com/services/data/v46.0/opportunities/query",
            params={
                "query": "prospectId eq '{}' and createdDate gt '{}'".format(
                    prospect_id, opportunity_creation_date
                )
            }
        )

        if response.status_code == 200:
            opportunities.extend(json.loads(response.content))

    # Compile the results
    prospect_ids_with_opportunities = []
    for opportunity in opportunities:
        if (
            opportunity["createdDate"] - opportunity_creation_date
            <= opportunity_creation_window_days
        ):
            prospect_ids_with_opportunities.append(opportunity["prospectId"])

    print(prospect_ids_with_opportunities)

else:
    print("Error getting visitor activities.")
