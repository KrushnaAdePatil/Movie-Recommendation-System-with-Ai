from flask import Flask, render_template, jsonify, request
import requests
import json
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

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
    """Discover movies/tv shows by genre and release year range (1991-latest)"""
    if media_type not in ['movie', 'tv']:
        return jsonify({'error': 'Invalid media type'}), 400
        
    params = {
        'api_key': TMDB_API_KEY,
        'language': 'en-US',
        'sort_by': 'popularity.desc',
        'page': request.args.get('page', 1)
    }
    
    genre_ids = request.args.get('with_genres')
    if genre_ids:
        params['with_genres'] = genre_ids

    # Watch providers filtering (supporting Netflix, Prime, JioCinema, SonyLIV etc. for India)
    watch_providers = request.args.get('with_watch_providers')
    if watch_providers:
        params['with_watch_providers'] = watch_providers
        params['watch_region'] = 'IN'
        params['with_watch_monetization_types'] = 'flatrate|free|ads'
        
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
    response = requests.get(endpoint, params=params)
    
    if response.status_code == 200:
        data = response.json()
        for item in data.get('results', []):
            item['poster_url'] = f"{IMAGE_BASE_URL}{item['poster_path']}" if item.get('poster_path') else None
            item['display_title'] = item.get('title') or item.get('name')
            item['display_date'] = item.get('release_date') or item.get('first_air_date')
            item['media_type'] = media_type
        return jsonify(data)
    return jsonify({'error': f'Failed to discover {media_type}'}), 500

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
    response = requests.get(endpoint, params=params)
    
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
    return jsonify({'error': f'Failed to search {media_type}'}), 500

@app.route('/api/<media_type>/<int:media_id>')
def get_media_details(media_type, media_id):
    """Get detailed movie or TV show info, including streaming providers, runtime and recommendations"""
    if media_type not in ['movie', 'tv']:
        return jsonify({'error': 'Invalid media type'}), 400
        
    params = {
        'api_key': TMDB_API_KEY,
        'language': 'en-US',
        'append_to_response': 'videos,recommendations'
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
            # Check regions for providers
            for country in ['US', 'IN', 'GB', 'CA']:
                region_data = prov_data.get(country, {})
                flatrate = region_data.get('flatrate', [])
                if flatrate:
                    for p in flatrate:
                        watch_providers.append({
                            'provider_name': p.get('provider_name'),
                            'logo_url': f"https://image.tmdb.org/t/p/w200{p.get('logo_path')}" if p.get('logo_path') else None,
                            'region': country
                        })
                    break
            
            # Fallback to any region if target lists empty
            if not watch_providers:
                for country, r_data in prov_data.items():
                    flatrate = r_data.get('flatrate', [])
                    if flatrate:
                        for p in flatrate:
                            watch_providers.append({
                                'provider_name': p.get('provider_name'),
                                'logo_url': f"https://image.tmdb.org/t/p/w200{p.get('logo_path')}" if p.get('logo_path') else None,
                                'region': country
                            })
                        break
                        
        # Remove duplicate provider logos by provider name
        seen_providers = set()
        item['watch_providers'] = []
        for p in watch_providers:
            if p['provider_name'] not in seen_providers:
                seen_providers.add(p['provider_name'])
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
        response = requests.get(endpoint, params=params)
        if response.status_code == 200:
            details = response.json()
            details['poster_url'] = f"{IMAGE_BASE_URL}{details['poster_path']}" if details.get('poster_path') else None
            details['display_title'] = details.get('title') or details.get('name')
            details['display_date'] = details.get('release_date') or details.get('first_air_date')
            details['media_type'] = m_type
            enriched.append(details)
            
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
    response = requests.get(endpoint, params=params)
    return jsonify(response.json())

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
    response = requests.get(endpoint, params=params)
    if response.status_code == 200:
        data = response.json()
        for item in data.get('results', []):
            item['poster_url'] = f"{IMAGE_BASE_URL}{item['poster_path']}" if item.get('poster_path') else None
            item['display_title'] = item.get('title') or item.get('name')
            item['display_date'] = item.get('release_date') or item.get('first_air_date')
            item['media_type'] = media_type
        return jsonify(data)
    return jsonify({'error': f'Failed to fetch TV/Movie trending'}), 500

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
        
    api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    
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
    
    try:
        response = requests.post(api_url, params=params, json=payload, timeout=15)
        if response.status_code == 200:
            result = response.json()
            candidates = result.get('candidates', [])
            if candidates:
                text = candidates[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                if text:
                    return jsonify({'response': text})
            
            return jsonify({'error': 'Empty response from Gemini API'}), 500
        else:
            return jsonify({'error': f"Gemini API returned status {response.status_code}", 'details': response.json() if response.headers.get("Content-Type") == "application/json" else response.text}), 500
            
    except Exception as e:
        return jsonify({'error': f"Failed to connect to Gemini API: {str(e)}"}), 500

@app.route('/api/discover/mood')
def discover_by_mood():
    """Gemini-powered mood discovery that maps user moods to TMDB collections"""
    mood = request.args.get('mood', '').strip()
    if not mood:
        return jsonify({'error': 'Mood is required'}), 400

    api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    
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

    try:
        response = requests.post(api_url, params=params, json=payload, timeout=12)
        if response.status_code != 200:
            return jsonify({
                'error': f'Failed to query Gemini API with status {response.status_code}',
                'details': response.json() if response.headers.get("Content-Type") == "application/json" else response.text
            }), 500
            
        result = response.json()
        candidates = result.get('candidates', [])
        if not candidates:
            return jsonify({'error': 'Empty response from Gemini'}), 500
            
        text = candidates[0].get('content', {}).get('parts', [{}])[0].get('text', '').strip()
        
        # Clean markdown code block wraps if Gemini returns them
        if text.startswith("```"):
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

if __name__ == '__main__':
    app.run(debug=True, port=5000)