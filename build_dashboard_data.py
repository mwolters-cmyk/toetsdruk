#!/usr/bin/env python3
"""Aggregeert output/*.json tot dashboard/data/toetsdruk.json voor de Toetsdruk Monitor."""

import json
import os
import re
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
DASHBOARD_DATA_DIR = BASE_DIR / "docs" / "data"

# Schoolkalender 2025-2026
MODULE_WEEKS = {
    1: list(range(36, 49)),                          # wk 36-48
    2: list(range(49, 53)) + list(range(1, 12)),     # wk 49-52 + 1-11
    3: list(range(12, 27)),                           # wk 12-26
    # Klas 6: modules 4-5 vallen in dezelfde periodes als 1-2
    4: list(range(36, 49)),                          # = module 1
    5: list(range(49, 53)) + list(range(1, 12)),     # = module 2
}
TOETSWEEK_WEEKS = [47, 48, 10, 11, 25, 26]
VAKANTIE_WEEKS = [43, 52, 1, 8, 18, 19]

# Onderbouw locatie-indeling: A-F = Socrates, G-Q = Athena
SOCRATES_LETTERS = set("ABCDEF")

# Keywords voor herclassificatie naar "oefentoets" (niet-meetellend, getoond als "Oef")
# Check 1: exacte substring-match in beschrijving+stof
OEFENTOETS_KEYWORDS = [
    "oefentoets", "oefenproefwerk", "oefenpractice",
    "oefenuso", "oefen-po", "oefenpo", "oefenvertaling",
    "oefensessie", "oefenopgave", "oefenvragen",
    "diagnostisch", "diagnostic",
    "d-toets", "nulmeting", "formatief",
    "practice test", "practice exam", "exam practice",
    "test practice", "practice essay",
    "practice writing", "writing practice",
    "practice listening", "listening practice",
    "practice speaking", "speaking practice",
    "practice cito",
    "proeftoets",
]
# Check 2: regex — beschrijving BEGINT met "oefen" (vangt oefenUSO, oefenPO, etc.)
OEFENTOETS_PREFIX_RE = re.compile(r"^oefen", re.IGNORECASE)

# Docentcode → vak mapping (bron: "Overzicht collega's 2025-2026" + bestandsanalyse)
# kt = Klassieke Talen → standaard "Latijn", code corrigeert naar Grieks op basis van beschrijving
DOCENT_VAK = {
    # A
    "AAL": "Wiskunde", "ABO": "Latijn", "AJE": "Kunst - BV",
    "AOU": "Informatica", "ASK": "Lichamelijke opvoeding",
    "AST": "Latijn", "AUS": "Muziek", "AVP": "Geschiedenis",
    # B
    "BAR": "Wiskunde", "BLE": "Lichamelijke opvoeding",
    "BML": "Natuurkunde", "BNG": "Geschiedenis", "BOO": "Latijn",
    "BOS": "Kunst - BV", "BRD": "Geschiedenis", "BRM": "Nederlands",
    "BVW": "Filosofie",
    # C
    "CGI": "Nederlands", "CLC": "Frans", "COL": "Aardrijkskunde",
    # D
    "DBA": "Latijn", "DDP": "Nederlands", "DHE": "Duits",
    "DJK": "Muziek", "DKO": "Latijn", "DWB": "Scheikunde",
    # E
    "EBE": "Drama", "ECK": "Latijn", "EDH": "Nederlands",
    "ENS": "Duits", "ESC": "Drama", "EVH": "Economie",
    # F
    "FER": "Natuurkunde", "FPE": "Biologie", "FRA": "Economie",
    # G
    "GDR": "Wiskunde", "GES": "Geschiedenis", "GIR": "Aardrijkskunde",
    "GRN": "Muziek", "GRV": "Frans", "GST": "Latijn",
    "GVN": "Lichamelijke opvoeding",
    # H
    "HDE": "Duits", "HEI": "Latijn", "HGV": "Biologie",
    "HKT": "Maatschappijleer", "HNS": "Geschiedenis",
    "HPR": "Wiskunde", "HSC": "Wiskunde", "HTA": "Engels",
    "HUI": "Latijn", "HVL": "Latijn",
    # I
    "IST": "Engels",
    # J
    "JCB": "Biologie", "JJO": "Wiskunde", "JNG": "Engels",
    "JST": "Engels", "JVZ": "Engels", "JWI": "Frans",
    # K
    "KAS": "Latijn", "KFM": "Frans", "KHL": "Duits",
    "KNA": "Biologie", "KOM": "Wiskunde", "KUA": "Kunst - BV",
    # L
    "LIE": "Natuurkunde", "LIN": "Engels", "LJA": "Latijn",
    "LNS": "Engels", "LSK": "Nederlands", "LVL": "Nederlands",
    "LWN": "Aardrijkskunde",
    # M
    "MER": "Scheikunde", "MHA": "Engels", "MKP": "Scheikunde",
    "MNT": "Natuurkunde", "MRA": "Duits", "MRL": "Frans",
    "MSM": "Natuurkunde", "MSS": "Latijn", "MVI": "Wiskunde",
    # N
    "NBL": "Nederlands", "NBR": "Wiskunde", "NHE": "Drama",
    "NVM": "Nederlands", "NVS": "Nederlands",
    # O
    "OJN": "Engels", "OST": "Natuurkunde",
    # P
    "PHN": "Frans", "PON": "Economie",
    # R
    "RBO": "Drama", "RBR": "Biologie", "RDR": "Wiskunde",
    "RET": "Engels", "RJO": "Wiskunde", "RNP": "Wiskunde",
    "ROE": "Latijn", "ROS": "Geschiedenis", "ROZ": "Economie",
    "RTE": "Biologie", "RTP": "Geschiedenis", "RVD": "Latijn",
    "RWA": "Aardrijkskunde",
    # S
    "SAH": "Aardrijkskunde", "SBU": "Nederlands", "SCB": "Latijn",
    "SCM": "Latijn", "SDC": "Muziek", "SDR": "Lichamelijke opvoeding",
    "SFL": "Frans", "SGL": "Muziek", "SIS": "Aardrijkskunde",
    "SMI": "Scheikunde", "SMK": "Kunst - BV", "SON": "Kunst - BV",
    # T
    "TCM": "Latijn", "TIN": "Duits", "TMS": "Kunst - BV",
    "TSL": "Maatschappijleer", "TVL": "Latijn", "TVS": "Economie",
    # V
    "VHL": "Kunst - BV", "VHN": "Geschiedenis", "VIN": "Lichamelijke opvoeding",
    "VKO": "Kunst - BV", "VLK": "Filosofie", "VLT": "Biologie",
    "VRL": "Wiskunde", "VRT": "Scheikunde",
    # W
    "WAG": "Natuurkunde", "WIT": "Lichamelijke opvoeding",
    "WLT": "Wiskunde", "WNS": "Latijn", "WRN": "Lichamelijke opvoeding",
    # Z
    "ZAN": "Natuurkunde", "ZEE": "Economie", "ZIL": "Latijn",
    "ZRN": "Natuurkunde", "ZVN": "Latijn",
}


# Handmatige overrides voor bestanden die niet automatisch gedetecteerd kunnen worden
# Key: (deel van) bestandsnaam (lowercase), Value: vaknaam
MANUAL_OVERRIDES = {
    "studiewijzer klas 3 gh module 2 25-26": "Wiskunde",  # Goudriaan (GDR)
    "sw k3m1 25-26": "Biologie",  # Centrale Bio studiewijzer klas 3
}


def classify_locatie(klas: str) -> str:
    """Bepaal locatie op basis van klasletter. A-F=Socrates, G+=Athena."""
    letter = klas[-1].upper() if klas else ""
    return "Socrates" if letter in SOCRATES_LETTERS else "Athena"

# Vaknaam-afkortingen voor compacte weergave in dashboard
VAK_AFKORTINGEN = {
    "Nederlands": "Ne", "Engels": "En", "Frans": "Fr", "Duits": "Du",
    "Wiskunde": "Wi", "Biologie": "Bi", "Natuurkunde": "Na", "Scheikunde": "Sk",
    "Geschiedenis": "Gs", "Aardrijkskunde": "Ak",
    "Latijn": "La", "Grieks": "Gr", "Filosofie": "Fi",
    "Economie": "Ec", "Informatica": "In",
    "Kunst - BV": "KuBV", "Kunst - MU": "KuMU", "Kunst - DR": "KuDR",
    "Muziek": "Mu", "Drama": "Dr", "Techniek": "Te",
    "Lichamelijke opvoeding": "LO", "Godsdienst": "Go",
    "Mens en maatschappij": "M&M", "Mens en natuur": "M&N",
    "Rekenen": "Re",
    "Onbekend": "??",
}

# Toetstype afkortingen
TYPE_AFKORTINGEN = {
    "proefwerk": "PW", "so": "SO", "uso": "USO", "po": "PO",
    "mondeling": "MO", "presentatie": "PR", "portfolio": "PF",
    "handelingsdeel": "HD", "oefentoets": "Oef", "anders": "?",
    # Veelvoorkomende LLM-typos
    "handleingsdeel": "HD", "handleiding": "HD",
}


MAANDEN_NL = ["jan", "feb", "mrt", "apr", "mei", "jun",
              "jul", "aug", "sep", "okt", "nov", "dec"]

def week_label(week_nr: int) -> str:
    """Geeft maandag-datum als label voor een ISO weeknummer (schooljaar 2025-2026)."""
    year = 2025 if week_nr >= 36 else 2026
    monday = datetime.strptime(f"{year}-W{week_nr:02d}-1", "%G-W%V-%u")
    return f"{monday.day} {MAANDEN_NL[monday.month - 1]}"


def load_all_json() -> list[dict]:
    """Laadt alle studiewijzer-JSONs uit output/."""
    results = []
    for json_path in OUTPUT_DIR.rglob("*.json"):
        if json_path.parent == OUTPUT_DIR:
            continue  # Skip summary.json etc.
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            if "metadata" in data and "toetsen" in data:
                results.append(data)
        except (json.JSONDecodeError, KeyError):
            pass
    return results


def vak_kort(vak: str | None) -> str:
    """Verkort vaknaam voor dashboard-weergave."""
    if not vak:
        return "?"
    if vak in VAK_AFKORTINGEN:
        return VAK_AFKORTINGEN[vak]
    for lang, kort in VAK_AFKORTINGEN.items():
        if vak.lower().startswith(lang.lower()[:4]):
            return kort
    return vak[:4]


def type_kort(toets_type: str) -> str:
    """Verkort toetstype."""
    return TYPE_AFKORTINGEN.get(toets_type, toets_type.upper()[:3])


def detect_vak_from_override(bron: str) -> str | None:
    """Check handmatige overrides voor ondetecteerbare bestanden."""
    name = os.path.splitext(os.path.basename(bron))[0].lower()
    for pattern, vak in MANUAL_OVERRIDES.items():
        if pattern in name:
            return vak
    return None


def detect_vak_from_filename(bron: str) -> str | None:
    """Detecteer vak uit bestandsnaam als metadata.vak ontbreekt."""
    name = unicodedata.normalize("NFC", bron.lower())
    patterns = {
        "Nederlands": ["nederland", "1ne ", "2ne ", "3ne ", " ne ", "_ne_", "ned ",
                        "planner 1ne", "planner 2ne", "planner 3ne", "leesles"],
        "Engels": ["english", "engels", " eng ", "englsh"],
        "Frans": ["français", "francais", "fran ", "planning fa ", "planning période",
                  "planning periode", " fa p"],
        "Duits": ["deutsch", "duits", " du ", "2k m2 2526", "2m m2 2526"],
        "Wiskunde": ["wiskunde", " wi ", "wis "],
        "Rekenen": ["rekenen", "rekenlessen"],
        "Biologie": ["biologie", "bio ", "k3m1 biologie", "k3m2"],
        "Natuurkunde": ["natuurkunde", "nask", "elektriciteit", "kracht en beweging",
                        "warmte", "geluid", "licht fer"],
        "Scheikunde": ["scheikunde", " sk ", "verbranding"],
        "Geschiedenis": ["geschiedenis", "geschied", " ges ", "gesbng", "gsbng",
                         "fascisme", "planner ges", " gs ", "samos"],
        "Aardrijkskunde": ["aardrijkskunde", " ak "],
        "Latijn": ["latijn", "_la_", " la ", "1la ", "2la ", "3la ",
                   "1la_", "2la_", "3la_", "lagr"],
        "Grieks": ["grieks", "_gr_", " gr ", "1gr ", "2gr ", "3gr ",
                   "1gr_", "2gr_", "3gr_"],
        "Economie": ["economie", " ec "],
        "Kunst - BV": ["beeldende", " bv ", "portret", "maskers", "linoleum",
                       "waarneming tekenen", "druktechniek", "tekenen en schilderen"],
        "Muziek": ["muziek", "begrippenlijst klas 1 periode 2 met audio"],
        "Drama": ["drama"],
        "Filosofie": ["filosofie"],
        "Lichamelijke opvoeding": ["lichamelijke", " lo "],
        "Informatica": ["informatica"],
    }
    for vak, keywords in patterns.items():
        for kw in keywords:
            if kw in name:
                return vak
    return None


def detect_vak_from_docentcode(bron: str) -> str | None:
    """Detecteer vak via docentcode (3-4 hoofdletters) in bestandsnaam."""
    name = os.path.splitext(os.path.basename(bron))[0]
    # Zoek 3-4 letter uppercase codes op logische posities
    candidates = re.findall(r'(?:^|[\s_\-])([A-Z]{3,4})(?:[\s_\-.]|$)', name)
    end_match = re.search(r'[^A-Z]([A-Z]{3,4})$', name)
    if end_match:
        candidates.append(end_match.group(1))
    for code in candidates:
        if code in DOCENT_VAK:
            return DOCENT_VAK[code]
    return None


def detect_vak_from_beschrijving(beschrijving: str) -> str | None:
    """Detecteer vak uit toetsbeschrijving als laatste fallback.

    Twee lagen: eerst vakspecifieke termen, dan vaknamen letterlijk in de tekst.
    """
    desc = unicodedata.normalize("NFC", beschrijving.lower())

    # Laag 1: vakspecifieke termen (hoge betrouwbaarheid)
    specifieke_patterns = {
        "Frans": ["vocabulaire", "grammaire", "verbe", "unité", "leçon",
                  "écriture", "écrit", "production écrite"],
        "Duits": ["grammatik", "kapitel", "vokabel", "prüfung", "hörverstehen",
                  "leseverstehen", "haustier", "restaurantspiel", "berühmtheiten",
                  "lesefertigkeit", "haben/sein/werden", "ergänze"],
        "Wiskunde": ["haakjes", "herleiden", "breuken met letters", "cirkels",
                     "middelloodlijn", "zwaartelijnen", "hoogtelijnen",
                     "oppervlakte driehoek", "procenten", "evenwijdige lijnen",
                     "exceltoets"],
        "Scheikunde": ["verbranding en ademhaling"],
        "Aardrijkskunde": ["himalaya", "croquis", "demografie", "croquisatlas",
                           "moesson", "verstedelijking", "malediven"],
        "Nederlands": ["leesles", "fictie en werkelijkheid", "vermaken en ontroeren",
                       "taal en identiteit", "opvallend schrijven"],
        "Geschiedenis": ["franse revolutie", "staten-generaal", "rechtszaak",
                         "samos", "egypte", "en bronnen"],
        "Kunst - BV": ["knutsel"],
        "Latijn": ["godenopdracht", "verbuigingsgroep", "grammatica les",
                   "woorden les", "tekst 44", "tekst 43"],
    }
    for vak, keywords in specifieke_patterns.items():
        for kw in keywords:
            if kw in desc:
                return vak

    # Laag 2: vaknaam letterlijk in beschrijving (catch-all voor generieke bestanden)
    vaknaam_patterns = {
        "Nederlands": "nederlands",
        "Engels": "engels",
        "Frans": "frans",
        "Duits": "duits",
        "Wiskunde": "wiskunde",
        "Biologie": "biologie",
        "Natuurkunde": "natuurkunde",
        "Scheikunde": "scheikunde",
        "Geschiedenis": "geschiedenis",
        "Aardrijkskunde": "aardrijkskunde",
        "Latijn": "latijn",
        "Grieks": "grieks",
        "Economie": "economie",
        "Filosofie": "filosofie",
        "Informatica": "informatica",
        "Muziek": "muziek",
        "Drama": "drama",
    }
    for vak, vaknaam in vaknaam_patterns.items():
        if vaknaam in desc:
            return vak

    return None


def build_data():
    """Bouwt het dashboard databestand."""
    all_files = load_all_json()
    print(f"Geladen: {len(all_files)} studiewijzer-JSONs")

    # Verzamel toetsen per klas per week
    # Structuur: klas -> week -> [(vak, type, beschrijving, stof)]
    klas_toetsen = defaultdict(lambda: defaultdict(list))

    # Deduplicatie: track (klas, week, vak, type) om duplicaten te voorkomen
    seen = set()
    # Track (klas, week, type) met bekend vak — voorkomt dat Onbekend-dubbelen verschijnen
    seen_known = set()

    # Sorteer: bestanden met bekend vak eerst, zodat dedup Onbekend-dubbelen onderdrukt
    all_files.sort(key=lambda d: (d["metadata"].get("vak") is None, d.get("bron_bestand", "")))

    for doc in all_files:
        meta = doc["metadata"]
        klas = meta.get("klas", "")
        leerjaar = meta.get("leerjaar")
        if not klas or not leerjaar or leerjaar > 3:
            continue  # Alleen onderbouw

        # Bepaal vak op bestandsniveau (eenmalig per document)
        bron = doc.get("bron_bestand", "")
        file_vak = (meta.get("vak")
                    or detect_vak_from_override(bron)
                    or detect_vak_from_filename(bron)
                    or detect_vak_from_docentcode(bron))

        # Als bestandsniveau geen vak oplevert: probeer alle beschrijvingen
        # in het bestand. Als meerdere toetsen hetzelfde vak aanwijzen, gebruik dat.
        if not file_vak:
            detected_vaks = set()
            for t in doc.get("toetsen", []):
                combo = ((t.get("beschrijving") or "") + " " +
                         (t.get("stof") or "")).strip()
                v = detect_vak_from_beschrijving(combo)
                if v:
                    detected_vaks.add(v)
            if len(detected_vaks) == 1:
                file_vak = detected_vaks.pop()

        for toets in doc.get("toetsen", []):
            if not isinstance(toets, dict):
                continue
            # Filter: proefwerkweek-toetsen uitsluiten
            if toets.get("in_toetsweek", False):
                continue

            # Filter: herkansingen uitsluiten (geen reguliere toetsdruk)
            beschrijving = (toets.get("beschrijving") or "").lower()
            if any(kw in beschrijving for kw in [
                "herkans", "resit", "rattrapage", "repêchage", "rep\u00eachage",
            ]):
                continue

            week = toets.get("week")
            if not week:
                continue

            # Combineer beschrijving + stof voor bredere detectie
            beschrijving_plus = ((toets.get("beschrijving") or "") + " " +
                                 (toets.get("stof") or "")).strip()
            vak = (file_vak
                   or detect_vak_from_beschrijving(beschrijving_plus)
                   or "Onbekend")
            # Normaliseer wiskunde-varianten (Wiskunde A/B/C/D → Wiskunde)
            if "iskunde" in vak.lower() or vak.lower() == "wiskunde":
                vak = "Wiskunde"
            # Gecombineerde studiewijzers: Latijn/Grieks-correctie
            if vak == "Latijn":
                desc_lower = beschrijving
                if "grieks" in desc_lower and "latijn" not in desc_lower:
                    vak = "Grieks"
            toets_type = toets.get("type", "anders")

            # Herclassificeer oefentoetsen/diagnostische toetsen → "oefentoets"
            desc_check = beschrijving_plus.lower()
            if any(kw in desc_check for kw in OEFENTOETS_KEYWORDS):
                toets_type = "oefentoets"
            elif OEFENTOETS_PREFIX_RE.match(beschrijving.strip()):
                toets_type = "oefentoets"
            # "quiz" apart: wel Oef, maar alleen in beschrijving (niet stof),
            # en niet als het onderdeel is van presentatie/po
            elif ("quiz" in beschrijving
                  and toets_type not in ("presentatie", "po")):
                toets_type = "oefentoets"

            dedup_key = (klas, week, vak, toets_type)

            if dedup_key in seen:
                continue

            # Onderdruk Onbekend-entries als er al een entry met bekend vak is
            # voor dezelfde (klas, week, type) — voorkomt dubbelen uit overzichtsdocumenten
            base_key = (klas, week, toets_type)
            if vak == "Onbekend" and base_key in seen_known:
                continue
            if vak != "Onbekend":
                seen_known.add(base_key)

            seen.add(dedup_key)

            klas_toetsen[klas][str(week)].append({
                "vak": vak,
                "vak_kort": vak_kort(vak),
                "type": toets_type,
                "type_kort": type_kort(toets_type),
                "beschrijving": toets.get("beschrijving", ""),
                "stof": toets.get("stof", ""),
            })

    # Sorteer toetsen per cel op vaknaam
    for klas in klas_toetsen:
        for week in klas_toetsen[klas]:
            klas_toetsen[klas][week].sort(key=lambda t: t["vak"] or "")

    # Week labels genereren
    all_weeks = list(range(36, 53)) + list(range(1, 27))
    week_labels = {}
    for w in all_weeks:
        try:
            week_labels[str(w)] = week_label(w)
        except ValueError:
            week_labels[str(w)] = f"wk{w}"

    # Dynamisch klassen detecteren per jaarlaag en locatie
    klassen_per_lj = defaultdict(lambda: {"Athena": [], "Socrates": []})
    for klas in sorted(klas_toetsen.keys()):
        lj = int(klas[0]) if klas[0].isdigit() else None
        if lj:
            loc = classify_locatie(klas)
            klassen_per_lj[lj][loc].append(klas)

    # Output structuur
    output = {
        "schooljaar": "2025-2026",
        "gegenereerd": datetime.now().isoformat(timespec="seconds"),
        "kalender": {
            "module_weken": {str(k): v for k, v in MODULE_WEEKS.items()},
            "toetsweken": TOETSWEEK_WEEKS,
            "vakanties": VAKANTIE_WEEKS,
            "week_labels": week_labels,
        },
        "klassen": {
            str(lj): locs for lj, locs in sorted(klassen_per_lj.items())
        },
        "toetsen": dict(klas_toetsen),
    }

    # Statistieken
    total_toetsen = sum(
        len(toetsen)
        for weeks in klas_toetsen.values()
        for toetsen in weeks.values()
    )
    print(f"Totaal: {total_toetsen} toetsen over {len(klas_toetsen)} klassen")
    for lj in sorted(klassen_per_lj):
        alle = klassen_per_lj[lj]["Athena"] + klassen_per_lj[lj]["Socrates"]
        n = sum(len(t) for k in alle for t in klas_toetsen.get(k, {}).values())
        print(f"  Klas {lj}: {n} toetsen ({klassen_per_lj[lj]['Athena']} Athena, {klassen_per_lj[lj]['Socrates']} Socrates)")

    # ── Bovenbouw (klas 4-6): rijen per vak, clusters samengevoegd ──────────
    bovenbouw = build_bovenbouw(all_files)
    if bovenbouw:
        output["bovenbouw"] = bovenbouw

    # Schrijf output
    DASHBOARD_DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DASHBOARD_DATA_DIR / "toetsdruk.json"
    out_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Geschreven: {out_path}")


def build_bovenbouw(all_files: list[dict]) -> dict:
    """Bovenbouw: groepeer per leerjaar → vak → week.

    Clusters worden samengevoegd: als meerdere clusters (4AK1, 4AK2) hetzelfde
    vak in dezelfde week hebben, tonen we dat 1x. Rijen = vakken, niet klassen.
    """
    # Structuur: leerjaar -> vak -> week -> [toets-entries]
    lj_data = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    seen = set()  # dedup per (leerjaar, vak, week, type)

    for doc in all_files:
        meta = doc["metadata"]
        leerjaar = meta.get("leerjaar")
        if not leerjaar or leerjaar < 4:
            continue  # Alleen bovenbouw

        bron = doc.get("bron_bestand", "")
        file_vak = (meta.get("vak")
                    or detect_vak_from_override(bron)
                    or detect_vak_from_filename(bron)
                    or detect_vak_from_docentcode(bron))

        # File-level vak inheritance
        if not file_vak:
            detected_vaks = set()
            for t in doc.get("toetsen", []):
                combo = ((t.get("beschrijving") or "") + " " +
                         (t.get("stof") or "")).strip()
                v = detect_vak_from_beschrijving(combo)
                if v:
                    detected_vaks.add(v)
            if len(detected_vaks) == 1:
                file_vak = detected_vaks.pop()

        for toets in doc.get("toetsen", []):
            if not isinstance(toets, dict):
                continue
            # Filter: alleen BUITEN toetsweek
            if toets.get("in_toetsweek", False):
                continue

            # Filter: herkansingen
            beschrijving = (toets.get("beschrijving") or "").lower()
            if any(kw in beschrijving for kw in [
                "herkans", "resit", "rattrapage", "repêchage",
            ]):
                continue

            week = toets.get("week")
            if not week:
                continue

            beschrijving_plus = ((toets.get("beschrijving") or "") + " " +
                                 (toets.get("stof") or "")).strip()
            vak = (file_vak
                   or detect_vak_from_beschrijving(beschrijving_plus)
                   or "Onbekend")

            # Bovenbouw: Wiskunde A/B/C/D zijn aparte vakken
            # (NIET samenvoegen zoals in onderbouw)

            # Latijn/Grieks correctie
            if vak == "Latijn":
                if "grieks" in beschrijving and "latijn" not in beschrijving:
                    vak = "Grieks"

            toets_type = toets.get("type", "anders")

            # Oefentoets herclassificatie (zelfde als onderbouw)
            desc_check = beschrijving_plus.lower()
            if any(kw in desc_check for kw in OEFENTOETS_KEYWORDS):
                toets_type = "oefentoets"
            elif OEFENTOETS_PREFIX_RE.match(beschrijving.strip()):
                toets_type = "oefentoets"
            elif "quiz" in beschrijving and toets_type not in ("presentatie", "po"):
                toets_type = "oefentoets"

            # Dedup: clusters samenvoegen
            dedup_key = (leerjaar, vak, week, toets_type)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            lj_data[leerjaar][vak][str(week)].append({
                "type": toets_type,
                "type_kort": type_kort(toets_type),
                "beschrijving": toets.get("beschrijving", ""),
                "stof": toets.get("stof", ""),
            })

    # Sorteer en structureer output
    result = {}
    for lj in sorted(lj_data):
        vakken = sorted(lj_data[lj].keys())
        total = sum(
            len(toetsen)
            for weeks in lj_data[lj].values()
            for toetsen in weeks.values()
        )
        print(f"  Bovenbouw klas {lj}: {total} toetsen over {len(vakken)} vakken")

        # Sorteer toetsen per week
        vak_toetsen = {}
        for vak in vakken:
            vak_toetsen[vak] = dict(lj_data[lj][vak])
            for w in vak_toetsen[vak]:
                vak_toetsen[vak][w].sort(key=lambda t: t["type"])

        result[str(lj)] = {
            "vakken": vakken,
            "toetsen": vak_toetsen,
        }

    return result


if __name__ == "__main__":
    build_data()
