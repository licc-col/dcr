import os
import json
import glob
import re

def is_grammatical_only(text):
    if not text:
        return True
    # Strip spaces and punctuation
    text_clean = re.sub(r'[\s.,()]+', ' ', text).strip().lower()
    if not text_clean:
        return True
    
    # Grammatical abbreviation words
    gram_words = {
        's', 'f', 'm', 'adj', 'v', 'adv', 'prep', 'pron', 'art', 'conj', 'interj',
        'pl', 'sing', 'tr', 'intr', 'ref', 'p', 'part', 'a', 'd', 'c', 'masc', 'fem',
        'n', 'u', 't', 'g', 'o', 'r', 'e', 'x'
    }
    
    words = text_clean.split()
    return all(w in gram_words for w in words)

def main():
    json_dir = r"d:\ICC-2026\pasantía\cuervo\json"
    files = glob.glob(os.path.join(json_dir, "*.json"))
    valid_files = [f for f in files if not os.path.basename(f).startswith("_") and "index_db" not in f and "authors_db" not in f]

    cleared_intros = []
    kept_intros = []
    
    for filepath in valid_files:
        filename = os.path.basename(filepath)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
            
        intro = data.get("introduccion", "")
        if intro:
            # We also check if it's grammatical only
            if is_grammatical_only(intro):
                cleared_intros.append((filename, intro))
            else:
                # If it's short but not grammatical only, let's keep it but track it for visibility
                if len(intro.strip()) <= 30:
                    kept_intros.append((filename, intro))

    # Write output to a UTF-8 log file to prevent console encoding crashes
    out_log_path = r"d:\ICC-2026\pasantía\cuervo\scratch\diagnose_intros_results.txt"
    with open(out_log_path, "w", encoding="utf-8") as out_f:
        out_f.write(f"Total files checked: {len(valid_files)}\n")
        out_f.write(f"Total introductions that WOULD BE CLEARED (grammatical only): {len(cleared_intros)}\n\n")
        
        out_f.write("--- INTRODUCTIONS TO BE CLEARED ---\n")
        for fn, intro in sorted(cleared_intros):
            out_f.write(f"  {fn}: {repr(intro)}\n")
            
        out_f.write("\n--- SHORT INTRODUCTIONS KEPT (<= 30 chars, not grammatical only) ---\n")
        for fn, intro in sorted(kept_intros):
            out_f.write(f"  {fn}: {repr(intro)}\n")

    print(f"Diagnostics complete! Results written to: {out_log_path}")
    print(f"Introductions to be cleared: {len(cleared_intros)}")
    print(f"Short introductions kept: {len(kept_intros)}")

if __name__ == "__main__":
    main()
