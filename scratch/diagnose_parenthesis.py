import os
import json
import re

json_dir = r"d:\ICC-2026\pasantía\cuervo\json"
files = [f for f in os.listdir(json_dir) if f.endswith(".json") and f != "index_db.json" and f != "_index.json"]

print(f"Total files to scan: {len(files)}")

matches_count = 0
results = []

# Punctuation reference pattern
# Typically, if it was part of a parenthetical like (Cp. «A»; «B»), the remainder after B is ");" or ")." or ";" etc.
punctuation_ref_pat = re.compile(r'^[\s.,;()[\]\-‑—]*$')

def check_citas(citas_list, file_path, context_info):
    global matches_count
    for idx, cita in enumerate(citas_list):
        ref = cita.get("referencia_obra", "").strip()
        autor = cita.get("autor", "").strip()
        texto = cita.get("texto_cita", "").strip()
        
        # If autor is empty and reference is only punctuation/short symbols, it's highly likely a split parenthetical
        if not autor and punctuation_ref_pat.match(ref) and ref:
            results.append({
                "file": os.path.basename(file_path),
                "context": context_info,
                "texto_cita": texto,
                "referencia_obra": ref
            })
            matches_count += 1

for f_name in files:
    f_path = os.path.join(json_dir, f_name)
    try:
        with open(f_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        continue
    
    # Check main acepciones
    for acep_idx, acep in enumerate(data.get("acepciones", [])):
        context_acep = f"Acepción ID: {acep.get('id', 'N/A')}"
        check_citas(acep.get("ejemplos_citas", []), f_path, context_acep)
        
        # Check subacepciones
        for sub_idx, sub in enumerate(acep.get("subacepciones", [])):
            context_sub = f"Acepción ID: {acep.get('id', 'N/A')} -> Subacepción ID: {sub.get('id_limpio', 'N/A')}"
            check_citas(sub.get("ejemplos_citas", []), f_path, context_sub)
            
            # Check subsubacepciones
            for subsub in sub.get("subsubacepciones", []):
                context_subsub = f"Acepción ID: {acep.get('id', 'N/A')} -> Subacepción ID: {sub.get('id_limpio', 'N/A')} -> Subsubacepción ID: {subsub.get('id_limpio', 'N/A')}"
                check_citas(subsub.get("ejemplos_citas", []), f_path, context_subsub)

print(f"\nScan completed. Found {matches_count} cases of potential incorrect split parentheticals.")

# Save results to a file for review
out_path = r"d:\ICC-2026\pasantía\cuervo\scratch\diagnose_parenthesis_results.txt"
with open(out_path, 'w', encoding='utf-8') as out_f:
    out_f.write(f"Diagnóstico de comillas partidas incorrectamente\n")
    out_f.write(f"Total casos detectados: {matches_count}\n\n")
    for r in results:
        out_f.write(f"Archivo: {r['file']}\n")
        out_f.write(f"Contexto: {r['context']}\n")
        out_f.write(f"Cita: {r['texto_cita']}\n")
        out_f.write(f"Referencia: {r['referencia_obra']}\n")
        out_f.write("-" * 50 + "\n")

print(f"Results saved to {out_path}")
