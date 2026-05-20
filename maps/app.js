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

    // Academic
    { id:"mcas_g10_ela_me",  label:"MCAS Gr10 ELA % M+E",   cat:"Academic", levels:["district","muni"], palette:"Viridis", format:"pct" },
    { id:"mcas_g10_math_me", label:"MCAS Gr10 Math % M+E",  cat:"Academic", levels:["district","muni"], palette:"Viridis", format:"pct" },
    { id:"mcas_g10_sci_me",  label:"MCAS Gr10 STE % M+E",   cat:"Academic", levels:["district","muni"], palette:"Viridis", format:"pct" },
    { id:"mcas_g38_ela_me",  label:"MCAS Gr3-8 ELA % M+E",  cat:"Academic", levels:["district","muni"], palette:"Viridis", format:"pct" },
    { id:"mcas_g38_math_me", label:"MCAS Gr3-8 Math % M+E", cat:"Academic", levels:["district","muni"], palette:"Viridis", format:"pct" },

    // Outcomes
    { id:"grad_4yr",            label:"4-yr Graduation Rate",        cat:"Outcomes", levels:["district","muni"], palette:"Viridis", format:"pct" },
    { id:"grad_5yr",            label:"5-yr Graduation Rate",        cat:"Outcomes", levels:["district","muni"], palette:"Viridis", format:"pct" },
    { id:"dropout_pct",         label:"Dropout Rate",                cat:"Outcomes", levels:["district","muni"], palette:"Reds",    format:"pct" },
    { id:"chronic_absent_pct",  label:"Chronic Absenteeism Rate",    cat:"Outcomes", levels:["district","muni"], palette:"Reds",    format:"pct" },
    { id:"attendance_rate",     label:"Attendance Rate",             cat:"Outcomes", levels:["district","muni"], palette:"Greens",  format:"pct" },
    { id:"masscore_pct",        label:"MassCore Completion",         cat:"Outcomes", levels:["district","muni"], palette:"Greens",  format:"pct" },
    { id:"ap_pct_3plus",        label:"% AP Tests Scoring 3+",       cat:"Outcomes", levels:["district","muni"], palette:"BuPu",    format:"pct" },

    // Postsecondary plans
    { id:"pct_any_college",     label:"% Planning Any College",      cat:"Postsecondary", levels:["district","muni"], palette:"Viridis", format:"pct" },
    { id:"pct_4yr_college",     label:"% Planning 4-yr College",     cat:"Postsecondary", levels:["district","muni"], palette:"Viridis", format:"pct" },
    { id:"pct_2yr_college",     label:"% Planning 2-yr College",     cat:"Postsecondary", levels:["district","muni"], palette:"BuPu",    format:"pct" },
    { id:"pct_work_after_hs",   label:"% Planning to Work after HS", cat:"Postsecondary", levels:["district","muni"], palette:"Oranges", format:"pct" },
    { id:"pct_military",        label:"% Planning Military",         cat:"Postsecondary", levels:["district","muni"], palette:"Greys",   format:"pct" },

    // Finance
    { id:"per_pupil",                  label:"Per-Pupil $ (Total)",         cat:"Finance", levels:["district","muni"], palette:"Viridis", format:"usd" },
    { id:"per_pupil_teachers",         label:"Per-Pupil $ — Teachers",      cat:"Finance", levels:["district","muni"], palette:"Viridis", format:"usd" },
    { id:"per_pupil_admin",            label:"Per-Pupil $ — Administration",cat:"Finance", levels:["district","muni"], palette:"Viridis", format:"usd" },
    { id:"per_pupil_pupil_services",   label:"Per-Pupil $ — Pupil Services",cat:"Finance", levels:["district","muni"], palette:"Viridis", format:"usd" },

    // Workforce
    { id:"staff_white_pct",        label:"% Staff: White",            cat:"Workforce", levels:["district","muni"], palette:"Greys",   format:"pct" },
    { id:"staff_hispanic_pct",     label:"% Staff: Hispanic",         cat:"Workforce", levels:["district","muni"], palette:"Oranges", format:"pct" },
    { id:"staff_black_pct",        label:"% Staff: Black",            cat:"Workforce", levels:["district","muni"], palette:"Purples", format:"pct" },
    { id:"stu_tchr_ratio",         label:"Student : Teacher Ratio",   cat:"Workforce", levels:["district","muni"], palette:"Reds",    format:"num" },
    { id:"teacher_experienced_pct",label:"% Experienced Teachers",    cat:"Workforce", levels:["district","muni"], palette:"Greens",  format:"pct" },
    { id:"teacher_infield_pct",    label:"% Teachers In-Field",       cat:"Workforce", levels:["district","muni"], palette:"Greens",  format:"pct" },
    { id:"teacher_retention_pct",  label:"Teacher Retention Rate",    cat:"Workforce", levels:["district","muni"], palette:"Greens",  format:"pct" },

    // Tract — ACS (Lynn only)
    { id:"non_english_pct",          label:"% non-English at home",      cat:"Tract — Census ACS", levels:["tract"], palette:"Greens",  format:"pct" },
    { id:"median_household_income",  label:"Median Household Income",    cat:"Tract — Census ACS", levels:["tract"], palette:"Viridis", format:"usd" },
    { id:"foreign_born_pct",         label:"% Foreign-born",             cat:"Tract — Census ACS", levels:["tract"], palette:"Purples", format:"pct" },
    { id:"bachelors_or_higher_pct",  label:"% Bachelor's or higher",     cat:"Tract — Census ACS", levels:["tract"], palette:"Blues",   format:"pct" },
    { id:"severe_burden_pct",        label:"% Severely Rent-Burdened",   cat:"Tract — Census ACS", levels:["tract"], palette:"Reds",    format:"pct" },
];

// ─── STATE ───────────────────────────────────────────────────────────────────
const state = {
    level: "tract",                    // Lynn-focused → start at the tract level
    metric: "non_english_pct",         // ACS linguistic landscape: Lynn's defining demographic story
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
    showLynnTown: true,
    showGatewayHighlight: true,
    studentGroup: "all",
    year: 2026,
    playing: false,
};

let GEO_DATA = null;  // populated after load

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

// ─── MAP INITIALIZATION ──────────────────────────────────────────────────────
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
map.addControl(new maplibregl.AttributionControl({
    compact: true,
    customAttribution: '<a href="https://maxwellhowegis.com" target="_blank">© Maxwell Howe</a> · MA DESE · US Census · MassGIS',
}), "bottom-right");
map.addControl(new maplibregl.ScaleControl({ maxWidth: 120, unit: "imperial" }), "bottom-left");

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

        addLayers();
        wireUI();
        applyChoropleth();
        updateLegend();
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
    map.addLayer({
        id: "muni-fill", type: "fill", source: "municipalities",
        paint: {
            "fill-color": NO_DATA_COLOR,
            "fill-opacity": [
                "case",
                ["boolean", ["feature-state", "hover"], false], 0.92,
                0.78
            ],
        },
        layout: { visibility: state.level === "muni" ? "visible" : "none" },
    });
    map.addLayer({
        id: "district-fill", type: "fill", source: "districts",
        paint: {
            "fill-color": NO_DATA_COLOR,
            "fill-opacity": [
                "case",
                ["boolean", ["feature-state", "hover"], false], 0.92,
                0.78
            ],
        },
        layout: { visibility: state.level === "district" ? "visible" : "none" },
    });
    map.addLayer({
        id: "tract-fill", type: "fill", source: "tracts",
        paint: {
            "fill-color": NO_DATA_COLOR,
            "fill-opacity": [
                "case",
                ["boolean", ["feature-state", "hover"], false], 0.92,
                0.78
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

    // ── LYNN SCHOOLS (point markers + labels) ────────────────────────────────
    map.addLayer({
        id: "schools-circles", type: "circle", source: "schools",
        paint: {
            "circle-radius": [
                "interpolate", ["linear"], ["coalesce", ["get", "TOTAL_CNT"], 250],
                100, 4, 500, 7, 1000, 11, 2000, 16,
            ],
            "circle-color": [
                "case",
                ["==", ["get", "ORG_CODE"], "01630510"], "#FFB81C",
                "#0A1F44",
            ],
            "circle-stroke-color": "#ffffff",
            "circle-stroke-width": 2,
            "circle-opacity": 0.95,
        },
        layout: { visibility: state.showLynnSchools ? "visible" : "none" },
    });
    map.addLayer({
        id: "schools-labels", type: "symbol", source: "schools",
        layout: {
            "text-field": ["get", "NAME"],
            "text-font": ["Noto Sans Regular"],
            "text-size": 10,
            "text-anchor": "top",
            "text-offset": [0, 1.1],
            "text-optional": true,
            "visibility": state.labels ? "visible" : "none",
        },
        paint: {
            "text-color": "#0A1F44",
            "text-halo-color": "#ffffff",
            "text-halo-width": 1.5,
        },
        minzoom: 13,
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

function buildPanelHtml(p, kind) {
    if (kind === "school") {
        const isLehs = p.ORG_CODE === "01630510";
        return `
            ${isLehs ? '<div class="feature-panel-tag">Focus school</div>' : ""}
            <div class="feature-panel-section">
                <div class="feature-panel-row"><span class="label">Type</span><span class="value">${p.TYPE_DESC || "—"}</span></div>
                <div class="feature-panel-row"><span class="label">Grades</span><span class="value">${p.GRADES || "—"}</span></div>
                ${fpRow("Enrollment", p.TOTAL_CNT, "num")}
            </div>
            ${fpSection("Student composition", [
                fpRow("% English Learner", p.EL_PCT, "pct"),
                fpRow("% Low Income", p.LI_PCT, "pct"),
                fpRow("% High Needs", p.HN_PCT, "pct"),
                fpRow("% Hispanic/Latino", p.HL_PCT, "pct"),
                fpRow("% Black/African Am.", p.BAA_PCT, "pct"),
                fpRow("% Asian", p.AS_PCT, "pct"),
                fpRow("% White", p.WH_PCT, "pct"),
                fpRow("% SPED", p.SWD_PCT, "pct"),
            ].join(""))}
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
        stopsEl.innerHTML = '<div class="legend-row" style="color:#90A4AE;">No data at this level for this metric.</div>';
        metaEl.innerHTML = `<span class="legend-null"><span class="legend-null-swatch"></span>No data — ${nullCount.toLocaleString()} of ${totalFeatures.toLocaleString()}</span>`;
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
}

// ─── UI WIRING ───────────────────────────────────────────────────────────────
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
            opt.textContent = m.label;
            grp.appendChild(opt);
        });
        sel.appendChild(grp);
    });
    const availIds = candidates.map(m => m.id);
    if (!availIds.includes(state.metric)) state.metric = availIds[0];
    sel.value = state.metric;
    state.palette = getMetric(state.metric).palette;
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
        state.palette = getMetric(state.metric).palette;
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
        "ref-lynn-schools":      ["schools-circles", "schools-labels"],
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
