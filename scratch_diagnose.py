import os
import json
import glob
import re

def analyze_json_files():
    json_dir = r"d:\ICC-2026\pasantía\cuervo\json"
    files = glob.glob(os.path.join(json_dir, "*.json"))
    
    # Exclude special files and index files
    valid_files = [f for f in files if not os.path.basename(f).startswith("_") and "abbreviations_db" not in f and "authors_db" not in f and "index_db" not in f]
    
    print(f"Analyzing {len(valid_files)} JSON entry files...")
    
    dot_definitions = []
    trailing_dot_ids = []
    
    for filepath in valid_files:
        filename = os.path.basename(filepath)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            continue
            
        def inspect_acepcion(acep, path_str):
            # Check ID
            acep_id = acep.get("id", "")
            if acep_id.endswith("."):
                trailing_dot_ids.append({
                    "file": filename,
                    "path": path_str,
                    "id": acep_id,
                    "def": acep.get("definicion", "")[:30]
                })
                
            # Check definition for leading dot or single dot
            definicion = acep.get("definicion", "")
            if definicion.strip() == ".":
                dot_definitions.append({
                    "file": filename,
                    "path": path_str,
                    "type": "exact_dot",
                    "text": definicion
                })
            elif definicion.strip().startswith("."):
                dot_definitions.append({
                    "file": filename,
                    "path": path_str,
                    "type": "leading_dot",
                    "text": definicion[:30]
                })
                
            # Recurse subacepciones
            for idx, sub in enumerate(acep.get("subacepciones", [])):
                inspect_acepcion(sub, f"{path_str} -> sub[{idx}]")
                
            # Recurse subsubacepciones
            for idx, ss in enumerate(acep.get("subsubacepciones", [])):
                inspect_acepcion(ss, f"{path_str} -> subsub[{idx}]")
                
        for idx, acep in enumerate(data.get("acepciones", [])):
            inspect_acepcion(acep, f"acep[{idx}]")
            
    print(f"\n--- RESULTS ---")
    print(f"Total exact dot/punctuation-only definitions found: {len([d for d in dot_definitions if d['type'] == 'exact_dot'])}")
    print(f"Total leading dot definitions found: {len([d for d in dot_definitions if d['type'] == 'leading_dot'])}")
    print(f"Total trailing dot IDs found: {len(trailing_dot_ids)}")
    
    print("\nSamples of leading dot definitions:")
    for d in dot_definitions[:10]:
        print(f"  File: {d['file']} ({d['path']}) -> Type: {d['type']}, Text: {d['text']}")
        
    print("\nSamples of trailing dot IDs:")
    for t in trailing_dot_ids[:10]:
        print(f"  File: {t['file']} ({t['path']}) -> ID: {t['id']}, Def: {t['def']}")

if __name__ == "__main__":
    analyze_json_files()
