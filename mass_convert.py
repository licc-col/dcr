"""
Script de Conversión Masiva: Diccionario Cuervo (HTML a JSON)
-----------------------------------------------------------
Este script procesa archivos HTML de un diccionario lexicográfico antiguo 
y los convierte a una estructura JSON organizada, preservando el formato 
original y manejando casos complejos de sub-acepciones marcadas con símbolos griegos.
"""

import os
import json
import re
import glob

# Mapeo de caracteres de la fuente 'Symbol' de Windows a Unicode.
# Utilizado para traducir marcadores de sub-acepciones (alpha, beta, etc.)
symbol_map = {
    'a': 'α', 'b': 'β', 'g': 'γ', 'd': 'δ', 'e': 'ε', 'z': 'ζ',
    'h': 'η', 'q': 'θ', 'i': 'ι', 'k': 'κ', 'l': 'λ', 'm': 'μ',
    'n': 'ν', 'x': 'ξ', 'o': 'ο', 'p': 'π', 'r': 'ρ', 's': 'σ',
    't': 'τ', 'u': 'υ', 'f': 'φ', 'c': 'χ', 'y': 'ψ', 'w': 'ω',
    '¾': '—', # Em-dash
    '½': '|'  # Pipe de separación de versos
}

def translate_symbols(text):
    """
    Traduce caracteres en bloques <font face='symbol'> a Unicode.
    Protege las etiquetas HTML internas para evitar corromper atributos (ej. <a href>).
    """
    def replace_symbol(match):
        full_tag_content = match.group(1)
        # Dividimos por etiquetas HTML para traducir solo los nodos de texto
        parts = re.split(r'(<[^>]+>)', full_tag_content)
        translated_parts = []
        for p in parts:
            if p.startswith('<'):
                translated_parts.append(p) # Es una etiqueta, no traducir
            else:
                translated_parts.append("".join(symbol_map.get(c, c) for c in p))
        return f'<font face="symbol">{"".join(translated_parts)}</font>'
    
    return re.sub(r'<font[^>]*face=["\']?symbol["\']?[^>]*>(.*?)</font>', replace_symbol, text, flags=re.IGNORECASE)

def balance_tags(text):
    """
    Asegura que etiquetas de formato (i, b, font, u) abiertas se cierren dentro del mismo bloque.
    Evita que el formato de una acepción se "derrame" sobre el resto del visor web.
    """
    tags = ['i', 'b', 'font', 'u']
    for tag in tags:
        open_count = len(re.findall(f'<{tag}[^>]*>', text, re.IGNORECASE))
        close_count = len(re.findall(f'</{tag}>', text, re.IGNORECASE))
        if open_count > close_count:
            text += f'</{tag}>' * (open_count - close_count)
        elif close_count > open_count:
            # Si hay etiquetas de cierre huérfanas al principio, no se pueden arreglar fácilmente
            # sin conocer el contexto anterior. Aquí simplemente nos aseguramos de no dejar etiquetas abiertas.
            pass
    return text

def clean_structural_tags(text):
    """
    Limpia etiquetas de bloque (<p>, <br>) al inicio y final de los textos.
    Mejora la alineación visual en el visor (flexbox/grid).
    """
    text = re.sub(r'^(<p[^>]*>|<br/?>|\s)+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'(</p>|<br/?>|\s)+$', '', text, flags=re.IGNORECASE)
    return text

def split_subacepciones(block):
        # (B) Leading Dash: ( [tags]* — [tags/spaces]* )?
    # Permissive marker regex that handles markers split across multiple tags or lines.
    # It ensures the em-dash prefix stays with the marker even if it's in a previous tag or block.
    # Structure: (Optional <p>) (Optional Dash) (One or more Greek font/text blocks) (Closing parenthesis)
    marker_regex = (
        r'('
        r'(?:<p[^>]*>\s*)?'                                     # Optional <p> start
        r'(?:(?:<[^>]+>\s*)*[—‑-](?:\s*<[^>]+>)*\s*)?'           # Optional dash prefix (—)
        r'(?:(?:<[^>]+>\s*)*[α-ωΑ-Ω—]+(?:\s*<[^>]+>)*\s*)+'      # Greek letters/symbols series
        r'\)'                                                   # Closing )
        r'(?:\s*</font>|\s*</p>)?'                              # Optional immediate closing tag
        r')'
    )
    
    # Higher level splitting using the regex above. 
    # re.split keeps the capturing group in the list of results.
    parts = re.split(marker_regex, block, flags=re.IGNORECASE)
    return parts

def parse_html_to_json(filepath):
    try:
        with open(filepath, 'r', encoding='windows-1252', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        return None

    content = re.sub(r'[\r\n]+', ' ', content)
    content = translate_symbols(content)
    
    data = {"lema": "", "categoria_gramatical": "", "introduccion": "", "acepciones": [], "etimologia": ""}
    
    m_lema = re.search(r'<dicentry>(.*?)</dicentry>', content, flags=re.IGNORECASE)
    if m_lema: data['lema'] = m_lema.group(1).strip()
    
    m_gram = re.search(r'<dicgrammar>(.*?)</dicgrammar>', content, flags=re.IGNORECASE)
    pos_gram_end = m_gram.end() if m_gram else 0
    if m_gram: data['categoria_gramatical'] = m_gram.group(1).strip()
        
    def is_real_acep(text):
        clean = re.sub(r'<[^>]+>', '', text).strip()
        special_words = ['per. antecl.', 'etim.', 'test. lat. hisp.', 'nota', 'forma', 'ortografía', 'conjugación', 'construcciones', 'constr.', 'prosodia', 'colocación']
        clean_lower = clean.lower()
        for w in special_words:
            if w in clean_lower:
                return False
        return True

    dicarb_matches = list(re.finditer(r'<dicarbrecont>(.*?)</dicarbrecont>', content, flags=re.IGNORECASE))
    
    real_acep_matches = [m for m in dicarb_matches if is_real_acep(m.group(1))]
    special_matches = [m for m in dicarb_matches if not is_real_acep(m.group(1))]
    
    etim_match = re.search(r'(<p[^>]*>|<font[^>]*>|<b[^>]*>)\s*Etim\.', content, flags=re.IGNORECASE)
    pos_etim_start = etim_match.start() if etim_match else len(content)
    
    # Extract the "Constr." section if it exists. Note: sometimes it's inside dicarbrecont.
    constr_match = re.search(r'(?:<[^>]*>)?\s*Constr\.', content, flags=re.IGNORECASE)
    pos_constr_start = constr_match.start() if constr_match else len(content)
    
    # Check for other special section headers
    special_headers_regex = r'(?:<p[^>]*>|<font[^>]*>|<b[^>]*>)\s*(?:Per\.\s*antecl\.|Test\.\s*lat\.\s*hisp\.|Etim\.|Nota\b|Forma\b|Ortografía\b|Conjugación\b|Construcciones\b|Constr\.)'
    header_matches = list(re.finditer(special_headers_regex, content, flags=re.IGNORECASE))
    
    # Find where normal lexicographical acepciones end
    special_positions = [pos_etim_start, pos_constr_start]
    for m in special_matches:
        special_positions.append(m.start())
    for m in header_matches:
        special_positions.append(m.start())
        
    pos_normal_end = min(special_positions)

    def process_citas(text):
        citas_list = []
        citas_split = re.split(r'«', text)
        def_text = clean_structural_tags(balance_tags(citas_split[0].strip()))
        for c in citas_split[1:]:
            qp = re.split(r'»', c, maxsplit=1)
            texto_cita = balance_tags("«" + qp[0].strip() + ("»" if len(qp) > 1 else ""))
            autor_raw = ""
            ref_raw = ""
            if len(qp) > 1:
                remainder = qp[1].strip()
                m_autor = re.search(r'<dicautor>(.*?)</dicautor>', remainder, flags=re.IGNORECASE)
                if m_autor:
                    autor_raw = clean_structural_tags(balance_tags(m_autor.group(1).strip()))
                    ref_raw = clean_structural_tags(balance_tags(remainder[m_autor.end():].strip()))
                else:
                    ref_raw = clean_structural_tags(balance_tags(remainder))
            citas_list.append({
                "texto_cita": texto_cita,
                "autor": autor_raw,
                "author": autor_raw,  # Dual compatibility for JS frontend
                "referencia_obra": ref_raw
            })
        return def_text, citas_list

    if not real_acep_matches:
        # Lemma has no main alphabetical acep (e.g. abominar, abusar)
        block = content[pos_gram_end:pos_normal_end].strip()
        acep_def = ""
        
        acepcion = {
            "id": "",
            "definicion": "",
            "ejemplos_citas": [],
            "subacepciones": []
        }
        
        subparts = split_subacepciones(block)
        intro_def, intro_citas = process_citas(subparts[0])
        data['introduccion'] = intro_def
        acepcion['ejemplos_citas'] = intro_citas
        
        current_sub_acep = None
        for j in range(1, len(subparts), 2):
            marker = subparts[j].strip()
            clean_marker = re.sub(r'<[^>]+>', '', marker).strip()
            clean_marker = re.sub(r'\s+', ' ', clean_marker)
            
            greek_letters = "".join([c for c in clean_marker if '\u0370' <= c <= '\u03ff'])
            if not greek_letters:
                stripped = re.sub(r'[\s—\-‑\)]', '', clean_marker)
                level = len(stripped) if stripped else 1
            else:
                level = len(greek_letters)
                
            content_sub = subparts[j+1] if j+1 < len(subparts) else ""
            sub_def, sub_citas = process_citas(content_sub)
            
            if level == 1:
                sub_acep = {
                    "id_marcador_html": clean_structural_tags(marker),
                    "id_limpio": clean_marker.strip(),
                    "definicion": sub_def,
                    "ejemplos_citas": sub_citas,
                    "subsubacepciones": []
                }
                acepcion["subacepciones"].append(sub_acep)
                current_sub_acep = sub_acep
            else:
                # Level 2 (sub-subacepción)
                subsub_acep = {
                    "id_marcador_html": clean_structural_tags(marker),
                    "id_limpio": clean_marker.strip(),
                    "definicion": sub_def,
                    "ejemplos_citas": sub_citas
                }
                if current_sub_acep is not None:
                    current_sub_acep["subsubacepciones"].append(subsub_acep)
                else:
                    implicit_sub = {
                        "id_marcador_html": "",
                        "id_limpio": "",
                        "definicion": "",
                        "ejemplos_citas": [],
                        "subsubacepciones": [subsub_acep]
                    }
                    acepcion["subacepciones"].append(implicit_sub)
                    current_sub_acep = implicit_sub
        data["acepciones"].append(acepcion)
    else:
        # Standard alphabetical acepciones exist
        data['introduccion'] = clean_structural_tags(balance_tags(content[pos_gram_end:real_acep_matches[0].start()].strip()))
        
        for i in range(len(real_acep_matches)):
            start_idx = real_acep_matches[i].end()
            if i + 1 < len(real_acep_matches):
                end_idx = real_acep_matches[i+1].start()
            else:
                end_idx = pos_normal_end
            
            block = content[start_idx:end_idx].strip()
            acep_html_id = real_acep_matches[i].group(1).strip()
            acepcion_id = re.sub(r'<[^>]+>', '', acep_html_id).strip()
            
            acepcion = {
                "id": acepcion_id,
                "definicion": "",
                "ejemplos_citas": [],
                "subacepciones": []
            }
            
            subparts = split_subacepciones(block)
            acep_def, acep_citas = process_citas(subparts[0])
            acepcion['definicion'] = acep_def
            acepcion['ejemplos_citas'] = acep_citas
            
            current_sub_acep = None
            for j in range(1, len(subparts), 2):
                marker = subparts[j].strip()
                clean_marker = re.sub(r'<[^>]+>', '', marker).strip()
                clean_marker = re.sub(r'\s+', ' ', clean_marker)
                
                greek_letters = "".join([c for c in clean_marker if '\u0370' <= c <= '\u03ff'])
                if not greek_letters:
                    stripped = re.sub(r'[\s—\-‑\)]', '', clean_marker)
                    level = len(stripped) if stripped else 1
                else:
                    level = len(greek_letters)
                    
                content_sub = subparts[j+1] if j+1 < len(subparts) else ""
                sub_def, sub_citas = process_citas(content_sub)
                
                if level == 1:
                    sub_acep = {
                        "id_marcador_html": clean_structural_tags(marker),
                        "id_limpio": clean_marker.strip(),
                        "definicion": sub_def,
                        "ejemplos_citas": sub_citas,
                        "subsubacepciones": []
                    }
                    acepcion["subacepciones"].append(sub_acep)
                    current_sub_acep = sub_acep
                else:
                    # Level 2 (sub-subacepción)
                    subsub_acep = {
                        "id_marcador_html": clean_structural_tags(marker),
                        "id_limpio": clean_marker.strip(),
                        "definicion": sub_def,
                        "ejemplos_citas": sub_citas
                    }
                    if current_sub_acep is not None:
                        current_sub_acep["subsubacepciones"].append(subsub_acep)
                    else:
                        implicit_sub = {
                            "id_marcador_html": "",
                            "id_limpio": "",
                            "definicion": "",
                            "ejemplos_citas": [],
                            "subsubacepciones": [subsub_acep]
                        }
                        acepcion["subacepciones"].append(implicit_sub)
                        current_sub_acep = implicit_sub
            data["acepciones"].append(acepcion)

    if constr_match:
        # Construction section goes until Etim or end of file
        data['construccion_sintactica'] = clean_structural_tags(balance_tags(content[pos_constr_start:pos_etim_start].strip()))

    etim_start = pos_etim_start
    if not etim_match and pos_normal_end < len(content) and pos_normal_end != pos_constr_start:
        etim_start = pos_normal_end
        
    if etim_start < len(content):
        data['etimologia'] = clean_structural_tags(balance_tags(content[etim_start:].strip()))

    return data

def main():
    html_dir = r'd:\ICC-2026\pasantía\cuervo\CD-ROM\html'
    json_dir = r'd:\ICC-2026\pasantía\cuervo\json'
    os.makedirs(json_dir, exist_ok=True)
    
    files = glob.glob(os.path.join(html_dir, '*.htm'))
    valid_files = [f for f in files if not re.search(r'_[ef]\.htm$', f, re.IGNORECASE) and not os.path.basename(f).startswith('a-x')]
    
    print(f"Found {len(valid_files)} valid HTM files... Processing.")
    
    index_lemas = []
    
    for count, filepath in enumerate(valid_files):
        filename = os.path.basename(filepath)
        json_filename = filename.replace('.htm', '.json')
        
        parsed = parse_html_to_json(filepath)
        if parsed and parsed.get('lema'):
            lema_clean = re.sub(r'<[^>]+>', '', parsed['lema']).strip()
            if lema_clean:
                index_lemas.append({
                    "lema": lema_clean,
                    "file": json_filename
                })
                
                out_path = os.path.join(json_dir, json_filename)
                with open(out_path, 'w', encoding='utf-8') as out_f:
                    json.dump(parsed, out_f, ensure_ascii=False, indent=2)
        
        if (count + 1) % 250 == 0 or (count + 1) == len(valid_files):
            print(f"Processed {count + 1}/{len(valid_files)}")

    index_lemas.sort(key=lambda x: x['lema'].lower())
    
    # Save both _index.json and index_db.json
    with open(os.path.join(json_dir, '_index.json'), 'w', encoding='utf-8') as idx_f:
        json.dump(index_lemas, idx_f, ensure_ascii=False, indent=2)
        
    with open(os.path.join(json_dir, 'index_db.json'), 'w', encoding='utf-8') as idx_f:
        json.dump(index_lemas, idx_f, ensure_ascii=False, indent=2)
        
    print(f"Finished processing. Total extracted lemmas: {len(index_lemas)}")

if __name__ == '__main__':
    main()
