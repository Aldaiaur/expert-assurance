"""Le schéma JSON valide, les liens croisés tiennent, les statuts sont posés."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build  # noqa: E402


def test_schema_et_liens():
    data, perso = build.load_all()
    errors = build.validate(data, perso)
    assert errors == [], "\n".join(errors)


def test_scenarios_fictifs_marques():
    data, _ = build.load_all()
    for s in data["scenarios"]["items"]:
        assert s["statut"] == "fictif"
        assert s["marque"] == "FICTIF"


def test_accidents_tracables():
    """Aucun numéro ARIA/BEA-TT inventé : tout accident vérifié porte son
    numéro de base et l'URL de sa fiche ; les pistes non vérifiées restent NV."""
    data, _ = build.load_all()
    items = data["accidents"]["items"]
    assert items, "table accidents vide"
    for a in items:
        if a["statut"] == "V":
            assert a["numero_base"] and a["numero_base"] != "—", a["id"]
            assert a["source_url"], a["id"]


def test_anonymisation_depot():
    """Règle du dépôt : aucune mention de l'organisme d'origine dans les
    fichiers versionnés."""
    root = Path(__file__).resolve().parents[1]
    interdits = ["CNRS", "cnrs"]
    for p in list(root.rglob("data/**/*.json")) + list(root.glob("src/*")) + [root / "build.py"]:
        txt = p.read_text(encoding="utf-8")
        for mot in interdits:
            assert mot not in txt, f"{p} contient « {mot} »"
