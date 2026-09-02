from flask import Flask, render_template, jsonify, request
import requests
import json
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

# Load environment variables from .env if present
if os.path.exists('.env'):
    with open('.env', encoding='utf-8-sig') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ[k.strip()] = v.strip()

# Database Initialization
def init_db():
    conn = sqlite3.connect('movies.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            media_id TEXT NOT NULL,
            media_type TEXT NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(device_id, media_id, media_type)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

TMDB_API_KEY = os.environ.get("TMDB_API_KEY")
BASE_URL = "https://api.tmdb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"

# Curated collections removed
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

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/api/<media_type>/<category>')
def get_media(media_type, category):
    """Fetch movies or tv shows by category (e.g. popular, top_rated)"""
    if media_type not in ['movie', 'tv']:
        return jsonify({'error': 'Invalid media type'}), 400
        
    endpoint = f"{BASE_URL}/{media_type}/{category}"
    params = {
        'api_key': TMDB_API_KEY,
        'language': 'en-US',
        'page': request.args.get('page', 1)
    }
    
    response = requests.get(endpoint, params=params)
    if response.status_code == 200:
        data = response.json()
        for item in data.get('results', []):
            item['poster_url'] = f"{IMAGE_BASE_URL}{item['poster_path']}" if item.get('poster_path') else None
            item['display_title'] = item.get('title') or item.get('name')
            item['display_date'] = item.get('release_date') or item.get('first_air_date')
            item['media_type'] = media_type
        return jsonify(data)
    return jsonify({'error': f'Failed to fetch {media_type}'}), 500

@app.route('/api/<media_type>/discover')
def discover_media(media_type):
    """Discover movies/tv shows by genre, provider, language and year"""
    if media_type not in ['movie', 'tv']:
        return jsonify({'error': 'Invalid media type'}), 400

    date_field = 'primary_release_date' if media_type == 'movie' else 'first_air_date'
    params = {
        'api_key': TMDB_API_KEY,
        'language': 'en-US',
        'sort_by': 'popularity.desc',
        'page': request.args.get('page', 1),
        'with_genres': request.args.get('with_genres'),
        'with_original_language': request.args.get('with_original_language'),
        f'{date_field}.gte': f"{request.args.get('year_start', '1991')}-01-01",
        f'{date_field}.lte': f"{request.args.get('year_end', '2026')}-12-31"
    }

    if request.args.get('with_watch_providers'):
        params.update({
            'with_watch_providers': request.args.get('with_watch_providers'),
            'watch_region': 'IN',
            'with_watch_monetization_types': 'flatrate|free|ads'
        })

    # Keep only provided parameters to keep requests clean
    params = {k: v for k, v in params.items() if v is not None}

    resp = requests.get(f"{BASE_URL}/discover/{media_type}", params=params)
    if resp.status_code != 200:
        return jsonify({'error': f'TMDB API Error: {resp.text}'}), resp.status_code

    data = resp.json()
    for item in data.get('results', []):
        item['poster_url'] = f"{IMAGE_BASE_URL}{item['poster_path']}" if item.get('poster_path') else None
        item['display_title'] = item.get('title') or item.get('name')
        item['display_date'] = item.get('release_date') or item.get('first_air_date')
        item['media_type'] = media_type
        
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
    
    resp = requests.get(f"{BASE_URL}/search/{media_type}", params=params)
    if resp.status_code != 200:
        return jsonify({'error': f'Search failed: {resp.text}'}), resp.status_code
        
    data = resp.json()
    year_start = int(request.args.get('year_start', 1991))
    year_end = int(request.args.get('year_end', 2026))
    
    filtered = []
    for item in data.get('results', []):
        date_str = item.get('release_date') or item.get('first_air_date')
        item_year = int(date_str[:4]) if date_str and len(date_str) >= 4 and date_str[:4].isdigit() else None
        
        # Check if year is within constraints
        if not date_str or item_year is None or (year_start <= item_year <= year_end):
            item['poster_url'] = f"{IMAGE_BASE_URL}{item['poster_path']}" if item.get('poster_path') else None
            item['display_title'] = item.get('title') or item.get('name')
            item['display_date'] = date_str
            item['media_type'] = media_type
            filtered.append(item)
            
    data['results'] = filtered
    return jsonify(data)

@app.route('/api/<media_type>/<int:media_id>')
def get_media_details(media_type, media_id):
    """Get detailed movie or TV show info, including streaming providers, runtime and recommendations"""
    if media_type not in ['movie', 'tv']:
        return jsonify({'error': 'Invalid media type'}), 400
        
    params = {
        'api_key': TMDB_API_KEY,
        'language': 'en-US',
        'append_to_response': 'videos,recommendations,credits'
    }
    
    endpoint = f"{BASE_URL}/{media_type}/{media_id}"
    response = requests.get(endpoint, params=params)
    
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
        providers_url = f"{BASE_URL}/{media_type}/{media_id}/watch/providers"
        prov_resp = requests.get(providers_url, params={'api_key': TMDB_API_KEY})
        watch_providers = []
        
        if prov_resp.status_code == 200:
            prov_data = prov_resp.json().get('results', {})
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
    return jsonify({'error': f'Failed to fetch {media_type} details'}), 500



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
    response = requests.get(endpoint, params=params)
    return jsonify(response.json())

@app.route('/api/<media_type>/trending')
def get_trending(media_type):
    """Get trending movies or tv shows this week"""
    if media_type not in ['movie', 'tv']:
        return jsonify({'error': 'Invalid media type'}), 400
        
    params = {'api_key': TMDB_API_KEY, 'language': 'en-US'}
    resp = requests.get(f"{BASE_URL}/trending/{media_type}/week", params=params)
    
    if resp.status_code != 200:
        return jsonify({'error': f'Trending failed: {resp.text}'}), resp.status_code
        
    data = resp.json()
    for item in data.get('results', []):
        item['poster_url'] = f"{IMAGE_BASE_URL}{item['poster_path']}" if item.get('poster_path') else None
        item['display_title'] = item.get('title') or item.get('name')
        item['display_date'] = item.get('release_date') or item.get('first_air_date')
        item['media_type'] = media_type
        
    return jsonify(data)

@app.route('/api/person/<person_id>')
def get_person(person_id):
    """Fetch person bio and credits"""
    endpoint = f"{BASE_URL}/person/{person_id}"
    params = {
        'api_key': TMDB_API_KEY,
        'language': 'en-US',
        'append_to_response': 'combined_credits'
    }
    resp = requests.get(endpoint, params=params)
    if resp.status_code == 200:
        data = resp.json()
        data['profile_url'] = f"{IMAGE_BASE_URL}{data['profile_path']}" if data.get('profile_path') else None
        
        # Sort combined credits by popularity
        credits = data.get('combined_credits', {}).get('cast', [])
        credits.sort(key=lambda x: x.get('popularity', 0), reverse=True)
        # We cap it at 15 to keep the frontend clean
        top_credits = credits[:15]
        
        for c in top_credits:
            c['poster_url'] = f"{IMAGE_BASE_URL}{c['poster_path']}" if c.get('poster_path') else None
            c['display_title'] = c.get('title') or c.get('name')
        
        data['top_credits'] = top_credits
        return jsonify(data)
        
    return jsonify({'error': 'Failed to fetch person details'}), 500

@app.route('/api/trivia/<media_type>/<media_id>')
def get_trivia(media_type, media_id):
    """Fetch fun trivia using Gemini"""
    # 1. First fetch title/year from TMDB
    tmdb_endpoint = f"{BASE_URL}/{media_type}/{media_id}"
    tmdb_params = {'api_key': TMDB_API_KEY, 'language': 'en-US'}
    resp = requests.get(tmdb_endpoint, params=tmdb_params)
    if resp.status_code != 200:
        return jsonify({'error': 'Failed to fetch media from TMDB'}), 500
        
    media = resp.json()
    title = media.get('title') or media.get('name')
    date = media.get('release_date') or media.get('first_air_date', '')
    year = date[:4] if date else "Unknown Year"
    
    # 2. Ask OpenAI for trivia
    api_url = "https://api.openai.com/v1/chat/completions"
    prompt = f"Give me exactly 3 fascinating behind-the-scenes facts or Easter eggs about the {media_type} '{title}' ({year}). Make them concise, exciting, and bullet-pointed with emojis."
    
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.8,
        "max_tokens": 400
    }
    
    openai_key = os.environ.get("GEMINI_API_KEY")
    headers = {
        "Authorization": f"Bearer {openai_key}",
        "Content-Type": "application/json"
    }
    
    try:
        g_resp = requests.post(api_url, headers=headers, json=payload, timeout=10)
        if g_resp.status_code == 200:
            result = g_resp.json()
            if result.get('choices'):
                trivia = result['choices'][0]['message']['content']
                return jsonify({'success': True, 'trivia': trivia})
    except Exception as e:
        print(f"Trivia error: {e}")
        
    return jsonify({'error': 'Failed to generate trivia.'}), 500
@app.route('/api/chat', methods=['POST'])
def chat():
    """Proxy chatbot requests to the Gemini API with custom system instructions."""
    data = request.json or {}
    user_message = data.get('message')
    history = data.get('history', [])
    
    if not user_message:
        return jsonify({'error': 'Message required'}), 400
        
    # Append the new user message to the history we send to OpenAI
    messages = []
    
    # System Instruction
    messages.append({
        "role": "system",
        "content": (
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
        )
    })
    
    # Convert Gemini-style history to OpenAI format
    for h in history:
        r = "assistant" if h.get("role") == "model" else "user"
        txt = h.get("parts", [{}])[0].get("text", "")
        messages.append({"role": r, "content": txt})
        
    messages.append({"role": "user", "content": user_message})
    
    # Restrict history length to prevent huge context costs for simple chatting
    if len(messages) > 20:
        # Keep system prompt, take last 19 messages
        messages = [messages[0]] + messages[-19:]
        
    api_url = "https://api.openai.com/v1/chat/completions"
    
    payload = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 600
    }
    
    openai_key = os.environ.get("GEMINI_API_KEY")
    headers = {
        "Authorization": f"Bearer {openai_key}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=15)
        if response.status_code == 200:
            result = response.json()
            if result.get('choices'):
                text = result['choices'][0]['message']['content']
                if text:
                    return jsonify({'response': text})
            
            return jsonify({'error': 'Empty response from OpenAI API'}), 500
        else:
            if response.status_code == 429:
                return jsonify({'error': 'OpenAI API rate limit exceeded. Please wait a moment and try again! 🍿⏳'}), 429
            return jsonify({'error': f"OpenAI API returned status {response.status_code}", 'details': response.json() if response.headers.get("Content-Type") == "application/json" else response.text}), 500
            
    except Exception as e:
        return jsonify({'error': f"Failed to connect to Gemini API: {str(e)}"}), 500

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
        # Fallback to querying the OpenAI API if not found in the local cache
        api_url = "https://api.openai.com/v1/chat/completions"
        
        # Instruct OpenAI to return clean JSON
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
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Suggest movies/TV shows for the mood: '{mood}'"}
            ],
            "temperature": 0.7,
            "max_tokens": 600
        }
        
        openai_key = os.environ.get('GEMINI_API_KEY')
        headers = {
            "Authorization": f"Bearer {openai_key}",
            "Content-Type": "application/json"
        }
    
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=12)
            if response.status_code != 200:
                if response.status_code == 429:
                    return jsonify({
                        'error': 'OpenAI API rate limit exceeded. Please wait a moment and try again! 🍿⏳'
                    }), 429
                return jsonify({
                    'error': f'Failed to query OpenAI API with status {response.status_code}',
                    'details': response.json() if response.headers.get("Content-Type") == "application/json" else response.text
                }), 500
                
            result = response.json()
            if not result.get('choices'):
                return jsonify({'error': 'Empty response from OpenAI'}), 500
                
            text = result['choices'][0]['message']['content'].strip()
            
            # Clean markdown code block wraps or extract JSON array if OpenAI returns conversational text
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
        except Exception as e:
            print(f"Error parsing Gemini mood output: {e}")
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

# --- Watchlist Database Endpoints ---

@app.route('/api/db/watchlist/get', methods=['GET'])
def get_watchlist():
    device_id = request.args.get('device_id')
    if not device_id:
        return jsonify({'error': 'device_id required'}), 400
    
    conn = sqlite3.connect('movies.db')
    c = conn.cursor()
    c.execute('SELECT media_id, media_type, added_at FROM watchlist WHERE device_id = ? ORDER BY added_at DESC', (device_id,))
    rows = c.fetchall()
    conn.close()
    
    results = [{"id": r[0], "type": r[1], "added_at": r[2]} for r in rows]
    return jsonify({'success': True, 'results': results})

@app.route('/api/db/watchlist/add', methods=['POST'])
def add_watchlist():
    data = request.json or {}
    device_id = data.get('device_id')
    media_id = str(data.get('media_id'))
    media_type = data.get('media_type')
    
    if not device_id or not media_id or not media_type:
        return jsonify({'error': 'Missing required fields'}), 400
        
    try:
        conn = sqlite3.connect('movies.db')
        c = conn.cursor()
        c.execute('INSERT OR IGNORE INTO watchlist (device_id, media_id, media_type) VALUES (?, ?, ?)', 
                  (device_id, media_id, media_type))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/db/watchlist/remove', methods=['POST'])
def remove_watchlist():
    data = request.json or {}
    device_id = data.get('device_id')
    media_id = str(data.get('media_id'))
    media_type = data.get('media_type')
    
    if not device_id or not media_id or not media_type:
        return jsonify({'error': 'Missing required fields'}), 400
        
    try:
        conn = sqlite3.connect('movies.db')
        c = conn.cursor()
        c.execute('DELETE FROM watchlist WHERE device_id = ? AND media_id = ? AND media_type = ?', 
                  (device_id, media_id, media_type))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)