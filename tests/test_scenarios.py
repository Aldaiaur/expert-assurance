"""Les résultats affichés par les scénarios fictifs sortent bien du moteur."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build  # noqa: E402
from tests.test_calculs import run_engine  # noqa: E402

DATA, _ = build.load_all()
CAS = [(s["id"], k, rc) for s in DATA["scenarios"]["items"]
       for k, rc in s["resultats_calcules"].items()]


@pytest.mark.parametrize("sid,nom,rc", CAS, ids=[f"{s}:{k}" for s, k, _ in CAS])
def test_resultat_scenario(sid, nom, rc):
    obtenu = run_engine(rc["calcul"], rc["entrees"])
    attendu = rc["attendu"]
    if isinstance(attendu, dict):
        for k, v in attendu.items():
            assert obtenu[k] == pytest.approx(v, abs=0.01)
    else:
        candidats = [obtenu.get("indemnite"), obtenu.get("perte"),
                     obtenu.get("plafond_dts"), obtenu.get("plafond_eur")]
        assert any(c is not None and abs(c - attendu) < 0.01 for c in candidats), \
            f"{attendu} absent de {obtenu}"
