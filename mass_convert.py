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

import html

def strip_html_tags(text):
    """
    Elimina todas las etiquetas HTML y decodifica entidades HTML.
    Normaliza los espacios en blanco.
    """
    if not text:
        return ""
    # Eliminar cualquier etiqueta HTML
    clean = re.sub(r'<[^>]+>', '', text)
    # Decodificar entidades HTML
    clean = html.unescape(clean)
    # Normalizar espacios
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

def get_section_key(header_text):
    clean = re.sub(r'<[^>]+>', '', header_text).strip().lower()
    clean_norm = re.sub(r'\.$', '', clean).strip()
    
    # 1. Periodo Anteclasico
    if any(p in clean_norm for p in ['per. antecl', 'período antecl', 'per. antecel', 'per. antec', 'periodo antec']):
        return 'periodo_anteclasico'
        
    # 2. Testimonios Latino-Hispanicos
    if any(p in clean_norm for p in ['test. lat', 'test. latin', 'text. lat', 'testimonios lat', 'testimonios latin', 'test. latin. hisp']):
        return 'testimonios_latino_hispanicos'
        
    # 3. Etimologia
    if 'etim' in clean_norm:
        return 'etimologia'
        
    # 4. Nota
    if 'nota' in clean_norm:
        return 'nota'
        
    # 5. Forma
    if 'forma' in clean_norm:
        return 'forma'
        
    # 6. Ortografia
    if 'ortografia' in clean_norm or 'ortografía' in clean_norm or 'ortogr' in clean_norm:
        return 'ortografia'
        
    # 7. Conjugacion
    if any(p in clean_norm for p in ['conjugacion', 'conjugación', 'conjug', 'conj']):
        return 'conjugacion'
        
    # 8. Construcciones
    if 'construccion' in clean_norm or 'construcción' in clean_norm or 'constr' in clean_norm:
        return 'construccion_sintactica'
        
    # 9. Prosodia
    if 'prosodia' in clean_norm or 'pros' in clean_norm:
        return 'prosodia'
        
    # 10. Colocacion y concordancia
    if any(p in clean_norm for p in ['colocacion', 'colocación', 'coloc', 'concordancia']):
        return 'colocacion_concordancia'
        
    return None

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
    
    data = {
        "lema": "",
        "categoria_gramatical": "",
        "introduccion": "",
        "acepciones": [],
        "periodo_anteclasico": "",
        "testimonios_latino_hispanicos": "",
        "etimologia": "",
        "nota": "",
        "forma": "",
        "ortografia": "",
        "conjugacion": "",
        "construccion_sintactica": "",
        "prosodia": "",
        "colocacion_concordancia": ""
    }
    
    m_lema = re.search(r'<dicentry>(.*?)</dicentry>', content, flags=re.IGNORECASE)
    if m_lema: data['lema'] = strip_html_tags(m_lema.group(1))
    
    m_gram = re.search(r'<dicgrammar>(.*?)</dicgrammar>', content, flags=re.IGNORECASE)
    pos_gram_end = m_gram.end() if m_gram else 0
    if m_gram: data['categoria_gramatical'] = strip_html_tags(m_gram.group(1))
        
    def is_real_acep(text):
        return get_section_key(text) is None

    dicarb_matches = list(re.finditer(r'<dicarbrecont>(.*?)</dicarbrecont>', content, flags=re.IGNORECASE))
    
    real_acep_matches = [m for m in dicarb_matches if is_real_acep(m.group(1))]
    special_matches = [m for m in dicarb_matches if not is_real_acep(m.group(1))]
    
    kw_pattern = (
        r'Per\.\s*antecl\.|Per\.\s*antecel\.|Período\s*antecl\.|'
        r'Test\.\s*lat\.\s*hisp\.|Test\.\s*latin\.\s*hisp\.|Text\.\s*lat\.\s*hisp\.|Test\.\s*lat\.\s*hist\.|'
        r'Etim\b\.?|Nota\b\.?|Forma\b\.?|Ortografía\b\.?|Ortogr\b\.?|Conjug\b\.?|Conj\b\.?|'
        r'Construcciones\b|Constr\b\.?|Prosodia\b|Pros\b\.?|Colocación\b|Coloc\b\.?'
    )
    header_regex = r'<p[^>]*>(?:\s*<[^>]+>)*\s*(' + kw_pattern + r')\b'
    regex_matches = list(re.finditer(header_regex, content, flags=re.IGNORECASE))
    
    candidates = []
    for m in special_matches:
        candidates.append((m.start(), m.group(0)))
    for m in regex_matches:
        candidates.append((m.start(), m.group(1)))
        
    unique_candidates = []
    if candidates:
        candidates.sort(key=lambda x: x[0])
        last_pos = -1
        for pos, text in candidates:
            if last_pos == -1 or pos > last_pos + 10:
                unique_candidates.append((pos, text))
                last_pos = pos
        pos_normal_end = unique_candidates[0][0]
    else:
        pos_normal_end = len(content)

    def process_citas(text):
        citas_list = []
        citas_split = re.split(r'«', text)
        def_text = strip_html_tags(citas_split[0])
        for c in citas_split[1:]:
            qp = re.split(r'»', c, maxsplit=1)
            texto_cita = "«" + strip_html_tags(qp[0]) + ("»" if len(qp) > 1 else "")
            autor_raw = ""
            ref_raw = ""
            if len(qp) > 1:
                remainder = qp[1].strip()
                m_autor = re.search(r'<dicautor>(.*?)</dicautor>', remainder, flags=re.IGNORECASE)
                if m_autor:
                    autor_raw = strip_html_tags(m_autor.group(1))
                    ref_raw = strip_html_tags(remainder[m_autor.end():])
                else:
                    ref_raw = strip_html_tags(remainder)
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
                    "id_marcador_html": strip_html_tags(marker),
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
                    "id_marcador_html": strip_html_tags(marker),
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
        data['introduccion'] = strip_html_tags(content[pos_gram_end:real_acep_matches[0].start()])
        
        for i in range(len(real_acep_matches)):
            start_idx = real_acep_matches[i].end()
            if i + 1 < len(real_acep_matches):
                end_idx = real_acep_matches[i+1].start()
            else:
                end_idx = pos_normal_end
            
            block = content[start_idx:end_idx].strip()
            acep_html_id = real_acep_matches[i].group(1).strip()
            acepcion_id = strip_html_tags(acep_html_id)
            
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
                        "id_marcador_html": strip_html_tags(marker),
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
                        "id_marcador_html": strip_html_tags(marker),
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

    # Extract and assign tail sections
    for i in range(len(unique_candidates)):
        pos, text = unique_candidates[i]
        next_pos = unique_candidates[i+1][0] if i + 1 < len(unique_candidates) else len(content)
        
        block = content[pos:next_pos].strip()
        key = get_section_key(text)
        if key:
            cleaned_block = strip_html_tags(block)
            if key in data:
                if data[key]:
                    data[key] += " " + cleaned_block
                else:
                    data[key] = cleaned_block

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
