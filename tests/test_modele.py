"""Cohérence du modèle systémique : diagramme de boucles (≤ 25 nœuds,
polarité sur chaque flèche), polarité de chaque boucle = parité des liens
négatifs, SVG à jour par rapport à la source Mermaid, contenu attendu."""
import hashlib
import re
import sys
import xml.dom.minidom
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build  # noqa: E402

DATA, _ = build.load_all()
ITEMS = DATA["modele_systemique"]["items"]
BY_ID = {i["id"]: i for i in ITEMS}
EDGE = re.compile(r'^\s*(\w+)\s*-->\|"\((\+|−)\)"\|\s*(\w+)\s*$')
NODE = re.compile(r'^\s*(\w+)\["')


def graphe():
    src = BY_ID["ms-diag-boucles"]["mermaid"]
    noeuds, liens = set(), {}
    for ligne in src.splitlines():
        m = NODE.match(ligne)
        if m:
            noeuds.add(m.group(1))
        m = EDGE.match(ligne)
        if m:
            liens[(m.group(1), m.group(3))] = m.group(2)
    return noeuds, liens


def test_diagramme_boucles_25_noeuds_max_et_polarites():
    noeuds, liens = graphe()
    assert 0 < len(noeuds) <= 25, len(noeuds)
    fleches = [l for l in BY_ID["ms-diag-boucles"]["mermaid"].splitlines() if "-->" in l]
    assert len(fleches) == len(liens), "une flèche sans polarité (+)/(−)"
    for (a, b) in liens:
        assert a in noeuds and b in noeuds


@pytest.mark.parametrize("bid", [i["id"] for i in ITEMS if i["type"] == "boucle"])
def test_polarite_boucle_coherente(bid):
    """R si nombre pair de liens négatifs, B si impair — calculé sur le graphe."""
    _, liens = graphe()
    boucle = BY_ID[bid]
    n = boucle["noeuds"]
    negatifs = 0
    for a, b in zip(n, n[1:] + n[:1]):
        assert (a, b) in liens, f"{bid} : lien absent du diagramme {a} → {b}"
        negatifs += liens[(a, b)] == "−"
    attendu = "R" if negatifs % 2 == 0 else "B"
    assert boucle["polarite"] == attendu, f"{bid} : {negatifs} lien(s) négatif(s)"


@pytest.mark.parametrize("did", [i["id"] for i in ITEMS if i["type"] == "diagramme"])
def test_svg_a_jour_et_valide(did):
    svg = ROOT / "data" / "diagrams" / f"{did}.svg"
    assert svg.exists(), "lancer node tools/render_diagrams.cjs"
    texte = svg.read_text(encoding="utf-8")
    sha = hashlib.sha256(BY_ID[did]["mermaid"].encode("utf-8")).hexdigest()
    assert f"mermaid-sha256: {sha}" in texte, "SVG périmé : relancer node tools/render_diagrams.cjs"
    xml.dom.minidom.parseString(texte)
    assert "Unsupported markdown" not in texte


def test_contenu_attendu():
    types = [i["type"] for i in ITEMS]
    assert types.count("acteur") >= 14
    assert len(BY_ID["ms-synthese"]["contenu"]) == 10
    assert sorted(i["ordre"] for i in ITEMS if i["type"] == "etape_cycle") == list(range(1, 13))
    assert {"R", "B"} <= {i["polarite"] for i in ITEMS if i["type"] == "boucle"}
    flux = [i for i in ITEMS if i["type"] == "flux"]
    assert len(flux) == 4
    assert BY_ID["ms-cas-test"]["statut"] == "fictif"


def test_marques_presentes():
    """Chaque élément porte une marque S/C/H, et les textes longs en citent."""
    for it in ITEMS:
        assert it["marque"] in {"S", "C", "H", "mixte"}
    texte = " ".join(str(v) for it in ITEMS for v in it.values())
    for m in ("[S]", "[C]", "[H]"):
        assert m in texte
