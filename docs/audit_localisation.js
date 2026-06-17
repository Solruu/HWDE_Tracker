#!/usr/bin/env node
/* ============================================================================
 * audit_localisation.js
 * ----------------------------------------------------------------------------
 * Audit de la couverture FR du tracker HWDE.
 *
 * Principe : le tracker traduit MAPS_RAW à la volée via des dictionnaires
 * (MIS_PRE, MIS_PH, LOOT_T, BASE_LOC, DIR_MAP, SEARCH_PH) appliqués par des
 * fonctions pures (tMis, tLoot, tKeep, tBase, tSearch, tSkull).
 *
 * Ce script EXTRAIT ces dictionnaires et fonctions DEPUIS index.html, les
 * exécute réellement (donc résultat fidèle au rendu navigateur), applique la
 * bonne fonction à chaque champ, puis liste les chaînes qui contiennent
 * ENCORE de l'anglais après traduction — regroupées par champ et triées par
 * fréquence, pour donner une todo-list d'enrichissement des dictionnaires.
 *
 * USAGE :
 *   node audit_localisation.js [chemin/index.html]   (défaut: ./index.html)
 *   node audit_localisation.js index.html --csv > rapport.csv
 *   node audit_localisation.js index.html --field m  (audite un seul champ)
 * ========================================================================== */

const fs = require('fs');
const vm = require('vm');

const args = process.argv.slice(2);
const htmlPath = args.find(a => !a.startsWith('--')) || 'index.html';
const csvMode  = args.includes('--csv');
const onlyField = (() => { const i = args.indexOf('--field'); return i >= 0 ? args[i + 1] : null; })();

const html = fs.readFileSync(htmlPath, 'utf8');

/* ── 1. Extraction d'une const top-level par son nom ───────────────────────
 * On repère `const NAME=` et on lit jusqu'au prochain `\nconst ` (les consts
 * du tracker sont déclarées à plat, une par bloc). */
function extractConst(name) {
  const re = new RegExp('\\nconst ' + name + '\\s*=');
  const m = re.exec(html);
  if (!m) throw new Error('const introuvable: ' + name);
  const start = m.index + m[0].length;
  const end = html.indexOf('\nconst ', start);
  return html.slice(start, end < 0 ? undefined : end).trim().replace(/;\s*$/, '');
}

/* ── 2. Extraction d'une fonction par son nom ──────────────────────────────
 * Lecture par équilibrage d'accolades à partir de `function NAME(`. */
function extractFunction(name) {
  const sig = 'function ' + name + '(';
  const i = html.indexOf(sig);
  if (i < 0) throw new Error('fonction introuvable: ' + name);
  let depth = 0, started = false, j = i;
  for (; j < html.length; j++) {
    const c = html[j];
    if (c === '{') { depth++; started = true; }
    else if (c === '}') { depth--; if (started && depth === 0) { j++; break; } }
  }
  return html.slice(i, j);
}

/* ── 3. Construction d'un sandbox avec les vrais dictionnaires + fonctions ── */
const sandbox = {};
vm.createContext(sandbox);

// Dictionnaires (ordre indifférent, ils ne se référencent pas entre eux)
const DICT_CONSTS = ['BASE_LOC', 'MIS_PRE', 'MIS_PH', 'SEARCH_PH', 'LOOT_T', 'DIR_MAP', 'EFR', 'NAMES'];
// DIR_RE est une regex utilisée par tKeep
const REGEX_CONSTS = ['DIR_RE'];

for (const name of [...DICT_CONSTS, ...REGEX_CONSTS]) {
  vm.runInContext('const ' + name + '=' + extractConst(name) + ';', sandbox);
}

// Fonctions de traduction pures (déclarées dans l'ordre de dépendance)
const FUNCS = ['tBase', 'tKeep', 'tName', 'tMis', 'tLoot', 'tSearch', 'tSkull'];
for (const fn of FUNCS) {
  vm.runInContext(extractFunction(fn), sandbox);
}
// Exposer chaque fonction comme référence appelable depuis Node.
const T = {};
for (const fn of FUNCS) {
  T[fn] = vm.runInContext(fn, sandbox);
}

// MAPS_RAW et GUIDE : on récupère la valeur de retour (les `const` dans un
// contexte VM ne deviennent pas des propriétés énumérables du sandbox).
const MAPS_RAW = vm.runInContext('(' + extractConst('MAPS_RAW') + ')', sandbox);
const GUIDE    = vm.runInContext('(' + extractConst('GUIDE') + ')', sandbox);

/* ── 4. Détecteur d'anglais résiduel ───────────────────────────────────────
 * Heuristique par mots-marqueurs anglais. Les noms propres (personnages,
 * lieux non couverts) produisent des faux positifs — signalés comme tels. */
const EN_WORDS = new RegExp('\\b(' + [
  'the', 'of', 'and', 'with', 'without', 'enemies', 'enemy', 'Keep', 'Keeps',
  'Defeat', 'Complete', 'Battle', 'Rule', 'Heart', 'Container', 'Piece',
  'Outfit', 'Robes', 'Clothes', 'Tunic', 'Costume', 'Material', 'Weapon',
  'Skulltula', 'Warrior', 'light', 'Room', 'Hall', 'Square', 'Field', 'Base',
  'Castle', 'Temple', 'Bridge', 'Gate', 'Cave', 'Island', 'Tower', 'Forest',
  'Mountain', 'River', 'Lake', 'Desert', 'Boulder', 'Hood', 'Mask', 'Bandana',
  'Jewel', 'Earrings', 'Pendant', 'Book', 'Sorcery', 'Spear', 'Sword', 'Blade',
  'Rod', 'Gauntlets', 'Gloves', 'Boots', 'Hat', 'Cap', 'Crown', 'Ring',
  'collision', 'advances', 'sleeps', 'cries', 'voice', 'army', 'leader',
  'Exit', 'Entrance', 'North', 'South', 'East', 'West', 'Central', 'Sage',
  'Pirate', 'Demon', 'Lord', 'Gerudo', 'Goron', 'Zora', 'Hylian'
].join('|') + ')\\b');

// Noms propres connus (réduisent les faux positifs dans le rapport)
const PROPER = /\b(Link|Zelda|Impa|Lana|Cia|Agitha|Midna|Darunia|Ruto|Sheik|Ganondorf|Ghirahim|Zant|Fi|Tingle|Linkle|Marin|Toon|Tetra|Medli|Wizzro|Volga|Cya|Yuga|Ravio|Skull Kid|Young Link|King)\b/g;

// Marqueurs FR : si présents, la chaîne est déjà (au moins partiellement) traduite.
const FR_WORDS = /\b(Réalisez|Complétez|Éliminez|Capturez|Utilisez|Bombez|Brûlez|Creusez|Poussez|Visez|Tirez|Emplacement|au nord|au sud|à l'est|à l'ouest|depuis|sans perdre|première mission|forts?|ennemis?|impasse|mur|salle|zone|Règle|Pas de|Pas d')\b/i;

function residualEnglish(s) {
  if (!s) return null;
  // On retire noms propres + niveaux pour ne pas les compter comme anglais.
  const stripped = s.replace(PROPER, '').replace(/\b(Lv|Niv)\.?\d?\+?\b/g, '');
  if (!EN_WORDS.test(stripped)) return null;
  // Si la chaîne contient déjà beaucoup de français ET peu de mots anglais,
  // on la classe « partiellement traduite » plutôt que « anglais résiduel ».
  const enHits = (stripped.match(new RegExp(EN_WORDS.source, 'g')) || []).length;
  const frHit = FR_WORDS.test(s);
  if (frHit && enHits <= 2) return null;   // ex. skulltulas FR avec "Switch"/"Place"
  return s;
}

/* ── 5. Application de la bonne fonction par champ ──────────────────────────
 * Reproduit ce que fait buildDetail() : quel champ passe par quel traducteur. */
const FIELD_TRANSLATOR = {
  m:  s => T.tMis(s),
  ta: s => T.tMis(s),
  la: s => T.tLoot(s),
  lv: s => T.tLoot(s),
  t:  s => T.tLoot(s),          // t est un tableau, géré ci-dessous
};
// Champs GUIDE
const GUIDE_TRANSLATOR = {
  skull_1: s => T.tSkull(s),
  skull_2: s => T.tSkull(s),
  boss_key: s => T.tKeep(s),
  'search.desc': s => T.tSearch(s),
};

const report = {};       // field -> Map(résidu -> {count, sample[]})
function note(field, original, translated) {
  const r = residualEnglish(translated);
  if (!r) return;
  if (!report[field]) report[field] = new Map();
  const m = report[field];
  if (!m.has(translated)) m.set(translated, { count: 0, original });
  m.get(translated).count++;
}

/* MAPS_RAW */
for (const [mapName, cells] of Object.entries(MAPS_RAW)) {
  for (const [coord, cell] of Object.entries(cells)) {
    for (const field of ['m', 'ta', 'la', 'lv']) {
      if (onlyField && field !== onlyField) continue;
      const v = cell[field];
      if (typeof v === 'string' && v) {
        // lv peut contenir plusieurs segments séparés par ' · '
        for (const seg of v.split(' · ')) {
          if (seg.trim()) note(field, seg, FIELD_TRANSLATOR[field](seg));
        }
      }
    }
    if ((!onlyField || onlyField === 't') && Array.isArray(cell.t)) {
      for (const x of cell.t) if (x) note('t', x, T.tLoot(x));
    }
    // locations (fées / foods) → tKeep
    if (!onlyField || onlyField === 'location') {
      if (cell.f && cell.f.location) note('location', cell.f.location, T.tKeep(cell.f.location));
      for (const food of (cell.ff || [])) {
        if (food && food.location) note('location', food.location, T.tKeep(food.location));
      }
    }
  }
}

/* GUIDE */
for (const [mapName, cells] of Object.entries(GUIDE)) {
  for (const [coord, cell] of Object.entries(cells)) {
    for (const f of ['skull_1', 'skull_2', 'boss_key']) {
      if (onlyField && onlyField !== f) continue;
      if (typeof cell[f] === 'string' && cell[f]) {
        note(f, cell[f], GUIDE_TRANSLATOR[f](cell[f]));
      }
    }
    if (!onlyField || onlyField === 'search.desc') {
      for (const item of (cell.search || [])) {
        if (item.desc) note('search.desc', item.desc, T.tSearch(item.desc));
      }
    }
  }
}

/* ── 6. Sortie ─────────────────────────────────────────────────────────────*/
const FIELD_LABEL = {
  m: 'Missions/règles (→tMis, dict MIS_PH/MIS_PRE)',
  ta: 'Temps rang A (→tMis)',
  la: 'Récompense A : armes/cœurs (→tLoot, dict LOOT_T)',
  lv: 'Récompense V : cartes/costumes (→tLoot, dict LOOT_T)',
  t: 'Trésors (→tLoot, dict LOOT_T)',
  location: 'Emplacements fées/foods (→tKeep, dict BASE_LOC)',
  skull_1: 'Skulltula 1 (→tSkull)',
  skull_2: 'Skulltula 2 (→tSkull)',
  boss_key: 'Clé de boss (→tKeep, dict BASE_LOC)',
  'search.desc': 'Descriptions recherche (→tSearch, dict SEARCH_PH)',
};

if (csvMode) {
  console.log('champ,occurrences,chaine_residuelle_apres_traduction,source_en');
  for (const [field, m] of Object.entries(report)) {
    for (const [txt, info] of [...m.entries()].sort((a, b) => b[1].count - a[1].count)) {
      const esc = s => '"' + String(s).replace(/"/g, '""') + '"';
      console.log([field, info.count, esc(txt), esc(info.original)].join(','));
    }
  }
} else {
  console.log('\n╔══════════════════════════════════════════════════════════════╗');
  console.log('║   AUDIT LOCALISATION HWDE — anglais résiduel après rendu      ║');
  console.log('╚══════════════════════════════════════════════════════════════╝');
  console.log('\nNote : noms propres (Link, Lana…) filtrés. Quelques faux positifs');
  console.log('possibles sur lieux non encore dans BASE_LOC.\n');

  const order = ['m', 't', 'lv', 'la', 'location', 'boss_key', 'skull_1', 'skull_2', 'search.desc', 'ta'];
  let grandTotal = 0;
  for (const field of order) {
    const m = report[field];
    if (!m || m.size === 0) continue;
    const total = [...m.values()].reduce((a, b) => a + b.count, 0);
    grandTotal += total;
    console.log('─'.repeat(66));
    console.log(`▶ ${FIELD_LABEL[field] || field}`);
    console.log(`  ${m.size} chaînes distinctes · ${total} occurrences\n`);
    const top = [...m.entries()].sort((a, b) => b[1].count - a[1].count).slice(0, 12);
    for (const [txt, info] of top) {
      console.log(`   [${String(info.count).padStart(3)}×] ${txt.slice(0, 70)}`);
    }
    if (m.size > 12) console.log(`   … +${m.size - 12} autres (voir --csv pour la liste complète)`);
    console.log('');
  }
  console.log('─'.repeat(66));
  console.log(`TOTAL anglais résiduel estimé : ${grandTotal} occurrences\n`);
  console.log('Pour exporter la liste complète :');
  console.log('  node audit_localisation.js index.html --csv > rapport_localisation.csv\n');
}
