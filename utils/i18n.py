"""Lightweight internationalization (i18n) for the LEHS Data Dive.

A gettext-style translation layer: call ``t("English source text")`` and get
back the active language's string. There are no opaque key names — the English
text *is* the key, so an untranslated string gracefully renders in English
instead of showing a broken ``home.hero.title`` placeholder. That makes a
phased, page-by-page rollout safe: wrap a string in ``t(...)``, add a Spanish
entry when ready, and anything not yet translated simply stays English.

The active language lives in ``st.session_state["lang"]`` so it persists across
``st.navigation`` page switches. ``language_selector()`` (rendered in every
sidebar via ``branding.sidebar_attribution``) is the single control that sets it.

Lookup is whitespace-insensitive: the catalog key and the in-code string are
both collapsed to single spaces before matching, so multi-line markdown blocks
don't have to match the catalog byte-for-byte to resolve.
"""

from __future__ import annotations

import streamlit as st

# Display name for each supported language, keyed by its code.
LANGUAGES: dict[str, str] = {"en": "English", "es": "Español"}

DEFAULT_LANG = "en"


def current_lang() -> str:
    """The active language code ('en' / 'es'), defaulting to English."""
    return st.session_state.get("lang", DEFAULT_LANG)


def _norm(s: str) -> str:
    """Collapse all runs of whitespace to single spaces for robust matching."""
    return " ".join(s.split())


def t(text: str, /, **kwargs) -> str:
    """Translate ``text`` into the active language.

    The English source string is the lookup key. If the active language is
    English (or no translation exists) the original ``text`` is returned, so
    untranslated strings degrade gracefully. ``kwargs`` are applied via
    ``str.format`` to support placeholders, e.g.
    ``t("Per-pupil ({fy})", fy=2024)``.
    """
    lang = current_lang()
    if lang == DEFAULT_LANG:
        out = text
    else:
        out = _CATALOG.get(lang, {}).get(_norm(text), text)
    return out.format(**kwargs) if kwargs else out


def language_selector() -> None:
    """Render the sidebar language toggle. Binds to ``session_state['lang']``,
    which persists across pages, so the choice sticks through the whole app."""
    st.session_state.setdefault("lang", DEFAULT_LANG)
    with st.sidebar:
        st.radio(
            "🌐 Idioma / Language",
            options=list(LANGUAGES.keys()),
            format_func=lambda c: LANGUAGES[c],
            key="lang",
            horizontal=True,
        )


# ---------------------------------------------------------------------------
# Translation catalog.
#
# Keyed by language code → {normalized English source : translated string}.
# Keys are normalized (single-spaced) at import time so the in-code strings
# (which may carry indentation / line breaks) still match. To translate a new
# string: wrap it in t(...) at the call site, then add an entry below.
#
# Spanish is written in neutral, natural Spanish for Lynn's large
# Spanish-speaking community — not a literal machine gloss. Proper nouns
# (Lynn English High School, LEHS, LPS, MCAS, Gateway Cities, MapLibre) are
# kept in their original form.
# ---------------------------------------------------------------------------

_ES_RAW: dict[str, str] = {
    # --- Sidebar chrome (search box) -------------------------------------
    "🔍 Search": "🔍 Buscar",
    "Search the dashboard": "Buscar en el panel",
    "MCAS, suspensions, budget…": "MCAS, suspensiones, presupuesto…",
    "Type a topic — e.g. *graduation*, *AP*, *budget*, *bilingual*.":
        "Escribe un tema — p. ej. *graduación*, *AP*, *presupuesto*, *bilingüe*.",
    "No matches for “{q}”. Try a broader topic.":
        "Sin resultados para «{q}». Prueba con un tema más general.",

    # --- Header ----------------------------------------------------------
    "Built by": "Creado por",
    "A public, interactive data exploration tool centered on Lynn English "
    "High School (LEHS) — Lynn, Massachusetts.":
        "Una herramienta pública e interactiva para explorar datos sobre Lynn "
        "English High School (LEHS) — Lynn, Massachusetts.",

    # --- Where do you want to start? -------------------------------------
    "Where do you want to start?": "¿Por dónde quieres empezar?",
    "Three nested views of the same place — **Lynn English** the school, "
    "**Lynn Public Schools** the district, and **Lynn** the city around them. "
    "Open whichever one you're curious about; jumping between them is always "
    "one click away in the sidebar.":
        "Tres vistas anidadas del mismo lugar: **Lynn English**, la escuela; "
        "**Lynn Public Schools**, el distrito; y **Lynn**, la ciudad que las "
        "rodea. Abre la que te interese; cambiar entre ellas siempre está a un "
        "clic en la barra lateral.",

    # --- Scope cards -----------------------------------------------------
    "#### 🎓 The School": "#### 🎓 La escuela",
    "#### 🏛️ The District": "#### 🏛️ El distrito",
    "#### 🏙️ The City": "#### 🏙️ La ciudad",

    "Total Enrollment": "Matrícula total",
    "% English Learners": "% Estudiantes de inglés (EL)",
    "% Chronic Absence": "% Ausentismo crónico",
    "4-yr Graduation Rate": "Tasa de graduación (4 años)",
    "District Enrollment": "Matrícula del distrito",
    "Per-pupil expenditure (FY {fy})": "Gasto por alumno (año fiscal {fy})",
    "Total Population": "Población total",
    "Median HH Income": "Ingreso medio del hogar",
    "Foreign-born": "Nacidos en el extranjero",
    "Home languages spoken": "Idiomas hablados en casa",

    "Open School Profile →": "Abrir Perfil de la escuela →",
    "Open District →": "Abrir Distrito →",
    "Open Lynn City →": "Abrir Ciudad de Lynn →",

    "Lynn, MA · coastal Gateway city · "
    "**Citywide + Neighborhoods (22 census tracts)** tabs":
        "Lynn, MA · ciudad costera Gateway · pestañas "
        "**Toda la ciudad + Vecindarios (22 sectores censales)**",

    # Card caption fragments (composed around live data).
    "Lynn English High · Grades 9–12": "Lynn English High · Grados 9–12",
    " · {ratio} student–teacher ratio": " · {ratio} alumnos por docente",
    " · {flne} non-English home language": " · {flne} con idioma del hogar distinto al inglés",
    "Lynn Public Schools · 26 schools": "Lynn Public Schools · 26 escuelas",

    # --- The shift that defines LEHS -------------------------------------
    "The shift that defines LEHS": "El cambio que define a LEHS",
    "More than any single statistic, this is the story: the share of Lynn "
    "English students who are **English Learners** has climbed dramatically over "
    "a generation. It reshapes what the school teaches, who it hires, and how to "
    "read every other number in this dashboard.":
        "Más que cualquier estadística aislada, esta es la historia: la "
        "proporción de estudiantes de Lynn English que son **estudiantes de "
        "inglés** ha aumentado drásticamente en una generación. Eso transforma "
        "lo que la escuela enseña, a quién contrata y cómo leer todas las demás "
        "cifras de este panel.",
    "See the full English Learner pipeline →":
        "Ver todo el recorrido de los estudiantes de inglés →",

    # --- Utility row -----------------------------------------------------
    "#### 🗺️ Maps": "#### 🗺️ Mapas",
    "Interactive MapLibre experiences — Lynn-focused (school pins + "
    "tract demographics) and statewide MA Education Atlas. "
    "**1,800+ MA schools · 351 municipalities · 22 Lynn census tracts.**":
        "Experiencias interactivas en MapLibre: enfocadas en Lynn (escuelas + "
        "datos demográficos por sector censal) y el Atlas Educativo de todo "
        "Massachusetts. **Más de 1,800 escuelas de MA · 351 municipios · 22 "
        "sectores censales de Lynn.**",
    "Open Maps →": "Abrir Mapas →",

    "#### 📊 Data 101": "#### 📊 Datos 101",
    "New to dashboards? **Start here.** A beginner-friendly guide to "
    "what a dataset is, how to read each chart type (bar, line, "
    "histogram, scatter, choropleth, heatmap), what percentages "
    "actually mean, and the most common ways charts mislead. "
    "Built for LEHS students and anyone who's never opened a "
    "dashboard before.":
        "¿Es tu primera vez con un panel de datos? **Empieza aquí.** Una guía "
        "para principiantes sobre qué es un conjunto de datos, cómo leer cada "
        "tipo de gráfico (barras, líneas, histograma, dispersión, mapa "
        "coroplético, mapa de calor), qué significan realmente los porcentajes "
        "y las formas más comunes en que los gráficos engañan. Hecha para "
        "estudiantes de LEHS y para cualquiera que nunca haya abierto un panel.",
    "Open Data 101 →": "Abrir Datos 101 →",

    # --- Or pick by role -------------------------------------------------
    "Or pick by role": "O elige según tu rol",
    "The scopes above answer *what* you want to see. These three paths "
    "answer *who you are* — tailored entry points for families, teachers, "
    "and the school committee.":
        "Las vistas de arriba responden *qué* quieres ver. Estos tres caminos "
        "responden *quién eres*: puntos de entrada pensados para familias, "
        "docentes y el comité escolar.",

    "### For families": "### Para las familias",
    "Choosing a school, understanding outcomes, comparing to siblings.":
        "Elegir escuela, entender los resultados y comparar con escuelas similares.",
    "### For teachers": "### Para docentes",
    "Instructional planning, student insight, subgroup gaps.":
        "Planificación de la enseñanza, conocimiento del estudiantado y brechas entre subgrupos.",
    "### For school committee": "### Para el comité escolar",
    "Accountability, peer comparison, dollar-for-outcome leverage.":
        "Rendición de cuentas, comparación con pares y rendimiento por cada dólar invertido.",

    "School Profile — who attends LEHS today":
        "Perfil de la escuela — quién asiste a LEHS hoy",
    "Academic Performance — MCAS scores, growth, gaps":
        "Rendimiento académico — resultados de MCAS, crecimiento, brechas",
    "Success After HS — does the promise hold up?":
        "Éxito después de la prepa — ¿se cumple la promesa?",
    "Lynn Schools — LEHS vs. its sibling high schools":
        "Escuelas de Lynn — LEHS frente a sus escuelas hermanas",
    "Academic Performance — MCAS by subject, growth, gaps":
        "Rendimiento académico — MCAS por materia, crecimiento, brechas",
    "English Learners — LEHS's central narrative":
        "Estudiantes de inglés — la narrativa central de LEHS",
    "Discipline & Climate — chronic absence by group":
        "Disciplina y clima — ausentismo crónico por grupo",
    "Teachers & Workforce — who's in the building":
        "Docentes y personal — quién está en la escuela",
    "Lynn District — LPS as a whole":
        "Distrito de Lynn — LPS en su conjunto",
    "Finance — per-pupil spending by category":
        "Finanzas — gasto por alumno por categoría",
    "Lynn Schools — vs. same-district siblings":
        "Escuelas de Lynn — frente a las hermanas del mismo distrito",
    "Gateway Cities — 26-city scorecard":
        "Gateway Cities — tabla comparativa de 26 ciudades",
    "Cross-Topic Explorer — what moves with what":
        "Explorador de temas — qué se relaciona con qué",

    "These are starting points, not the only useful pages. The full sidebar "
    "shows every section.":
        "Estos son solo puntos de partida, no las únicas páginas útiles. La "
        "barra lateral muestra todas las secciones.",

    # --- What is this dashboard? -----------------------------------------
    "What is this dashboard?": "¿Qué es este panel?",

    "**The LEHS Data Dive pulls together every publicly available dataset relevant "
    "to Lynn English High School and renders it as a single navigable analysis.** "
    "It's designed for the people who actually need to *understand* the school — "
    "families choosing schools, educators planning supports, journalists looking "
    "for context, researchers studying urban education, and the Lynn community "
    "itself. "
    "It exists because the official sources are fragmented: MCAS scores live in "
    "one DESE Power BI dashboard, enrollment in another, finance in a third, "
    "educator data in a fourth, federal civil-rights data in a fifth, Census "
    "community context in a sixth. **Pulling them together at the school level "
    "is the difference between a stack of separate facts and a coherent picture "
    "of one school.**":
        "**El LEHS Data Dive reúne todos los conjuntos de datos públicos "
        "relevantes para Lynn English High School y los presenta como un único "
        "análisis navegable.**\n\n"
        "Está pensado para quienes de verdad necesitan *entender* la escuela: "
        "familias que eligen escuela, educadores que planifican apoyos, "
        "periodistas que buscan contexto, investigadores que estudian la "
        "educación urbana y la propia comunidad de Lynn.\n\n"
        "Existe porque las fuentes oficiales están fragmentadas: los resultados "
        "de MCAS viven en un panel de Power BI de DESE, la matrícula en otro, las "
        "finanzas en un tercero, los datos del personal docente en un cuarto, los "
        "datos federales de derechos civiles en un quinto y el contexto "
        "comunitario del Censo en un sexto. **Reunirlos a nivel de escuela es la "
        "diferencia entre un montón de datos sueltos y una imagen coherente de "
        "una sola escuela.**",

    # --- Scope box -------------------------------------------------------
    "**Data scope** "
    "- **22 datasets** from MA DESE's E2C Hub (MCAS, graduation, AP, attendance, "
    "finance, staffing, plans of graduates, pathways, postsecondary outcomes) "
    "- **Original research**: Maxwell Howe's catchment + absenteeism geospatial "
    "study using aggregated Lynn Public Schools enrollment data "
    "- **Federal data**: US Census ACS 5-year for Lynn tracts, MassGIS shapefiles "
    "- **Historical depth**: enrollment back to **1992–93**, MCAS back to 2017, "
    "graduation cohorts back to 2005":
        "**Alcance de los datos**\n"
        "- **22 conjuntos de datos** del E2C Hub de MA DESE (MCAS, graduación, "
        "AP, asistencia, finanzas, personal, planes de los graduados, "
        "trayectorias, resultados postsecundarios)\n"
        "- **Investigación original**: el estudio geoespacial de zonas de "
        "asistencia y ausentismo de Maxwell Howe, con datos agregados de "
        "matrícula de Lynn Public Schools\n"
        "- **Datos federales**: Censo de EE. UU. ACS de 5 años para los sectores "
        "de Lynn, shapefiles de MassGIS\n"
        "- **Profundidad histórica**: matrícula desde **1992–93**, MCAS desde "
        "2017, cohortes de graduación desde 2005",

    "**Three peer cohorts** for comparing LEHS: "
    "- **Same district** *(closest comparison)* — LEHS vs. its sibling "
    "Lynn high schools. Same city, same policies → school-level effects show through. "
    "- **Same system** — LEHS within LPS as a whole, including all 26 "
    "schools and elementary feeders. "
    "- **Same role, different city** — LEHS vs. the main public high "
    "school in each of MA's 26 Gateway cities (Brockton, Lawrence, "
    "Chelsea, Lowell, Holyoke, Springfield, +19).":
        "**Tres grupos de comparación** para LEHS:\n"
        "- **Mismo distrito** *(la comparación más cercana)* — LEHS frente a sus "
        "escuelas secundarias hermanas de Lynn. Misma ciudad, mismas políticas → "
        "se notan los efectos a nivel de escuela.\n"
        "- **Mismo sistema** — LEHS dentro de todo LPS, incluidas las 26 escuelas "
        "y las primarias que nutren la matrícula.\n"
        "- **Mismo rol, otra ciudad** — LEHS frente a la principal escuela "
        "secundaria pública de cada una de las 26 ciudades Gateway de MA "
        "(Brockton, Lawrence, Chelsea, Lowell, Holyoke, Springfield y 19 más).",

    "→ Lynn Schools (same district)": "→ Escuelas de Lynn (mismo distrito)",
    "→ Lynn District (same system)": "→ Distrito de Lynn (mismo sistema)",
    "→ Gateway Cities (same role)": "→ Gateway Cities (mismo rol)",

    # --- Questions you can answer here -----------------------------------
    "Questions you can answer here": "Preguntas que puedes responder aquí",

    "- **How is LEHS doing?** — Headline metrics, trends, and peer comparison "
    "on **School Profile** and **Academic Performance**. "
    "- **What does LEHS's English Learner pipeline actually look like?** — "
    "From WIDA proficiency through MCAS, graduation, and into former-EL "
    "years on **English Learners**. "
    "- **Where does the budget go, and does it buy what we hope?** — "
    "Per-pupil spending by category on **Finance**, plus cross-domain "
    "analysis on **Cross-Topic Explorer**. "
    "- **Who works at LEHS, and how does the teacher body match the student "
    "body?** — **Teachers & Workforce**. "
    "- **Where do LEHS students live, and does distance from school predict "
    "absence?** — **Where Students Live** *(aggregated maps)*. "
    "- **What can Lynn learn from Lawrence, Chelsea, Holyoke, and other peer "
    "cities?** — Side-by-side scorecards on **Gateway Cities**. "
    "- **What patterns emerge when you cross-reference everything?** — "
    "**Cross-Topic Explorer** lets you pick any two metrics and see how they "
    "relate across the 26 gateway-city high schools. "
    "*Jump to any of these from the index just below, or the sidebar.*":
        "- **¿Cómo le va a LEHS?** — Métricas clave, tendencias y comparación "
        "con pares en **Perfil de la escuela** y **Rendimiento académico**.\n"
        "- **¿Cómo es realmente el recorrido de los estudiantes de inglés de "
        "LEHS?** — Desde el dominio del idioma (WIDA) hasta MCAS, la graduación "
        "y los años como exestudiante de inglés, en **Estudiantes de inglés**.\n"
        "- **¿A dónde va el presupuesto y compra lo que esperamos?** — Gasto por "
        "alumno por categoría en **Finanzas**, además del análisis entre temas "
        "en **Explorador de temas**.\n"
        "- **¿Quién trabaja en LEHS y cómo se compara el personal docente con el "
        "estudiantado?** — **Docentes y personal**.\n"
        "- **¿Dónde viven los estudiantes de LEHS y la distancia a la escuela "
        "predice la ausencia?** — **Dónde viven los estudiantes** *(mapas "
        "agregados)*.\n"
        "- **¿Qué puede aprender Lynn de Lawrence, Chelsea, Holyoke y otras "
        "ciudades pares?** — Tablas comparativas lado a lado en **Gateway "
        "Cities**.\n"
        "- **¿Qué patrones surgen al cruzar todo?** — El **Explorador de temas** "
        "te permite elegir dos métricas cualesquiera y ver cómo se relacionan en "
        "las 26 escuelas secundarias de las ciudades Gateway.\n\n"
        "*Salta a cualquiera de estas desde el índice de abajo o desde la barra "
        "lateral.*",

    # --- All sections ----------------------------------------------------
    "All sections": "Todas las secciones",
    "The sidebar is grouped into five clusters. Pick anything that's "
    "relevant to what you're trying to figure out.":
        "La barra lateral está organizada en cinco grupos. Elige lo que sea "
        "relevante para lo que quieres averiguar.",
    "**Top of sidebar**": "**Parte superior de la barra lateral**",
    "**The School (LEHS)**": "**La escuela (LEHS)**",
    "**Lynn**": "**Lynn**",
    "**Comparison**": "**Comparación**",
    "**About**": "**Acerca de**",

    "Home — this page": "Inicio — esta página",
    "Maps — Lynn map + statewide MA Education Atlas":
        "Mapas — mapa de Lynn + Atlas Educativo de todo MA",
    "School Profile — demographics, enrollment trends":
        "Perfil de la escuela — datos demográficos y tendencias de matrícula",
    "Academic Performance — MCAS, growth, gaps":
        "Rendimiento académico — MCAS, crecimiento, brechas",
    "English Learners (central narrative)":
        "Estudiantes de inglés (narrativa central)",
    "College & Career — AP, MassCore, FAFSA, plans":
        "Universidad y carrera — AP, MassCore, FAFSA, planes",
    "Success After HS — 9th grade → degrees → earnings":
        "Éxito después de la prepa — 9.º grado → títulos → ingresos",
    "Teachers & Workforce — diversity, staffing":
        "Docentes y personal — diversidad, dotación",
    "Finance — per-pupil spending breakdowns":
        "Finanzas — desglose del gasto por alumno",
    "Discipline & Climate — suspensions, attendance":
        "Disciplina y clima — suspensiones, asistencia",
    "Athletics — records, rivalry, hall of fame":
        "Deportes — récords, rivalidad, salón de la fama",
    "Where Students Live — residential pattern":
        "Dónde viven los estudiantes — patrón residencial",
    "LEHS History — 130+ years of the school's story":
        "Historia de LEHS — más de 130 años de la escuela",
    "District — LPS snapshot + all 26 schools":
        "Distrito — panorama de LPS + las 26 escuelas",
    "City — demographics, economy, neighborhoods":
        "Ciudad — demografía, economía, vecindarios",
    "Lynn Schools — closest peer view":
        "Escuelas de Lynn — la comparación más cercana",
    "Cross-Topic Explorer — cross-domain analysis":
        "Explorador de temas — análisis entre dominios",
    "Data 101 — beginner's guide to the charts":
        "Datos 101 — guía para principiantes sobre los gráficos",
    "Methodology — sources and caveats":
        "Metodología — fuentes y advertencias",

    # --- Footer ----------------------------------------------------------
    "source on GitHub": "código en GitHub",
}

# Normalize keys once so call-site whitespace/indentation doesn't matter.
_CATALOG: dict[str, dict[str, str]] = {
    "es": {_norm(k): v for k, v in _ES_RAW.items()},
}
