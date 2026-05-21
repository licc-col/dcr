/**
 * importDCR.js (Refined)
 * Main importer: parses all 2760 lemma HTM files from CD-ROM/html/
 * into MongoDB. Uses confirmed hierarchy:
 *   Level 0: <dicarbrecont>letter)</dicarbrecont>  → main acepción
 *   Hierarchy markers: Supports both ¾ (0xBE) AND — (em-dash/dash)
 *   Greek counts: 1 char = sub-acepción, 2 chars = sub-sub-acepción
 */
import { readFileSync, readdirSync } from 'fs';
import { join, basename } from 'path';
import { load } from 'cheerio';
import iconv from 'iconv-lite';
import mongoose from 'mongoose';
import { CDROM_HTML_DIR, MONGODB_URI } from '../config.js';
import { replaceSymbolFontInHtml } from './symbolFont.js';

// ── Mongoose Schemas ──────────────────────────────────────────────────────────
const exampleSchema = new mongoose.Schema({
  text:      String,
  isPoetry:  { type: Boolean, default: false },
  author:    { abbrev: String, id: String },
  work:      String,
  reference: String,
}, { _id: false });

const subSubAcepcionSchema = new mongoose.Schema({
  letter:     String,  // "— αα)", etc.
  definition: String,
  examples:   [exampleSchema],
}, { _id: false });

const subAcepcionSchema = new mongoose.Schema({
  letter:           String,  // "— α)", etc.
  type:             String,  // "Refl.", "Part.", etc.
  definition:       String,
  examples:         [exampleSchema],
  subSubAcepciones: [subSubAcepcionSchema], // Nested!
}, { _id: false });

const acepcionSchema = new mongoose.Schema({
  id:            String,
  letter:        String,  // "a)", "b)", ...
  definition:    String,
  examples:      [exampleSchema],
  subAcepciones: [subAcepcionSchema],
}, { _id: false });

const lemmaSchema = new mongoose.Schema({
  lemma:               { type: String, required: true, index: true },
  slug:                { type: String, required: true, unique: true },
  grammaticalCategory: String,
  introduction:        String,
  acepciones:          [acepcionSchema],
  etymology:           String,
  transformedHtml:     String,
  authorsUsed:         [String],
  abbrevsUsed:         [String],
}, { collection: 'lemmas' });

lemmaSchema.index({ lemma: 'text', introduction: 'text' });
const Lemma = mongoose.model('Lemma', lemmaSchema);

// ── File helpers ──────────────────────────────────────────────────────────────
function getLemmaFiles() {
  return readdirSync(CDROM_HTML_DIR)
    .filter(f => f.endsWith('.htm') && !f.endsWith('_e.htm') && !f.endsWith('_f.htm'))
    .sort();
}

// ── HTML Cleaning ─────────────────────────────────────────────────────────────
function preCleanHtml(raw) {
  // Fix broken <dicarbrecont> tags (missing </a> before closure)
  // Pattern: <dicarbrecont><a name="arbreNNN">a)</dicarbrecont>
  let clean = raw.replace(
    /(<dicarbrecont><a name="[^"]*">)([^<]*)(<\/dicarbrecont>)/gi,
    '$1$2</a>$3'
  );
  
  // Also handle cases where <dicarbrecont> is wraped in <b> or other tags
  // The goal is to make it parseable by Cheerio.
  return clean;
}

// ── Build transformed HTML (Cleaned/Styled) ──────────────────────────────────
function buildTransformedHtml(raw) {
  let html = preCleanHtml(raw);

  // 1. Lemma headword (blue bold)
  html = html.replace(
    /<font[^>]*color="#0000ff"[^>]*><b>([^<]*)<\/b><\/font>/gi,
    '<span class="dcr-lemma">$1</span>'
  );
  // 2. Main acepcion markers (purple dicarbrecont)
  html = html.replace(/<dicarbrecont>([\s\S]*?)<\/dicarbrecont>/gi, (_, inner) => {
    const text = inner.replace(/<[^>]+>/g, '').trim();
    const isEtym = /^etim/i.test(text);
    return `<span class="dcr-acepcion${isEtym ? ' dcr-etym' : ''}">${text}</span>`;
  });
  // 3. Dark blue quotations
  html = html.replace(
    /<font[^>]*color="#000080"[^>]*>([\s\S]*?)<\/font>/gi,
    '<span class="dcr-quote">$1</span>'
  );
  // 4. Authors
  html = html.replace(/<dicautor>([\s\S]*?)<\/dicautor>/gi, (_, inner) => {
    const abbrev = inner.replace(/<[^>]+>/g, '').trim();
    return `<span class="dcr-author" data-abbrev="${abbrev.replace(/"/g, '&quot;')}">${abbrev}</span>`;
  });
  // 5. Abbreviations
  html = html.replace(/<dicabrev>([\s\S]*?)<\/dicabrev>/gi, (_, inner) => {
    const abbrev = inner.replace(/<[^>]+>/g, '').trim();
    return `<span class="dcr-abbrev" data-abbrev="${abbrev.replace(/"/g, '&quot;')}">${abbrev}</span>`;
  });
  // 6. Symbols
  html = replaceSymbolFontInHtml(html);
  
  // 7. Strip legacy
  html = html
    .replace(/<font[^>]*>/gi, '').replace(/<\/font>/gi, '')
    .replace(/<dir>/gi, '').replace(/<\/dir>/gi, '')
    .replace(/<u>/gi, '').replace(/<\/u>/gi, '')
    .replace(/<!--[\s\S]*?-->/g, '');

  return html.trim();
}

// ── Parse example ─────────────────────────────────────────────────────────────
function parseExample($p, $) {
  const quoteEl = $p.find('font[color="#000080"], [color="#000080"], .dcr-quote');
  const quoteText = quoteEl.map((_, el) => $(el).text()).get().join(' ').replace(/\s+/g, ' ').trim();
  const isPoetry = $p.html()?.includes('\u00BD') || $p.find('.dcr-verse-break').length > 0;

  const authorEl = $p.find('dicautor, .dcr-author').first();
  const authorAbbrev = authorEl.length ? authorEl.text().trim() : '';

  const $clone = $p.clone();
  $clone.find('font[color="#000080"], [color="#000080"], dicautor, .dcr-quote, .dcr-author, .dcr-verse-break').remove();
  const workRef = $clone.text().replace(/\s+/g, ' ').trim();

  return {
    text: quoteText,
    isPoetry,
    author: { abbrev: authorAbbrev, id: '' },
    work: workRef.split('(')[0].trim().replace(/^[,.\s—]+/, ''),
    reference: (workRef.match(/\(([^)]+)\)/) || [])[1] || '',
  };
}

// ── Parse single file ─────────────────────────────────────────────────────────
function parseLemmaFile(filePath) {
  const raw = iconv.decode(readFileSync(filePath), 'windows-1252');
  const slug = basename(filePath, '.htm').toLowerCase();

  // Extraction of Lemma/Grammar from comments
  const lemmaMatch = raw.match(/<!--\s*[<>]\s*<dicentry>(.*?)<\/dicentry>/i);
  const lemma = lemmaMatch ? lemmaMatch[1].trim().replace(/\.$/, '') : slug.toUpperCase();
  const grammarMatch = raw.match(/<!--\s*[<>]\s*<dicgrammar>(.*?)<\/dicgrammar>/i);
  const grammaticalCategory = grammarMatch ? grammarMatch[1].trim() : '';

  // Use Symbol-replaced HTML for structured detection
  const processedHtml = replaceSymbolFontInHtml(preCleanHtml(raw));
  const $ = load(processedHtml, { xmlMode: false, decodeEntities: false });

  // Authors/Abbrevs Used
  const authorsUsed = new Set();
  const abbrevsUsed = new Set();
  $('dicautor, .dcr-author').each((_, el) => { const t=$(el).text().trim(); if(t) authorsUsed.add(t); });
  $('dicabrev, .dcr-abbrev').each((_, el) => { const t=$(el).text().trim(); if(t) abbrevsUsed.add(t); });

  const acepciones = [];
  let introduction = '';
  let currentAcep = null;

  $('body p, dir p').each((_, p) => {
    const $p = $(p);
    const html = $p.html() || '';
    const text = $p.text().replace(/\s+/g, ' ').trim();
    if (!text) return;

    // Detect Main Acepción
    const acepcionEl = $p.find('dicarbrecont, .dcr-acepcion').first();
    if (acepcionEl.length) {
      if (currentAcep) acepciones.push(currentAcep);
      const letter = acepcionEl.text().trim();
      acepcionEl.remove();
      const def = $p.text().replace(/\s+/g, ' ').trim();
      currentAcep = { id: '', letter, definition: def, examples: [], subAcepciones: [] };
      return;
    }

    // Detect Sub-Acepción (¾, —, -)
    const subMatch = text.match(/^[\—\-\§\s]*([\u03B1-\u03C9\u0391-\u03A9\s]+)\s*\)/);
    if (subMatch) {
      if (!currentAcep) {
        currentAcep = { id: '', letter: '', definition: '', examples: [], subAcepciones: [] };
      }
      
      const rawGreek = subMatch[1];
      const greekClean = rawGreek.replace(/\s+/g, '');
      const level = greekClean.length;
      
      const hasIndent = $p.find('.dcr-indent-bullet').length > 0;
      const markerChar = hasIndent ? '§' : '—';
      const letter = `${markerChar} ${greekClean})`;

      const $pClone = $p.clone();
      $pClone.find('.dcr-indent-bullet, .dcr-greek').remove();
      const prefixLength = subMatch[0].length;
      const fullDefText = text.substring(prefixLength).trim();
      
      // Split Type Label (Refl., Part., etc.)
      const typeMatch = fullDefText.match(/^(Refl\.|Part\.|Impers\.|Intr\.|Tr\.|[A-Z][a-z]+\.)\s+/);
      const type = typeMatch ? typeMatch[1] : '';
      const def = typeMatch ? fullDefText.slice(typeMatch[0].length) : fullDefText;

      currentAcep.subAcepciones.push({
        letter, level, type, definition: def, examples: []
      });
      return;
    }

    // Detect Example (Quotations)
    if (html.includes('#000080') || html.includes('dcr-quote')) {
      const ex = parseExample($p, $);
      if (ex.text) {
        if (currentAcep?.subAcepciones?.length) {
          currentAcep.subAcepciones.at(-1).examples.push(ex);
        } else if (currentAcep) {
          currentAcep.examples.push(ex);
        }
      }
      return;
    }

    // Capture orphaned text into definition or introduction
    if (!currentAcep) {
      introduction += (introduction ? ' ' : '') + text;
    }
  });

  if (currentAcep) acepciones.push(currentAcep);

  return {
    lemma, slug, grammaticalCategory,
    introduction: introduction.slice(0, 2000),
    acepciones,
    etymology: (acepciones.find(a => /^etim/i.test(a.letter))?.definition || ''),
    transformedHtml: buildTransformedHtml(raw),
    authorsUsed: [...authorsUsed],
    abbrevsUsed: [...abbrevsUsed]
  };
}

// ── Main ──────────────────────────────────────────────────────────────────────
async function main() {
  await mongoose.connect(MONGODB_URI);
  console.log('Connected to MongoDB');
  await Lemma.deleteMany({});
  const files = getLemmaFiles();
  let imported = 0;
  for (let i = 0; i < files.length; i += 50) {
    const chunk = files.slice(i, i + 50);
    const docs = chunk.map(f => parseLemmaFile(join(CDROM_HTML_DIR, f)));
    await Lemma.insertMany(docs);
    imported += docs.length;
    process.stdout.write(`\rImported ${imported}/${files.length}`);
  }
  console.log('\n✅ Import complete');
  await mongoose.disconnect();
}
main().catch(console.error);
