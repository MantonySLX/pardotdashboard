
from flask import Flask, redirect, request, jsonify
from requests_oauthlib import OAuth2Session

app = Flask(__name__)

# Your Salesforce Connected App credentials
CLIENT_ID = 'YOUR_CLIENT_ID'
CLIENT_SECRET = 'YOUR_CLIENT_SECRET'
REDIRECT_URI = 'http://localhost:5000/callback'  # Replace with your Heroku app's callback URL

# Pardot OAuth2 URLs
AUTHORIZATION_URL = 'https://login.salesforce.com/services/oauth2/authorize'
TOKEN_URL = 'https://login.salesforce.com/services/oauth2/token'

# Initialize OAuth2 session
pardot = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI)

@app.route('/')
def index():
    return "Welcome to Pardot OAuth2 Test. <a href='/auth'>Login with Pardot</a>"

@app.route('/auth')
def auth():
    # Redirect user to Pardot for authorization
    authorization_url, state = pardot.authorization_url(AUTHORIZATION_URL)
    return redirect(authorization_url)

@app.route('/callback', methods=['GET'])
def callback():
    # User has authorized, now let's get the access token
    pardot.fetch_token(
        TOKEN_URL,
        client_secret=CLIENT_SECRET,
        authorization_response=request.url
    )
    
    # At this point, you have the access token and can make Pardot API calls
    # For demonstration, let's fetch and display some dummy data
    return jsonify({"message": "Successfully authenticated", "average_open_rate": "25%"})

if __name__ == '__main__':
    app.run(debug=True)
