/* Expert assurance — application autonome (aucune requête réseau).
   Données de référence : injectées au build (window.DB).
   Données personnelles : localStorage, ensemencées depuis data/personal/. */
(function () {
  'use strict';

  // ---------------------------------------------------------------- état
  const DB = JSON.parse(document.getElementById('data-ref').textContent);
  const SEED = JSON.parse(document.getElementById('data-perso').textContent);
  const LS_KEY = 'expert-assurance-perso-v1';

  function loadPerso() {
    try {
      const raw = localStorage.getItem(LS_KEY);
      if (raw) return JSON.parse(raw);
    } catch (e) { /* stockage indisponible : on travaille en mémoire */ }
    return JSON.parse(JSON.stringify(SEED));
  }
  const P = loadPerso();
  P.ui = P.ui || { theme: 'auto' };
  P.methode = P.methode || {};
  function save() {
    try { localStorage.setItem(LS_KEY, JSON.stringify(P)); } catch (e) { /* ignoré */ }
  }

  // ---------------------------------------------------------------- utils
  const $ = (sel, el) => (el || document).querySelector(sel);
  const main = () => $('#vue');
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }
  function eur(x) {
    if (x == null || isNaN(x)) return '—';
    return new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 2 }).format(x) + ' €';
  }
  function num(x) {
    if (x == null || isNaN(x)) return '—';
    return new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 2 }).format(x);
  }
  const STATUT_LABEL = { V: 'V · vérifié', NV: 'NV · non vérifié', ordre_de_grandeur: 'ordre de grandeur', fictif: 'FICTIF' };
  function badge(st) {
    return st ? `<span class="badge ${esc(st)}" title="${esc(STATUT_LABEL[st] || st)}">${esc(st === 'ordre_de_grandeur' ? '≈' : st.toUpperCase())}</span>` : '';
  }

  // Index global des éléments par id (navigation croisée + recherche)
  const INDEX = {};
  const ROUTES_TABLE = {
    fiches: (id) => '#/fiche/' + id, references: (id) => '#/references?focus=' + id,
    calculs: (id) => '#/calc/' + id, etapes_methode: () => '#/methode',
    pieces: () => '#/methode', scenarios: (id) => '#/scenario/' + id,
    trames: (id) => '#/trames?focus=' + id, grilles_entretien: (id) => '#/entretien?grille=' + id,
    questions: (id) => '#/entretien?q=' + id, accidents: () => '#/averifier',
    ressources: () => '#/ressources', cabinets: (id) => '#/cabinets?focus=' + id,
    lexique_fr_en: () => '#/lexique', a_verifier: () => '#/averifier',
  };
  Object.keys(ROUTES_TABLE).forEach((t) => {
    (DB[t].items || []).forEach((it) => {
      INDEX[it.id] = { table: t, item: it, route: ROUTES_TABLE[t](it.id) };
    });
  });
  (SEED.star.items || []).forEach((it) => { INDEX[it.id] = { table: 'star', item: it, route: '#/entretien?star=1' }; });

  function titleOf(it, table) {
    return it.titre || it.intitule || it.label || it.question || it.nom || it.fr || it.sujet || it.poste || it.id;
  }
  function refLink(id) {
    const e = INDEX[id];
    if (!e) return esc(id);
    const t = titleOf(e.item, e.table);
    const numero = e.item.numero && e.table === 'references' ? e.item.numero + ' — ' : '';
    return `<a href="${e.route}">${esc(numero + t)}</a> ${badge(e.item.statut)}`;
  }

  // ---------------------------------------------------------------- thème
  function applyTheme() {
    const t = P.ui.theme;
    const dark = t === 'dark' || (t === 'auto' && matchMedia('(prefers-color-scheme: dark)').matches);
    document.documentElement.dataset.theme = dark ? 'dark' : 'light';
    $('#btn-theme').textContent = t === 'auto' ? '◐' : (t === 'dark' ? '●' : '○');
  }
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', applyTheme);

  // ---------------------------------------------------------------- vues
  const VUES = {};

  VUES.accueil = function () {
    const nv = DB.a_verifier.items.length;
    const dues = srsDue().length;
    return `
    <h1>Expert assurance — base personnelle</h1>
    <div class="bandeau-fictif">Les scénarios sont FICTIFS. Statuts : V vérifié · NV non vérifié · ≈ ordre de grandeur.</div>
    <div class="grid cols2">
      <div class="card"><h3>Réviser</h3>
        <p><a href="#/quiz">Cartes à répétition espacée</a> — <b>${dues}</b> carte(s) dues.</p>
        <p><a href="#/entretien">Entraînement entretien</a> : tirage chronométré, grilles par poste, banque STAR.</p>
        <p><a href="#/fiches">Fiches</a> · <a href="#/lexique">Lexique FR↔EN</a></p></div>
      <div class="card"><h3>Travailler un sinistre</h3>
        <p><a href="#/methode">Méthode en 12 étapes</a> + 3 scénarios fictifs déroulables.</p>
        <p><a href="#/calculs">Calculateurs</a> : règles proportionnelles, chaîne d'indemnisation, PE, plafonds transport, délais.</p></div>
      <div class="card"><h3>Chercher un poste</h3>
        <p><a href="#/cabinets">Cibles et cabinets</a> · <a href="#/candidatures">Suivi des candidatures</a></p>
        <p><a href="#/ressources">Ressources et sprint de 6 semaines</a></p></div>
      <div class="card"><h3>Fiabilité</h3>
        <p><a href="#/averifier">Vue « À vérifier »</a> : <b>${nv}</b> éléments NV avec leur source primaire.</p>
        <p><a href="#/references">Références juridiques et normatives</a></p>
        <p><a href="#/donnees">Exporter / importer mes données</a></p></div>
    </div>`;
  };

  // ------------------------------------------------ recherche plein texte
  function searchCorpus() {
    const corpus = [];
    Object.keys(ROUTES_TABLE).forEach((t) => {
      DB[t].items.forEach((it) => {
        corpus.push({ id: it.id, table: t, titre: titleOf(it, t), statut: it.statut, route: INDEX[it.id].route, text: JSON.stringify(it).toLowerCase() });
      });
    });
    return corpus;
  }
  let CORPUS = null;
  VUES.recherche = function (params) {
    const q = (params.get('q') || '').trim().toLowerCase();
    if (!CORPUS) CORPUS = searchCorpus();
    let hits = [];
    if (q.length >= 2) {
      hits = CORPUS.filter((c) => c.text.includes(q)).slice(0, 80);
    }
    const TABLE_LABEL = { fiches: 'fiche', references: 'référence', calculs: 'calculateur', etapes_methode: 'étape', pieces: 'pièce', scenarios: 'scénario', trames: 'trame', grilles_entretien: 'grille', questions: 'question', accidents: 'accident', ressources: 'ressource', cabinets: 'cible', lexique_fr_en: 'lexique', a_verifier: 'à vérifier' };
    return `<h1>Recherche</h1>
      <p class="muted">${q ? `${hits.length} résultat(s) pour « ${esc(q)} »` : 'Saisir au moins 2 caractères dans la barre du haut.'}</p>
      <ul class="clean searchhit">${hits.map((h2) => `<li><a href="${h2.route}">${esc(h2.titre)}</a>
        <span class="badge theme">${TABLE_LABEL[h2.table]}</span> ${badge(h2.statut)}</li>`).join('')}</ul>`;
  };

  // ---------------------------------------------------------------- fiches
  VUES.fiches = function (params) {
    const th = params.get('theme') || '';
    const st = params.get('statut') || '';
    const themes = [...new Set(DB.fiches.items.map((f) => f.theme))];
    const items = DB.fiches.items.filter((f) => (!th || f.theme === th) && (!st || f.statut === st));
    return `<h1>Fiches</h1>
      <div class="filters">${themes.map((t) => `<a class="chip ${t === th ? 'on' : ''}" href="#/fiches${t === th ? '' : '?theme=' + t}">${esc(t)}</a>`).join('')}
        ${['V', 'NV', 'ordre_de_grandeur'].map((s) => `<a class="chip ${s === st ? 'on' : ''}" href="#/fiches${s === st ? '' : '?statut=' + s}${th ? '&theme=' + th : ''}">${esc(s)}</a>`).join('')}</div>
      <ul class="clean">${items.map((f) => `<li><a href="#/fiche/${f.id}"><b>${esc(f.numero)}</b> — ${esc(f.titre)}</a>
        <span class="badge theme">${esc(f.theme)}</span> ${badge(f.statut)}</li>`).join('')}</ul>
      <p class="muted">La numérotation « noyau dur 1.0-1.11 » viendra du rapport_recherche.md (non fourni) — voir <a href="#/averifier">À vérifier</a>.</p>`;
  };

  VUES.fiche = function (_p, id) {
    const f = DB.fiches.items.find((x) => x.id === id);
    if (!f) return '<p>Fiche introuvable.</p>';
    const l = f.liens || {};
    const bloc = (label, ids) => (ids && ids.length ? `<p><b>${label} :</b> ${ids.map(refLink).join(' · ')}</p>` : '');
    return `<div class="toolbar no-print"><a class="btn" href="#/fiches">← Fiches</a>
        <button onclick="window.print()">Imprimer (A4)</button></div>
      <div class="card">
      <h1>${esc(f.numero)} — ${esc(f.titre)} ${badge(f.statut)} <span class="badge theme">${esc(f.theme)}</span></h1>
      <ul>${f.points.map((p) => `<li>${esc(p)}</li>`).join('')}</ul>
      ${bloc('Références', l.referenceIds)}${bloc('Calculateurs', l.calculIds)}${bloc('Questions', l.questionIds)}${bloc('Scénarios', l.scenarioIds)}
      ${f.note ? `<p class="muted">Note : ${esc(f.note)}</p>` : ''}
      <p class="print-only muted">Base personnelle de révision — ${new Date().toLocaleDateString('fr-FR')}. Statut : ${esc(STATUT_LABEL[f.statut] || f.statut)}.</p>
      </div>`;
  };

  // ------------------------------------------------------------ références
  VUES.references = function (params) {
    const ty = params.get('type') || '';
    const st = params.get('statut') || '';
    const focus = params.get('focus') || '';
    const types = [...new Set(DB.references.items.map((r) => r.type))];
    const items = DB.references.items.filter((r) => (!ty || r.type === ty) && (!st || r.statut === st));
    setTimeout(() => { const el = document.getElementById(focus); if (el) el.scrollIntoView({ block: 'center' }); }, 30);
    return `<h1>Références</h1>
      <div class="filters">${types.map((t) => `<a class="chip ${t === ty ? 'on' : ''}" href="#/references${t === ty ? '' : '?type=' + t}">${esc(t)}</a>`).join('')}
      ${['V', 'NV'].map((s) => `<a class="chip ${s === st ? 'on' : ''}" href="#/references${s === st ? '' : '?statut=' + s}${ty ? '&type=' + ty : ''}">${s}</a>`).join('')}</div>
      ${items.map((r) => `<div class="card" id="${r.id}">
        <h3>${esc(r.code)}${r.numero ? ' · ' + esc(r.numero) : ''} ${badge(r.statut)}</h3>
        <p><b>${esc(r.intitule)}</b></p><p>${esc(r.resume)}</p>
        ${r.source_url ? `<p><a href="${esc(r.source_url)}" rel="noopener">Source consultée</a>${r.date_verification ? ' · vérifié le ' + esc(r.date_verification) : ''}</p>` : ''}
        ${r.note ? `<p class="muted">${esc(r.note)}</p>` : ''}</div>`).join('')}`;
  };

  // ----------------------------------------------------------- calculateurs
  VUES.calculs = function () {
    return `<h1>Calculateurs</h1>
      ${DB.calculs.items.map((c) => `<div class="card"><h3><a href="#/calc/${c.id}">${esc(c.titre)}</a> ${badge(c.statut)}</h3>
      <p class="muted">${esc(c.formule.slice(0, 140))}${c.formule.length > 140 ? '…' : ''}</p>
      <p><b>Base :</b> ${c.base_juridique.map(refLink).join(' · ') || '—'}</p></div>`).join('')}`;
  };

  const CALC_FORMS = {
    'calc-rp-capitaux': { run: (v) => CalcEngine.rpCapitaux(v), out: (r) => `Coefficient : <b>${num(r.coeff * 100)} %</b><br>Indemnité : <strong class="total">${eur(r.indemnite)}</strong>` },
    'calc-rp-prime': { run: (v) => CalcEngine.rpPrime(v), out: (r) => (r.indemnite == null ? 'Renseigner la prime due.' : `Coefficient : <b>${num(r.coeff * 100)} %</b><br>Indemnité réduite : <strong class="total">${eur(r.indemnite)}</strong>`) },
    'calc-chaine-indemnite': { run: (v) => CalcEngine.chaineIndemnite(v), out: (r) => `Vétusté : ${eur(r.vetuste)} · Valeur vétusté déduite : ${eur(r.valeur_vetuste_deduite)} · Coeff RP : ${num(r.coeff * 100)} %<br>Indemnité immédiate : <strong class="total">${eur(r.immediat)}</strong><br>Indemnité différée (rachat de vétusté) : <strong>${eur(r.differe)}</strong>` },
    'calc-pe': { run: (v) => CalcEngine.pe(v), out: (r) => `Marge brute perdue : ${eur(r.marge_perdue)} · Frais retenus (écrêtés) : ${eur(r.frais_retenus)}<br>Perte d'exploitation : <strong class="total">${eur(r.perte)}</strong>` },
    'calc-plafonds-transport': { run: (v) => CalcEngine.plafondsTransport(v), out: (r) => `${r.plafond_dts != null ? `Plafond : <strong class="total">${num(r.plafond_dts)} DTS</strong>` : ''}${r.plafond_eur != null ? `Plafond : <strong class="total">${eur(r.plafond_eur)}</strong>` : ''}${r.en_euros != null ? `<br>≈ ${eur(r.en_euros)} (au cours saisi)` : ''}` },
  };

  function calcForm(c) {
    if (c.id === 'calc-echeancier') return echeancierForm(c);
    const spec = CALC_FORMS[c.id];
    const inputs = c.parametres.map((p) => {
      if (p.type === 'choix') {
        return `<label>${esc(p.label)}</label><select name="${p.nom}">${p.options.map((o) => `<option>${o}</option>`).join('')}</select>`;
      }
      const defv = p.defaut != null ? ` value="${p.defaut}"` : '';
      const step = p.type === 'taux' ? ' step="0.01" placeholder="ex. 0,20 pour 20 %"' : ' step="any"';
      return `<label>${esc(p.label)}${p.optionnel ? ' <small>(optionnel)</small>' : ''}</label><input name="${p.nom}" type="number" inputmode="decimal"${step}${defv}>`;
    }).join('');
    return `<form class="calc" id="f-${c.id}" onsubmit="return false">${inputs}
      <p><button class="primary" data-run="${c.id}">Calculer</button></p>
      <div class="resultat" id="r-${c.id}" hidden></div></form>`;
  }

  function echeancierForm(c) {
    const dates = [['date_sinistre', 'Date du sinistre / de sa connaissance'], ['date_declaration', 'Date de déclaration'], ['date_livraison', 'Date de livraison (transport)'], ['date_accord', "Date d'accord sur la proposition"]];
    return `<form class="calc" id="f-${c.id}" onsubmit="return false">
      ${dates.map(([n, l]) => `<label>${l}</label><input type="date" name="${n}">`).join('')}
      <p><button class="primary" data-run="${c.id}">Calculer l'échéancier</button></p>
      <div class="resultat" id="r-${c.id}" hidden></div></form>`;
  }

  function runCalc(id) {
    const c = DB.calculs.items.find((x) => x.id === id);
    const form = document.getElementById('f-' + id);
    const out = document.getElementById('r-' + id);
    const vals = {};
    new FormData(form).forEach((v, k) => { vals[k] = v === '' ? null : (form.elements[k].type === 'number' ? parseFloat(v) : v); });
    out.hidden = false;
    if (id === 'calc-echeancier') {
      const r = CalcEngine.echeancier(vals);
      const labels = {}; const bases = {}; const stat = {};
      c.delais.forEach((d) => { labels[d.id] = d.label + ' — ' + d.regle; bases[d.id] = d.base; stat[d.id] = (INDEX[d.base] || {}).item; });
      labels['d-declaration-vol'] = 'Déclaration en cas de vol (2 jours ouvrés) — L.113-2';
      const rows = Object.keys(r).map((k) => {
        const st2 = stat[k] ? badge(stat[k].statut) : badge('V');
        return `<tr><td>${esc(labels[k] || k)} ${st2}</td><td><b>${new Date(r[k] + 'T12:00:00').toLocaleDateString('fr-FR')}</b></td></tr>`;
      }).join('');
      out.innerHTML = rows ? `<div class="tablewrap"><table class="flat"><tr><th>Échéance (base, règle)</th><th>Date limite</th></tr>${rows}</table></div><p class="muted">Jours fériés non décomptés automatiquement : les vérifier à la main (L.113-2, L.133-3).</p>` : 'Saisir au moins une date.';
      return;
    }
    const spec = CALC_FORMS[id];
    const r = spec.run(vals);
    out.innerHTML = spec.out(r);
  }

  VUES.calc = function (_p, id) {
    const c = DB.calculs.items.find((x) => x.id === id);
    if (!c) return '<p>Calculateur introuvable.</p>';
    return `<div class="toolbar no-print"><a class="btn" href="#/calculs">← Calculateurs</a></div>
      <h1>${esc(c.titre)} ${badge(c.statut)}</h1>
      <div class="card"><p><b>Formule.</b></p><div class="formule">${esc(c.formule)}</div>
      <p><b>Hypothèses :</b></p><ul>${c.hypotheses.map((h2) => `<li>${esc(h2)}</li>`).join('')}</ul>
      <p><b>Base juridique :</b> ${c.base_juridique.map(refLink).join(' · ')}</p>
      ${c.note ? `<p class="muted">${esc(c.note)}</p>` : ''}</div>
      <div class="card">${calcForm(c)}</div>
      <div class="card"><h3>Vecteurs de test embarqués</h3>
      <ul class="clean">${(c.vecteurs_test || []).map((v) => `<li><b>${esc(v.nom)}</b> — entrées ${esc(JSON.stringify(v.entrees))} → attendu ${esc(JSON.stringify(v.attendu))}${v.note ? `<br><small class="muted">${esc(v.note)}</small>` : ''}</li>`).join('')}</ul></div>`;
  };

  // -------------------------------------------------------------- méthode
  VUES.methode = function () {
    const scns = DB.scenarios.items;
    return `<h1>Méthode sinistre — 12 étapes</h1>
      <div class="toolbar"><button id="btn-reset-methode">Réinitialiser la checklist</button></div>
      <p>Scénarios fictifs déroulables : ${scns.map((s) => `<a class="btn" href="#/scenario/${s.id}">(${s.code}) ${esc(s.titre.slice(0, 40))}…</a>`).join(' ')}</p>
      <div class="checklist">
      ${DB.etapes_methode.items.map((e) => {
        const done = !!P.methode[e.id];
        return `<div class="etape ${done ? 'done' : ''}" id="${e.id}">
        <h3><input type="checkbox" data-etape="${e.id}" ${done ? 'checked' : ''}> ${e.ordre}. ${esc(e.titre)} ${badge(e.statut)}</h3>
        <p class="muted">${esc(e.objectif)}</p>
        <ul>${e.actions.map((a) => `<li>${esc(a)}</li>`).join('')}</ul>
        ${e.pieges && e.pieges.length ? `<p><b>Pièges :</b> ${e.pieges.map(esc).join(' · ')}</p>` : ''}
        ${e.pieceIds.length ? `<p><b>Pièces :</b> ${e.pieceIds.map((i) => esc((INDEX[i] || { item: {} }).item.label || i)).join(' · ')}</p>` : ''}
        ${e.referenceIds.length ? `<p><b>Références :</b> ${e.referenceIds.map(refLink).join(' · ')}</p>` : ''}
        ${e.calculIds.length ? `<p><b>Calculateurs :</b> ${e.calculIds.map(refLink).join(' · ')}</p>` : ''}
        </div>`;
      }).join('')}</div>`;
  };

  VUES.scenario = function (_p, id) {
    const s = DB.scenarios.items.find((x) => x.id === id);
    if (!s) return '<p>Scénario introuvable.</p>';
    const etapes = {}; DB.etapes_methode.items.forEach((e) => { etapes[e.id] = e; });
    const resultats = Object.entries(s.resultats_calcules).map(([k, rc]) => {
      const r = CalcEngine.runVector(rc.calcul, rc.entrees);
      return `<li><b>${esc(k)}</b> (${refLink(rc.calcul)}) : calculé en direct → <b>${esc(JSON.stringify(r))}</b><br><small class="muted">attendu : ${esc(JSON.stringify(rc.attendu))}${rc.note ? ' — ' + esc(rc.note) : ''}</small></li>`;
    }).join('');
    return `<div class="toolbar no-print"><a class="btn" href="#/methode">← Méthode</a><button onclick="window.print()">Imprimer (A4)</button></div>
      <div class="bandeau-fictif">SCÉNARIO ${s.code.toUpperCase()} — ${esc(s.marque)}. Exercice de méthode, aucune donnée réelle.</div>
      <h1>${esc(s.titre)} ${badge(s.statut)}</h1>
      <div class="card"><p>${esc(s.resume)}</p>
        <h3>Données</h3><div class="tablewrap"><table class="flat"><tr><th>Donnée</th><th>Valeur</th><th>Origine</th></tr>
        ${Object.entries(s.donnees).map(([k, d]) => `<tr><td>${esc(k)}</td><td>${typeof d.valeur === 'number' ? num(d.valeur) : esc(d.valeur)}</td><td>${d.origine === 'dossier' ? 'dossier' : '<b>fictif (ajout)</b>'}${d.note ? ` — <small>${esc(d.note)}</small>` : ''}</td></tr>`).join('')}</table></div>
        <h3>Résultats (formules vives, recalculés à l'affichage)</h3><ul class="clean">${resultats}</ul>
        <h3>Pièges</h3><ul>${s.pieges.map((p) => `<li>${esc(p)}</li>`).join('')}</ul>
        <p class="muted">EN : ${esc(s.version_en || '')}</p></div>
      <h2>Déroulé pas à pas</h2>
      ${s.deroule.map((st) => `<div class="card"><h3>${etapes[st.etapeId].ordre}. ${esc(etapes[st.etapeId].titre)}</h3><p>${esc(st.contenu)}</p></div>`).join('')}
      <p class="print-only bandeau-fictif">FICTIF — exercice de méthode.</p>`;
  };

  // -------------------------------------------------------------- entretien
  function questionById(id) { return DB.questions.items.find((q) => q.id === id); }

  VUES.entretien = function (params) {
    const grilleId = params.get('grille') || DB.grilles_entretien.items[0].id;
    const g = DB.grilles_entretien.items.find((x) => x.id === grilleId);
    const focusQ = params.get('q');
    if (params.get('star')) return starView();
    if (focusQ) setTimeout(() => { const el = document.getElementById(focusQ); if (el) el.scrollIntoView({ block: 'center' }); }, 30);
    const hist = (P.progression.historique_entrainements || []).slice(-5).reverse();
    return `<h1>Entretien</h1>
      <div class="filters">${DB.grilles_entretien.items.map((x) => `<a class="chip ${x.id === g.id ? 'on' : ''}" href="#/entretien?grille=${x.id}">${esc(x.poste)}</a>`).join('')}
      <a class="chip" href="#/entretien?star=1">Banque STAR</a></div>
      <div class="card"><h3>${esc(g.poste)}</h3>
        <p><b>Thèmes évalués :</b></p><ul>${g.themes_evalues.map((t) => `<li>${esc(t)}</li>`).join('')}</ul>
        <p><b>Ce qui fait recaler :</b> ${g.ce_qui_fait_recaler.map(esc).join(' · ')}</p>
        <p><b>À poser au recruteur :</b></p><ul>${g.a_poser.map((t) => `<li>${esc(t)}</li>`).join('')}</ul>
        <div class="toolbar"><button class="primary" id="btn-tirage" data-grille="${g.id}">Tirage aléatoire chronométré</button></div>
      </div>
      <div id="zone-tirage"></div>
      <h2>Questions de la grille</h2>
      ${g.questionIds.map((qid) => { const q = questionById(qid); if (!q) return ''; return `<div class="card" id="${q.id}"><p><b>${esc(q.question)}</b> <span class="badge theme">${esc(q.type)}${q.niveau ? ' · ' + esc(q.niveau) : ''}</span> ${badge(q.statut)}${q.teste ? ` <small class="muted">teste : ${esc(q.teste)}</small>` : ''}</p><p>${esc(q.reponse)}</p>${q.a_eviter ? `<p><small>À éviter : ${esc(q.a_eviter)}</small></p>` : ''}</div>`; }).join('')}
      ${hist.length ? `<h2>Derniers entraînements</h2><ul class="clean">${hist.map((h2) => `<li>${esc(h2.date)} — ${esc(h2.grille)} — note moyenne ${num(h2.moyenne)}/5 (${h2.n} question(s))</li>`).join('')}</ul>` : ''}`;
  };

  // Tirage chronométré
  const TIRAGE = { actif: false, questions: [], i: 0, notes: [], timer: null, restant: 90, grille: '' };
  function startTirage(grilleId) {
    const g = DB.grilles_entretien.items.find((x) => x.id === grilleId);
    const pool = g.questionIds.map(questionById).filter(Boolean).filter((q) => q.type !== 'a_poser');
    const n = Math.min(5, pool.length);
    const qs = [...pool].sort(() => Math.random() - 0.5).slice(0, n);
    Object.assign(TIRAGE, { actif: true, questions: qs, i: 0, notes: [], restant: 90, grille: g.poste });
    renderTirage();
    TIRAGE.timer = setInterval(() => {
      TIRAGE.restant--; const el = $('#chrono');
      if (el) { el.textContent = fmtChrono(TIRAGE.restant); el.className = 'timer' + (TIRAGE.restant <= 0 ? ' over' : (TIRAGE.restant <= 15 ? ' warn' : '')); }
    }, 1000);
  }
  function fmtChrono(s) { const a = Math.abs(s); const m = Math.floor(a / 60); const r = a % 60; return (s < 0 ? '−' : '') + m + ':' + String(r).padStart(2, '0'); }
  function renderTirage() {
    const z = $('#zone-tirage'); if (!z) return;
    if (!TIRAGE.actif) { z.innerHTML = ''; return; }
    if (TIRAGE.i >= TIRAGE.questions.length) {
      clearInterval(TIRAGE.timer);
      const moyenne = TIRAGE.notes.reduce((a, b) => a + b, 0) / TIRAGE.notes.length;
      P.progression.historique_entrainements.push({ date: new Date().toISOString().slice(0, 10), grille: TIRAGE.grille, n: TIRAGE.notes.length, moyenne: Math.round(moyenne * 10) / 10 });
      save();
      z.innerHTML = `<div class="card"><h3>Terminé</h3><p>Note moyenne auto-évaluée : <b>${num(moyenne)}/5</b>. Historique enregistré.</p></div>`;
      TIRAGE.actif = false;
      return;
    }
    const q = TIRAGE.questions[TIRAGE.i];
    TIRAGE.restant = 90;
    z.innerHTML = `<div class="card">
      <p class="muted">Question ${TIRAGE.i + 1}/${TIRAGE.questions.length} — réponds à voix haute, 90 s</p>
      <div class="timer" id="chrono">1:30</div>
      <p><b>${esc(q.question)}</b></p>
      <p><button id="btn-reveal">Voir la réponse attendue</button></p>
      <div id="rep" hidden><p>${esc(q.reponse)}</p>${q.a_eviter ? `<p><small>À éviter : ${esc(q.a_eviter)}</small></p>` : ''}
      <p>Auto-notation :</p><div class="notation">${[1, 2, 3, 4, 5].map((n) => `<button data-note="${n}">${n}</button>`).join('')}</div></div></div>`;
    $('#btn-reveal').onclick = () => { $('#rep').hidden = false; };
    z.querySelectorAll('[data-note]').forEach((b) => {
      b.onclick = () => { TIRAGE.notes.push(+b.dataset.note); TIRAGE.i++; renderTirage(); };
    });
  }

  // Banque STAR (données personnelles, éditables)
  function starView() {
    return `<h1>Banque STAR</h1>
      <div class="toolbar"><a class="btn" href="#/entretien">← Entretien</a><button class="primary" id="btn-star-add">Ajouter un récit</button></div>
      <p class="muted">Récits personnels — stockés localement, exportables depuis <a href="#/donnees">Mes données</a>. « [à compléter] » = chiffres à valider avant usage en entretien.</p>
      ${P.star.items.map((s, i) => `<div class="card">
        <h3>${esc(s.titre)} ${badge(s.statut)}</h3>
        ${['situation', 'tache', 'action', 'resultat', 'chiffres'].map((f) => `<label class="muted">${f.toUpperCase()}</label>
          <p><textarea data-star="${i}" data-field="${f}" rows="2" style="width:100%">${esc(s[f] || '')}</textarea></p>`).join('')}
      </div>`).join('')}`;
  }

  // ------------------------------------------------------------------ quiz
  function srsState(id) { return P.progression.srs[id] || { ease: 2.5, interval: 0, due: '1970-01-01', reps: 0 }; }
  function srsDue() {
    const today = new Date().toISOString().slice(0, 10);
    const pool = DB.questions.items.filter((q) => q.type === 'flash' || q.type === 'technique');
    return pool.filter((q) => srsState(q.id).due <= today);
  }
  function srsGrade(id, grade) { // 0 encore, 3 difficile, 4 bien, 5 facile
    const s = srsState(id);
    if (grade < 3) { s.interval = 0; s.reps = 0; }
    else {
      s.reps += 1;
      s.ease = Math.max(1.3, s.ease + (0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02)));
      s.interval = s.reps === 1 ? 1 : (s.reps === 2 ? 3 : Math.round(s.interval * s.ease));
    }
    const d = new Date(); d.setDate(d.getDate() + Math.max(s.interval, grade < 3 ? 0 : 1));
    s.due = d.toISOString().slice(0, 10);
    P.progression.srs[id] = s;
    save();
  }
  const QUIZ = { file: [], i: 0 };
  VUES.quiz = function () {
    QUIZ.file = srsDue().sort(() => Math.random() - 0.5).slice(0, 20);
    QUIZ.i = 0;
    if (!QUIZ.file.length) return `<h1>Quiz / répétition espacée</h1><div class="card"><p>Aucune carte due aujourd'hui. Reviens demain, ou <a href="#/entretien">entraîne-toi sur une grille</a>.</p></div>`;
    setTimeout(renderQuiz, 0);
    return `<h1>Quiz / répétition espacée</h1><p class="muted">${QUIZ.file.length} carte(s) dues (SM-2 simplifié). Généré depuis les fiches et questions.</p><div id="zone-quiz"></div>`;
  };
  function renderQuiz() {
    const z = $('#zone-quiz'); if (!z) return;
    if (QUIZ.i >= QUIZ.file.length) { z.innerHTML = '<div class="card"><p>Session terminée ✔</p></div>'; return; }
    const q = QUIZ.file[QUIZ.i];
    z.innerHTML = `<div class="card srs-card" id="carte">
      <p class="muted">${QUIZ.i + 1}/${QUIZ.file.length} ${badge(q.statut)}</p>
      <p><b>${esc(q.question)}</b></p>
      <p><button id="btn-voir" class="primary">Voir la réponse</button></p>
      <div class="srs-answer"><p>${esc(q.reponse)}</p>${q.note ? `<p class="muted"><small>${esc(q.note)}</small></p>` : ''}
      <div class="srs-actions">
        <button data-g="0">Encore</button><button data-g="3">Difficile</button>
        <button data-g="4" class="primary">Bien</button><button data-g="5">Facile</button>
      </div></div></div>`;
    $('#btn-voir').onclick = () => $('#carte').classList.add('revealed');
    z.querySelectorAll('[data-g]').forEach((b) => {
      b.onclick = () => { srsGrade(q.id, +b.dataset.g); QUIZ.i++; renderQuiz(); };
    });
  }

  // ---------------------------------------------------------------- lexique
  VUES.lexique = function (params) {
    const cat = params.get('cat') || '';
    const cats = [...new Set(DB.lexique_fr_en.items.map((l) => l.categorie))];
    const items = DB.lexique_fr_en.items.filter((l) => !cat || l.categorie === cat);
    return `<h1>Lexique FR ↔ EN</h1>
      <div class="filters">${cats.map((c) => `<a class="chip ${c === cat ? 'on' : ''}" href="#/lexique${c === cat ? '' : '?cat=' + c}">${esc(c)}</a>`).join('')}</div>
      <div class="tablewrap"><table class="flat"><tr><th>FR</th><th>EN</th><th>Référence</th><th></th></tr>
      ${items.map((l) => `<tr><td>${esc(l.fr)}</td><td>${esc(l.en)}</td><td>${esc(l.reference || '—')}</td><td>${badge(l.statut)}</td></tr>`).join('')}</table></div>`;
  };

  // ---------------------------------------------------------------- cabinets
  VUES.cabinets = function (params) {
    const focus = params.get('focus');
    if (focus) setTimeout(() => { const el = document.getElementById(focus); if (el) el.scrollIntoView({ block: 'center' }); }, 30);
    const items = [...DB.cabinets.items].sort((a, b) => a.priorite - b.priorite);
    return `<h1>Cibles (cabinets, assureurs, conseils)</h1>
      ${items.map((c) => `<div class="card" id="${c.id}">
        <h3>${esc(c.nom)} <span class="badge theme">priorité ${c.priorite === 9 ? 'plan B' : c.priorite}</span> ${badge(c.statut)}</h3>
        <p class="muted">${esc(c.type)} · ${esc(c.bassin)} · ${esc(c.implantation || '')}</p>
        <p><b>Poste visé :</b> ${esc(c.poste_vise)} — <b>canal :</b> ${esc(c.canal)}</p>
        <p>${esc(c.faits)}</p>
        <p class="no-print"><a class="btn" href="#/candidatures?nouvelle=${encodeURIComponent(c.nom)}">Créer une candidature</a></p>
      </div>`).join('')}`;
  };

  // ------------------------------------------------------------ candidatures
  VUES.candidatures = function (params) {
    const pre = params.get('nouvelle');
    const etapes = SEED.candidatures.etapes_pipeline;
    const kpi = SEED.candidatures.kpi;
    const semaine = (() => { const d = new Date(); const j = (d.getDay() + 6) % 7; d.setDate(d.getDate() - j); return d.toISOString().slice(0, 10); })();
    const cetteSemaine = P.candidatures.items.filter((c) => (c.historique || []).some((h2) => h2.date >= semaine));
    if (pre) setTimeout(() => ouvreCandidature(null, pre), 50);
    return `<h1>Candidatures et contacts</h1>
      <div class="kpi">
        <div class="stat"><b>${P.candidatures.items.length}</b> candidatures</div>
        <div class="stat"><b>${cetteSemaine.length}</b> actives cette semaine <small>(objectif ${kpi.candidatures_par_semaine}/sem)</small></div>
        <div class="stat"><b>${P.candidatures.items.filter((c) => c.etape.startsWith('entretien')).length}</b> en entretien</div>
      </div>
      <p class="muted">${esc(kpi.note)}</p>
      <div class="toolbar"><button class="primary" id="btn-cand-add">Nouvelle candidature</button></div>
      <div class="tablewrap"><table class="flat"><tr><th>Cible</th><th>Poste</th><th>Étape</th><th>Contact</th><th>Dernier événement</th><th></th></tr>
      ${P.candidatures.items.map((c, i) => {
        const last = (c.historique || []).slice(-1)[0];
        return `<tr><td>${esc(c.cible)}</td><td>${esc(c.poste)}</td><td><b>${esc(c.etape)}</b></td><td>${esc(c.contact || '')}</td>
        <td>${last ? esc(last.date + ' — ' + last.note) : ''}</td>
        <td><button data-edit-cand="${i}">Modifier</button></td></tr>`;
      }).join('')}</table></div>
      <dialog id="dlg-cand"><form method="dialog" class="calc" style="min-width:280px">
        <h3 id="dlg-titre">Candidature</h3>
        <input type="hidden" name="idx" value="">
        <label>Cible</label><input name="cible" list="cibles"><datalist id="cibles">${DB.cabinets.items.map((c) => `<option>${esc(c.nom)}</option>`).join('')}</datalist>
        <label>Poste</label><input name="poste">
        <label>Étape</label><select name="etape">${etapes.map((e) => `<option>${e}</option>`).join('')}</select>
        <label>Contact (nom, mail…)</label><input name="contact">
        <label>Note d'événement (ajoutée à l'historique avec la date du jour)</label><input name="note">
        <p><button class="primary" value="ok">Enregistrer</button> <button value="suppr" id="btn-cand-del">Supprimer</button> <button value="annuler">Annuler</button></p>
      </form></dialog>`;
  };
  function ouvreCandidature(idx, cible) {
    const dlg = $('#dlg-cand'); if (!dlg) return;
    const f = dlg.querySelector('form');
    f.elements.idx.value = idx == null ? '' : idx;
    const c = idx != null ? P.candidatures.items[idx] : { cible: cible || '', poste: '', etape: 'repérée', contact: '' };
    f.elements.cible.value = c.cible; f.elements.poste.value = c.poste;
    f.elements.etape.value = c.etape; f.elements.contact.value = c.contact || '';
    f.elements.note.value = '';
    dlg.showModal();
    dlg.onclose = () => {
      if (dlg.returnValue === 'ok') {
        const date = new Date().toISOString().slice(0, 10);
        const item = idx != null ? P.candidatures.items[idx] : { id: 'cand-' + Date.now(), statut: 'NV', source_url: null, date_verification: null, note: null, historique: [] };
        item.cible = f.elements.cible.value; item.poste = f.elements.poste.value;
        item.etape = f.elements.etape.value; item.contact = f.elements.contact.value;
        if (f.elements.note.value) item.historique.push({ date, note: f.elements.note.value });
        if (idx == null) P.candidatures.items.push(item);
        save(); route();
      } else if (dlg.returnValue === 'suppr' && idx != null) {
        if (confirm('Supprimer cette candidature ?')) { P.candidatures.items.splice(idx, 1); save(); route(); }
      }
    };
  }

  // --------------------------------------------------------------- trames
  VUES.trames = function (params) {
    const focus = params.get('focus');
    if (focus) setTimeout(() => { const el = document.getElementById(focus); if (el) el.scrollIntoView({ block: 'center' }); }, 30);
    return `<h1>Trames (rapports, pitchs, messages)</h1>
      ${DB.trames.items.map((t) => `<div class="card" id="${t.id}"><h3>${esc(t.titre)} <span class="badge theme">${esc(t.categorie)}</span> ${badge(t.statut)}</h3>
      <ul>${t.contenu.map((l) => `<li>${esc(l)}</li>`).join('')}</ul>
      ${(t.phrases_fr || []).length ? `<p><b>FR :</b> ${t.phrases_fr.map(esc).join(' ')}</p>` : ''}
      ${(t.phrases_en || []).length ? `<p><b>EN :</b> ${t.phrases_en.map(esc).join(' ')}</p>` : ''}
      ${t.note ? `<p class="muted">${esc(t.note)}</p>` : ''}</div>`).join('')}`;
  };

  // -------------------------------------------------------------- à vérifier
  VUES.averifier = function () {
    const items = [...DB.a_verifier.items].sort((a, b) => a.priorite - b.priorite);
    return `<h1>À vérifier</h1>
      <p class="muted">Tout ce qui est NV ou signalé à contrôler, avec la source primaire à ouvrir. Ne passe jamais un élément à V sans ce contrôle (URL + date).</p>
      ${items.map((a) => `<div class="card"><h3>${esc(a.sujet)} <span class="badge theme">priorité ${a.priorite}</span> ${badge(a.statut)}</h3>
      <p>${esc(a.detail)}</p>
      ${a.source_primaire ? `<p><b>Source primaire :</b> <a href="${esc(a.source_primaire)}" rel="noopener">${esc(a.source_primaire)}</a></p>` : ''}
      ${a.note ? `<p class="muted">${esc(a.note)}</p>` : ''}</div>`).join('')}
      <h2>Références NV</h2>
      <ul class="clean">${DB.references.items.filter((r) => r.statut === 'NV').map((r) => `<li>${refLink(r.id)}</li>`).join('')}</ul>`;
  };

  // -------------------------------------------------------------- ressources
  VUES.ressources = function () {
    const types = [...new Set(DB.ressources.items.map((r) => r.type))];
    return `<h1>Ressources</h1>
      ${types.map((t) => `<h2>${esc(t)}</h2><ul class="clean">
        ${DB.ressources.items.filter((r) => r.type === t).map((r) => `<li>${r.url ? `<a href="${esc(r.url)}" rel="noopener"><b>${esc(r.nom)}</b></a>` : `<b>${esc(r.nom)}</b>`} ${badge(r.statut)}<br><small class="muted">${esc(r.usage)}${r.note ? ' — ' + esc(r.note) : ''}</small></li>`).join('')}</ul>`).join('')}`;
  };

  // ------------------------------------------------------------- mes données
  VUES.donnees = function () {
    return `<h1>Mes données</h1>
      <div class="card"><h3>Export</h3>
      <p>Télécharge un JSON de tes données personnelles (STAR, candidatures, notes, progression, checklist méthode). Les données de référence, régénérées par build.py, n'y figurent pas : une mise à jour de l'outil n'écrase jamais tes données.</p>
      <p><button class="primary" id="btn-export">Exporter mes données (JSON)</button></p></div>
      <div class="card"><h3>Import</h3>
      <p>Recharge un export précédent (remplace les données personnelles actuelles après confirmation).</p>
      <p><input type="file" id="inp-import" accept="application/json"></p></div>
      <div class="card"><h3>Réinitialiser</h3>
      <p><button id="btn-reset">Revenir aux données d'origine</button></p></div>`;
  };

  // ---------------------------------------------------------------- routage
  const NAV = [
    ['#/accueil', 'Accueil'], ['#/fiches', 'Fiches'], ['#/references', 'Références'],
    ['#/calculs', 'Calculs'], ['#/methode', 'Méthode'], ['#/entretien', 'Entretien'],
    ['#/quiz', 'Quiz'], ['#/lexique', 'Lexique'], ['#/trames', 'Trames'],
    ['#/cabinets', 'Cibles'], ['#/candidatures', 'Candidatures'],
    ['#/ressources', 'Ressources'], ['#/averifier', 'À vérifier'], ['#/donnees', 'Mes données'],
  ];
  function route() {
    const hash = location.hash || '#/accueil';
    const [path, qs] = hash.split('?');
    const parts = path.replace(/^#\//, '').split('/');
    const vue = parts[0] || 'accueil';
    const arg = parts[1] ? decodeURIComponent(parts[1]) : null;
    const params = new URLSearchParams(qs || '');
    const fn = VUES[vue] || VUES.accueil;
    main().innerHTML = fn(params, arg);
    document.querySelectorAll('nav.tabs a').forEach((a) => {
      a.classList.toggle('active', a.getAttribute('href').split('?')[0] === '#/' + vue);
    });
    window.scrollTo(0, 0);
    bind(vue);
  }

  function bind(vue) {
    // délégation des actions propres à chaque vue
    main().querySelectorAll('[data-run]').forEach((b) => { b.onclick = () => runCalc(b.dataset.run); });
    main().querySelectorAll('[data-etape]').forEach((cb) => {
      cb.onchange = () => { P.methode[cb.dataset.etape] = cb.checked; save(); cb.closest('.etape').classList.toggle('done', cb.checked); };
    });
    const r1 = $('#btn-reset-methode'); if (r1) r1.onclick = () => { if (confirm('Décocher les 12 étapes ?')) { P.methode = {}; save(); route(); } };
    const t1 = $('#btn-tirage'); if (t1) t1.onclick = () => startTirage(t1.dataset.grille);
    const sa = $('#btn-star-add'); if (sa) {
      sa.onclick = () => {
        const titre = prompt('Titre du récit :'); if (!titre) return;
        P.star.items.push({ id: 'star-' + Date.now(), titre, situation: '', tache: '', action: '', resultat: '', chiffres: '', tags: [], statut: 'NV', source_url: null, date_verification: null, note: null });
        save(); route();
      };
    }
    main().querySelectorAll('[data-star]').forEach((ta) => {
      ta.onchange = () => { P.star.items[+ta.dataset.star][ta.dataset.field] = ta.value; save(); };
    });
    const ca = $('#btn-cand-add'); if (ca) ca.onclick = () => ouvreCandidature(null);
    main().querySelectorAll('[data-edit-cand]').forEach((b) => { b.onclick = () => ouvreCandidature(+b.dataset.editCand); });
    const ex = $('#btn-export'); if (ex) {
      ex.onclick = () => {
        const blob = new Blob([JSON.stringify(P, null, 2)], { type: 'application/json' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'expert-assurance-mes-donnees-' + new Date().toISOString().slice(0, 10) + '.json';
        a.click();
        setTimeout(() => URL.revokeObjectURL(a.href), 5000);
      };
    }
    const im = $('#inp-import'); if (im) {
      im.onchange = () => {
        const f = im.files[0]; if (!f) return;
        f.text().then((txt) => {
          const data = JSON.parse(txt);
          if (!data.star || !data.candidatures) { alert('Fichier non reconnu.'); return; }
          if (confirm('Remplacer les données personnelles actuelles par cet export ?')) {
            Object.keys(data).forEach((k) => { P[k] = data[k]; });
            save(); route();
          }
        }).catch(() => alert('JSON invalide.'));
      };
    }
    const rz = $('#btn-reset'); if (rz) {
      rz.onclick = () => {
        if (confirm('Effacer toutes les données personnelles (STAR, candidatures, progression) ?')) {
          try { localStorage.removeItem(LS_KEY); } catch (e) { /* */ }
          location.reload();
        }
      };
    }
  }

  // ---------------------------------------------------------------- amorçage
  function boot() {
    $('#nav').innerHTML = NAV.map(([h2, l]) => `<a href="${h2}">${l}</a>`).join('');
    $('#btn-theme').onclick = () => {
      P.ui.theme = P.ui.theme === 'auto' ? 'dark' : (P.ui.theme === 'dark' ? 'light' : 'auto');
      save(); applyTheme();
    };
    const si = $('#inp-recherche');
    si.addEventListener('input', () => {
      const q = si.value.trim();
      if (q.length >= 2) location.hash = '#/recherche?q=' + encodeURIComponent(q);
    });
    si.addEventListener('keydown', (e) => { if (e.key === 'Enter') location.hash = '#/recherche?q=' + encodeURIComponent(si.value.trim()); });
    window.addEventListener('hashchange', route);
    applyTheme();
    route();
  }
  document.addEventListener('DOMContentLoaded', boot);
})();
