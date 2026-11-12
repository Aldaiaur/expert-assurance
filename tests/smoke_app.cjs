/* Test hors ligne de app/index.html dans Chromium (Playwright préinstallé).
   Échoue si : une requête réseau part, une vue est vide, un calcul
   d'acceptation est faux, la marque FICTIF manque, ou la persistance échoue. */
const path = require('path');
const { chromium } = require('playwright');

(async () => {
  const appPath = path.resolve(__dirname, '..', 'app', 'index.html');
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 390, height: 800 } });
  const netReqs = [];
  page.on('request', (r) => { const u = r.url(); if (!u.startsWith('file://')) netReqs.push(u); });
  const errors = [];
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
  page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()); });

  await page.goto('file://' + appPath, { waitUntil: 'load' });
  await page.waitForTimeout(300);

  const vues = ['systeme', 'fiches', 'references', 'calculs', 'methode', 'entretien', 'quiz', 'lexique',
    'trames', 'cabinets', 'candidatures', 'ressources', 'averifier', 'donnees', 'accueil'];
  for (const v of vues) {
    await page.evaluate((vv) => { location.hash = '#/' + vv; }, v);
    await page.waitForTimeout(100);
    const txt = await page.evaluate(() => document.getElementById('vue').innerText.length);
    if (txt < 40) errors.push('vue vide: ' + v);
  }

  await page.evaluate(() => { location.hash = '#/systeme'; });
  await page.waitForTimeout(200);
  const nbSvg = await page.evaluate(() => document.querySelectorAll('#vue .diagramme svg').length);
  if (nbSvg !== 2) errors.push('onglet Système : ' + nbSvg + ' diagramme(s) au lieu de 2');
  const nbActeurs = await page.evaluate(() => document.querySelectorAll('#vue table.acteurs tr').length - 1);
  if (nbActeurs < 14) errors.push('onglet Système : ' + nbActeurs + ' acteurs');

  await page.evaluate(() => { location.hash = '#/scenario/scn-a'; });
  await page.waitForTimeout(150);
  if (!(await page.evaluate(() => document.body.innerText.includes('FICTIF')))) {
    errors.push('marque FICTIF absente du scénario');
  }

  await page.evaluate(() => { location.hash = '#/calc/calc-rp-capitaux'; });
  await page.waitForTimeout(150);
  await page.fill('input[name=dommage]', '200000');
  await page.fill('input[name=declare]', '800000');
  await page.fill('input[name=reel]', '1000000');
  await page.click('[data-run=calc-rp-capitaux]');
  if (!(await page.textContent('#r-calc-rp-capitaux')).includes('160')) errors.push('RP capitaux UI fausse');

  const acc = await page.evaluate(() => {
    const a = CalcEngine.rpCapitaux({ dommage: 200000, declare: 800000, reel: 1000000 });
    const b = CalcEngine.chaineIndemnite({ dommage_van: 900000, taux_vetuste: 0.2, declare: 3000000, reel: 3600000, franchise: 10000, plafond: null, taux_rachat_max: 0.25 });
    const c = CalcEngine.plafondsTransport({ regime: 'cmr', poids_kg: 8000, nb_colis: 1 });
    return [a.indemnite, b.immediat, b.differe, c.plafond_dts];
  });
  const attendu = [160000, 590000, 150000, 66640];
  attendu.forEach((v, i) => { if (acc[i] !== v) errors.push(`acceptation[${i}]: ${acc[i]} ≠ ${v}`); });

  await page.evaluate(() => { location.hash = '#/candidatures'; });
  await page.waitForTimeout(120);
  await page.click('#btn-cand-add');
  await page.fill('#dlg-cand input[name=cible]', 'Test');
  await page.click('#dlg-cand button[value=ok]');
  await page.waitForTimeout(120);
  const n = await page.evaluate(() => JSON.parse(localStorage.getItem('expert-assurance-perso-v1')).candidatures.items.length);
  if (n !== 1) errors.push('persistance candidature: ' + n);

  if (netReqs.length) errors.push('requêtes réseau: ' + netReqs.join(', '));
  if (errors.length) { console.error(errors.join('\n')); process.exit(1); }
  console.log('OK hors ligne');
  await browser.close();
})().catch((e) => { console.error('FATAL', e); process.exit(2); });
