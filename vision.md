# Toetsdruk Monitor — Visie & Ontwerp

## Projectdoel

Een online tool (GitHub Pages) waar collega's van het Stedelijk Gymnasium Leiden per jaarlaag kunnen zien welke toetsen, overhoringen en deadlines per klas per week gepland staan. Het doel is inzicht in de toetsdruk buiten de proefwerkweken.

**Doelgroep:** Examencommissie, sectievoorzitters, teamleiders.

## Wat de tool toont

Een heatmap/tabel met:
- **Horizontaal:** weken van de geselecteerde module
- **Verticaal:** klassen binnen een jaarlaag (max 12 rijen)
- **Per cel:** vaknaam + toetstype (bijv. "En: USO", "Wi: SO", "Ge: PO")
- **Kleurcodering:** donkerder = meer toetsen die week
- **Toetsweken:** oranje gemarkeerd, geen toetsen getoond (proefwerken vallen buiten scope)
- **Vakanties:** grijs/uitgegrijsd
- **TOTAAL-rij:** onderaan, som per week over alle zichtbare klassen

### Filters
- **Jaarlaag:** Klas 1, 2 of 3 (bovenbouw komt later)
- **Locatie:** Alle / Athena / Socrates
- **Module:** 1, 2 of 3

## Scope & afbakeningen

- **Onderbouw eerst** (klas 1-3), bovenbouw (klas 4-6 met clustergroepen) komt later
- **Proefwerken in proefwerkweken worden UITGESLOTEN** — die worden apart geregeld
- **Zwaarte/piekdruk is geen issue** — we tonen alleen wat er is, niet hoe zwaar het weegt
- **Wat telt als toets:** alles wat meetelt voor het cijfer — SO, USO, PO, mondeling, presentatie, portfolio, handelingsdeel, anders. Diagnostische toetsen en oefentoetsen tellen NIET mee.

## Schoolstructuur

### Onderbouw — vaste klassen
| Jaarlaag | Athena | Socrates |
|----------|--------|----------|
| Klas 1   | 1G, 1H, 1K, 1M | 1P, 1Q |
| Klas 2   | 2G, 2H | 2K, 2M |
| Klas 3   | 3G, 3H | 3K, 3M, 3P |

### Modules & kalender 2025-2026
| Module | Weken | Toetsweek |
|--------|-------|-----------|
| 1 | 36-48 (sep-nov 2025) | wk 47-48 |
| 2 | 49-11 (dec 2025-mrt 2026) | wk 10-11 |
| 3 | 12-26 (mrt-jun 2026) | wk 25-26 |

### Vakanties
- Herfst: wk 43
- Kerst: wk 52 + 1
- Voorjaar: wk 9
- Mei: wk 18-19

## Data pipeline

```
Gebruiker plaatst studiewijzers in _extracted/{klas}/Studiewijzers/{KLAS}/Module {N}/
    ↓
standardize.py → Claude Haiku API → output/*.json (per studiewijzer)
    ↓
build_dashboard_data.py → docs/data/toetsdruk.json (1 geaggregeerd bestand)
    ↓
docs/ (statische website op GitHub Pages)
```

### Stap 1: Studiewijzers plaatsen
Gebruiker (niet de tool, niet collega's) plaatst studiewijzer-bestanden (docx/pdf/xlsx/txt) handmatig in de juiste `_extracted/` subdirectory.

### Stap 2: standardize.py
Bestaand script. Leest alle formats, roept Claude Haiku API aan, produceert gestandaardiseerde JSON per studiewijzer in `output/`. Werkt uitstekend (552/554 bestanden succesvol op 5 maart 2026).

### Stap 3: build_dashboard_data.py
Nieuw script. Aggregeert alle output/*.json tot één `docs/data/toetsdruk.json`. Filtert toetsen met `in_toetsweek: true` eruit. Dedupliceert (max 1 toets per vak/type/week per klas).

### Stap 4: Dashboard
Statische website. Leest toetsdruk.json, toont heatmap per jaarlaag/locatie/module.

## Technische keuzes

- **Frontend:** Vanilla HTML/CSS/JS (geen framework, geen build stap)
- **Styling:** CSS variables hergebruikt van SHZG Vensters dashboard
- **Auth:** PIN-authenticatie (zelfde PIN als Vensters dashboard)
- **Deployment:** GitHub Pages, serveert uit `docs/` directory
- **Backend:** Geen. Alles is statisch. Data wordt lokaal gegenereerd en gecommit.
- **LLM:** Claude Haiku (claude-haiku-4-5-20251001) voor studiewijzer-parsing

## Projectstructuur

```
Toetsdruk/
├── CLAUDE.md                    # Projectinstructies voor Claude
├── vision.md                    # Dit document
├── standardize.py               # Studiewijzer → JSON pipeline
├── build_dashboard_data.py      # Aggregeert output/ → dashboard JSON
├── _extracted/                  # Bronbestanden studiewijzers (niet in git)
├── output/                      # Verwerkte JSON (niet in git)
└── docs/                   # GitHub Pages site
    ├── index.html
    ├── style.css
    ├── app.js
    ├── auth.js
    └── data/
        └── toetsdruk.json       # Gegenereerd door build script
```

## Bestaande data (proof of concept)

Uit module 1 & 2 zijn 592 studiewijzers verwerkt tot JSON. Deze data wordt gebruikt als proof of concept om het dashboard te bouwen en testen. Zodra module 3 studiewijzers beschikbaar zijn, draait de pipeline opnieuw en is het dashboard direct bruikbaar.

## Roadmap

1. **Nu:** Dashboard bouwen met module 1&2 data als proof of concept
2. **Bij beschikbaarheid module 3 studiewijzers:** Pipeline draaien, dashboard updaten
3. **Later:** Bovenbouw toevoegen (klas 4-6, clustergroepen, profielen)
4. **Optioneel:** Waarschuwingssysteem bij hoge toetsdruk, studiewijzer-template
