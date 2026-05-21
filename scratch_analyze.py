import os
import re
import glob
from collections import Counter

def analyze_cdrom_structure():
    html_dir = r'd:\ICC-2026\pasantía\cuervo\CD-ROM\html'
    files = glob.glob(os.path.join(html_dir, '*.htm'))
    
    # 1. Analyze tags like dicabrev, dicautor, dicgrammar for anchors/links
    tag_anchors = {
        'dicgrammar': Counter(),
        'dicabrev': Counter(),
        'dicautor': Counter(),
    }
    
    all_anchor_prefixes = Counter()
    sample_anchors_with_context = []
    
    # 2. Analyze trailing paragraphs after the last section candidate
    files_with_trailing_paras = []
    
    kw_pattern = (
        r'Per\.\s*antecl\.|Per\.\s*antecel\.|Período\s*antecl\.|'
        r'Test\.\s*lat\.\s*hisp\.|Test\.\s*latin\.\s*hisp\.|Text\.\s*lat\.\s*hisp\.|Test\.\s*lat\.\s*hist\.|'
        r'Etim\b\.?|Nota\b\.?|Forma\b\.?|Ortografía\b\.?|Ortogr\b\.?|Conjug\b\.?|Conj\b\.?|'
        r'Construcciones\b|Constr\b\.?|Prosodia\b|Pros\b\.?|Colocación\b|Coloc\b\.?'
    )
    header_regex = r'<p[^>]*>(?:\s*<[^>]+>)*\s*(' + kw_pattern + r')\b'
    
    for count, filepath in enumerate(files):
        filename = os.path.basename(filepath)
        with open(filepath, 'r', encoding='windows-1252', errors='ignore') as f:
            content = f.read()
            
            # Find all <a name="..."> tags and analyze their context
            anchors = re.findall(r'<a\s+name=["\']?([^"\'>]+)["\']?[^>]*>(.*?)</a>', content, re.IGNORECASE)
            for name, text in anchors:
                prefix = re.match(r'^([a-zA-Z]+)', name)
                if prefix:
                    all_anchor_prefixes[prefix.group(1)] += 1
                
                # Check surrounding tag
                # We can search for the anchor in the context of dicabrev, dicautor, dicgrammar
                for tag in tag_anchors:
                    if re.search(f'<{tag}[^>]*>[^<]*<a\\s+name=["\']?{re.escape(name)}["\']?', content, re.IGNORECASE):
                        tag_anchors[tag]['has_anchor'] += 1
                        
            # Count tags in general
            for tag in tag_anchors:
                matches = re.findall(f'<{tag}[^>]*>(.*?)</{tag}>', content, re.IGNORECASE)
                tag_anchors[tag]['total_tags'] += len(matches)
                for m in matches:
                    if '<a ' in m:
                        tag_anchors[tag]['tags_with_a'] += 1
                        
            # Analyze trailing paragraphs at the end of the file after the last structural candidate
            dicarb_matches = list(re.finditer(r'<dicarbrecont>(.*?)</dicarbrecont>', content, flags=re.IGNORECASE))
            regex_matches = list(re.finditer(header_regex, content, flags=re.IGNORECASE))
            
            # Clean candidates
            candidates = []
            for m in dicarb_matches:
                # check if it's a real section
                clean = re.sub(r'<[^>]+>', '', m.group(1)).strip().lower()
                clean_norm = re.sub(r'\.$', '', clean).strip()
                if any(k in clean_norm for k in ['per. antecl', 'período antecl', 'test. lat', 'etim', 'nota', 'forma', 'ortografia', 'ortografía', 'conjugacion', 'conjugación', 'construccion', 'construcción', 'constr', 'prosodia', 'colocacion', 'colocación']):
                    candidates.append((m.start(), m.group(0)))
            for m in regex_matches:
                candidates.append((m.start(), m.group(1)))
                
            if candidates:
                candidates.sort(key=lambda x: x[0])
                last_candidate_pos = candidates[-1][0]
                
                # Extract text from last_candidate_pos to the end
                tail = content[last_candidate_pos:]
                # Split tail into paragraphs
                paragraphs = re.split(r'</p>|<p[^>]*>', tail, flags=re.IGNORECASE)
                # Clean paragraphs
                clean_paras = []
                for p in paragraphs:
                    p_clean = re.sub(r'<[^>]+>', '', p).strip()
                    p_clean = re.sub(r'\s+', ' ', p_clean)
                    if p_clean and not p_clean.startswith('Etim.') and not p_clean.startswith('Nota.') and not p_clean.startswith('Forma.') and not p_clean.startswith('Ortografía.') and not p_clean.startswith('Conjugación.') and not p_clean.startswith('Construcciones.'):
                        # Filter out basic spaces or end-of-file noise
                        if len(p_clean) > 5 and not p_clean.startswith('&nbsp;'):
                            clean_paras.append(p_clean)
                
                if len(clean_paras) > 1: # There is more than just the section's starting paragraph
                    files_with_trailing_paras.append((filename, clean_paras))

    print("=== ANCHORS & TAGS ANALYSIS ===")
    for tag, counts in tag_anchors.items():
        print(f"Tag: <{tag}>")
        print(f"  Total tags: {counts['total_tags']}")
        print(f"  Tags containing <a>: {counts['tags_with_a']}")
        print(f"  Other details: {dict(counts)}")
        
    print("\n=== ANCHOR PREFIXES ===")
    for prefix, count in all_anchor_prefixes.most_common(20):
        print(f"  {prefix}: {count} occurrences")
        
    print("\n=== FILES WITH TRAILING PARAGRAPHS AFTER THE LAST SECTION ===")
    print(f"Total files with multiple paragraphs in the last tail section: {len(files_with_trailing_paras)}")
    for fname, paras in files_with_trailing_paras[:10]:
        print(f"\nFile: {fname}")
        for idx, p in enumerate(paras):
            print(f"  Para {idx+1}: {p[:150]}...")

if __name__ == '__main__':
    analyze_cdrom_structure()

