import requests

BASE_URL = "http://127.0.0.1:5000"

def test_endpoint(path, name):
    url = f"{BASE_URL}{path}"
    try:
        response = requests.get(url, timeout=5)
        print(f"[{name}] GET {path} - Status: {response.status_code}")
        if response.status_code == 200:
            print("  -> Success!")
            if response.headers.get("Content-Type") == "application/json":
                data = response.json()
                results = data.get("results") or data.get("watch_providers") or data
                print(f"  -> Returned items: {len(results) if isinstance(results, list) else 'dict'}")
            else:
                print(f"  -> Body snippet: {response.text[:100].strip()}...")
        else:
            print(f"  -> Error details: {response.text[:200]}")
    except Exception as e:
        print(f"[{name}] GET {path} - FAILED with exception: {e}")

if __name__ == "__main__":
    print("Starting API Endpoints Verification...")
    test_endpoint("/", "Homepage")
    test_endpoint("/api/movie/trending", "Trending Movies")
    test_endpoint("/api/movie/discover?year_start=2015&year_end=2020&with_genres=12", "Discover Adventure Movies")
    test_endpoint("/api/movie/search?query=Batman&year_start=2005&year_end=2010", "Search Batman")
    test_endpoint("/api/movie/475557", "Movie Details (Joker)")
    test_endpoint("/api/movie/genres", "Get Genres list")
    test_endpoint("/api/curated/korean", "Curated Korean collection")
