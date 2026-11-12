"""Assemble app/index.html : gabarit + CSS + moteur de calcul + app + données.

Un seul fichier autonome, zéro requête réseau. Les données de référence sont
inlinées ; les données personnelles embarquées ne servent que de graine
(l'app travaille ensuite dans localStorage).
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path


def _json_inline(obj) -> str:
    # </script> ne doit jamais apparaître dans un bloc script
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def generate_app(root: Path, data: dict, perso: dict, out: Path) -> Path:
    src = root / "src"
    shell = (src / "app_shell.html").read_text(encoding="utf-8")
    css = (src / "app.css").read_text(encoding="utf-8")
    engine = (src / "calc_engine.js").read_text(encoding="utf-8")
    appjs = (src / "app.js").read_text(encoding="utf-8")

    templates = []
    for svg in sorted((root / "data" / "diagrams").glob("*.svg")):
        contenu = svg.read_text(encoding="utf-8")
        contenu = contenu[contenu.index("<svg"):]  # retire le commentaire d'empreinte
        templates.append(f'<template id="tpl-{svg.stem}">{contenu}</template>')

    html = (shell
            .replace("__SVG_TEMPLATES__", "\n".join(templates))
            .replace("__DATE__", dt.date.today().isoformat())
            .replace("__CSS__", css)
            .replace("__CALC_ENGINE__", engine.replace("</", "<\\/"))
            .replace("__APP_JS__", appjs.replace("</", "<\\/"))
            .replace("__DATA_REF__", _json_inline(data))
            .replace("__DATA_PERSO__", _json_inline(perso)))

    assert "http://" not in html.replace("http://www.w3.org", ""), "URL http inattendue"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out
