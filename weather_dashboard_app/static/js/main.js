/**
 * =============================================================================
 * SkyPulse Weather Dashboard - Client-Side JavaScript (main.js)
 * =============================================================================
 * Description:
 *   Handles all reactive user interface interactions, asynchronous data
 *   fetching from the Flask backend, SVG icon generation, dynamic gauge
 *   animations, Chart.js hourly area chart rendering, and single-request search.
 *
 * Core Modules:
 *   1. State Management: Tracks active units (°C / °F), coordinates, and cached weather payload.
 *   2. Unit Conversion: Real-time mathematical conversions in memory (no extra API calls).
 *   3. Dynamic SVG Graphics: Weather conditions, 360° rotating compass needle, radial arc gauges.
 *   4. Asynchronous Data Fetching: Calls `/api/weather` and updates the DOM.
 *   5. Hourly Chart: Chart.js cubic-spline temperature & rain probability area chart.
 *   6. Single-Request City Search: Triggers strictly on form submit (Enter/click) with zero requests while typing.
 *   7. HTML5 Geolocation: Native browser GPS location resolution.
 * =============================================================================
 */

// -----------------------------------------------------------------------------
// 1. GLOBAL STATE MANAGEMENT
// -----------------------------------------------------------------------------
let currentUnit = 'C';                 // Active temperature unit: 'C' (Celsius) or 'F' (Fahrenheit)
let currentLat = 52.52;                // Default starting latitude (Berlin, Germany)
let currentLon = 13.41;                // Default starting longitude (Berlin, Germany)
let currentCityName = 'Berlin, Germany';// Currently selected city label
let weatherDataCache = null;           // In-memory cache of the latest API response for instant unit toggling
let hourlyChart = null;                // Reference to the active Chart.js instance (destroyed & redrawn on update)


// -----------------------------------------------------------------------------
// 2. MATHEMATICAL CONVERSION HELPERS
// -----------------------------------------------------------------------------

/**
 * Converts a temperature from Celsius to Fahrenheit.
 * Formula: (°C * 9/5) + 32
 * @param {number} celsius - Temperature in Celsius.
 * @returns {number} Temperature rounded to nearest whole Fahrenheit degree.
 */
function toFahrenheit(celsius) {
  return Math.round((celsius * 9 / 5) + 32);
}

/**
 * Formats a temperature according to the user's active unit preference (°C or °F).
 * @param {number} celsius - Raw temperature in Celsius from Open-Meteo.
 * @returns {string|number} Formatted temperature or '--' placeholder if unavailable.
 */
function formatTemp(celsius) {
  if (celsius === null || celsius === undefined) return '--';
  return currentUnit === 'C' ? Math.round(celsius) : toFahrenheit(celsius);
}

/**
 * Converts wind speed between km/h and mph.
 * 1 km/h = 0.621371 mph
 * @param {number} kmh - Speed in kilometers per hour.
 * @returns {string|number} Converted speed.
 */
function formatWindSpeed(kmh) {
  if (kmh === null || kmh === undefined) return '--';
  return currentUnit === 'C' ? Math.round(kmh) : Math.round(kmh * 0.621371);
}

/**
 * Returns the wind speed unit string based on current unit state.
 * @returns {string} 'km/h' or 'mph'
 */
function getWindUnit() {
  return currentUnit === 'C' ? 'km/h' : 'mph';
}

/**
 * Converts visibility distance between kilometers and miles.
 * @param {number} km - Visibility in kilometers.
 * @returns {string|number} Converted distance.
 */
function formatVisibility(km) {
  if (km === null || km === undefined) return '--';
  return currentUnit === 'C' ? Math.round(km) : Math.round(km * 0.621371);
}

/**
 * Returns the visibility unit string based on current unit state.
 * @returns {string} 'km' or 'mi'
 */
function getVisibilityUnit() {
  return currentUnit === 'C' ? 'km' : 'mi';
}


// -----------------------------------------------------------------------------
// 3. DYNAMIC VECTOR (SVG) WEATHER ICON GENERATOR
// -----------------------------------------------------------------------------

/**
 * Generates responsive SVG markup corresponding to the weather condition key.
 * Distinguishes between daytime and nighttime icons for clear sky conditions.
 * @param {string} iconType - Category string ('sunny', 'cloudy', 'rain', etc.)
 * @param {number} isDay - 1 for daytime, 0 for nighttime.
 * @returns {string} Clean SVG markup string.
 */
function getWeatherIconSvg(iconType, isDay = 1) {
  switch (iconType) {
    case 'sunny':
      // Golden gradient sun for daytime, glowing yellow crescent moon for nighttime
      return isDay ? `
        <svg viewBox="0 0 64 64" width="70" height="70">
          <circle cx="32" cy="32" r="16" fill="url(#sunGradHero)" />
          <defs>
            <radialGradient id="sunGradHero" cx="30%" cy="30%">
              <stop offset="0%" stop-color="#fef08a"/>
              <stop offset="60%" stop-color="#f59e0b"/>
              <stop offset="100%" stop-color="#ea580c"/>
            </radialGradient>
          </defs>
        </svg>
      ` : `
        <svg viewBox="0 0 64 64" width="70" height="70">
          <path d="M44 38A18 18 0 1 1 26 20a14 14 0 0 0 18 18z" fill="#facc15" filter="drop-shadow(0 2px 8px rgba(250, 204, 21, 0.4))"/>
        </svg>
      `;
    case 'partly_cloudy':
      return `
        <svg viewBox="0 0 64 64" width="70" height="70">
          <circle cx="26" cy="26" r="12" fill="#f59e0b"/>
          <path d="M22 48h24a10 10 0 0 0 2-19.8 13 13 0 0 0-25-2.2A9 9 0 0 0 22 48z" fill="#94a3b8" opacity="0.9"/>
        </svg>
      `;
    case 'cloudy':
      return `
        <svg viewBox="0 0 64 64" width="70" height="70">
          <path d="M20 46h26a11 11 0 0 0 2.2-21.8 14 14 0 0 0-27-2.4A10 10 0 0 0 20 46z" fill="#64748b"/>
        </svg>
      `;
    case 'rain':
    case 'showers':
    case 'drizzle':
      return `
        <svg viewBox="0 0 64 64" width="70" height="70">
          <path d="M20 38h24a9 9 0 0 0 2-17.8 12 12 0 0 0-23-2A8 8 0 0 0 20 38z" fill="#475569"/>
          <line x1="22" y1="44" x2="19" y2="52" stroke="#38bdf8" stroke-width="2.5" stroke-linecap="round"/>
          <line x1="32" y1="44" x2="29" y2="52" stroke="#38bdf8" stroke-width="2.5" stroke-linecap="round"/>
          <line x1="42" y1="44" x2="39" y2="52" stroke="#38bdf8" stroke-width="2.5" stroke-linecap="round"/>
        </svg>
      `;
    case 'thunderstorm':
      return `
        <svg viewBox="0 0 64 64" width="70" height="70">
          <path d="M20 36h24a9 9 0 0 0 2-17.8 12 12 0 0 0-23-2A8 8 0 0 0 20 36z" fill="#334155"/>
          <polygon points="31 38 26 47 32 47 28 56 38 45 32 45" fill="#facc15"/>
        </svg>
      `;
    case 'snow':
    case 'heavy_snow':
      return `
        <svg viewBox="0 0 64 64" width="70" height="70">
          <path d="M20 36h24a9 9 0 0 0 2-17.8 12 12 0 0 0-23-2A8 8 0 0 0 20 36z" fill="#94a3b8"/>
          <circle cx="22" cy="46" r="2" fill="#38bdf8"/>
          <circle cx="32" cy="48" r="2.5" fill="#38bdf8"/>
          <circle cx="42" cy="46" r="2" fill="#38bdf8"/>
        </svg>
      `;
    default:
      return `
        <svg viewBox="0 0 64 64" width="70" height="70">
          <circle cx="32" cy="32" r="16" fill="#f59e0b"/>
        </svg>
      `;
  }
}


// -----------------------------------------------------------------------------
// 4. ASYNCHRONOUS WEATHER DATA FETCHER
// -----------------------------------------------------------------------------

/**
 * Calls the Flask backend endpoint `/api/weather` for specific coordinates.
 * Saves the response in `weatherDataCache` and triggers dashboard rendering.
 * @param {number} lat - Geographical latitude.
 * @param {number} lon - Geographical longitude.
 * @param {string} [displayName] - Formatted city, region, and country name.
 */
async function loadWeatherData(lat, lon, displayName) {
  try {
    currentLat = lat;
    currentLon = lon;
    if (displayName) currentCityName = displayName;

    // Asynchronous non-blocking fetch call to Flask server
    const res = await fetch(`/api/weather?latitude=${lat}&longitude=${lon}`);
    if (!res.ok) throw new Error('Failed to load weather data');
    const data = await res.json();
    
    // Store in global cache so unit switching (°C/°F) requires zero re-fetching
    weatherDataCache = data;

    // Update all visual cards
    renderDashboard(data);
  } catch (err) {
    console.error('Error fetching weather:', err);
  }
}


// -----------------------------------------------------------------------------
// 5. DASHBOARD DOM RENDERER
// -----------------------------------------------------------------------------

/**
 * Injects meteorological data from the API payload into corresponding HTML elements.
 * @param {Object} data - Clean JSON weather payload returned by /api/weather.
 */
function renderDashboard(data) {
  const current = data.current;

  // Header: Location name & last updated status
  document.getElementById('city-display-name').textContent = currentCityName;
  document.getElementById('last-updated-text').textContent = 'Updated just now';

  // Format and display current local time (e.g. 09:45 AM)
  const now = new Date();
  document.getElementById('local-time-text').textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  // Hero Card: Current temperature, unit symbol, description, and High/Low
  document.getElementById('current-temp-val').textContent = formatTemp(current.temperature);
  document.getElementById('current-temp-unit').textContent = `°${currentUnit}`;
  document.getElementById('weather-condition-text').textContent = current.description;
  document.getElementById('high-temp').textContent = `H ${formatTemp(current.high_temp)}°`;
  document.getElementById('low-temp').textContent = `L ${formatTemp(current.low_temp)}°`;

  // Hero Card Icon: Inject animated SVG
  const heroVisual = document.getElementById('hero-weather-icon');
  heroVisual.innerHTML = getWeatherIconSvg(current.icon, current.is_day);

  // 7-Day Forecast Horizontal Pill Carousel
  renderDailyForecast(data.daily);

  // 24-Hour Hourly Timeline Chart (Chart.js)
  renderHourlyChart(data.hourly);

  // Visibility Card
  document.getElementById('visibility-val').textContent = formatVisibility(current.visibility_km);
  document.getElementById('visibility-unit').textContent = getVisibilityUnit();
  document.getElementById('visibility-status').textContent = current.visibility_label;

  // Atmospheric Pressure Card
  document.getElementById('pressure-val').textContent = current.pressure;
  document.getElementById('pressure-status').textContent = current.pressure_trend;

  // Wind Card: Speeds, gusts, and Beaufort force
  document.getElementById('wind-speed-val').textContent = formatWindSpeed(current.wind_speed);
  document.getElementById('wind-unit-label').textContent = getWindUnit();
  document.getElementById('wind-gust-val').textContent = formatWindSpeed(current.wind_gust);
  document.getElementById('wind-gust-unit-label').textContent = getWindUnit();
  document.getElementById('wind-force-label').textContent = current.wind_force;

  // Physical 360° Compass Needle Rotation via CSS transform
  const compassNeedle = document.getElementById('compass-needle');
  if (compassNeedle) {
    compassNeedle.style.transform = `translate(-50%, -50%) rotate(${current.wind_direction}deg)`;
  }

  // Air Quality Index (AQI) Card: Computes dashoffset for circular SVG gauge
  const aqiVal = current.aqi || 45;
  document.getElementById('aqi-val').textContent = aqiVal;
  document.getElementById('aqi-status').textContent = current.aqi_label;
  const aqiArc = document.getElementById('aqi-arc-path');
  if (aqiArc) {
    // 0 to 250 scale mapped across dashoffset range (142 to 0)
    const pct = Math.min(1, Math.max(0, aqiVal / 250));
    aqiArc.style.strokeDashoffset = 142 - (142 * pct);
  }

  // UV Index Card: Radial SVG gauge animation
  const uvVal = current.uv_index || 4;
  document.getElementById('uv-val').textContent = uvVal;
  document.getElementById('uv-status').textContent = current.uv_label;
  const uvArc = document.getElementById('uv-arc-path');
  if (uvArc) {
    // 0 to 11 WHO scale mapped to dashoffset (142 to 0)
    const pct = Math.min(1, Math.max(0, uvVal / 11));
    uvArc.style.strokeDashoffset = 142 - (142 * pct);
  }

  // Humidity Card: Percentage, Dew point, and vertical equalizer bars
  const hum = current.relative_humidity || 50;
  document.getElementById('humidity-val').textContent = `${hum}%`;
  document.getElementById('dew-point-val').textContent = `${formatTemp(current.dew_point)}°`;
  const humBars = document.querySelectorAll('#humidity-bars .eq-bar i');
  humBars.forEach((bar, idx) => {
    // Slight wave distribution factor for visually realistic equalizer look
    const factor = 0.5 + (Math.sin(idx * 0.8) * 0.3);
    const heightPct = Math.min(100, Math.max(15, Math.round(hum * factor)));
    bar.style.height = `${heightPct}%`;
  });

  // Sun Hours Card: Daylight duration and localized 12-hour AM/PM times
  document.getElementById('sun-duration-text').textContent = current.daylight_duration_text;
  if (current.sunrise) {
    const sr = new Date(current.sunrise);
    document.getElementById('sunrise-time-text').innerHTML = `${sr.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: true })}`.replace(/(AM|PM)/, '<small>$1</small>');
  }
  if (current.sunset) {
    const ss = new Date(current.sunset);
    document.getElementById('sunset-time-text').innerHTML = `${ss.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: true })}`.replace(/(AM|PM)/, '<small>$1</small>');
  }
}


// -----------------------------------------------------------------------------
// 6. DAILY FORECAST CAROUSEL RENDERER
// -----------------------------------------------------------------------------

/**
 * Creates dynamic pill cards for the 7-day weather outlook.
 * @param {Array<Object>} dailyList - 7 daily forecast items from API.
 */
function renderDailyForecast(dailyList) {
  const container = document.getElementById('daily-forecast-container');
  container.innerHTML = ''; // Clear existing cards

  dailyList.forEach((day, index) => {
    const pill = document.createElement('div');
    pill.className = `forecast-pill ${index === 0 ? 'today' : ''}`;

    // Format day name: 'Today' for index 0, otherwise short weekday (e.g. 'Thu 15')
    let dayName = 'Today';
    if (index > 0) {
      const d = new Date(day.date);
      dayName = d.toLocaleDateString([], { weekday: 'short', day: 'numeric' });
    }

    pill.innerHTML = `
      <span class="day-label">${dayName}</span>
      <div class="day-icon">${getWeatherIconSvg(day.icon, 1)}</div>
      <div class="day-temps">
        <span class="max">${formatTemp(day.max_temp)}°</span>
        <span class="min">${formatTemp(day.min_temp)}°</span>
      </div>
    `;
    container.appendChild(pill);
  });
}


// -----------------------------------------------------------------------------
// 7. HOURLY TEMPERATURE & RAIN CHART (CHART.JS)
// -----------------------------------------------------------------------------

/**
 * Initializes and renders the smooth 24-hour area chart with rain probabilities.
 * @param {Array<Object>} hourlyList - 24 hourly data entries from API.
 */
function renderHourlyChart(hourlyList) {
  const ctx = document.getElementById('hourlyTempChart').getContext('2d');

  // Sample data points every 3 hours for clean presentation (8 data points total)
  const step = 3;
  const filtered = hourlyList.filter((_, i) => i % step === 0).slice(0, 8);

  // X-axis time labels (e.g., '10 AM', '1 PM', '4 PM')
  const labels = filtered.map(h => {
    const d = new Date(h.time);
    return d.toLocaleTimeString([], { hour: 'numeric', hour12: true });
  });

  // Y-axis temperature values converted to active unit
  const temps = filtered.map(h => formatTemp(h.temp));
  const precips = filtered.map(h => h.precip_prob || 0);

  // If a chart already exists, destroy it before re-drawing to prevent memory leaks and overlapping canvas
  if (hourlyChart) {
    hourlyChart.destroy();
  }

  // Create subtle vertical orange area gradient fill beneath the curve
  const gradient = ctx.createLinearGradient(0, 0, 0, 140);
  gradient.addColorStop(0, 'rgba(251, 146, 60, 0.35)');
  gradient.addColorStop(1, 'rgba(251, 146, 60, 0.0)');

  // Initialize new Chart.js line instance
  hourlyChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'Temperature',
        data: temps,
        borderColor: '#f97316',               // Warm orange line color
        backgroundColor: gradient,            // Gradient fill under the spline
        borderWidth: 2.5,
        tension: 0.4,                         // Cubic bezier smoothing for soft curves
        fill: true,
        pointBackgroundColor: '#ffffff',
        pointBorderColor: '#f97316',
        pointBorderWidth: 2,
        pointRadius: 4.5,
        pointHoverRadius: 6,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },           // Hide default legend for minimal aesthetic
        tooltip: {
          backgroundColor: '#0f172a',
          titleFont: { family: 'Plus Jakarta Sans', size: 12 },
          bodyFont: { family: 'Plus Jakarta Sans', size: 12 },
          callbacks: {
            // Custom tooltip callback showing both temperature and rain probability drop (💧 %)
            label: (ctx) => {
              const idx = ctx.dataIndex;
              return `${ctx.parsed.y}°${currentUnit} | 💧 ${precips[idx]}% Rain`;
            }
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },           // Hide vertical grid lines
          ticks: {
            font: { family: 'Plus Jakarta Sans', size: 11, weight: '600' },
            color: '#64748b'
          }
        },
        y: {
          display: false,                     // Hide Y-axis labels to preserve clean card layout
          suggestedMin: Math.min(...temps) - 3,
          suggestedMax: Math.max(...temps) + 3
        }
      }
    }
  });
}


// -----------------------------------------------------------------------------
// 8. WORLDWIDE CITY SEARCH - SINGLE REQUEST ON SUBMIT (ENTER / SEARCH BUTTON)
// -----------------------------------------------------------------------------
const searchForm = document.getElementById('city-search-form');
const searchInput = document.getElementById('city-search-input');
const searchBtn = document.getElementById('btn-search-submit');
const searchBtnText = document.getElementById('btn-search-text');
const searchFeedback = document.getElementById('search-feedback');

// Client-side in-memory search cache to eliminate duplicate network calls
const citySearchCache = new Map();

/**
 * Displays error or informational validation messages below the search bar.
 * @param {string} message - User-friendly message explaining the status or error.
 * @param {'error'|'info'} type - Category styling ('error' for red alert, 'info' for blue).
 */
function showFeedback(message, type = 'error') {
  searchFeedback.textContent = message;
  searchFeedback.className = `search-feedback ${type}`;
}

/**
 * Clears and hides the validation message banner.
 */
function hideFeedback() {
  searchFeedback.textContent = '';
  searchFeedback.className = 'search-feedback';
}

/**
 * Keystroke listener: Clears previous validation error when the user starts typing.
 * IMPORTANT: Absolutely ZERO network requests or API calls are made here.
 * Keystrokes only clear old alerts so the user has an unobstructed input experience.
 */
searchInput.addEventListener('input', () => {
  hideFeedback();
});

/**
 * Fetches matching city coordinates from the Open-Meteo Geocoding API via Flask.
 * Uses an in-memory cache to guarantee zero duplicate network calls for identical queries.
 * @param {string} query - Complete city name typed by the user (e.g., "Dharmavaram", "London").
 * @returns {Promise<Array>} List of matching city objects returned from backend.
 */
async function fetchCityMatches(query) {
  const normalized = query.trim().toLowerCase();
  
  // Return cached results instantly if this city was already searched in this session
  if (citySearchCache.has(normalized)) {
    return citySearchCache.get(normalized);
  }

  // Exactly ONE network request sent when submitted
  const res = await fetch(`/api/search?name=${encodeURIComponent(query.trim())}`);
  if (!res.ok) throw new Error('Search API failed');
  const data = await res.json();
  const results = data.results || [];

  // Cache up to 100 recent searches in memory
  if (citySearchCache.size > 100) {
    const firstKey = citySearchCache.keys().next().value;
    citySearchCache.delete(firstKey);
  }
  citySearchCache.set(normalized, results);

  return results;
}

/**
 * Form Submit Listener (Triggered ONLY when user hits Enter key or clicks "Search" button):
 * 1. Validates input is not empty (no API call if empty).
 * 2. Sends exactly ONE request to search for the city.
 * 3. Validates whether the city exists.
 * 4. If found: Immediately loads the weather and displays it on the dashboard.
 * 5. If not found: Displays a clear error message.
 */
searchForm.addEventListener('submit', async (e) => {
  e.preventDefault();

  const query = searchInput.value.trim();

  // Validation 1: Check if input field is empty
  if (!query) {
    showFeedback('Please enter a city name to search.', 'error');
    searchInput.focus();
    return;
  }

  hideFeedback();
  if (searchBtn) searchBtn.disabled = true;
  if (searchBtnText) searchBtnText.textContent = 'Searching...';

  try {
    // Single request to search for the city
    const results = await fetchCityMatches(query);

    // Validation 2: Check if any city matched the query
    if (!results || results.length === 0) {
      showFeedback(`City "${query}" not found. Please check the spelling and try again.`, 'error');
      return;
    }

    // City found: Automatically load and display weather for the top match
    const topCity = results[0];
    searchInput.value = topCity.display_name;
    loadWeatherData(topCity.latitude, topCity.longitude, topCity.display_name);

  } catch (err) {
    console.error('Search error:', err);
    showFeedback('Unable to reach search service. Please try again later.', 'error');
  } finally {
    if (searchBtn) searchBtn.disabled = false;
    if (searchBtnText) searchBtnText.textContent = 'Search';
  }
});


// -----------------------------------------------------------------------------
// 9. HTML5 GEOLOCATION API ("USE CURRENT LOCATION")
// -----------------------------------------------------------------------------
document.getElementById('btn-current-location').addEventListener('click', () => {
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        loadWeatherData(lat, lon, 'Your Current Location');
      },
      () => {
        alert('Could not determine current location. Please use the search bar.');
      }
    );
  }
});


// -----------------------------------------------------------------------------
// 10. DYNAMIC UNIT SWITCHING (°C <-> °F)
// -----------------------------------------------------------------------------

/**
 * Sets the active temperature unit and updates the UI without re-fetching from API.
 * @param {string} unit - 'C' or 'F'.
 */
function setUnit(unit) {
  if (currentUnit === unit) return;
  currentUnit = unit;

  // Toggle active class on all unit buttons in the header and hero card
  document.querySelectorAll('.unit-btn, .small-unit-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.unit === unit);
  });

  // Re-render cached weather data instantly
  if (weatherDataCache) {
    renderDashboard(weatherDataCache);
  }
}

// Bind click event listeners to all unit buttons
document.querySelectorAll('.unit-btn, .small-unit-btn').forEach(btn => {
  btn.addEventListener('click', () => setUnit(btn.dataset.unit));
});


// -----------------------------------------------------------------------------
// 11. INITIAL APPLICATION BOOTSTRAP
// -----------------------------------------------------------------------------
window.addEventListener('DOMContentLoaded', () => {
  // Load default city (Berlin) on initial page load
  loadWeatherData(currentLat, currentLon, currentCityName);
});

