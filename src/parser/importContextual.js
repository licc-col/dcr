/**
 * importContextual.js
 * Processes all HTML files from CD-ROM/ayuda/presenta/ and copies them to
 * public/contextual/ with:
 *   - Symbol font → Unicode conversion
 *   - Inline style/font tags → CSS class injection
 *   - A shared wrapper that matches the app's design system
 */
import { readFileSync, writeFileSync, mkdirSync, readdirSync, copyFileSync } from 'fs';
import { join, extname, basename } from 'path';
import iconv from 'iconv-lite';
import { load } from 'cheerio';
import { CDROM_PRESENTA_DIR, PUBLIC_CONTEXTUAL_DIR } from '../config.js';
import { replaceSymbolFontInHtml } from './symbolFont.js';

const CONTEXTUAL_FILES = [
  { file: 'Presentacion.htm',      slug: 'presentacion' },
  { file: 'Introducción.htm',      slug: 'introduccion' },
  { file: 'CaracteristicasDCR.htm',slug: 'caracteristicas' },
  { file: 'Historia del DCR.htm',  slug: 'historia' },
  { file: 'BiografiaCuervo.htm',   slug: 'biografia' },
  { file: 'AbreviaturasCDROM.htm', slug: 'abreviaturas' },
  { file: 'Bibliografia.htm',      slug: 'bibliografia' },
  { file: 'Signos.htm',            slug: 'signos' },
  { file: 'nominaCDROM.htm',       slug: 'nomina' },
  { file: 'creditos.htm',          slug: 'creditos' },
];

function processContextualFile(srcPath) {
  const raw = readFileSync(srcPath);
  let html = iconv.decode(raw, 'windows-1252');

  // Apply Symbol font mapping
  html = replaceSymbolFontInHtml(html);

  const $ = load(html, { decodeEntities: false });

  // Remove head styles and replace with class references
  $('head style, head link').remove();
  $('head').prepend('<link rel="stylesheet" href="/css/style.css">');

  // Replace body inline styles with class
  $('body').removeAttr('style').removeAttr('background').removeAttr('bgproperties')
           .removeAttr('leftmargin').attr('class', 'dcr-contextual-page');

  // Replace colour-encoded font tags with semantic spans
  $('font').each((_, el) => {
    const $el = $(el);
    const color = ($el.attr('color') || '').toLowerCase();
    const face = ($el.attr('face') || '').toLowerCase();
    let cls = 'dcr-text';
    if (color === '#0000ff' || color === 'blue') cls = 'dcr-lemma';
    else if (color === '#800080' || color === 'purple') cls = 'dcr-acepcion';
    else if (color === '#000080' || color === 'navy') cls = 'dcr-quote';
    else if (color.startsWith('#ff0') || color === 'red') cls = 'dcr-author';
    $el.replaceWith(`<span class="${cls}">${$el.html()}</span>`);
  });

  // Replace <dicautor> and <dicabrev> with clickable spans
  $('dicautor').each((_, el) => {
    const $el = $(el);
    const abbrev = $el.text().trim();
    $el.replaceWith(`<span class="dcr-author" data-abbrev="${abbrev}">${abbrev}</span>`);
  });
  $('dicabrev').each((_, el) => {
    const $el = $(el);
    const abbrev = $el.text().trim();
    $el.replaceWith(`<span class="dcr-abbrev" data-abbrev="${abbrev}">${abbrev}</span>`);
  });

  return $.html();
}

async function main() {
  console.log('📄 Processing contextual pages...');
  mkdirSync(PUBLIC_CONTEXTUAL_DIR, { recursive: true });

  // Also copy images from presenta/Imagenes if present
  try {
    const imgDir = join(CDROM_PRESENTA_DIR, 'Imagenes');
    const destImgDir = join(PUBLIC_CONTEXTUAL_DIR, 'Imagenes');
    mkdirSync(destImgDir, { recursive: true });
    for (const f of readdirSync(imgDir)) {
      copyFileSync(join(imgDir, f), join(destImgDir, f));
    }
    console.log('   Images copied');
  } catch { /* no images dir */ }

  for (const { file, slug } of CONTEXTUAL_FILES) {
    const srcPath = join(CDROM_PRESENTA_DIR, file);
    try {
      const processed = processContextualFile(srcPath);
      const destPath = join(PUBLIC_CONTEXTUAL_DIR, `${slug}.html`);
      writeFileSync(destPath, processed, 'utf-8');
      console.log(`   ✓ ${file} → contextual/${slug}.html`);
    } catch (err) {
      console.warn(`   ✗ ${file}: ${err.message}`);
    }
  }

  console.log('✅ Contextual pages ready');
}

main().catch(err => { console.error(err); process.exit(1); });
