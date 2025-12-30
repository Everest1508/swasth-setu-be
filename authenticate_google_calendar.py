#!/usr/bin/env python
"""
Google Calendar Authentication Script

Run this script to authenticate and get access tokens for Google Calendar API.
This only needs to be run once (or when tokens expire).
"""

import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.auth.exceptions import RefreshError
from google_auth_oauthlib.flow import InstalledAppFlow

# Scopes required for Google Calendar API
SCOPES = ['https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/calendar.events']


def authenticate():
    """Authenticate and save token"""
    creds = None
    
    # Check if token already exists
    token_path = 'token.json'
    credentials_path = 'credentials.json'
    
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            try:
                creds.refresh(Request())
            except RefreshError as e:
                print(f"⚠️  Refresh token is invalid: {str(e)}")
                print("The token file will be deleted and you'll need to re-authenticate.")
                # Delete the invalid token file
                if os.path.exists(token_path):
                    os.remove(token_path)
                    print(f"✅ Removed invalid token file: {token_path}")
                # Reset creds to None to trigger fresh authentication
                creds = None
        
        # If we still don't have valid credentials, start fresh authentication
        if not creds or not creds.valid:
            if not os.path.exists(credentials_path):
                print(f"❌ Error: {credentials_path} not found!")
                print("\nPlease:")
                print("1. Go to Google Cloud Console")
                print("2. Create OAuth 2.0 credentials (type: Desktop app or Web application)")
                print("3. Download credentials.json")
                print("4. Save it in the same directory as this script")
                return
            
            print("Starting authentication flow...")
            print("A browser window will open for you to sign in.")
            print("After signing in, you'll be redirected to localhost:8080")
            print()
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, SCOPES
            )
            # Use fixed port 8080 so we can configure it in Google Cloud Console
            # This opens a browser window for the user to log in
            creds = flow.run_local_server(port=8080, open_browser=True)
        
        # Save the credentials for the next run
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
        print(f"✅ Token saved to {token_path}")
    
    print("✅ Authentication successful!")
    print(f"Token file: {token_path}")
    print("\nYou can now use Google Calendar integration.")
    return creds


if __name__ == '__main__':
    print("=" * 50)
    print("Google Calendar Authentication")
    print("=" * 50)
    print()
    authenticate()