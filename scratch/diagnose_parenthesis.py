import os
import json

def main():
    index_path = r"d:\ICC-2026\pasantía\cuervo\json\index_db.json"
    with open(index_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    parenthesis_lemmas = [x['lema'] for x in data if '(' in x['lema']]
    
    print(f"Found {len(parenthesis_lemmas)} lemmas with parenthesis:")
    for lema in sorted(parenthesis_lemmas)[:20]:
        print(f"  {repr(lema)}")

if __name__ == "__main__":
    main()
