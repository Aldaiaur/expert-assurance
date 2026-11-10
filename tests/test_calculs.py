"""Tous les vecteurs de test de calculs.json passent dans le moteur JS (node).

C'est le même fichier calc_engine.js qui est inliné dans app/index.html :
ce test garantit donc les résultats de l'application.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build  # noqa: E402

DATA, _ = build.load_all()
VECTEURS = [
    (c["id"], v) for c in DATA["calculs"]["items"] for v in c["vecteurs_test"]
]


def run_engine(calc_id: str, entrees: dict) -> dict:
    script = (
        "const E=require(process.argv[1]);"
        "const [id,entrees]=JSON.parse(process.argv[2]);"
        "process.stdout.write(JSON.stringify(E.runVector(id,entrees)));"
    )
    out = subprocess.run(
        ["node", "-e", script, str(ROOT / "src" / "calc_engine.js"),
         json.dumps([calc_id, entrees])],
        capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


@pytest.mark.parametrize("calc_id,vec", VECTEURS, ids=[f"{c}:{v['nom']}" for c, v in VECTEURS])
def test_vecteur(calc_id, vec):
    obtenu = run_engine(calc_id, vec["entrees"])
    attendu = vec["attendu"]
    if not isinstance(attendu, dict):
        attendu = {"_scalaire": attendu}
        # un attendu scalaire vise la grandeur principale du calcul
        principal = {"calc-rp-capitaux": "indemnite", "calc-rp-prime": "indemnite",
                     "calc-pe": "perte"}
        obtenu = {"_scalaire": obtenu[principal[calc_id]]}
    for k, v in attendu.items():
        assert obtenu[k] == pytest.approx(v, abs=0.01), f"{k}: {obtenu[k]} ≠ {v}"


def test_acceptation_mission():
    """Les 3 cas chiffrés du cahier des charges, en direct."""
    assert run_engine("calc-rp-capitaux", {"dommage": 200000, "declare": 800000, "reel": 1000000})["indemnite"] == 160000
    r = run_engine("calc-chaine-indemnite", {"dommage_van": 900000, "taux_vetuste": 0.20,
                                             "declare": 3000000, "reel": 3600000,
                                             "franchise": 10000, "plafond": None, "taux_rachat_max": 0.25})
    assert r["immediat"] == 590000 and r["differe"] == 150000
    assert run_engine("calc-plafonds-transport", {"regime": "cmr", "poids_kg": 8000, "nb_colis": 1})["plafond_dts"] == 66640
