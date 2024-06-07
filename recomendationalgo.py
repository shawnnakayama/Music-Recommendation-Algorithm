# -*- coding: utf-8 -*-
"""
Created on Fri Jun  7 09:24:33 2024

@author: shawn
"""

import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import base64

# Spotify API credentials
client_id = "ec3d868061ca4b32ba5d7d1b30f3e604"
client_secret = "5ffc8ff78f514f0eba200ae74a7560ee"

# Musixmatch API key
musixmatch_api_key = "d23111dc373b0f22f120dc280b558a8d"

# Base URLs for the APIs
musixmatch_base_url = "https://api.musixmatch.com/ws/1.1/"
spotify_base_url = "https://api.spotify.com/v1/"

def get_spotify_access_token():
    auth_headers = {
        "Authorization": "Basic " + base64.b64encode(f"{client_id}:{client_secret}".encode()).decode(),
        "Content-Type": "application/x-www-form-urlencoded"
    }
    auth_data = {"grant_type": "client_credentials"}
    response = requests.post("https://accounts.spotify.com/api/token", headers=auth_headers, data=auth_data)
    return response.json()["access_token"]

def search_songs(query, access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(f"{spotify_base_url}search?q={query}&type=track&limit=50", headers=headers)
    return response.json()["tracks"]["items"]

def get_musixmatch_track_id(track_name, artist_name):
    search_url = f"{musixmatch_base_url}track.search?q_track={track_name}&q_artist={artist_name}&apikey={musixmatch_api_key}"
    search_response = requests.get(search_url)

    if search_response.status_code == 200:
        search_data = search_response.json()
        track_list = search_data["message"]["body"]["track_list"]

        if track_list:
            return track_list[0]["track"]["track_id"]
    
    return None

def get_lyrics_and_genre(track_name, artist_name):
    track_id = get_musixmatch_track_id(track_name, artist_name)

    if track_id:
        lyrics_url = f"{musixmatch_base_url}track.lyrics.get?track_id={track_id}&apikey={musixmatch_api_key}"
        lyrics_response = requests.get(lyrics_url)

        if lyrics_response.status_code == 200:
            lyrics_data = lyrics_response.json()
            lyrics_body = lyrics_data["message"]["body"]

            if isinstance(lyrics_body, dict) and "lyrics" in lyrics_body:
                lyrics = lyrics_body["lyrics"]["lyrics_body"]
            else:
                lyrics = ""
        else:
            lyrics = ""

        track_url = f"{musixmatch_base_url}track.get?track_id={track_id}&apikey={musixmatch_api_key}"
        track_response = requests.get(track_url)

        if track_response.status_code == 200:
            track_data = track_response.json()
            
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

    return lyrics, genre

def get_recommendations(song_name, artist_name, song_lyrics, song_genre, num_recommendations=10):
    # Create a TF-IDF vectorizer
    vectorizer = TfidfVectorizer(stop_words="english")

    # Extract lyrics and genres from the songs_data list
    lyrics_list = [song["Lyrics"] for song in songs_data if song_name.lower() not in song["Song"].lower() and song["Lyrics"]]
    genre_list = [song["Genre"] for song in songs_data if song_name.lower() not in song["Song"].lower() and song["Lyrics"]]

    if not lyrics_list:
        return []

    # Fit and transform the lyrics to get the TF-IDF matrix
    tfidf_matrix = vectorizer.fit_transform([song_lyrics] + lyrics_list)

    # Calculate the cosine similarity between the input song and all other songs
    similarity_scores = cosine_similarity(tfidf_matrix[0], tfidf_matrix[1:])

    # Combine similarity scores and genre matching
    combined_scores = similarity_scores.flatten()
    for i in range(len(lyrics_list)):
        if genre_list[i] == song_genre:
            combined_scores[i] += 0.2  # Increase score for matching genre

    # Get the indices of the top similar songs
    similar_song_indices = combined_scores.argsort()[::-1]

    # Get the recommended songs
    recommended_songs = []
    for i in similar_song_indices:
        if len(recommended_songs) == num_recommendations:
            break
        song = songs_data[i]["Song"]
        artist = songs_data[i]["Artist"]
        if song_name.lower() not in song.lower() and song not in [rec[0] for rec in recommended_songs]:
            recommended_songs.append((song, artist))

    return recommended_songs

# Get the Spotify access token
access_token = get_spotify_access_token()

while True:
    user_input = input("Enter a song title (or 'quit' to exit): ")

    if user_input.lower() == "quit":
        break

    search_results = search_songs(user_input, access_token)

    if not search_results:
        print("No songs found. Please try again.")
        continue

    print("Search results:")
    for i, track in enumerate(search_results[:10], start=1):
        print(f"{i}. {track['name']} - {track['artists'][0]['name']}")

    selection = input("Enter the number of the desired song: ")

    try:
        selected_track = search_results[int(selection) - 1]
        song_name = selected_track["name"]
        artist_name = selected_track["artists"][0]["name"]

        lyrics, genre = get_lyrics_and_genre(song_name, artist_name)

        if lyrics:
            # Clear the songs_data list for each new search
            songs_data = []
            songs_data.append({"Song": song_name, "Artist": artist_name, "Lyrics": lyrics, "Genre": genre})

            # Fetch lyrics and genre for other songs
            for track in search_results:
                if track["name"] != song_name or track["artists"][0]["name"] != artist_name:
                    track_lyrics, track_genre = get_lyrics_and_genre(track["name"], track["artists"][0]["name"])
                    if track_lyrics:
                        songs_data.append({"Song": track["name"], "Artist": track["artists"][0]["name"], "Lyrics": track_lyrics, "Genre": track_genre})

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