// State variables
let mediaType = 'movie'; // 'movie' or 'tv'
let selectedGenreId = null;
let selectedProviderId = null;
let minYear = 1991;
let maxYear = 2026;
let currentPage = 1;
let currentQuery = '';
let currentCategory = 'trending'; // 'trending', 'popular', 'top_rated', 'curated'
let activeCuratedCollection = null;

// Watchlist Shelf lists
let watchlist = JSON.parse(localStorage.getItem('watchlist')) || [];
let favorites = JSON.parse(localStorage.getItem('favorites')) || [];
let activeDrawerTab = 'watchlist';

// Debouncer timeout
let searchSuggestTimeout = null;

// YouTube Custom Player state
let ytPlayer = null;
let ytPlayerTimer = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeSliders();
    setupSearch();
    loadContent();
    setupSuggestions();
    updateShelfCounts();
    renderShelfDrawer();
    checkSharedURL(); // Check if viewing a shared playlist
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

// Search interaction & suggestions setup
function setupSearch() {
    const input = document.getElementById('searchInput');
    const btn = document.getElementById('searchBtn');

    btn.addEventListener('click', performSearch);
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            performSearch();
            closeSuggestions();
        }
    });
}

function setupSuggestions() {
    const input = document.getElementById('searchInput');
    const box = document.getElementById('suggestionsBox');

    input.addEventListener('input', () => {
        clearTimeout(searchSuggestTimeout);
        const query = input.value.trim();

        if (query.length < 2) {
            closeSuggestions();
            return;
        }

        searchSuggestTimeout = setTimeout(async () => {
            try {
                const response = await fetch(`/api/${mediaType}/search?query=${encodeURIComponent(query)}&year_start=${minYear}&year_end=${maxYear}&page=1`);
                if (response.ok) {
                    const data = await response.json();
                    renderSuggestions(data.results || []);
                }
            } catch (err) {
                console.error('Error fetching suggestions:', err);
            }
        }, 250);
    });

    // Close suggestions on clicking outside
    document.addEventListener('click', (e) => {
        if (!input.contains(e.target) && !box.contains(e.target)) {
            closeSuggestions();
        }
    });
}

function renderSuggestions(items) {
    const box = document.getElementById('suggestionsBox');
    if (!items || items.length === 0) {
        closeSuggestions();
        return;
    }

    box.innerHTML = '';
    // Show top 5 suggestions
    items.slice(0, 5).forEach(item => {
        const div = document.createElement('div');
        div.className = 'suggestion-item';
        div.onclick = () => {
            showDetailsModal(item.id, item.media_type || mediaType);
            document.getElementById('searchInput').value = item.display_title;
            closeSuggestions();
        };

        const poster = item.poster_url || 'https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?q=80&w=150';
        const year = item.display_date ? item.display_date.substring(0, 4) : 'N/A';
        const rating = item.vote_average ? item.vote_average.toFixed(1) : '0.0';

        div.innerHTML = `
            <img src="${poster}" class="suggestion-poster" alt="${item.display_title}">
            <div class="suggestion-info">
                <span class="suggestion-title">${item.display_title}</span>
                <div class="suggestion-meta">
                    <span>${year}</span>
                    <span class="suggestion-ratio"><i class="fas fa-star"></i> ${rating}</span>
                </div>
            </div>
        `;
        box.appendChild(div);
    });

    box.style.display = 'block';
}

function closeSuggestions() {
    document.getElementById('suggestionsBox').style.display = 'none';
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
    // 1.5. Mood Discovery active
    else if (currentCategory === 'mood') {
        url = `/api/discover/mood?mood=${activeMood}`;
    }
    // 2. Curated collections active
    else if (currentCategory === 'curated') {
        url = `/api/curated/${activeCuratedCollection}`;
    }
    // 3. Discovery Filter (Genre selection, Streaming providers, and/or Year range adjustments)
    else if (currentCategory === 'discover' || selectedGenreId !== null || selectedProviderId !== null) {
        let extraParams = '';
        if (selectedGenreId !== null) {
            extraParams += `&with_genres=${getGenreMapping(selectedGenreId, mediaType)}`;
        }
        if (selectedProviderId !== null) {
            extraParams += `&with_watch_providers=${selectedProviderId}`;
        }
        url = `/api/${mediaType}/discover?year_start=${minYear}&year_end=${maxYear}${extraParams}&page=${currentPage}`;
    }
    // 4. Default categories (trending, popular, top_rated)
    else {
        url = `/api/${mediaType}/${currentCategory}?page=${currentPage}`;
    }

    try {
        const response = await fetch(url);
        const data = await response.json();

        if (!response.ok) {
            const errorMsg = data.error || 'Server error. Please try again later.';
            grid.innerHTML = `
                <div class="loading">
                    <i class="fas fa-exclamation-triangle" style="font-size: 2.5rem; color: #ff5252;"></i>
                    <p style="margin-top: 15px; color: #ff5252; text-align: center; font-weight: 500;">${errorMsg}</p>
                </div>`;
            return;
        }

        if (data.results && data.results.length > 0) {
            renderCards(data.results);

            // Manage pagination details (curated, shared, and mood lists don't use pages)
            if (currentCategory !== 'curated' && currentCategory !== 'shared' && currentCategory !== 'mood') {
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
        grid.innerHTML = '<p class="error-text" style="color: #ff5252; text-align: center; grid-column: 1/-1;">Connection lost with server. Please try again later.</p>';
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

        // Check if item is already in watchlist or favorites
        const inWatchlist = watchlist.some(m => m.id === item.id && m.type === mType);
        const inFavorites = favorites.some(m => m.id === item.id && m.type === mType);

        // Watch Providers
        let providersHtml = '';
        if (item.watch_providers && item.watch_providers.length > 0) {
            const region = item.watch_providers[0].region || 'IN';
            const regionLabel = ` (${region})`;

            const flatrate = item.watch_providers.filter(p => p.type === 'flatrate');
            const freeAds = item.watch_providers.filter(p => p.type === 'free' || p.type === 'ads');
            const rentBuy = item.watch_providers.filter(p => p.type === 'rent' || p.type === 'buy');

            let sectionsHtml = '';
            if (flatrate.length > 0) {
                sectionsHtml += `
                    <div class="provider-category">
                        <h5><i class="fas fa-tv"></i> Stream / Subscription</h5>
                        <div class="providers-grid">
                            ${flatrate.map(p => `
                                <div class="provider-badge" title="${p.provider_name}">
                                    <img src="${p.logo_url}" alt="${p.provider_name}">
                                    <span>${p.provider_name}</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `;
            }
            if (freeAds.length > 0) {
                sectionsHtml += `
                    <div class="provider-category">
                        <h5><i class="fas fa-gift"></i> Free / Ads</h5>
                        <div class="providers-grid">
                            ${freeAds.map(p => `
                                <div class="provider-badge" title="${p.provider_name}">
                                    <img src="${p.logo_url}" alt="${p.provider_name}">
                                    <span>${p.provider_name}</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `;
            }
            if (rentBuy.length > 0) {
                sectionsHtml += `
                    <div class="provider-category">
                        <h5><i class="fas fa-shopping-bag"></i> Rent / Buy</h5>
                        <div class="providers-grid">
                            ${rentBuy.map(p => `
                                <div class="provider-badge" title="${p.provider_name}">
                                    <img src="${p.logo_url}" alt="${p.provider_name}">
                                    <span>${p.provider_name}</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `;
            }

            providersHtml = `
                <div class="watch-providers-box">
                    <h4><i class="fas fa-play"></i> Where to Watch${regionLabel}</h4>
                    <div class="providers-container">
                        ${sectionsHtml}
                    </div>
                </div>
            `;
        } else {
            providersHtml = `
                <div class="watch-providers-box">
                    <h4><i class="fas fa-exclamation-circle" style="color: var(--text-muted);"></i> Where to Watch</h4>
                    <p style="font-size: 0.85rem; color: var(--text-muted);">Not available for streaming, rent, or buy currently in supported regions.</p>
                </div>
            `;
        }

        // Custom Action Bar (Trailer button + Shelf controls)
        const actionButtonsHtml = `
            <div class="modal-actions-bar">
                ${item.trailer ? `
                    <button class="btn btn-trailer" onclick="openCustomPlayer('${item.trailer.key}')">
                        <i class="fas fa-play-circle"></i> Watch Trailer
                    </button>
                ` : ''}
                <button class="btn-shelf watchlist ${inWatchlist ? 'active' : ''}" onclick="toggleShelfItem('watchlist', ${item.id}, \`${item.display_title.replace(/'/g, "\\'")}\`, '${poster}', '${mType}')">
                    <i class="fas ${inWatchlist ? 'fa-check' : 'fa-bookmark'}"></i> ${inWatchlist ? 'In Watchlist' : 'Add to Watchlist'}
                </button>
                <button class="btn-shelf favorite ${inFavorites ? 'active' : ''}" onclick="toggleShelfItem('favorites', ${item.id}, \`${item.display_title.replace(/'/g, "\\'")}\`, '${poster}', '${mType}')">
                    <i class="fas fa-heart"></i> ${inFavorites ? 'Favorited' : 'Favorite'}
                </button>
            </div>
        `;

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
                    
                    ${actionButtonsHtml}
                    ${providersHtml}
                </div>
            </div>
            <div class="modal-multimedia">
                ${recsHtml}
            </div>
        `;

        // Extract dominant color for ambient glow backdrop using canvas
        if (poster && poster.startsWith('http')) {
            const tempImg = new Image();
            tempImg.crossOrigin = "Anonymous";
            tempImg.src = poster;
            tempImg.onload = () => {
                try {
                    const canvas = document.createElement('canvas');
                    canvas.width = 10;
                    canvas.height = 10;
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(tempImg, 0, 0, 10, 10);
                    const imgData = ctx.getImageData(0, 0, 10, 10).data;

                    let r = 0, g = 0, b = 0, count = 0;
                    for (let i = 0; i < imgData.length; i += 4) {
                        if (imgData[i] + imgData[i + 1] + imgData[i + 2] > 35) {
                            r += imgData[i];
                            g += imgData[i + 1];
                            b += imgData[i + 2];
                            count++;
                        }
                    }
                    if (count > 0) {
                        r = Math.floor(r / count);
                        g = Math.floor(g / count);
                        b = Math.floor(b / count);
                    } else {
                        r = 124; g = 77; b = 255;
                    }
                    const glowVal = document.querySelector('.modal-ambient-glow');
                    if (glowVal) {
                        glowVal.style.background = `radial-gradient(circle, rgba(${r}, ${g}, ${b}, 0.5) 0%, rgba(20, 20, 35, 0) 75%)`;
                    }
                } catch (chgErr) {
                    console.warn("Ambient backlight canvas failed:", chgErr);
                }
            };
        }
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
    selectedProviderId = null;
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
    document.querySelectorAll('.provider-card').forEach(c => c.classList.remove('active'));
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

/* ==========================================
   Chatbot Widget Script (MovieBot)
   ========================================== */
let chatbotHistory = [];

function toggleChatbot() {
    const windowEl = document.getElementById('chatbotWindow');
    windowEl.classList.toggle('active');

    // Auto focus input if active
    if (windowEl.classList.contains('active')) {
        document.getElementById('chatbotInput').focus();

        // Show greeting on first load if messages empty
        const messagesDiv = document.getElementById('chatbotMessages');
        if (messagesDiv.children.length === 0) {
            addBotMessage("Hello! How can I help you to watch a movie or series? 🍿🎬");
        }
    }
}

function addBotMessage(text) {
    const messagesDiv = document.getElementById('chatbotMessages');
    const msgEl = document.createElement('div');
    msgEl.className = 'chat-msg bot';
    msgEl.innerHTML = formatBotMessage(text);

    messagesDiv.appendChild(msgEl);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function addUserMessage(text) {
    const messagesDiv = document.getElementById('chatbotMessages');
    const msgEl = document.createElement('div');
    msgEl.className = 'chat-msg user';
    msgEl.innerText = text;

    messagesDiv.appendChild(msgEl);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function handleChatbotKey(event) {
    if (event.key === 'Enter') {
        sendChatbotMessage();
    }
}

async function sendChatbotMessage() {
    const inputEl = document.getElementById('chatbotInput');
    const userText = inputEl.value.trim();
    if (!userText) return;

    // Clear input
    inputEl.value = '';

    // Display user message
    addUserMessage(userText);

    // Show typing loader
    showTypingIndicator();

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: userText,
                history: chatbotHistory
            })
        });

        hideTypingIndicator();

        if (response.ok) {
            const data = await response.json();
            const botResponse = data.response;

            // Add bot message
            addBotMessage(botResponse);

            // Save to JS chat history state
            chatbotHistory.push({
                role: 'user',
                parts: [{ text: userText }]
            });
            chatbotHistory.push({
                role: 'model',
                parts: [{ text: botResponse }]
            });

            // Restrict size of local client-side history state
            if (chatbotHistory.length > 20) {
                chatbotHistory = chatbotHistory.slice(-20);
            }
        } else {
            console.error('Server error response');
            addBotMessage("Sorry, I'm having trouble getting suggestions right now. Please try again! 😥🍿");
        }
    } catch (error) {
        console.error('Network error calling chatbot API:', error);
        hideTypingIndicator();
        addBotMessage("Oops, I lost connection to the server. Please check your network and try again! 🔌❌");
    }
}

function showTypingIndicator() {
    const messagesDiv = document.getElementById('chatbotMessages');
    // Ensure doesn't double-show
    if (document.getElementById('chatbotTyping')) return;

    const indicator = document.createElement('div');
    indicator.className = 'typing-indicator-container';
    indicator.id = 'chatbotTyping';
    indicator.innerHTML = `
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
    `;

    messagesDiv.appendChild(indicator);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function hideTypingIndicator() {
    const indicator = document.getElementById('chatbotTyping');
    if (indicator) {
        indicator.remove();
    }
}

function formatBotMessage(text) {
    // Escape HTML tags to prevent XSS
    let formatted = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    // Bold: **text** -> <strong>text</strong>
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Convert newlines to breaks first or process lists
    const lines = formatted.split('\n');
    let inList = false;
    let result = [];

    for (let line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith('* ') || trimmed.startsWith('- ')) {
            if (!inList) {
                result.push('<ul>');
                inList = true;
            }
            const content = trimmed.substring(2);
            result.push(`<li>${content}</li>`);
        } else {
            if (inList) {
                result.push('</ul>');
                inList = false;
            }
            result.push(line);
        }
    }
    if (inList) {
        result.push('</ul>');
    }

    formatted = result.join('<br>').replace(/<\/ul><br>/g, '</ul>').replace(/<br><ul>/g, '<ul>');

    // Parse Interactive Pills: [Title (Year)](show-media:movie:12345)
    formatted = formatted.replace(/\[([^\]]+)\]\(show-media:(movie|tv):(\d+)\)/g,
        `<button class="chat-media-pill" onclick="showDetailsModal($3, '$2')"><i class="fas fa-film"></i> $1</button>`
    );

    // Parse Search Pills: [Title (Year)](search-media:movie:Joker)
    formatted = formatted.replace(/\[([^\]]+)\]\(search-media:(movie|tv):([^)]+)\)/g,
        `<button class="chat-media-pill" onclick="triggerPillSearch('$3', '$2')"><i class="fas fa-search"></i> $1</button>`
    );

    return formatted;
}

/* ==========================================================================
   Watchlist Drawer Controllers
   ========================================================================== */
function toggleWatchlistDrawer() {
    const drawer = document.getElementById('watchlistDrawer');
    drawer.classList.toggle('active');
}

function switchDrawerTab(tab) {
    activeDrawerTab = tab;
    document.getElementById('tabWatchlist').classList.toggle('active', tab === 'watchlist');
    document.getElementById('tabFavorites').classList.toggle('active', tab === 'favorites');
    renderShelfDrawer();
}

function toggleShelfItem(shelf, id, title, poster, type) {
    let list = shelf === 'watchlist' ? watchlist : favorites;
    const index = list.findIndex(m => m.id === id && m.type === type);

    if (index > -1) {
        // Remove item
        list.splice(index, 1);
    } else {
        // Add item
        list.push({ id, title, poster, type });
    }

    // Save to LocalStorage
    localStorage.setItem(shelf, JSON.stringify(list));

    // Update state
    updateShelfCounts();
    renderShelfDrawer();

    // Toggle button state in detail modal
    const btn = document.querySelector(`.btn-shelf.${shelf === 'watchlist' ? 'watchlist' : 'favorite'}`);
    if (btn) {
        const isActive = index === -1;
        btn.classList.toggle('active', isActive);
        if (shelf === 'watchlist') {
            btn.innerHTML = `<i class="fas ${isActive ? 'fa-check' : 'fa-bookmark'}"></i> ${isActive ? 'In Watchlist' : 'Add to Watchlist'}`;
        } else {
            btn.innerHTML = `<i class="fas fa-heart"></i> ${isActive ? 'Favorited' : 'Favorite'}`;
        }
    }
}

function updateShelfCounts() {
    document.getElementById('watchlistCount').innerText = watchlist.length;
}

function renderShelfDrawer() {
    const container = document.getElementById('drawerItems');
    const items = activeDrawerTab === 'watchlist' ? watchlist : favorites;

    if (!items || items.length === 0) {
        container.innerHTML = `<p class="drawer-empty-msg">Your ${activeDrawerTab} is empty. Add movies/series from details page!</p>`;
        return;
    }

    container.innerHTML = '';
    items.forEach(item => {
        const card = document.createElement('div');
        card.className = 'drawer-card';
        card.onclick = (e) => {
            if (!e.target.closest('.drawer-card-remove')) {
                showDetailsModal(item.id, item.type);
                toggleWatchlistDrawer();
            }
        };

        const mediaLabel = item.type === 'movie' ? 'Movie' : 'Series';
        const mediaClass = item.type === 'movie' ? 'movie' : 'tv';
        const mediaIcon = item.type === 'movie' ? 'fa-film' : 'fa-tv';

        card.innerHTML = `
            <img src="${item.poster}" alt="${item.title}">
            <div class="drawer-card-info">
                <span class="drawer-card-title">${item.title}</span>
                <span class="drawer-card-meta ${mediaClass}"><i class="fas ${mediaIcon}"></i> ${mediaLabel}</span>
            </div>
            <button class="drawer-card-remove" onclick="toggleShelfItem('${activeDrawerTab}', ${item.id}, '', '', '${item.type}'); event.stopPropagation();"><i class="fas fa-trash"></i></button>
        `;
        container.appendChild(card);
    });
}

function triggerPillSearch(query, type) {
    setMediaType(type);
    document.getElementById('searchInput').value = query;
    performSearch();
    // toggle bot window closed to show results
    const chatbotWindow = document.getElementById('chatbotWindow');
    if (chatbotWindow.classList.contains('active')) {
        toggleChatbot();
    }
}

/* ==========================================================================
   Fluid Custom YouTube Video Player Controllers
   ========================================================================== */
function openCustomPlayer(videoId) {
    const modal = document.getElementById('customPlayerModal');
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden'; // lock background

    // If player not initialized yet
    if (!ytPlayer) {
        ytPlayer = new YT.Player('customYoutubePlayer', {
            videoId: videoId,
            playerVars: {
                'autoplay': 1,
                'controls': 0, // Disable standard Youtube controls
                'showinfo': 0,
                'rel': 0,
                'modestbranding': 1,
                'iv_load_policy': 3
            },
            events: {
                'onReady': (event) => {
                    event.target.playVideo();
                    startTimelineTimer();
                },
                'onStateChange': onPlayerStateChange
            }
        });
    } else {
        // Load active video ID
        ytPlayer.loadVideoById(videoId);
        ytPlayer.playVideo();
        startTimelineTimer();
    }

    // Reset controls UI
    document.getElementById('customPlayBtn').innerHTML = '<i class="fas fa-pause"></i>';
    document.getElementById('customVolumeSlider').value = 100;
}

function closeCustomPlayer() {
    const modal = document.getElementById('customPlayerModal');
    modal.style.display = 'none';

    // If not showing detail modal, restore scroll
    const detailModal = document.getElementById('movieModal');
    if (detailModal.style.display !== 'block') {
        document.body.style.overflow = 'auto';
    }

    if (ytPlayer && typeof ytPlayer.pauseVideo === 'function') {
        ytPlayer.pauseVideo();
    }
    clearInterval(ytPlayerTimer);
}

function onPlayerStateChange(event) {
    const playBtn = document.getElementById('customPlayBtn');
    if (event.data === YT.PlayerState.PLAYING) {
        playBtn.innerHTML = '<i class="fas fa-pause"></i>';
        startTimelineTimer();
    } else {
        playBtn.innerHTML = '<i class="fas fa-play"></i>';
        if (event.data === YT.PlayerState.PAUSED || event.data === YT.PlayerState.ENDED) {
            clearInterval(ytPlayerTimer);
        }
    }
}

function toggleCustomPlay() {
    if (!ytPlayer) return;
    const state = ytPlayer.getPlayerState();
    if (state === YT.PlayerState.PLAYING) {
        ytPlayer.pauseVideo();
    } else {
        ytPlayer.playVideo();
    }
}

function toggleCustomMute() {
    if (!ytPlayer) return;
    const muteBtn = document.getElementById('customMuteBtn');
    const volSlider = document.getElementById('customVolumeSlider');

    if (ytPlayer.isMuted()) {
        ytPlayer.unMute();
        muteBtn.innerHTML = '<i class="fas fa-volume-up"></i>';
        volSlider.value = ytPlayer.getVolume();
    } else {
        ytPlayer.mute();
        muteBtn.innerHTML = '<i class="fas fa-volume-mute"></i>';
        volSlider.value = 0;
    }
}

function changeCustomVolume(val) {
    if (!ytPlayer) return;
    ytPlayer.setVolume(val);
    const muteBtn = document.getElementById('customMuteBtn');
    if (val == 0) {
        ytPlayer.mute();
        muteBtn.innerHTML = '<i class="fas fa-volume-mute"></i>';
    } else {
        ytPlayer.unMute();
        muteBtn.innerHTML = val < 50 ? '<i class="fas fa-volume-down"></i>' : '<i class="fas fa-volume-up"></i>';
    }
}

function seekCustomPlayer(event) {
    if (!ytPlayer) return;
    const tracker = event.currentTarget;
    const rect = tracker.getBoundingClientRect();
    const offsetX = event.clientX - rect.left;
    const percentage = offsetX / rect.width;

    const duration = ytPlayer.getDuration();
    if (duration > 0) {
        const seekTime = duration * percentage;
        ytPlayer.seekTo(seekTime, true);
        updateProgressBar();
    }
}

function startTimelineTimer() {
    clearInterval(ytPlayerTimer);
    ytPlayerTimer = setInterval(updateProgressBar, 500);
}

function updateProgressBar() {
    if (!ytPlayer || typeof ytPlayer.getCurrentTime !== 'function') return;

    const currentTime = ytPlayer.getCurrentTime();
    const duration = ytPlayer.getDuration();

    if (duration > 0) {
        const pct = (currentTime / duration) * 100;
        document.getElementById('customProgressBar').style.width = `${pct}%`;
        document.getElementById('customTimeText').innerText = `${formatPlayerTime(currentTime)} / ${formatPlayerTime(duration)}`;
    }
}

function formatPlayerTime(sec) {
    const mins = Math.floor(sec / 60);
    const secs = Math.floor(sec % 60);
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
}

function toggleCustomFullscreen() {
    const wrapper = document.querySelector('.custom-video-wrapper');
    if (!document.fullscreenElement) {
        wrapper.requestFullscreen().catch(err => {
            console.error(`Error enabling fullscreen: ${err.message}`);
        });
    } else {
        document.exitFullscreen();
    }
}

/* ==========================================================================
   Watch Provider Actions
   ========================================================================== */
function toggleProvider(providerId, providerName) {
    const element = document.getElementById(`prov-${providerName}`);

    // Toggle active state
    if (selectedProviderId === providerId) {
        selectedProviderId = null;
        element.classList.remove('active');
    } else {
        selectedProviderId = providerId;
        // deactivate other providers (since we only support single provider filtering at a time for ease of UI)
        document.querySelectorAll('.provider-card').forEach(c => c.classList.remove('active'));
        element.classList.add('active');

        // Deactivate search queries / curated lists so streaming filters are prioritized
        currentQuery = '';
        document.getElementById('searchInput').value = '';
        activeCuratedCollection = null;
        deactivateCuratedButtons();
    }

    currentPage = 1;
    currentCategory = selectedProviderId ? 'discover' : 'trending';
    updateCategorySubHeader();
    loadContent();
}

/* ==========================================================================
   Mood Discovery Feature
   ========================================================================== */
let activeMood = null;

async function discoverByMood(mood) {
    const card = document.getElementById(`mood-${mood}`);

    // Toggle active state
    if (activeMood === mood) {
        activeMood = null;
        card.classList.remove('active');
        currentCategory = 'trending';
        document.getElementById('catalogTitle').innerText = 'Trending Right Now';
    } else {
        activeMood = mood;
        document.querySelectorAll('.mood-card').forEach(c => c.classList.remove('active'));
        card.classList.add('active');

        // Deactivate search queries / curated lists / provider filters
        currentQuery = '';
        document.getElementById('searchInput').value = '';
        selectedProviderId = null;
        document.querySelectorAll('.provider-card').forEach(c => c.classList.remove('active'));
        activeCuratedCollection = null;
        deactivateCuratedButtons();

        currentCategory = 'mood';
        document.getElementById('catalogTitle').innerText = `Mood: ${mood.toUpperCase()}`;
    }

    currentPage = 1;
    updateCategorySubHeader();
    loadContent();
}

/* ==========================================================================
   Tinder-Style AI Quick Matcher Quiz
   ========================================================================== */
let matcherDeckList = [];
let matcherIndex = 0;
let matcherLikes = [];
let matcherDislikes = [];

function toggleQuickMatcher() {
    const overlay = document.getElementById('matcherOverlay');
    if (overlay.style.display === 'none') {
        overlay.style.display = 'flex';
        document.body.style.overflow = 'hidden';
        startQuickMatcherQuiz();
    } else {
        overlay.style.display = 'none';
        if (document.getElementById('movieModal').style.display !== 'block') {
            document.body.style.overflow = 'auto';
        }
    }
}

async function startQuickMatcherQuiz() {
    const deckContainer = document.getElementById('matcherDeck');
    deckContainer.innerHTML = '<div class="loading" style="padding-top: 100px;"><i class="fas fa-spinner fa-spin"></i><p>Generating card deck...</p></div>';

    matcherDeckList = [];
    matcherIndex = 0;
    matcherLikes = [];
    matcherDislikes = [];

    try {
        // Fetch trending items to swipe on
        const response = await fetch(`/api/movie/trending?page=1`);
        if (!response.ok) throw new Error('API Error');
        const data = await response.json();

        const rawItems = data.results || [];
        matcherDeckList = rawItems.filter(item => item.poster_path).slice(0, 10);

        renderMatcherDeck();
    } catch (e) {
        deckContainer.innerHTML = '<p style="padding-top: 100px; color: var(--text-muted);">Failed to load matcher deck.</p>';
    }
}

function renderMatcherDeck() {
    const deckContainer = document.getElementById('matcherDeck');
    const countDisplay = document.getElementById('matcherDeckCount');

    deckContainer.innerHTML = '';
    const itemsLeft = matcherDeckList.length - matcherIndex;
    countDisplay.innerText = itemsLeft;

    if (itemsLeft <= 0) {
        deckContainer.innerHTML = `
            <div class="matcher-deck-empty">
                <i class="fas fa-check-circle"></i>
                <h4>Deck Complete!</h4>
                <p>Ready to recommend titles matching your profile.</p>
                <button class="btn btn-generate-rec" onclick="getQuizRecommendations()">
                    <i class="fas fa-sparkles"></i> Generate AI Picks
                </button>
            </div>
        `;
        document.getElementById('matcherControls').style.opacity = '0.3';
        document.getElementById('matcherControls').querySelectorAll('button').forEach(b => b.disabled = true);
        return;
    }

    document.getElementById('matcherControls').style.opacity = '1';
    document.getElementById('matcherControls').querySelectorAll('button').forEach(b => b.disabled = false);

    for (let i = matcherDeckList.length - 1; i >= matcherIndex; i--) {
        const item = matcherDeckList[i];
        const card = document.createElement('div');
        card.className = `matcher-card`;
        card.id = `m-card-${i}`;

        const offset = (i - matcherIndex) * 8;
        const scale = 1 - (i - matcherIndex) * 0.05;
        card.style.transform = `translateY(${offset}px) scale(${scale})`;
        card.style.zIndex = matcherDeckList.length - i;

        const posterUrl = item.poster_url || 'https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?q=80&w=300';
        const date = item.display_date ? item.display_date.substring(0, 4) : 'N/A';
        const rating = item.vote_average ? item.vote_average.toFixed(1) : '0';

        card.innerHTML = `
            <img src="${posterUrl}" alt="${item.display_title}">
            <div class="matcher-card-info">
                <div class="matcher-card-title">${item.display_title}</div>
                <div class="matcher-card-meta"><i class="fas fa-calendar"></i> ${date} &bull; <i class="fas fa-star" style="color:#ffb300"></i> ${rating}</div>
            </div>
        `;

        deckContainer.appendChild(card);
    }
}

function swipeMatcherCard(direction) {
    if (matcherIndex >= matcherDeckList.length) return;

    const card = document.getElementById(`m-card-${matcherIndex}`);
    const swipedItem = matcherDeckList[matcherIndex];

    if (direction === 'like') {
        card.classList.add('swipe-like');
        matcherLikes.push(swipedItem.display_title);
    } else if (direction === 'dislike') {
        card.classList.add('swipe-dislike');
        matcherDislikes.push(swipedItem.display_title);
    } else {
        card.classList.add('swipe-skip');
    }

    matcherIndex++;
    setTimeout(() => {
        renderMatcherDeck();
    }, 400);
}

async function getQuizRecommendations() {
    toggleQuickMatcher();

    const triggerMessage = `Recommend movies based on my preferences. I liked these: [${matcherLikes.join(', ')}]. I disliked these: [${matcherDislikes.join(', ')}].`;

    const chatWindow = document.getElementById('chatbotWindow');
    chatWindow.classList.add('active');

    addUserMessage("Match recommendations for my swiped items! 🍿");
    showTypingIndicator();

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: triggerMessage,
                history: chatbotHistory
            })
        });

        hideTypingIndicator();
        if (response.ok) {
            const data = await response.json();
            addBotMessage(data.response);

            chatbotHistory.push({ role: 'user', parts: [{ text: triggerMessage }] });
            chatbotHistory.push({ role: 'model', parts: [{ text: data.response }] });
        } else {
            addBotMessage("Sorry! I couldn't crunch your swipe preferences. Try again! 💫");
        }
    } catch (e) {
        hideTypingIndicator();
        addBotMessage("Whoops! There was a network issue analyzing your tastes. 🤖");
    }
}

/* ==========================================================================
   Watchlist Sharing & Shared Banner
   ========================================================================== */
function shareWatchlist(shelf) {
    const list = shelf === 'watchlist' ? watchlist : favorites;
    if (list.length === 0) {
        alert(`Your ${shelf} is currently empty! Add items before sharing.`);
        return;
    }

    try {
        const payload = JSON.stringify({ type: shelf, items: list });
        const hash = btoa(unescape(encodeURIComponent(payload)));
        const shareUrl = `${window.location.origin}${window.location.pathname}?share=${hash}`;

        navigator.clipboard.writeText(shareUrl).then(() => {
            alert(`Link copied to clipboard! Share it with a friend: ${shareUrl}`);
        }).catch(err => {
            prompt("Could not copy automatically. Copy this URL instead:", shareUrl);
        });
    } catch (e) {
        console.error(e);
        alert("Failed to package the list for sharing.");
    }
}

let tempSharedList = null;

function checkSharedURL() {
    const urlParams = new URLSearchParams(window.location.search);
    const shareHash = urlParams.get('share');
    if (!shareHash) return;

    try {
        const decoded = decodeURIComponent(escape(atob(shareHash)));
        const data = JSON.parse(decoded);

        if (data.type && data.items) {
            tempSharedList = data;
            const banner = document.getElementById('sharedPlaylistBanner');
            banner.style.display = 'block';

            currentCategory = 'shared';
            renderCards(data.items);
            document.getElementById('catalogTitle').innerText = `Curated Shared List (${data.type.toUpperCase()})`;
            document.getElementById('paginationControls').style.display = 'none';
        }
    } catch (e) {
        console.error("Error reading shared list URL:", e);
    }
}

function importSharedList() {
    if (!tempSharedList) return;

    const targetShelf = tempSharedList.type;
    const items = tempSharedList.items;

    if (targetShelf === 'watchlist') {
        items.forEach(itm => {
            if (!watchlist.some(w => w.id === itm.id)) {
                watchlist.push(itm);
            }
        });
        localStorage.setItem('watchlist', JSON.stringify(watchlist));
    } else {
        items.forEach(itm => {
            if (!favorites.some(f => f.id === itm.id)) {
                favorites.push(itm);
            }
        });
        localStorage.setItem('favorites', JSON.stringify(favorites));
    }

    updateShelfCounts();
    renderShelfDrawer();
    closeSharedBanner();
    alert("Successfully imported shared items into your drawer collections!");
}

function closeSharedBanner() {
    document.getElementById('sharedPlaylistBanner').style.display = 'none';
    tempSharedList = null;

    currentCategory = 'trending';
    document.getElementById('catalogTitle').innerText = 'Trending Right Now';
    document.getElementById('paginationControls').style.display = 'flex';

    const newurl = window.location.protocol + "//" + window.location.host + window.location.pathname;
    window.history.pushState({ path: newurl }, '', newurl);

    loadContent();
}



