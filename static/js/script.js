// State variables
let mediaType = 'movie'; // 'movie' or 'tv'
let selectedGenreId = null;
let minYear = 1991;
let maxYear = 2026;
let currentPage = 1;
let currentQuery = '';
let currentCategory = 'trending'; // 'trending', 'popular', 'top_rated', 'curated'
let activeCuratedCollection = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeSliders();
    setupSearch();
    loadContent();
});

// Setup sliders for year range (1991 to latest)
function initializeSliders() {
    const minSlider = document.getElementById('minYearSlider');
    const maxSlider = document.getElementById('maxYearSlider');

    minSlider.value = minYear;
    maxSlider.value = maxYear;

    updateYearLabels();
}

function updateYearLabels() {
    document.getElementById('lblMinYear').innerText = minYear;
    document.getElementById('lblMaxYear').innerText = maxYear;
}

function updateYearFilter() {
    const minSlider = document.getElementById('minYearSlider');
    const maxSlider = document.getElementById('maxYearSlider');

    let valPrevMin = minYear;
    let valPrevMax = maxYear;

    minYear = parseInt(minSlider.value);
    maxYear = parseInt(maxSlider.value);

    // Maintain overlap constraint
    if (minYear > maxYear) {
        if (minSlider === document.activeElement) {
            maxSlider.value = minYear;
            maxYear = minYear;
        } else {
            minSlider.value = maxYear;
            minYear = maxYear;
        }
    }

    updateYearLabels();

    // Only reload if values actually changed
    if (valPrevMin !== minYear || valPrevMax !== maxYear) {
        // Debounce fetch slightly to prevent heavy API calls on slider drag
        clearTimeout(window.sliderTimeout);
        window.sliderTimeout = setTimeout(() => {
            currentPage = 1;
            // Clear current query if details changed, or perform search with filter
            loadContent();
        }, 300);
    }
}

// Media type toggling (Movies / Series)
function setMediaType(type) {
    if (mediaType === type) return;
    mediaType = type;

    // Update active UI classes
    document.getElementById('btnMovie').classList.toggle('active', type === 'movie');
    document.getElementById('btnTV').classList.toggle('active', type === 'tv');

    // Reset pages & load
    currentPage = 1;
    activeCuratedCollection = null;
    deactivateCuratedButtons();
    loadContent();
}

// Genre select/toggle (Adventure, Horror, Thriller, Drama)
// TMDB Specific Genre IDs:
// Movie: Adventure=12, Horror=27, Thriller=53, Drama=18
// TV (Series): Action & Adventure=10759, Mystery=9648 (Horror equivalent), Drama=18, Sci-Fi/Thriller equivalent=10765 or 9648
function getGenreMapping(genreId, type) {
    if (type === 'movie') return genreId;

    // TV translations
    if (genreId === 12) return 10759; // Adventure -> Action/Adventure
    if (genreId === 27) return 9648;  // Horror -> Mystery (best match)
    if (genreId === 53) return 9648;  // Thriller -> Mystery
    if (genreId === 18) return 18;    // Drama -> Drama
    return genreId;
}

function toggleGenre(genreId, elementIdSuffix) {
    // Curated lists override active categories
    activeCuratedCollection = null;
    deactivateCuratedButtons();

    const card = document.getElementById(`genre-${elementIdSuffix}`);
    const isActive = card.classList.contains('active');

    // Clear other active genre cards
    document.querySelectorAll('.genre-card').forEach(c => c.classList.remove('active'));

    if (isActive) {
        selectedGenreId = null;
    } else {
        selectedGenreId = genreId;
        card.classList.add('active');
    }

    currentPage = 1;
    currentCategory = 'discover';
    updateCategorySubHeader();
    loadContent();
}

// Search interaction
function setupSearch() {
    const input = document.getElementById('searchInput');
    const btn = document.getElementById('searchBtn');

    btn.addEventListener('click', performSearch);
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') performSearch();
    });
}

function performSearch() {
    const query = document.getElementById('searchInput').value.trim();
    if (!query) {
        currentQuery = '';
        currentCategory = 'trending';
        loadContent();
        return;
    }

    currentQuery = query;
    currentPage = 1;
    currentCategory = 'search';

    // Reset genre toggles
    selectedGenreId = null;
    document.querySelectorAll('.genre-card').forEach(c => c.classList.remove('active'));
    activeCuratedCollection = null;
    deactivateCuratedButtons();

    updateCategorySubHeader();
    loadContent();
}

// Curated collections loader
function loadCuratedList(collection) {
    activeCuratedCollection = collection;
    currentCategory = 'curated';
    currentQuery = '';
    selectedGenreId = null;

    // Reset UI selections
    document.querySelectorAll('.genre-card').forEach(c => c.classList.remove('active'));
    document.getElementById('searchInput').value = '';

    // Toggle active collection side-bar buttons
    deactivateCuratedButtons();
    document.querySelectorAll('.col-item-btn').forEach(btn => {
        if (btn.innerText.toLowerCase().includes(collection)) {
            btn.classList.add('active');
        }
    });

    currentPage = 1;
    updateCategorySubHeader();
    loadContent();
}

function deactivateCuratedButtons() {
    document.querySelectorAll('.col-item-btn').forEach(btn => btn.classList.remove('active'));
}

// Quick lists loader (Popular, Top rated)
function loadQuickCategory(cat) {
    currentCategory = cat;
    currentQuery = '';
    selectedGenreId = null;
    activeCuratedCollection = null;

    // Reset buttons and input elements
    document.getElementById('searchInput').value = '';
    document.querySelectorAll('.genre-card').forEach(c => c.classList.remove('active'));
    deactivateCuratedButtons();

    document.getElementById('qPopular').classList.toggle('active', cat === 'popular');
    document.getElementById('qTopRated').classList.toggle('active', cat === 'top_rated');

    currentPage = 1;
    updateCategorySubHeader();
    loadContent();
}

function updateCategorySubHeader() {
    const title = document.getElementById('catalogTitle');
    const mediaName = mediaType === 'movie' ? 'Movies' : 'TV Shows';

    if (currentCategory === 'trending') {
        title.innerHTML = `Trending ${mediaName}`;
    } else if (currentCategory === 'popular') {
        title.innerHTML = `Popular ${mediaName}`;
    } else if (currentCategory === 'top_rated') {
        title.innerHTML = `Top Rated ${mediaName}`;
    } else if (currentCategory === 'search') {
        title.innerHTML = `Search Results: "${currentQuery}"`;
    } else if (currentCategory === 'discover') {
        title.innerHTML = `Suggested ${mediaName}`;
    } else if (currentCategory === 'curated') {
        title.innerHTML = `Curated: ${activeCuratedCollection.toUpperCase()} Collection`;
    }
}

// Load dynamic data based on active states
async function loadContent() {
    const grid = document.getElementById('moviesGrid');
    const pagination = document.getElementById('paginationControls');

    grid.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i><p>Discovering titles...</p></div>';
    pagination.style.display = 'none';

    let url = '';

    // 1. Search Query active
    if (currentCategory === 'search') {
        url = `/api/${mediaType}/search?query=${encodeURIComponent(currentQuery)}&year_start=${minYear}&year_end=${maxYear}&page=${currentPage}`;
    }
    // 2. Curated collections active
    else if (currentCategory === 'curated') {
        url = `/api/curated/${activeCuratedCollection}`;
    }
    // 3. Discovery Filter (Genre selection and/or Year range adjustments)
    else if (currentCategory === 'discover' || selectedGenreId !== null) {
        let genreParam = '';
        if (selectedGenreId !== null) {
            genreParam = `&with_genres=${getGenreMapping(selectedGenreId, mediaType)}`;
        }
        url = `/api/${mediaType}/discover?year_start=${minYear}&year_end=${maxYear}${genreParam}&page=${currentPage}`;
    }
    // 4. Default categories (trending, popular, top_rated)
    else {
        url = `/api/${mediaType}/${currentCategory}?page=${currentPage}`;
    }

    try {
        const response = await fetch(url);
        const data = await response.json();

        if (data.results && data.results.length > 0) {
            renderCards(data.results);

            // Manage pagination details (curated collections don't use pages)
            if (currentCategory !== 'curated') {
                pagination.style.display = 'flex';
                document.getElementById('pageNumberDisplay').innerText = `Page ${currentPage} of ${data.total_pages || 1}`;

                // Toggle navbar buttons
                const prevBtn = pagination.querySelector('button:first-child');
                const nextBtn = pagination.querySelector('button:last-child');
                prevBtn.disabled = currentPage === 1;
                nextBtn.disabled = currentPage >= (data.total_pages || 1);
            }
        } else {
            grid.innerHTML = `
                <div class="loading">
                    <i class="fas fa-search-minus" style="font-size: 2.5rem; color: var(--text-muted);"></i>
                    <p style="margin-top: 15px;">No matches found matching your filters (1991 to latest).</p>
                </div>`;
        }
    } catch (error) {
        console.error('Error fetching list:', error);
        grid.innerHTML = '<p class="error-text" style="color: #ff5252; text-align: center; grid-column: 1/-1;">Connection lost with TMDB server. Retrying...</p>';
    }
}

// Render catalog display grid
function renderCards(items) {
    const grid = document.getElementById('moviesGrid');
    grid.innerHTML = '';

    items.forEach(item => {
        const card = document.createElement('div');
        card.className = 'movie-card';
        card.onclick = () => showDetailsModal(item.id, item.media_type || mediaType);

        const poster = item.poster_url || 'https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?q=80&w=500&auto=format&fit=crop';
        const rating = item.vote_average ? item.vote_average.toFixed(1) : 'N/A';
        const dateStr = item.display_date || '';
        const releaseYear = dateStr ? dateStr.substring(0, 4) : 'N/A';
        const mediaLabel = (item.media_type || mediaType) === 'movie' ? 'Movie' : 'Series';
        const mediaClass = (item.media_type || mediaType) === 'movie' ? 'movie' : 'tv';
        const mediaIcon = (item.media_type || mediaType) === 'movie' ? 'fa-film' : 'fa-tv';

        card.innerHTML = `
            <div class="card-img-wrap">
                <img src="${poster}" alt="${item.display_title}" loading="lazy">
                <div class="card-badge ${mediaClass}">
                    <i class="fas ${mediaIcon}"></i> ${mediaLabel}
                </div>
            </div>
            <div class="movie-info">
                <h3>${item.display_title}</h3>
                <div class="movie-meta">
                    <span>${releaseYear}</span>
                    <span class="rating">
                        <i class="fas fa-star"></i> ${rating}
                    </span>
                </div>
            </div>
        `;
        grid.appendChild(card);
    });
}

// Pagination adjustments
function changePage(step) {
    currentPage += step;
    loadContent();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Detail display overlays
async function showDetailsModal(id, mType) {
    const modal = document.getElementById('movieModal');
    const detailsDiv = document.getElementById('movieDetails');

    modal.style.display = 'block';
    document.body.style.overflow = 'hidden'; // Lock background scroll
    detailsDiv.innerHTML = '<div class="loading" style="padding: 100px 0;"><i class="fas fa-spinner fa-spin"></i><p>Retrieving title contents...</p></div>';

    try {
        const response = await fetch(`/api/${mType}/${id}`);
        if (!response.ok) throw new Error('API Error');
        const item = await response.json();

        const genres = item.genres ? item.genres.map(g => `<span class="modal-genre-tag">${g.name}</span>`).join('') : '';
        const rating = item.vote_average ? item.vote_average.toFixed(1) : 'N/A';
        const backdrop = item.backdrop_path ? `https://image.tmdb.org/t/p/original${item.backdrop_path}` : 'https://images.unsplash.com/photo-1536440136628-849c177e76a1?q=80&w=1200=format&fit=crop';
        const poster = item.poster_url || 'https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?q=80&w=500&auto=format&fit=crop';
        const timeline = item.timeline_detail || 'N/A';
        const releaseDate = item.display_date || 'N/A';

        // Watch Providers
        let providersHtml = '';
        if (item.watch_providers && item.watch_providers.length > 0) {
            providersHtml = `
                <div class="watch-providers-box">
                    <h4><i class="fas fa-play"></i> Streaming On</h4>
                    <div class="providers-grid">
                        ${item.watch_providers.map(p => `
                            <div class="provider-badge" title="${p.provider_name} (${p.region})">
                                <img src="${p.logo_url}" alt="${p.provider_name}">
                                <span>${p.provider_name}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        } else {
            providersHtml = `
                <div class="watch-providers-box">
                    <h4><i class="fas fa-exclamation-circle" style="color: var(--text-muted);"></i> Streaming</h4>
                    <p style="font-size: 0.85rem; color: var(--text-muted);">Only available for purchase/rent or not streaming currently.</p>
                </div>
            `;
        }

        // Trailer Iframe
        const trailerHtml = item.trailer ? `
            <div class="trailer-section">
                <h4><i class="fab fa-youtube"></i> Dynamic Trailer</h4>
                <div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);">
                    <iframe style="position: absolute; top:0; left:0; width:100%; height:100%;" src="https://www.youtube.com/embed/${item.trailer.key}" frameborder="0" allowfullscreen></iframe>
                </div>
            </div>
        ` : '';

        // Recommendations list
        const recsHtml = item.recs && item.recs.length > 0 ? `
            <div class="recs-section">
                <h4><i class="fas fa-star-half-alt"></i> Suggested Matches</h4>
                <div class="recs-grid">
                    ${item.recs.map(rec => `
                        <div class="rec-card" onclick="showDetailsModal(${rec.id}, '${mType}')">
                            <img src="${rec.poster_url || 'https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?q=80&w=200'}" alt="${rec.display_title}">
                            <p>${rec.display_title}</p>
                        </div>
                    `).join('')}
                </div>
            </div>
        ` : '';

        detailsDiv.innerHTML = `
            <div class="modal-hero" style="background-image: url('${backdrop}');"></div>
            <div class="detail-layout">
                <div class="detail-poster-wrap">
                    <img src="${poster}" alt="${item.display_title}">
                </div>
                <div class="detail-info">
                    <div class="detail-title">
                        <h2>${item.display_title}</h2>
                        ${item.tagline ? `<p class="detail-tagline">"${item.tagline}"</p>` : ''}
                    </div>
                    <div class="detail-meta-row">
                        <span><i class="fas fa-calendar"></i> ${releaseDate}</span>
                        <span><i class="fas fa-clock"></i> ${timeline}</span>
                        <span class="rating-val"><i class="fas fa-star"></i> ${rating} / 10</span>
                    </div>
                    <div class="tag-container">${genres}</div>
                    <p class="modal-overview">${item.overview || 'Synopsis not available.'}</p>
                    
                    ${providersHtml}
                </div>
            </div>
            <div class="modal-multimedia">
                ${trailerHtml}
                ${recsHtml}
            </div>
        `;
    } catch (err) {
        console.error('Error loading detail item:', err);
        detailsDiv.innerHTML = '<p style="text-align: center; padding: 40px; color: #ff5252;">Failed to retrieve details. Try again.</p>';
    }
}

// Close Modal
function closeModal() {
    document.getElementById('movieModal').style.display = 'none';
    document.body.style.overflow = 'auto'; // Restore background scroll
}

window.onclick = function (event) {
    const modal = document.getElementById('movieModal');
    if (event.target === modal) {
        closeModal();
    }
}

// Reset filters to defaults
function resetFilters() {
    mediaType = 'movie';
    selectedGenreId = null;
    minYear = 1991;
    maxYear = 2026;
    currentPage = 1;
    currentQuery = '';
    currentCategory = 'trending';
    activeCuratedCollection = null;

    // Reset UI bindings
    document.getElementById('btnMovie').classList.add('active');
    document.getElementById('btnTV').classList.remove('active');
    document.getElementById('searchInput').value = '';
    document.querySelectorAll('.genre-card').forEach(c => c.classList.remove('active'));
    deactivateCuratedButtons();

    document.getElementById('qPopular').classList.remove('active');
    document.getElementById('qTopRated').classList.remove('active');

    initializeSliders();
    updateCategorySubHeader();
    loadContent();
}

// Surprise me button triggers random selections
async function surpriseMe() {
    const grid = document.getElementById('moviesGrid');
    grid.innerHTML = '<div class="loading"><i class="fas fa-random fa-spin"></i><p>Spinning the wheel of movies...</p></div>';

    try {
        const response = await fetch(`/api/${mediaType}/trending`);
        const data = await response.json();

        if (data.results && data.results.length > 0) {
            // Pick a random offset
            const items = data.results.filter(m => m.poster_url);
            const shuffled = items.sort(() => 0.5 - Math.random());
            const selection = shuffled.slice(0, 10);
            renderCards(selection);
            document.getElementById('catalogTitle').innerHTML = `💡 Lucky Picks: Curated For You`;
            document.getElementById('paginationControls').style.display = 'none';
        } else {
            loadContent();
        }
    } catch (e) {
        console.error(e);
        loadContent();
    }
}
