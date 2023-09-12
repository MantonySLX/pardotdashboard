from datetime import datetime, timedelta
from flask import Flask, redirect, request, jsonify, render_template, session
from requests_oauthlib import OAuth2Session
import xml.etree.ElementTree as ET
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

@app.route("/prospects_from_opportunities")
def prospects_from_opportunities():
    access_token = session.get("access_token")
    if access_token is None:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        six_months_ago = datetime.now() - timedelta(days=180)
        six_months_ago_str = six_months_ago.strftime('%Y-%m-%d %H:%M:%S')
        
        api_endpoint = "https://pi.pardot.com/api/opportunity/version/4/do/query"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Pardot-Business-Unit-Id": "0Uv5A000000PAzxSAG"
        }
        params = {
            "created_after": six_months_ago_str,
            "fields": "id,prospect_id"
        }
        
        response = requests.get(api_endpoint, headers=headers, params=params)
        
        if response.status_code == 200:
            tree = ET.ElementTree(ET.fromstring(response.content))
            root = tree.getroot()
            
            prospect_ids = []
            for opportunity in root.findall(".//opportunity"):
                for prospect in opportunity.findall(".//prospect"):
                    prospect_ids.append(prospect.find("id").text)
            
            visitor_ids = []
            for prospect_id in prospect_ids:
                visitor_id = get_visitor_id_by_prospect_id(prospect_id, access_token)
                if visitor_id:
                    visitor_ids.append(visitor_id)

            session['visitor_ids'] = visitor_ids

            return jsonify({"prospect_ids": prospect_ids, "visitor_ids": visitor_ids})
        else:
            return jsonify({"error": f"Failed to fetch data. Status code: {response.status_code}, Raw response: {response.text}"}), 400
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route("/visited_urls_by_prospects")
def visited_urls_by_prospects():
    visitor_ids = session.get('visitor_ids')
    if not visitor_ids:
        return jsonify({"error": "No visitors available"}), 404

    visited_urls_by_visitors = {}
    access_token = session.get("access_token")
    if access_token is None:
        return jsonify({"error": "Not authenticated"}), 401
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Pardot-Business-Unit-Id": "0Uv5A000000PAzxSAG"
    }
    
    for visitor_id in visitor_ids:
        params = {
            "fields": "id,url,title,createdAt,visitorId,campaignId,visitId,durationInSeconds,salesforceId",
            "visitor_id": visitor_id
        }
        api_endpoint = "https://pi.pardot.com/api/v5/objects/visitor-page-views"
        response = requests.get(api_endpoint, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            urls = [item.get('url') for item in data.get('data', [])]
            visited_urls_by_visitors[visitor_id] = urls
        else:
            error_detail = f"Failed to fetch data for visitor ID {visitor_id}. "
            error_detail += f"Status code: {response.status_code}, "
            error_detail += f"Raw response: {response.text}"
            print(f"Warning: {error_detail}")

    return jsonify({"visited_urls_by_visitors": visited_urls_by_visitors})

def get_visitor_id_by_prospect_id(prospect_id, access_token):
    api_endpoint = "https://pi.pardot.com/api/visitor/version/4/do/query"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Pardot-Business-Unit-Id": "0Uv5A000000PAzxSAG",
    }
    params = {
        "prospect_id": prospect_id
    }

    response = requests.get(api_endpoint, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        visit_data = data.get("data", [])
        if visit_data:
            visitor_id = visit_data[0].get("visitorId")
            return visitor_id
        return None
    else:
        print(f"Failed to fetch visitor ID for prospect ID {prospect_id}. Status code: {response.status_code}")
        print(f"Error message: {response.text}")
        return None

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
