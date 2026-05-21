import os
import re
import json
from bs4 import BeautifulSoup

def compile_abbreviations():
    path = r"CD-ROM\ayuda\presenta\AbreviaturasCDROM.htm"
    if not os.path.exists(path):
        print(f"Error: {path} not found.")
        return {}
        
    with open(path, "r", encoding="windows-1252", errors="ignore") as f:
        html = f.read()
    
    soup = BeautifulSoup(html, "html.parser")
    abbrev_map = {}
    
    # Strategía: Buscar todos los elementos <p>
    for p in soup.find_all("p"):
        text = p.get_text().replace('\xa0', ' ')
        text = re.sub(r'\s+', ' ', text).strip()
        if not text:
            continue
            
        # Match "abreviatura expansión" (ej. "absol. absoluto")
        m = re.match(r"^([A-Za-záéíóúüñÑ\.\-]+)\s+(.+)$", text)
        if m:
            abbrev = m.group(1).strip()
            expansion = m.group(2).strip()
            
            # Normalizar para que termine en punto si es necesario
            if not abbrev.endswith('.'):
                abbrev += '.'
                
            if len(abbrev) < 15 and len(expansion) > 1:
                abbrev_map[abbrev] = expansion
                abbrev_map[abbrev.lower()] = expansion
                
    print(f"Compiled {len(abbrev_map)} abbreviations")
    return abbrev_map

def compile_authors():
    path = r"CD-ROM\ayuda\presenta\nominaCDROM.htm"
    if not os.path.exists(path):
        print(f"Error: {path} not found.")
        return {}
        
    with open(path, "r", encoding="windows-1252", errors="ignore") as f:
        html = f.read()
        
    soup = BeautifulSoup(html, "html.parser")
    authors_map = {}
    
    # nominaCDROM contiene párrafos con líneas como "A. Arguedas = Alcides Arguedas (1879-1946)"
    # y líneas posteriores para obras como "Obr. compl. = Obras completas..." o "Pisagua (1903)"
    current_author = None
    
    for p in soup.find_all(["p", "h2"]):
        text = p.get_text().replace('\xa0', ' ')
        text = re.sub(r'\s+', ' ', text).strip()
        if not text:
            continue
            
        # Match nuevo autor: ej. "A. Arguedas = Alcides Arguedas (1879-1946)"
        if " = " in text:
            parts = text.split(" = ", 1)
            key = parts[0].strip()
            val = parts[1].strip()
            
            # Si el key es corto, es la abreviatura de un autor
            if len(key) < 30 and not any(kw in key.lower() for kw in ["obr.", "cart.", "nov.", "poes.", "trad.", "s.f."]):
                current_author = key
                authors_map[current_author] = {
                    "name": val,
                    "works": []
                }
            elif current_author and current_author in authors_map:
                # Es una obra o aclaración del autor actual
                authors_map[current_author]["works"].append(text)
        else:
            # Puede ser una obra secundaria listada en el párrafo siguiente
            if current_author and current_author in authors_map and len(text) > 5:
                authors_map[current_author]["works"].append(text)
                
    # Formatear el resultado como texto enriquecido para los popovers
    formatted_authors = {}
    for abbrev, info in authors_map.items():
        full_info = f"👤 <strong>{info['name']}</strong>"
        if info["works"]:
            full_info += "<br><span class='popover-works-label'>Obras y Referencias:</span><ul class='popover-works-list'>"
            for w in info["works"][:6]: # Limitar a un máximo de 6 obras
                full_info += f"<li>{w}</li>"
            full_info += "</ul>"
            
        formatted_authors[abbrev] = full_info
        
        # Mapeo dual: con y sin punto
        clean_abbrev = abbrev.replace(".", "")
        if clean_abbrev != abbrev:
            formatted_authors[clean_abbrev] = full_info
            
    print(f"Compiled {len(formatted_authors)} authors")
    return formatted_authors

def main():
    json_dir = r"json"
    os.makedirs(json_dir, exist_ok=True)
    
    abbrevs = compile_abbreviations()
    authors = compile_authors()
    
    # Guardar ambos JSONs
    with open(os.path.join(json_dir, "abbreviations_db.json"), "w", encoding="utf-8") as f:
        json.dump(abbrevs, f, ensure_ascii=False, indent=2)
        
    with open(os.path.join(json_dir, "authors_db.json"), "w", encoding="utf-8") as f:
        json.dump(authors, f, ensure_ascii=False, indent=2)
        
    print("Glossaries compiled successfully!")

if __name__ == '__main__':
    main()
