import { readFileSync, readdirSync } from 'fs';
import { join } from 'path';
import iconv from 'iconv-lite';
import { CDROM_HTML_DIR } from './src/config.js';

function getLemmaFiles() {
  return readdirSync(CDROM_HTML_DIR)
    .filter(f => f.endsWith('.htm') && !f.endsWith('_e.htm') && !f.endsWith('_f.htm'))
    .sort();
}

function main() {
  const files = getLemmaFiles();
  console.log(`Total files to analyze: ${files.length}`);
  
  const failures = [];

  for (const file of files) {
    const raw = iconv.decode(readFileSync(join(CDROM_HTML_DIR, file)), 'windows-1252');
    
    // Exact match used in importDCR.js
    const currentRegex = /<!--\s*[<>]\s*<dicgrammar>(.*?)<\/dicgrammar>/i;
    const match = raw.match(currentRegex);
    
    // Also check if <dicgrammar> exists at all in the file
    const existsAtAll = raw.includes('dicgrammar');
    
    if (!match) {
      // Find what the actual surrounding lines or tag looks like
      const index = raw.indexOf('dicgrammar');
      let snippet = 'NOT_FOUND';
      if (index !== -1) {
        snippet = raw.substring(Math.max(0, index - 50), Math.min(raw.length, index + 100));
      } else {
        // Look for the first 500 chars to see if there is any other way grammatical category is listed
        snippet = raw.substring(0, 400).replace(/\r?\n/g, ' ');
      }
      
      failures.push({ file, existsAtAll, snippet });
    }
  }

  console.log(`\nFound ${failures.length} files that failed standard regex match.\n`);
  
  console.log('--- SAMPLES OF FAILURES ---');
  failures.slice(0, 15).forEach(f => {
    console.log(`File: ${f.file}`);
    console.log(`Exists: ${f.existsAtAll}`);
    console.log(`Snippet: ${f.snippet.trim()}`);
    console.log('---------------------------');
  });
}

main();
