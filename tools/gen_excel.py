"""Génération des deux classeurs Excel (openpyxl, formules vives uniquement).

- methode_sinistre.xlsx : classeur de méthode en 12 onglets, scénario (a)
  pré-chargé, sélecteur (a)/(b)/(c), plages nommées, validations.
- base_expert.xlsx : export à plat de toutes les tables, un onglet filtrable
  par table.

Aucune valeur calculée n'est écrite en dur : tout résultat est une formule.
"""
from __future__ import annotations

import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation

# ---------------------------------------------------------------- styles
BLEU_SAISIE = PatternFill("solid", fgColor="DCE9FB")   # cellules de saisie
GRIS_FORMULE = PatternFill("solid", fgColor="F3F3F3")
BANDEAU = PatternFill("solid", fgColor="B45309")
ENTETE = PatternFill("solid", fgColor="1F3A5F")
FICTIF = PatternFill("solid", fgColor="FDE68A")
F_ENTETE = Font(bold=True, color="FFFFFF")
F_BANDEAU = Font(bold=True, color="FFFFFF", size=12)
F_TITRE = Font(bold=True, size=14)
F_GRAS = Font(bold=True)
F_PETIT = Font(size=9, italic=True, color="666666")
BORD = Border(*(Side(style="thin", color="CCCCCC"),) * 4)
WRAP = Alignment(wrap_text=True, vertical="top")

EURO = "#,##0\\ \"€\""
NUM = "#,##0.00"


def _bandeau_fictif(ws, ncols=8):
    # La ligne 1 est réservée au bandeau par construction (aucune insertion :
    # une insertion décalerait les formules et plages nommées déjà posées).
    c = ws.cell(row=1, column=1, value="SCÉNARIO FICTIF — EXERCICE DE MÉTHODE. Aucune donnée réelle.")
    c.fill = FICTIF
    c.font = Font(bold=True, color="92400E")
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncols)


def _entete(ws, row, labels, widths=None):
    for j, lab in enumerate(labels, start=1):
        c = ws.cell(row=row, column=j, value=lab)
        c.fill = ENTETE
        c.font = F_ENTETE
        c.alignment = WRAP
        c.border = BORD
    if widths:
        for j, w in enumerate(widths, start=1):
            ws.column_dimensions[get_column_letter(j)].width = w


def _saisie(ws, coord, value=None, fmt=None):
    c = ws[coord]
    if value is not None:
        c.value = value
    c.fill = BLEU_SAISIE
    c.border = BORD
    if fmt:
        c.number_format = fmt
    return c


def _nom(wb, name, sheet_title, coord):
    wb.defined_names.add(DefinedName(name, attr_text=f"'{sheet_title}'!{coord}"))


# ------------------------------------------------------------- scénarios
# Grille normalisée des paramètres chargés par le sélecteur (a)/(b)/(c).
def _poste(n):
    return [
        (f"poste{n}_lib", f"Poste {n} — libellé", None, "texte"),
        (f"poste{n}_van", f"Poste {n} — dommage valeur à neuf (€)", EURO, "nombre"),
        (f"poste{n}_vet", f"Poste {n} — taux de vétusté", "0.0%", "nombre"),
        (f"poste{n}_decl", f"Poste {n} — capitaux déclarés (€)", EURO, "nombre"),
        (f"poste{n}_reel", f"Poste {n} — valeur réelle (€)", EURO, "nombre"),
        (f"poste{n}_rp", f"Poste {n} — règle proportionnelle (Oui/Non)", None, "texte"),
    ]


CHAMPS = (
    [("desc", "Description du scénario", None, "texte")]
    + _poste(1) + _poste(2) + _poste(3) + _poste(4)
    + [
        ("franchise", "Franchise dommages directs (€)", EURO, "nombre"),
        ("lci", "Plafond / LCI (€, 0 = sans)", EURO, "nombre"),
        ("taux_rachat", "Vétusté récupérable plafonnée à (en % de la VN)", "0.0%", "nombre"),
        ("pe_baisse_ca", "PE — baisse de CA (€)", EURO, "nombre"),
        ("pe_tendance", "PE — coefficient de tendance", NUM, "nombre"),
        ("pe_taux_marge", "PE — taux de marge brute assurée", "0.0%", "nombre"),
        ("pe_fse", "PE — frais supplémentaires engagés (€)", EURO, "nombre"),
        ("pe_mb_sauvee", "PE — marge brute sauvée par les FSE (€)", EURO, "nombre"),
        ("pe_eco", "PE — économies de charges (€)", EURO, "nombre"),
        ("pe_mb_decl", "PE — marge brute déclarée (€, 0 = pas de RP)", EURO, "nombre"),
        ("pe_mb_reelle", "PE — marge brute réelle (€)", EURO, "nombre"),
        ("pe_mb_annuelle", "PE — marge brute annuelle (€, pour la franchise en jours)", EURO, "nombre"),
        ("pe_franchise_jours", "PE — franchise (jours ouvrés, base 250 j/an)", "0", "nombre"),
        ("tr_regime", "Transport — régime", None, "texte"),
        ("tr_poids", "Transport — poids brut (kg)", NUM, "nombre"),
        ("tr_colis", "Transport — nombre de colis", "0", "nombre"),
    ]
)

def _vide(**kw):
    base = {}
    for n in (1, 2, 3, 4):
        base.update({f"poste{n}_lib": "—", f"poste{n}_van": 0, f"poste{n}_vet": 0,
                     f"poste{n}_decl": 0, f"poste{n}_reel": 0, f"poste{n}_rp": "Non"})
    base.update({"franchise": 0, "lci": 0, "taux_rachat": 0.25,
                 "pe_baisse_ca": 0, "pe_tendance": 1, "pe_taux_marge": 0, "pe_fse": 0,
                 "pe_mb_sauvee": 0, "pe_eco": 0, "pe_mb_decl": 0, "pe_mb_reelle": 0,
                 "pe_mb_annuelle": 0, "pe_franchise_jours": 0,
                 "tr_regime": "(sans objet)", "tr_poids": 0, "tr_colis": 0})
    base.update(kw)
    return base


SCN_VALS = {
    "a": _vide(
        desc="FICTIF — Incendie d'un atelier de décolletage, Cluses (74) — scénario (a) du rapport",
        poste1_lib="Bâtiment", poste1_van=900000, poste1_vet=0.25,
        poste2_lib="Matériel (tour multibroche…)", poste2_van=1800000, poste2_vet=0.40,
        poste2_decl=4000000, poste2_reel=5000000, poste2_rp="Oui",
        poste3_lib="Marchandises (au prix de revient)", poste3_van=500000,
        poste4_lib="Frais : déblais 120 k€ + décontamination 180 k€", poste4_van=300000,
        franchise=10000,
        pe_baisse_ca=2400000, pe_tendance=1.05, pe_taux_marge=0.55,
        pe_fse=250000, pe_mb_sauvee=462000, pe_eco=60000,
        pe_mb_decl=4000000, pe_mb_reelle=4400000, pe_mb_annuelle=4400000, pe_franchise_jours=3,
    ),
    "b": _vide(
        desc="FICTIF — Citerne de 30 m³ d'UN 1202 renversée, affluent de l'Arve — scénario (b)",
        poste1_lib="Dépollution : SUR DEVIS uniquement (aucun coût vérifié)",
        poste2_lib="Marchandise (gazole)",
        tr_regime="cmr", tr_poids=6800, tr_colis=1,
    ),
    "c": _vide(
        desc="FICTIF — Batteries lithium UN 3480 vendues CIP, emballement chez le commissionnaire — scénario (c)",
        poste1_lib="Marchandise : 20 palettes, 480 000 € (à chiffrer selon cause et couverture)",
        tr_regime="cmr", tr_poids=8000, tr_colis=1,
    ),
}

# Source affichée pour chaque paramètre réglementaire de 11_Paramètres.
PARAMS_REGL = [
    ("CMR_Taux", "CMR — DTS par kg", 8.33, "CMR art. 23 — dossier + sources concordantes (détail des délais NV)"),
    ("MTL_Taux", "Montréal — DTS par kg (depuis le 28/12/2024)", 26, "OACI, révision 2024 — vérifié le 2026-11-10"),
    ("HV_Colis", "La Haye-Visby — DTS par colis", 666.67, "Protocole DTS 1979, art. IV(5)(a) — vérifié le 2026-11-10"),
    ("HV_Kg", "La Haye-Visby — DTS par kg", 2, "Protocole DTS 1979, art. IV(5)(a) — vérifié le 2026-11-10"),
    ("CTG33", "Contrat type général <3 t — €/kg", 33, "C. transports, annexe II art. 22 — vérifié le 2026-11-10"),
    ("CTG1000", "Contrat type général <3 t — €/colis max", 1000, "C. transports, annexe II art. 22 — vérifié le 2026-11-10"),
    ("CTG20", "Contrat type général ≥3 t — €/kg", 20, "C. transports, annexe II art. 22 — vérifié le 2026-11-10"),
    ("CTG3200", "Contrat type général ≥3 t — €/tonne max", 3200, "C. transports, annexe II art. 22 — vérifié le 2026-11-10"),
    ("P_CoursDTS", "Cours du DTS (€/DTS) — SAISIE MANUELLE", 0, "non sourcé — à relever le jour même (FMI / Banque de France)"),
]


def generate_methode(data: dict, out: Path) -> Path:
    wb = Workbook()
    wb.remove(wb.active)

    # ---------------- feuille cachée Scenarios
    scn = wb.create_sheet("Scenarios")
    scn["A1"] = "champ"
    for j, code in enumerate(["a", "b", "c"], start=2):
        scn.cell(row=1, column=j, value=code).font = F_GRAS
    for i, (key, label, _fmt, _k) in enumerate(CHAMPS, start=2):
        scn.cell(row=i, column=1, value=key)
        for j, code in enumerate(["a", "b", "c"], start=2):
            scn.cell(row=i, column=j, value=SCN_VALS[code][key])
    scn.sheet_state = "hidden"

    # ---------------- 11_Paramètres (créée d'abord : les autres s'y réfèrent)
    par = wb.create_sheet("11_Paramètres")
    par["A1"] = "Paramètres du dossier"
    par["A1"].font = F_TITRE
    par["A3"] = "Scénario chargé (a, b ou c) :"
    par["A3"].font = F_GRAS
    _saisie(par, "B3", "a")
    dv = DataValidation(type="list", formula1='"a,b,c"', allow_blank=False)
    dv.add(par["B3"])
    par.add_data_validation(dv)
    _nom(wb, "Scn_Sel", par.title, "$B$3")
    par["C3"] = "Sélecteur : charge les valeurs du scénario ; la colonne « Saisie manuelle » prime si remplie."
    par["C3"].font = F_PETIT

    _entete(par, 5, ["Champ", "Valeur scénario", "Saisie manuelle (bleu)", "Valeur retenue", "Source"],
            widths=[44, 20, 20, 20, 58])
    noms = {}
    r = 6
    for i, (key, label, fmt, kind) in enumerate(CHAMPS):
        srow = i + 2  # ligne dans Scenarios
        par.cell(row=r, column=1, value=label).alignment = WRAP
        c_scn = par.cell(row=r, column=2)
        c_scn.value = f'=HLOOKUP(Scn_Sel,Scenarios!$B$1:$D${len(CHAMPS) + 1},{srow},FALSE)'
        c_scn.fill = GRIS_FORMULE
        _saisie(par, f"C{r}")
        c_ret = par.cell(row=r, column=4)
        c_ret.value = f'=IF($C{r}<>"",$C{r},$B{r})'
        c_ret.font = F_GRAS
        src = "scénario fictif (données du dossier + ajouts fictifs signalés)"
        par.cell(row=r, column=5, value=src).font = F_PETIT
        if fmt:
            c_scn.number_format = fmt
            par[f"C{r}"].number_format = fmt
            c_ret.number_format = fmt
        nom = "P_" + key
        _nom(wb, nom, par.title, f"$D${r}")
        noms[key] = nom
        r += 1

    r += 1
    par.cell(row=r, column=1, value="Paramètres réglementaires (plafonds, taux)").font = F_TITRE
    r += 1
    _entete(par, r, ["Paramètre", "Valeur", "", "", "Source (ou « non sourcé »)"])
    r += 1
    for name, label, val, src in PARAMS_REGL:
        par.cell(row=r, column=1, value=label).alignment = WRAP
        c = par.cell(row=r, column=2, value=val)
        c.number_format = NUM
        if name == "P_CoursDTS":
            c.fill = BLEU_SAISIE
        else:
            c.fill = GRIS_FORMULE
        par.cell(row=r, column=5, value=src).font = F_PETIT
        par.cell(row=r, column=5).alignment = WRAP
        _nom(wb, name, par.title, f"$B${r}")
        r += 1

    # ---------------- 0_Lisez-moi
    lis = wb.create_sheet("0_Lisez-moi", 0)
    lignes = [
        ("Classeur de méthode — sinistre fictif", F_TITRE),
        ("", None),
        ("TOUS LES SCÉNARIOS SONT FICTIFS. Aucune donnée réelle d'employeur ou de dossier.", Font(bold=True, color="92400E")),
        ("", None),
        ("Mode d'emploi :", F_GRAS),
        ("1. Choisir le scénario (a, b ou c) dans 11_Paramètres (cellule bleue B3). Le (a) est pré-chargé.", None),
        ("2. Les cellules BLEUES sont des saisies ; tout le reste est calculé par des formules vives.", None),
        ("3. Dérouler les onglets dans l'ordre : Mission → Chrono → Pièces → Constatations → Garantie → DD → PE → Recours → Réserves → Rapport.", None),
        ("4. Chaque paramètre de 11_Paramètres porte sa source, ou la mention « non sourcé ».", None),
        ("", None),
        ("Hypothèse affichée : franchise déduite APRÈS la règle proportionnelle ; l'ordre réel dépend de la police.", F_PETIT),
        ("Le cours du DTS est saisi à la main (aucune récupération réseau).", F_PETIT),
        ("Régénéré par build.py — ne pas éditer la structure à la main (les saisies bleues, si).", F_PETIT),
    ]
    for i, (txt, font) in enumerate(lignes, start=1):
        c = lis.cell(row=i, column=1, value=txt)
        if font:
            c.font = font
    lis.column_dimensions["A"].width = 110

    # ---------------- 1_Mission
    mis = wb.create_sheet("1_Mission")
    mis["A2"] = "Scénario chargé :"
    mis["A2"].font = F_GRAS
    mis["B2"] = "=P_desc"
    mis["B2"].fill = GRIS_FORMULE
    _entete(mis, 4, ["Champ", "Saisie"], widths=[32, 80])
    champs_mission = [
        "Mandant (assureur / gestionnaire)", "N° de dossier", "Assuré", "Police n°",
        "Date de mission", "Date du sinistre", "Lieu", "Nature du sinistre",
        "Garanties concernées", "Conflit d'intérêts vérifié (Oui/Non)", "Expert d'assuré présent (Oui/Non)",
    ]
    for i, ch in enumerate(champs_mission, start=5):
        mis.cell(row=i, column=1, value=ch)
        _saisie(mis, f"B{i}")
    _bandeau_fictif(mis, 2)

    # ---------------- 2_Chrono
    chr_ = wb.create_sheet("2_Chrono")
    chr_["A2"] = "Dates du dossier (saisies bleues) — l'échéancier se calcule seul."
    chr_["A2"].font = F_PETIT
    _entete(chr_, 3, ["Événement", "Date"], widths=[46, 16])
    dates = [("Sinistre / connaissance", "D_Sinistre"), ("Déclaration à l'assureur", "D_Declaration"),
             ("Livraison (transport)", "D_Livraison"), ("Accord sur la proposition", "D_Accord")]
    for i, (lab, nom) in enumerate(dates, start=4):
        chr_.cell(row=i, column=1, value=lab)
        _saisie(chr_, f"B{i}", fmt="DD/MM/YYYY")
        _nom(wb, nom, chr_.title, f"$B${i}")
    _entete(chr_, 9, ["Échéance", "Base", "Statut base", "Date limite"], widths=[46, 28, 10, 16])
    echeances = [
        ("Déclaration du sinistre (5 jours ouvrés)", "L.113-2", "V", "=IF(D_Sinistre=\"\",\"\",WORKDAY(D_Sinistre,5))"),
        ("Déclaration en cas de vol (2 jours ouvrés)", "L.113-2", "V", "=IF(D_Sinistre=\"\",\"\",WORKDAY(D_Sinistre,2))"),
        ("Réponse assureur sans expert (2 mois)", "L.121-18", "V", "=IF(D_Declaration=\"\",\"\",EDATE(D_Declaration,2))"),
        ("Réponse assureur avec expert (6 mois)", "L.121-18", "V", "=IF(D_Declaration=\"\",\"\",EDATE(D_Declaration,6))"),
        ("Versement après accord (21 jours)", "L.121-18", "V", "=IF(D_Accord=\"\",\"\",D_Accord+21)"),
        ("CatNat : information + expertise (1 mois)", "L.125-2", "V", "=IF(D_Declaration=\"\",\"\",EDATE(D_Declaration,1))"),
        ("Protestation motivée au voiturier (3 jours, fériés non compris)", "L.133-3 C. com.", "V", "=IF(D_Livraison=\"\",\"\",D_Livraison+3)"),
        ("CMR : réserves avaries non apparentes (7 jours)", "CMR art. 30", "NV", "=IF(D_Livraison=\"\",\"\",D_Livraison+7)"),
        ("CMR : réserve écrite retard (21 jours)", "CMR art. 30", "NV", "=IF(D_Livraison=\"\",\"\",D_Livraison+21)"),
        ("Présomption de perte (30 jours après délai de livraison)", "Contrat type art. 21", "V", "=IF(D_Livraison=\"\",\"\",D_Livraison+30)"),
        ("Prescription transport (1 an)", "L.133-6 C. com.", "V", "=IF(D_Livraison=\"\",\"\",EDATE(D_Livraison,12))"),
        ("CMR : prescription (1 an ; 3 ans si dol)", "CMR art. 32", "NV", "=IF(D_Livraison=\"\",\"\",EDATE(D_Livraison,12))"),
        ("Prescription biennale assurance (2 ans)", "L.114-1", "V", "=IF(D_Sinistre=\"\",\"\",EDATE(D_Sinistre,24))"),
    ]
    for i, (lab, base, st, f) in enumerate(echeances, start=10):
        chr_.cell(row=i, column=1, value=lab).alignment = WRAP
        chr_.cell(row=i, column=2, value=base)
        chr_.cell(row=i, column=3, value=st)
        c = chr_.cell(row=i, column=4, value=f)
        c.number_format = "DD/MM/YYYY"
        c.fill = GRIS_FORMULE
    chr_.cell(row=24, column=1, value="Jours fériés non décomptés automatiquement (L.113-2 : WORKDAY sans liste de fériés ; L.133-3 : ajouter les fériés à la main).").font = F_PETIT
    _bandeau_fictif(chr_, 4)

    # ---------------- 3_Pièces
    pcs = wb.create_sheet("3_Pièces")
    _entete(pcs, 2, ["Pièce", "Catégorie", "Quand", "État", "Demandée le", "Reçue le"],
            widths=[56, 14, 26, 14, 13, 13])
    dv_etat = DataValidation(type="list", formula1='"à demander,demandée,relancée,reçue,sans objet"', allow_blank=True)
    pcs.add_data_validation(dv_etat)
    for i, p in enumerate(data["pieces"]["items"], start=3):
        pcs.cell(row=i, column=1, value=p["label"]).alignment = WRAP
        pcs.cell(row=i, column=2, value=p["categorie"])
        pcs.cell(row=i, column=3, value=p["quand"])
        _saisie(pcs, f"D{i}", "à demander")
        dv_etat.add(pcs[f"D{i}"])
        _saisie(pcs, f"E{i}", fmt="DD/MM/YYYY")
        _saisie(pcs, f"F{i}", fmt="DD/MM/YYYY")
    n = len(data["pieces"]["items"])
    pcs.cell(row=n + 4, column=1, value="Pièces reçues :").font = F_GRAS
    c = pcs.cell(row=n + 4, column=2, value=f'=COUNTIF(D3:D{n + 2},"reçue")&" / "&COUNTA(A3:A{n + 2})')
    c.fill = GRIS_FORMULE
    pcs.auto_filter.ref = f"A2:F{n + 2}"
    _bandeau_fictif(pcs, 6)

    # ---------------- 4_Constatations
    cst = wb.create_sheet("4_Constatations")
    cst["A2"] = "Méthode NFPA 921 : zone d'origine par les figures de feu, hypothèses multiples, preuves tracées."
    cst["A2"].font = F_PETIT
    _entete(cst, 3, ["Hypothèse de cause", "Éléments pour", "Éléments contre", "Statut"],
            widths=[34, 38, 38, 16])
    dv_hyp = DataValidation(type="list", formula1='"à instruire,renforcée,écartée,retenue"', allow_blank=True)
    cst.add_data_validation(dv_hyp)
    for i in range(4, 9):
        for col in "ABC":
            _saisie(cst, f"{col}{i}")
        _saisie(cst, f"D{i}", "à instruire")
        dv_hyp.add(cst[f"D{i}"])
    _entete(cst, 10, ["Scellé n°", "Description", "Localisation", "PV contradictoire (Oui/Non)"])
    for i in range(11, 16):
        for col in "ABCD":
            _saisie(cst, f"{col}{i}")
    cst.cell(row=17, column=1, value="Interdits : affirmer une cause non démontrée ; adjectifs émotionnels ; ouvrir un scellé hors présence des parties.").font = F_PETIT
    _bandeau_fictif(cst, 4)

    # ---------------- 5_Garantie
    gar = wb.create_sheet("5_Garantie")
    _entete(gar, 2, ["Contrôle", "Base", "Réponse / constat"], widths=[52, 16, 40])
    controles = [
        ("Exclusion invoquée : est-elle formelle et limitée ?", "L.113-1"),
        ("Déclarations du risque exactes à la souscription ?", "L.113-8 / L.113-9"),
        ("Circonstances nouvelles déclarées sous 15 jours ?", "L.113-2 / L.113-4"),
        ("Capitaux déclarés vs valeurs réelles (par poste) ?", "L.121-5"),
        ("Clause dérogatoire (premier risque, tolérance) ?", "police"),
        ("Ordre d'application de la franchise prévu par la police ?", "police"),
        ("Garantie PE et période d'indemnisation ?", "police"),
    ]
    for i, (lab, base) in enumerate(controles, start=3):
        gar.cell(row=i, column=1, value=lab).alignment = WRAP
        gar.cell(row=i, column=2, value=base)
        _saisie(gar, f"C{i}")
    gar["A12"] = "Mini-calcul — règle proportionnelle de PRIME (L.113-9)"
    gar["A12"].font = F_GRAS
    gar["A13"] = "Dommage (€)"; _saisie(gar, "B13", 0, EURO)
    gar["A14"] = "Prime payée (ou taux)"; _saisie(gar, "B14", 0, NUM)
    gar["A15"] = "Prime due (ou taux)"; _saisie(gar, "B15", 0, NUM)
    gar["A16"] = "Indemnité réduite"
    gar["B16"] = "=IF(B15=0,\"\",MIN(B13,B13*B14/B15))"
    gar["B16"].number_format = EURO
    gar["B16"].fill = GRIS_FORMULE
    _bandeau_fictif(gar, 3)

    # ---------------- 6_DD (dommages directs)
    dd = wb.create_sheet("6_DD")
    _entete(dd, 2, ["Poste", "Dommage VàN", "Taux vétusté", "Vétusté", "Dommage VD",
                    "Déclaré", "Réel", "RP ?", "Coeff. RP", "Indemnité avant franchise", "Différé (rachat vétusté)"],
            widths=[34, 14, 10, 12, 13, 13, 13, 7, 9, 10, 12])
    dv_rp = DataValidation(type="list", formula1='"Oui,Non"', allow_blank=True)
    dd.add_data_validation(dv_rp)
    # Lignes 3-6 : alimentées par les paramètres (scénario) ; lignes 7-8 : saisie libre
    for i, pref in ((3, "P_poste1_"), (4, "P_poste2_"), (5, "P_poste3_"), (6, "P_poste4_")):
        dd.cell(row=i, column=1, value=f"={pref}lib").fill = GRIS_FORMULE
        dd.cell(row=i, column=2, value=f"={pref}van").number_format = EURO
        dd.cell(row=i, column=3, value=f"={pref}vet").number_format = "0.0%"
        dd.cell(row=i, column=6, value=f"={pref}decl").number_format = EURO
        dd.cell(row=i, column=7, value=f"={pref}reel").number_format = EURO
        dd.cell(row=i, column=8, value=f"={pref}rp")
    for i in range(7, 9):
        _saisie(dd, f"A{i}")
        for col, fmt in (("B", EURO), ("C", "0.0%"), ("F", EURO), ("G", EURO)):
            _saisie(dd, f"{col}{i}", fmt=fmt)
        _saisie(dd, f"H{i}", "Non")
        dv_rp.add(dd[f"H{i}"])
    for i in range(3, 9):
        dd.cell(row=i, column=4, value=f'=IF($B{i}="","",$B{i}*$C{i})').number_format = EURO
        dd.cell(row=i, column=5, value=f'=IF($B{i}="","",$B{i}-$D{i})').number_format = EURO
        dd.cell(row=i, column=9, value=f'=IF($B{i}="","",IF(AND($H{i}="Oui",$G{i}>0),MIN(1,$F{i}/$G{i}),1))').number_format = "0.0%"
        dd.cell(row=i, column=10, value=f'=IF($B{i}="","",$E{i}*$I{i})').number_format = EURO
        dd.cell(row=i, column=11, value=f'=IF($B{i}="","",MIN($D{i},P_taux_rachat*$B{i})*$I{i})').number_format = EURO
        for col in range(4, 12):
            dd.cell(row=i, column=col).fill = GRIS_FORMULE
    dd["A10"] = "Totaux"; dd["A10"].font = F_GRAS
    dd["J10"] = "=SUM(J3:J8)"; dd["K10"] = "=SUM(K3:K8)"
    dd["A11"] = "Franchise (une fois, APRÈS la règle proportionnelle — ordre usuel, lire la police)"
    dd["J11"] = "=-P_franchise"
    dd["A12"] = "Indemnité immédiate avant plafond"; dd["J12"] = "=MAX(0,J10+J11)"
    dd["A13"] = "Plafond / LCI"; dd["J13"] = '=IF(P_lci=0,"(sans)",P_lci)'
    dd["A14"] = "INDEMNITÉ IMMÉDIATE"; dd["A14"].font = F_GRAS
    dd["J14"] = "=IF(P_lci=0,J12,MIN(J12,P_lci))"
    dd["A15"] = "INDEMNITÉ DIFFÉRÉE (vétusté récupérable, reconstruction dans le délai)"; dd["A15"].font = F_GRAS
    dd["J15"] = "=K10"
    for coord in ("J10", "K10", "J11", "J12", "J14", "J15"):
        dd[coord].number_format = EURO
        dd[coord].fill = GRIS_FORMULE
        dd[coord].font = F_GRAS
    _nom(wb, "R_ImmTotal", dd.title, "$J$14")
    _nom(wb, "R_DiffTotal", dd.title, "$J$15")
    dd.cell(row=17, column=1, value="Différé plafonné en % de la VALEUR À NEUF (pratique [NV]). Stock de produits finis au prix de revient. RP seulement sur les postes sous-déclarés.").font = F_PETIT
    _bandeau_fictif(dd, 11)

    # ---------------- 7_PE
    pe = wb.create_sheet("7_PE")
    rows = [
        ("Baisse de chiffre d'affaires (€)", "=P_pe_baisse_ca", EURO),
        ("Coefficient de tendance", "=P_pe_tendance", NUM),
        ("Taux de marge brute assurée", "=P_pe_taux_marge", "0.0%"),
        ("Perte de marge brute (= B3 × B4 × B5)", "=B3*B4*B5", EURO),
        ("Frais supplémentaires d'exploitation (FSE) engagés", "=P_pe_fse", EURO),
        ("Marge brute sauvée par les FSE", "=P_pe_mb_sauvee", EURO),
        ("FSE retenus (limite économique : min des deux)", "=MIN(B7,B8)", EURO),
        ("Économies de charges", "=P_pe_eco", EURO),
        ("Sous-total (= B6 + B9 − B10)", "=B6+B9-B10", EURO),
        ("Marge brute déclarée", "=P_pe_mb_decl", EURO),
        ("Marge brute réelle", "=P_pe_mb_reelle", EURO),
        ("Coefficient de règle proportionnelle PE", "=IF(B13=0,1,MIN(1,B12/B13))", "0.00%"),
        ("Après règle proportionnelle (= B11 × B14)", "=B11*B14", EURO),
        ("Franchise (jours ouvrés × MB annuelle / 250)", "=P_pe_mb_annuelle/250*P_pe_franchise_jours", EURO),
        ("PERTE D'EXPLOITATION", "=MAX(0,B15-B16)", EURO),
    ]
    _entete(pe, 2, ["Élément", "Valeur"], widths=[56, 18])
    for i, (lab, f, fmt) in enumerate(rows, start=3):
        pe.cell(row=i, column=1, value=lab).alignment = WRAP
        c = pe.cell(row=i, column=2, value=f)
        c.number_format = fmt
        c.fill = GRIS_FORMULE
    pe["A17"].font = F_GRAS
    pe["B17"].font = F_GRAS
    _nom(wb, "R_PE", pe.title, "$B$17")
    pe.cell(row=19, column=1, value="MB assurée (soustractive) = CA + variation des stocks − charges variables (≠ marge comptable). FSE admis dans la limite de la MB sauvée. Franchise en jours ouvrés sur une base de 250 j/an (pratique [NV]). Vérifier période d'indemnisation et carence dans la police.").font = F_PETIT
    _bandeau_fictif(pe, 2)

    # ---------------- 8_Recours
    rec = wb.create_sheet("8_Recours")
    _entete(rec, 2, ["Recours potentiel", "Fondement", "Assiette (€)", "Notes"], widths=[34, 30, 14, 40])
    fondements = [
        ("Fabricant de l'équipement", "C. civ. 1245 et s. (produits défectueux)"),
        ("Mainteneur / installateur", "Responsabilité contractuelle"),
        ("Transporteur", "L.133-1 C. com. / CMR"),
        ("Expéditeur / chargeur / remplisseur", "ADR 1.4"),
    ]
    for i, (lab, base) in enumerate(fondements, start=3):
        rec.cell(row=i, column=1, value=lab)
        rec.cell(row=i, column=2, value=base)
        _saisie(rec, f"C{i}", fmt=EURO)
        _saisie(rec, f"D{i}")
    rec["A8"] = "Plafond transport applicable à la marchandise"
    rec["A8"].font = F_GRAS
    rec["A9"] = "Régime"; rec["B9"] = "=P_tr_regime"; rec["B9"].fill = GRIS_FORMULE
    rec["A10"] = "Poids brut (kg)"; rec["B10"] = "=P_tr_poids"; rec["B10"].fill = GRIS_FORMULE
    rec["A11"] = "Nombre de colis"; rec["B11"] = "=P_tr_colis"; rec["B11"].fill = GRIS_FORMULE
    rec["A12"] = "Plafond (DTS si convention, € si contrat type)"
    rec["B12"] = ('=IF(B9="cmr",CMR_Taux*B10,'
                  'IF(B9="montreal",MTL_Taux*B10,'
                  'IF(B9="hague_visby",MAX(HV_Colis*B11,HV_Kg*B10),'
                  'IF(B9="ctg_moins_3t",MIN(CTG33*B10,CTG1000*B11),'
                  'IF(B9="ctg_3t_et_plus",MIN(CTG20*B10,CTG3200*B10/1000),0)))))')
    rec["B12"].number_format = NUM
    rec["B12"].fill = GRIS_FORMULE
    rec["B12"].font = F_GRAS
    _nom(wb, "R_PlafondTransport", rec.title, "$B$12")
    rec["A13"] = "Converti en € (× cours du DTS saisi dans 11_Paramètres)"
    rec["B13"] = '=IF(OR(B9="cmr",B9="montreal",B9="hague_visby"),IF(P_CoursDTS=0,"saisir le cours du DTS",B12*P_CoursDTS),B12)'
    rec["B13"].number_format = NUM
    rec["B13"].fill = GRIS_FORMULE
    rec.cell(row=15, column=1, value="Dol / faute inexcusable : les plafonds sautent (CMR art. 29 ; contrat type art. 22.1). Préserver la subrogation (L.121-12) : rien signer qui y renonce.").font = F_PETIT
    _bandeau_fictif(rec, 4)

    # ---------------- 9_Réserves
    res = wb.create_sheet("9_Réserves")
    _entete(res, 2, ["Poste de réserve", "Montant", "Commentaire"], widths=[44, 18, 44])
    lignes_res = [
        ("Dommages directs — indemnité immédiate", "=R_ImmTotal"),
        ("Dommages directs — indemnité différée", "=R_DiffTotal"),
        ("Perte d'exploitation", "=R_PE"),
        ("Honoraires et frais d'expertise (saisie)", None),
        ("Marge de prudence (saisie)", None),
    ]
    for i, (lab, f) in enumerate(lignes_res, start=3):
        res.cell(row=i, column=1, value=lab)
        if f:
            c = res.cell(row=i, column=2, value=f)
            c.fill = GRIS_FORMULE
        else:
            _saisie(res, f"B{i}")
        res.cell(row=i, column=2).number_format = EURO
        _saisie(res, f"C{i}")
    res["A8"] = "RÉSERVE TOTALE"; res["A8"].font = F_GRAS
    res["B8"] = "=SUM(B3:B7)"; res["B8"].number_format = EURO; res["B8"].font = F_GRAS; res["B8"].fill = GRIS_FORMULE
    res["A10"] = "Suivi des acomptes (L.121-18 : acompte motivé à 6 mois si causes/évaluation non établies)"
    res["A10"].font = F_PETIT
    _entete(res, 11, ["Date", "Acompte versé", "Motif"])
    for i in range(12, 15):
        _saisie(res, f"A{i}", fmt="DD/MM/YYYY")
        _saisie(res, f"B{i}", fmt=EURO)
        _saisie(res, f"C{i}")
    _bandeau_fictif(res, 3)

    # ---------------- 10_Rapport
    rap = wb.create_sheet("10_Rapport")
    rap["A2"] = "Synthèse pour rapport (toutes valeurs = formules vers les onglets)"
    rap["A2"].font = F_GRAS
    synth = [
        ("Scénario", "=P_desc"),
        ("Indemnité immédiate (dommages directs)", "=R_ImmTotal"),
        ("Indemnité différée (rachat de vétusté)", "=R_DiffTotal"),
        ("Perte d'exploitation", "=R_PE"),
        ("Réserve totale", "='9_Réserves'!B8"),
        ("Plafond transport (si applicable)", "=R_PlafondTransport"),
    ]
    for i, (lab, f) in enumerate(synth, start=3):
        rap.cell(row=i, column=1, value=lab)
        c = rap.cell(row=i, column=2, value=f)
        c.fill = GRIS_FORMULE
        if i > 3:
            c.number_format = NUM if i == 8 else EURO
    rap.column_dimensions["A"].width = 44
    rap.column_dimensions["B"].width = 60
    rap["A10"] = "Plan du rapport préliminaire :"
    rap["A10"].font = F_GRAS
    trame = next(t for t in data["trames"]["items"] if t["id"] == "tr-rapport-preliminaire")
    for i, ligne in enumerate(trame["contenu"], start=11):
        rap.cell(row=i, column=1, value=f"{i - 10}. {ligne}").alignment = WRAP
    r0 = 11 + len(trame["contenu"]) + 1
    rap.cell(row=r0, column=1, value="Plan du rapport définitif : cause, chiffrage, application de la police (franchises, règle proportionnelle), recours. PV contradictoire joint. Transmission à l'assureur ET à l'assuré (L.121-18 II).").alignment = WRAP
    rap.cell(row=r0, column=1).font = F_PETIT
    _bandeau_fictif(rap, 2)

    # Ordre final des onglets : 0..10 puis 11_Paramètres puis Scenarios (cachée)
    ordre = ["0_Lisez-moi", "1_Mission", "2_Chrono", "3_Pièces", "4_Constatations",
             "5_Garantie", "6_DD", "7_PE", "8_Recours", "9_Réserves", "10_Rapport",
             "11_Paramètres", "Scenarios"]
    wb._sheets.sort(key=lambda ws: ordre.index(ws.title))

    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    return out


# ------------------------------------------------------------ base_expert
def _flat(v):
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    return v


def generate_base(data: dict, out: Path) -> Path:
    wb = Workbook()
    wb.remove(wb.active)
    for name, table in data.items():
        ws = wb.create_sheet(name[:31])
        items = table["items"]
        cols: list[str] = []
        for it in items:
            for k in it:
                if k not in cols:
                    cols.append(k)
        if not cols:
            cols = ["(table vide)"]
            ws.cell(row=2, column=1, value=table.get("_source", ""))
        _entete(ws, 1, cols)
        for i, it in enumerate(items, start=2):
            for j, k in enumerate(cols, start=1):
                c = ws.cell(row=i, column=j, value=_flat(it.get(k)))
                c.alignment = WRAP
                c.border = BORD
        ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{max(2, len(items) + 1)}"
        ws.freeze_panes = "A2"
        for j, k in enumerate(cols, start=1):
            ws.column_dimensions[get_column_letter(j)].width = min(60, max(12, len(k) + 6))
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    return out
