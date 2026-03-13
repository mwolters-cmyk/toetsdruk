#!/usr/bin/env python3
"""Aggregeert output/*.json tot dashboard/data/toetsdruk.json voor de Toetsdruk Monitor."""

import json
import os
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
}
TOETSWEEK_WEEKS = [47, 48, 10, 11, 25, 26]
VAKANTIE_WEEKS = [43, 52, 1, 9, 18, 19]

# Onderbouw locatie-indeling: A-F = Socrates, G-Q = Athena
SOCRATES_LETTERS = set("ABCDEF")


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
}

# Toetstype afkortingen
TYPE_AFKORTINGEN = {
    "proefwerk": "PW", "so": "SO", "uso": "USO", "po": "PO",
    "mondeling": "MO", "presentatie": "PR", "portfolio": "PF",
    "handelingsdeel": "HD", "anders": "?",
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


def build_data():
    """Bouwt het dashboard databestand."""
    all_files = load_all_json()
    print(f"Geladen: {len(all_files)} studiewijzer-JSONs")

    # Verzamel toetsen per klas per week
    # Structuur: klas -> week -> [(vak, type, beschrijving, stof)]
    klas_toetsen = defaultdict(lambda: defaultdict(list))

    # Deduplicatie: track (klas, week, vak, type) om duplicaten te voorkomen
    seen = set()

    for doc in all_files:
        meta = doc["metadata"]
        klas = meta.get("klas", "")
        leerjaar = meta.get("leerjaar")
        if not klas or not leerjaar or leerjaar > 3:
            continue  # Alleen onderbouw

        for toets in doc.get("toetsen", []):
            # Filter: proefwerkweek-toetsen uitsluiten
            if toets.get("in_toetsweek", False):
                continue

            # Filter: herkansingen uitsluiten (geen reguliere toetsdruk)
            beschrijving = (toets.get("beschrijving") or "").lower()
            if "herkans" in beschrijving or "resit" in beschrijving:
                continue

            week = toets.get("week")
            if not week:
                continue

            vak = meta.get("vak", "Onbekend")
            # Gecombineerde studiewijzers: Latijn/Grieks-correctie
            if vak == "Latijn":
                desc_lower = beschrijving
                if "grieks" in desc_lower and "latijn" not in desc_lower:
                    vak = "Grieks"
            toets_type = toets.get("type", "anders")
            dedup_key = (klas, week, vak, toets_type)

            if dedup_key in seen:
                continue
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

    # Schrijf output
    DASHBOARD_DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DASHBOARD_DATA_DIR / "toetsdruk.json"
    out_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Geschreven: {out_path}")


if __name__ == "__main__":
    build_data()
