import json
import re
import difflib
from copy import deepcopy
import os
import requests
from datetime import datetime

# Cargar archivos JSON
print("Cargando archivos JSON...")
if os.path.exists('juegos.json'):
    with open('juegos.json', 'r', encoding='utf-8') as f:
        juegos = json.load(f)
else:
    print("juegos.json no encontrado. Cargando desde Gist...")
    # Reemplaza con la URL real
    gist_url = "https://gist.githubusercontent.com/usuario/ejemplo/raw/juegos.json"
    response = requests.get(gist_url)
    if response.status_code == 200:
        juegos = response.json()
    else:
        print("Error al cargar juegos desde Gist. Verifica la URL.")
        juegos = []

with open('listas_youtube.json', 'r', encoding='utf-8') as f:
    listas_youtube = json.load(f)

# Normalizar texto para comparación


def normalize_title(title):
    """Normaliza un título para facilitar la comparación."""
    if not title:
        return ""
    # Convertir a minúsculas
    title = title.lower()
    # Eliminar paréntesis y su contenido
    title = re.sub(r'\([^)]*\)', '', title)
    # Eliminar caracteres especiales
    title = re.sub(r'[:\-,;.&]', ' ', title)
    # Reemplazar múltiples espacios por uno solo
    title = re.sub(r'\s+', ' ', title)
    # Eliminar espacios al inicio y final
    title = title.strip()
    return title


# Preparar diccionario de listas de YouTube
youtube_listas = {}
all_yt_titles = []
for lista_id, info in listas_youtube.items():
    if 'title' in info and info['title']:
        title = info['title']
        normalized_title = normalize_title(title)
        youtube_listas[normalized_title] = {
            'id': lista_id,
            'title': title,
            'videos': info.get('videos', [])
        }
        all_yt_titles.append((title, lista_id))

print(f"Encontradas {len(youtube_listas)} listas de YouTube.")

# Función para encontrar todas las posibles coincidencias


def find_matches(game_title, youtube_listas, threshold=0.6):
    """Encuentra todas las posibles coincidencias para un título de juego."""
    normalized_game = normalize_title(game_title)

    # Buscar coincidencias
    matches = []
    for yt_norm, yt_info in youtube_listas.items():
        ratio = difflib.SequenceMatcher(None, normalized_game, yt_norm).ratio()
        matches.append((yt_info, ratio))

    # Ordenar por ratio de coincidencia (mayor a menor)
    matches.sort(key=lambda x: x[1], reverse=True)

    # Filtrar por umbral
    matches = [m for m in matches if m[1] >= threshold]

    return matches

# Función para encontrar los títulos más similares independientemente del ratio


def find_most_similar(game_title, all_titles, limit=10):
    """Encuentra los títulos más similares en una lista."""
    normalized_game = normalize_title(game_title)

    # Calcular similitud para todos los títulos
    similarities = []
    for title, lista_id in all_titles:
        normalized_title = normalize_title(title)
        ratio = difflib.SequenceMatcher(
            None, normalized_game, normalized_title).ratio()
        similarities.append((title, lista_id, ratio))

    # Ordenar por similitud (mayor a menor)
    similarities.sort(key=lambda x: x[2], reverse=True)

    # Devolver los top N
    return similarities[:limit]


# Definir la función buscar_caratula_en_wikipedia antes de su uso

def buscar_caratula_en_wikipedia(nombre_juego):
    """Busca la carátula de un juego en Wikipedia."""
    url = f"https://en.wikipedia.org/w/api.php"
    params = {
        'action': 'query',
        'format': 'json',
        'titles': nombre_juego,
        'prop': 'pageimages',
        'pithumbsize': 500
    }
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            pages = data.get('query', {}).get('pages', {})
            for page_id, page_data in pages.items():
                if 'thumbnail' in page_data:
                    return page_data['thumbnail']['source']
    except Exception as e:
        print(f"Error al buscar carátula en Wikipedia: {e}")
    return None


def buscar_caratula_en_giant_bomb(nombre_juego):
    """Busca la carátula de un juego en la API de Giant Bomb."""
    api_key = "fb38062e53df7ec7d1cafcdf152021e4e51d9b4f"  # Reemplaza con tu clave de API de Giant Bomb
    url = "https://www.giantbomb.com/api/search/"
    params = {
        'api_key': api_key,
        'format': 'json',
        'query': nombre_juego,
        'resources': 'game'
    }
    headers = {
        'User-Agent': 'GameCoverFetcher/1.0'
    }
    try:
        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            if results:
                # Tomar la primera carátula disponible
                for result in results:
                    if 'image' in result and 'super_url' in result['image']:
                        return result['image']['super_url']
    except Exception as e:
        print(f"Error al buscar carátula en Giant Bomb: {e}")
    return None


# Añadir videos a cada juego
juegos_actualizados = []
coincidencias_auto = 0
coincidencias_manual = 0
coincidencias_previas = 0
sin_coincidencias = 0

print("\nAsignando videos a juegos desde listas de YouTube...\n")

for i, juego in enumerate(juegos):
    nombre_juego = juego.get('name', '')
    if not nombre_juego:
        juegos_actualizados.append(juego)
        continue

    # Crear una copia del juego para modificar
    juego_actualizado = deepcopy(juego)

    # Comprobar si ya tiene un ID de lista asignado previamente
    if juego.get('lista_youtube') and juego['lista_youtube'].get('id'):
        lista_id = juego['lista_youtube']['id']
        if lista_id in listas_youtube:
            # La lista ya está asignada y sigue existiendo, conservarla
            lista_info = listas_youtube[lista_id]
            juego_actualizado['videos'] = lista_info.get('videos', [])
            juego_actualizado['lista_youtube'] = {
                'id': lista_id,
                'title': lista_info.get('title', '')
            }

            # Asignar fecha si no tiene 'played'
            if not juego_actualizado.get('played'):
                videos = lista_info.get('videos', [])
                if videos:
                    # Obtener la fecha más reciente
                    fechas = [
                        datetime.strptime(
                            v.get('publishedAt', ''), '%Y-%m-%dT%H:%M:%SZ')
                        for v in videos if v.get('publishedAt')
                    ]
                    if fechas:
                        fecha_reciente = max(fechas)
                        juego_actualizado['played'] = fecha_reciente.strftime(
                            '%Y-%m')
                    else:
                        print(
                            f"⚠️ No se encontraron fechas válidas en los videos de la lista '{lista_info.get('title', '')}'.")
            coincidencias_previas += 1
            print(
                f"♻️ Lista previamente asignada para '{nombre_juego}' → '{lista_info.get('title', '')}'")
            juegos_actualizados.append(juego_actualizado)
            continue

    print(f"Procesando juego: '{nombre_juego}'")

    # Encontrar todas las posibles coincidencias
    matches = find_matches(nombre_juego, youtube_listas)

    if matches:
        # Tomar la coincidencia con el ratio más alto
        best_match, ratio = matches[0]

        # Si la coincidencia es alta (>0.9), asignar automáticamente
        if ratio > 0.9:
            juego_actualizado['videos'] = best_match['videos']
            juego_actualizado['lista_youtube'] = {
                'id': best_match['id'],
                'title': best_match['title']
            }
            coincidencias_auto += 1
            print(
                f"✅ Coincidencia fuerte ({ratio:.2f}): '{nombre_juego}' ↔ '{best_match['title']}'")

        # Si la coincidencia es moderada, pedir confirmación
        else:
            print(f"\nPosibles coincidencias para '{nombre_juego}':")

            # Mostrar las coincidencias con mejor ratio
            for idx, (match_info, match_ratio) in enumerate(matches[:5], 1):
                print(
                    f"{idx}. '{match_info['title']}' (similitud: {match_ratio:.2f})")

            # Mostrar otras opciones similares
            most_similar = find_most_similar(nombre_juego, all_yt_titles, 20)

            print("\nOtras listas que podrían coincidir:")
            for idx, (title, lista_id, ratio) in enumerate(most_similar, 20):
                # Mostrar hasta 10 opciones adicionales (total 15)
                if idx <= 15:
                    print(f"{idx}. '{title}' (similitud: {ratio:.2f})")

            while True:
                seleccion = input(
                    f"\nSelecciona una lista (1-15) o ingresa 'n' para ninguna: ")

                if seleccion.lower() == 'n':
                    # No asignar ninguna lista
                    juego_actualizado['videos'] = []
                    if 'lista_youtube' in juego_actualizado:
                        del juego_actualizado['lista_youtube']
                    sin_coincidencias += 1
                    print("❌ Ninguna lista asignada.")
                    break
                else:
                    try:
                        num = int(seleccion)
                        if 1 <= num <= 5 and num <= len(matches):
                            # Selección de las mejores coincidencias
                            selected_match, _ = matches[num-1]
                            juego_actualizado['videos'] = selected_match['videos']
                            juego_actualizado['lista_youtube'] = {
                                'id': selected_match['id'],
                                'title': selected_match['title']
                            }
                            coincidencias_manual += 1
                            print(
                                f"✅ Lista asignada: '{selected_match['title']}'")
                            break
                        elif 6 <= num <= 25 and (num-6) < len(most_similar):
                            # Selección de las listas más similares
                            _, lista_id, _ = most_similar[num-6]
                            lista_info = listas_youtube[lista_id]
                            juego_actualizado['videos'] = lista_info.get(
                                'videos', [])
                            juego_actualizado['lista_youtube'] = {
                                'id': lista_id,
                                'title': lista_info.get('title', '')
                            }
                            coincidencias_manual += 1
                            print(
                                f"✅ Lista asignada: '{lista_info.get('title', '')}'")
                            break
                        else:
                            print(f"Por favor, elige un número válido entre 1 y 15")
                    except ValueError:
                        print("Entrada no válida. Ingresa un número o 'n'.")

    else:
        print(f"❌ No se encontró ninguna coincidencia para '{nombre_juego}'")
        most_similar = find_most_similar(nombre_juego, all_yt_titles, 20)

        print("\nLas listas más similares son:")
        for idx, (title, lista_id, ratio) in enumerate(most_similar, 1):
            print(f"{idx}. '{title}' (similitud: {ratio:.2f})")

        while True:
            seleccion = input(
                f"\nSelecciona una lista (1-15) o ingresa 'n' para ninguna: ")

            if seleccion.lower() == 'n':
                # No asignar ninguna lista
                juego_actualizado['videos'] = []
                if 'lista_youtube' in juego_actualizado:
                    del juego_actualizado['lista_youtube']
                sin_coincidencias += 1
                print("❌ Ninguna lista asignada.")
                break
            else:
                try:
                    num = int(seleccion)
                    if 1 <= num <= len(most_similar):
                        _, lista_id, _ = most_similar[num-1]
                        lista_info = listas_youtube[lista_id]
                        juego_actualizado['videos'] = lista_info.get(
                            'videos', [])
                        juego_actualizado['lista_youtube'] = {
                            'id': lista_id,
                            'title': lista_info.get('title', '')
                        }
                        coincidencias_manual += 1
                        print(
                            f"✅ Lista asignada: '{lista_info.get('title', '')}'")
                        break
                    else:
                        print(
                            f"Por favor, elige un número entre 1 y {len(most_similar)}")
                except ValueError:
                    print("Entrada no válida. Ingresa un número o 'n'.")

    # Asegurar que se busque la carátula si no está definida
    if 'cover' not in juego_actualizado or not juego_actualizado['cover']:
        print(f"Buscando carátula para el juego: {nombre_juego}")
        caratula = buscar_caratula_en_wikipedia(nombre_juego)
        if not caratula:
            print(
                f"No se encontró carátula en Wikipedia para: {nombre_juego}. Intentando en Giant Bomb...")
            caratula = buscar_caratula_en_giant_bomb(nombre_juego)
        if caratula:
            print(f"Carátula encontrada para {nombre_juego}: {caratula}")
        else:
            print(
                f"No se encontró carátula para {nombre_juego}. Usando carátula predeterminada.")
        juego_actualizado['cover'] = caratula or 'https://via.placeholder.com/220x250?text=Sin+Caratula'

    juegos_actualizados.append(juego_actualizado)

# Cargar listas ignoradas previamente
IGNORADAS_FILE = 'listas_ignoradas.json'
try:
    with open(IGNORADAS_FILE, 'r', encoding='utf-8') as f:
        listas_ignoradas = set(json.load(f))
except (FileNotFoundError, json.JSONDecodeError):
    listas_ignoradas = set()

# Filtrar listas no asignadas usando la clave del diccionario como ID
asignadas = {juego.get('lista_youtube', {}).get('id')
             for juego in juegos_actualizados}
no_asignadas = [info for lista_id, info in listas_youtube.items(
) if lista_id not in asignadas and lista_id not in listas_ignoradas]

# Asegurarse de que cada lista tenga su ID asignado desde la clave del diccionario
for lista_id, info in listas_youtube.items():
    info['id'] = lista_id

if no_asignadas:
    print(
        f"\nSe encontraron {len(no_asignadas)} listas no asignadas. Preguntando una por una...")
    for lista in no_asignadas:
        print(f"\nLista: {lista['title']}")
        while True:
            respuesta = input(
                "¿Deseas añadir esta lista como un nuevo juego? (s/n): ").strip().lower()
            if respuesta == 's':
                nuevo_juego = {
                    'name': lista['title'],
                    'lista_youtube': {
                        'id': lista['id'],
                        'title': lista['title']
                    },
                    'videos': lista.get('videos', [])
                }
                juegos_actualizados.append(nuevo_juego)
                print(f"✅ Lista añadida: {lista['title']}")
                break
            elif respuesta == 'n':
                listas_ignoradas.add(lista['id'])
                print(f"❌ Lista ignorada: {lista['title']}")
                break
            else:
                print("Por favor, responde 's' o 'n'.")

# Guardar listas ignoradas
with open(IGNORADAS_FILE, 'w', encoding='utf-8') as f:
    json.dump(list(listas_ignoradas), f, ensure_ascii=False, indent=4)

# Guardar el archivo JSON actualizado
with open('juegos.json', 'w', encoding='utf-8') as f:
    json.dump(juegos_actualizados, f, ensure_ascii=False, indent=4)

print(f"\n--- Resumen Final ---")
print(f"Total de juegos procesados: {len(juegos)}")
print(
    f"Coincidencias conservadas de ejecuciones previas: {coincidencias_previas}")
print(f"Coincidencias automáticas (ratio > 0.9): {coincidencias_auto}")
print(f"Coincidencias asignadas manualmente: {coincidencias_manual}")
print(f"Juegos sin coincidencia: {sin_coincidencias}")
print(
    f"Listas añadidas como nuevos juegos: {len(no_asignadas) - len(listas_ignoradas)}")
print(f"Listas ignoradas: {len(listas_ignoradas)}")
print(f"\nArchivo actualizado guardado como: juegos.json")
