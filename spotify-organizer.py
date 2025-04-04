import os
import calendar
import datetime
import logging
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dateutil.relativedelta import relativedelta

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_previous_month_info():
    """Get the previous month and year"""
    today = datetime.datetime.now()
    first_day_of_month = today.replace(day=1)
    last_day_of_previous_month = first_day_of_month - datetime.timedelta(days=1)
    
    prev_month_name = last_day_of_previous_month.strftime("%B")
    prev_month_year = last_day_of_previous_month.strftime("%Y")
    
    return prev_month_name, prev_month_year

def authenticate_spotify():
    """Authenticate with Spotify API"""
    try:
        auth_manager = SpotifyOAuth(
            client_id=os.environ["SPOTIFY_CLIENT_ID"],
            client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
            redirect_uri=os.environ["SPOTIFY_REDIRECT_URI"],
            scope="playlist-modify-public playlist-modify-private playlist-read-private",
            cache_path=None
        )
        sp = spotipy.Spotify(auth_manager=auth_manager)
        return sp
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise

def find_playlist_by_name(sp, name):
    """Find a playlist by name (case insensitive)"""
    offset = 0
    limit = 50
    
    while True:
        playlists = sp.current_user_playlists(limit=limit, offset=offset)
        
        if not playlists['items']:
            break
            
        for playlist in playlists['items']:
            if playlist['name'].lower() == name.lower():
                return playlist
                
        offset += limit
        
        if offset >= playlists['total']:
            break
    
    return None

def get_playlist_tracks(sp, playlist_id):
    """Get all tracks from a playlist"""
    tracks = []
    offset = 0
    limit = 100
    
    while True:
        results = sp.playlist_tracks(playlist_id, offset=offset, limit=limit)
        tracks.extend(results['items'])
        
        offset += limit
        
        if offset >= results['total']:
            break
    
    return [track['track']['uri'] for track in tracks if track['track']]

def add_tracks_to_playlist(sp, playlist_id, track_uris):
    """Add tracks to a playlist in batches"""
    if not track_uris:
        logger.warning("No tracks to add")
        return
        
    # Spotify has a limit of 100 tracks per request
    batch_size = 100
    for i in range(0, len(track_uris), batch_size):
        batch = track_uris[i:i + batch_size]
        sp.playlist_add_items(playlist_id, batch)
        logger.info(f"Added batch of {len(batch)} tracks to playlist")

def main():
    try:
        # Get previous month and year
        prev_month, prev_year = get_previous_month_info()
        logger.info(f"Processing playlists for {prev_month} {prev_year}")
        
        # Authenticate with Spotify
        sp = authenticate_spotify()
        
        # Find source playlist (previous month and year)
        source_playlist_name = f"{prev_month} {prev_year}"
        source_playlist = find_playlist_by_name(sp, source_playlist_name)
        
        if not source_playlist:
            logger.error(f"Source playlist '{source_playlist_name}' not found")
            return
            
        logger.info(f"Found source playlist: {source_playlist['name']} (ID: {source_playlist['id']})")
        
        # Get all tracks from source playlist
        track_uris = get_playlist_tracks(sp, source_playlist['id'])
        logger.info(f"Found {len(track_uris)} tracks in source playlist")
        
        if not track_uris:
            logger.warning("No tracks found in source playlist. Exiting.")
            return
        
        # Find and update month playlist (APRIL)
        month_playlist_name = prev_month.upper()
        month_playlist = find_playlist_by_name(sp, month_playlist_name)
        
        if month_playlist:
            logger.info(f"Adding tracks to month playlist: {month_playlist['name']}")
            add_tracks_to_playlist(sp, month_playlist['id'], track_uris)
        else:
            logger.error(f"Month playlist '{month_playlist_name}' not found")
        
        # Find and update year playlist
        year_playlist_name = prev_year
        year_playlist = find_playlist_by_name(sp, year_playlist_name)
        
        if year_playlist:
            logger.info(f"Adding tracks to year playlist: {year_playlist['name']}")
            add_tracks_to_playlist(sp, year_playlist['id'], track_uris)
        else:
            logger.error(f"Year playlist '{year_playlist_name}' not found")
        
        # Find and update 'Oh at all' playlist
        all_playlist_name = "Oh at all"
        all_playlist = find_playlist_by_name(sp, all_playlist_name)
        
        if all_playlist:
            logger.info(f"Adding tracks to 'Oh at all' playlist")
            add_tracks_to_playlist(sp, all_playlist['id'], track_uris)
        else:
            logger.error(f"'Oh at all' playlist not found")
        
        logger.info("Playlist organization completed successfully")
        
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise

if __name__ == "__main__":
    main()