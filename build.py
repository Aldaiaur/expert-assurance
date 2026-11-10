#!/usr/bin/env python3
"""Régénère les livrables de l'outil « expert assurance » depuis data/ :

    python3 build.py            # valide + génère app/index.html, excel/*.xlsx
    python3 build.py --check    # validation seule (schéma + liens croisés)

Source unique de vérité : data/reference/*.json (régénérable) et
data/personal/*.json (jamais écrasé par ce script — il ne fait que les lire
pour ensemencer l'application).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parent
DATA_REF = ROOT / "data" / "reference"
DATA_PERSO = ROOT / "data" / "personal"
SCHEMA_PATH = ROOT / "schema" / "tables.schema.json"

REFERENCE_TABLES = [
    "fiches", "references", "calculs", "etapes_methode", "pieces", "scenarios",
    "trames", "grilles_entretien", "questions", "accidents", "ressources",
    "cabinets", "lexique_fr_en", "a_verifier",
]
PERSONAL_TABLES = ["star", "candidatures", "notes", "progression"]


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_all():
    data = {}
    for name in REFERENCE_TABLES:
        data[name] = load_json(DATA_REF / f"{name}.json")
    perso = {}
    for name in PERSONAL_TABLES:
        perso[name] = load_json(DATA_PERSO / f"{name}.json")
    return data, perso


def validate(data: dict, perso: dict) -> list[str]:
    """Valide chaque table contre son schéma + vérifie les liens croisés."""
    errors: list[str] = []
    schema = load_json(SCHEMA_PATH)
    registry = {"tables_schema": schema}

    def item_validator(def_name: str):
        sub = {"$defs": schema["$defs"], "$ref": f"#/$defs/{def_name}"}
        return jsonschema.Draft202012Validator(sub)

    tables_cfg = schema["tables"]
    for name, cfg in tables_cfg.items():
        table = data.get(name) if name in data else perso.get(name)
        if table is None:
            errors.append(f"table manquante : {name}")
            continue
        if table.get("_table") != name:
            errors.append(f"{name} : _table = {table.get('_table')!r}")
        validator = item_validator(cfg["items_schema"])
        for i, item in enumerate(table.get("items", [])):
            for err in validator.iter_errors(item):
                errors.append(f"{name}[{i}] ({item.get('id', '?')}) : {err.message}")

    # Unicité des ids, globale
    seen: dict[str, str] = {}
    for name in REFERENCE_TABLES + ["star"]:
        table = data.get(name) or perso.get(name)
        for item in table.get("items", []):
            iid = item.get("id")
            if iid in seen:
                errors.append(f"id dupliqué : {iid} ({seen[iid]} et {name})")
            seen[iid] = name

    # Liens croisés
    def check_ids(kind: str, ids, where: str):
        for i in ids:
            if i not in seen:
                errors.append(f"{where} : lien {kind} inconnu → {i}")

    for f in data["fiches"]["items"]:
        liens = f.get("liens", {})
        check_ids("reference", liens.get("referenceIds", []), f"fiches/{f['id']}")
        check_ids("question", liens.get("questionIds", []), f"fiches/{f['id']}")
        check_ids("calcul", liens.get("calculIds", []), f"fiches/{f['id']}")
        check_ids("scenario", liens.get("scenarioIds", []), f"fiches/{f['id']}")
    for e in data["etapes_methode"]["items"]:
        check_ids("piece", e.get("pieceIds", []), f"etapes/{e['id']}")
        check_ids("reference", e.get("referenceIds", []), f"etapes/{e['id']}")
        check_ids("calcul", e.get("calculIds", []), f"etapes/{e['id']}")
    for c in data["calculs"]["items"]:
        check_ids("reference", c.get("base_juridique", []), f"calculs/{c['id']}")
        for d in c.get("delais", []):
            check_ids("reference", [d["base"]], f"calculs/{c['id']}/delais/{d['id']}")
    for g in data["grilles_entretien"]["items"]:
        check_ids("question", g.get("questionIds", []), f"grilles/{g['id']}")
    etape_ids = {e["id"] for e in data["etapes_methode"]["items"]}
    calc_ids = {c["id"] for c in data["calculs"]["items"]}
    for s in data["scenarios"]["items"]:
        for st in s.get("deroule", []):
            if st["etapeId"] not in etape_ids:
                errors.append(f"scenarios/{s['id']} : etapeId inconnu → {st['etapeId']}")
        for key, rc in s.get("resultats_calcules", {}).items():
            if rc["calcul"] not in calc_ids:
                errors.append(f"scenarios/{s['id']}/{key} : calcul inconnu → {rc['calcul']}")

    # Ordres des 12 étapes
    ordres = sorted(e["ordre"] for e in data["etapes_methode"]["items"])
    if ordres != list(range(1, 13)):
        errors.append(f"etapes_methode : ordres = {ordres}, attendu 1..12")

    return errors


def build_app(data: dict, perso: dict) -> Path:
    from tools.gen_app import generate_app  # import local : dépendances légères
    out = ROOT / "app" / "index.html"
    generate_app(ROOT, data, perso, out)
    return out


def build_excel(data: dict) -> list[Path]:
    from tools.gen_excel import generate_methode, generate_base
    outs = [
        generate_methode(data, ROOT / "excel" / "methode_sinistre.xlsx"),
        generate_base(data, ROOT / "excel" / "base_expert.xlsx"),
    ]
    return outs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="validation seule")
    args = ap.parse_args(argv)

    data, perso = load_all()
    errors = validate(data, perso)
    if errors:
        print(f"ÉCHEC DE VALIDATION — {len(errors)} erreur(s) :")
        for e in errors:
            print("  -", e)
        return 1
    n_items = sum(len(t["items"]) for t in data.values())
    print(f"Validation OK : {len(REFERENCE_TABLES)} tables de référence, {n_items} éléments.")
    if args.check:
        return 0

    out_app = build_app(data, perso)
    print(f"Généré : {out_app.relative_to(ROOT)} ({out_app.stat().st_size // 1024} ko)")
    for p in build_excel(data):
        print(f"Généré : {p.relative_to(ROOT)}")
    print(f"Terminé — {dt.date.today().isoformat()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
