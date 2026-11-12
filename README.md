# Expert assurance — outil personnel hors ligne

Base de connaissances « expertise d'assurance – risques d'entreprise et
transport » + calculateurs, pour préparer des entretiens d'expert IARD junior :
réviser, dérouler une méthode sur un sinistre **fictif**, montrer un portfolio.

**Tout fonctionne sans réseau** : l'application est un seul fichier
`app/index.html` ouvrable en `file://` (zéro CDN, zéro police distante, zéro
analytics — un test l'impose).

## Arborescence

```
expert-assurance/
├── build.py              ← régénère app + les 2 classeurs : python3 build.py
├── requirements.txt      ← openpyxl, jsonschema, pytest (pas d'autre dépendance)
├── sources/              ← PDF sources — NON versionné (.gitignore, données perso)
├── schema/tables.schema.json
├── data/
│   ├── reference/        ← source unique de vérité, régénérable (14 tables)
│   └── personal/         ← graines de TES données — jamais écrasées par build.py
├── src/                  ← app_shell.html, app.css, app.js, calc_engine.js (lisibles)
├── tools/                ← gen_app.py, gen_excel.py
├── app/index.html        ← GÉNÉRÉ — l'application, un seul fichier
├── excel/
│   ├── methode_sinistre.xlsx   ← GÉNÉRÉ — méthode 12 onglets, formules vives
│   └── base_expert.xlsx        ← GÉNÉRÉ — toutes les tables, filtrables
└── tests/                ← pytest (schéma, calculs, Excel↔app, hors-ligne)
```

## Utilisation

```bash
pip install -r requirements.txt
python3 build.py            # valide puis régénère app/ et excel/
python3 build.py --check    # validation seule
python3 -m pytest tests/    # suite complète (node + LibreOffice si présents)
```

Les classeurs : cellules **bleues = saisies**, tout le reste = formules vives.
Dans `methode_sinistre.xlsx`, l'onglet `11_Paramètres` porte le **sélecteur de
scénario** (a pré-chargé ; b, c au choix), une colonne « saisie manuelle » qui
prime sur le scénario, et la **source de chaque paramètre** (ou « non sourcé »).

## Statuts et fiabilité

Chaque élément factuel porte `statut` : `V` (vérifié, avec `source_url` +
`date_verification`), `NV` (non vérifié), `ordre_de_grandeur`, `fictif`.
Règles :

- **ne jamais passer NV → V** sans contrôle sur la source primaire (Légifrance,
  ARIA, BEA-TT, éditeur de norme) — noter l'URL et la date ;
- les textes de normes privées (NFPA, APSAD, FM, ASTM, SIA) ne sont **jamais
  reproduits** : référence, résumé reformulé, lien ;
- la vue **« À vérifier »** de l'app liste tous les NV avec leur source primaire ;
- les 3 scénarios sont **FICTIFS** (marqué sur chaque écran, onglet, impression).

Vérifications du 2026-11-10 : articles français contrôlés **verbatim** sur
l'édition DILA des codes du 2026-10-14 (miroir `codes.droit.org` — Légifrance
bloque les accès automatisés) : L.113-1/2/4/8/9, L.114-1, L.121-1/5/12/17/**18**
(créé par la loi n° 2026-403 du 26 mai 2026), L.125-1/2, C. com. L.133-1/3/6,
contrat type général (annexe II, art. 21-22). Montréal **26 DTS/kg** depuis le
28/12/2024 (OACI). La Haye-Visby 666,67 DTS/colis ou 2 DTS/kg. Restent NV,
entre autres : le détail des délais CMR art. 30/32, le décret d'application de
L.121-18 — voir `data/reference/a_verifier.json`.

## Mettre à jour la base

1. Éditer `data/reference/*.json` (jamais `app/` ni `excel/`, qui sont générés).
2. `python3 build.py` — la validation refuse tout lien croisé cassé, statut
   manquant ou étape hors 1-12.
3. `python3 -m pytest tests/` — les vecteurs de test de `calculs.json` sont la
   source unique des cas chiffrés : app, Excel et tests les partagent.
4. Tes données (récits STAR, candidatures, progression, checklist) vivent dans
   le navigateur (localStorage) : **une régénération ne les touche pas**.
   Sauvegarde/restaure-les via « Mes données » (export/import JSON).

**Rapport de recherche intégré** (novembre 2026) : fiches du noyau dur 1.0 à 1.11,
accidents vérifiés (ARIA 54441, 60243, 61711, 50520, 37008 ; BEA-TT 2023-03,
2006-010, 2012-008), scénario (a) exact — 2 329 000 € immédiat, 585 000 € différé,
1 379 927 € de PE —, identique dans l'app, dans Excel et dans les tests.

## Onglet « Système » : modèle systémique du métier

Table `data/reference/modele_systemique.json` : frontière, 14 acteurs, flux en
4 couches, stocks et délais, 8 boucles (R/B), tensions, cycle de vie en 12
étapes, perturbations, leviers, cas test, limites, version orale de 3 minutes.
Chaque élément est marqué **[S]** (sources), **[C]** (connaissance à vérifier)
ou **[H]** (hypothèse de modélisation).

Les deux diagrammes Mermaid sont rendus **une fois** en SVG versionnés
(`data/diagrams/`) ; l'app les embarque, sans Mermaid ni réseau. Si tu modifies
une source Mermaid :

```bash
npm install --prefix tools/.mermaid mermaid@11.4.1   # une fois (dossier ignoré par git)
node tools/render_diagrams.cjs
```

Un test refuse un SVG périmé (empreinte SHA-256), et un autre vérifie que la
polarité de chaque boucle (R/B) correspond au nombre de liens négatifs du graphe.

## Mobile : file:// et variante PWA

Vérifié ici : Chromium (bureau + fenêtre mobile 390 px) ouvre `app/index.html`
en `file://` sans aucune requête réseau. **Pas d'appareil iOS/Android réel dans
cet environnement** — comportement attendu, à confirmer sur tes appareils :

- **Android / Chrome** : ouvrir le fichier via l'appli Fichiers fonctionne
  (`file://`), localStorage inclus, mais chaque mise à jour oblige à rouvrir le
  fichier ;
- **iOS / Safari** : pas d'ouverture directe de `file://` ; depuis l'appli
  Fichiers, l'aperçu HTML n'exécute pas toujours le JavaScript. Solutions :
  une appli tierce type « serveur web local », ou la variante PWA.
- **Variante PWA (sur demande)** : manifest + service worker à héberger une
  fois en HTTPS (ex. GitHub Pages privé) ; installation initiale **en ligne**
  (c'est le compromis — contraire au « zéro réseau » strict), puis
  fonctionnement 100 % hors ligne et icône d'accueil. Les données restent
  locales au téléphone.

## Copier vers un dépôt dédié (procédure téléphone)

Le dossier est autonome (aucun lien avec l'app QHSE). Depuis le téléphone :

1. github.com → **+** → *New repository* → nom `expert-assurance`, **Private**,
   sans README → *Create repository*.
2. Si l'appli GitHub « Claude » est limitée à certains dépôts : Settings →
   Applications → Claude → ajouter `expert-assurance`.
3. Me demander « pousse expert-assurance dans le nouveau dépôt » : je copie le
   dossier tel quel (les sources PDF, non versionnées, seront à re-téléverser
   dans la conversation si besoin).
