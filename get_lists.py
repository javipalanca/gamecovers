import requests
import json
import os
import time

# ==== CONFIGURACIÓN ====
# Archivo para almacenar tokens
TOKEN_FILE = 'youtube_tokens.json'
# Ir a: https://developers.google.com/oauthplayground/
# En el panel izquierdo, busca "YouTube Data API v3"
# Selecciona el scope https://www.googleapis.com/auth/youtube.readonly
# Haz clic en "Authorize APIs"
# Sigue el proceso de autorización
# Obtén los tokens:
# En el paso 2, haz clic en "Exchange authorization code for tokens"
# En el panel derecho, verás tanto el access_token como el refresh_token
# Copia estos valores cuando el script te los solicite

# Tus credenciales de OAuth (reemplaza con las tuyas)
with open("client_tokens.json", 'r') as f:
    credentials = json.load(f)
    CLIENT_ID = credentials['installed']['client_id']
    CLIENT_SECRET = credentials['installed']['client_secret']

def load_tokens():
    """Carga los tokens desde el archivo."""
    try:
        with open(TOKEN_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_tokens(tokens):
    """Guarda los tokens en el archivo."""
    with open(TOKEN_FILE, 'w') as f:
        json.dump(tokens, f)

def refresh_access_token(refresh_token):
    """Obtiene un nuevo access_token usando el refresh_token."""
    url = 'https://oauth2.googleapis.com/token'
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token'
    }
    
    response = requests.post(url, data=data)
    if response.status_code == 200:
        token_data = response.json()
        return {
            'access_token': token_data['access_token'],
            'expires_at': int(time.time()) + token_data['expires_in'],
            'refresh_token': refresh_token  # Mantener el mismo refresh_token
        }
    else:
        print(f"Error al refrescar el token: {response.text}")
        return None

def get_access_token():
    """Obtiene un access_token válido."""
    tokens = load_tokens()
    
    # Si no tenemos tokens o falta el refresh_token
    if not tokens or 'refresh_token' not in tokens:
        print("\nNo se encontró un refresh_token válido.")
        print("Por favor, obtén un refresh_token visitando:")
        print("https://developers.google.com/oauthplayground/")
        
        # Opción manual: solicitar tokens al usuario
        refresh_token = input("\nIngresa el refresh_token: ")
        access_token = input("Ingresa el access_token actual: ")
        
        if refresh_token and access_token:
            tokens = {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'expires_at': int(time.time()) + 3600  # Asumimos 1 hora de validez
            }
            save_tokens(tokens)
        else:
            return None
    
    # Si el access_token ha expirado o falta
    current_time = int(time.time())
    if 'expires_at' not in tokens or tokens['expires_at'] <= current_time + 30:
        print("El access_token ha expirado o está por expirar. Obteniendo uno nuevo...")
        new_tokens = refresh_access_token(tokens['refresh_token'])
        if new_tokens:
            save_tokens(new_tokens)
            return new_tokens['access_token']
        else:
            # Si falla la renovación, usamos el token existente como último recurso
            return tokens.get('access_token')
    
    return tokens['access_token']

def get_playlists(access_token):
    # Código existente sin cambios
    playlists = []
    url = 'https://www.googleapis.com/youtube/v3/playlists'
    params = {
        'part': 'snippet',
        'maxResults': 50,
        'mine': True
    }
    headers = {'Authorization': f'Bearer {access_token}'}

    while True:
        res = requests.get(url, params=params, headers=headers)
        data = res.json()
        
        if 'error' in data:
            print(f"Error: {data['error']['message']}")
            break
            
        if 'items' in data:
            playlists.extend(data['items'])

        if 'nextPageToken' in data:
            params['pageToken'] = data['nextPageToken']
        else:
            break

    return playlists

def get_videos_from_playlist(access_token, playlist_id):
    # Código existente sin cambios
    videos = []
    url = 'https://www.googleapis.com/youtube/v3/playlistItems'
    params = {
        'part': 'snippet',
        'playlistId': playlist_id,
        'maxResults': 50
    }
    headers = {'Authorization': f'Bearer {access_token}'}

    while True:
        res = requests.get(url, params=params, headers=headers)
        data = res.json()
        
        if 'error' in data:
            print(f"Error en playlist {playlist_id}: {data['error']['message']}")
            break
            
        if 'items' in data:
            videos.extend(data['items'])

        if 'nextPageToken' in data:
            params['pageToken'] = data['nextPageToken']
        else:
            break

    return videos

# === PROGRAMA PRINCIPAL ===
# Obtener un token válido
ACCESS_TOKEN = get_access_token()
if not ACCESS_TOKEN:
    print("No se pudo obtener un access_token válido. Saliendo...")
    exit(1)

print(f"Token válido obtenido: {ACCESS_TOKEN[:20]}...")

# Estructura para almacenar resultados
result = {}

# Obtener todas las listas de reproducción
playlists = get_playlists(ACCESS_TOKEN)
print(f"Encontradas {len(playlists)} listas de reproducción.")

# Procesar cada lista
for pl in playlists:
    playlist_title = pl['snippet']['title']
    playlist_id = pl['id']
    
    print(f"Procesando: {playlist_title}")
    
    # Obtener videos de esta lista
    videos = get_videos_from_playlist(ACCESS_TOKEN, playlist_id)
    video_list = []
    
    # Procesar cada video
    for v in videos:
        snippet = v['snippet']
        title = snippet.get('title', 'Sin título')
        video_id = snippet.get('resourceId', {}).get('videoId')
        
        # URLs
        video_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else None
        
        # Miniaturas (de mayor a menor calidad)
        thumbnails = snippet.get('thumbnails', {})
        thumbnail = None
        for quality in ['maxres', 'high', 'medium', 'default']:
            if quality in thumbnails:
                thumbnail = thumbnails[quality]['url']
                break
        
        # Añadir a la lista de videos
        video_list.append({
            'title': title,
            'url': video_url,
            'thumbnail': thumbnail
        })
    
    # Añadir esta lista y sus videos al resultado
    result[playlist_id] = {
        'title': playlist_title,
        'videos': video_list
    }

# Guardar en JSON
json_filename = 'listas_youtube.json'
with open(json_filename, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"Datos exportados a {json_filename}.")