/* ============================================================================
   Lynn Data Dive — Interactive Maps
   MapLibre GL JS · OpenFreeMap vector tiles · MassGIS polygons · MA DESE data

   Architecture:
     - Always-on reference layers (muni borders, district borders, town labels)
     - One configurable CHOROPLETH layer (target = muni | district | tract)
     - 35+ metrics across demographics, academic, outcomes, finance, workforce
     - 12 color palettes (ColorBrewer-style sequential + diverging)
     - 3 classification methods: continuous / 5 quantiles / 5 equal-interval
     - Click any polygon for an info popup
   ============================================================================ */

// ─── DATA SOURCES (same-origin, slim simplified GeoJSON) ─────────────────────
const SOURCES = {
    tracts:        "data/lynn_tracts.geojson",
    schools:       "data/lynn_schools.geojson",
    town:          "data/lynn_town.geojson",
    districts:     "data/ma_districts_metrics.geojson",
    municipalities:"data/ma_municipalities.geojson",
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
    { id:"grad_4yr",            label:"4-yr Graduation Rate",   cat:"Outcomes", levels:["district","muni"], palette:"Viridis", format:"pct" },
    { id:"grad_5yr",            label:"5-yr Graduation Rate",   cat:"Outcomes", levels:["district","muni"], palette:"Viridis", format:"pct" },
    { id:"dropout_pct",         label:"Dropout Rate",           cat:"Outcomes", levels:["district","muni"], palette:"Reds",    format:"pct" },
    { id:"chronic_absent_pct",  label:"Chronic Absenteeism Rate", cat:"Outcomes", levels:["district","muni"], palette:"Reds",    format:"pct" },
    { id:"masscore_pct",        label:"MassCore Completion",    cat:"Outcomes", levels:["district","muni"], palette:"Greens",  format:"pct" },
    { id:"ap_pct_3plus",        label:"% AP Tests Scoring 3+",  cat:"Outcomes", levels:["district","muni"], palette:"BuPu",    format:"pct" },

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
    level: "muni",
    metric: "EL_PCT",
    palette: "Greens",
    classify: "continuous",
    extrude3d: false,
    labels: true,
    townLabels: true,
    showMuniOutline: true,
    showDistrictOutline: false,
    showLynnSchools: true,
    showLynnTown: true,
    showGatewayHighlight: true,
};

let GEO_DATA = null;  // populated after load

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
    return fc.features.map(f => f.properties[metricId])
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

function paintExpression(metricId, paletteName, classify, level) {
    const colors = PALETTES[paletteName].colors;
    const values = getValuesForLevel(level, metricId);

    const fallback = "#e0e0e0";
    const valid = ["case",
        ["==", ["typeof", ["get", metricId]], "number"], true,
        false
    ];

    if (classify === "continuous") {
        // Linear interp across full data range
        if (values.length < 2) return ["case", valid, colors[colors.length - 1], fallback];
        const min = Math.min(...values);
        const max = Math.max(...values);
        const stops = sampleColors(colors, 5);
        const expr = ["interpolate", ["linear"], ["to-number", ["get", metricId]]];
        for (let i = 0; i < stops.length; i++) {
            expr.push(min + (max - min) * i / (stops.length - 1), stops[i]);
        }
        return ["case", valid, expr, fallback];
    }

    // Stepped
    const breaks = classify === "quantile"
        ? quantileBreaks(values, 5)
        : equalIntervalBreaks(values, 5);
    const stops = sampleColors(colors, 5);
    const expr = ["step", ["to-number", ["get", metricId]], stops[0]];
    breaks.forEach((b, i) => { expr.push(b, stops[i + 1]); });
    return ["case", valid, expr, fallback];
}

// ─── MAP INITIALIZATION ──────────────────────────────────────────────────────
const map = new maplibregl.Map({
    container: "map",
    style: "https://tiles.openfreemap.org/styles/positron",
    center: [-70.95, 42.47],
    zoom: 11.6,
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
        const [tracts, schools, town, districts, munis] = await Promise.all([
            fetch(SOURCES.tracts).then(r => r.json()),
            fetch(SOURCES.schools).then(r => r.json()),
            fetch(SOURCES.town).then(r => r.json()),
            fetch(SOURCES.districts).then(r => r.json()),
            fetch(SOURCES.municipalities).then(r => r.json()),
        ]);
        GEO_DATA = { tract: tracts, district: districts, muni: munis };

        map.addSource("tracts", { type: "geojson", data: tracts });
        map.addSource("schools", { type: "geojson", data: schools });
        map.addSource("town", { type: "geojson", data: town });
        map.addSource("districts", { type: "geojson", data: districts });
        map.addSource("municipalities", { type: "geojson", data: munis });
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
    // Municipality choropleth fill
    map.addLayer({
        id: "muni-fill", type: "fill", source: "municipalities",
        paint: { "fill-color": "#e0e0e0", "fill-opacity": 0.7 },
        layout: { visibility: state.level === "muni" ? "visible" : "none" },
    });
    // District choropleth fill (only Operating Districts)
    map.addLayer({
        id: "district-fill", type: "fill", source: "districts",
        filter: ["==", ["get", "TYPE"], "Operating District"],
        paint: { "fill-color": "#e0e0e0", "fill-opacity": 0.7 },
        layout: { visibility: state.level === "district" ? "visible" : "none" },
    });
    // Tract choropleth fill (Lynn only)
    map.addLayer({
        id: "tract-fill", type: "fill", source: "tracts",
        paint: { "fill-color": "#e0e0e0", "fill-opacity": 0.7 },
        layout: { visibility: state.level === "tract" ? "visible" : "none" },
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
    // District borders (toggleable, slightly thicker / different color)
    map.addLayer({
        id: "district-outline", type: "line", source: "districts",
        filter: ["==", ["get", "TYPE"], "Operating District"],
        paint: {
            "line-color": "#1a3a6b",
            "line-width": 1.3,
            "line-opacity": 0.65,
            "line-dasharray": [3, 1.5],
        },
        layout: { visibility: state.showDistrictOutline ? "visible" : "none" },
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
    ["muni-fill", "district-fill", "tract-fill", "schools-circles"].forEach(id => {
        map.on("mouseenter", id, () => map.getCanvas().style.cursor = "pointer");
        map.on("mouseleave", id, () => map.getCanvas().style.cursor = "");
    });
}

// ─── POPUPS ──────────────────────────────────────────────────────────────────
function showPopup(e, kind) {
    if (!e.features.length) return;
    const p = e.features[0].properties;
    new maplibregl.Popup({ closeButton: true, maxWidth: "340px" })
        .setLngLat(e.lngLat)
        .setHTML(buildPopupHtml(p, kind))
        .addTo(map);
}

function row(label, value, kind = "num") {
    return `<div class="popup-row"><span class="label">${label}</span><span class="value">${fmt(+value, kind)}</span></div>`;
}

function buildPopupHtml(p, kind) {
    if (kind === "school") {
        const isLehs = p.ORG_CODE === "01630510";
        return `
            ${isLehs ? '<div class="popup-tag">FOCUS SCHOOL</div>' : ""}
            <div class="popup-title">${p.NAME}</div>
            <div class="popup-row"><span class="label">Type</span><span class="value">${p.TYPE_DESC || "—"}</span></div>
            <div class="popup-row"><span class="label">Grades</span><span class="value">${p.GRADES || "—"}</span></div>
            ${row("Enrollment", p.TOTAL_CNT, "num")}
            ${row("% English Learner", p.EL_PCT, "pct")}
            ${row("% Low Income", p.LI_PCT, "pct")}
            ${row("% High Needs", p.HN_PCT, "pct")}
        `;
    }
    if (kind === "tract") {
        return `
            <div class="popup-title">${p.NAMELSAD || "Census Tract"}</div>
            <div class="popup-row"><span class="label">GEOID</span><span class="value">${p.GEOID}</span></div>
            ${row("Population 5+", p.lang_total, "num")}
            ${row("Median Household Income", p.median_household_income, "usd")}
            ${row("% non-English at home", p.non_english_pct, "pct")}
            ${row("% Foreign-born", p.foreign_born_pct, "pct")}
            ${row("% Bachelor's or higher", p.bachelors_or_higher_pct, "pct")}
            ${row("% Severely Rent-Burdened", p.severe_burden_pct, "pct")}
        `;
    }
    if (kind === "muni") {
        const tags = [];
        if (p.is_lynn) tags.push('<div class="popup-tag" style="background:#FFE082;">LYNN — DASHBOARD FOCUS</div>');
        else if (p.is_gateway) tags.push('<div class="popup-tag" style="background:#E1BEE7;">GATEWAY CITY</div>');
        return `
            ${tags.join("")}
            <div class="popup-title">${p.town_display || p.TOWN}</div>
            <div class="popup-row"><span class="label">County</span><span class="value">${p.COUNTY || "—"}</span></div>
            ${row("Population (2020)", p.pop_2020 || p.POP2020, "num")}
            ${p.DIST_NAME ? `<div class="popup-row"><span class="label">Matched district</span><span class="value">${p.DIST_NAME}</span></div>` : ""}
            ${row("Enrollment", p.TOTAL_CNT, "num")}
            ${row("4-yr grad rate", p.grad_4yr, "pct")}
            ${row("Per-pupil $", p.per_pupil, "usd")}
            ${row("% ELL", p.EL_PCT, "pct")}
            ${row("% Low Income", p.LI_PCT, "pct")}
            ${row("MCAS Gr10 ELA %M+E", p.mcas_g10_ela_me, "pct")}
            ${row("MCAS Gr10 Math %M+E", p.mcas_g10_math_me, "pct")}
        `;
    }
    if (kind === "district") {
        const isLynn = p.ORG8CODE === "01630000";
        return `
            ${isLynn ? '<div class="popup-tag">LYNN PUBLIC SCHOOLS</div>' : ""}
            <div class="popup-title">${p.DIST_NAME || "District"}</div>
            <div class="popup-row"><span class="label">Org code</span><span class="value">${p.ORG8CODE}</span></div>
            <div class="popup-row"><span class="label">Type</span><span class="value">${p.TYPE || "—"}</span></div>
            ${row("Enrollment", p.TOTAL_CNT, "num")}
            ${row("4-yr Graduation", p.grad_4yr, "pct")}
            ${row("Dropout", p.dropout_pct, "pct")}
            ${row("Per-pupil $", p.per_pupil, "usd")}
            ${row("% ELL", p.EL_PCT, "pct")}
            ${row("% Low Income", p.LI_PCT, "pct")}
            ${row("MCAS Gr10 ELA %M+E", p.mcas_g10_ela_me, "pct")}
            ${row("MCAS Gr10 Math %M+E", p.mcas_g10_math_me, "pct")}
            ${row("Chronic absent", p.chronic_absent_pct, "pct")}
        `;
    }
    return `<div class="popup-title">Feature</div>`;
}

// ─── CHOROPLETH APPLY ────────────────────────────────────────────────────────
function applyChoropleth() {
    const { level, metric, palette, classify } = state;
    const m = getMetric(metric);
    const paint = paintExpression(metric, palette, classify, level);
    const layerMap = { muni: "muni-fill", district: "district-fill", tract: "tract-fill" };
    Object.entries(layerMap).forEach(([lvl, layerId]) => {
        if (!map.getLayer(layerId)) return;
        map.setLayoutProperty(layerId, "visibility", lvl === level ? "visible" : "none");
        if (lvl === level) {
            map.setPaintProperty(layerId, "fill-color", paint);
        }
    });
    if (state.extrude3d) refresh3D();
}

function refresh3D() {
    const { level, metric } = state;
    const layerId = { muni: "muni-3d", district: "district-3d", tract: "tract-3d" }[level];
    // 3D layer is added lazily — handled in toggle handler
}

// ─── LEGEND ──────────────────────────────────────────────────────────────────
function updateLegend() {
    const { level, metric, palette, classify } = state;
    const m = getMetric(metric);
    const palObj = PALETTES[palette];
    const titleEl = document.getElementById("legendTitle");
    const stopsEl = document.getElementById("legendStops");
    const metaEl = document.getElementById("legendMeta");
    titleEl.textContent = m.label;

    const values = getValuesForLevel(level, metric);

    if (values.length === 0) {
        stopsEl.innerHTML = '<div class="legend-row" style="color:#90A4AE;">No data available at this level</div>';
        metaEl.innerHTML = "";
        return;
    }

    if (classify === "continuous") {
        const min = Math.min(...values), max = Math.max(...values);
        const colors = sampleColors(palObj.colors, 9);
        const bar = colors.map(c => `<span class="legend-bar-stop" style="background:${c};"></span>`).join("");
        stopsEl.innerHTML = `
            <div class="legend-bar">${bar}</div>
            <div class="legend-axis">
                <span>${fmt(min, m.format)}</span>
                <span>${fmt(max, m.format)}</span>
            </div>
        `;
    } else {
        const breaks = classify === "quantile"
            ? quantileBreaks(values, 5)
            : equalIntervalBreaks(values, 5);
        const colors = sampleColors(palObj.colors, 5);
        const min = Math.min(...values), max = Math.max(...values);
        const ranges = [`< ${fmt(breaks[0], m.format)}`];
        for (let i = 0; i < breaks.length - 1; i++) {
            ranges.push(`${fmt(breaks[i], m.format)} – ${fmt(breaks[i+1], m.format)}`);
        }
        ranges.push(`≥ ${fmt(breaks[breaks.length-1], m.format)}`);
        let html = "";
        for (let i = 0; i < 5; i++) {
            html += `<div class="legend-class"><span class="legend-class-swatch" style="background:${colors[i]};"></span><span class="legend-class-range">${ranges[i]}</span></div>`;
        }
        stopsEl.innerHTML = html;
    }

    metaEl.innerHTML = `${values.length.toLocaleString()} of ${GEO_DATA[level].features.length.toLocaleString()} have data`;
}

// ─── UI WIRING ───────────────────────────────────────────────────────────────
function populateMetricSelect() {
    const sel = document.getElementById("metricSelect");
    const categories = [...new Set(METRICS.filter(m => m.levels.includes(state.level)).map(m => m.cat))];
    sel.innerHTML = "";
    categories.forEach(cat => {
        const grp = document.createElement("optgroup");
        grp.label = cat;
        METRICS.filter(m => m.cat === cat && m.levels.includes(state.level)).forEach(m => {
            const opt = document.createElement("option");
            opt.value = m.id;
            opt.textContent = m.label;
            grp.appendChild(opt);
        });
        sel.appendChild(grp);
    });
    // If current metric isn't available at this level, pick the first option
    const avail = METRICS.filter(m => m.levels.includes(state.level)).map(m => m.id);
    if (!avail.includes(state.metric)) state.metric = avail[0];
    sel.value = state.metric;
    // Also reset palette to metric's default
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
        "ref-district-outline":  ["district-outline"],
        "ref-lynn-schools":      ["schools-circles", "schools-labels"],
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

    document.getElementById("panelToggle").addEventListener("click", () => {
        document.getElementById("controlPanel").classList.toggle("collapsed");
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
    const paint = paintExpression(metric, state.palette, state.classify, level);
    const layerCfg = {
        id: extrudeLayerId, type: "fill-extrusion", source: sourceId,
        paint: {
            "fill-extrusion-color": paint,
            "fill-extrusion-height": [
                "case",
                ["==", ["typeof", ["get", metric]], "number"],
                ["*", ["to-number", ["get", metric]], heightScalar],
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
