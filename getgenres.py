import json
import requests
import time
import re
import ollama
from collections import defaultdict
from fuzzywuzzy import fuzz
import os
# Configuración de Ollama
OLLAMA = os.getenv("OLLAMA_HOST", "http://localhost:11434")


messages = [{"role": "system",
             "content": "You are a video game expert. I need you to determine the genres of the game."}]

client = ollama.Client(host=OLLAMA, verify=False)


# Función para consultar al LLM usando la biblioteca ollama


def query_llm(prompt):
    try:
        # Usar la biblioteca ollama en lugar de solicitudes HTTP directas
        response = client.chat(
            model='llama3.3:70b',
            messages=[{"role": "user", "content": prompt}],
            options={
                'temperature': 0.1
            }
        )

        # Extraer la respuesta
        if response:
            r = response.message.content.strip()
            messages.append({"role": "assistant", "content": r})
            return r
        else:
            print(f"  ⚠️ Error del LLM: respuesta vacía o inválida")
            return None
    except Exception as e:
        print(f"  ⚠️ Error consultando LLM: {e}")
        return None

# Función para obtener el género desde RAWG API


def get_genre_from_rawg(game_name):
    try:
        # Limpieza básica del nombre del juego
        clean_name = game_name.split(":")[0] if ":" in game_name else game_name
        clean_name = clean_name.split("(")[0].strip()

        # URL base de la API de RAWG - versión sin autenticación
        base_url = "https://api.rawg.io/api/games"

        # Construir parámetros de búsqueda
        params = {
            "search": clean_name,
            "page_size": 10
        }

        # Realizar solicitud a la API
        response = requests.get(base_url, params=params)

        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])

            if results:
                # Intentar encontrar una coincidencia exacta o similar
                best_match = None
                highest_score = 0

                for game in results:
                    # Usar fuzzy matching para encontrar la mejor coincidencia
                    score = fuzz.ratio(
                        game['name'].lower(), clean_name.lower())
                    if score > highest_score:
                        highest_score = score
                        best_match = game

                # Si tenemos una coincidencia razonable (más del 80% de similitud)
                if best_match and highest_score > 80 and 'genres' in best_match and best_match['genres']:
                    genres = [genre['name'] for genre in best_match['genres']]
                    return genres, best_match['name'], highest_score

                # Si no hay una coincidencia fuerte pero hay resultados con géneros
                for game in results:
                    if 'genres' in game and game['genres']:
                        genres = [genre['name'] for genre in game['genres']]
                        return genres, game['name'], fuzz.ratio(game['name'].lower(), clean_name.lower())

    except Exception as e:
        print(f"  ✗ Error consultando API RAWG para {game_name}: {e}")

    return [], "", 0

# Función para obtener géneros según reglas predefinidas


def get_rule_based_genres(game_name, editor=None, year=None):
    name_lower = game_name.lower()

    rules_matches = []

    # Adventure/Point and Click
    point_and_click_keywords = ["monkey island", "day of the tentacle", "grim fandango", "sam & max",
                                "myst", "broken sword", "kyrandia", "simon the sorcerer", "leisure suit larry",
                                "kings quest", "space quest", "police quest", "gabriel knight",
                                "toonstruck", "deponia", "runaway", "edna", "machinarium", "thimbleweed",
                                "full throttle", "indiana jones", "hollywood monsters", "goblins",
                                "discworld", "syberia", "longest journey", "feeble files", "dig",
                                "beneath a steel sky", "primordia", "whispered world", "raw danger",
                                "nancy drew", "sanitarium", "gibbous"]

    for keyword in point_and_click_keywords:
        if keyword in name_lower:
            rules_matches.append(
                f"Keyword match: '{keyword}' found in game name. Suggests Point-and-Click/Adventure.")
            return ["Point-and-Click", "Adventure"], rules_matches

    # First Person Shooters
    fps_keywords = ["doom", "quake", "wolfenstein", "duke nukem", "half-life", "dark forces",
                    "jedi knight", "serious sam", "painkiller", "bioshock", "borderlands",
                    "call of duty", "battlefield", "medal of honor", "halo", "counter-strike",
                    "crysis", "rainbow six", "overwatch", "titanfall", "prey"]

    for keyword in fps_keywords:
        if keyword in name_lower:
            rules_matches.append(
                f"Keyword match: '{keyword}' found in game name. Suggests First-Person Shooter.")
            return ["First-Person Shooter", "Action"], rules_matches

    # Third Person Shooters
    tps_keywords = ["uncharted", "gears of war", "max payne", "spec ops",
                    "tomb raider", "just cause", "mafia", "ghost recon"]

    for keyword in tps_keywords:
        if keyword in name_lower:
            rules_matches.append(
                f"Keyword match: '{keyword}' found in game name. Suggests Third-Person Shooter.")
            return ["Third-Person Shooter", "Action"], rules_matches

    # RPGs
    rpg_keywords = ["mass effect", "dragon age", "fallout", "elder scrolls", "baldur",
                    "final fantasy", "witcher", "gothic", "kingdom come", "divinity",
                    "pillars of eternity", "deus ex", "skyrim", "oblivion", "morrowind",
                    "dragon quest", "dark souls", "persona", "chrono", "ultima", "fable",
                    "planescape", "icewind dale", "neverwinter", "knights of the old republic"]

    for keyword in rpg_keywords:
        if keyword in name_lower:
            rules_matches.append(
                f"Keyword match: '{keyword}' found in game name. Suggests Role-Playing (RPG).")
            return ["Role-Playing (RPG)"], rules_matches

    # Más reglas basadas en editor/desarrollador
    if editor:
        editor_lower = editor.lower()

        # Adventure game studios
        adventure_studios = ["lucasarts", "sierra", "daedalic", "pendulo", "revolution software",
                             "telltale", "wadjet eye", "amanita", "microids", "adventure soft"]

        for studio in adventure_studios:
            if studio in editor_lower:
                rules_matches.append(
                    f"Developer/publisher match: '{studio}' is known for adventure games.")
                return ["Adventure", "Point-and-Click"], rules_matches

        # RPG studios
        rpg_studios = ["bioware", "obsidian", "bethesda", "cd projekt", "square", "enix",
                       "black isle", "inxile", "troika", "larian"]

        for studio in rpg_studios:
            if studio in editor_lower:
                rules_matches.append(
                    f"Developer/publisher match: '{studio}' is known for RPGs.")
                return ["Role-Playing (RPG)"], rules_matches

    # Reglas basadas en año
    if year:
        try:
            year_num = int(re.search(r'\b(19\d{2}|20\d{2})\b', str(year)).group(
                1)) if re.search(r'\b(19\d{2}|20\d{2})\b', str(year)) else 0

            if 1980 <= year_num <= 1995:
                rules_matches.append(
                    f"Game from {year_num}, a period when adventure games were popular.")
                if "quest" in name_lower or "larry" in name_lower:
                    return ["Adventure", "Point-and-Click"], rules_matches
        except:
            pass

    return [], rules_matches

# Función para analizar todas las fuentes y consultar al LLM para determinar el género final


def determine_game_genres(game_name, editor=None, year=None):
    sources_info = {}
    all_genres = set()

    # 1. Buscar en RAWG
    rawg_genres, match_name, match_score = get_genre_from_rawg(game_name)
    if rawg_genres:
        sources_info["rawg"] = {
            "genres": rawg_genres,
            "match_name": match_name,
            "match_score": match_score
        }
        all_genres.update(rawg_genres)
        print(
            f"  ✓ RAWG ({match_name}, score: {match_score}): {', '.join(rawg_genres)}")

    # 2. Aplicar reglas basadas en nombre/editor/año
    rule_genres, rule_matches = get_rule_based_genres(game_name, editor, year)
    if rule_genres:
        sources_info["rules"] = {
            "genres": rule_genres,
            "matches": rule_matches
        }
        all_genres.update(rule_genres)
        print(f"  ✓ Reglas: {', '.join(rule_genres)}")

    # 3. Preparar prompt para el LLM
    prompt = f"""You are a video game expert. I need you to determine the genres of the game "{game_name}".

Information about the game:
- Name: {game_name}
- Developer/Publisher: {editor or 'Unknown'}
- Year: {year or 'Unknown'}

I have gathered information from different sources:
"""

    if "rawg" in sources_info:
        prompt += f"\nRAWG database suggests these genres: {', '.join(sources_info['rawg']['genres'])}"
        prompt += f"\nMatch found: {sources_info['rawg']['match_name']} (similarity score: {sources_info['rawg']['match_score']})"
    else:
        prompt += "\nNo information found on RAWG database."

    if "rules" in sources_info and sources_info['rules']['matches']:
        prompt += "\n\nRule-based analysis:"
        for match in sources_info['rules']['matches']:
            prompt += f"\n- {match}"
    else:
        prompt += "\n\nNo rule-based matches found."

    prompt += """

Based on all available information AND YOUR OWN KNOWLEDGE about video games, please determine the most appropriate genres for this game.
Use your expertise to evaluate and possibly correct the information provided by other sources.
Consider the game's time period, developer tendencies, and franchise history if applicable.

Present your answer as a JSON array of strings, with each string representing one genre.
Only include well-established video game genres.
The array should have between 1 and 3 genres, ordered by relevance.
For example: ["Role-Playing (RPG)", "Action"]

Response (just the JSON array):"""

    # 4. Consultar al LLM
    print(f"  → Consultando al LLM...")
    llm_response = query_llm(prompt)

    if llm_response:
        try:
            # Intentar extraer el array JSON de la respuesta
            json_match = re.search(r'\[.*?\]', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                final_genres = json.loads(json_str)
                print(f"  ✓ LLM determinó: {', '.join(final_genres)}")
                return final_genres
            else:
                print(
                    f"  ⚠️ No se pudo extraer JSON de la respuesta LLM: {llm_response}")
        except Exception as e:
            print(f"  ⚠️ Error procesando respuesta LLM: {e}")
            print(f"  ⚠️ Respuesta original: {llm_response}")

    # Fallback si el LLM falla: usar todas las fuentes combinadas
    if all_genres:
        # Limitar a los 2-3 géneros más comunes entre todas las fuentes
        genres_list = list(all_genres)
        return genres_list[:min(3, len(genres_list))]
    else:
        # Último recurso: género genérico
        return ["Action", "Adventure"]


def normalizar_nombre(nombre):
    """Normaliza el nombre del juego para mejorar las búsquedas."""
    nombre = nombre.lower()
    # Eliminar paréntesis y su contenido
    nombre = re.sub(r'\([^)]*\)', '', nombre)
    # Eliminar caracteres especiales
    nombre = re.sub(r'[:\-,;.&]', ' ', nombre)
    nombre = re.sub(r'\s+', ' ', nombre).strip()  # Eliminar espacios extra
    return nombre


def traducir_nombre(nombre):
    """Traduce el nombre del juego al inglés utilizando el LLM."""
    prompt = f"""Convierte el siguiente título de videojuego al original en inglés: '{nombre}'. 
    Devuelve solo el título traducido sin explicaciones ni contexto adicional.
    Si no estás seguro, devuelve el título original sin cambios.
    Debes devolver el título que haga más sencillo encontrar la carátula del juego en inglés."""
    try:
        traduccion = query_llm(prompt)
        if traduccion:
            print(f"  ✓ Traducción del LLM: {traduccion}")
            return traduccion
        else:
            print("⚠️ No se pudo obtener una traducción del LLM.")
            return nombre
    except Exception as e:
        print(f"Error al traducir el nombre con el LLM: {e}")
        return nombre


def actualizar_generos_si_no_existen(juego, game_name, editor=None, year=None):
    """Actualiza los géneros de un juego solo si no están ya asignados."""
    if 'genres' not in juego or not juego['genres']:
        print(f"Buscando géneros para el juego: {game_name}")
        nuevos_generos = determine_game_genres(game_name, editor, year)
        if nuevos_generos:
            print(f"Géneros encontrados: {nuevos_generos}")
            juego['genres'] = nuevos_generos
        else:
            print(f"No se encontraron géneros para {game_name}.")


# Cargar el JSON de juegos
with open("juegos.json", "r", encoding="utf-8") as file:
    games = json.load(file)

# Crear una copia con información de género
games_with_genres = []
genre_stats = defaultdict(int)

# Procesar cada juego
for i, game in enumerate(games):
    print(
        f"Procesando {i+1}/{len(games)}: {game.get('name', 'Unknown Game Name')}")

    # Añadir un retraso para no sobrecargar las APIs
    # if i > 0:
    #    # Aumentamos el tiempo de espera por las múltiples solicitudes
    #    time.sleep(2)

    # Asegurarse de que tenemos los campos necesarios
    game_name = game.get("name", "")
    if not game_name:
        print(f"  ⚠️ Juego en posición {i+1} sin nombre, saltando...")
        continue

    # Determinar géneros usando todas las fuentes y el LLM
    # genres = determine_game_genres(
    #    game_name, game.get("editor"), game.get("year"))
    actualizar_generos_si_no_existen(game, game.get(
        'name', ''), game.get('editor'), game.get('year'))

    # Añadir el género al objeto del juego
    game_with_genre = game.copy()
    genres = game_with_genre["genres"]

    # Actualizar estadísticas
    for genre in genres:
        genre_stats[genre] += 1

    games_with_genres.append(game_with_genre)
    print(f"  ✅ Géneros finales: {', '.join(genres)}")
    print("-" * 60)

# Guardar el nuevo JSON con información de género
with open("juegos_con_generos.json", "w", encoding="utf-8") as file:
    json.dump(games_with_genres, file, ensure_ascii=False, indent=4)

# Ordenar y mostrar estadísticas de géneros
sorted_genres = sorted(genre_stats.items(), key=lambda x: x[1], reverse=True)

print("\nEstadísticas de géneros:")
for genre, count in sorted_genres:
    print(f"{genre}: {count} juegos")

print(
    f"\nProcesamiento completado. Se han procesado {len(games_with_genres)} juegos.")
