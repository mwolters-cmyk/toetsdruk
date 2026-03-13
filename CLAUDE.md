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
├── _extracted/                  # Bronbestanden studiewijzers (niet in git)
├── output/                      # Verwerkte JSON per studiewijzer (niet in git)
└── docs/                   # GitHub Pages site
    ├── index.html               # Hoofdpagina
    ├── style.css                # Styling (Vensters design system)
    ├── app.js                   # Heatmap rendering + filters
    ├── auth.js                  # PIN-authenticatie (zelfde PIN als Vensters)
    └── data/
        └── toetsdruk.json       # Gegenereerd door build_dashboard_data.py
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

- **Onderbouw (klas 1-3):** vaste klassen per locatie
  - Klas 1: 1G, 1H, 1K, 1M (Athena) + 1P, 1Q (Socrates)
  - Klas 2: 2G, 2H (Athena) + 2K, 2M (Socrates)
  - Klas 3: 3G, 3H (Athena) + 3K, 3M, 3P (Socrates)
- **Bovenbouw (klas 4-6):** later, clustergroepen per profiel
- **3 modules** per jaar, proefwerkweken: wk 47-48, 10-11, 25-26
- **Vakanties:** wk 43, 52, 1, 9, 18-19

## Scope-afbakeningen

- Proefwerken in proefwerkweken worden UITGESLOTEN (apart geregeld)
- Zwaarte/piekdruk is niet relevant — alleen wat er is, niet hoe zwaar
- Alleen meetellende toetsen: SO, USO, PO, mondeling, presentatie, portfolio, HD
- Bovenbouw komt later
