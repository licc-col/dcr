import os
import json
import glob
import re

def normalize_lemma(lema):
    lema = lema.strip()
    if not lema:
        return lema
        
    # Check if it already ends with a dot
    if lema.endswith('.'):
        return lema
        
    # Check if it ends with dot and asterisk (with optional space)
    # e.g., "LEMA. *", "LEMA.*", "LEMA.  *"
    if re.search(r'\.\s*\*\s*$', lema):
        return lema
        
    # Check if it ends with parenthesis and has a dot before the parenthesis
    # e.g., "ALISTAR. (I)", "ALTO. (II)"
    if lema.endswith(')'):
        # Find if there is a dot before the opening parenthesis (possibly with spaces)
        # We look for a pattern like "word. (roman)" or "word. (synonym)"
        if re.search(r'\.\s*\([^)]+\)$', lema):
            return lema
            
    # Otherwise, append a trailing dot!
    return lema + '.'

def main():
    json_dir = r"d:\ICC-2026\pasantía\cuervo\json"
    files = glob.glob(os.path.join(json_dir, "*.json"))
    valid_files = [f for f in files if not os.path.basename(f).startswith("_") and "index_db" not in f and "authors_db" not in f]

    changes = []
    for filepath in valid_files:
        filename = os.path.basename(filepath)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
            
        original = data.get("lema", "")
        normalized = normalize_lemma(original)
        if original != normalized:
            changes.append((filename, original, normalized))

    print(f"Total changes that would be made: {len(changes)}")
    print("\nSamples of changes:")
    for fn, orig, norm in sorted(changes)[:50]:
        print(f"  {fn}: {repr(orig)} -> {repr(norm)}")

if __name__ == "__main__":
    main()
