from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
import json
import os

# Configuración de OAuth
SCOPES = ['https://www.googleapis.com/auth/youtube.readonly']
TOKEN_FILE = 'token.json'
CLIENT_SECRET_FILE = 'client_secret.json'


def get_authenticated_service():
    """Autentica al usuario y devuelve un cliente de la API de YouTube."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                creds = None
        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    return build('youtube', 'v3', credentials=creds)


def get_playlists(youtube):
    """Obtiene todas las listas de reproducción del usuario autenticado."""
    playlists = []
    request = youtube.playlists().list(
        part='snippet',
        maxResults=50,
        mine=True
    )

    while request:
        response = request.execute()
        playlists.extend(response.get('items', []))
        request = youtube.playlists().list_next(request, response)

    return playlists


def get_videos_from_playlist(youtube, playlist_id):
    """Obtiene todos los videos de una lista de reproducción específica."""
    videos = []
    request = youtube.playlistItems().list(
        part='snippet',
        playlistId=playlist_id,
        maxResults=50
    )

    while request:
        response = request.execute()
        videos.extend(response.get('items', []))
        request = youtube.playlistItems().list_next(request, response)

    return videos


# === PROGRAMA PRINCIPAL ===
if __name__ == "__main__":
    youtube = get_authenticated_service()

    # Obtener todas las listas de reproducción
    playlists = get_playlists(youtube)
    print(f"Encontradas {len(playlists)} listas de reproducción.")

    result = {}

    # Procesar cada lista
    for pl in playlists:
        playlist_title = pl['snippet']['title']
        playlist_id = pl['id']

        print(f"Procesando: {playlist_title}")

        # Obtener videos de esta lista
        videos = get_videos_from_playlist(youtube, playlist_id)
        video_list = []

        for v in videos:
            snippet = v['snippet']
            title = snippet.get('title', 'Sin título')
            video_id = snippet.get('resourceId', {}).get('videoId')

            video_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else None

            thumbnails = snippet.get('thumbnails', {})
            thumbnail = None
            for quality in ['maxres', 'high', 'medium', 'default']:
                if quality in thumbnails:
                    thumbnail = thumbnails[quality]['url']
                    break

            video_published_at = snippet.get('publishedAt')

            video_list.append({
                'title': title,
                'url': video_url,
                'thumbnail': thumbnail,
                'publishedAt': video_published_at
            })

        result[playlist_id] = {
            'title': playlist_title,
            'videos': video_list
        }

    # Guardar en JSON
    json_filename = 'listas_youtube.json'
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Datos exportados a {json_filename}.")
