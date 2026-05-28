"""
LEHS History.

A dedicated narrative page covering Lynn English from its 1892 founding
to today. Lives at the end of "The School (LEHS)" sidebar group so the
analytical pages stay analytical; this is where the story goes.

Sourced from:
  - Wikipedia (Lynn English High School + 1892 Essex Street building +
    Lynn Public Schools articles)
  - Boston Public Library postcard collection
  - National Register of Historic Places listing
  - The Lynn Item local-paper coverage (architecture and openings)
  - LEHS curated athletics file (assets/curated/lehs_athletics_history.yaml)
  - Athletics page in this dashboard

No content here pulls from opinionated or commentary-driven news
sources — the recent-leadership controversy that lived on School
Profile before is omitted entirely.
"""

import streamlit as st

from utils.branding import sidebar_attribution
from utils.constants import IMAGES_DIR

st.set_page_config(
    page_title="LEHS History | LEHS", page_icon="📜", layout="wide",
)
sidebar_attribution()

# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------

st.title("📜 A history of Lynn English")
st.markdown(
    "The school that the rest of this dashboard talks about as data has "
    "**130+ years** of physical buildings, fires, rebuilds, parades, "
    "world-champion alumni, and civic memory behind it. This page is "
    "the narrative side. The data side lives on "
    "**[School Profile](/School_Profile)** and every page beyond it."
)

_hero_l, _hero_r = st.columns([2, 1], gap="medium")
with _hero_l:
    st.image(
        str(IMAGES_DIR / "lehs-building.jpg"),
        use_container_width=True,
        caption=(
            "The 1931 Classical-Revival main entrance on Goodridge Street — "
            "the third Lynn English building since the school's 1892 founding."
        ),
    )
with _hero_r:
    st.info(
        "**Quick timeline**  \n"
        "**1892** — Founded as Lynn's second high school, Essex Street campus  \n"
        "**1916** — Wheeler & Johnson addition  \n"
        "**1924** — Fire destroys the 1892 building · same-year rebuild  \n"
        "**1931** — Current Goodridge Street campus opens  \n"
        "**1934** — Lincoln Foyer statue donated; alumni parade saves the LEHS name  \n"
        "**1940s–50s** — Tom Whelan era (faculty + alumnus, MLB Boston Braves)  \n"
        "**1986** — Old Essex Street building added to National Register  \n"
        "**Today** — Largest school in Lynn Public Schools"
    )

st.divider()

# ---------------------------------------------------------------------------
# Tabs — five chapters
# ---------------------------------------------------------------------------

(
    _tab_origins,
    _tab_fire,
    _tab_today,
    _tab_alumni,
    _tab_leadership,
    _tab_civic,
) = st.tabs([
    "Origins (1892–1923)",
    "The 1924 fire & rebuild",
    "Today's campus (1931–present)",
    "Notable alumni & faculty",
    "Leadership",
    "Lynn as a school city",
])

# --- Tab 1: Origins ---------------------------------------------------------
with _tab_origins:
    st.subheader("Founding and the first Essex Street building")
    st.markdown(
        """
**Lynn English High School opened in 1892** as the city's second high
school. The decision split the public-high-school pipeline that had
run through a single building since 1850: an academic stream became
Lynn Classical High; a more practical, English-language stream became
Lynn English. The two schools have been twinned ever since — same
city, same district, same Thanksgiving football rivalry that's now
more than a century old.

**The first English campus stood at 498 Essex Street**, directly
across Liberty Street from the original 1850–51 Lynn High School. The
building was a Romanesque brick design by the firm **Wheeler &
Northend**, the same Boston-area firm responsible for several other
late-19th-century New England school buildings. As the city grew and
high-school enrollment grew faster, the original building proved too
small almost immediately.
        """
    )

    st.subheader("The 1916 James Street addition")
    st.markdown(
        """
By the mid-1910s the school had outgrown Wheeler & Northend's
footprint. **In 1916 a James Street–facing addition by Wheeler &
Johnson** was opened — same architectural lineage, expanded
capacity. The expanded school served Lynn through the rest of the
1910s and into the early 1920s — peak years for Lynn's
shoe-manufacturing industry and a high-water mark for the city's
population and tax base.
        """
    )

    st.subheader("City context — Lynn at the turn of the century")
    st.markdown(
        """
A school doesn't open in a vacuum. **Lynn was founded in 1629** —
the **fifth-oldest city in Massachusetts** — and by the late 1800s
was a regional industrial power, mainly through shoes. The city's
population grew on the back of waves of immigration: Irish, then
Italian, then French-Canadian — each wave passing through Lynn's
public schools. **GE Lynn River Works** (jet engines) would later
become the city's other anchor employer.

The original Essex Street campus was, in other words, built to
educate the children of a manufacturing city at the peak of its
manufacturing era. That history shows up later in this dashboard
indirectly — in the city demographics, in the wave of immigration
that follows in the 20th and 21st centuries, and in the dynamics
the **[English Learners](/ELL_Pipeline)** page is built around.
        """
    )

# --- Tab 2: The 1924 fire & rebuild ----------------------------------------
with _tab_fire:
    st.subheader("March 29, 1924 — the fire")
    st.markdown(
        """
On **March 29, 1924**, a major fire destroyed the original 1892
Wheeler & Northend portion of Lynn English. The 1916 addition
survived; the heart of the school did not. **One Lynn firefighter
was killed in the response.**

This was, by any standard, a civic disaster. Lynn was in the middle
of a school year; the building it had spent thirty years filling had
just become a ruin; and the public-school district had to decide,
fast, whether to relocate students or rebuild on the same site.
        """
    )

    st.subheader("Same-year rebuild")
    st.markdown(
        """
The decision was to rebuild — and rebuild quickly. **The new building
was designed by George A. Cornet** as a T-shaped three-story
**Jacobethan** structure (a revival style blending late-Gothic and
Tudor elements that was popular for American school buildings of the
period). **The post-fire rebuild was completed later in the same
calendar year (1924)** so classes could resume on the same site
without losing more than a few months.

This second Essex Street English — the 1916 addition plus Cornet's
1924 rebuild — served as Lynn English's home through **1932**, when
the school relocated to its current Goodridge Street campus (next
tab). The Essex Street building was then converted to a junior high
school, then sat vacant (documented as such in 1985), and was
eventually adapted into residential units.
        """
    )

    st.subheader("National Register listing")
    st.markdown(
        """
On **September 11, 1986**, the old Essex Street building was added to
the **National Register of Historic Places** — recognizing its
significance as both a 19th-century educational building and an
example of the institutional civic architecture of post-fire Lynn.
The listing covers the Cornet-rebuild fabric layered over the
surviving 1916 Wheeler & Johnson addition. Today the building stands
as residential housing on Essex Street, but its civic identity
lives on through the National Register designation.
        """
    )

# --- Tab 3: Today's campus -------------------------------------------------
with _tab_today:
    st.subheader("1931 — the move to Goodridge Street")
    st.markdown(
        """
**The current Lynn English campus opened on Goodridge Street in
East Lynn in 1931** — a **Classical Revival** design, distinct in
style from both Wheeler & Northend's Romanesque original and Cornet's
post-fire Jacobethan rebuild. Construction cost **\\$1.8 million in
1931 dollars** — roughly \\$36 million in today's money.

The new campus moved the school out of downtown's Essex Street
corridor and into the East Lynn residential neighborhood where it
still sits. The 1931 building remains the recognizable face of the
school — the photograph above is its main entrance.
        """
    )

    st.subheader("The Lincoln Foyer")
    st.markdown(
        """
The ceremonial entrance to the 1931 building is the **Lincoln
Foyer** — built around a **life-sized statue of Abraham Lincoln
donated by the class of 1934**. The statue and the foyer it anchors
are the school's institutional touchstone: graduating classes,
alumni events, and yearbook traditions have circled around it for
nearly a century.
        """
    )

    st.subheader("The 1934 name parade")
    st.markdown(
        """
Not long after the new campus opened, a movement formed to rename
the school **"Eastern Senior High"** — reflecting its East Lynn
location and a citywide push to standardize school-naming
conventions. The proposal was beaten back when **LEHS alumni
organized a parade of 2,000+ people** through the city in defense of
the Lynn English name.

The parade is the kind of small civic event that ends up in a
school's institutional self-image for generations. It's also a
clean window into how Lynn English alumni networks operate — the
same kind of energy that, decades later, would build out the Hall
of Fame and Whelan Family Scholarship the **[Athletics](/Athletics)**
page documents.
        """
    )

    st.subheader("Today")
    st.markdown(
        """
LEHS is today **the largest school in Lynn Public Schools** by
enrollment — about 1,700 students per the latest school year. The
1931 building still anchors the campus, with the Lincoln Foyer
still serving as the ceremonial entrance, the parade story still
in institutional memory, and the rivalry game with Lynn Classical
still played every Thanksgiving on **Manning Bowl** — see the
**[Athletics](/Athletics)** page for that thread.
        """
    )

# --- Tab 4: Notable alumni & faculty ----------------------------------------
with _tab_alumni:
    st.markdown(
        "A few of the people LEHS has graduated or employed over the past "
        "130 years. The full Hall of Fame and the season-by-season athletics "
        "history live on **[Athletics](/Athletics)** — this is the short list "
        "that doubles as institutional history."
    )

    st.subheader("🎓 Tom Whelan — faculty *and* alumnus")
    st.markdown(
        """
The most LEHS-specific name on this list. **Tom Whelan** was an
infielder for the **Boston Braves in 1920** — and, in the same
year, played football for the **Canton Bulldogs** alongside Jim
Thorpe. He was one of the country's earliest two-sport professional
athletes.

He then came home. Through the **1940s–50s** Whelan taught at LEHS,
coached baseball, served as athletic director, and eventually as
principal. The **Whelan Family Scholarship** at LEHS is named for him
and remains active.
        """
    )

    st.subheader("⚾ Major-league baseball")
    st.markdown(
        """
- **Jim Hegan** (class of **1938**) — Quarterback at LEHS during the
  early Manning Bowl years, then a **17-year MLB career as a catcher
  (1941–1960)**. **Five-time All-Star** (1947, '49, '50, '51, '52).
  **1948 World Series champion** with the Cleveland Indians.
  Widely considered one of the best defensive catchers of his era —
  caught **four no-hitters**. Later a long-tenured Yankees coach.
- **Bump Hadley** (1920s) — Right-handed pitcher; 16 MLB seasons,
  three World Series titles with the Yankees in the 1930s.
- **Les Burke** — Infielder, Detroit Tigers, 1920s.
- **Mike Pazik** — Quarterback at LEHS, then a pitcher with the
  Minnesota Twins in the mid-1970s. Son of LEHS football alum
  Henry Pazik, who scored the first touchdown ever at Manning Bowl
  in 1937.
- **Ben Bowden** (class of **2013**) — Left-handed pitcher;
  Vanderbilt commit out of LEHS; reached the majors with the
  **Colorado Rockies in 2021**.
        """
    )

    st.subheader("🏀 Basketball & beyond")
    st.markdown(
        """
- **Anthony Anderson** (class of **2000**) — LEHS Hall of Fame
  class of 2024. Played at **UMass Amherst** (Atlantic 10 Rookie of
  the Year, 2002); the program's second-best all-time three-point
  shooter. Pro career in the ABA, PBL, and NBL Canada — **NBL Canada
  all-time leading scorer**; **2014 league MVP**.
- **Antonio Anderson** (Anthony's younger brother) — Started at LEHS
  before transferring to Lynn Tech. Played at **Memphis** under John
  Calipari; **Conference USA Defensive Player of the Year 2009**.
  Multiple 10-day contracts with the **Oklahoma City Thunder** in
  2010. Returned home as LEHS boys-basketball head coach
  **2017–2021** — back-to-back state titles in **2019 and 2020**.
        """
    )

    st.subheader("🎵 Music · 🎬 Acting · 🎓 Academia")
    st.markdown(
        """
- **Sib Hashian** — Drummer for the rock band **Boston**; performed
  on the band's self-titled **1976 debut**, one of the best-selling
  debut albums of all time.
- **Jack Noseworthy** (class of **1982**) — Film and TV actor;
  *Event Horizon*, *S.W.A.T.*, *Killing Kennedy*, Broadway and
  off-Broadway credits.
- **John A. Curry** (class of **1951**) — Served as **president of
  Northeastern University**.
- **John J. Donovan** (class of **1959**) — MIT professor and
  entrepreneur; founder of multiple software companies in the
  Cambridge tech ecosystem.
        """
    )

    st.subheader("👩 Women who made LEHS history")
    st.markdown(
        """
- **Ashley Aldred** — Named LEHS Athletic Director in **July 2025**,
  making her **the first female AD in the City of Lynn**. Arlington
  native; played college softball at **Salem State**. Joined LEHS
  as varsity softball head coach in 2019 and was named *The Lynn
  Item*'s **Coach of the Year in 2023** after leading the Bulldogs
  softball team to its first postseason appearance since 1999.

- **Michelle Fabian Ennis** (class of **1984**) — Multi-sport athlete
  in soccer, basketball, and softball; **LEHS Hall of Fame class of
  2024**. The 2024 induction class was unusually deep in women from
  the class of 1984 — **Alisa Fila** and **Martha Jamieson** were
  both inducted the same night, alongside **Deidre (Jackson) Roper**
  (class of 1995) and **Kara (Lunden) Migliozzi** (also class of
  1995).

- **The Conlon family** — **LEHS Hall of Fame class of 2013**, a
  collective induction recognizing six members across soccer and
  swimming. Four of the six honored were women: **Diane Conlon**,
  **Marianne (Conlon) Duncan**, **Melissa (Conlon) McElaney**, and
  (posthumously) **Michelle Conlon**. The all-time deepest single-
  family contribution to LEHS girls' athletics.

- **Christine Pierce** (class of **1978**) — Hall of Fame class of
  **2019**. Inducted alongside **Joyce Knappe** the same year.

- **Dr. Miriam Morse · Carol Ruggiero · Francie Sudak** — Three of
  the women named in the **Hall of Fame class of 2013** alongside
  the Conlon family — one of the largest single induction classes
  in LEHS history.

- **Dina Wavezwa** (class of **1992**) — Current **head coach of
  LEHS boys basketball** (since April 2025). Grew up in the Meadows
  neighborhood across the street from the school. Was an assistant
  under **Antonio Anderson** on the 2019–2020 back-to-back MA
  Division 1 state-championship staffs.

- **Stephanie Vasquez** — Current **head coach of LEHS girls
  basketball** (2026–). Coaching path through St. Mary's Middle
  School, KIPP Academy, a prior stint as a LEHS assistant under
  **Rachael Bradley** in 2014, Essex Tech, and Salem State.
        """
    )

    st.caption(
        "Listed here as the institutional short list, not a complete index. "
        "The **[Athletics](/Athletics)** page carries the full Hall of "
        "Fame, season records, championship history, and the curated "
        "history file the names above are sourced from."
    )

# --- Tab 5: Leadership ------------------------------------------------------
with _tab_leadership:
    st.subheader("Current principal")
    _p_l, _p_r = st.columns([1, 4], gap="medium")
    with _p_l:
        st.image(str(IMAGES_DIR / "principal-rardy-pena.jpg"), width=140)
    with _p_r:
        st.markdown(
            "**Dr. Rardy Peña** is the principal of Lynn English High School. "
            "The data on the rest of this dashboard tells a story about "
            "students, demographics, and outcomes — the people leading the "
            "school's response to that story matter just as much."
        )

    st.subheader("Recent principals — short list")
    st.markdown(
        """
- **Dr. Rardy Peña** — current principal (see above).
- **Tessie Mower** — interim principal beginning **July 1, 2020**.
  An **LEHS alumna** who served as a longtime English Department
  head at the school before stepping into the principalship; came
  to the interim role from the vice principal seat at Lynn Classical.
  Mower started her LPS teaching career in **1994**, making her one
  of the longest-tenured Lynn Public Schools educators to lead LEHS.
        """
    )

    st.subheader("Historical leadership note")
    st.markdown(
        "The most historically significant LEHS leader was **Tom Whelan**, "
        "who served as teacher, baseball coach, athletic director, and "
        "eventually principal through the **1940s–50s** — the same Tom "
        "Whelan who'd played MLB for the Boston Braves in 1920 and "
        "professional football alongside Jim Thorpe on the Canton Bulldogs "
        "in 1919–20. The **Whelan Family Scholarship** at LEHS is named "
        "for him and remains active. See the **Notable alumni & faculty** "
        "tab for the full Whelan write-up."
    )

# --- Tab 6: Lynn as a school city ------------------------------------------
with _tab_civic:
    st.subheader("The district around LEHS")
    st.markdown(
        """
LEHS doesn't exist alone in Lynn. **Lynn Public Schools (LPS)** as
of June 2024 enrolled **17,447 students across 27 schools**. The
five LPS public high schools, in order of size:

- **Lynn English** (9–12) — the focus of this dashboard. Largest.
- **Lynn Vocational & Technical Institute (LVTI / Lynn Tech)** (8–12)
- **Lynn Classical** (9–12) — sister school, the Thanksgiving rival
- **Frederick Douglass Collegiate Academy** at North Shore
  Community College (9–12, opened Fall 2022)
- **Fecteau-Leary Junior/Senior High School** (7–12)

For the comparative view across these five schools, see the
**[Lynn Schools](/Lynn_Schools)** page; for the full district context
(including all 22 elementary and middle feeders), see
**[Lynn District](/Lynn_District)**.
        """
    )

    st.subheader("Three district moments that shaped LEHS")
    st.markdown(
        """
- **~2011 — the refugee wave.** The UN High Commission for Refugees
  relocated families to Lynn from many countries during this period,
  sharply increasing the district's English Learner population.
  LEHS, as the largest LPS high school, absorbed the bulk of that
  increase at the secondary level. The
  **[English Learners](/ELL_Pipeline)** page is built around the
  long arc of that demographic shift at LEHS specifically.
- **2017 — the middle-school ballot.** Lynn voters rejected a
  ballot proposal to fund two new middle schools. The decision
  shaped capacity planning across the district through the 2020s.
- **2018 — district leadership.** **Dr. Patrick Tutwiler** became
  LPS's first Black superintendent; instituted free meals and a
  set of district-wide Operating Protocols during his tenure.
  Resigned in summer 2022.
        """
    )

    st.subheader("Why LEHS is the dashboard's center of gravity")
    st.markdown(
        """
This dashboard is named for LEHS but it talks about Lynn, the
district, and 26 MA Gateway cities. **The reason LEHS sits in the
middle is straightforward:** the school is large enough that its
demographic and outcome numbers move with the district's overall
fortunes, but it's still one building with one principal — so
school-level effects are visible. Lynn Classical is the closest
direct comparison; the 26 other Gateway-city high schools are the
broader peer group. The **[Lynn Schools](/Lynn_Schools)** and
**[Gateway Cities](/Gateway_Peer_Comparison)** pages are where
those comparisons live.
        """
    )

# ---------------------------------------------------------------------------
# Footer — pointer back to the data
# ---------------------------------------------------------------------------

st.divider()

_f_l, _f_r = st.columns([3, 1], gap="medium")
with _f_l:
    st.markdown("#### 📊 The numbers behind the story")
    st.caption(
        "Demographics, enrollment trends, attendance, grade-level breakdowns, "
        "and the long arc since 1992 live on School Profile. The history "
        "above is meant to sit next to the data, not replace it."
    )
with _f_r:
    st.write("")
    st.page_link(
        "pages/1_School_Profile.py",
        label="Open School Profile →",
        use_container_width=True,
    )
