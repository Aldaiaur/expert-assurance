/* Rend les diagrammes Mermaid du modèle systémique en SVG autonomes.
   À relancer UNIQUEMENT quand une source Mermaid change :
       npm install --prefix tools/.mermaid mermaid@11.4.1   (une fois)
       node tools/render_diagrams.cjs
   Les SVG produits (data/diagrams/*.svg) sont versionnés : build.py les
   inline sans dépendre de Mermaid ni du réseau. Chaque SVG porte l'empreinte
   SHA-256 de sa source ; un test échoue si elle ne correspond plus. */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { chromium } = require('playwright');

const ROOT = path.resolve(__dirname, '..');
const MERMAID = path.join(__dirname, '.mermaid', 'node_modules', 'mermaid', 'dist', 'mermaid.min.js');
const OUT = path.join(ROOT, 'data', 'diagrams');

(async () => {
  if (!fs.existsSync(MERMAID)) {
    console.error('Mermaid absent : npm install --prefix tools/.mermaid mermaid@11.4.1');
    process.exit(2);
  }
  const modele = JSON.parse(fs.readFileSync(path.join(ROOT, 'data', 'reference', 'modele_systemique.json'), 'utf8'));
  const diagrammes = modele.items.filter((i) => i.type === 'diagramme');
  fs.mkdirSync(OUT, { recursive: true });

  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.setContent('<!doctype html><html><body></body></html>');
  await page.addScriptTag({ path: MERMAID });
  await page.evaluate(() => {
    window.mermaid.initialize({
      startOnLoad: false, theme: 'neutral', securityLevel: 'strict',
      htmlLabels: false, flowchart: { htmlLabels: false, curve: 'basis', padding: 12 },
      themeVariables: { fontFamily: 'system-ui, -apple-system, Segoe UI, Roboto, sans-serif', fontSize: '14px' },
    });
  });

  for (const d of diagrammes) {
    const svg = await page.evaluate(async ({ id, code }) => {
      const res = await window.mermaid.render('svg-' + id, code);
      return res.svg;
    }, { id: d.id, code: d.mermaid });
    const sha = crypto.createHash('sha256').update(d.mermaid, 'utf8').digest('hex');
    const file = path.join(OUT, d.id + '.svg');
    fs.writeFileSync(file, `<!-- mermaid-sha256: ${sha} -->\n` + svg, 'utf8');
    console.log('Rendu :', path.relative(ROOT, file), Math.round(svg.length / 1024) + ' ko');
  }
  await browser.close();
})().catch((e) => { console.error('ÉCHEC', e); process.exit(1); });
