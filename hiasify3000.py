import streamlit as st
import pandas as pd
import zipfile
import os


###########################################################
# DATA IMPORT
def get_spotify_data(json_files: list) -> pd.DataFrame:
    dataframe = pd.DataFrame()

    for json_file in json_files:
        with zip_ref.open(json_file) as f:
            df_temp = pd.read_json(f)
            df_temp = df_temp[[
                'ts',
                'ms_played',
                'master_metadata_track_name',
                'master_metadata_album_artist_name',
                'master_metadata_album_album_name',
                'reason_end'
            ]]

            dataframe = pd.concat([dataframe, df_temp])

    dataframe.columns = ['time', 'ms_played', 'track', 'artist', 'album', 'reason_end']

    # remove empty rows
    dataframe = dataframe.fillna("")
    dataframe = dataframe.loc[dataframe['ms_played'] > 60000]
    dataframe['ms_played'] = dataframe['ms_played'] / 1000 / 60 / 60
    dataframe.rename(columns={'ms_played': 'hours_played'}, inplace=True)
    dataframe = dataframe.loc[dataframe['track'] != '']

    dataframe = dataframe.sort_values(by='time')

    dataframe = dataframe.drop_duplicates(subset=['time', 'track', 'artist', 'album'])
    dataframe['time'] = pd.to_datetime(dataframe['time'])

    return dataframe


###########################################################
# SPOTIFY DATA
def helper_get_spotify_tracks(df: pd.DataFrame) -> pd.DataFrame:
    df_tracks_grouped = df[['hours_played', 'track', 'artist', 'time']].copy()
    df_tracks_grouped['track'] = df_tracks_grouped['artist'] + " - " + df_tracks_grouped['track']
    df_tracks_grouped = df_tracks_grouped[['time', 'hours_played', 'track']]
    df_tracks_grouped = df_tracks_grouped.groupby(['track']).agg({'track': 'count', 'hours_played': 'sum'})
    df_tracks_grouped.rename(columns={'track': 'anzahl'}, inplace=True)
    df_tracks_grouped.sort_values(by=['anzahl'], ascending=False, inplace=True)
    df_tracks_grouped.reset_index(inplace=True)
    df_tracks_grouped['hours_played'] = df_tracks_grouped['hours_played'].round(2)
    return df_tracks_grouped


def helper_get_spotify_artists(df: pd.DataFrame) -> pd.DataFrame:
    df_artists_grouped = df[['hours_played', 'artist', 'time']].copy()
    df_artists_grouped = df_artists_grouped.groupby(['artist']).agg({'artist': 'count', 'hours_played': 'sum'})
    df_artists_grouped.rename(columns={'artist': 'anzahl'}, inplace=True)
    df_artists_grouped.sort_values(by=['anzahl'], ascending=False, inplace=True)
    df_artists_grouped.reset_index(inplace=True)
    df_artists_grouped['hours_played'] = df_artists_grouped['hours_played'].round(2)
    return df_artists_grouped


def get_spotify_all_time_data(df: pd.DataFrame) -> None:
    # TOP TRACKS
    df_tracks_grouped = helper_get_spotify_tracks(df)

    # TOP ARTISTS
    df_artists_grouped = helper_get_spotify_artists(df)

    # TOP ALBUMS
    df_albums_grouped = df[['hours_played', 'artist', 'album']].copy()
    df_albums_grouped['album'] = df_albums_grouped['artist'] + " - " + df_albums_grouped['album']
    df_albums_grouped = df_albums_grouped.groupby(['album']).agg({'album': 'count', 'hours_played': 'sum'})
    df_albums_grouped.rename(columns={'album': '#'}, inplace=True)
    df_albums_grouped.sort_values(by=['#'], ascending=False, inplace=True)
    df_albums_grouped.reset_index(inplace=True)
    df_albums_grouped['hours_played'] = df_albums_grouped['hours_played'].round(2)

    # CREATE Tables
    filter_str_spotify = tab_spotify_alltime.text_input("Search Spotify")
    if filter_str_spotify:
        mask = df_tracks_grouped.map(lambda x: filter_str_spotify in str(x).lower()).any(axis=1)
        df_tracks_grouped = df_tracks_grouped[mask]
        mask = df_artists_grouped.map(lambda x: filter_str_spotify in str(x).lower()).any(axis=1)
        df_artists_grouped = df_artists_grouped[mask]
        mask = df_albums_grouped.map(lambda x: filter_str_spotify in str(x).lower()).any(axis=1)
        df_albums_grouped = df_albums_grouped[mask]

    tab_spotify_alltime.dataframe(df_tracks_grouped, width='stretch', hide_index=True)
    tab_spotify_alltime.dataframe(df_artists_grouped, width='stretch', hide_index=True)
    tab_spotify_alltime.dataframe(df_albums_grouped, width='stretch', hide_index=True)


def get_spotify_wrapped(df: pd.DataFrame) -> None:
    # List of years to filter for
    years = [2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016]

    # Create a dictionary to store the filtered DataFrames
    dfs_tracks = {}
    dfs_artists = {}

    # Loop through the years and create filtered DataFrames
    for year in years:
        dfs_tracks[f'{year}'] = df[df['time'].dt.year == year]
        dfs_tracks[f'{year}'] = helper_get_spotify_tracks(dfs_tracks[f'{year}'])
        dfs_artists[f'{year}'] = df[df['time'].dt.year == year]
        dfs_artists[f'{year}'] = helper_get_spotify_artists(dfs_artists[f'{year}'])

    filter_dropdown_spotify = tab_spotify_wrapped.selectbox("year", years)
    tab_spotify_wrapped.dataframe(dfs_tracks[str(filter_dropdown_spotify)], width='stretch', hide_index=True)
    tab_spotify_wrapped.dataframe(dfs_artists[str(filter_dropdown_spotify)], width='stretch', hide_index=True)

###########################################################


st.image("title_gold.png", width="stretch")

# create upload field
uploaded_file = st.file_uploader(
    "Hol dir deine Spotify-Daten, indem du dich am Rechner bei Spotify anmeldest und unter 'Konto' -> 'Account Privacy' deine 'Extended Streaming History' anforderst. Nach ein paar Tagen bekommst du eine zip-Datei (my_spotify_data.zip), die du hier hochladen kannst und die Analyse kann beginnen!",
    type=["zip"],
    accept_multiple_files=False
)

if uploaded_file is not None:
    with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
        # Liste aller Dateien im ZIP-Archiv
        file_list = zip_ref.namelist()

        # Filtere nur JSON-Dateien, die mit "Streaming_History_Audio" beginnen
        relevant_files = [
            f for f in file_list
            if os.path.basename(f).startswith('Streaming_History_Audio') and f.endswith('.json')
        ]

        if not relevant_files:
            st.warning("Keine passenden JSON-Dateien (Streaming_History_Audio*.json) gefunden.")

        else:
            df_spotify_data = get_spotify_data(relevant_files)

            # Create Tabs
            tab_spotify_alltime, tab_spotify_wrapped = st.tabs(["All-Time", "Wrapped"])

            get_spotify_all_time_data(df_spotify_data)
            get_spotify_wrapped(df_spotify_data)
