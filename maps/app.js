/* ============================================================================
   Lynn Data Dive — Interactive Maps
   Built with MapLibre GL JS + OpenFreeMap vector tiles + jsDelivr-served GeoJSON
   from the lehs-data-dive repo.

   This is a real, ArcGIS-style web map: vector polygons, layer toggling,
   click-to-inspect feature popups, bivariate choropleths, 3D extrusion,
   and a live-updating legend.
   ============================================================================ */

// ----------------------------------------------------------------------------
// Data sources — same-origin (served from this maps/ folder on GitHub Pages).
// Sourced from the lehs-data-dive repo; copied here at build time so loads
// are fast and free of CDN/CORS gotchas. Refresh by re-running the geo
// build script in that repo and copying the .geojson outputs here.
// ----------------------------------------------------------------------------
const DATA_BASE = "data";
const SOURCES = {
    tracts:        `${DATA_BASE}/lynn_tracts.geojson`,
    schools:       `${DATA_BASE}/lynn_schools.geojson`,
    town:          `${DATA_BASE}/lynn_town.geojson`,
    districts:     `${DATA_BASE}/ma_districts_metrics.geojson`,
    municipalities:`${DATA_BASE}/ma_municipalities.geojson`,
};

// ----------------------------------------------------------------------------
// Map state
// ----------------------------------------------------------------------------
const state = {
    activeLayers: {
        tracts: true,
        schools: true,
        town: true,
        districts: false,
        gateway: false,  // legacy alias — we now use municipalities subset
    },
    tractVariable: "non_english_pct",
    districtVariable: "grad_4yr",
    extrude3d: false,
    bivariate: false,
    labels: true,
};

// ----------------------------------------------------------------------------
// Color scales — Carto-style sequential palettes by domain
// ----------------------------------------------------------------------------
const SCALES = {
    // Tract variables (0..1 except income)
    non_english_pct:        { stops: [0, "#f7fcf5", 0.1, "#c7e9c0", 0.2, "#74c476", 0.35, "#31a354", 0.5, "#006d2c"], fmt: pct },
    median_household_income:{ stops: [25000, "#f7fbff", 60000, "#9ecae1", 90000, "#4292c6", 120000, "#08519c"],       fmt: usd },
    foreign_born_pct:       { stops: [0, "#fcfbfd", 0.1, "#dadaeb", 0.2, "#9e9ac8", 0.35, "#6a51a3", 0.5, "#3f007d"], fmt: pct },
    bachelors_or_higher_pct:{ stops: [0, "#f7fbff", 0.25, "#9ecae1", 0.5, "#4292c6", 0.75, "#08519c"],                fmt: pct },
    severe_burden_pct:      { stops: [0, "#fff5f0", 0.3, "#fcae91", 0.5, "#fb6a4a", 0.7, "#cb181d"],                  fmt: pct },
    // District / town variables
    grad_4yr:               { stops: [0.5, "#440154", 0.7, "#3b528b", 0.85, "#21918c", 0.95, "#5ec962", 1.0, "#fde725"], fmt: pct },
    per_pupil:              { stops: [12000, "#440154", 18000, "#3b528b", 24000, "#21918c", 32000, "#5ec962"],          fmt: usd },
    EL_PCT:                 { stops: [0, "#f7fcf5", 0.1, "#c7e9c0", 0.25, "#74c476", 0.5, "#31a354"],                   fmt: pct },
    LI_PCT:                 { stops: [0, "#fff5f0", 0.3, "#fcae91", 0.6, "#fb6a4a", 0.9, "#cb181d"],                    fmt: pct },
    HN_PCT:                 { stops: [0, "#fcfbfd", 0.3, "#dadaeb", 0.6, "#9e9ac8", 0.9, "#3f007d"],                    fmt: pct },
};

const VARIABLE_LABELS = {
    non_english_pct:         "% non-English at home",
    median_household_income: "Median household income",
    foreign_born_pct:        "% Foreign-born",
    bachelors_or_higher_pct: "% Bachelor's or higher",
    severe_burden_pct:       "% Severely rent-burdened",
    grad_4yr:                "4-year graduation rate",
    per_pupil:               "Per-pupil spending",
    EL_PCT:                  "% English Learner",
    LI_PCT:                  "% Low Income",
    HN_PCT:                  "% High Needs",
};

// 3×3 bivariate palette: ELL × LowIncome (Joshua Stevens / Cynthia Brewer scheme)
const BIVARIATE_PALETTE = [
    "#e8e8e8", "#b4d3e1", "#509dc2",  // low EL, low→high LI
    "#e4acac", "#ad9eaf", "#5698b9",
    "#c85a5a", "#985356", "#574249",  // high EL, low→high LI
];

// ----------------------------------------------------------------------------
// Formatting helpers
// ----------------------------------------------------------------------------
function pct(v) { return v == null ? "—" : `${(v * 100).toFixed(0)}%`; }
function usd(v) { return v == null ? "—" : `$${Math.round(v).toLocaleString()}`; }
function num(v) { return v == null ? "—" : Math.round(v).toLocaleString(); }

// Build a MapLibre paint expression for a color scale variable
function paintForVariable(variable) {
    const scale = SCALES[variable];
    if (!scale) return "#cccccc";
    const expr = ["interpolate", ["linear"], ["get", variable]];
    for (let i = 0; i < scale.stops.length; i += 2) {
        expr.push(scale.stops[i], scale.stops[i + 1]);
    }
    return ["case",
        ["==", ["get", variable], null], "#e0e0e0",
        ["!=", ["typeof", ["get", variable]], "number"], "#e0e0e0",
        expr
    ];
}

// Build a bivariate color expression: ELL × LI quantiles
function paintBivariate(elVar = "EL_PCT", liVar = "LI_PCT") {
    // Map (el_bin, li_bin) -> index 0..8 in palette
    // el_bin: <0.1 → 0, 0.1-0.3 → 1, >=0.3 → 2
    // li_bin: <0.3 → 0, 0.3-0.6 → 1, >=0.6 → 2
    return ["case",
        ["==", ["get", elVar], null], "#e0e0e0",
        ["all", ["<", ["get", elVar], 0.1], ["<", ["get", liVar], 0.3]], BIVARIATE_PALETTE[0],
        ["all", ["<", ["get", elVar], 0.1], ["<", ["get", liVar], 0.6]], BIVARIATE_PALETTE[1],
        ["all", ["<", ["get", elVar], 0.1]],                              BIVARIATE_PALETTE[2],
        ["all", ["<", ["get", elVar], 0.3], ["<", ["get", liVar], 0.3]], BIVARIATE_PALETTE[3],
        ["all", ["<", ["get", elVar], 0.3], ["<", ["get", liVar], 0.6]], BIVARIATE_PALETTE[4],
        ["all", ["<", ["get", elVar], 0.3]],                              BIVARIATE_PALETTE[5],
        ["all", ["<", ["get", liVar], 0.3]],                              BIVARIATE_PALETTE[6],
        ["all", ["<", ["get", liVar], 0.6]],                              BIVARIATE_PALETTE[7],
        BIVARIATE_PALETTE[8],
    ];
}

// ----------------------------------------------------------------------------
// Init map
// ----------------------------------------------------------------------------
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
    customAttribution: '<a href="https://maxwellhowegis.com" target="_blank">© Maxwell Howe</a> · Data: MA DESE · US Census · MassGIS',
}), "bottom-right");
map.addControl(new maplibregl.ScaleControl({ maxWidth: 120, unit: "imperial" }), "bottom-left");

// ----------------------------------------------------------------------------
// On map load, fetch all GeoJSON in parallel and add sources + layers
// ----------------------------------------------------------------------------
map.on("load", async () => {
    const [tracts, schools, town, districts, municipalities] = await Promise.all([
        fetch(SOURCES.tracts).then(r => r.json()),
        fetch(SOURCES.schools).then(r => r.json()),
        fetch(SOURCES.town).then(r => r.json()),
        fetch(SOURCES.districts).then(r => r.json()),
        fetch(SOURCES.municipalities).then(r => r.json()),
    ]).catch(err => {
        console.error("GeoJSON load failed:", err);
        document.getElementById("mapLoading").innerHTML = "<div>Failed to load map data. Check the browser console.</div>";
        return [null, null, null, null, null];
    });

    if (!tracts) return;

    // ---------------- SOURCES ----------------
    map.addSource("tracts", { type: "geojson", data: tracts });
    map.addSource("schools", { type: "geojson", data: schools });
    map.addSource("town", { type: "geojson", data: town });
    map.addSource("districts", { type: "geojson", data: districts });
    map.addSource("municipalities", { type: "geojson", data: municipalities });

    // ---------------- MA MUNICIPALITIES (background, statewide context) ----------------
    // Polygon fill — visible when zoomed out
    map.addLayer({
        id: "muni-fill",
        type: "fill",
        source: "municipalities",
        paint: {
            "fill-color": [
                "case",
                ["==", ["get", "is_lynn"], true], "#FFB81C",
                ["==", ["get", "is_gateway"], true], "#9C27B0",
                "#e0e7ed",
            ],
            "fill-opacity": [
                "interpolate", ["linear"], ["zoom"],
                7, 0.6,
                10, 0.35,
                12, 0.1,
                14, 0.0,
            ],
        },
        layout: { visibility: "none" },
    });
    map.addLayer({
        id: "muni-outline",
        type: "line",
        source: "municipalities",
        paint: {
            "line-color": [
                "case",
                ["==", ["get", "is_lynn"], true], "#FFB81C",
                ["==", ["get", "is_gateway"], true], "#6a1b9a",
                "#90a4ae",
            ],
            "line-width": [
                "case",
                ["==", ["get", "is_lynn"], true], 3,
                ["==", ["get", "is_gateway"], true], 2,
                0.5,
            ],
            "line-opacity": [
                "interpolate", ["linear"], ["zoom"],
                7, 0.85,
                12, 0.55,
            ],
        },
        layout: { visibility: "none" },
    });

    // ---------------- MA DISTRICTS (alternative polygon choropleth) ----------------
    map.addLayer({
        id: "districts-fill",
        type: "fill",
        source: "districts",
        filter: ["==", ["get", "TYPE"], "Operating District"],
        paint: {
            "fill-color": paintForVariable(state.districtVariable),
            "fill-opacity": 0.65,
        },
        layout: { visibility: "none" },
    });
    map.addLayer({
        id: "districts-outline",
        type: "line",
        source: "districts",
        filter: ["==", ["get", "TYPE"], "Operating District"],
        paint: { "line-color": "#37474F", "line-width": 0.4, "line-opacity": 0.4 },
        layout: { visibility: "none" },
    });

    // ---------------- LYNN TRACTS (choropleth) ----------------
    map.addLayer({
        id: "tracts-fill",
        type: "fill",
        source: "tracts",
        paint: {
            "fill-color": paintForVariable(state.tractVariable),
            "fill-opacity": 0.7,
        },
    });
    map.addLayer({
        id: "tracts-outline",
        type: "line",
        source: "tracts",
        paint: { "line-color": "#37474F", "line-width": 0.5, "line-opacity": 0.5 },
    });
    map.addLayer({
        id: "tracts-3d",
        type: "fill-extrusion",
        source: "tracts",
        paint: {
            "fill-extrusion-color": paintForVariable(state.tractVariable),
            "fill-extrusion-height": [
                "case",
                ["==", ["get", state.tractVariable], null], 0,
                ["*", ["coalesce", ["get", state.tractVariable], 0], 800],
            ],
            "fill-extrusion-opacity": 0.75,
            "fill-extrusion-base": 0,
        },
        layout: { visibility: "none" },
    });

    // ---------------- LYNN TOWN + NEIGHBORS (outline only) ----------------
    map.addLayer({
        id: "town-outline",
        type: "line",
        source: "town",
        paint: {
            "line-color": [
                "case",
                ["==", ["get", "TOWN"], "LYNN"], "#0A1F44",
                "#607D8B",
            ],
            "line-width": [
                "case",
                ["==", ["get", "TOWN"], "LYNN"], 3.5,
                1.5,
            ],
            "line-opacity": 0.85,
        },
    });
    map.addLayer({
        id: "town-labels",
        type: "symbol",
        source: "town",
        layout: {
            "text-field": ["upcase", ["get", "TOWN"]],
            "text-font": ["Noto Sans Bold"],
            "text-size": 11,
            "text-letter-spacing": 0.08,
            "text-anchor": "center",
            "symbol-placement": "point",
        },
        paint: {
            "text-color": "#0A1F44",
            "text-halo-color": "#ffffff",
            "text-halo-width": 1.8,
            "text-halo-blur": 0.3,
        },
        filter: ["!=", ["get", "TOWN"], "LYNN"],
    });

    // ---------------- LYNN SCHOOLS (point markers) ----------------
    // Compute a "need_index" feature-state for coloring? Use total enrollment for sizing.
    map.addLayer({
        id: "schools-circles",
        type: "circle",
        source: "schools",
        paint: {
            "circle-radius": [
                "interpolate", ["linear"], ["coalesce", ["get", "TOTAL_CNT"], 250],
                100, 5,
                500, 8,
                1000, 12,
                2000, 18,
            ],
            "circle-color": [
                "case",
                ["==", ["get", "ORG_CODE"], "01630510"], "#FFB81C",  // LEHS
                "#0A1F44",
            ],
            "circle-stroke-color": "#ffffff",
            "circle-stroke-width": 2,
            "circle-opacity": 0.95,
        },
    });
    map.addLayer({
        id: "schools-labels",
        type: "symbol",
        source: "schools",
        layout: {
            "text-field": ["get", "NAME"],
            "text-font": ["Noto Sans Regular"],
            "text-size": 10,
            "text-anchor": "top",
            "text-offset": [0, 1.2],
            "text-allow-overlap": false,
            "text-optional": true,
        },
        paint: {
            "text-color": "#0A1F44",
            "text-halo-color": "#ffffff",
            "text-halo-width": 1.5,
        },
        minzoom: 13,
    });

    // ---------------- INTERACTIONS ----------------
    setupHover("tracts-fill", "tract");
    setupHover("districts-fill", "district");
    setupHover("muni-fill", "muni");
    setupClick("tracts-fill", buildTractPopup);
    setupClick("districts-fill", buildDistrictPopup);
    setupClick("muni-fill", buildMuniPopup);
    setupClick("schools-circles", buildSchoolPopup);

    // ---------------- LAUNCH ----------------
    updateLegend();
    document.getElementById("mapLoading").classList.add("hidden");
});

// ----------------------------------------------------------------------------
// Hover helpers — change cursor + slight color highlight via feature-state
// ----------------------------------------------------------------------------
function setupHover(layerId, kind) {
    let hoveredId = null;
    map.on("mouseenter", layerId, () => { map.getCanvas().style.cursor = "pointer"; });
    map.on("mouseleave", layerId, () => { map.getCanvas().style.cursor = ""; });
}

function setupClick(layerId, popupBuilder) {
    map.on("click", layerId, e => {
        if (!e.features.length) return;
        const feat = e.features[0];
        const popupContent = popupBuilder(feat);
        new maplibregl.Popup({ closeButton: true, maxWidth: "340px" })
            .setLngLat(e.lngLat)
            .setHTML(popupContent)
            .addTo(map);
    });
}

// ----------------------------------------------------------------------------
// Popup builders
// ----------------------------------------------------------------------------
function buildSchoolPopup(feat) {
    const p = feat.properties;
    const isLehs = p.ORG_CODE === "01630510";
    return `
        ${isLehs ? '<div class="popup-tag">FOCUS SCHOOL</div>' : ""}
        <div class="popup-title">${p.NAME}</div>
        <div class="popup-row"><span class="label">Type</span><span class="value">${p.TYPE_DESC || p.TYPE || "—"}</span></div>
        <div class="popup-row"><span class="label">Grades</span><span class="value">${p.GRADES || "—"}</span></div>
        <div class="popup-row"><span class="label">Enrollment</span><span class="value">${num(p.TOTAL_CNT)}</span></div>
        <div class="popup-row"><span class="label">% English Learner</span><span class="value">${pct(p.EL_PCT)}</span></div>
        <div class="popup-row"><span class="label">% Low Income</span><span class="value">${pct(p.LI_PCT)}</span></div>
        <div class="popup-row"><span class="label">% High Needs</span><span class="value">${pct(p.HN_PCT)}</span></div>
    `;
}

function buildTractPopup(feat) {
    const p = feat.properties;
    return `
        <div class="popup-title">${p.NAMELSAD || "Census Tract"}</div>
        <div class="popup-row"><span class="label">GEOID</span><span class="value">${p.GEOID}</span></div>
        <div class="popup-row"><span class="label">Population (5+)</span><span class="value">${num(p.lang_total)}</span></div>
        <div class="popup-row"><span class="label">% non-English at home</span><span class="value">${pct(p.non_english_pct)}</span></div>
        <div class="popup-row"><span class="label">Median household income</span><span class="value">${usd(p.median_household_income)}</span></div>
        <div class="popup-row"><span class="label">% Foreign-born</span><span class="value">${pct(p.foreign_born_pct)}</span></div>
        <div class="popup-row"><span class="label">% Bachelor's or higher</span><span class="value">${pct(p.bachelors_or_higher_pct)}</span></div>
        <div class="popup-row"><span class="label">% Severely rent-burdened</span><span class="value">${pct(p.severe_burden_pct)}</span></div>
    `;
}

function buildDistrictPopup(feat) {
    const p = feat.properties;
    const isLynn = p.ORG8CODE === "01630000";
    return `
        ${isLynn ? '<div class="popup-tag">LYNN PUBLIC SCHOOLS</div>' : ""}
        <div class="popup-title">${p.DIST_NAME || p.NAME || "District"}</div>
        <div class="popup-row"><span class="label">Org code</span><span class="value">${p.ORG8CODE}</span></div>
        <div class="popup-row"><span class="label">Type</span><span class="value">${p.TYPE || "—"}</span></div>
        <div class="popup-row"><span class="label">Enrollment</span><span class="value">${num(p.TOTAL_CNT)}</span></div>
        <div class="popup-row"><span class="label">4-yr graduation rate</span><span class="value">${pct(p.grad_4yr)}</span></div>
        <div class="popup-row"><span class="label">Per-pupil spending</span><span class="value">${usd(p.per_pupil)}</span></div>
        <div class="popup-row"><span class="label">% English Learner</span><span class="value">${pct(p.EL_PCT)}</span></div>
        <div class="popup-row"><span class="label">% Low Income</span><span class="value">${pct(p.LI_PCT)}</span></div>
        <div class="popup-row"><span class="label">% High Needs</span><span class="value">${pct(p.HN_PCT)}</span></div>
    `;
}

function buildMuniPopup(feat) {
    const p = feat.properties;
    const tags = [];
    if (p.is_lynn) tags.push('<div class="popup-tag" style="background:#FFE082;">LYNN — DASHBOARD FOCUS</div>');
    else if (p.is_gateway) tags.push('<div class="popup-tag" style="background:#E1BEE7;">GATEWAY CITY</div>');
    return `
        ${tags.join("")}
        <div class="popup-title">${p.town_display || p.TOWN}</div>
        <div class="popup-row"><span class="label">County</span><span class="value">${p.COUNTY || "—"}</span></div>
        <div class="popup-row"><span class="label">Population (2020)</span><span class="value">${num(p.pop_2020 || p.POP2020)}</span></div>
        <div class="popup-row"><span class="label">Type</span><span class="value">${p.TYPE || "—"}</span></div>
        ${p.DIST_NAME ? `
            <div class="popup-row"><span class="label">Matched district</span><span class="value">${p.DIST_NAME}</span></div>
            <div class="popup-row"><span class="label">District 4-yr grad rate</span><span class="value">${pct(p.grad_4yr)}</span></div>
            <div class="popup-row"><span class="label">District per-pupil</span><span class="value">${usd(p.per_pupil)}</span></div>
        ` : '<div class="popup-row" style="color:#90A4AE;font-size:11px;">No direct district match (regional district or charter)</div>'}
    `;
}

// ----------------------------------------------------------------------------
// Layer toggles
// ----------------------------------------------------------------------------
function setLayerVisibility(layerIds, visible) {
    layerIds.forEach(id => {
        if (map.getLayer(id)) {
            map.setLayoutProperty(id, "visibility", visible ? "visible" : "none");
        }
    });
}

const LAYER_GROUPS = {
    tracts: ["tracts-fill", "tracts-outline"],
    schools: ["schools-circles", "schools-labels"],
    town: ["town-outline", "town-labels"],
    districts: ["districts-fill", "districts-outline"],
    gateway: ["muni-fill", "muni-outline"],  // gateway = MA municipalities layer
};

["tracts", "schools", "town", "districts", "gateway"].forEach(layer => {
    const el = document.getElementById(`layer-${layer}`);
    if (!el) return;
    el.addEventListener("change", e => {
        state.activeLayers[layer] = e.target.checked;
        const ids = LAYER_GROUPS[layer];
        // 3D extrusion replaces the flat tracts-fill, so handle that toggle separately
        if (layer === "tracts" && state.extrude3d) {
            setLayerVisibility(["tracts-3d", "tracts-outline"], e.target.checked);
            setLayerVisibility(["tracts-fill"], false);
        } else {
            setLayerVisibility(ids, e.target.checked);
        }
        if (layer === "districts") {
            document.getElementById("district-variable-section").style.display =
                e.target.checked ? "block" : "none";
        }
    });
});

// ----------------------------------------------------------------------------
// Variable selectors
// ----------------------------------------------------------------------------
document.getElementById("tract-variable").addEventListener("change", e => {
    state.tractVariable = e.target.value;
    map.setPaintProperty("tracts-fill", "fill-color", paintForVariable(state.tractVariable));
    if (map.getLayer("tracts-3d")) {
        map.setPaintProperty("tracts-3d", "fill-extrusion-color", paintForVariable(state.tractVariable));
        const heightVar = state.tractVariable;
        map.setPaintProperty("tracts-3d", "fill-extrusion-height", [
            "case",
            ["==", ["get", heightVar], null], 0,
            ["*", ["coalesce", ["get", heightVar], 0],
                heightVar === "median_household_income" ? 0.03 : 800],
        ]);
    }
    updateLegend();
});

document.getElementById("district-variable").addEventListener("change", e => {
    state.districtVariable = e.target.value;
    map.setPaintProperty("districts-fill", "fill-color", paintForVariable(state.districtVariable));
    updateLegend();
});

// ----------------------------------------------------------------------------
// 3D toggle
// ----------------------------------------------------------------------------
document.getElementById("toggle-3d").addEventListener("change", e => {
    state.extrude3d = e.target.checked;
    if (e.target.checked) {
        setLayerVisibility(["tracts-3d"], state.activeLayers.tracts);
        setLayerVisibility(["tracts-fill"], false);
        map.easeTo({ pitch: 50, bearing: -20, duration: 800 });
    } else {
        setLayerVisibility(["tracts-3d"], false);
        setLayerVisibility(["tracts-fill"], state.activeLayers.tracts);
        map.easeTo({ pitch: 0, bearing: 0, duration: 800 });
    }
});

// ----------------------------------------------------------------------------
// Bivariate toggle
// ----------------------------------------------------------------------------
document.getElementById("toggle-bivariate").addEventListener("change", e => {
    state.bivariate = e.target.checked;
    if (e.target.checked) {
        // For Lynn tracts we don't have EL_PCT / LI_PCT at tract level —
        // bivariate applies to districts or municipalities. Use district paint.
        map.setPaintProperty("districts-fill", "fill-color", paintBivariate("EL_PCT", "LI_PCT"));
        map.setPaintProperty("muni-fill", "fill-color", paintBivariate("EL_PCT", "LI_PCT"));
    } else {
        map.setPaintProperty("districts-fill", "fill-color", paintForVariable(state.districtVariable));
        map.setPaintProperty("muni-fill", "fill-color", [
            "case",
            ["==", ["get", "is_lynn"], true], "#FFB81C",
            ["==", ["get", "is_gateway"], true], "#9C27B0",
            "#e0e7ed",
        ]);
    }
    updateLegend();
});

// ----------------------------------------------------------------------------
// School label toggle
// ----------------------------------------------------------------------------
document.getElementById("toggle-labels").addEventListener("change", e => {
    state.labels = e.target.checked;
    if (map.getLayer("schools-labels")) {
        map.setLayoutProperty("schools-labels", "visibility", e.target.checked ? "visible" : "none");
    }
});

// ----------------------------------------------------------------------------
// Quick view buttons (Lynn / MA / North Shore)
// ----------------------------------------------------------------------------
const VIEWS = {
    lynn:        { center: [-70.95, 42.47], zoom: 11.8, pitch: 0, bearing: 0 },
    ma:          { center: [-71.7, 42.25],  zoom: 7.5,  pitch: 0, bearing: 0 },
    "north-shore": { center: [-70.9, 42.55],  zoom: 9.5,  pitch: 0, bearing: 0 },
};
document.querySelectorAll(".view-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".view-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        const v = VIEWS[btn.dataset.view];
        if (!v) return;
        map.flyTo({ ...v, duration: 1200, essential: true });
        // Auto-toggle layers for the MA view
        if (btn.dataset.view === "ma") {
            // Show MA-scale layers, hide Lynn close-up layers
            document.getElementById("layer-gateway").checked = true;
            document.getElementById("layer-gateway").dispatchEvent(new Event("change"));
            document.getElementById("layer-districts").checked = false;  // pick municipalities as primary
            document.getElementById("layer-districts").dispatchEvent(new Event("change"));
        } else {
            document.getElementById("layer-gateway").checked = false;
            document.getElementById("layer-gateway").dispatchEvent(new Event("change"));
        }
    });
});

// ----------------------------------------------------------------------------
// Control panel collapse
// ----------------------------------------------------------------------------
document.getElementById("panelToggle").addEventListener("click", () => {
    document.getElementById("controlPanel").classList.toggle("collapsed");
});

// ----------------------------------------------------------------------------
// Legend rendering — updates whenever the active variable changes
// ----------------------------------------------------------------------------
function updateLegend() {
    const titleEl = document.getElementById("legendTitle");
    const stopsEl = document.getElementById("legendStops");
    if (state.bivariate) {
        titleEl.textContent = "% ELL × % Low Income (district/muni)";
        stopsEl.innerHTML = renderBivariateLegend();
        return;
    }
    // Default: show tract variable legend
    const variable = state.activeLayers.tracts ? state.tractVariable : state.districtVariable;
    titleEl.textContent = VARIABLE_LABELS[variable] || "Legend";
    const scale = SCALES[variable];
    if (!scale) {
        stopsEl.innerHTML = "<div class='legend-row'>(no legend)</div>";
        return;
    }
    // Build a horizontal gradient bar with axis labels
    const colors = [];
    for (let i = 1; i < scale.stops.length; i += 2) colors.push(scale.stops[i]);
    const minVal = scale.stops[0];
    const maxVal = scale.stops[scale.stops.length - 2];
    const bar = colors.map(c => `<span class="legend-bar-stop" style="background:${c};"></span>`).join("");
    stopsEl.innerHTML = `
        <div class="legend-bar">${bar}</div>
        <div class="legend-axis">
            <span>${scale.fmt(minVal)}</span>
            <span>${scale.fmt(maxVal)}</span>
        </div>
    `;
}

function renderBivariateLegend() {
    const labels = ["low", "mid", "high"];
    let html = '<div style="display:grid;grid-template-columns:auto repeat(3,18px);gap:2px;font-size:10px;align-items:center;">';
    html += '<div></div>';
    labels.forEach(l => html += `<div style="text-align:center;">${l}</div>`);
    ["high", "mid", "low"].forEach((rowLabel, rowIdx) => {
        const row = 2 - rowIdx;  // high row first (top)
        html += `<div style="text-align:right;padding-right:4px;">${rowLabel}</div>`;
        for (let col = 0; col < 3; col++) {
            const idx = row * 3 + col;
            html += `<div style="width:18px;height:18px;background:${BIVARIATE_PALETTE[idx]};"></div>`;
        }
    });
    html += '</div>';
    html += '<div style="font-size:10px;color:#607D8B;margin-top:6px;">Row: % ELL · Column: % Low Income</div>';
    return html;
}
