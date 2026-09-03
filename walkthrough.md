# Project Walkthrough - Movie & Series Suggestion System

The Movie & TV Series Suggestion System ("ShowSeeker") is complete! We have upgraded the application, styled the frontend with glassmorphism card layouts, and verified that both movies and series details (including release dates, runtimes, and local streaming providers) load correctly.

## Changes Made

### 1. Updated Backend (`app.py`)
- **API Mirror Domain**: Replaced `api.themoviedb.org` with `api.tmdb.org` to bypass the connection reset issues.
- **Unified Media Routes**: Supported dynamic retrieval for both `movie` and `tv` categories (Trending, Popular, Top Rated).
- **Search Boundaries**: Added range filters inside TV and Movie search, filtering results from **1991 to 2026** (latest).
- **Watch Providers Integration**: Fetched stream options by checking targeted country regions (`US`, `IN`, `GB`, `CA`) and extracting flatrate streaming sources (Netflix, Disney+, Prime, etc.).
- **Timeline details**: Added custom formatting for durations (e.g., `2h 15m` for movies, and `4 Seasons, 50 Episodes (45m/ep)` for TV shows).

### 2. Upgraded Frontend Templates & Scripts
- **UI Architecture (`templates/home.html`)**: Features clean dark neon themes, a media switcher toggle, year sliders, and explicit buttons for **Adventure**, **Horror**, **Thriller**, and **Drama**.
- **Interactive Logic (`static/js/script.js`)**: Orchestrates search queries, year sliders, dynamic pagination, and triggers modal overlays containing embedded YouTube trailers, recommended titles, and watch providers.
- **Modern CSS Layout (`static/css/style.css`)**: Elegant dark theme using subtle radial glows, custom slider styling, and glassmorphic panels.

---

## Verification Results

We verified the local Flask application endpoints programmatically. Here are the outputs:

| Test Case | Request | Output Status | Sample Results |
| :--- | :--- | :---: | :--- |
| **Movie Trending** | `/api/movie/trending` | `200 OK` | `Obsession`, `Alien: Romulus` |
| **Discover Adventure (2015-2020)** | `/api/movie/discover?year_start=2015&year_end=2020&with_genres=12` | `200 OK` | Releases match the range: `2018-04-27`, `2015-05-15` |
| **Search Batman (2005-2010)** | `/api/movie/search?query=Batman&year_start=2005&year_end=2010` | `200 OK` | `Batman Begins (2005)`, `The Dark Knight (2008)`, `Batman: Under the Red Hood (2010)` |
| **Media Details (Joker id=475557)** | `/api/movie/475557` | `200 OK` | Title: `Joker`, duration: `2h 2m`, watch providers loaded. |

---

## How to Run the Project Locally
To start the server and view the dashboard:
1. Ensure your virtual environment contains the necessary dependencies:
   ```powershell
   venv\Scripts\pip.exe install -r templates/requirement.txt
   ```
2. Start the Flask application:
   ```powershell
   venv\Scripts\python.exe app.py
   ```
3. Open a browser and navigate to:
   ```
   http://127.0.0.1:5000
   ```
4. You can search movies/shows, filter by years from 1991 onwards, load the custom genre choices, and click titles to view casting, trailers, and streaming provider badges.