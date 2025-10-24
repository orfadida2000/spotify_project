# Import the requests library to make HTTP requests
# Import csv module for reading and writing CSV files
import csv

# Import os module for operating system dependent functionality (e.g., file path manipulation)
import os

# Import re module for regular expression operations (e.g., pattern matching in text)
import re

import requests

# Import BeautifulSoup from bs4 for parsing HTML documents
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from .constants.genius import GENIUS_ENV_PATH, GENIUS_TOKEN_ENV_VAR

load_dotenv(dotenv_path=GENIUS_ENV_PATH)
GENIUS_API_TOKEN = os.getenv(key=GENIUS_TOKEN_ENV_VAR)


def request_artist_info(artist_name: str, page: int) -> requests.Response | None:
    """
    Makes a request to the Genius API to retrieve information about an artist.

    Parameters:
    - artist_name (str): Name of the artist to search for.
    - page (int): Page number for pagination of results.

    Returns:
    - Response object from the API if successful.
    - None if there is an error.
    """
    if not GENIUS_API_TOKEN:
        print("Genius API token not found. Please set the GENIUS_API_TOKEN environment variable.")
        return None

    # Base URL for the Genius API
    base_url = "https://api.genius.com"

    # Authorization header with the Genius API token (replace GENIUS_API_TOKEN with your actual token)
    headers = {"Authorization": "Bearer " + GENIUS_API_TOKEN}

    # Construct the search URL endpoint for the Genius API
    search_url = base_url + "/search"

    # Define the parameters for the API request (artist name, results per page, page number)
    params = {"q": artist_name, "per_page": 10, "page": page}

    # Make the GET request to the Genius API with the search URL, parameters, and headers
    response = requests.get(search_url, params=params, headers=headers)

    # Check if the response status code is not 200 (OK), print an error message and return None
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return None

    # Return the response object if the request is successful
    return response


# Genius API: Retrieve Song URLs for an Artist


def request_song_url(artist_name: str, song_cap: int) -> list[str]:
    """
    Retrieves song URLs for a given artist from the Genius API.

    Parameters:
    - artist_name (str): Name of the artist to search for.
    - song_cap (int): Maximum number of songs to retrieve.

    Returns:
        list[str]: A list of song URLs up to the specified song_cap.
    """

    # Initialize the page number for pagination and an empty list to store song URLs
    page = 1
    songs = []

    # Loop to fetch song URLs until the song_cap is reached
    while True:
        # Make a request to the Genius API to get artist information for the given page
        response = request_artist_info(artist_name, page)

        # If the response is None (error occurred), exit the loop
        if response is None:
            break

        # Parse the response JSON data
        json_data = response.json()

        # Ensure the 'response' and 'hits' keys exist in the JSON data to avoid KeyError
        if "response" not in json_data or "hits" not in json_data["response"]:
            print("Error: 'response' or 'hits' key not found in the response data")
            break

        # List to store song information from the JSON response
        song_info = []

        # Iterate over the 'hits' in the JSON response to filter songs by the artist name
        for hit in json_data["response"]["hits"]:
            # Check if the artist name in the result matches the requested artist
            if artist_name.lower() in hit["result"]["primary_artist"]["name"].lower():
                song_info.append(hit)

        # Collect URLs from the song objects and add them to the songs list until the song_cap is reached
        for song in song_info:
            if len(songs) < song_cap:
                url = song["result"]["url"]
                songs.append(url)

        # If the desired number of song URLs (song_cap) is reached, exit the loop
        if len(songs) == song_cap:
            break
        else:
            # Increment the page number to fetch the next set of results
            page += 1

    # Print the number of songs found for the artist
    print(f"Found {len(songs)} songs by {artist_name}")

    # Return the list of song URLs
    return songs


# Web Scraping: Extract Lyrics from a Genius.com Song URL


def scrape_song_lyrics(url: str) -> str:
    """
    Scrapes the lyrics of a song from a given Genius.com URL.

    Parameters:
    - url (str): URL of the Genius.com song page.

    Returns:
    - str: A string containing the song lyrics, cleaned and formatted.
    """

    # Make an HTTP GET request to the provided song URL
    page = requests.get(url)

    # Parse the page content using BeautifulSoup
    html = BeautifulSoup(page.text, "html.parser")

    # Find all <div> elements with the 'data-lyrics-container' attribute which contains the lyrics
    lyrics_divs = html.find_all("div", attrs={"data-lyrics-container": "true"})

    # If no lyrics are found, print an error message and return an empty string
    if not lyrics_divs:
        print(f"Could not find lyrics for {url}")
        return ""

    # Extract the text from each lyrics <div> and join them with a newline separator
    lyrics = "\n".join([div.get_text(separator="\n") for div in lyrics_divs])

    # Remove unwanted identifiers like [Chorus], [Verse], etc. using regular expressions
    lyrics = re.sub(r"[\(\[].*?[\)\]]", "", lyrics)

    # Remove empty lines from the lyrics
    lyrics = os.linesep.join([s for s in lyrics.splitlines() if s])

    # Return the cleaned lyrics
    return lyrics


# Write lyrics and song names to a CSV file


def write_lyrics_to_csv(artist_name: str, song_count: int) -> None:
    """
    Writes the lyrics of songs by a given artist to a CSV file, with each line of the lyrics as a separate row.

    Parameters:
    - artist_name (str): The name of the artist.
    - song_count (int): The number of songs to retrieve and write to the file.
    """

    # Create the 'lyrics' directory if it doesn't exist
    if not os.path.exists("lyrics"):
        os.makedirs("lyrics")

    # Generate the file path for the CSV file, replacing spaces with underscores
    file_path = "lyrics/" + artist_name.lower().replace(" ", "_") + ".csv"

    # Open the CSV file for writing
    with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
        # Define the column names for the CSV file
        fieldnames = ["Song", "Lyrics"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        # Write the header row
        writer.writeheader()

        # Retrieve song URLs from Genius API
        urls = request_song_url(artist_name, song_count)

        # Loop through each song URL
        for url in urls:
            # Extract song name from the URL by replacing '-' with spaces and title-casing it
            song_name = url.split("/")[-1].replace("-", " ").title()

            # Dynamically remove the artist's name from the song title
            song_name = song_name.replace(artist_name.title() + " ", "").replace(
                " Lyrics", ""
            )  # Clean song name

            # Scrape the lyrics for the current song
            lyrics = scrape_song_lyrics(url)

            # Only write to the CSV file if lyrics are found
            if lyrics:
                # Split lyrics into lines and write each line to a new row
                for line in lyrics.splitlines():
                    writer.writerow({"Song": song_name, "Lyrics": line})

    # Print a message indicating success
    print(f"Lyrics written to {file_path}")
