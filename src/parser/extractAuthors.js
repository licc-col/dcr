/**
 * extractAuthors.js
 * Scans all 2760 lemma HTML files to collect unique <dicautor> abbreviations.
 * Cross-references with nominaCDROM.htm and Bibliografia.htm for full names/works.
 * Saves to MongoDB `authors` collection.
 */
import { readFileSync, readdirSync } from 'fs';
import { join } from 'path';
import { load } from 'cheerio';
import iconv from 'iconv-lite';
import mongoose from 'mongoose';
import { CDROM_HTML_DIR, CDROM_PRESENTA_DIR, MONGODB_URI } from '../config.js';

// ── Schema ──────────────────────────────────────────────────────────────────
const authorSchema = new mongoose.Schema({
  abbrev:   { type: String, required: true, unique: true },
  fullInfo: { type: String, default: '' },
}, { collection: 'authors' });

const Author = mongoose.model('Author', authorSchema);

// ── Helpers ──────────────────────────────────────────────────────────────────
function decodeHtm(filePath) {
  const raw = readFileSync(filePath);
  return iconv.decode(raw, 'windows-1252');
}

function getLemmaFiles() {
  return readdirSync(CDROM_HTML_DIR)
    .filter(f => f.endsWith('.htm') && !f.endsWith('_e.htm') && !f.endsWith('_f.htm'));
}

// ── Scan lemma files for all unique dicautor values ───────────────────────────
function scanAuthorsFromLemmas() {
  const files = getLemmaFiles();
  const authorSet = new Set();

  console.log(`   Scanning ${files.length} lemma files for <dicautor> tags...`);
  let processed = 0;

  for (const file of files) {
    try {
      const html = decodeHtm(join(CDROM_HTML_DIR, file));
      const $ = load(html, { xmlMode: false, decodeEntities: false });
      $('dicautor').each((_, el) => {
        const text = $(el).text().trim();
        if (text) authorSet.add(text);
      });
    } catch (err) {
      console.error(`   Error in ${file}: ${err.message}`);
    }
    processed++;
    if (processed % 500 === 0) process.stdout.write(`\r   Scanned ${processed}/${files.length}...`);
  }
  console.log(`\n   Found ${authorSet.size} unique author abbreviations`);
  return authorSet;
}

// ── Parse nominaCDROM.htm for full author/work info ───────────────────────────
function parseNominaCDROM() {
  const filePath = join(CDROM_PRESENTA_DIR, 'nominaCDROM.htm');
  const html = decodeHtm(filePath);
  const $ = load(html);

  // nominaCDROM contains long entries. We extract paragraph text to build
  // a searchable info string keyed by what looks like author abbreviations.
  const info = {};
  $('p, li').each((_, el) => {
    const text = $(el).text().replace(/\s+/g, ' ').trim();
    if (text.length > 10) {
      // First word(s) up to first comma or period often = abbreviation
      const m = text.match(/^([A-Za-záéíóúüñÑ\.\-]{2,20})[,\.\s]/);
      if (m) {
        const key = m[1].trim();
        if (!info[key]) info[key] = text.slice(0, 300);
      }
    }
  });
  return info;
}

// ── Main ─────────────────────────────────────────────────────────────────────
async function main() {
  console.log('👤 Extracting authors...');

  const authorSet = scanAuthorsFromLemmas();
  const nominaInfo = parseNominaCDROM();

  await mongoose.connect(MONGODB_URI);
  console.log('   Connected to MongoDB');

  await Author.deleteMany({});

  const docs = [...authorSet].map(abbrev => {
    // Try to find info in nomina by partial key match
    const key = abbrev.replace(/\.$/, '');
    const fullInfo = nominaInfo[key] || nominaInfo[abbrev] || '';
    return { abbrev, fullInfo };
  });

  await Author.insertMany(docs, { ordered: false });
  console.log(`✅ Inserted ${docs.length} authors into MongoDB`);

  await mongoose.disconnect();
}

main().catch(err => { console.error(err); process.exit(1); });
