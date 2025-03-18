import requests
import random

class LastFMClient:
    """
    Class to interact with Last.fm API.
    """
    def __init__(self, api_key: str):
        """
        Initialize the LastFM class with the given API key and Base Url.
        """
        # Set the API key
        self.api_key = api_key

        # Set the base URL for API requests
        self.base_url = "http://ws.audioscrobbler.com/2.0/"
    
    def _request(self, method: str, **args):
        """
        Make a request to the Last.fm API. 
        Returns the JSON response or {} in case of an error.
        """
        # Create the request parameters
        params = {
            "method": method,
            "api_key": self.api_key,
            "format": "json"
        }

        # Update the parameters with the provided arguments
        params.update(args)

        # Make the request
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception:
            return {}
    
    def _get_similar_track(self, track_name: str, artist_name: str):
        """
        Fetches a similar/recommended track based on the given track name and artist name.
        The 5 similar tracks are fetched and one is randomly selected.
        Returns the recommended track in the format "<Track Name> - <Artist Name>",
        otherwise returns None.
        """
        # Make the request
        data = self._request(
            "track.getSimilar", 
            track=track_name, 
            artist=artist_name,
            limit=5
        )
        
        # Check if the response contains the required similar tracks data
        if "similartracks" not in data or not data["similartracks"]["track"]:
            return None
        
        # Extract similar tracks
        similar_tracks = data["similartracks"]["track"]
        
        # Randomly select one of the similar tracks
        recommended_track = random.choice(similar_tracks)

        # Return the recommended track
        return f'{recommended_track["name"]} - {recommended_track["artist"]["name"]}'
    
    def _get_top_chart(self, track_name: str):
        """
        Fetches the top tracks chart from Last.fm API.
        The 35 top chart tracks are fetched and one is randomly selected.
        Returns the recommended track in the format "<Track Name> - <Artist Name>",
        otherwise returns None.
        """
        # Make the request
        data = self._request(
            "chart.getTopTracks", 
            limit=35
        )
        
        # Check if the response contains the required top tracks data
        if "tracks" not in data or not data["tracks"]["track"]:
            return None
        
        # Extract top tracks
        top_tracks = data["tracks"]["track"]
        
        # Randomly select one of the top tracks
        recommended_track = random.choice(top_tracks)

        # Make sure the recommended track is different from the given track
        while recommended_track["name"] == track_name:
            recommended_track = random.choice(top_tracks)

        # Return the recommended track
        return f'{recommended_track["name"]} - {recommended_track["artist"]["name"]}'
    
    def get_recommendation(self, track_name: str, artist_name: str):
        """
        Fetches a recommended track based on the given track name and artist name.
        If the similar tracks are not found, fetches from the top chart track.
        Returns the recommended track in the format "<Track Name> - <Artist Name>",
        otherwise returns None.
        """
        # Get similar track
        similar_track = self._get_similar_track(track_name, artist_name)
        
        # If similar track is not found, get top chart track
        if not similar_track:
            similar_track = self._get_top_chart(track_name)
        
        # Return the recommended track
        return similar_track      