/* ============================================================================
   Lynn Data Dive — Lynn-Focused Maps
   Hyper-focused on Lynn: census-tract demographics, Lynn schools, and Lynn
   compared to other Gateway city high schools. For the FULL statewide
   experience (351 munis, 274 districts, 40+ metrics, etc.) see
   maxwellhowegis.com/ma-atlas/
   ============================================================================ */

const LYNN_FOCUS = true;  // hides statewide reference layers + filters metric catalog

// ─── DATA SOURCES (same-origin, slim simplified GeoJSON) ─────────────────────
const SOURCES = {
    tracts:        "data/lynn_tracts.geojson",
    schools:       "data/lynn_schools.geojson",
    town:          "data/lynn_town.geojson",
    academic:      "data/ma_academic_districts.geojson",   // dissolved town polygons (~250)
    ccuv:          "data/ma_districts_metrics.geojson",    // charter/voc-tech/collab (150)
    municipalities:"data/ma_municipalities.geojson",
    maSchools:     "data/ma_public_schools.geojson",       // all MA public + charter schools (~1700)
};

// ─── COLOR PALETTES (ColorBrewer-style) ──────────────────────────────────────
const PALETTES = {
    // Sequential
    Blues:   { type: "seq", colors: ["#f7fbff","#deebf7","#c6dbef","#9ecae1","#6baed6","#4292c6","#2171b5","#08519c","#08306b"] },
    Greens:  { type: "seq", colors: ["#f7fcf5","#e5f5e0","#c7e9c0","#a1d99b","#74c476","#41ab5d","#238b45","#006d2c","#00441b"] },
    Reds:    { type: "seq", colors: ["#fff5f0","#fee0d2","#fcbba1","#fc9272","#fb6a4a","#ef3b2c","#cb181d","#a50f15","#67000d"] },
    Oranges: { type: "seq", colors: ["#fff5eb","#fee6ce","#fdd0a2","#fdae6b","#fd8d3c","#f16913","#d94801","#a63603","#7f2704"] },
    Purples: { type: "seq", colors: ["#fcfbfd","#efedf5","#dadaeb","#bcbddc","#9e9ac8","#807dba","#6a51a3","#54278f","#3f007d"] },
    Greys:   { type: "seq", colors: ["#ffffff","#f0f0f0","#d9d9d9","#bdbdbd","#969696","#737373","#525252","#252525","#000000"] },
    Viridis: { type: "seq", colors: ["#440154","#482878","#3e4a89","#31688e","#26828e","#1f9e89","#35b779","#6dcd59","#b4de2c","#fde725"] },
    Plasma:  { type: "seq", colors: ["#0d0887","#5402a3","#8b0aa5","#b83289","#db5c68","#f48849","#febc2a","#f0f921"] },
    YlGnBu:  { type: "seq", colors: ["#ffffd9","#edf8b1","#c7e9b4","#7fcdbb","#41b6c4","#1d91c0","#225ea8","#253494","#081d58"] },
    BuPu:    { type: "seq", colors: ["#f7fcfd","#e0ecf4","#bfd3e6","#9ebcda","#8c96c6","#8c6bb1","#88419d","#810f7c","#4d004b"] },
    // Diverging
    RdBu:    { type: "div", colors: ["#67001f","#b2182b","#d6604d","#f4a582","#fddbc7","#f7f7f7","#d1e5f0","#92c5de","#4393c3","#2166ac","#053061"] },
    RdYlGn:  { type: "div", colors: ["#a50026","#d73027","#f46d43","#fdae61","#fee08b","#ffffbf","#d9ef8b","#a6d96a","#66bd63","#1a9850","#006837"] },
    BrBG:    { type: "div", colors: ["#543005","#8c510a","#bf812d","#dfc27d","#f6e8c3","#f5f5f5","#c7eae5","#80cdc1","#35978f","#01665e","#003c30"] },
};

// ─── METRIC CATALOG ──────────────────────────────────────────────────────────
const METRICS = [
    // Demographics
    { id:"TOTAL_CNT",  label:"Total Enrollment",            cat:"Demographics", levels:["district","muni"], palette:"Blues",   format:"num" },
    { id:"EL_PCT",     label:"% English Learner",           cat:"Demographics", levels:["district","muni"], palette:"Greens",  format:"pct" },
    { id:"LI_PCT",     label:"% Low Income",                cat:"Demographics", levels:["district","muni"], palette:"Reds",    format:"pct" },
    { id:"HN_PCT",     label:"% High Needs",                cat:"Demographics", levels:["district","muni"], palette:"Purples", format:"pct" },
    { id:"HL_PCT",     label:"% Hispanic / Latino",         cat:"Demographics", levels:["district","muni"], palette:"Oranges", format:"pct" },
    { id:"BAA_PCT",    label:"% Black / African Am.",       cat:"Demographics", levels:["district","muni"], palette:"Purples", format:"pct" },
    { id:"AS_PCT",     label:"% Asian",                     cat:"Demographics", levels:["district","muni"], palette:"Blues",   format:"pct" },
    { id:"WH_PCT",     label:"% White",                     cat:"Demographics", levels:["district","muni"], palette:"Greys",   format:"pct" },
    { id:"SWD_PCT",    label:"% Students w/ Disabilities",  cat:"Demographics", levels:["district","muni"], palette:"Purples", format:"pct" },
    { id:"FLNE_PCT",   label:"% First Lang Not English",    cat:"Demographics", levels:["district","muni"], palette:"Greens",  format:"pct" },

    // Academic — mcas_g38_* live only on district features (no muni-level join today)
    { id:"mcas_g10_ela_me",  label:"MCAS Gr10 ELA % M+E",   cat:"Academic", levels:["district","muni"], palette:"Viridis", format:"pct" },
    { id:"mcas_g10_math_me", label:"MCAS Gr10 Math % M+E",  cat:"Academic", levels:["district","muni"], palette:"Viridis", format:"pct" },
    { id:"mcas_g10_sci_me",  label:"MCAS Gr10 STE % M+E",   cat:"Academic", levels:["district","muni"], palette:"Viridis", format:"pct" },
    { id:"mcas_g38_ela_me",  label:"MCAS Gr3-8 ELA % M+E",  cat:"Academic", levels:["district"],        palette:"Viridis", format:"pct" },
    { id:"mcas_g38_math_me", label:"MCAS Gr3-8 Math % M+E", cat:"Academic", levels:["district"],        palette:"Viridis", format:"pct" },

    // Outcomes — full set mirrors the Streamlit dashboard. chronic_absent /
    // attendance / AP currently render no-data because the pipeline build
    // joined them but the source CSV was empty for these columns at last
    // refresh. Re-running scripts/11_build_lynn_geo.py with a fresh raw/
    // dir should populate them.
    { id:"grad_4yr",            label:"4-yr Graduation Rate",        cat:"Outcomes", levels:["district","muni"], palette:"Viridis", format:"pct" },
    { id:"grad_5yr",            label:"5-yr Graduation Rate",        cat:"Outcomes", levels:["district"],        palette:"Viridis", format:"pct" },
    { id:"dropout_pct",         label:"Dropout Rate",                cat:"Outcomes", levels:["district","muni"], palette:"Reds",    format:"pct" },
    { id:"chronic_absent_pct",  label:"Chronic Absenteeism Rate",    cat:"Outcomes", levels:["district"],        palette:"Reds",    format:"pct" },
    { id:"attendance_rate",     label:"Attendance Rate",             cat:"Outcomes", levels:["district"],        palette:"Greens",  format:"pct" },
    { id:"masscore_pct",        label:"MassCore Completion",         cat:"Outcomes", levels:["district"],        palette:"Greens",  format:"pct" },
    { id:"ap_pct_3plus",        label:"% AP Tests Scoring 3+",       cat:"Outcomes", levels:["district"],        palette:"BuPu",    format:"pct" },

    // Postsecondary plans — joined onto district features only
    { id:"pct_any_college",     label:"% Planning Any College",      cat:"Postsecondary", levels:["district"], palette:"Viridis", format:"pct" },
    { id:"pct_4yr_college",     label:"% Planning 4-yr College",     cat:"Postsecondary", levels:["district"], palette:"Viridis", format:"pct" },
    { id:"pct_2yr_college",     label:"% Planning 2-yr College",     cat:"Postsecondary", levels:["district"], palette:"BuPu",    format:"pct" },
    { id:"pct_work_after_hs",   label:"% Planning to Work after HS", cat:"Postsecondary", levels:["district"], palette:"Oranges", format:"pct" },
    { id:"pct_military",        label:"% Planning Military",         cat:"Postsecondary", levels:["district"], palette:"Greys",   format:"pct" },

    // Finance — totals at both levels; breakdowns district-only
    { id:"per_pupil",                  label:"Per-Pupil $ (Total)",         cat:"Finance", levels:["district","muni"], palette:"Viridis", format:"usd" },
    { id:"per_pupil_teachers",         label:"Per-Pupil $ — Teachers",      cat:"Finance", levels:["district","muni"], palette:"Viridis", format:"usd" },
    { id:"per_pupil_admin",            label:"Per-Pupil $ — Administration",cat:"Finance", levels:["district"],        palette:"Viridis", format:"usd" },
    { id:"per_pupil_pupil_services",   label:"Per-Pupil $ — Pupil Services",cat:"Finance", levels:["district"],        palette:"Viridis", format:"usd" },

    // Workforce — full set mirrors the dashboard. staff_*_pct and
    // teacher_experienced/infield render no-data today (same root cause as
    // the Outcomes block — needs a pipeline rebuild against fresh raw/).
    { id:"staff_white_pct",         label:"% Staff: White",            cat:"Workforce", levels:["district"], palette:"Greys",   format:"pct" },
    { id:"staff_hispanic_pct",      label:"% Staff: Hispanic",         cat:"Workforce", levels:["district"], palette:"Oranges", format:"pct" },
    { id:"staff_black_pct",         label:"% Staff: Black",            cat:"Workforce", levels:["district"], palette:"Purples", format:"pct" },
    { id:"stu_tchr_ratio",          label:"Student : Teacher Ratio",   cat:"Workforce", levels:["district"], palette:"Reds",    format:"num" },
    { id:"teacher_experienced_pct", label:"% Experienced Teachers",    cat:"Workforce", levels:["district"], palette:"Greens",  format:"pct" },
    { id:"teacher_infield_pct",     label:"% Teachers In-Field",       cat:"Workforce", levels:["district"], palette:"Greens",  format:"pct" },
    { id:"teacher_retention_pct",   label:"Teacher Retention Rate",    cat:"Workforce", levels:["district"], palette:"Greens",  format:"pct" },

    // Tract — ACS (Lynn only)
    { id:"non_english_pct",          label:"% non-English at home",      cat:"Tract — Census ACS", levels:["tract"], palette:"Greens",  format:"pct" },
    { id:"median_household_income",  label:"Median Household Income",    cat:"Tract — Census ACS", levels:["tract"], palette:"Viridis", format:"usd" },
    { id:"foreign_born_pct",         label:"% Foreign-born",             cat:"Tract — Census ACS", levels:["tract"], palette:"Purples", format:"pct" },
    { id:"bachelors_or_higher_pct",  label:"% Bachelor's or higher",     cat:"Tract — Census ACS", levels:["tract"], palette:"Blues",   format:"pct" },
    { id:"severe_burden_pct",        label:"% Severely Rent-Burdened",   cat:"Tract — Census ACS", levels:["tract"], palette:"Reds",    format:"pct" },
];

// ─── STATE ───────────────────────────────────────────────────────────────────
const state = {
    // Open on the muni level so visitors land on a metric-rich view (~25 metrics)
    // instead of the tract level (only 5 ACS metrics) and immediately see the
    // Lynn-vs-gateway-vs-neighbors comparison this tool exists for.
    level: "muni",
    metric: "EL_PCT",                  // % English Learner — Lynn's defining demographic
    palette: "Greens",
    classify: "jenks",                 // Fisher-Jenks natural breaks (standard cartographic default)
    extrude3d: false,
    labels: true,
    townLabels: true,
    showMuniOutline: true,
    showAcademicOutline: false,
    showVoctechOverlay: false,
    showCharterOverlay: false,
    showLynnSchools: true,
    showAllMaSchools: false,
    schoolColorMode: "type",           // "type" | "focus" | EL_PCT | LI_PCT | SWD_PCT
    showLynnTown: true,
    showGatewayHighlight: true,
    studentGroup: "all",
    year: 2026,
    playing: false,
    theme: "light",                    // "light" | "dark" — drives the basemap swap
};

let GEO_DATA = null;  // populated after load

// Assigned by setupLegendCustomization(); lets updateLegend() re-clamp a moved/
// resized legend after its content height changes. No-op until wired.
let _legendClamp = null;

// ─── THEME (light / dark) ────────────────────────────────────────────────────
// Token-based dark mode: a [data-theme] attr on <html> flips the CSS custom
// properties (see style.css), and we swap the basemap to a dark raster +
// re-halo our own labels for legibility. Persisted to localStorage; respected
// on load. Adapted from the statewide atlas (applyTheme/toggleTheme/initTheme),
// but this Lynn map loads the Positron style directly, so the basemap swap
// hides Positron's own vector layers and shows a CARTO dark raster instead
// (see addDarkBasemap() + applyThemeBasemap()).
function currentTheme() {
    return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
}
function syncThemeButton() {
    const dark = currentTheme() === "dark";
    const btn = document.getElementById("themeToggle");
    if (btn) {
        btn.setAttribute("aria-pressed", dark ? "true" : "false");
        btn.title = dark ? "Switch to light mode" : "Switch to dark mode";
    }
    // Show the sun icon in light mode, the moon in dark mode.
    document.querySelectorAll("[data-theme-ico]").forEach(el => {
        el.style.display = ((el.dataset.themeIco === "dark") === dark) ? "" : "none";
    });
}
function applyTheme(theme, opts = {}) {
    const dark = theme === "dark";
    state.theme = dark ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
    syncThemeButton();
    // Swap the basemap once the map + dark layer exist (skipped at first paint;
    // initTheme seeds the attr and the load handler paints the right base).
    if (!opts.skipBasemap && typeof map !== "undefined" && map.getLayer && map.getLayer("dark-base")) {
        applyThemeBasemap(dark ? "dark" : "light");
    }
    try { localStorage.setItem("lynn-maps-theme", dark ? "dark" : "light"); } catch (e) {}
}
function toggleTheme() { applyTheme(currentTheme() === "dark" ? "light" : "dark"); }

// Run at module load (DOM parsed; map not yet created). Sets the chrome from the
// saved preference / OS setting so the FIRST paint already carries the theme; the
// load handler then paints the matching basemap (no light flash in dark mode).
function initTheme() {
    let t = null;
    try { t = localStorage.getItem("lynn-maps-theme"); } catch (e) {}
    if (t !== "dark" && t !== "light") {
        t = (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) ? "dark" : "light";
    }
    state.theme = t;
    document.documentElement.setAttribute("data-theme", t);
}
initTheme();

// Year-keyed schema introspection. After load, for each (level, baseMetric)
// pair we record which years actually have data — drives the slider availability
// and lets us fall back to latest when a metric isn't year-keyed.
const YEAR_KEYED_INDEX = {
    /* level: { baseMetric: Set<int years> } */
    muni: {}, district: {}, tract: {},
};

function buildYearKeyedIndex() {
    for (const level of ["muni", "district", "tract"]) {
        const fc = GEO_DATA[level];
        if (!fc || !fc.features.length) continue;
        const sample = fc.features[0].properties;
        const idx = {};
        for (const key of Object.keys(sample)) {
            const m = key.match(/^(.+)__(\d{4})$/);
            if (!m) continue;
            const base = m[1], year = parseInt(m[2], 10);
            if (!idx[base]) idx[base] = new Set();
            idx[base].add(year);
        }
        YEAR_KEYED_INDEX[level] = idx;
    }
}

// Group-keyed schema introspection. { level: { baseMetric: Set<group_code> } }
// group_code is the lowercase suffix in the column name (e.g. "ell", "baa").
const GROUP_KEYED_INDEX = { muni: {}, district: {}, tract: {} };
const KNOWN_GROUPS = new Set(["hl","baa","as","wh","ell","fmrell","li","swd","hn"]);

function buildGroupKeyedIndex() {
    for (const level of ["muni", "district", "tract"]) {
        const fc = GEO_DATA[level];
        if (!fc || !fc.features.length) continue;
        const sample = fc.features[0].properties;
        const idx = {};
        for (const key of Object.keys(sample)) {
            const m = key.match(/^(.+)__([a-z]+)$/);
            if (!m) continue;
            const base = m[1], code = m[2];
            if (!KNOWN_GROUPS.has(code)) continue;  // skip year suffixes (numeric)
            if (!idx[base]) idx[base] = new Set();
            idx[base].add(code);
        }
        GROUP_KEYED_INDEX[level] = idx;
    }
}

// Resolve the active column name for state.metric + state.year + state.studentGroup.
// Precedence: group-keyed > year-keyed > base column. (Combined year×group isn't
// stored — too many columns for too little gain.) HTML option values are
// uppercase abbreviations (ELL, HL); data column suffixes are lowercase (__ell,
// __hl). Normalize to lowercase before lookup.
function activeColumn(metricId = state.metric, year = state.year, level = state.level) {
    const grp = (state.studentGroup || "all").toLowerCase();
    if (grp !== "all") {
        const gIdx = GROUP_KEYED_INDEX[level] || {};
        if (gIdx[metricId] && gIdx[metricId].has(grp)) {
            return `${metricId}__${grp}`;
        }
        // Group requested but no group-keyed data — fall through to year/base
    }
    const idx = YEAR_KEYED_INDEX[level] || {};
    const years = idx[metricId];
    if (years && years.has(year)) return `${metricId}__${year}`;
    return metricId;
}

// Updates the helper note under the student-group dropdown.
function updateGroupNote() {
    const noteEl = document.getElementById("groupNote");
    if (!noteEl) return;
    if (!state.studentGroup || state.studentGroup === "all") {
        noteEl.textContent = "Select a group to filter outcomes (MCAS, graduation, AP, chronic absent). Works at district/muni level.";
        return;
    }
    const grp = state.studentGroup.toLowerCase();
    const gIdx = GROUP_KEYED_INDEX[state.level] || {};
    const supported = gIdx[state.metric] && gIdx[state.metric].has(grp);
    if (supported) {
        noteEl.textContent = `✓ Showing ${getMetric(state.metric).label} for the ${state.studentGroup} student group only.`;
    } else {
        noteEl.textContent = `⚠ This metric isn't group-sliced. Falling back to All Students. (Group filter works on MCAS, graduation, AP, and chronic absent metrics.)`;
    }
}

// Available years for the active metric/level. Returns an array.
function availableYears(metricId = state.metric, level = state.level) {
    const idx = YEAR_KEYED_INDEX[level] || {};
    const set = idx[metricId];
    return set ? [...set].sort((a, b) => a - b) : [];
}

// ─── YEAR ANIMATION (slideshow) ──────────────────────────────────────────────
let _yearAnimTimer = null;
const YEAR_ANIM_INTERVAL_MS = 900;

function startYearAnimation() {
    if (state.playing) return;
    const years = availableYears();
    if (years.length < 2) return;
    state.playing = true;
    const btn = document.getElementById("yearPlay");
    if (btn) { btn.textContent = "⏸"; btn.classList.add("playing"); btn.title = "Pause slideshow"; }
    _yearAnimTimer = setInterval(() => {
        const yrs = availableYears();
        if (yrs.length < 2) { stopYearAnimation(); return; }
        const idx = yrs.indexOf(state.year);
        const nextIdx = (idx + 1) % yrs.length;
        state.year = yrs[nextIdx];
        const slider = document.getElementById("yearSlider");
        if (slider) slider.value = state.year;
        const label = document.getElementById("yearLabel");
        if (label) label.textContent = state.year;
        applyChoropleth();
        updateLegend();
        updateMetricSummary();
    }, YEAR_ANIM_INTERVAL_MS);
}

function stopYearAnimation() {
    state.playing = false;
    if (_yearAnimTimer) { clearInterval(_yearAnimTimer); _yearAnimTimer = null; }
    const btn = document.getElementById("yearPlay");
    if (btn) { btn.textContent = "▶"; btn.classList.remove("playing"); btn.title = "Play slideshow"; }
}

// ─── FORMATTERS ──────────────────────────────────────────────────────────────
function fmt(value, kind) {
    if (value == null || !isFinite(value)) return "—";
    if (kind === "pct") return `${(value * 100).toFixed(1)}%`;
    if (kind === "usd") return `$${Math.round(value).toLocaleString()}`;
    return Math.round(value).toLocaleString();
}

function getMetric(id) { return METRICS.find(m => m.id === id) || METRICS[0]; }

// ─── METRIC POLARITY + SEMANTIC PALETTES ─────────────────────────────────────
// A metric's inherent direction, independent of the chosen palette:
//   "good"    higher = better  (graduation, attendance, college-going, income…)
//   "concern" higher = worse   (dropout, chronic absenteeism, rent burden…)
//   "neutral" no value judgment (raw counts, demographic shares, ratios…)
// Drives both the plain-language legend caption and the auto-picked semantic
// palette. Adapted from the atlas's metricPolarity/semanticPalette, but this
// Lynn catalog is small, so we classify with explicit id/category lists rather
// than the atlas's broad category sets.
const POLARITY_GOOD_IDS = new Set([
    "grad_4yr", "grad_5yr", "attendance_rate", "masscore_pct", "ap_pct_3plus",
    "mcas_g10_ela_me", "mcas_g10_math_me", "mcas_g10_sci_me",
    "mcas_g38_ela_me", "mcas_g38_math_me",
    "pct_any_college", "pct_4yr_college", "pct_2yr_college",
    "teacher_experienced_pct", "teacher_infield_pct", "teacher_retention_pct",
    "median_household_income", "bachelors_or_higher_pct",
]);
const POLARITY_CONCERN_IDS = new Set([
    "dropout_pct", "chronic_absent_pct", "severe_burden_pct",
    // Equity-need shares: "higher = more of a high-need group". On this Lynn map
    // these read as "more concentrated need", so a warm ramp is the honest cue.
    "LI_PCT", "HN_PCT", "EL_PCT", "SWD_PCT",
]);
function metricPolarity(m) {
    if (!m) return "neutral";
    if (POLARITY_CONCERN_IDS.has(m.id)) return "concern";
    if (POLARITY_GOOD_IDS.has(m.id))    return "good";
    return "neutral";
}
// Semantic palette default by meaning: a "bad when high" metric → a warm Reds/
// Oranges ramp; a "good when high" metric → a cool Greens/Blues ramp; neutral →
// the metric's own catalog palette. The user can still override via the palette
// selector. Kept lightweight: one map + a polarity fallback.
const SEM_GOOD_PALETTE    = "Greens";   // higher = better → cool/green
const SEM_CONCERN_PALETTE = "Reds";     // higher = worse  → warm/red
function semanticPalette(m) {
    if (!m) return SEM_GOOD_PALETTE;
    const pol = metricPolarity(m);
    if (pol === "concern") return SEM_CONCERN_PALETTE;
    if (pol === "good")    return SEM_GOOD_PALETTE;
    return m.palette;   // neutral — keep the catalog's own ramp
}
// One plain-language sentence describing how to read the active color ramp:
// which way is "higher", and (where the metric has a clear direction) whether
// darker is better or worse. The default ramps paint high = dark.
function legendCaptionText() {
    const m = getMetric(state.metric);
    let s = "Darker = higher values";
    const pol = metricPolarity(m);
    if (pol !== "neutral") {
        // Default ramps put the dark end at the HIGH end, so darker-is-good iff
        // the metric is "good when high".
        s += (pol === "good") ? " — darker is better" : " — darker is worse";
    }
    return s + ".";
}

// Convert numeric-looking string property values to real numbers in place,
// for every feature in a GeoJSON FeatureCollection. Necessary because some
// of the upstream pipeline's pct columns are written as strings, which the
// MapLibre paint expression's typeof-number validity check treats as invalid.
// Only touches values that round-trip cleanly through Number(); leaves
// identifier-looking strings (GEOIDs, names, codes) alone.
function coerceNumericStringProps(fc) {
    if (!fc || !fc.features) return;
    const NUM_RE = /^-?\d+(\.\d+)?$/;  // plain integers/decimals only, no scientific/hex
    for (const f of fc.features) {
        const p = f.properties;
        if (!p) continue;
        for (const k in p) {
            const v = p[k];
            if (typeof v !== "string") continue;
            if (!NUM_RE.test(v)) continue;
            const n = Number(v);
            if (Number.isFinite(n)) p[k] = n;
        }
    }
}

// ─── CLASSIFICATION & PAINT BUILDERS ─────────────────────────────────────────
function getValuesForLevel(level, metricId) {
    if (!GEO_DATA) return [];
    const fc = GEO_DATA[level];
    if (!fc || !fc.features) return [];
    // Year-aware: read year-keyed column when available, else fall back to base.
    const col = activeColumn(metricId, state.year, level);
    return fc.features.map(f => f.properties[col])
                        .filter(v => v != null && isFinite(+v))
                        .map(v => +v);
}

function quantileBreaks(values, n) {
    const sorted = [...values].sort((a, b) => a - b);
    if (sorted.length < n) return sorted.slice(0, -1);
    const breaks = [];
    for (let i = 1; i < n; i++) {
        breaks.push(sorted[Math.floor(sorted.length * i / n)]);
    }
    return breaks;
}

function equalIntervalBreaks(values, n) {
    if (values.length === 0) return [];
    const min = Math.min(...values);
    const max = Math.max(...values);
    const step = (max - min) / n;
    return Array.from({ length: n - 1 }, (_, i) => min + step * (i + 1));
}

// Fisher-Jenks natural breaks — minimizes within-class variance, maximizes
// between-class variance. The standard cartographic choice for thematic maps.
// Runs O(n² · k) which is fine for n < 500 polygons.
function jenksBreaks(values, n) {
    if (values.length <= n) return values.slice(0, -1);
    const sorted = [...values].sort((a, b) => a - b);
    const len = sorted.length;

    // Lower class limits and variance combinations matrices
    const lc = Array.from({ length: len + 1 }, () => new Array(n + 1).fill(0));
    const vc = Array.from({ length: len + 1 }, () => new Array(n + 1).fill(0));
    for (let j = 1; j <= n; j++) {
        lc[1][j] = 1;
        vc[1][j] = 0;
        for (let i = 2; i <= len; i++) vc[i][j] = Infinity;
    }

    for (let l = 2; l <= len; l++) {
        let s1 = 0, s2 = 0, w = 0;
        for (let m = 1; m <= l; m++) {
            const i3 = l - m + 1;
            const val = sorted[i3 - 1];
            s2 += val * val;
            s1 += val;
            w++;
            const v = s2 - (s1 * s1) / w;
            const i4 = i3 - 1;
            if (i4 !== 0) {
                for (let j = 2; j <= n; j++) {
                    if (vc[l][j] >= v + vc[i4][j - 1]) {
                        lc[l][j] = i3;
                        vc[l][j] = v + vc[i4][j - 1];
                    }
                }
            }
        }
        lc[l][1] = 1;
        vc[l][1] = s2 - (s1 * s1) / w;
    }

    // Walk back through lc[] to recover the class boundaries
    const kclass = new Array(n + 1).fill(0);
    kclass[n] = sorted[len - 1];
    kclass[0] = sorted[0];
    let k = len;
    for (let countNum = n; countNum > 1; countNum--) {
        const id = lc[k][countNum] - 1;
        kclass[countNum - 1] = sorted[id];
        k = lc[k][countNum] - 1;
    }
    // Return only the inner breaks (n - 1 of them)
    return kclass.slice(1, -1);
}

// Pick N evenly-spaced colors from a palette
function sampleColors(palette, n) {
    if (palette.length === n) return palette;
    if (palette.length < n) return palette;
    const out = [];
    for (let i = 0; i < n; i++) {
        out.push(palette[Math.floor(i * (palette.length - 1) / (n - 1))]);
    }
    return out;
}

// Explicit "no data" color — distinct from any palette stop, slightly warm
// off-white. We also style its outline differently (dashed) for clarity.
const NO_DATA_COLOR = "#f0eee8";

// ─── LYNN SCHOOLS — THE CENTERPIECE ──────────────────────────────────────────
// This is the Lynn-focused map, so the school dots are the star (more prominent
// here than in the statewide atlas). They are sized by enrollment, colored by a
// switchable mode, carry their own size + color legends, and always render the
// focus school (Lynn English High) in gold. Adapted from the atlas's school
// layer (SCHOOL_RADIUS / SCHOOL_COLOR_BY_LEVEL / schoolDotRadius) but scaled to
// Lynn's enrollment range (~26–1,727, not the statewide 0–55,000) and keyed on
// this geojson's TYPE codes (ELE/MID/SEC/PRI/CHA/UNK), not TYPE_DESC strings.

const LEHS_ORG_CODE = "01630510";   // Lynn English High — the focus school

// School TYPE → label + categorical color. Order drives the color legend.
const SCHOOL_TYPES = [
    { key: "ELE", label: "Elementary",   color: "#1976D2" },
    { key: "MID", label: "Middle",       color: "#F57C00" },
    { key: "SEC", label: "High / 2ndary",color: "#C62828" },
    { key: "PRI", label: "Private",      color: "#00897B" },
    { key: "CHA", label: "Charter",      color: "#7B1FA2" },
    { key: "UNK", label: "Other",        color: "#607D8B" },
];

// Demographic color-by options (sequential ramp on a 0–1 fraction). low→high.
// 5-stop ramps re-using the catalog palettes so colors feel consistent.
const SCHOOL_DEMO_MODES = {
    EL_PCT:  { label: "% English Learner",          ramp: PALETTES.Greens.colors },
    LI_PCT:  { label: "% Low Income",               ramp: PALETTES.Reds.colors },
    SWD_PCT: { label: "% Students w/ Disabilities", ramp: PALETTES.Purples.colors },
};

// Enrollment → radius. Area ∝ enrollment ⇒ radius ∝ sqrt(enrollment); grows with
// zoom (dots get bigger as you zoom in). Stops chosen for Lynn's range, with a
// floor so the smallest schools stay visible. Schools with null TOTAL_CNT (the 9
// private/charter) coalesce to a small fixed size so they appear but don't
// dominate. Deliberately larger than the atlas's stops — this is the centerpiece.
const SCHOOL_NULL_ENROLL = 90;   // fallback enrollment for sizing null schools
// radius output for one zoom anchor: max(floor, k·sqrt(enrollment)), plus an
// optional flat offset (used by the halo / LEHS-ring layers). The offset is
// folded into the OUTPUT, not wrapped around the whole zoom interpolate —
// MapLibre rejects ["+", <zoom-interpolate>, n] ("zoom expression may only be
// used as input to a top-level step/interpolate").
function _schoolRadiusOutput(floor, k, offset = 0) {
    const core = ["max", floor, ["*", k, ["sqrt", ["to-number", ["coalesce", ["get", "TOTAL_CNT"], SCHOOL_NULL_ENROLL]]]]];
    return offset ? ["+", offset, core] : core;
}
function _schoolRadiusExpr(offset = 0) {
    return [
        "interpolate", ["linear"], ["zoom"],
        9,  _schoolRadiusOutput(3.5, 0.30, offset),
        12, _schoolRadiusOutput(5,   0.62, offset),
        15, _schoolRadiusOutput(7,   1.05, offset),
    ];
}
const SCHOOL_RADIUS           = _schoolRadiusExpr(0);
const SCHOOL_RADIUS_HALO      = _schoolRadiusExpr(3);
const SCHOOL_RADIUS_LEHS_RING = _schoolRadiusExpr(6);

// circle-color expression for each color mode. LEHS gold is layered on top via a
// separate gold focus-ring layer, so these palettes don't need a LEHS branch
// (except "focus" mode, where every non-LEHS school is muted grey).
const SCHOOL_COLOR_BY_TYPE = [
    "match", ["get", "TYPE"],
    ...SCHOOL_TYPES.flatMap(t => [t.key, t.color]),
    "#607D8B",
];
function schoolColorByDemo(metricId) {
    const ramp = (SCHOOL_DEMO_MODES[metricId] || SCHOOL_DEMO_MODES.EL_PCT).ramp;
    const stops = sampleColors(ramp, 5);
    return [
        "case",
        ["==", ["typeof", ["get", metricId]], "number"],
        ["interpolate", ["linear"], ["to-number", ["get", metricId]],
            0,    stops[0],
            0.25, stops[1],
            0.50, stops[2],
            0.75, stops[3],
            1.0,  stops[4]],
        "#cfd8dc",   // no demographic data (the 9 private/charter) → light grey
    ];
}
const SCHOOL_COLOR_FOCUS = [
    "case",
    ["==", ["get", "ORG_CODE"], LEHS_ORG_CODE], "#FFB81C",
    "#b0bcc6",
];

// Resolve the active circle-color expression from state.schoolColorMode, which is
// one of: "type" | "focus" | a demographic metric id (EL_PCT/LI_PCT/SWD_PCT).
function schoolColorExpression() {
    const mode = state.schoolColorMode;
    if (mode === "type")  return SCHOOL_COLOR_BY_TYPE;
    if (mode === "focus") return SCHOOL_COLOR_FOCUS;
    if (SCHOOL_DEMO_MODES[mode]) return schoolColorByDemo(mode);
    return SCHOOL_COLOR_BY_TYPE;
}

// JS mirror of SCHOOL_RADIUS for the graduated-dot SIZE legend (so the key dots
// match the on-map dots at the current zoom; recomputed on zoom).
const SCHOOL_SIZE_LEGEND_ENROLLMENTS = [200, 800, 1700];
function schoolDotRadius(enrollment, zoom) {
    const sqrtE = Math.sqrt(enrollment);
    const r9  = Math.max(3.5, 0.30 * sqrtE);
    const r12 = Math.max(5,   0.62 * sqrtE);
    const r15 = Math.max(7,   1.05 * sqrtE);
    if (zoom <= 9)  return r9;
    if (zoom <= 12) return r9  + (r12 - r9)  * (zoom - 9)  / 3;
    if (zoom <= 15) return r12 + (r15 - r12) * (zoom - 12) / 3;
    return r15;
}

// Apply the active color mode to the schools circle layer + toggle which legend
// (categorical type swatches vs sequential demographic ramp) is shown.
function applySchoolColorMode() {
    if (map.getLayer("schools-circles")) {
        map.setPaintProperty("schools-circles", "circle-color", schoolColorExpression());
    }
    renderSchoolColorLegend();
}

// Build the COLOR legend matching the active mode (categorical chips for "type"/
// "focus", a gradient bar for a demographic). Lives in the schools panel section.
function renderSchoolColorLegend() {
    const el = document.getElementById("schoolColorLegend");
    if (!el) return;
    const mode = state.schoolColorMode;
    let html = "";
    if (mode === "type") {
        html = SCHOOL_TYPES.map(t =>
            `<span class="scl-chip"><span class="scl-sw" style="background:${t.color}"></span>${t.label}</span>`
        ).join("");
        html += `<span class="scl-chip"><span class="scl-sw scl-sw--lehs"></span>Lynn English (focus)</span>`;
    } else if (mode === "focus") {
        html = `<span class="scl-chip"><span class="scl-sw scl-sw--lehs"></span>Lynn English High</span>` +
               `<span class="scl-chip"><span class="scl-sw" style="background:#b0bcc6"></span>All other schools</span>`;
    } else {
        const cfg = SCHOOL_DEMO_MODES[mode] || SCHOOL_DEMO_MODES.EL_PCT;
        const stops = sampleColors(cfg.ramp, 5);
        const grad = `linear-gradient(to right, ${stops.join(", ")})`;
        html = `<div class="scl-bar" style="background:${grad}"></div>` +
               `<div class="scl-axis"><span>0%</span><span>${cfg.label}</span><span>100%</span></div>` +
               `<div class="scl-note">Grey dot = no data (private / charter)</div>`;
    }
    el.innerHTML = html;
}

// Graduated-dot SIZE legend for the schools layer — mirrors SCHOOL_RADIUS so the
// key dots match the on-map dots at the current zoom (recomputed on zoom). Fill
// is neutral grey — this key is about size (enrollment), not the color mode.
function renderSchoolSizeLegend() {
    const el = document.getElementById("schoolSizeLegend");
    if (!el) return;
    if (!el.childElementCount) {
        el.innerHTML = SCHOOL_SIZE_LEGEND_ENROLLMENTS.map(e =>
            `<span class="ssl-item"><span class="ssl-dot-wrap"><span class="ssl-dot"></span></span>` +
            `<span class="ssl-label">${e.toLocaleString()}</span></span>`
        ).join("");
    }
    const z = map.getZoom();
    const dias = SCHOOL_SIZE_LEGEND_ENROLLMENTS.map(e => Math.max(6, Math.round(schoolDotRadius(e, z) * 2)));
    el.style.setProperty("--ssl-h", Math.max(...dias) + "px");
    el.querySelectorAll(".ssl-dot").forEach((dot, i) => {
        dot.style.width = dias[i] + "px";
        dot.style.height = dias[i] + "px";
    });
}

function paintExpression(metricId, paletteName, classify, level) {
    const colors = PALETTES[paletteName].colors;
    const values = getValuesForLevel(level, metricId);

    const valid = ["case",
        ["==", ["typeof", ["get", metricId]], "number"], true,
        false
    ];

    if (classify === "continuous") {
        if (values.length < 2) return ["case", valid, colors[colors.length - 1], NO_DATA_COLOR];
        const min = Math.min(...values);
        const max = Math.max(...values);
        const stops = sampleColors(colors, 5);
        const expr = ["interpolate", ["linear"], ["to-number", ["get", metricId]]];
        for (let i = 0; i < stops.length; i++) {
            expr.push(min + (max - min) * i / (stops.length - 1), stops[i]);
        }
        return ["case", valid, expr, NO_DATA_COLOR];
    }

    const breaks = classify === "quantile"
        ? quantileBreaks(values, 5)
        : classify === "jenks"
            ? jenksBreaks(values, 5)
            : equalIntervalBreaks(values, 5);
    const stops = sampleColors(colors, 5);
    // Ensure breaks are strictly increasing for MapLibre's step expression.
    // Jenks/quantile can return duplicates when the data has ties.
    const cleanBreaks = [];
    let prev = -Infinity;
    breaks.forEach(b => {
        const v = Number(b);
        if (isFinite(v) && v > prev) {
            cleanBreaks.push(v);
            prev = v;
        }
    });
    if (cleanBreaks.length === 0) {
        return ["case", valid, stops[Math.floor(stops.length / 2)], NO_DATA_COLOR];
    }
    const expr = ["step", ["to-number", ["get", metricId]], stops[0]];
    cleanBreaks.forEach((b, i) => { expr.push(b, stops[Math.min(i + 1, stops.length - 1)]); });
    return ["case", valid, expr, NO_DATA_COLOR];
}

// ─── HOME / RESET-VIEW CONTROL ───────────────────────────────────────────────
// A standard map button (stacked under the zoom +/−) that flies back to the
// default Lynn extent. Mirrors the atlas's HomeControl, retargeted at VIEWS.lynn.
class HomeControl {
    onAdd(m) {
        this._map = m;
        const c = document.createElement("div");
        c.className = "maplibregl-ctrl maplibregl-ctrl-group";
        const b = document.createElement("button");
        b.type = "button";
        b.className = "maplibregl-ctrl-home";
        b.title = "Reset to the Lynn view";
        b.setAttribute("aria-label", "Reset map to the default Lynn view");
        b.innerHTML = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">' +
            '<path d="M3 11l9-8 9 8" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>' +
            '<path d="M5 10v10h5v-6h4v6h5V10" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
        b.addEventListener("click", () => {
            const v = (typeof VIEWS !== "undefined" && VIEWS.lynn) ? VIEWS.lynn : { center: [-70.95, 42.47], zoom: 11.8 };
            m.flyTo({ ...v, duration: 1000, essential: true });
            if (typeof setActiveView === "function") setActiveView("lynn");
        });
        c.appendChild(b);
        this._container = c;
        return c;
    }
    onRemove() { if (this._container) this._container.remove(); this._map = undefined; }
}

// ─── MAP INITIALIZATION ──────────────────────────────────────────────────────
// Smooth choropleth color cross-fade when the metric/year changes (applied via
// the fill layers' paint transitions). Off for users who prefer reduced motion.
const PREFERS_REDUCED_MOTION = !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
const FILL_XFADE_MS = PREFERS_REDUCED_MOTION ? 0 : 260;

const map = new maplibregl.Map({
    container: "map",
    style: "https://tiles.openfreemap.org/styles/positron",
    center: [-70.95, 42.47],   // Lynn close-up — Lynn-focused default
    zoom: 12.3,
    minZoom: 6,
    maxZoom: 18,
    attributionControl: false,
});
map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
// Standard map controls users expect, stacked under the zoom buttons (top-right):
// jump back to the Lynn view, locate themselves, and go fullscreen.
map.addControl(new HomeControl(), "top-right");
map.addControl(new maplibregl.GeolocateControl({
    positionOptions: { enableHighAccuracy: true },
    // trackUserLocation makes the control a TOGGLE: click to show your location,
    // click the active button again to clear the dot.
    trackUserLocation: true,
    showUserLocation: true,
}), "top-right");
// Fullscreen the whole app shell (#main-content / .maps-main), not just the map
// canvas — the panel, legend, and modals are siblings of #map, so targeting
// their shared ancestor keeps the entire UI visible in fullscreen.
map.addControl(
    new maplibregl.FullscreenControl({ container: document.getElementById("main-content") }),
    "top-right"
);
// Leaving/entering fullscreen changes the map size — let it re-fit.
document.addEventListener("fullscreenchange", () => { map.resize(); });
map.addControl(new maplibregl.AttributionControl({
    compact: true,
    customAttribution: '<a href="https://maxwellhowegis.com" target="_blank">© Maxwell Howe</a> · MA DESE · US Census · MassGIS · © CARTO',
}), "bottom-right");
map.addControl(new maplibregl.ScaleControl({ maxWidth: 120, unit: "imperial" }), "bottom-left");

// Positron's own vector layer IDs — captured before we add data layers so the
// theme swap can hide/show the light basemap without touching our overlays.
let BASEMAP_LAYER_IDS = [];

// Add a keyless CARTO dark-matter raster basemap as the BOTTOM layer (hidden by
// default; shown in dark theme). Inserted beneath the first Positron layer so it
// sits under everything; our data layers are added on top afterwards.
function addDarkBasemap() {
    if (!map.getSource("dark-tiles")) {
        map.addSource("dark-tiles", {
            type: "raster", tileSize: 256,
            tiles: [
                "https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
                "https://b.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
                "https://c.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
            ],
            attribution: "© OpenStreetMap contributors, © CARTO",
        });
    }
    if (!map.getLayer("dark-base")) {
        const firstId = BASEMAP_LAYER_IDS[0];   // insert beneath Positron's first layer
        map.addLayer(
            { id: "dark-base", type: "raster", source: "dark-tiles", layout: { visibility: "none" } },
            firstId
        );
    }
}

// Swap the basemap to match the theme: light → Positron vector layers visible,
// dark raster hidden; dark → Positron hidden, dark raster shown. Also re-halo
// our own symbol labels (town + school) so they stay legible on the dark base.
function applyThemeBasemap(theme) {
    const dark = theme === "dark";
    BASEMAP_LAYER_IDS.forEach(id => {
        if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", dark ? "none" : "visible");
    });
    if (map.getLayer("dark-base")) {
        map.setLayoutProperty("dark-base", "visibility", dark ? "visible" : "none");
    }
    // Page behind the (transparent) canvas: near-black for dark so any gaps read
    // on-theme; default otherwise.
    const container = map.getContainer();
    if (container) container.style.background = dark ? "#0b0b0d" : "";
    // Our text labels need a light fill + dark halo to stay legible on the dark
    // base. Each block is getLayer-guarded (no-op until the layer exists).
    if (map.getLayer("town-labels")) {
        map.setPaintProperty("town-labels", "text-color", dark ? "#ECEFF1" : "#0A1F44");
        map.setPaintProperty("town-labels", "text-halo-color", dark ? "#000000" : "#ffffff");
        map.setPaintProperty("town-labels", "text-halo-width", dark ? 2.0 : 1.8);
    }
    if (map.getLayer("schools-labels")) {
        map.setPaintProperty("schools-labels", "text-color", dark ? "#ECEFF1" : "#0A1F44");
        // Keep the gold halo on the focus school in both themes; others get a
        // dark halo in dark mode for contrast.
        map.setPaintProperty("schools-labels", "text-halo-color", [
            "case",
            ["==", ["get", "ORG_CODE"], LEHS_ORG_CODE], "#FFF3D6",
            dark ? "#0b0b0d" : "#ffffff",
        ]);
    }
}

map.on("load", async () => {
    try {
        const [tracts, schools, town, academic, ccuv, munis, maSchools] = await Promise.all([
            fetch(SOURCES.tracts).then(r => r.json()),
            fetch(SOURCES.schools).then(r => r.json()),
            fetch(SOURCES.town).then(r => r.json()),
            fetch(SOURCES.academic).then(r => r.json()),
            fetch(SOURCES.ccuv).then(r => r.json()),
            fetch(SOURCES.municipalities).then(r => r.json()),
            fetch(SOURCES.maSchools).then(r => r.json()).catch(() => ({ type: "FeatureCollection", features: [] })),
        ]);

        // Some tract columns are written as strings (e.g. "0.32") in the
        // upstream pipeline. MapLibre's paint expressions use
        //   ["==", ["typeof", ["get", metricId]], "number"]
        // for validity, so string values render as "no data" cream. Coerce
        // any numeric-looking string property to a real number once at load
        // time — covers tracts today and future schema drift on any source.
        [tracts, academic, munis].forEach(coerceNumericStringProps);

        // Capture Positron's own layer IDs BEFORE we add data/basemap layers, so
        // the theme swap can hide/show the light vector basemap cleanly.
        BASEMAP_LAYER_IDS = map.getStyle().layers.map(l => l.id);

        GEO_DATA = { tract: tracts, district: academic, muni: munis };
        buildYearKeyedIndex();
        buildGroupKeyedIndex();

        // Sub-collections of CCUV by type, for separate styling
        const voctech = {
            type: "FeatureCollection",
            features: ccuv.features.filter(f => f.properties.TYPE === "Vocational"),
        };
        const charter = {
            type: "FeatureCollection",
            features: ccuv.features.filter(f => f.properties.TYPE === "Charter"),
        };

        // generateId: true assigns a numeric feature ID so setFeatureState works
        map.addSource("tracts",         { type: "geojson", data: tracts,    generateId: true });
        map.addSource("schools",        { type: "geojson", data: schools,   generateId: true });
        map.addSource("town",           { type: "geojson", data: town,      generateId: true });
        map.addSource("districts",      { type: "geojson", data: academic,  generateId: true });
        map.addSource("ccuv-voctech",   { type: "geojson", data: voctech,   generateId: true });
        map.addSource("ccuv-charter",   { type: "geojson", data: charter,   generateId: true });
        map.addSource("municipalities", { type: "geojson", data: munis,     generateId: true });
        map.addSource("ma-schools",     { type: "geojson", data: maSchools, generateId: true });
        map.addSource("lynn-only", {
            type: "geojson",
            data: {
                type: "FeatureCollection",
                features: munis.features.filter(f => f.properties.is_lynn),
            },
        });
        map.addSource("gateway-only", {
            type: "geojson",
            data: {
                type: "FeatureCollection",
                features: munis.features.filter(f => f.properties.is_gateway && !f.properties.is_lynn),
            },
        });

        addDarkBasemap();
        addLayers();
        wireUI();
        applyChoropleth();
        updateLegend();
        // Paint the basemap + label halos to match the (already-set) theme attr,
        // and sync the toggle button. skipBasemap on applyTheme would double-call,
        // so call applyThemeBasemap directly here.
        applyThemeBasemap(state.theme);
        syncThemeButton();
        document.getElementById("mapLoading").classList.add("hidden");
    } catch (err) {
        console.error("Map load failed:", err);
        document.getElementById("mapLoading").innerHTML =
            "<div>Failed to load map data. Check browser console.</div>";
    }
});

function addLayers() {
    // ── CHOROPLETH LAYERS (one visible at a time based on state.level) ───────
    // Use feature-state for hover highlights without re-styling
    // Choropleth fill opacity is a touch lower than a standard atlas (0.68 vs
    // ~0.8) so the school dots — the centerpiece of this Lynn map — pop off the
    // backdrop. Hover still lifts to 0.85 for clear feedback.
    map.addLayer({
        id: "muni-fill", type: "fill", source: "municipalities",
        paint: {
            "fill-color": NO_DATA_COLOR,
            // Brief cross-fade so recoloring on metric/year change eases in
            // instead of hard-flipping (respects prefers-reduced-motion).
            "fill-color-transition": { duration: FILL_XFADE_MS, delay: 0 },
            "fill-opacity": [
                "case",
                ["boolean", ["feature-state", "hover"], false], 0.85,
                0.68
            ],
        },
        layout: { visibility: state.level === "muni" ? "visible" : "none" },
    });
    map.addLayer({
        id: "district-fill", type: "fill", source: "districts",
        paint: {
            "fill-color": NO_DATA_COLOR,
            "fill-color-transition": { duration: FILL_XFADE_MS, delay: 0 },
            "fill-opacity": [
                "case",
                ["boolean", ["feature-state", "hover"], false], 0.85,
                0.68
            ],
        },
        layout: { visibility: state.level === "district" ? "visible" : "none" },
    });
    map.addLayer({
        id: "tract-fill", type: "fill", source: "tracts",
        paint: {
            "fill-color": NO_DATA_COLOR,
            "fill-color-transition": { duration: FILL_XFADE_MS, delay: 0 },
            "fill-opacity": [
                "case",
                ["boolean", ["feature-state", "hover"], false], 0.85,
                0.68
            ],
        },
        layout: { visibility: state.level === "tract" ? "visible" : "none" },
    });

    // Per-source hover-outline layers — each invisible by default, only the
    // hovered feature gets gold edges. Cheaper than re-adding the layer on
    // every mousemove.
    ["municipalities", "districts", "tracts"].forEach(src => {
        const cfg = {
            id: `hover-outline-${src}`, type: "line", source: src,
            paint: {
                "line-color": "#FFB81C",
                "line-width": 3.5,
                "line-opacity": ["case", ["boolean", ["feature-state", "hover"], false], 1, 0],
            },
        };
        map.addLayer(cfg);
    });

    // ── ALWAYS-ON REFERENCE BORDERS ──────────────────────────────────────────
    // Municipality borders
    map.addLayer({
        id: "muni-outline", type: "line", source: "municipalities",
        paint: {
            "line-color": "#78909c",
            "line-width": [
                "interpolate", ["linear"], ["zoom"],
                7, 0.35,
                10, 0.7,
                12, 1.0,
            ],
            "line-opacity": 0.75,
        },
    });
    // Academic district borders (dissolved town boundaries — ~250 districts)
    map.addLayer({
        id: "academic-outline", type: "line", source: "districts",
        paint: {
            "line-color": "#1a3a6b",
            "line-width": 1.5,
            "line-opacity": 0.8,
        },
        layout: { visibility: state.showAcademicOutline ? "visible" : "none" },
    });

    // Regional vocational/technical district OVERLAY (they cross town lines)
    map.addLayer({
        id: "voctech-fill", type: "fill", source: "ccuv-voctech",
        paint: {
            "fill-color": "#6a1b9a",
            "fill-opacity": 0.08,
        },
        layout: { visibility: state.showVoctechOverlay ? "visible" : "none" },
    });
    map.addLayer({
        id: "voctech-outline", type: "line", source: "ccuv-voctech",
        paint: {
            "line-color": "#6a1b9a",
            "line-width": 1.8,
            "line-opacity": 0.85,
            "line-dasharray": [4, 2],
        },
        layout: { visibility: state.showVoctechOverlay ? "visible" : "none" },
    });

    // Charter district OVERLAY (service areas — also cross town lines)
    map.addLayer({
        id: "charter-fill", type: "fill", source: "ccuv-charter",
        paint: {
            "fill-color": "#00897B",
            "fill-opacity": 0.08,
        },
        layout: { visibility: state.showCharterOverlay ? "visible" : "none" },
    });
    map.addLayer({
        id: "charter-outline", type: "line", source: "ccuv-charter",
        paint: {
            "line-color": "#00695C",
            "line-width": 1.3,
            "line-opacity": 0.85,
            "line-dasharray": [1, 2],
        },
        layout: { visibility: state.showCharterOverlay ? "visible" : "none" },
    });

    // ── GATEWAY HIGHLIGHT (filled overlay on the 25 non-Lynn gateways) ───────
    map.addLayer({
        id: "gateway-highlight-fill", type: "fill", source: "gateway-only",
        paint: { "fill-color": "#9C27B0", "fill-opacity": 0.18 },
        layout: { visibility: state.showGatewayHighlight ? "visible" : "none" },
    });
    map.addLayer({
        id: "gateway-highlight-line", type: "line", source: "gateway-only",
        paint: { "line-color": "#6a1b9a", "line-width": 2.2, "line-opacity": 0.95 },
        layout: { visibility: state.showGatewayHighlight ? "visible" : "none" },
    });

    // ── LYNN HIGHLIGHT (gold fill + outline) ─────────────────────────────────
    map.addLayer({
        id: "lynn-highlight-fill", type: "fill", source: "lynn-only",
        paint: { "fill-color": "#FFB81C", "fill-opacity": 0.22 },
        layout: { visibility: state.showLynnTown ? "visible" : "none" },
    });
    map.addLayer({
        id: "lynn-highlight-line", type: "line", source: "lynn-only",
        paint: { "line-color": "#0A1F44", "line-width": 3.5, "line-opacity": 1.0 },
        layout: { visibility: state.showLynnTown ? "visible" : "none" },
    });

    // ── LYNN TOWN NEIGHBORS LABELS ───────────────────────────────────────────
    map.addLayer({
        id: "town-labels", type: "symbol", source: "town",
        layout: {
            "text-field": ["upcase", ["get", "TOWN"]],
            "text-font": ["Noto Sans Bold"],
            "text-size": 11,
            "text-letter-spacing": 0.08,
            "visibility": state.townLabels ? "visible" : "none",
        },
        paint: {
            "text-color": "#0A1F44",
            "text-halo-color": "#ffffff",
            "text-halo-width": 1.8,
        },
        minzoom: 10,
    });

    // ── ALL MA PUBLIC SCHOOLS (~1700) — toggleable, small markers ────────────
    map.addLayer({
        id: "ma-schools-circles", type: "circle", source: "ma-schools",
        paint: {
            "circle-radius": [
                "interpolate", ["linear"], ["zoom"],
                8, 1.5, 11, 3, 14, 5,
            ],
            "circle-color": [
                "match", ["get", "TYPE_DESC"],
                "Charter",                       "#00897B",
                "Public Voc/Tech/Ag Reg'l HS",   "#6a1b9a",
                "Public Elementary",             "#1976D2",
                "Public Middle",                 "#F57C00",
                "Public Secondary",              "#C62828",
                "#455A64",
            ],
            "circle-stroke-color": "#ffffff",
            "circle-stroke-width": 0.8,
            "circle-opacity": 0.85,
        },
        layout: { visibility: state.showAllMaSchools ? "visible" : "none" },
        minzoom: 7,
    });

    // ── LYNN SCHOOLS — THE CENTERPIECE (halo + proportional dots + focus ring) ─
    // Soft white halo underneath each dot so schools pop off the choropleth
    // backdrop regardless of the fill color behind them.
    map.addLayer({
        id: "schools-halo", type: "circle", source: "schools",
        paint: {
            "circle-radius": SCHOOL_RADIUS_HALO,
            "circle-color": "#ffffff",
            "circle-opacity": 0.55,
            "circle-blur": 0.35,
        },
        layout: { visibility: state.showLynnSchools ? "visible" : "none" },
    });
    // Gold focus ring drawn UNDER the dot for Lynn English High only — a fat gold
    // halo that reads as "special" no matter the active color mode. Filtered to
    // the single LEHS feature so it never paints anywhere else.
    map.addLayer({
        id: "schools-lehs-ring", type: "circle", source: "schools",
        filter: ["==", ["get", "ORG_CODE"], LEHS_ORG_CODE],
        paint: {
            "circle-radius": SCHOOL_RADIUS_LEHS_RING,
            "circle-color": "rgba(0,0,0,0)",
            "circle-stroke-color": "#FFB81C",
            "circle-stroke-width": 4,
            "circle-stroke-opacity": 0.95,
        },
        layout: { visibility: state.showLynnSchools ? "visible" : "none" },
    });
    // The proportional, color-coded school dots themselves.
    map.addLayer({
        id: "schools-circles", type: "circle", source: "schools",
        paint: {
            "circle-radius": SCHOOL_RADIUS,
            "circle-color": schoolColorExpression(),
            "circle-stroke-color": "#ffffff",
            "circle-stroke-width": [
                "case",
                ["==", ["get", "ORG_CODE"], LEHS_ORG_CODE], 2.4,
                1.6,
            ],
            "circle-opacity": 0.95,
        },
        layout: { visibility: state.showLynnSchools ? "visible" : "none" },
    });
    // School name labels — appear a touch earlier than before; LEHS label always
    // shown (no collision-drop) and rendered bold/gold-haloed to stand out.
    map.addLayer({
        id: "schools-labels", type: "symbol", source: "schools",
        layout: {
            "text-field": ["get", "NAME"],
            // text-font can't be data-driven reliably across MapLibre versions, so
            // it stays static (Bold); LEHS emphasis is carried by a larger size,
            // a gold halo, and always-on label visibility below.
            "text-font": ["Noto Sans Bold"],
            "text-size": [
                "case",
                ["==", ["get", "ORG_CODE"], LEHS_ORG_CODE], 13,
                10,
            ],
            "text-anchor": "top",
            "text-offset": [0, 1.2],
            "text-optional": ["!=", ["get", "ORG_CODE"], LEHS_ORG_CODE],
            "text-allow-overlap": ["==", ["get", "ORG_CODE"], LEHS_ORG_CODE],
            "visibility": state.labels ? "visible" : "none",
        },
        paint: {
            "text-color": "#0A1F44",
            "text-halo-color": [
                "case",
                ["==", ["get", "ORG_CODE"], LEHS_ORG_CODE], "#FFF3D6",
                "#ffffff",
            ],
            "text-halo-width": 1.6,
        },
        minzoom: 12,
    });

    // ── CLICK HANDLERS ───────────────────────────────────────────────────────
    map.on("click", "muni-fill",     e => showPopup(e, "muni"));
    map.on("click", "district-fill", e => showPopup(e, "district"));
    map.on("click", "tract-fill",    e => showPopup(e, "tract"));
    map.on("click", "schools-circles", e => showPopup(e, "school"));

    // ── HOVER HIGHLIGHT + TOOLTIP ────────────────────────────────────────────
    const sourceForLevel = { muni: "municipalities", district: "districts", tract: "tracts" };
    let hoverState = { source: null, id: null };

    function setHover(source, id) {
        if (hoverState.source && hoverState.id != null) {
            map.setFeatureState({ source: hoverState.source, id: hoverState.id }, { hover: false });
        }
        if (source && id != null) {
            map.setFeatureState({ source, id }, { hover: true });
        }
        hoverState = { source, id };
    }

    const tooltip = document.getElementById("mapTooltip");
    function showTooltip(e, feat) {
        const m = getMetric(state.metric);
        const v = feat.properties[activeColumn()];
        const name = feat.properties.town_display
            || feat.properties.TOWN
            || feat.properties.DIST_NAME
            || feat.properties.NAMELSAD
            || "Feature";
        tooltip.innerHTML = `
            <div class="tooltip-name">${name}</div>
            <div class="tooltip-value">${m.label}: <strong>${fmt(+v, m.format)}</strong></div>
        `;
        tooltip.style.display = "block";
        tooltip.style.left = (e.point.x + 14) + "px";
        tooltip.style.top  = (e.point.y + 14) + "px";
    }
    function hideTooltip() { tooltip.style.display = "none"; }

    ["muni-fill", "district-fill", "tract-fill"].forEach(layerId => {
        const lvl = layerId.split("-")[0];
        const src = sourceForLevel[lvl];
        map.on("mousemove", layerId, e => {
            map.getCanvas().style.cursor = "pointer";
            if (!e.features.length) return;
            const feat = e.features[0];
            setHover(src, feat.id);
            showTooltip(e, feat);
        });
        map.on("mouseleave", layerId, () => {
            map.getCanvas().style.cursor = "";
            setHover(null, null);
            hideTooltip();
        });
    });

    map.on("mouseenter", "schools-circles", () => map.getCanvas().style.cursor = "pointer");
    map.on("mouseleave", "schools-circles", () => map.getCanvas().style.cursor = "");

    // MA-wide schools click → simple popup with school info
    map.on("click", "ma-schools-circles", e => {
        if (!e.features.length) return;
        const p = e.features[0].properties;
        new maplibregl.Popup({ closeButton: true, maxWidth: "300px" })
            .setLngLat(e.lngLat)
            .setHTML(`
                <div class="popup-title">${p.NAME}</div>
                <div class="popup-row"><span class="label">Type</span><span class="value">${p.TYPE_DESC || "—"}</span></div>
                <div class="popup-row"><span class="label">Grades</span><span class="value">${p.GRADES || "—"}</span></div>
                <div class="popup-row"><span class="label">Town</span><span class="value">${p.TOWN || "—"}</span></div>
                <div class="popup-row"><span class="label">District</span><span class="value">${p.DIST_NAME || "—"}</span></div>
            `)
            .addTo(map);
    });
    map.on("mouseenter", "ma-schools-circles", () => map.getCanvas().style.cursor = "pointer");
    map.on("mouseleave", "ma-schools-circles", () => map.getCanvas().style.cursor = "");
}

// ─── FEATURE DETAIL — STICKY SIDE PANEL (replaces popup) ─────────────────────
function showPopup(e, kind) {
    if (!e.features.length) return;
    openFeaturePanel(e.features[0].properties, kind);
}

function openFeaturePanel(p, kind) {
    const panel = document.getElementById("featurePanel");
    const title = document.getElementById("featurePanelTitle");
    const body = document.getElementById("featurePanelBody");
    title.textContent = featureName(p, kind);
    body.innerHTML = buildPanelHtml(p, kind);
    panel.classList.add("open");
    panel.setAttribute("aria-hidden", "false");

    // Mobile: auto-close the control drawer so the bottom-sheet has room
    if (window.matchMedia("(max-width: 768px)").matches) {
        const ctrl = document.getElementById("controlPanel");
        const bd   = document.getElementById("panelBackdrop");
        if (ctrl) ctrl.classList.remove("open");
        if (bd)   bd.classList.remove("open");
    }
}

function closeFeaturePanel() {
    const panel = document.getElementById("featurePanel");
    panel.classList.remove("open");
    panel.setAttribute("aria-hidden", "true");
}

function featureName(p, kind) {
    if (kind === "school")   return p.NAME || "School";
    if (kind === "tract")    return p.NAMELSAD || "Census Tract";
    if (kind === "muni")     return p.town_display || p.TOWN || "Municipality";
    if (kind === "district") return p.dist_display || p.DIST_NAME || "District";
    return "Feature";
}

function fpSection(title, rowsHtml) {
    return rowsHtml.trim()
        ? `<div class="feature-panel-section"><h3>${title}</h3>${rowsHtml}</div>`
        : "";
}

function fpRow(label, value, kind = "num", highlight = false) {
    const v = fmt(+value, kind);
    if (value == null || !isFinite(+value)) return "";
    return `<div class="feature-panel-row"><span class="label">${label}</span><span class="value${highlight ? ' highlight' : ''}">${v}</span></div>`;
}

// Turn the DESE grade string ("PK,K,01,02,...") into a friendly span ("PK–5").
function formatGrades(gradesStr) {
    if (!gradesStr) return "—";
    const parts = String(gradesStr).split(",").map(s => s.trim()).filter(Boolean);
    if (!parts.length) return "—";
    const norm = g => (g === "PK" ? "PK" : g === "K" ? "K" : String(parseInt(g, 10)));
    const first = norm(parts[0]);
    const last = norm(parts[parts.length - 1]);
    return parts.length === 1 ? first : `${first}–${last}`;
}

// Single labeled horizontal bar (value 0–1) for a school composition metric.
function fpBarRow(label, value, color) {
    if (value == null || !isFinite(+value)) return "";
    const pct = Math.max(0, Math.min(100, +value * 100));
    return `<div class="fp-bar-row">
        <div class="fp-bar-head"><span class="fp-bar-label">${label}</span><span class="fp-bar-val">${pct.toFixed(1)}%</span></div>
        <div class="fp-bar-track"><span class="fp-bar-fill" style="width:${pct}%;background:${color};"></span></div>
    </div>`;
}

// Stacked single-row bar for the race/ethnicity breakdown.
function fpStackBar(segments) {
    const total = segments.reduce((a, s) => a + +s.v, 0) || 1;
    const segHtml = segments.map(s =>
        `<span class="fp-stack-seg" style="width:${(+s.v / total) * 100}%;background:${s.color};" title="${s.label}: ${(+s.v * 100).toFixed(1)}%"></span>`
    ).join("");
    const legHtml = segments.map(s =>
        `<span class="fp-stack-key"><span class="fp-stack-sw" style="background:${s.color};"></span>${s.label} ${(+s.v * 100).toFixed(0)}%</span>`
    ).join("");
    return `<div class="fp-stack">${segHtml}</div><div class="fp-stack-legend">${legHtml}</div>`;
}

// "Student composition" section as labeled bars — the headline equity metrics.
function buildSchoolCompositionSection(p) {
    const bars = [
        fpBarRow("English Learner", p.EL_PCT, "#43A047"),
        fpBarRow("Low Income", p.LI_PCT, "#E53935"),
        fpBarRow("High Needs", p.HN_PCT, "#8E24AA"),
        fpBarRow("Students w/ Disabilities", p.SWD_PCT, "#5C6BC0"),
        fpBarRow("First Lang. Not English", p.FLNE_PCT, "#00897B"),
    ].join("");
    if (!bars.trim()) return "";
    return `<div class="feature-panel-section"><h3>Student composition</h3>${bars}</div>`;
}

function buildPanelHtml(p, kind) {
    if (kind === "school") {
        const isLehs = p.ORG_CODE === LEHS_ORG_CODE;
        const typeLabel = (SCHOOL_TYPES.find(t => t.key === p.TYPE) || {}).label || p.TYPE_DESC || "School";
        const grades = formatGrades(p.GRADES);
        const enrollHtml = (p.TOTAL_CNT != null && isFinite(+p.TOTAL_CNT))
            ? `<div class="school-enroll-num">${(+p.TOTAL_CNT).toLocaleString()}</div><div class="school-enroll-lbl">students enrolled${p.SY ? ` · SY ${p.SY}` : ""}</div>`
            : `<div class="school-enroll-lbl" style="font-style:italic;">No DESE enrollment / demographics reported (private or charter).</div>`;
        // Race/ethnicity composition stacked bar (only when data present).
        const raceParts = [
            { label: "Hispanic / Latino", v: p.HL_PCT,  color: "#F57C00" },
            { label: "Black / African Am.", v: p.BAA_PCT, color: "#7B1FA2" },
            { label: "Asian", v: p.AS_PCT, color: "#1976D2" },
            { label: "White", v: p.WH_PCT, color: "#90A4AE" },
            { label: "Multi / Other", v: p.MNHL_PCT, color: "#26A69A" },
        ].filter(s => s.v != null && isFinite(+s.v) && +s.v > 0);
        return `
            ${isLehs
                ? '<div class="feature-panel-tag lehs-badge">★ Lynn English — focus school</div>'
                : `<div class="school-type-pill" style="background:${(SCHOOL_TYPES.find(t => t.key === p.TYPE) || {}).color || "#607D8B"};">${typeLabel}</div>`}
            <div class="feature-panel-section school-headline">
                <div class="feature-panel-row"><span class="label">Type</span><span class="value">${typeLabel}${p.TYPE_DESC ? ` <span style="color:#90A4AE;font-weight:400;">(${p.TYPE_DESC})</span>` : ""}</span></div>
                <div class="feature-panel-row"><span class="label">Grades</span><span class="value">${grades}</span></div>
                ${p.ADDRESS ? `<div class="feature-panel-row"><span class="label">Address</span><span class="value" style="font-weight:400;text-align:right;">${p.ADDRESS}</span></div>` : ""}
                <div class="school-enroll">${enrollHtml}</div>
            </div>
            ${buildSchoolCompositionSection(p)}
            ${raceParts.length ? `
                <div class="feature-panel-section">
                    <h3>Race / ethnicity</h3>
                    ${fpStackBar(raceParts)}
                </div>` : ""}
        `;
    }
    if (kind === "tract") {
        return `
            <div class="feature-panel-section">
                <div class="feature-panel-row"><span class="label">GEOID</span><span class="value">${p.GEOID}</span></div>
                ${fpRow("Population (age 5+)", p.lang_total, "num")}
            </div>
            ${fpSection("Census ACS — economic", [
                fpRow("Median household income", p.median_household_income, "usd"),
                fpRow("% Severely rent-burdened", p.severe_burden_pct, "pct"),
            ].join(""))}
            ${fpSection("Census ACS — demographic", [
                fpRow("% Foreign-born", p.foreign_born_pct, "pct"),
                fpRow("% non-English at home", p.non_english_pct, "pct"),
                fpRow("% Bachelor's or higher", p.bachelors_or_higher_pct, "pct"),
            ].join(""))}
            ${state.metric ? fpSection("Active metric", [
                fpRow(getMetric(state.metric).label, p[activeColumn()], getMetric(state.metric).format, true)
            ].join("")) : ""}
        `;
    }
    if (kind === "muni") {
        let tagHtml = "";
        if (p.is_lynn) tagHtml = '<div class="feature-panel-tag" style="background:#FFE082;">Lynn — dashboard focus</div>';
        else if (p.is_gateway) tagHtml = '<div class="feature-panel-tag" style="background:#E1BEE7;">Gateway City</div>';
        return `
            ${tagHtml}
            <div class="feature-panel-section">
                <div class="feature-panel-row"><span class="label">County</span><span class="value">${p.COUNTY || "—"}</span></div>
                ${fpRow("Population (2020)", p.pop_2020 || p.POP2020, "num")}
                ${p.DIST_NAME ? `<div class="feature-panel-row"><span class="label">Matched district</span><span class="value">${p.DIST_NAME}</span></div>` : ""}
            </div>
            ${fpSection("District composition", [
                fpRow("Enrollment", p.TOTAL_CNT, "num"),
                fpRow("% English Learner", p.EL_PCT, "pct"),
                fpRow("% Low Income", p.LI_PCT, "pct"),
                fpRow("% High Needs", p.HN_PCT, "pct"),
            ].join(""))}
            ${fpSection("District outcomes", [
                fpRow("4-yr Graduation", p.grad_4yr, "pct"),
                fpRow("Dropout", p.dropout_pct, "pct"),
                fpRow("MCAS Gr10 ELA % M+E", p.mcas_g10_ela_me, "pct"),
                fpRow("MCAS Gr10 Math % M+E", p.mcas_g10_math_me, "pct"),
                fpRow("Chronic absent", p.chronic_absent_pct, "pct"),
            ].join(""))}
            ${fpSection("Finance", [
                fpRow("Per-pupil $", p.per_pupil, "usd"),
            ].join(""))}
            ${fpSection("Active metric", [
                fpRow(getMetric(state.metric).label, p[activeColumn()], getMetric(state.metric).format, true)
            ].join(""))}
        `;
    }
    if (kind === "district") {
        const isLynn = p.DIST_CODE === "01630000" || p.is_lynn === true;
        return `
            ${isLynn ? '<div class="feature-panel-tag" style="background:#FFE082;">Lynn Public Schools</div>' : ""}
            <div class="feature-panel-section">
                <div class="feature-panel-row"><span class="label">District code</span><span class="value">${p.DIST_CODE || "—"}</span></div>
                ${fpRow("Enrollment", p.TOTAL_CNT, "num")}
            </div>
            ${fpSection("Student composition", [
                fpRow("% English Learner", p.EL_PCT, "pct"),
                fpRow("% Low Income", p.LI_PCT, "pct"),
                fpRow("% High Needs", p.HN_PCT, "pct"),
                fpRow("% Hispanic/Latino", p.HL_PCT, "pct"),
                fpRow("% Black/African Am.", p.BAA_PCT, "pct"),
                fpRow("% White", p.WH_PCT, "pct"),
                fpRow("% SPED", p.SWD_PCT, "pct"),
            ].join(""))}
            ${fpSection("Academic outcomes", [
                fpRow("MCAS Gr10 ELA % M+E", p.mcas_g10_ela_me, "pct"),
                fpRow("MCAS Gr10 Math % M+E", p.mcas_g10_math_me, "pct"),
                fpRow("MCAS Gr10 STE % M+E", p.mcas_g10_sci_me, "pct"),
                fpRow("4-yr Graduation", p.grad_4yr, "pct"),
                fpRow("5-yr Graduation", p.grad_5yr, "pct"),
                fpRow("Dropout", p.dropout_pct, "pct"),
                fpRow("Attendance", p.attendance_rate, "pct"),
                fpRow("Chronic absent", p.chronic_absent_pct, "pct"),
                fpRow("MassCore completion", p.masscore_pct, "pct"),
                fpRow("AP % scoring 3+", p.ap_pct_3plus, "pct"),
            ].join(""))}
            ${fpSection("Postsecondary plans", [
                fpRow("% Any college", p.pct_any_college, "pct"),
                fpRow("% 4-yr college", p.pct_4yr_college, "pct"),
                fpRow("% 2-yr college", p.pct_2yr_college, "pct"),
                fpRow("% Work after HS", p.pct_work_after_hs, "pct"),
                fpRow("% Military", p.pct_military, "pct"),
            ].join(""))}
            ${fpSection("Finance — per-pupil $", [
                fpRow("Total", p.per_pupil, "usd"),
                fpRow("Teachers", p.per_pupil_teachers, "usd"),
                fpRow("Administration", p.per_pupil_admin, "usd"),
                fpRow("Pupil services", p.per_pupil_pupil_services, "usd"),
            ].join(""))}
            ${fpSection("Workforce", [
                fpRow("Student : Teacher", p.stu_tchr_ratio, "num"),
                fpRow("% Experienced teachers", p.teacher_experienced_pct, "pct"),
                fpRow("% Teachers in-field", p.teacher_infield_pct, "pct"),
                fpRow("Teacher retention", p.teacher_retention_pct, "pct"),
                fpRow("% Staff: White", p.staff_white_pct, "pct"),
                fpRow("% Staff: Hispanic", p.staff_hispanic_pct, "pct"),
                fpRow("% Staff: Black", p.staff_black_pct, "pct"),
            ].join(""))}
            ${fpSection("Active metric", [
                fpRow(getMetric(state.metric).label, p[activeColumn()], getMetric(state.metric).format, true)
            ].join(""))}
        `;
    }
    return `<div class="feature-panel-section">Click a feature on the map.</div>`;
}

// Wire close button + help modal (added once on load)
document.addEventListener("DOMContentLoaded", () => {
    const closeBtn = document.getElementById("featurePanelClose");
    if (closeBtn) closeBtn.addEventListener("click", closeFeaturePanel);

    // Help modal — opens via "?" button, auto-shows once on first visit.
    // Uses a Lynn-specific localStorage key so this map's help-seen state
    // is independent of the atlas's.
    const helpBtn   = document.getElementById("helpButton");
    const helpModal = document.getElementById("helpModal");
    const helpClose = document.getElementById("helpModalClose");
    const helpDone  = document.getElementById("helpGotIt");
    if (!helpModal) return;  // bail if HTML doesn't have the modal
    const openHelp  = () => { helpModal.classList.add("open"); helpModal.setAttribute("aria-hidden", "false"); };
    const closeHelp = () => { helpModal.classList.remove("open"); helpModal.setAttribute("aria-hidden", "true"); };
    if (helpBtn)   helpBtn.addEventListener("click", openHelp);
    if (helpClose) helpClose.addEventListener("click", closeHelp);
    if (helpDone)  helpDone.addEventListener("click", () => {
        try { localStorage.setItem("lynn-maps-help-seen", "1"); } catch (e) {}
        closeHelp();
    });
    helpModal.addEventListener("click", e => {
        if (e.target === helpModal) closeHelp();   // click backdrop
    });
    document.addEventListener("keydown", e => {
        if (e.key === "Escape") closeHelp();
    });
    try {
        if (!localStorage.getItem("lynn-maps-help-seen")) {
            setTimeout(openHelp, 800);  // brief delay so the map renders first
        }
    } catch (e) {}
});

// ─── CHOROPLETH APPLY ────────────────────────────────────────────────────────
function applyChoropleth() {
    const { level, metric, palette, classify } = state;
    const m = getMetric(metric);
    // Year-aware: paint uses year-keyed column when available, falls back to base
    const col = activeColumn(metric, state.year, level);
    const paint = paintExpression(col, palette, classify, level);
    const layerMap = { muni: "muni-fill", district: "district-fill", tract: "tract-fill" };
    Object.entries(layerMap).forEach(([lvl, layerId]) => {
        if (!map.getLayer(layerId)) return;
        map.setLayoutProperty(layerId, "visibility", lvl === level ? "visible" : "none");
        if (lvl === level) {
            map.setPaintProperty(layerId, "fill-color", paint);
        }
    });
    if (state.extrude3d) toggle3D();
}

// ─── LEGEND ──────────────────────────────────────────────────────────────────
function buildHistogram(values, breaks, palette) {
    // 24-bin mini histogram, colored according to which class each bin falls in
    if (values.length < 5) return "";
    const min = Math.min(...values), max = Math.max(...values);
    if (max === min) return "";
    const nBins = 24;
    const bins = Array(nBins).fill(0);
    const binWidth = (max - min) / nBins;
    values.forEach(v => {
        let idx = Math.floor((v - min) / binWidth);
        if (idx >= nBins) idx = nBins - 1;
        if (idx < 0) idx = 0;
        bins[idx]++;
    });
    const peak = Math.max(...bins);
    const colorForBin = (binVal) => {
        if (!breaks || breaks.length === 0) {
            // Continuous — interpolate position into palette
            const ratio = (binVal - min) / (max - min);
            const idx = Math.min(palette.length - 1, Math.max(0, Math.floor(ratio * palette.length)));
            return palette[idx];
        }
        for (let i = 0; i < breaks.length; i++) {
            if (binVal < breaks[i]) return palette[i];
        }
        return palette[breaks.length];
    };
    let html = '<div class="hist">';
    bins.forEach((count, i) => {
        const center = min + (i + 0.5) * binWidth;
        const h = Math.max(2, Math.round(28 * count / peak));
        html += `<span class="hist-bar" style="height:${h}px; background:${colorForBin(center)};" title="${count} polygon${count !== 1 ? 's' : ''}"></span>`;
    });
    html += '</div>';
    return html;
}

function updateLegend() {
    const { level, metric, palette, classify } = state;
    const m = getMetric(metric);
    const palObj = PALETTES[palette];
    const titleEl = document.getElementById("legendTitle");
    const stopsEl = document.getElementById("legendStops");
    const metaEl = document.getElementById("legendMeta");
    titleEl.textContent = m.label;

    const values = getValuesForLevel(level, metric);
    const totalFeatures = GEO_DATA[level] ? GEO_DATA[level].features.length : 0;
    const nullCount = Math.max(0, totalFeatures - values.length);

    if (values.length === 0) {
        stopsEl.innerHTML = '<div class="legend-row" style="color:var(--text-muted);">No data at this level for this metric.</div>';
        metaEl.innerHTML = `<span class="legend-null"><span class="legend-null-swatch"></span>No data — ${nullCount.toLocaleString()} of ${totalFeatures.toLocaleString()}</span>`;
        const capEl0 = document.getElementById("legendCaption");
        if (capEl0) capEl0.hidden = true;
        if (_legendClamp) _legendClamp();
        return;
    }

    let breaks = null;
    let stops = sampleColors(palObj.colors, 5);

    if (classify === "continuous") {
        const min = Math.min(...values), max = Math.max(...values);
        const colors9 = sampleColors(palObj.colors, 9);
        const bar = colors9.map(c => `<span class="legend-bar-stop" style="background:${c};"></span>`).join("");
        stopsEl.innerHTML = `
            ${buildHistogram(values, null, colors9)}
            <div class="legend-bar">${bar}</div>
            <div class="legend-axis">
                <span>${fmt(min, m.format)}</span>
                <span>${fmt(max, m.format)}</span>
            </div>
        `;
    } else {
        breaks = classify === "quantile"
            ? quantileBreaks(values, 5)
            : classify === "jenks"
                ? jenksBreaks(values, 5)
                : equalIntervalBreaks(values, 5);
        const ranges = [`&lt; ${fmt(breaks[0], m.format)}`];
        for (let i = 0; i < breaks.length - 1; i++) {
            ranges.push(`${fmt(breaks[i], m.format)} – ${fmt(breaks[i+1], m.format)}`);
        }
        ranges.push(`≥ ${fmt(breaks[breaks.length-1], m.format)}`);
        let html = buildHistogram(values, breaks, stops);
        for (let i = 0; i < 5; i++) {
            html += `<div class="legend-class"><span class="legend-class-swatch" style="background:${stops[i]};"></span><span class="legend-class-range">${ranges[i]}</span></div>`;
        }
        stopsEl.innerHTML = html;
    }

    // Always show a no-data swatch (so users learn what cream means)
    const dataPct = totalFeatures ? Math.round(100 * values.length / totalFeatures) : 0;
    metaEl.innerHTML = `
        <span class="legend-null"><span class="legend-null-swatch"></span>No data — <strong>${nullCount.toLocaleString()}</strong> of ${totalFeatures.toLocaleString()} polygons (${100 - dataPct}%)</span>
    `;

    // Plain-language "how to read the colors" caption (metric polarity).
    const capEl = document.getElementById("legendCaption");
    if (capEl) {
        const cap = legendCaptionText();
        capEl.textContent = cap;
        capEl.hidden = !cap;
    }
    // A moved/resized legend may now be a different height — keep it on-screen.
    if (_legendClamp) _legendClamp();
}

// ─── UI WIRING ───────────────────────────────────────────────────────────────
// Counts features with any non-null numeric value across the base column +
// any year-keyed (__YYYY) variants. Used to flag metrics that exist in the
// catalog but have no data in the currently-loaded GeoJSON (usually means
// the build pipeline ran but the source CSV was empty for those columns —
// re-running scripts/11_build_lynn_geo.py with fresh raw/ should populate
// them). Cached per (level, metricId) to keep the dropdown render cheap.
const _METRIC_DATA_CACHE = {};
function metricHasData(metricId, level) {
    const key = `${level}|${metricId}`;
    if (key in _METRIC_DATA_CACHE) return _METRIC_DATA_CACHE[key];
    const fc = GEO_DATA && GEO_DATA[level];
    if (!fc || !fc.features || !fc.features.length) {
        return _METRIC_DATA_CACHE[key] = true;  // unknown — don't flag
    }
    const sample = fc.features[0].properties;
    const cols = Object.keys(sample).filter(k => k === metricId || k.startsWith(metricId + "__"));
    if (!cols.length) return _METRIC_DATA_CACHE[key] = false;
    const hasAny = fc.features.some(f => cols.some(c => {
        const v = f.properties[c];
        return v != null && isFinite(+v);
    }));
    return _METRIC_DATA_CACHE[key] = hasAny;
}

function populateMetricSelect(searchTerm = "") {
    const sel = document.getElementById("metricSelect");
    const term = searchTerm.trim().toLowerCase();
    const matches = m =>
        m.levels.includes(state.level) &&
        (!term || m.label.toLowerCase().includes(term) || m.cat.toLowerCase().includes(term));
    const candidates = METRICS.filter(matches);
    const categories = [...new Set(candidates.map(m => m.cat))];
    sel.innerHTML = "";
    if (candidates.length === 0) {
        const opt = document.createElement("option");
        opt.textContent = `No metrics match "${searchTerm}"`;
        opt.disabled = true;
        sel.appendChild(opt);
        return;
    }
    categories.forEach(cat => {
        const grp = document.createElement("optgroup");
        grp.label = cat;
        candidates.filter(m => m.cat === cat).forEach(m => {
            const opt = document.createElement("option");
            opt.value = m.id;
            const hasData = metricHasData(m.id, state.level);
            opt.textContent = hasData ? m.label : `${m.label}  · (data refresh pending)`;
            if (!hasData) opt.style.color = "#9E9E9E";
            grp.appendChild(opt);
        });
        sel.appendChild(grp);
    });
    const availIds = candidates.map(m => m.id);
    if (!availIds.includes(state.metric)) state.metric = availIds[0];
    sel.value = state.metric;
    // Auto-pick a meaning-aware default palette (warm for "bad-when-high", cool
    // for "good-when-high", catalog default for neutral). User can still override.
    state.palette = semanticPalette(getMetric(state.metric));
    document.getElementById("paletteSelect").value = state.palette;
    updateMetricSummary();
}

function populatePaletteSelect() {
    const sel = document.getElementById("paletteSelect");
    sel.innerHTML = "";
    const seq = Object.keys(PALETTES).filter(n => PALETTES[n].type === "seq");
    const div = Object.keys(PALETTES).filter(n => PALETTES[n].type === "div");
    const grpSeq = document.createElement("optgroup");
    grpSeq.label = "Sequential";
    seq.forEach(n => {
        const o = document.createElement("option");
        o.value = n; o.textContent = n;
        grpSeq.appendChild(o);
    });
    sel.appendChild(grpSeq);
    const grpDiv = document.createElement("optgroup");
    grpDiv.label = "Diverging";
    div.forEach(n => {
        const o = document.createElement("option");
        o.value = n; o.textContent = n;
        grpDiv.appendChild(o);
    });
    sel.appendChild(grpDiv);
    sel.value = state.palette;
}

function updateMetricSummary() {
    const m = getMetric(state.metric);
    const values = GEO_DATA ? getValuesForLevel(state.level, state.metric) : [];
    const el = document.getElementById("metricSummary");
    if (!values.length) {
        el.innerHTML = `<em>No data for ${m.label} at this level.</em>`;
        return;
    }
    const min = Math.min(...values), max = Math.max(...values);
    const mean = values.reduce((a,b)=>a+b,0) / values.length;
    el.innerHTML = `
        <div class="summary-row"><span>Min</span><strong>${fmt(min, m.format)}</strong></div>
        <div class="summary-row"><span>Mean</span><strong>${fmt(mean, m.format)}</strong></div>
        <div class="summary-row"><span>Max</span><strong>${fmt(max, m.format)}</strong></div>
        <div class="summary-row"><span>N (with data)</span><strong>${values.length}</strong></div>
    `;
}

function wireUI() {
    populatePaletteSelect();
    populateMetricSelect();

    document.getElementById("levelSelect").addEventListener("change", e => {
        state.level = e.target.value;
        populateMetricSelect();
        applyChoropleth();
        updateLegend();
        if (state.level === "tract") {
            map.flyTo(VIEWS.lynn);
            setActiveView("lynn");
        }
    });
    document.getElementById("metricSelect").addEventListener("change", e => {
        state.metric = e.target.value;
        state.palette = semanticPalette(getMetric(state.metric));
        document.getElementById("paletteSelect").value = state.palette;
        applyChoropleth();
        updateLegend();
        updateMetricSummary();
    });
    document.getElementById("metricSearch").addEventListener("input", e => {
        populateMetricSelect(e.target.value);
        applyChoropleth();
        updateLegend();
    });
    // Year slider — live wired to year-keyed geojson columns.
    const yearSlider = document.getElementById("yearSlider");
    const yearLabel  = document.getElementById("yearLabel");
    if (yearSlider && yearLabel) {
        yearSlider.addEventListener("input", e => {
            state.year = parseInt(e.target.value, 10);
            yearLabel.textContent = e.target.value;
            // Stop animation if user manually drags
            if (state.playing) stopYearAnimation();
            applyChoropleth();
            updateLegend();
            updateMetricSummary();
        });
    }
    // Year animation (play / pause)
    const playBtn = document.getElementById("yearPlay");
    if (playBtn) {
        playBtn.addEventListener("click", () => {
            if (state.playing) stopYearAnimation();
            else startYearAnimation();
        });
    }
    // Student-group filter — repaints choropleth using metric__group column
    // when available, otherwise falls back to All Students (note shows why).
    const groupSelectEl = document.getElementById("groupSelect");
    if (groupSelectEl) {
        groupSelectEl.addEventListener("change", e => {
            state.studentGroup = e.target.value;
            applyChoropleth();
            updateLegend();
            updateMetricSummary();
            updateGroupNote();
        });
    }
    document.getElementById("paletteSelect").addEventListener("change", e => {
        state.palette = e.target.value;
        applyChoropleth();
        updateLegend();
    });
    document.querySelectorAll('input[name="classify"]').forEach(r => {
        r.addEventListener("change", e => {
            if (e.target.checked) {
                state.classify = e.target.value;
                applyChoropleth();
                updateLegend();
            }
        });
    });

    // Reference layer toggles
    const ref = {
        "ref-muni-outline":      ["muni-outline"],
        "ref-academic-outline":  ["academic-outline"],
        "ref-voctech-overlay":   ["voctech-fill", "voctech-outline"],
        "ref-charter-overlay":   ["charter-fill", "charter-outline"],
        "ref-lynn-schools":      ["schools-halo", "schools-lehs-ring", "schools-circles", "schools-labels"],
        "ref-all-ma-schools":    ["ma-schools-circles"],
        "ref-lynn-town":         ["lynn-highlight-fill", "lynn-highlight-line"],
        "ref-gateway-highlight": ["gateway-highlight-fill", "gateway-highlight-line"],
    };
    Object.entries(ref).forEach(([id, layers]) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.addEventListener("change", e => {
            layers.forEach(l => {
                if (map.getLayer(l))
                    map.setLayoutProperty(l, "visibility", e.target.checked ? "visible" : "none");
            });
        });
    });

    // Keep state.showLynnSchools + the size legend in sync with its toggle so the
    // zoom-recompute guard and a freshly-re-enabled legend behave correctly.
    const schoolsToggle = document.getElementById("ref-lynn-schools");
    if (schoolsToggle) {
        schoolsToggle.addEventListener("change", e => {
            state.showLynnSchools = e.target.checked;
            if (e.target.checked) renderSchoolSizeLegend();
        });
    }

    // 3D extrusion
    document.getElementById("toggle-3d").addEventListener("change", e => {
        state.extrude3d = e.target.checked;
        toggle3D();
    });

    // School labels
    document.getElementById("toggle-labels").addEventListener("change", e => {
        if (map.getLayer("schools-labels"))
            map.setLayoutProperty("schools-labels", "visibility", e.target.checked ? "visible" : "none");
    });
    document.getElementById("toggle-town-labels").addEventListener("change", e => {
        if (map.getLayer("town-labels"))
            map.setLayoutProperty("town-labels", "visibility", e.target.checked ? "visible" : "none");
    });

    // ── SCHOOL COLOR-MODE control (the centerpiece) ──────────────────────────
    // A single dropdown drives the dot color: by Type, by a demographic, or the
    // Lynn-English focus view. Repaints dots + swaps the color legend.
    const schoolColorSel = document.getElementById("schoolColorMode");
    if (schoolColorSel) {
        schoolColorSel.value = state.schoolColorMode;
        schoolColorSel.addEventListener("change", e => {
            state.schoolColorMode = e.target.value;
            applySchoolColorMode();
        });
    }
    // Size legend recomputes on zoom so the key dots always match the map dots.
    map.on("zoom", () => {
        if (state.showLynnSchools) renderSchoolSizeLegend();
    });
    // Initial paint of both school legends.
    renderSchoolSizeLegend();
    renderSchoolColorLegend();

    // Quick views
    document.querySelectorAll(".view-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            setActiveView(btn.dataset.view);
            const v = VIEWS[btn.dataset.view];
            if (v) map.flyTo({ ...v, duration: 1200, essential: true });
        });
    });

    // Panel open/close — desktop uses .collapsed slide-out, mobile uses
    // .open slide-in drawer with backdrop
    const panel    = document.getElementById("controlPanel");
    const fab      = document.getElementById("panelFab");
    const toggle   = document.getElementById("panelToggle");
    const backdrop = document.getElementById("panelBackdrop");
    const isMobile = () => window.matchMedia("(max-width: 768px)").matches;

    function openPanel() {
        panel.classList.add("open");
        panel.classList.remove("collapsed");
        if (backdrop) backdrop.classList.add("open");
    }
    function closePanel() {
        panel.classList.remove("open");
        if (isMobile()) panel.classList.add("collapsed");
        if (backdrop) backdrop.classList.remove("open");
    }
    function togglePanel() {
        if (isMobile()) {
            (panel.classList.contains("open") ? closePanel : openPanel)();
        } else {
            panel.classList.toggle("collapsed");
        }
    }

    if (toggle)   toggle.addEventListener("click", togglePanel);
    if (fab)      fab.addEventListener("click", togglePanel);
    if (backdrop) backdrop.addEventListener("click", closePanel);

    document.querySelectorAll(".view-btn").forEach(b => {
        b.addEventListener("click", () => { if (isMobile()) closePanel(); });
    });

    // Theme (dark / light) toggle — sync its initial state, then wire the click.
    syncThemeButton();
    const themeBtn = document.getElementById("themeToggle");
    if (themeBtn) themeBtn.addEventListener("click", toggleTheme);

    // Reset metric, level, view, theme, school color mode & reference toggles.
    const resetBtn = document.getElementById("resetAllBtn");
    if (resetBtn) resetBtn.addEventListener("click", resetAll);

    // Legend drag-to-move + resize controls (desktop).
    setupLegendCustomization();
}

function setActiveView(view) {
    document.querySelectorAll(".view-btn").forEach(b => b.classList.remove("active"));
    const el = document.querySelector(`.view-btn[data-view="${view}"]`);
    if (el) el.classList.add("active");
}

const VIEWS = {
    lynn:          { center: [-70.95, 42.47], zoom: 11.8, pitch: 0, bearing: 0 },
    ma:            { center: [-71.7, 42.25],  zoom: 7.5,  pitch: 0, bearing: 0 },
    "north-shore": { center: [-70.9, 42.55],  zoom: 9.3,  pitch: 0, bearing: 0 },
};

// ─── RESET ALL ───────────────────────────────────────────────────────────────
// Restore the landing defaults: metric, level, classification, student group,
// year, school color mode, reference-layer toggles, visual mode, theme, and the
// view. Mirrors the initial `state` object + the HTML's default-checked inputs.
const REF_TOGGLE_DEFAULTS = {
    "ref-muni-outline":      true,
    "ref-academic-outline":  false,
    "ref-voctech-overlay":   false,
    "ref-charter-overlay":   false,
    "ref-lynn-schools":      true,
    "ref-all-ma-schools":    false,
    "ref-lynn-town":         true,
    "ref-gateway-highlight": true,
};
const REF_TOGGLE_LAYERS = {
    "ref-muni-outline":      ["muni-outline"],
    "ref-academic-outline":  ["academic-outline"],
    "ref-voctech-overlay":   ["voctech-fill", "voctech-outline"],
    "ref-charter-overlay":   ["charter-fill", "charter-outline"],
    "ref-lynn-schools":      ["schools-halo", "schools-lehs-ring", "schools-circles", "schools-labels"],
    "ref-all-ma-schools":    ["ma-schools-circles"],
    "ref-lynn-town":         ["lynn-highlight-fill", "lynn-highlight-line"],
    "ref-gateway-highlight": ["gateway-highlight-fill", "gateway-highlight-line"],
};
function resetAll() {
    if (state.playing) stopYearAnimation();
    // Core data view → landing defaults.
    state.level = "muni";
    state.metric = "EL_PCT";
    state.classify = "jenks";
    state.studentGroup = "all";
    state.year = 2026;
    state.extrude3d = false;
    state.labels = true;
    state.townLabels = true;
    state.schoolColorMode = "type";
    // Reflect the simple selects/radios.
    const levelSel = document.getElementById("levelSelect"); if (levelSel) levelSel.value = state.level;
    const grpSel   = document.getElementById("groupSelect"); if (grpSel) grpSel.value = "all";
    const search   = document.getElementById("metricSearch"); if (search) search.value = "";
    const yearSl   = document.getElementById("yearSlider"); if (yearSl) yearSl.value = String(state.year);
    const yearLb   = document.getElementById("yearLabel");  if (yearLb) yearLb.textContent = String(state.year);
    document.querySelectorAll('input[name="classify"]').forEach(r => { r.checked = (r.value === "jenks"); });
    const t3d = document.getElementById("toggle-3d");          if (t3d) t3d.checked = false;
    const tl  = document.getElementById("toggle-labels");      if (tl) tl.checked = true;
    const ttl = document.getElementById("toggle-town-labels"); if (ttl) ttl.checked = true;
    const scm = document.getElementById("schoolColorMode");    if (scm) scm.value = "type";
    // Reference layers → defaults (state flags + checkboxes + layer visibility).
    state.showMuniOutline = true; state.showAcademicOutline = false;
    state.showVoctechOverlay = false; state.showCharterOverlay = false;
    state.showLynnSchools = true; state.showAllMaSchools = false;
    state.showLynnTown = true; state.showGatewayHighlight = true;
    Object.entries(REF_TOGGLE_DEFAULTS).forEach(([id, on]) => {
        const el = document.getElementById(id); if (el) el.checked = on;
        (REF_TOGGLE_LAYERS[id] || []).forEach(l => {
            if (map.getLayer(l)) map.setLayoutProperty(l, "visibility", on ? "visible" : "none");
        });
    });
    // 3D off (also flattens pitch); labels back on.
    toggle3D();
    if (map.getLayer("schools-labels")) map.setLayoutProperty("schools-labels", "visibility", "visible");
    if (map.getLayer("town-labels"))    map.setLayoutProperty("town-labels", "visibility", "visible");
    // Theme → light (landing default).
    if (currentTheme() !== "light") applyTheme("light");
    // Rebuild the metric list for the muni level, repaint, refresh legends.
    populateMetricSelect();              // resets palette via semanticPalette + select value
    applySchoolColorMode();
    applyChoropleth();
    updateLegend();
    updateMetricSummary();
    updateGroupNote();
    renderSchoolSizeLegend();
    setActiveView("lynn");
    map.flyTo({ ...VIEWS.lynn, duration: 1000, essential: true });
}

// ─── LEGEND CUSTOMIZATION (drag to move + resize, persisted) ─────────────────
// The legend header doubles as a drag handle; the −/+ buttons + corner grip
// resize it (--legend-scale); ⟲ resets. Position & size persist to localStorage.
// Desktop-only (the legend docks full-width on mobile). Adapted from the atlas's
// setupLegendCustomization(); pointer events + on-screen clamping unchanged.
const LEGEND_LS_KEY      = "lynn-maps-legend";
const LEGEND_MIN_SCALE   = 0.7;
const LEGEND_MAX_SCALE   = 1.8;
const LEGEND_EDGE        = 8;     // min gap (px) between the card and the map edge
const LEGEND_DESKTOP_MIN = 769;  // matches the app's 768px mobile breakpoint
function setupLegendCustomization() {
    const legend = document.getElementById("legend");
    const header = document.getElementById("legendHeader");
    const grip   = document.getElementById("legendResize");
    const main   = document.querySelector(".maps-main");
    if (!legend || !header || !main) return;

    const st = { custom: false, left: 0, top: 0, scale: 1 };
    const isDesktop  = () => window.innerWidth >= LEGEND_DESKTOP_MIN;
    const clampScale = s => Math.min(LEGEND_MAX_SCALE, Math.max(LEGEND_MIN_SCALE, s));

    function save() {
        try {
            localStorage.setItem(LEGEND_LS_KEY, JSON.stringify({
                left: Math.round(st.left), top: Math.round(st.top), scale: st.scale,
            }));
        } catch (e) {}
    }

    // Seed left/top from the card's current spot, then hand positioning to JS.
    function detach() {
        if (st.custom) return;
        const lr = legend.getBoundingClientRect();
        const mr = main.getBoundingClientRect();
        st.left = lr.left - mr.left;
        st.top  = lr.top  - mr.top;
        st.custom = true;
    }

    // Write scale + position, then clamp using the rendered (scaled) box so the
    // card can never be pushed off the map.
    function place() {
        if (!st.custom) return;
        legend.style.right  = "auto";
        legend.style.bottom = "auto";
        legend.style.setProperty("--legend-scale", String(st.scale));
        legend.style.left = st.left + "px";
        legend.style.top  = st.top  + "px";
        const mr = main.getBoundingClientRect();
        const lr = legend.getBoundingClientRect();   // scaled box (transform applied)
        const maxLeft = Math.max(LEGEND_EDGE, mr.width  - lr.width  - LEGEND_EDGE);
        const maxTop  = Math.max(LEGEND_EDGE, mr.height - lr.height - LEGEND_EDGE);
        st.left = Math.min(Math.max(LEGEND_EDGE, st.left), maxLeft);
        st.top  = Math.min(Math.max(LEGEND_EDGE, st.top),  maxTop);
        legend.style.left = st.left + "px";
        legend.style.top  = st.top  + "px";
    }

    // Restore default CSS anchoring (bottom-right) and forget the saved layout.
    function reset() {
        st.custom = false; st.left = 0; st.top = 0; st.scale = 1;
        legend.style.removeProperty("--legend-scale");
        legend.style.left = legend.style.top = legend.style.right = legend.style.bottom = "";
        try { localStorage.removeItem(LEGEND_LS_KEY); } catch (e) {}
    }

    function bump(delta) {
        if (!isDesktop()) return;
        detach();
        st.scale = clampScale(+(st.scale + delta).toFixed(2));
        place();
        save();
    }

    // ── Pointer drag: move (grab the header) ─────────────────────────────────
    let drag = null;
    header.addEventListener("pointerdown", e => {
        if (!isDesktop() || (e.button !== undefined && e.button !== 0)) return;
        if (e.target.closest(".legend-tool")) return;   // clicks on −/+/⟲ aren't drags
        detach();
        drag = { x: e.clientX, y: e.clientY, l: st.left, t: st.top };
        try { header.setPointerCapture(e.pointerId); } catch (_) {}
        document.body.classList.add("legend-busy");
        document.body.style.cursor = "move";
        e.preventDefault();
    });
    header.addEventListener("pointermove", e => {
        if (!drag) return;
        st.left = drag.l + (e.clientX - drag.x);
        st.top  = drag.t + (e.clientY - drag.y);
        place();
    });
    function endDrag(e) {
        if (!drag) return;
        drag = null;
        try { header.releasePointerCapture(e.pointerId); } catch (_) {}
        document.body.classList.remove("legend-busy");
        document.body.style.cursor = "";
        save();
    }
    header.addEventListener("pointerup", endDrag);
    header.addEventListener("pointercancel", endDrag);

    // Keyboard nudge while the header is focused (arrows = 10px, Shift = 1px).
    header.addEventListener("keydown", e => {
        if (!isDesktop()) return;
        const step = e.shiftKey ? 1 : 10;
        let dx = 0, dy = 0;
        if      (e.key === "ArrowLeft")  dx = -step;
        else if (e.key === "ArrowRight") dx =  step;
        else if (e.key === "ArrowUp")    dy = -step;
        else if (e.key === "ArrowDown")  dy =  step;
        else return;
        e.preventDefault();
        detach();
        st.left += dx; st.top += dy;
        place();
        save();
    });

    // ── Pointer drag: resize (corner grip) ───────────────────────────────────
    let rez = null;
    if (grip) {
        grip.addEventListener("pointerdown", e => {
            if (!isDesktop() || (e.button !== undefined && e.button !== 0)) return;
            detach();
            const lr = legend.getBoundingClientRect();
            rez = { x: e.clientX, y: e.clientY, s: st.scale, w: lr.width };
            try { grip.setPointerCapture(e.pointerId); } catch (_) {}
            document.body.classList.add("legend-busy");
            document.body.style.cursor = "nwse-resize";
            e.preventDefault();
            e.stopPropagation();
        });
        grip.addEventListener("pointermove", e => {
            if (!rez) return;
            // Average of horizontal + vertical drag drives a uniform scale.
            const d = ((e.clientX - rez.x) + (e.clientY - rez.y)) / 2;
            st.scale = clampScale(rez.s * ((rez.w + d) / rez.w));
            place();
        });
        const endRez = e => {
            if (!rez) return;
            rez = null;
            try { grip.releasePointerCapture(e.pointerId); } catch (_) {}
            document.body.classList.remove("legend-busy");
            document.body.style.cursor = "";
            save();
        };
        grip.addEventListener("pointerup", endRez);
        grip.addEventListener("pointercancel", endRez);
    }

    // ── Buttons: −/+ scale, ⟲ reset ──────────────────────────────────────────
    const smaller  = document.getElementById("legendSmaller");
    const larger   = document.getElementById("legendLarger");
    const resetBtn = document.getElementById("legendReset");
    if (smaller)  smaller.addEventListener("click",  () => bump(-0.1));
    if (larger)   larger.addEventListener("click",   () => bump(+0.1));
    if (resetBtn) resetBtn.addEventListener("click", reset);

    // Re-clamp on viewport change; hand back to the docked CSS when narrow.
    let rzTimer;
    window.addEventListener("resize", () => {
        clearTimeout(rzTimer);
        rzTimer = setTimeout(() => {
            if (!st.custom) return;
            if (isDesktop()) {
                place();
            } else {
                legend.style.removeProperty("--legend-scale");
                legend.style.left = legend.style.top = legend.style.right = legend.style.bottom = "";
            }
        }, 150);
    });

    // Let updateLegend() re-clamp after a content (height) change.
    _legendClamp = () => { if (st.custom && isDesktop()) place(); };

    // Restore a saved layout (desktop only); clamp absorbs viewport differences.
    try {
        const saved = JSON.parse(localStorage.getItem(LEGEND_LS_KEY) || "null");
        if (saved && isDesktop()) {
            detach();
            if (typeof saved.left  === "number") st.left  = saved.left;
            if (typeof saved.top   === "number") st.top   = saved.top;
            if (typeof saved.scale === "number") st.scale = clampScale(saved.scale);
            place();
        }
    } catch (e) {}
}

// 3D extrusion — replaces the flat choropleth fill with extruded polygons
function toggle3D() {
    const { level, metric } = state;
    const m = getMetric(metric);
    const flatLayer = { muni: "muni-fill", district: "district-fill", tract: "tract-fill" }[level];
    const extrudeLayerId = `${level}-3d`;
    const sourceId = { muni: "municipalities", district: "districts", tract: "tracts" }[level];

    // Remove any prior 3D layers
    ["muni-3d","district-3d","tract-3d"].forEach(id => {
        if (map.getLayer(id)) map.removeLayer(id);
    });

    if (!state.extrude3d) {
        map.setLayoutProperty(flatLayer, "visibility", "visible");
        map.easeTo({ pitch: 0, bearing: 0, duration: 800 });
        return;
    }

    // Build height expression — values × scalar; for $ scale by 0.05 (so $30k = 1500m)
    const heightScalar = m.format === "usd" ? 0.05 : 8000;
    const col = activeColumn(metric, state.year, level);
    const paint = paintExpression(col, state.palette, state.classify, level);
    const layerCfg = {
        id: extrudeLayerId, type: "fill-extrusion", source: sourceId,
        paint: {
            "fill-extrusion-color": paint,
            "fill-extrusion-height": [
                "case",
                ["==", ["typeof", ["get", col]], "number"],
                ["*", ["to-number", ["get", col]], heightScalar],
                0,
            ],
            "fill-extrusion-opacity": 0.85,
            "fill-extrusion-base": 0,
        },
    };
    if (level === "district") layerCfg.filter = ["==", ["get", "TYPE"], "Operating District"];
    map.addLayer(layerCfg);
    map.setLayoutProperty(flatLayer, "visibility", "none");
    map.easeTo({ pitch: 55, bearing: -20, duration: 900 });
}

// ─── CSV EXPORT ──────────────────────────────────────────────────────────────
function _csvEscape(v) {
    if (v === null || v === undefined) return "";
    const s = String(v);
    if (/[",\n]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
    return s;
}

function featuresToCsv(features, primaryMetric) {
    if (!features || !features.length) return "";
    const idCols = ["DIST_CODE", "DIST_NAME", "dist_display",
                     "ORG8CODE", "ORG_NAME", "TOWN", "town_display",
                     "GEOID", "NAMELSAD", "TYPE", "NAME"];
    const seen = new Set();
    const cols = [];
    idCols.forEach(c => {
        if (features[0].properties && c in features[0].properties && !seen.has(c)) {
            cols.push(c); seen.add(c);
        }
    });
    if (primaryMetric && !seen.has(primaryMetric)) {
        cols.push(primaryMetric); seen.add(primaryMetric);
    }
    const otherKeys = new Set();
    features.forEach(f => {
        if (!f.properties) return;
        Object.keys(f.properties).forEach(k => { if (!seen.has(k)) otherKeys.add(k); });
    });
    [...otherKeys].sort().forEach(k => { cols.push(k); seen.add(k); });
    const lines = [cols.join(",")];
    features.forEach(f => {
        const p = f.properties || {};
        lines.push(cols.map(c => _csvEscape(p[c])).join(","));
    });
    return lines.join("\n");
}

function downloadCurrentLayerCsv() {
    if (typeof GEO_DATA !== "object" || !GEO_DATA) return;
    const lvl = state.level;
    const fc = GEO_DATA[lvl];
    if (!fc || !fc.features || !fc.features.length) return;
    const metricCol = (typeof activeColumn === "function")
        ? activeColumn(state.metric, state.year, lvl)
        : state.metric;
    const csv = featuresToCsv(fc.features, metricCol);
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `lynn-map_${lvl}_${state.metric}.csv`;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1500);
}

document.addEventListener("DOMContentLoaded", function () {
    const btn = document.getElementById("exportCsvBtn");
    if (btn) btn.addEventListener("click", downloadCurrentLayerCsv);
});
