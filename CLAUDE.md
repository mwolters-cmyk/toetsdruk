# Toetsdruk Monitor — Stedelijk Gymnasium Leiden

Lees altijd `vision.md` voor het volledige projectoverzicht en ontwerpbeslissingen.

## Doel

Online tool (GitHub Pages) waar collega's per jaarlaag zien welke toetsen/overhoringen/deadlines per klas per week gepland staan. Toont alleen toetsen **buiten** de proefwerkweken.

## Projectstructuur

```
Toetsdruk/
├── CLAUDE.md                    # Dit bestand
├── vision.md                    # Projectvisie & ontwerp (LEES DIT EERST)
├── standardize.py               # Studiewijzer → JSON pipeline (Claude Haiku API)
├── build_dashboard_data.py      # Aggregeert output/ → docs/data/toetsdruk.json
├── build_proefwerk_data.py      # Aggregeert output/ → docs/data/proefwerken.json (voor Woordjes Leren)
├── _extracted/                  # Bronbestanden studiewijzers (niet in git)
├── output/                      # Verwerkte JSON per studiewijzer (niet in git)
└── docs/                   # GitHub Pages site
    ├── index.html               # Hoofdpagina
    ├── style.css                # Styling (Vensters design system)
    ├── app.js                   # Heatmap rendering + filters
    ├── auth.js                  # PIN-authenticatie (zelfde PIN als Vensters)
    └── data/
        ├── toetsdruk.json       # Gegenereerd door build_dashboard_data.py
        └── proefwerken.json     # Gegenereerd door build_proefwerk_data.py
```

## Data pipeline

1. Gebruiker plaatst studiewijzers in `_extracted/{klas}/Studiewijzers/{KLAS}/Module {N}/`
2. `python standardize.py` → verwerkt naar `output/*.json` via Claude Haiku API
3. `python build_dashboard_data.py` → aggregeert naar `docs/data/toetsdruk.json`
4. Dashboard leest toetsdruk.json en toont heatmap

## Technische conventies

- Python 3.14, libraries: anthropic, python-docx, PyMuPDF, openpyxl
- API calls via Claude Haiku (claude-haiku-4-5-20251001)
- API key: `../Jaaroverstijgend wiskunde/Toetsenbank/Leerlijn/data/llm_batch/.api_key`
- Frontend: vanilla HTML/CSS/JS, geen framework, geen build stap
- Deployment: GitHub Pages uit `docs/` directory

## Schoolstructuur

- **Onderbouw (klas 1-3):** vaste klassen, locatie op basis van klasletter
  - A-F = Socrates, G-Q = Athena (dynamisch gedetecteerd uit data)
  - Klas 1: ~17 klassen (1A t/m 1Q), klas 2 en 3 iets minder
- **Bovenbouw (klas 4-6):** clustergroepen per profielvak, rijen = vakken (niet klassen)
  - Clusters (bijv. 4AK1, 4AK2) worden samengevoegd via dedup
  - Wiskunde A/B/C/D zijn aparte vakken in bovenbouw (niet samenvoegen)
  - Klas 6 gebruikt modules 4-5 (zelfde kalenderperiode als modules 1-2)
  - Geen module 6 — alleen CE's in die periode
  - Locatie-filter niet relevant voor bovenbouw
- **3 modules** per jaar, proefwerkweken: wk 47-48, 10-11, 25-26
- **Vakanties:** wk 43, 52, 1, 8, 18-19

## Scope-afbakeningen

- Proefwerken in proefwerkweken worden UITGESLOTEN (apart geregeld)
- Zwaarte/piekdruk is niet relevant — alleen wat er is, niet hoe zwaar
- Meetellende toetsen: SO, USO, PO, mondeling, presentatie, portfolio, HD
- **Oefentoetsen worden HERCLASSIFICEERD** (niet uitgefilterd): oefentoets, diagnostisch, d-toets, nulmeting, formatief, proeftoets, quiz → type "oefentoets" → getoond als "Oef" in het dashboard. Consistent voor onderbouw én bovenbouw.
- Herkansingen worden uitgefilterd (herkans, resit, rattrapage)
- LLM kan strings i.p.v. dicts in toetsenlijst retourneren → `isinstance(toets, dict)` check nodig
