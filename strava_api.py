import keyring
import requests
import osmnx as ox
import networkx as nx
import matplotlib.pyplot as plt

# Strava API credentials
CLIENT_ID = keyring.get_password('strava_client_id', 'segment_router')
CLIENT_SECRET = keyring.get_password('strava_client_secret', 'segment_router')
REFRESH_TOKEN = keyring.get_password('strava_refresh_token', 'segment_router')
BASE_URL = 'https://www.strava.com/api/v3'

def get_access_token(client_id, client_secret, refresh_token):
    """
    Obtain a new access token using the refresh token.
    """
    auth_url = 'https://www.strava.com/oauth/token'
    response = requests.post(auth_url, data={
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    })
    response.raise_for_status()  # Raise an error for bad status codes
    return response.json()['access_token']

def search_segments(lat_min, lon_min, lat_max, lon_max, access_token):
    """
    Search Strava segments within a bounding box defined by coordinates.
    """
    search_url = f"{BASE_URL}/segments/explore"
    params = {
        'bounds': f"{lat_min},{lon_min},{lat_max},{lon_max}",
        'activity_type': 'running',  # Can also use 'running', could modify later to allow
    }
    headers = {
        'Authorization': f"Bearer {access_token}"
    }
    response = requests.get(search_url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()