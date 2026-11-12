"""Les classeurs se régénèrent, recalculent sans erreur (LibreOffice headless)
et donnent les MÊMES résultats que le moteur de l'application."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build  # noqa: E402
from tools.gen_excel import CHAMPS, generate_base, generate_methode  # noqa: E402
from tests.test_calculs import run_engine  # noqa: E402

SOFFICE = shutil.which("soffice")


def recalc(path: Path, outdir: Path) -> Path:
    subprocess.run([SOFFICE, "--headless", "--norestore", "--convert-to", "xlsx",
                    "--outdir", str(outdir), str(path)],
                   check=True, capture_output=True, timeout=180)
    return outdir / path.name


def param_row(key: str) -> int:
    return 6 + [c[0] for c in CHAMPS].index(key)


@pytest.fixture(scope="module")
def data():
    d, _ = build.load_all()
    return d


@pytest.mark.skipif(SOFFICE is None, reason="LibreOffice absent")
def test_recalcul_sans_erreur_et_scenario_a(data, tmp_path_factory):
    tmp = tmp_path_factory.mktemp("xlsx")
    src = generate_methode(data, tmp / "methode_sinistre.xlsx")
    out = recalc(src, tmp / "recalc")
    wb = load_workbook(out, data_only=True)
    nb_err = sum(1 for ws in wb for row in ws.iter_rows() for c in row
                 if isinstance(c.value, str) and c.value.startswith("#"))
    assert nb_err == 0
    # Scénario (a) du rapport (bloc 2.4), pré-chargé : 2 329 000 / 585 000 / 1 379 927
    assert wb["6_DD"]["J14"].value == 2329000
    assert wb["6_DD"]["J15"].value == 585000
    assert wb["7_PE"]["B17"].value == pytest.approx(1379927.27, abs=0.01)
    assert round(wb["7_PE"]["B17"].value) == 1379927


@pytest.mark.skipif(SOFFICE is None, reason="LibreOffice absent")
def test_identite_app_excel_cas_acceptation(data, tmp_path_factory):
    """Cas bâtiment du cahier des charges, saisi dans la colonne « saisie
    manuelle » : Excel et le moteur JS doivent donner la même chose."""
    tmp = tmp_path_factory.mktemp("xlsx2")
    src = generate_methode(data, tmp / "methode.xlsx")
    wb = load_workbook(src)
    par = wb["11_Paramètres"]
    saisies = {
        "poste1_lib": "Bâtiment (cas d'acceptation)", "poste1_van": 900000, "poste1_vet": 0.20,
        "poste1_decl": 3000000, "poste1_reel": 3600000, "poste1_rp": "Oui",
        "poste2_lib": "-", "poste2_van": 0, "poste2_rp": "Non",
        "poste3_lib": "-", "poste3_van": 0, "poste4_lib": "-", "poste4_van": 0,
        "franchise": 10000, "lci": 0, "taux_rachat": 0.25,
        "pe_baisse_ca": 1200000, "pe_tendance": 1, "pe_taux_marge": 0.60, "pe_fse": 0,
        "pe_mb_sauvee": 0, "pe_eco": 30000, "pe_mb_decl": 0, "pe_mb_reelle": 0,
        "pe_mb_annuelle": 0, "pe_franchise_jours": 0,
        "tr_regime": "cmr", "tr_poids": 8000, "tr_colis": 1,
    }
    for k, v in saisies.items():
        par.cell(row=param_row(k), column=3, value=v)
    mod = tmp / "methode_cas.xlsx"
    wb.save(mod)
    out = recalc(mod, tmp / "recalc")
    wb2 = load_workbook(out, data_only=True)
    imm = wb2["6_DD"]["J14"].value
    dif = wb2["6_DD"]["J15"].value
    pe = wb2["7_PE"]["B17"].value
    cmr = wb2["8_Recours"]["B12"].value

    moteur = run_engine("calc-chaine-indemnite", {
        "dommage_van": 900000, "taux_vetuste": 0.20, "declare": 3000000,
        "reel": 3600000, "franchise": 10000, "plafond": None, "taux_rachat_max": 0.25})
    moteur_pe = run_engine("calc-pe", {"baisse_ca": 1200000, "tendance": 1, "taux_marge": 0.60,
                                       "frais_supp": 0, "perte_evitee": 0, "economies": 30000})
    moteur_cmr = run_engine("calc-plafonds-transport", {"regime": "cmr", "poids_kg": 8000, "nb_colis": 1})

    assert imm == pytest.approx(moteur["immediat"]) == 590000
    assert dif == pytest.approx(moteur["differe"]) == 150000
    assert pe == pytest.approx(moteur_pe["perte"]) == 690000
    assert cmr == pytest.approx(moteur_cmr["plafond_dts"]) == 66640


def test_base_expert_complet(data, tmp_path):
    out = generate_base(data, tmp_path / "base_expert.xlsx")
    wb = load_workbook(out)
    assert set(wb.sheetnames) == set(data.keys())
    for name in wb.sheetnames:
        ws = wb[name]
        assert ws.auto_filter.ref, f"{name} sans filtre"
