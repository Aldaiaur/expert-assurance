/* Moteur de calcul — source unique des formules côté application.
   Également chargé par Node pour les tests (résultats identiques app/Excel). */
(function (root) {
  'use strict';

  function round2(x) { return Math.round(x * 100) / 100; }

  const CalcEngine = {

    /** Règle proportionnelle de capitaux (L.121-5). */
    rpCapitaux({ dommage, declare, reel }) {
      const coeff = reel > 0 ? Math.min(1, declare / reel) : 1;
      return { coeff: round2(coeff), indemnite: round2(Math.min(dommage, dommage * coeff)) };
    },

    /** Règle proportionnelle de prime (L.113-9). */
    rpPrime({ dommage, prime_payee, prime_due }) {
      if (!prime_due) return { coeff: null, indemnite: null };
      const coeff = Math.min(1, prime_payee / prime_due);
      return { coeff: round2(coeff), indemnite: round2(Math.min(dommage, dommage * coeff)) };
    },

    /** Chaîne VàN → vétusté → RP → franchise → plafond → différé. */
    chaineIndemnite({ dommage_van, taux_vetuste, declare, reel, franchise, plafond, taux_rachat_max }) {
      const tr = (taux_rachat_max == null) ? 0.25 : taux_rachat_max;
      const vetuste = dommage_van * taux_vetuste;
      const vd = dommage_van - vetuste;
      const coeff = reel > 0 ? Math.min(1, declare / reel) : 1;
      let immediat = Math.max(0, vd * coeff - (franchise || 0));
      if (plafond != null && plafond > 0) immediat = Math.min(immediat, plafond);
      const differe = Math.min(vetuste, tr * vd) * coeff;
      return {
        vetuste: round2(vetuste), valeur_vetuste_deduite: round2(vd), coeff: round2(coeff),
        immediat: round2(immediat), differe: round2(differe),
      };
    },

    /** Perte d'exploitation (marge brute assurée). */
    pe({ baisse_ca, taux_marge, frais_supp, perte_evitee, economies }) {
      const margePerdue = baisse_ca * taux_marge;
      const fraisRetenus = Math.min(frais_supp || 0, perte_evitee || 0);
      return {
        marge_perdue: round2(margePerdue), frais_retenus: round2(fraisRetenus),
        perte: round2(margePerdue + fraisRetenus - (economies || 0)),
      };
    },

    /** Plafonds transport. Renvoie {plafond_dts|plafond_eur, en_euros?}. */
    plafondsTransport({ regime, poids_kg, nb_colis, taux_montreal, cours_dts }) {
      const colis = nb_colis || 1;
      let out = {};
      switch (regime) {
        case 'cmr': out = { plafond_dts: round2(8.33 * poids_kg) }; break;
        case 'montreal': out = { plafond_dts: round2((taux_montreal == null ? 26 : taux_montreal) * poids_kg) }; break;
        case 'hague_visby': out = { plafond_dts: round2(Math.max(666.67 * colis, 2 * poids_kg)) }; break;
        case 'ctg_moins_3t': out = { plafond_eur: round2(Math.min(33 * poids_kg, 1000 * colis)) }; break;
        case 'ctg_3t_et_plus': out = { plafond_eur: round2(Math.min(20 * poids_kg, 3200 * (poids_kg / 1000))) }; break;
        default: out = {};
      }
      if (out.plafond_dts != null && cours_dts) out.en_euros = round2(out.plafond_dts * cours_dts);
      return out;
    },

    /** Échéancier : dates ISO → échéances calculées. */
    echeancier({ date_sinistre, date_declaration, date_livraison, date_accord }) {
      const p = (iso) => (iso ? new Date(iso + 'T12:00:00') : null);
      const fmt = (d) => d.toISOString().slice(0, 10);
      const addD = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };
      const addM = (d, n) => { const x = new Date(d); x.setMonth(x.getMonth() + n); return x; };
      const addOuvres = (d, n) => { // jours ouvrés lun-ven, fériés non décomptés (à vérifier à la main)
        let x = new Date(d), c = 0;
        while (c < n) { x = addD(x, 1); const j = x.getDay(); if (j !== 0 && j !== 6) c++; }
        return x;
      };
      const S = p(date_sinistre), D = p(date_declaration), L = p(date_livraison), A = p(date_accord);
      const out = {};
      if (S) {
        out['d-declaration'] = fmt(addOuvres(S, 5));
        out['d-declaration-vol'] = fmt(addOuvres(S, 2));
        out['d-aggravation'] = fmt(addD(S, 15));
        out['d-prescription-assurance'] = fmt(addM(S, 24));
      }
      if (D) {
        out['d-reponse-sans-expert'] = fmt(addM(D, 2));
        out['d-reponse-avec-expert'] = fmt(addM(D, 6));
        out['d-catnat-info'] = fmt(addM(D, 1));
      }
      if (A) out['d-paiement'] = fmt(addD(A, 21));
      if (L) {
        out['d-protestation'] = fmt(addD(L, 3));
        out['d-cmr-non-apparent'] = fmt(addD(L, 7));
        out['d-cmr-retard'] = fmt(addD(L, 21));
        out['d-presomption-perte'] = fmt(addD(L, 30));
        out['d-prescription-transport'] = fmt(addM(L, 12));
        out['d-cmr-prescription'] = fmt(addM(L, 12));
      }
      return out;
    },

    /** Exécute un vecteur de test de calculs.json ; renvoie {ok, obtenu}. */
    runVector(calcId, entrees) {
      const map = {
        'calc-rp-capitaux': (e) => this.rpCapitaux(e),
        'calc-rp-prime': (e) => this.rpPrime(e),
        'calc-chaine-indemnite': (e) => this.chaineIndemnite(e),
        'calc-pe': (e) => this.pe(e),
        'calc-plafonds-transport': (e) => this.plafondsTransport(e),
        'calc-echeancier': (e) => this.echeancier(e),
      };
      return map[calcId] ? map[calcId].call(this, entrees) : null;
    },
  };

  root.CalcEngine = CalcEngine;
  if (typeof module !== 'undefined' && module.exports) module.exports = CalcEngine;
})(typeof globalThis !== 'undefined' ? globalThis : this);
