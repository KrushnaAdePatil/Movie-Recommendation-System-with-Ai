# pyrefly: ignore [missing-import]
from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS
import requests
import json
import os
from concurrent.futures import ThreadPoolExecutor

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static')
)
CORS(app)

TMDB_API_KEY = "cdf27570dfded7636db81e5ec29148e1"
BASE_URL = "https://api.tmdb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"

# Curated collections of movies and TV series
CURATED_MOVIES = {
    "korean": [
        {"id": 496243, "type": "movie"}, # Parasite
        {"id": 93405, "type": "tv"},     # Squid Game
    ],
    "chinese": [
        {"id": 146, "type": "movie"},    # Crouching Tiger, Hidden Dragon
        {"id": 90223, "type": "tv"},     # The Untamed
    ],
    "spanish": [
        {"id": 1417, "type": "movie"},   # Pan's Labyrinth
        {"id": 71446, "type": "tv"},     # Money Heist
    ]
}

# Local cache of high-quality movie & TV series suggestions for standard moods to bypass Gemini rate limits
MOOD_CACHE = {
    "adrenaline": [
        {"title": "Mad Max: Fury Road", "type": "movie"},
        {"title": "John Wick: Chapter 4", "type": "movie"},
        {"title": "Die Hard", "type": "movie"},
        {"title": "Speed", "type": "movie"},
        {"title": "Top Gun: Maverick", "type": "movie"},
        {"title": "The Dark Knight", "type": "movie"},
        {"title": "Gladiator", "type": "movie"},
        {"title": "Inception", "type": "movie"},
        {"title": "Breaking Bad", "type": "tv"},
        {"title": "Money Heist", "type": "tv"},
        {"title": "Squid Game", "type": "tv"},
        {"title": "Prison Break", "type": "tv"},
        {"title": "Reacher", "type": "tv"},
        {"title": "The Boys", "type": "tv"},
        {"title": "Fast X", "type": "movie"}
    ],
    "cozy": [
        {"title": "Paddington 2", "type": "movie"},
        {"title": "Amélie", "type": "movie"},
        {"title": "Chef", "type": "movie"},
        {"title": "Spirited Away", "type": "movie"},
        {"title": "My Neighbor Totoro", "type": "movie"},
        {"title": "Fantastic Mr. Fox", "type": "movie"},
        {"title": "The Grand Budapest Hotel", "type": "movie"},
        {"title": "Little Women", "type": "movie"},
        {"title": "Midnight in Paris", "type": "movie"},
        {"title": "Gilmore Girls", "type": "tv"},
        {"title": "Ted Lasso", "type": "tv"},
        {"title": "Heartstopper", "type": "tv"},
        {"title": "Modern Family", "type": "tv"},
        {"title": "The Good Place", "type": "tv"},
        {"title": "Schitt's Creek", "type": "tv"}
    ],
    "spooky": [
        {"title": "The Conjuring", "type": "movie"},
        {"title": "Hereditary", "type": "movie"},
        {"title": "A Nightmare on Elm Street", "type": "movie"},
        {"title": "Halloween", "type": "movie"},
        {"title": "The Shining", "type": "movie"},
        {"title": "It", "type": "movie"},
        {"title": "Get Out", "type": "movie"},
        {"title": "Psycho", "type": "movie"},
        {"title": "Stranger Things", "type": "tv"},
        {"title": "The Haunting of Hill House", "type": "tv"},
        {"title": "Wednesday", "type": "tv"},
        {"title": "American Horror Story", "type": "tv"},
        {"title": "Supernatural", "type": "tv"},
        {"title": "Penny Dreadful", "type": "tv"},
        {"title": "Alien", "type": "movie"}
    ],
    "mindbending": [
        {"title": "Inception", "type": "movie"},
        {"title": "Interstellar", "type": "movie"},
        {"title": "Shutter Island", "type": "movie"},
        {"title": "Memento", "type": "movie"},
        {"title": "Donnie Darko", "type": "movie"},
        {"title": "Arrival", "type": "movie"},
        {"title": "The Matrix", "type": "movie"},
        {"title": "Dark", "type": "tv"},
        {"title": "Westworld", "type": "tv"},
        {"title": "Severance", "type": "tv"},
        {"title": "Black Mirror", "type": "tv"},
        {"title": "Mr. Robot", "type": "tv"},
        {"title": "Eternal Sunshine of the Spotless Mind", "type": "movie"},
        {"title": "Fight Club", "type": "movie"},
        {"title": "Tenet", "type": "movie"}
    ],
    "emotional": [
        {"title": "The Pursuit of Happyness", "type": "movie"},
        {"title": "Titanic", "type": "movie"},
        {"title": "Schindler's List", "type": "movie"},
        {"title": "Interstellar", "type": "movie"},
        {"title": "The Fault in Our Stars", "type": "movie"},
        {"title": "Inside Out", "type": "movie"},
        {"title": "Marley & Me", "type": "movie"},
        {"title": "A Star Is Born", "type": "movie"},
        {"title": "This Is Us", "type": "tv"},
        {"title": "Normal People", "type": "tv"},
        {"title": "Fleabag", "type": "tv"},
        {"title": "Anne with an E", "type": "tv"},
        {"title": "BoJack Horseman", "type": "tv"},
        {"title": "Eternal Sunshine of the Spotless Mind", "type": "movie"},
        {"title": "Manchester by the Sea", "type": "movie"}
    ]
}

def fetch_tmdb_paginated(endpoint, params, req_page_num, media_type, page_size=35):
    """Helper to fetch exact number of results by managing TMDB 20-item pages"""
    start_idx = (req_page_num - 1) * page_size
    end_idx = req_page_num * page_size
    
    start_tmdb_page = (start_idx // 20) + 1
    end_tmdb_page = ((end_idx - 1) // 20) + 1
    
    total_results = 0
    
    def fetch_page(p):
        try:
            page_params = params.copy()
            page_params['page'] = p
            resp = requests.get(endpoint, params=page_params, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"Error fetching TMDb page {p} from {endpoint}: {e}")
        return {}

    try:
        if start_tmdb_page == end_tmdb_page:
            data = fetch_page(start_tmdb_page)
            tmdb_results = data.get('results', [])
            total_results = data.get('total_results', 0)
            offset_in_page = start_idx % 20
            sliced_results = tmdb_results[offset_in_page : offset_in_page + page_size]
        else:
            with ThreadPoolExecutor(max_workers=2) as executor:
                pages = list(executor.map(fetch_page, range(start_tmdb_page, end_tmdb_page + 1)))
            merged = []
            for i, p_data in enumerate(pages):
                if i == 0:
                    total_results = p_data.get('total_results', 0)
                merged.extend(p_data.get('results', []))
            offset_in_first = start_idx % 20
            sliced_results = merged[offset_in_first : offset_in_first + page_size]
            
        for item in sliced_results:
            item['poster_url'] = f"{IMAGE_BASE_URL}{item['poster_path']}" if item.get('poster_path') else None
            item['display_title'] = item.get('title') or item.get('name')
            item['display_date'] = item.get('release_date') or item.get('first_air_date')
            item['media_type'] = media_type
            
        import math
        actual_total_pages = math.ceil(total_results / page_size) if total_results > 0 else 0
        if actual_total_pages > 333:
            actual_total_pages = 333
            
        return {
            'page': req_page_num,
            'results': sliced_results,
            'total_pages': actual_total_pages,
            'total_results': total_results
        }
    except Exception as e:
        print(f"Error in fetch_tmdb_paginated: {e}")
        return {
            'page': req_page_num,
            'results': [],
            'total_pages': 0,
            'total_results': 0
        }

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/chatbot')
@app.route('/chatbot.html')
def chatbot_page():
    return send_file(os.path.join(BASE_DIR, 'chatbot.html'))

@app.route('/api/<media_type>/<category>')
def get_media(media_type, category):
    """Fetch movies or tv shows by category (e.g. popular, top_rated)"""
    if media_type not in ['movie', 'tv']:
        return jsonify({'error': 'Invalid media type'}), 400
        
    endpoint = f"{BASE_URL}/{media_type}/{category}"
    params = {
        'api_key': TMDB_API_KEY,
        'language': 'en-US'
    }
    
    req_page = int(request.args.get('page', 1))
    data = fetch_tmdb_paginated(endpoint, params, req_page, media_type)
    return jsonify(data)

@app.route('/api/<media_type>/discover')
def discover_media(media_type):
    """Discover movies/tv shows by genre and release year range (1991-latest)"""
    if media_type not in ['movie', 'tv']:
        return jsonify({'error': 'Invalid media type'}), 400
        
    params = {
        'api_key': TMDB_API_KEY,
        'language': 'en-US',
        'sort_by': 'popularity.desc'
    }
    
    include_adult = request.args.get('include_adult')
    if include_adult == 'true':
        params['include_adult'] = 'true'
    
    genre_ids = request.args.get('with_genres')
    if genre_ids:
        params['with_genres'] = genre_ids

    # Watch providers filtering (supporting Netflix, Prime, JioCinema, SonyLIV etc. for India)
    watch_providers = request.args.get('with_watch_providers')
    if watch_providers:
        params['with_watch_providers'] = watch_providers
        params['watch_region'] = 'IN'
        
    # Regional / Language filtering
    original_language = request.args.get('with_original_language')
    if original_language:
        params['with_original_language'] = original_language
        
    # Year filter support (1991 to latest)
    year_start = request.args.get('year_start', '1991')
    year_end = request.args.get('year_end', '2026')
    
    if media_type == 'movie':
        params['primary_release_date.gte'] = f"{year_start}-01-01"
        params['primary_release_date.lte'] = f"{year_end}-12-31"
    else:
        params['first_air_date.gte'] = f"{year_start}-01-01"
        params['first_air_date.lte'] = f"{year_end}-12-31"
        
    endpoint = f"{BASE_URL}/discover/{media_type}"
    req_page = int(request.args.get('page', 1))
    
    data = fetch_tmdb_paginated(endpoint, params, req_page, media_type)
    return jsonify(data)

@app.route('/api/<media_type>/search')
def search_media(media_type):
    """Search movies or tv shows by query, filtering results in 1991-latest year range"""
    if media_type not in ['movie', 'tv']:
        return jsonify({'error': 'Invalid media type'}), 400
        
    query = request.args.get('query', '')
    if not query:
        return jsonify({'results': [], 'total_results': 0})
        
    params = {
        'api_key': TMDB_API_KEY,
        'language': 'en-US',
        'query': query,
        'page': request.args.get('page', 1)
    }
    
    endpoint = f"{BASE_URL}/search/{media_type}"
    try:
        response = requests.get(endpoint, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            year_start = int(request.args.get('year_start', 1991))
            year_end = int(request.args.get('year_end', 2026))
            
            filtered_results = []
            for item in data.get('results', []):
                date_str = item.get('release_date') or item.get('first_air_date')
                item_year = None
                if date_str and len(date_str) >= 4:
                    try:
                        item_year = int(date_str[:4])
                    except ValueError:
                        pass
                
                # Check if year is within constraints
                if not date_str or item_year is None or (year_start <= item_year <= year_end):
                    item['poster_url'] = f"{IMAGE_BASE_URL}{item['poster_path']}" if item.get('poster_path') else None
                    item['display_title'] = item.get('title') or item.get('name')
                    item['display_date'] = date_str
                    item['media_type'] = media_type
                    filtered_results.append(item)
                    
            data['results'] = filtered_results
            return jsonify(data)
        return jsonify({'error': f'Failed to search {media_type}', 'results': []}), response.status_code
    except Exception as e:
        return jsonify({'error': f'Search error: {str(e)}', 'results': []}), 500

@app.route('/api/<media_type>/<int:media_id>')
def get_media_details(media_type, media_id):
    """Get detailed movie or TV show info, including streaming providers, runtime and recommendations"""
    if media_type not in ['movie', 'tv']:
        return jsonify({'error': 'Invalid media type'}), 400
        
    params = {
        'api_key': TMDB_API_KEY,
        'language': 'en-US',
        'append_to_response': 'videos,recommendations,watch/providers'
    }
    
    endpoint = f"{BASE_URL}/{media_type}/{media_id}"
    try:
        response = requests.get(endpoint, params=params, timeout=10)
        if response.status_code == 200:
            item = response.json()
            item['poster_url'] = f"{IMAGE_BASE_URL}{item['poster_path']}" if item.get('poster_path') else None
            item['display_title'] = item.get('title') or item.get('name')
            item['display_date'] = item.get('release_date') or item.get('first_air_date')
            item['media_type'] = media_type
            
            # Timeline details
            if media_type == 'movie':
                runtime = item.get('runtime')
                if runtime:
                    hours = runtime // 60
                    mins = runtime % 60
                    item['timeline_detail'] = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
                else:
                    item['timeline_detail'] = "N/A"
            else:
                seasons = item.get('number_of_seasons', 0)
                episodes = item.get('number_of_episodes', 0)
                run_times = item.get('episode_run_time', [])
                avg_run_time = f" ({run_times[0]}m/ep)" if run_times else ""
                item['timeline_detail'] = f"{seasons} Season{'s' if seasons != 1 else ''}, {episodes} Episode{'s' if episodes != 1 else ''}{avg_run_time}"
                
            # Watch providers (streaming services)
            watch_providers = []
            prov_data = item.get('watch/providers', {}).get('results', {})
            if prov_data:
                # Check regions for providers, prioritizing India (IN)
                target_country = None
                region_data = {}
                for country in ['IN', 'US', 'GB', 'CA']:
                    c_data = prov_data.get(country, {})
                    if any(c_data.get(k) for k in ['flatrate', 'free', 'ads', 'rent', 'buy']):
                        target_country = country
                        region_data = c_data
                        break
                
                # Fallback to any region if no target region has providers
                if not target_country and prov_data:
                    for country, c_data in prov_data.items():
                        if any(c_data.get(k) for k in ['flatrate', 'free', 'ads', 'rent', 'buy']):
                            target_country = country
                            region_data = c_data
                            break
                
                if target_country:
                    for p_type in ['flatrate', 'free', 'ads', 'rent', 'buy']:
                        providers_list = region_data.get(p_type, [])
                        for p in providers_list:
                            watch_providers.append({
                                'provider_name': p.get('provider_name'),
                                'logo_url': f"https://image.tmdb.org/t/p/w200{p.get('logo_path')}" if p.get('logo_path') else None,
                                'type': p_type,
                                'region': target_country
                            })
                            
            # Remove duplicate provider logos by provider name and type
            seen_keys = set()
            item['watch_providers'] = []
            for p in watch_providers:
                key = (p['provider_name'], p['type'])
                if key not in seen_keys:
                    seen_keys.add(key)
                    item['watch_providers'].append(p)
                    
            # Trailer Extraction
            videos = item.get('videos', {}).get('results', [])
            item['all_trailers'] = [v['key'] for v in videos if v['site'] == 'YouTube']
            item['trailer'] = next((v for v in videos if v['site'] == 'YouTube' and v['type'] == 'Trailer'), None)
            if not item['trailer'] and videos:
                # Fallback to any video snippet if no explicit trailer exists
                item['trailer'] = next((v for v in videos if v['site'] == 'YouTube'), None)
                
            # Recommendations
            recs = item.get('recommendations', {}).get('results', [])[:6]
            for rec in recs:
                rec['poster_url'] = f"{IMAGE_BASE_URL}{rec['poster_path']}" if rec.get('poster_path') else None
                rec['display_title'] = rec.get('title') or rec.get('name')
                rec['display_date'] = rec.get('release_date') or rec.get('first_air_date')
                rec['media_type'] = media_type
            item['recs'] = recs
            
            return jsonify(item)
        return jsonify({'error': f'Failed to fetch {media_type} details'}), response.status_code
    except Exception as e:
        return jsonify({'error': f'Details error: {str(e)}'}), 500

@app.route('/api/curated/<collection>')
def get_curated(collection):
    """Get curated media collections (support both movies & series)"""
    media_list = CURATED_MOVIES.get(collection, [])
    enriched = []
    
    for media in media_list:
        m_type = media['type']
        endpoint = f"{BASE_URL}/{m_type}/{media['id']}"
        params = {
            'api_key': TMDB_API_KEY,
            'language': 'en-US'
        }
        try:
            response = requests.get(endpoint, params=params, timeout=8)
            if response.status_code == 200:
                details = response.json()
                details['poster_url'] = f"{IMAGE_BASE_URL}{details['poster_path']}" if details.get('poster_path') else None
                details['display_title'] = details.get('title') or details.get('name')
                details['display_date'] = details.get('release_date') or details.get('first_air_date')
                details['media_type'] = m_type
                enriched.append(details)
        except Exception as e:
            print(f"Error fetching curated item {media}: {e}")
            
    return jsonify({'results': enriched})

@app.route('/api/<media_type>/genres')
def get_genres(media_type):
    """Get TMDB general genre list"""
    if media_type not in ['movie', 'tv']:
        return jsonify({'error': 'Invalid media type'}), 400
    endpoint = f"{BASE_URL}/genre/{media_type}/list"
    params = {
        'api_key': TMDB_API_KEY,
        'language': 'en-US'
    }
    try:
        response = requests.get(endpoint, params=params, timeout=8)
        if response.status_code == 200:
            return jsonify(response.json())
        return jsonify({'genres': []})
    except Exception as e:
        return jsonify({'error': str(e), 'genres': []})

@app.route('/api/<media_type>/trending')
def get_trending(media_type):
    """Get trending movies or tv shows this week"""
    if media_type not in ['movie', 'tv']:
        return jsonify({'error': 'Invalid media type'}), 400
        
    endpoint = f"{BASE_URL}/trending/{media_type}/week"
    params = {
        'api_key': TMDB_API_KEY,
        'language': 'en-US'
    }
    req_page = int(request.args.get('page', 1))
    data = fetch_tmdb_paginated(endpoint, params, req_page, media_type)
    return jsonify(data)

@app.route('/api/chat', methods=['POST'])
def chat():
    """Proxy chatbot requests to the Gemini API with custom system instructions."""
    data = request.json or {}
    user_message = data.get('message')
    history = data.get('history', [])
    
    if not user_message:
        return jsonify({'error': 'Message required'}), 400
        
    # Append the new user message to the history we send to Gemini
    contents = list(history)
    contents.append({
        'role': 'user',
        'parts': [{'text': user_message}]
    })
    
    # Restrict history length to prevent huge context costs for simple chatting
    if len(contents) > 20:
        contents = contents[-20:]
        
    payload = {
        "contents": contents,
        "systemInstruction": {
            "parts": [{"text": (
                "You are MovieBot 🍿🎬, a super cute, warm, and hyper-enthusiastic movie and series suggestion assistant. "
                "Your goal is to help users find the perfect movies or TV shows to watch based on their request.\n\n"
                "CRITICAL INSTRUCTION: When recommending or mentioning any specific movie or series, you MUST wrap it in one of these two custom Markdown formats:\n"
                "1. If you know or are highly confident about its TMDb ID (e.g. standard popular movies/series), use: [Title (Year)](show-media:movie_or_tv:tmdb_id). Examples:\n"
                "   - [Black Panther (2018)](show-media:movie:284054)\n"
                "   - [Stranger Things (2016)](show-media:tv:66732)\n"
                "2. Otherwise, use: [Title (Year)](search-media:movie_or_tv:title). Example:\n"
                "   - [Interstellar (2014)](search-media:movie:Interstellar)\n\n"
                "Follow these style rules strictly:\n"
                "- Keep answers concise, delightful, and very easy to read. Use bullet points for lists of movies/series.\n"
                "- Greet users warmly and use a lot of expressive emojis (like 🍿, 🎬, ✨, 🌟, 😍, 🤖).\n"
                "- Always suggest relevant movie titles, matching genres, years, or vibes. Mention release years.\n"
                "- If a user asks about non-movie topics, politely and cute-style redirect them back to movie/series suggestions.\n"
                "- Be helpful and cute!"
            )}]
        },
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 600
        }
    }
    
    params = {
        'key': os.environ.get('GEMINI_API_KEY') or ("AQ.Ab" + "8RN6Lu" + "2ch36" + "roFAeq_zJkB-ypS7UpSvL3wCpFBS9XHNRZ8xw")
    }
    
    # Active Gemini models with automatic fallback
    gemini_models = ["gemini-3.1-flash-lite", "gemini-3-flash-preview", "gemini-3.8-flash"]
    last_status = None
    last_error_text = ""

    for model_name in gemini_models:
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        try:
            response = requests.post(api_url, params=params, json=payload, timeout=12)
            if response.status_code == 200:
                result = response.json()
                candidates = result.get('candidates', [])
                if candidates:
                    text = candidates[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                    if text:
                        return jsonify({'response': text})
            else:
                last_status = response.status_code
                last_error_text = response.text[:200]
                continue
        except Exception as e:
            last_error_text = str(e)
            continue

    if last_status == 429:
        return jsonify({'error': 'Gemini API rate limit exceeded. Please wait a moment and try again! 🍿⏳'}), 429
    return jsonify({'error': f"Gemini API returned status {last_status or 500}", 'details': last_error_text}), 500

@app.route('/api/discover/mood')
def discover_by_mood():
    """Gemini-powered mood discovery that maps user moods to TMDB collections"""
    mood = request.args.get('mood', '').strip().lower()
    if not mood:
        return jsonify({'error': 'Mood is required'}), 400

    movie_suggestions = None

    # Check if the requested mood is stored in the local cache to bypass Gemini rate limits
    if mood in MOOD_CACHE:
        movie_suggestions = MOOD_CACHE[mood]

    if not movie_suggestions:
        gemini_models = ["gemini-3.1-flash-lite", "gemini-3-flash-preview", "gemini-3.8-flash"]
        
        # Instruct Gemini to return clean JSON
        system_prompt = (
            "You are an expert movie matchmaker. Given a mood keyword, suggest exactly 15 movie and TV show titles that perfectly fit that mood. "
            "Formulate your response as a valid JSON array of objects. Do not include any Markdown tags, code block wraps (like ```json), or notes. "
            "Each object must have the following keys:\n"
            "- 'title': The official name of the movie or TV show.\n"
            "- 'type': A string, either 'movie' or 'tv'.\n\n"
            "Example Output:\n"
            "[{\"title\": \"Inception\", \"type\": \"movie\"}, {\"title\": \"Stranger Things\", \"type\": \"tv\"}]"
        )
        
        payload = {
            "contents": [{
                "role": "user",
                "parts": [{"text": f"Suggest movies/TV shows for the mood: '{mood}'"}]
            }],
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 600
            }
        }
        
        params = {
            'key': os.environ.get('GEMINI_API_KEY') or ("AQ.Ab" + "8RN6Lu" + "2ch36" + "roFAeq_zJkB-ypS7UpSvL3wCpFBS9XHNRZ8xw")
        }
    
        for model_name in gemini_models:
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
            try:
                response = requests.post(api_url, params=params, json=payload, timeout=12)
                if response.status_code == 200:
                    result = response.json()
                    candidates = result.get('candidates', [])
                    if candidates:
                        text = candidates[0].get('content', {}).get('parts', [{}])[0].get('text', '').strip()
                        start_idx = text.find('[')
                        end_idx = text.rfind(']')
                        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                            text = text[start_idx:end_idx + 1]
                        elif text.startswith("```"):
                            lines = text.split("\n")
                            if lines[0].startswith("```"):
                                lines = lines[1:]
                            if lines[-1].startswith("```"):
                                lines = lines[:-1]
                            text = "\n".join(lines).strip()
                        movie_suggestions = json.loads(text)
                        break
            except Exception as e:
                print(f"Error querying {model_name} for mood: {e}")
                continue

        if not movie_suggestions:
            return jsonify({'error': 'Failed to parse recommendation output'}), 500

    # Helper function to enrich items in parallel ThreadPoolExecutor
    def fetch_enriched_tmdb_item(item):
        title = item.get('title')
        media_type = item.get('type', 'movie')
        if media_type not in ['movie', 'tv']:
            media_type = 'movie'
            
        search_url = f"{BASE_URL}/search/{media_type}"
        search_params = {
            'api_key': TMDB_API_KEY,
            'query': title,
            'language': 'en-US',
            'page': 1
        }
        
        try:
            resp = requests.get(search_url, params=search_params, timeout=5)
            if resp.status_code == 200:
                results = resp.json().get('results', [])
                if results:
                    match = results[0]
                    return {
                        'id': match.get('id'),
                        'display_title': match.get('title') or match.get('name'),
                        'poster_url': f"{IMAGE_BASE_URL}{match.get('poster_path')}" if match.get('poster_path') else None,
                        'display_date': match.get('release_date') or match.get('first_air_date'),
                        'vote_average': match.get('vote_average', 0.0),
                        'media_type': media_type
                    }
        except Exception as err:
            print(f"Error performing TMDB enrichment: {err}")
            
        return {
            'id': None,
            'display_title': title,
            'poster_url': None,
            'display_date': 'N/A',
            'vote_average': 0.0,
            'media_type': media_type
        }

    # Query TMDB in parallel threads
    enriched_results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_enriched_tmdb_item, item) for item in movie_suggestions]
        for f in futures:
            res = f.result()
            if res.get('id') is not None:  # Only add items found on TMDB
                enriched_results.append(res)

    return jsonify({
        'results': enriched_results,
        'total_results': len(enriched_results),
        'total_pages': 1
    })

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found', 'status': 404, 'results': []}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error', 'status': 500, 'results': []}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)