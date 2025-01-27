# Import necessary libraries
import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import base64

# Spotify API credentials
client_id = ## INSERT CLIENT ID HERE
client_secret = ## INSERT CLIENT KEY HERE

# Musixmatch API key
musixmatch_api_key = ### INSERT API KEY HERE

# Base URLs for the APIs
musixmatch_base_url = ## INSERT BASE URL
spotify_base_url = ## INSERT BASE URL

# ### Function to Get Spotify Access Token ###
# 
# The `get_spotify_access_token` function is responsible for authenticating with the Spotify API 
# and retrieving an access token. This token is necessary for making further requests to the Spotify API.
def get_spotify_access_token():
    # Prepare the authorization header by encoding the client ID and secret using base64 encoding.
    auth_headers = {
        "Authorization": "Basic " + base64.b64encode(f"{client_id}:{client_secret}".encode()).decode(),
        "Content-Type": "application/x-www-form-urlencoded"
    }
    # Set the data required for the request, specifying that we want a client credentials token.
    auth_data = {"grant_type": "client_credentials"}
    # Send a POST request to Spotify's token endpoint to get an access token.
    response = requests.post("https://accounts.spotify.com/api/token", headers=auth_headers, data=auth_data)
    # Parse the response to extract the access token and return it.
    return response.json()["access_token"]

# ### Function to Search for Songs on Spotify ###
# 
# The `search_songs` function takes a search query and an access token, and returns a list of tracks 
# that match the search criteria from the Spotify API.
def search_songs(query, access_token):
    # Set the authorization headers with the access token obtained earlier.
    headers = {"Authorization": f"Bearer {access_token}"}
    # Make a GET request to Spotify's search endpoint, specifying the query and limiting results to 50 tracks.
    response = requests.get(f"{spotify_base_url}search?q={query}&type=track&limit=50", headers=headers)
    # Parse the response to extract the list of tracks and return it.
    return response.json()["tracks"]["items"]

# ### Function to Get Musixmatch Track ID ###
# 
# The `get_musixmatch_track_id` function takes a track name and an artist name, and retrieves the 
# corresponding track ID from the Musixmatch API.
def get_musixmatch_track_id(track_name, artist_name):
    # Construct the search URL for Musixmatch, including the track name, artist name, and API key.
    search_url = f"{musixmatch_base_url}track.search?q_track={track_name}&q_artist={artist_name}&apikey={musixmatch_api_key}"
    # Send a GET request to Musixmatch's track search endpoint.
    search_response = requests.get(search_url)

    # Check if the request was successful (status code 200).
    if search_response.status_code == 200:
        search_data = search_response.json()
        # Extract the list of tracks from the response.
        track_list = search_data["message"]["body"]["track_list"]

        # If the track list is not empty, return the ID of the first track in the list.
        if track_list:
            return track_list[0]["track"]["track_id"]
    
    # Return None if no track ID is found.
    return None

# ### Function to Get Lyrics and Genre from Musixmatch ###
# 
# The `get_lyrics_and_genre` function retrieves the lyrics and genre of a track from Musixmatch 
# using the track name and artist name.
def get_lyrics_and_genre(track_name, artist_name):
    # Get the Musixmatch track ID for the given track and artist.
    track_id = get_musixmatch_track_id(track_name, artist_name)

    if track_id:
        # Construct the URL to get lyrics for the track.
        lyrics_url = f"{musixmatch_base_url}track.lyrics.get?track_id={track_id}&apikey={musixmatch_api_key}"
        # Send a GET request to Musixmatch's lyrics endpoint.
        lyrics_response = requests.get(lyrics_url)

        if lyrics_response.status_code == 200:
            lyrics_data = lyrics_response.json()
            lyrics_body = lyrics_data["message"]["body"]

            # Check if the lyrics data is in the expected format and extract the lyrics.
            if isinstance(lyrics_body, dict) and "lyrics" in lyrics_body:
                lyrics = lyrics_body["lyrics"]["lyrics_body"]
            else:
                lyrics = ""
        else:
            lyrics = ""

        # Construct the URL to get track details.
        track_url = f"{musixmatch_base_url}track.get?track_id={track_id}&apikey={musixmatch_api_key}"
        # Send a GET request to Musixmatch's track details endpoint.
        track_response = requests.get(track_url)

        if track_response.status_code == 200:
            track_data = track_response.json()
            
            # Check if the track data is in the expected format and extract the genre.
            if "message" in track_data and "body" in track_data["message"] and "track" in track_data["message"]["body"]:
                track_info = track_data["message"]["body"]["track"]

                if "primary_genres" in track_info and "music_genre_list" in track_info["primary_genres"]:
                    genre_list = track_info["primary_genres"]["music_genre_list"]
                    if genre_list:
                        genre = genre_list[0]["music_genre"]["music_genre_name"]
                    else:
                        genre = "N/A"
                else:
                    genre = "N/A"
            else:
                genre = "N/A"
        else:
            genre = "N/A"
    else:
        lyrics = ""
        genre = "N/A"

    # Return the extracted lyrics and genre.
    return lyrics, genre

# ### Function to Get Song Recommendations ###
# 
# The `get_recommendations` function generates song recommendations based on the lyrics and genre of 
# a given song. It uses TF-IDF vectorization and cosine similarity to find similar songs.
def get_recommendations(song_name, artist_name, song_lyrics, song_genre, num_recommendations=10):
    # Create a TF-IDF vectorizer to convert lyrics into numerical data.
    vectorizer = TfidfVectorizer(stop_words="english")

    # Extract lyrics and genres from the songs_data list, excluding the input song.
    lyrics_list = [song["Lyrics"] for song in songs_data if song_name.lower() not in song["Song"].lower() and song["Lyrics"]]
    genre_list = [song["Genre"] for song in songs_data if song_name.lower() not in song["Song"].lower() and song["Lyrics"]]

    # If no lyrics are available, return an empty list.
    if not lyrics_list:
        return []

    # Fit and transform the lyrics to get the TF-IDF matrix.
    tfidf_matrix = vectorizer.fit_transform([song_lyrics] + lyrics_list)

    # Calculate the cosine similarity between the input song and all other songs.
    similarity_scores = cosine_similarity(tfidf_matrix[0], tfidf_matrix[1:])

    # Combine similarity scores and genre matching.
    combined_scores = similarity_scores.flatten()
    for i in range(len(lyrics_list)):
        if genre_list[i] == song_genre:
            combined_scores[i] += 0.2  # Increase score for matching genre.

    # Get the indices of the top similar songs.
    similar_song_indices = combined_scores.argsort()[::-1]

    # Get the recommended songs.
    recommended_songs = []
    for i in similar_song_indices:
        if len(recommended_songs) == num_recommendations:
            break
        song = songs_data[i]["Song"]
        artist = songs_data[i]["Artist"]
        # Avoid recommending the input song itself.
        if song_name.lower() not in song.lower() and song not in [rec[0] for rec in recommended_songs]:
            recommended_songs.append((song, artist))

    return recommended_songs

# ### Main Program ###
# 
# The main program flow involves getting a Spotify access token, interacting with the user to get 
# song input, fetching search results from Spotify, and displaying recommendations based on the 
# selected song's lyrics and genre.

# Get the Spotify access token.
access_token = get_spotify_access_token()

# Main loop to interact with the user.
while True:
    # Prompt the user to enter a song title.
    user_input = input("Enter a song title (or 'quit' to exit): ")

    if user_input.lower() == "quit":
        break

    # Search for songs matching the user's input on Spotify.
    search_results = search_songs(user_input, access_token)

    if not search_results:
        print("No songs found. Please try again.")
        continue

    # Display search results to the user.
    print("Search results:")
    for i, track in enumerate(search_results[:10], start=1):
        print(f"{i}. {track['name']} - {track['artists'][0]['name']}")

    # Prompt the user to select a song from the search results.
    selection = input("Enter the number of the desired song: ")

    try:
        # Get the selected track's details.
        selected_track = search_results[int(selection) - 1]
        song_name = selected_track["name"]
        artist_name = selected_track["artists"][0]["name"]

        # Get the lyrics and genre of the selected track from Musixmatch.
        lyrics, genre = get_lyrics_and_genre(song_name, artist_name)

        if lyrics:
            # Clear the songs_data list for each new search.
            songs_data = []
            songs_data.append({"Song": song_name, "Artist": artist_name, "Lyrics": lyrics, "Genre": genre})

            # Fetch lyrics and genre for other songs in the search results.
            for track in search_results:
                if track["name"] != song_name or track["artists"][0]["name"] != artist_name:
                    track_lyrics, track_genre = get_lyrics_and_genre(track["name"], track["artists"][0]["name"])
                    if track_lyrics:
                        songs_data.append({"Song": track["name"], "Artist": track["artists"][0]["name"], "Lyrics": track_lyrics, "Genre": track_genre})

            # Get and display song recommendations.
            recommendations = get_recommendations(song_name, artist_name, lyrics, genre)

            print(f"\nRecommendations for '{song_name}' by {artist_name}:")
            if recommendations:
                for song, artist in recommendations:
                    print(f"{song} - {artist}")
            else:
                print("No recommendations found.")
        else:
            print("No lyrics found for the selected song.")

    except (ValueError, IndexError):
        print("Invalid selection. Please try again.")
