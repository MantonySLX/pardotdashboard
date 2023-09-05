from flask import Flask, redirect, request, jsonify, render_template, session  # Added session import
from requests_oauthlib import OAuth2Session
import os
import requests

# Setup Flask app and environment variables
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SESSION_TYPE'] = 'filesystem'  # Add this line
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

client_id = "3MVG9vrJTfRxlfl5mE9P222f0lPVcbroMn_i_eLgYtu_MTF2IBouHStVrA5nd5zSJTkSR1AHMe_U5ZUip6Len"
client_secret = "C936BFCFED42379E749DDC26FC3F754082790DF4C83193C3BB8DC27D5885371B"
authorization_base_url = "https://login.salesforce.com/services/oauth2/authorize"
token_url = "https://login.salesforce.com/services/oauth2/token"
redirect_uri = "https://pardotdashboard-7fc843d1f87a.herokuapp.com/"

@app.route("/")
def home():
    access_token = session.get("access_token", "")
    return render_template('templates.html', access_token=access_token)

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

    # Store the access token in the session
    session["access_token"] = token.get("access_token")
    
    return redirect("/dashboard")

@app.route("/dashboard")
def dashboard():
    # Mock average open rate data (replace with actual data)
    average_open_rate = 25.5
    return render_template('dashboard.html', average_open_rate=average_open_rate)

@app.route("/logout")
def logout():
    session.clear()  # This clears all session data
    return redirect("/")

@app.route("/get-email-templates")
def get_email_templates():
    access_token = request.args.get("access_token")
    if not access_token:
        return jsonify({"error": "Access token is required"}), 400

    fields = request.args.get("fields", "id,name,isOneToOneEmail,isAutoResponderEmail,isDripEmail,isListEmail")
    pardot_url = f"https://pi.pardot.com/api/v5/objects/email-templates?fields={fields}"

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.get(pardot_url, headers=headers)
    return jsonify(response.json())

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
