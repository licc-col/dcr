/**
 * extractAbbreviations.js
 * Parses AbreviaturasCDROM.htm (the authoritative abbreviation table)
 * and saves all abbreviations to the MongoDB `abbreviations` collection.
 */
import { readFileSync } from 'fs';
import { join } from 'path';
import { load } from 'cheerio';
import iconv from 'iconv-lite';
import mongoose from 'mongoose';
import { CDROM_PRESENTA_DIR, MONGODB_URI } from '../config.js';

// ── Schema ──────────────────────────────────────────────────────────────────
const abbreviationSchema = new mongoose.Schema({
  abbrev:    { type: String, required: true, unique: true },
  expansion: { type: String, required: true },
}, { collection: 'abbreviations' });

const Abbreviation = mongoose.model('Abbreviation', abbreviationSchema);

// ── Parser ───────────────────────────────────────────────────────────────────
function parseAbbreviationsHtml(filePath) {
  const raw = readFileSync(filePath);
  const html = iconv.decode(raw, 'windows-1252');
  const $ = load(html);

  const results = {};

  // The abbreviations are packed in <td> cells in a large table.
  // Each cell contains a run of "abbrev. expansion" pairs separated by spaces.
  // Example cell text: "absol. absoluto acus. acusativo adj. adjetivo ..."
  // Strategy: extract all text from TDs with length > 50, split by known pattern.

  $('td').each((_, td) => {
    const text = $(td).text().replace(/\s+/g, ' ').trim();
    if (text.length < 20) return;

    // Match pattern: "word(s) with dot(s)" followed by expansion until next abbrev
    // Abbreviations always end with a period or contain a period
    // Regex: captures "abbrev." then "expansion" (up to next abbrev or end)
    const pattern = /([A-Za-záéíóúüñÑ\.\-]+\.)\s+([^A-Z][^\.]*?)(?=\s+[A-Za-záéíóúüñÑ\.\-]+\.|$)/g;
    let match;
    while ((match = pattern.exec(text)) !== null) {
      const abbrev = match[1].trim();
      const expansion = match[2].trim();
      if (abbrev && expansion && abbrev.length < 25 && expansion.length > 1) {
        results[abbrev] = expansion;
      }
    }
  });

  // Fallback: also try splitting the full text of all TDs as a token stream
  const allText = $('td').map((_, td) => $(td).text()).get().join(' ');
  const tokens = allText.replace(/\s+/g, ' ').trim().split(' ');

  // Walk tokens: if a token ends with '.' and looks like an abbrev, next token(s) = expansion
  for (let i = 0; i < tokens.length - 1; i++) {
    const tok = tokens[i];
    if (tok.length > 1 && tok.length < 20 && tok.endsWith('.') && /[a-záéíóúüñ]/i.test(tok)) {
      // Collect expansion until next token ending in '.'
      const expansionParts = [];
      let j = i + 1;
      while (j < tokens.length && !(tokens[j].endsWith('.') && tokens[j].length < 20)) {
        expansionParts.push(tokens[j]);
        j++;
        if (expansionParts.length > 6) break;
      }
      if (expansionParts.length > 0) {
        const key = tok;
        const val = expansionParts.join(' ');
        if (!results[key]) results[key] = val;
      }
    }
  }

  return results;
}

// ── Main ─────────────────────────────────────────────────────────────────────
async function main() {
  console.log('📚 Extracting abbreviations from AbreviaturasCDROM.htm...');
  const filePath = join(CDROM_PRESENTA_DIR, 'AbreviaturasCDROM.htm');
  const abbrevMap = parseAbbreviationsHtml(filePath);

  const count = Object.keys(abbrevMap).length;
  console.log(`   Found ${count} abbreviations`);

  await mongoose.connect(MONGODB_URI);
  console.log('   Connected to MongoDB');

  await Abbreviation.deleteMany({});
  const docs = Object.entries(abbrevMap).map(([abbrev, expansion]) => ({ abbrev, expansion }));
  await Abbreviation.insertMany(docs, { ordered: false });

  console.log(`✅ Inserted ${docs.length} abbreviations into MongoDB`);
  await mongoose.disconnect();
}

main().catch(err => { console.error(err); process.exit(1); });
