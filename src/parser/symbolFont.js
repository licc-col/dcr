/**
 * symbolFont.js
 * Maps Windows Symbol font characters (encoded as Latin ASCII)
 * to their correct Unicode equivalents.
 *
 * In the DCR HTML files, <font face="symbol">a</font> means α,
 * <font face="symbol">b</font> means β, etc.
 *
 * Special structural chars:
 *   ½  → VERSE_BREAK  (poetic line break within quotations)
 *   ¾  → INDENT_BULLET (hierarchical indent marker before sub-acepciones)
 */

export const SYMBOL_MAP = {
  'a': 'α', 'b': 'β', 'g': 'γ', 'd': 'δ', 'e': 'ε',
  'z': 'ζ', 'h': 'η', 'q': 'θ', 'i': 'ι', 'k': 'κ',
  'l': 'λ', 'm': 'μ', 'n': 'ν', 'x': 'ξ', 'o': 'ο',
  'p': 'π', 'r': 'ρ', 's': 'σ', 't': 'τ', 'u': 'υ',
  'f': 'φ', 'c': 'χ', 'y': 'ψ', 'w': 'ω',
  'A': 'Α', 'B': 'Β', 'G': 'Γ', 'D': 'Δ', 'E': 'Ε',
  'Z': 'Ζ', 'H': 'Η', 'Q': 'Θ', 'I': 'Ι', 'K': 'Κ',
  'L': 'Λ', 'M': 'Μ', 'N': 'Ν', 'X': 'Ξ', 'O': 'Ο',
  'P': 'Π', 'R': 'Ρ', 'S': 'Σ', 'T': 'Τ', 'U': 'Υ',
  'F': 'Φ', 'C': 'Χ', 'Y': 'Ψ', 'W': 'Ω',
  // Structural markers
  '\u00BD': '½_VERSE',    // ½ → verse line break
  '\u00BE': '¾_INDENT',  // ¾ → hierarchical indent bullet
};

/**
 * Decode a single character from Symbol font to Unicode Greek or structural marker.
 * @param {string} ch - single character from Symbol font
 * @returns {string}
 */
export function decodeSymbolChar(ch) {
  return SYMBOL_MAP[ch] ?? ch;
}

/**
 * Replaces all Symbol font occurrences in an HTML string with
 * Unicode equivalents wrapped in semantic span elements.
 * Called on raw HTML before Cheerio parsing.
 *
 * @param {string} html - raw HTML string
 * @returns {string} - HTML with Symbol chars replaced by spans
 */
export function replaceSymbolFontInHtml(html) {
  // Match: <font face="symbol" ...>X</font>  (case-insensitive, any attrs)
  return html.replace(
    /<font\s+face=["']?symbol["']?[^>]*>([^<]*)<\/font>/gi,
    (match, content) => {
      const trimmed = content.trim();
      if (trimmed === '\u00BD') {
        // Verse line break — render as a visual separator
        return '<span class="dcr-verse-break" aria-hidden="true"> // </span>';
      }
      if (trimmed === '\u00BE') {
        // Indent bullet for sub-acepción
        return '<span class="dcr-indent-bullet" aria-hidden="true"></span>';
      }
      // Greek letter(s) — map each character
      const mapped = [...trimmed].map(decodeSymbolChar).join('');
      return `<span class="dcr-greek">${mapped}</span>`;
    }
  );
}
