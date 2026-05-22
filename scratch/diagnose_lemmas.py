import os
import json
import glob

def main():
    json_dir = r"d:\ICC-2026\pasantía\cuervo\json"
    files = glob.glob(os.path.join(json_dir, "*.json"))
    valid_files = [f for f in files if not os.path.basename(f).startswith("_") and "index_db" not in f and "authors_db" not in f]

    no_dot_lemmas = []
    star_lemmas = []
    
    for filepath in valid_files:
        filename = os.path.basename(filepath)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
            
        lema = data.get("lema", "").strip()
        if not lema:
            continue
            
        if lema.endswith(".*"):
            star_lemmas.append((filename, lema))
        elif not lema.endswith("."):
            no_dot_lemmas.append((filename, lema))

    print(f"Total entries analyzed: {len(valid_files)}")
    print(f"Found {len(star_lemmas)} lemmas ending with '.*'")
    print(f"Found {len(no_dot_lemmas)} lemmas NOT ending with '.' or '.*'")
    
    print("\nSamples of lemmas ending with '.*':")
    for fn, lema in sorted(star_lemmas)[:15]:
        print(f"  {fn}: {repr(lema)}")
        
    print("\nLemmas NOT ending with '.' or '.*':")
    for fn, lema in sorted(no_dot_lemmas):
        print(f"  {fn}: {repr(lema)}")

if __name__ == "__main__":
    main()
