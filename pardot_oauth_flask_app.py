
from flask import Flask, redirect, request, jsonify
from requests_oauthlib import OAuth2Session
import os

# Setup Flask app and environment variables
app = Flask(__name__)
app.secret_key = os.urandom(24)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
client_id = "3MVG9vrJTfRxlfl5mE9P222f0lPVcbroMn_i_eLgYtu_MTF2IBouHStVrA5nd5zSJTkSR1AHMe_U5ZUip6Len"
client_secret = "C936BFCFED42379E749DDC26FC3F754082790DF4C83193C3BB8DC27D5885371B"
authorization_base_url = "https://login.salesforce.com/services/oauth2/authorize"
token_url = "https://login.salesforce.com/services/oauth2/token"
redirect_uri = "https://oauth.pstmn.io/v1/browser-callback"

# Route for the home page
@app.route("/")
def home():
    return 'Welcome to Pardot OAuth2 Test. <a href="/auth">Click here to authorize</a>'

# Route to initiate OAuth2 process
@app.route("/auth")
def auth():
    pardot = OAuth2Session(client_id, redirect_uri=redirect_uri, scope = [
    "refresh_token",
    "offline_access",
    "openid",
    "pardot_api",
    "cdp_query_api"
])
    authorization_url, state = pardot.authorization_url(authorization_base_url)
    return redirect(authorization_url)

# Route for OAuth2 callback
@app.route("/callback", methods=["GET"])
def callback():
    pardot = OAuth2Session(client_id, state=request.args.get("state"), redirect_uri=redirect_uri)
    token = pardot.fetch_token(token_url, client_secret=client_secret, authorization_response=request.url)
    
    # Make a mock Pardot API call to get average open rate (replace this with an actual Pardot API call)
    average_open_rate = 25.5  # Mock data
    return jsonify({"access_token": token.get("access_token"), "average_open_rate": average_open_rate})

# Run the app
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
