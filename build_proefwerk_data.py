#!/usr/bin/env python3
"""Extraheert proefwerkweek-stof uit output/*.json voor de Woordjes Leren tool.

Parallel pad naast build_dashboard_data.py: dat script filtert proefwerkweek-toetsen
UIT (voor het toetsdruk-dashboard), dit script houdt ze juist IN (voor oefenmateriaal).

Output: docs/data/proefwerken.json — beschikbaar via GitHub Pages.
"""

import json
import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
DATA_DIR = BASE_DIR / "docs" / "data"

# Schoolkalender 2025-2026
MODULE_WEEKS = {
    1: list(range(36, 49)),                          # wk 36-48
    2: list(range(49, 53)) + list(range(1, 12)),     # wk 49-52 + 1-11
    3: list(range(12, 27)),                           # wk 12-26
}
TOETSWEEK_WEEKS = [47, 48, 10, 11, 25, 26]

# ── Vak-detectie (gedupliceerd uit build_dashboard_data.py) ──────────────────

DOCENT_VAK = {
    "AAL": "Wiskunde", "ABO": "Latijn", "AJE": "Kunst - BV",
    "AOU": "Informatica", "ASK": "Lichamelijke opvoeding",
    "AST": "Latijn", "AUS": "Muziek", "AVP": "Geschiedenis",
    "BAR": "Wiskunde", "BLE": "Lichamelijke opvoeding",
    "BML": "Natuurkunde", "BNG": "Geschiedenis", "BOO": "Latijn",
    "BOS": "Kunst - BV", "BRD": "Geschiedenis", "BRM": "Nederlands",
    "BVW": "Filosofie",
    "CGI": "Nederlands", "CLC": "Frans", "COL": "Aardrijkskunde",
    "DBA": "Latijn", "DDP": "Nederlands", "DHE": "Duits",
    "DJK": "Muziek", "DKO": "Latijn", "DWB": "Scheikunde",
    "EBE": "Drama", "ECK": "Latijn", "EDH": "Nederlands",
    "ENS": "Duits", "ESC": "Drama", "EVH": "Economie",
    "FER": "Natuurkunde", "FPE": "Biologie", "FRA": "Economie",
    "GDR": "Wiskunde", "GES": "Geschiedenis", "GIR": "Aardrijkskunde",
    "GRN": "Muziek", "GRV": "Frans", "GST": "Latijn",
    "GVN": "Lichamelijke opvoeding",
    "HDE": "Duits", "HEI": "Latijn", "HGV": "Biologie",
    "HKT": "Maatschappijleer", "HNS": "Geschiedenis",
    "HPR": "Wiskunde", "HSC": "Wiskunde", "HTA": "Engels",
    "HUI": "Latijn", "HVL": "Latijn",
    "IST": "Engels",
    "JCB": "Biologie", "JJO": "Wiskunde", "JNG": "Engels",
    "JST": "Engels", "JVZ": "Engels", "JWI": "Frans",
    "KAS": "Latijn", "KFM": "Frans", "KHL": "Duits",
    "KNA": "Biologie", "KOM": "Wiskunde", "KUA": "Kunst - BV",
    "LIE": "Natuurkunde", "LIN": "Engels", "LJA": "Latijn",
    "LNS": "Engels", "LSK": "Nederlands", "LVL": "Nederlands",
    "LWN": "Aardrijkskunde",
    "MER": "Scheikunde", "MHA": "Engels", "MKP": "Scheikunde",
    "MNT": "Natuurkunde", "MRA": "Duits", "MRL": "Frans",
    "MSM": "Natuurkunde", "MSS": "Latijn", "MVI": "Wiskunde",
    "NBL": "Nederlands", "NBR": "Wiskunde", "NHE": "Drama",
    "NVM": "Nederlands", "NVS": "Nederlands",
    "OJN": "Engels", "OST": "Natuurkunde",
    "PHN": "Frans", "PON": "Economie",
    "RBO": "Drama", "RBR": "Biologie", "RDR": "Wiskunde",
    "RET": "Engels", "RJO": "Wiskunde", "RNP": "Wiskunde",
    "ROE": "Latijn", "ROS": "Geschiedenis", "ROZ": "Economie",
    "RTE": "Biologie", "RTP": "Geschiedenis", "RVD": "Latijn",
    "RWA": "Aardrijkskunde",
    "SAH": "Aardrijkskunde", "SBU": "Nederlands", "SCB": "Latijn",
    "SCM": "Latijn", "SDC": "Muziek", "SDR": "Lichamelijke opvoeding",
    "SFL": "Frans", "SGL": "Muziek", "SIS": "Aardrijkskunde",
    "SMI": "Scheikunde", "SMK": "Kunst - BV", "SON": "Kunst - BV",
    "TCM": "Latijn", "TIN": "Duits", "TMS": "Kunst - BV",
    "TSL": "Maatschappijleer", "TVL": "Latijn", "TVS": "Economie",
    "VHL": "Kunst - BV", "VHN": "Geschiedenis", "VIN": "Lichamelijke opvoeding",
    "VKO": "Kunst - BV", "VLK": "Filosofie", "VLT": "Biologie",
    "VRL": "Wiskunde", "VRT": "Scheikunde",
    "WAG": "Natuurkunde", "WIT": "Lichamelijke opvoeding",
    "WLT": "Wiskunde", "WNS": "Latijn", "WRN": "Lichamelijke opvoeding",
    "ZAN": "Natuurkunde", "ZEE": "Economie", "ZIL": "Latijn",
    "ZRN": "Natuurkunde", "ZVN": "Latijn",
}

MANUAL_OVERRIDES = {
    "studiewijzer klas 3 gh module 2 25-26": "Wiskunde",
    "sw k3m1 25-26": "Biologie",
}

VAK_AFKORTINGEN = {
    "Nederlands": "Ne", "Engels": "En", "Frans": "Fr", "Duits": "Du",
    "Wiskunde": "Wi", "Biologie": "Bi", "Natuurkunde": "Na", "Scheikunde": "Sk",
    "Geschiedenis": "Gs", "Aardrijkskunde": "Ak",
    "Latijn": "La", "Grieks": "Gr", "Filosofie": "Fi",
    "Economie": "Ec", "Informatica": "In",
    "Kunst - BV": "KuBV", "Muziek": "Mu", "Drama": "Dr",
    "Lichamelijke opvoeding": "LO",
    "Rekenen": "Re",
}


def load_all_json() -> list[dict]:
    """Laadt alle studiewijzer-JSONs uit output/."""
    results = []
    for json_path in OUTPUT_DIR.rglob("*.json"):
        if json_path.parent == OUTPUT_DIR:
            continue
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            if "metadata" in data and "toetsen" in data:
                results.append(data)
        except (json.JSONDecodeError, KeyError):
            pass
    return results


def detect_vak_from_override(bron: str) -> str | None:
    name = os.path.splitext(os.path.basename(bron))[0].lower()
    for pattern, vak in MANUAL_OVERRIDES.items():
        if pattern in name:
            return vak
    return None


def detect_vak_from_filename(bron: str) -> str | None:
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
    name = os.path.splitext(os.path.basename(bron))[0]
    candidates = re.findall(r'(?:^|[\s_\-])([A-Z]{3,4})(?:[\s_\-.]|$)', name)
    end_match = re.search(r'[^A-Z]([A-Z]{3,4})$', name)
    if end_match:
        candidates.append(end_match.group(1))
    for code in candidates:
        if code in DOCENT_VAK:
            return DOCENT_VAK[code]
    return None


def detect_vak_from_beschrijving(beschrijving: str) -> str | None:
    desc = unicodedata.normalize("NFC", beschrijving.lower())
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
    vaknaam_patterns = {
        "Nederlands": "nederlands", "Engels": "engels",
        "Frans": "frans", "Duits": "duits",
        "Wiskunde": "wiskunde", "Biologie": "biologie",
        "Natuurkunde": "natuurkunde", "Scheikunde": "scheikunde",
        "Geschiedenis": "geschiedenis", "Aardrijkskunde": "aardrijkskunde",
        "Latijn": "latijn", "Grieks": "grieks",
        "Economie": "economie", "Filosofie": "filosofie",
        "Informatica": "informatica", "Muziek": "muziek", "Drama": "drama",
    }
    for vak, vaknaam in vaknaam_patterns.items():
        if vaknaam in desc:
            return vak
    return None


def detect_file_vak(doc: dict) -> str | None:
    """Volledige vak-detectieketen op documentniveau."""
    meta = doc.get("metadata", {})
    bron = doc.get("bron_bestand", "")

    file_vak = (meta.get("vak")
                or detect_vak_from_override(bron)
                or detect_vak_from_filename(bron)
                or detect_vak_from_docentcode(bron))

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

    return file_vak


def week_to_module(week: int) -> int | None:
    """Bepaal module op basis van weeknummer."""
    for mod, weeks in MODULE_WEEKS.items():
        if week in weeks:
            return mod
    return None


# ── Hoofdfunctie ─────────────────────────────────────────────────────────────

def build_proefwerk_data():
    """Extraheert proefwerkweek-toetsen en groepeert per klas/module/vak."""
    all_files = load_all_json()
    print(f"Geladen: {len(all_files)} studiewijzer-JSONs")

    # Structuur: klas -> module -> [(vak, beschrijving, stof, week, type)]
    proefwerken = defaultdict(lambda: defaultdict(list))
    seen = set()  # dedup

    for doc in all_files:
        meta = doc["metadata"]
        klas = meta.get("klas", "")
        leerjaar = meta.get("leerjaar")
        if not leerjaar:
            continue
        # Bovenbouw: klas kan leeg zijn, gebruik dan "klas {leerjaar}"
        if not klas and leerjaar >= 4:
            klas = f"klas {leerjaar}"
        elif not klas:
            continue

        file_vak = detect_file_vak(doc)

        for toets in doc.get("toetsen", []):
            # INVERSE filter: alleen proefwerkweek-toetsen
            if not toets.get("in_toetsweek", False):
                continue

            week = toets.get("week")
            if not week:
                continue

            beschrijving_plus = ((toets.get("beschrijving") or "") + " " +
                                 (toets.get("stof") or "")).strip()
            vak = (file_vak
                   or detect_vak_from_beschrijving(beschrijving_plus)
                   or "Onbekend")
            # Onderbouw: Wiskunde A/B/C/D samenvoegen. Bovenbouw: apart houden.
            if leerjaar <= 3:
                if "iskunde" in vak.lower() or vak.lower() == "wiskunde":
                    vak = "Wiskunde"
            if vak == "Latijn":
                desc_lower = (toets.get("beschrijving") or "").lower()
                if "grieks" in desc_lower and "latijn" not in desc_lower:
                    vak = "Grieks"

            toets_type = toets.get("type", "proefwerk")
            module = week_to_module(week) or meta.get("module")

            if not module:
                continue

            # Dedup per klas/module/vak
            dedup_key = (klas, module, vak)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            vak_kort = VAK_AFKORTINGEN.get(vak, vak[:4])

            proefwerken[klas][f"module_{module}"].append({
                "vak": vak,
                "vak_kort": vak_kort,
                "type": toets_type,
                "beschrijving": toets.get("beschrijving", ""),
                "stof": toets.get("stof") or "",
                "week": week,
            })

    # Sorteer toetsen per module op vaknaam
    for klas in proefwerken:
        for mod in proefwerken[klas]:
            proefwerken[klas][mod].sort(key=lambda t: t["vak"])

    # Output
    output = {
        "schooljaar": "2025-2026",
        "gegenereerd": datetime.now().isoformat(timespec="seconds"),
        "toetsweken": {
            "module_1": {"weken": [47, 48], "periode": "17-26 november 2025"},
            "module_2": {"weken": [10, 11], "periode": "4-13 maart 2026"},
            "module_3": {"weken": [25, 26], "periode": "juni 2026"},
        },
        "proefwerken": dict(proefwerken),
    }

    # Statistieken
    total = sum(
        len(toetsen)
        for mods in proefwerken.values()
        for toetsen in mods.values()
    )
    klassen = len(proefwerken)
    per_module = defaultdict(int)
    per_vak = defaultdict(int)
    for mods in proefwerken.values():
        for mod, toetsen in mods.items():
            per_module[mod] += len(toetsen)
            for t in toetsen:
                per_vak[t["vak"]] += 1

    print(f"Totaal: {total} proefwerken over {klassen} klassen")
    for mod in sorted(per_module):
        print(f"  {mod}: {per_module[mod]} proefwerken")
    print(f"  Per vak: {dict(sorted(per_vak.items(), key=lambda x: -x[1]))}")

    # Schrijf output
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DATA_DIR / "proefwerken.json"
    out_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Geschreven: {out_path}")


if __name__ == "__main__":
    build_proefwerk_data()
