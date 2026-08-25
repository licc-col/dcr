"""
Script de Conversión Masiva: Diccionario Cuervo (HTML a JSON)
-----------------------------------------------------------
Este script procesa archivos HTML de un diccionario lexicográfico antiguo 
y los convierte a una estructura JSON organizada, preservando el formato 
original y manejando casos complejos de sub-acepciones marcadas con símbolos griegos.
"""

import argparse
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

def drop_orphan_closers(text, tags):
    """Elimina las etiquetas de cierre que no tienen apertura previa."""
    abiertas = {t: 0 for t in tags}
    def visor(match):
        nombre = match.group(2).lower()
        if nombre not in abiertas:
            return match.group(0)
        if match.group(1):
            if abiertas[nombre] == 0:
                return ''
            abiertas[nombre] -= 1
        else:
            abiertas[nombre] += 1
        return match.group(0)
    return re.sub(r'<(/?)([a-zA-Z]+)[^>]*>', visor, text)

def clean_structural_tags(text):
    """
    Limpia etiquetas de bloque (<p>, <br>) al inicio y final de los textos.
    Mejora la alineación visual en el visor (flexbox/grid).
    """
    text = re.sub(r'^(<p[^>]*>|<br/?>|\s)+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'(</p>|<br/?>|\s)+$', '', text, flags=re.IGNORECASE)
    return text

import html

def strip_html_tags(text, keep=()):
    """
    Elimina las etiquetas HTML y decodifica entidades HTML.
    Normaliza los espacios en blanco y descarta caracteres de control
    (el HTML del CD-ROM arrastra un NUL de fin de fichero).

    `keep` es una tupla de nombres de etiqueta que se conservan (ej. ('i',))
    para no perder las cursivas significativas de la etimología.
    """
    if not text:
        return ""
    if keep:
        keep_re = '|'.join(keep)
        clean = re.sub(r'<(?!/?(?:' + keep_re + r')\b)[^>]+>', '', text, flags=re.IGNORECASE)
    else:
        clean = re.sub(r'<[^>]+>', '', text)
    # Decodificar entidades HTML
    clean = html.unescape(clean)
    # Eliminar caracteres de control residuales de la digitalización
    clean = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', clean)
    # Normalizar espacios
    clean = re.sub(r'\s+', ' ', clean).strip()
    if keep:
        # La fuente anida mal <p> e <i>, dejando cierres sin apertura
        clean = drop_orphan_closers(clean, keep).strip()
        clean = balance_tags(clean)
    return clean

def clean_and_preserve_paragraphs(text, keep=()):
    """
    Separa el texto mediante etiquetas de párrafo o salto de línea,
    limpia cada párrafo de HTML y los une con saltos de línea dobles.
    """
    if not text:
        return ""
    paragraphs = re.split(r'</p>|<p[^>]*>|<br\s*/?>', text, flags=re.IGNORECASE)
    cleaned_paras = []
    for p in paragraphs:
        clean_p = strip_html_tags(p, keep=keep)
        if clean_p:
            cleaned_paras.append(clean_p)
    return "\n\n".join(cleaned_paras)


def normalizar_espacios(text):
    """
    Corrige separaciones perdidas en la digitalización, como el "SigloXV" de las
    cabeceras de período anteclásico, y colapsa espacios sobrantes.
    """
    if not text:
        return ""
    text = re.sub(r'\b(Siglos?)(?=[IVXL]{1,4}\b)', r'\1 ', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = re.sub(r'[ \t]+([,;:])', r'\1', text)
    return text.strip()


# --- Marcas de autoría de los ejemplos (ver ayuda/presenta/Signos.htm del CD-ROM) ---
# En la fuente, la marca ANTECEDE al ejemplo que introduce:
#   X : va dentro del run azul (#000080) que abre la cita.
#   + : va al final del run negro previo, o como <font face="symbol">+</font>.
# Al partir el texto por «, ambas quedaban pegadas al final del campo anterior.
BLUE_RUN_OPEN = re.compile(r'<font[^>]*#000080[^>]*>', re.IGNORECASE)
MARCA_CRUZ = re.compile(r'\+\s*(?:<[^>]*>\s*)*$')
MARCA_EQUIS = re.compile(r'(?:^|[\s>])([Xx])\s*(?:<[^>]*>\s*)*$')

def extract_trailing_marca(chunk):
    """
    Separa del final de `chunk` la marca (X o +) que en realidad abre el ejemplo
    siguiente. Devuelve (chunk_sin_marca, marca).
    """
    if not chunk:
        return chunk, ""
    m = MARCA_CRUZ.search(chunk)
    if m:
        return chunk[:m.start()], "+"
    # La X sólo cuenta como marca si está dentro de un run azul; así no se
    # confunde con un numeral romano de una referencia bibliográfica.
    m = MARCA_EQUIS.search(chunk)
    if m:
        # Es marca si va dentro del run azul de la cita, o si el run azul se
        # abre justo después; así no se confunde con un numeral romano suelto.
        fonts = re.findall(r'<font[^>]*>', chunk[:m.start(1)], flags=re.IGNORECASE)
        # Sin ninguna etiqueta <font> por delante, la cita anterior y la marca
        # comparten el mismo run azul heredado del bloque.
        en_run_azul = '#000080' in fonts[-1] if fonts else True
        abre_cita = bool(BLUE_RUN_OPEN.search(chunk[m.end(1):]))
        if en_run_azul or abre_cita:
            return chunk[:m.start(1)], "X"
    return chunk, ""


# Subacepción de tercer nivel: un <p> cuyo primer carácter visible es un guion
# largo que NO va seguido de letra griega (esos son los niveles 1 y 2).
TERCER_NIVEL_RE = re.compile(
    r'((?:<p[^>]*>\s*)(?:<(?!/?p\b)[^>]*>\s*)*[—–]\s*(?!(?:<[^>]*>\s*)*[α-ωΑ-Ω]))',
    re.IGNORECASE)

def split_tercer_nivel(block):
    """Parte un bloque en [contenido, marcador, contenido, marcador, contenido...]."""
    return TERCER_NIVEL_RE.split(block or "")


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

def _protect_parenthesis_quotes(t):
    if not t:
        return ""
    def replace_parens(match):
        inner = match.group(0)
        if '«' in inner or '»' in inner:
            inner = inner.replace('«', '@@@LQUOT@@@').replace('»', '@@@RQUOT@@@')
        return inner
    return re.sub(r'\([^)]*\)', replace_parens, t)

def _restore_parenthesis_quotes(t):
    if not t:
        return ""
    return t.replace('@@@LQUOT@@@', '«').replace('@@@RQUOT@@@', '»')

def process_citas(text):
    """
    Parte un bloque en su definición y sus citas.
    Devuelve (definicion, citas, marca_final); `marca_final` es una X o + que
    quedó al final del bloque sin ejemplo que introducir.
    """
    protected_text = _protect_parenthesis_quotes(text)
    segments = re.split(r'«', protected_text)

    # La marca que cierra un segmento pertenece al ejemplo que abre el siguiente.
    marcas = [""] * len(segments)
    for i in range(len(segments) - 1):
        segments[i], marca = extract_trailing_marca(segments[i])
        marcas[i + 1] = marca
    segments[-1], marca_final = extract_trailing_marca(segments[-1])

    def_text = strip_html_tags(segments[0]).strip()
    # Clean leading dot and space
    def_text = re.sub(r'^\s*\.\s*', '', def_text).strip()
    if not re.search(r'\w', def_text):
        def_text = ""
    def_text = _restore_parenthesis_quotes(def_text)

    citas_list = []
    for idx, c in enumerate(segments[1:], start=1):
        qp = re.split(r'»', c, maxsplit=1)
        texto_cita = "«" + strip_html_tags(qp[0]) + ("»" if len(qp) > 1 else "")
        texto_cita = _restore_parenthesis_quotes(texto_cita)
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
        ref_raw = _restore_parenthesis_quotes(ref_raw)
        citas_list.append({
            "marca": marcas[idx],
            "texto_cita": texto_cita,
            "autor": autor_raw,
            "referencia_obra": ref_raw
        })
    return def_text, citas_list, marca_final


def fill_node(node, block):
    """
    Rellena definición, ejemplos y subacepciones de tercer nivel (—) de un nodo.
    """
    partes = split_tercer_nivel(block)
    definicion, citas, marca = process_citas(partes[0])
    node["definicion"] = definicion
    node["marca"] = marca
    node["ejemplos_citas"] = citas

    hijos = []
    for k in range(1, len(partes), 2):
        cuerpo = partes[k + 1] if k + 1 < len(partes) else ""
        def3, citas3, marca3 = process_citas(cuerpo)
        if not def3 and not citas3:
            continue
        hijos.append({
            "id_limpio": "—",
            "definicion": def3,
            "marca": marca3,
            "ejemplos_citas": citas3
        })
    node["subsubsubacepciones"] = hijos
    return node


def build_subacepciones(acepcion, subparts):
    """
    Recorre los marcadores griegos de un bloque y cuelga las subacepciones
    (1 griega) y subsubacepciones (2 griegas) de la acepción dada.
    """
    current_sub_acep = None
    for j in range(1, len(subparts), 2):
        marker = subparts[j].strip()
        clean_marker = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', marker).strip())

        greek_letters = "".join(c for c in clean_marker if 'Ͱ' <= c <= 'Ͽ')
        if not greek_letters:
            stripped = re.sub(r'[\s—\-‑\)]', '', clean_marker)
            level = len(stripped) if stripped else 1
        else:
            level = len(greek_letters)

        content_sub = subparts[j + 1] if j + 1 < len(subparts) else ""

        nodo = {
            "id_marcador_html": strip_html_tags(marker),
            "id_limpio": clean_marker,
            "definicion": "",
            "marca": "",
            "ejemplos_citas": [],
            "subsubsubacepciones": []
        }
        if level == 1:
            nodo["subsubacepciones"] = []
        fill_node(nodo, content_sub)

        if level == 1:
            acepcion["subacepciones"].append(nodo)
            current_sub_acep = nodo
        else:
            if current_sub_acep is None:
                current_sub_acep = {
                    "id_marcador_html": "",
                    "id_limpio": "",
                    "definicion": "",
                    "marca": "",
                    "ejemplos_citas": [],
                    "subsubsubacepciones": [],
                    "subsubacepciones": []
                }
                acepcion["subacepciones"].append(current_sub_acep)
            current_sub_acep["subsubacepciones"].append(nodo)


def parse_html_to_json(filepath):
    try:
        with open(filepath, 'r', encoding='windows-1252', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        return None

    content = re.sub(r'[\r\n]+', ' ', content)
    
    # Clean comment wrappers from dicentry and dicgrammar, keeping their content, and strip other comments
    content = re.sub(r'<!--\s*>\s*(<dicentry>.*?</dicentry>)\s*-->', r'\1', content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r'<!--\s*>\s*(<dicgrammar>.*?</dicgrammar>)\s*-->', r'\1', content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
    
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
    if m_lema:
        raw_lema = strip_html_tags(m_lema.group(1))
        lema_val = raw_lema.strip()
        if lema_val:
            # Trailing dot normalization: if it doesn't end with a dot,
            # nor ends with a dot followed by an asterisk, nor ends with a parenthesis
            # preceded by a dot (homograph markers).
            if not lema_val.endswith('.') and not re.search(r'\.\s*\*\s*$', lema_val) and not (lema_val.endswith(')') and re.search(r'\.\s*\([^)]+\)$', lema_val)):
                lema_val += '.'
        data['lema'] = lema_val
    
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

    if not real_acep_matches:
        # Lemma has no main alphabetical acep (e.g. abominar, abusar)
        block = content[pos_gram_end:pos_normal_end].strip()

        acepcion = {
            "id": "",
            "definicion": "",
            "marca": "",
            "ejemplos_citas": [],
            "subsubsubacepciones": [],
            "subacepciones": []
        }

        subparts = split_subacepciones(block)
        fill_node(acepcion, subparts[0])
        # Sin acepción alfabética maestra, la cabecera del bloque es la introducción.
        data['introduccion'] = acepcion['definicion']
        acepcion['definicion'] = ""

        build_subacepciones(acepcion, subparts)
        data["acepciones"].append(acepcion)
    else:
        # Standard alphabetical acepciones exist
        data['introduccion'] = clean_and_preserve_paragraphs(content[pos_gram_end:real_acep_matches[0].start()])

        for i in range(len(real_acep_matches)):
            start_idx = real_acep_matches[i].end()
            if i + 1 < len(real_acep_matches):
                end_idx = real_acep_matches[i+1].start()
            else:
                end_idx = pos_normal_end

            block = content[start_idx:end_idx].strip()
            acep_html_id = real_acep_matches[i].group(1).strip()
            acepcion_id = strip_html_tags(acep_html_id).strip()
            acepcion_id = re.sub(r'\.$', '', acepcion_id).strip()

            acepcion = {
                "id": acepcion_id,
                "definicion": "",
                "marca": "",
                "ejemplos_citas": [],
                "subsubsubacepciones": [],
                "subacepciones": []
            }

            subparts = split_subacepciones(block)
            fill_node(acepcion, subparts[0])
            build_subacepciones(acepcion, subparts)
            data["acepciones"].append(acepcion)


    # Extract and assign tail sections
    for i in range(len(unique_candidates)):
        pos, text = unique_candidates[i]
        next_pos = unique_candidates[i+1][0] if i + 1 < len(unique_candidates) else len(content)
        
        block = content[pos:next_pos].strip()
        key = get_section_key(text)
        if key:
            # La etimología conserva sus cursivas: en el original sólo van en
            # cursiva las formas citadas, no el bloque entero.
            keep = ('i',) if key == 'etimologia' else ()
            cleaned_block = normalizar_espacios(clean_and_preserve_paragraphs(block, keep=keep))
            if key in data:
                if data[key]:
                    data[key] += "\n\n" + cleaned_block
                else:
                    data[key] = cleaned_block

    # Clean category duplicate leaks from introduccion
    if data['introduccion'] and data['introduccion'].startswith('-->'):
        data['introduccion'] = re.sub(r'^-->\s*(?:[a-zA-Z]+)?\b\.?\s*', '', data['introduccion']).strip()

    # Clean leading duplicate lemma occurrences from introduccion
    if data['introduccion'] and data['lema']:
        lema_clean_norm = re.sub(r'[\s.,()\-‑—*]+', '', data['lema']).strip().lower()
        if lema_clean_norm:
            for _ in range(10):  # Maximum 10 iterations to prevent any infinite loops
                intro_str = data['introduccion'].strip()
                if not intro_str:
                    break
                first_chunk = re.split(r'\n+|<br\s*/?>|</p>|<p[^>]*>', intro_str, maxsplit=1)[0].strip()
                if not first_chunk:
                    break
                first_chunk_clean = re.sub(r'[\s.,()\-‑—*]+', '', first_chunk).strip().lower()
                if first_chunk_clean == lema_clean_norm:
                    remainder = intro_str[len(first_chunk):].strip()
                    remainder = re.sub(r'^(?:[\s.,()\-‑—]+|<br\s*/?>|</p>|<p[^>]*>)+', '', remainder).strip()
                    data['introduccion'] = remainder
                else:
                    break

    # Clean invalid introductions (grammatical tags, duplicate of the lemma, etc.)
    if data['introduccion']:
        intro_str = data['introduccion']
        intro_clean = re.sub(r'[\s.,()\-‑—]+', ' ', intro_str).strip().lower()
        lema_clean = re.sub(r'[\s.,()\-‑—*]+', ' ', data['lema']).strip().lower()
        
        is_invalid = False
        if not intro_clean or intro_clean == lema_clean:
            is_invalid = True
        else:
            gram_words = {
                's', 'f', 'm', 'adj', 'v', 'adv', 'prep', 'pron', 'art', 'conj', 'interj',
                'pl', 'sing', 'tr', 'intr', 'ref', 'p', 'part', 'a', 'd', 'c', 'masc', 'fem',
                'n', 'u', 't', 'g', 'o', 'r', 'e', 'x'
            }
            words = intro_clean.split()
            if all(w in gram_words for w in words):
                is_invalid = True
                
        if is_invalid:
            data['introduccion'] = ""

    # La categoría gramatical no debe repetirse al inicio de la introducción
    if data['introduccion'] and data['categoria_gramatical']:
        cat = data['categoria_gramatical'].strip()
        if cat and data['introduccion'].startswith(cat):
            data['introduccion'] = data['introduccion'][len(cat):].lstrip(' .,;:').strip()

    data['introduccion'] = normalizar_espacios(data['introduccion'])

    return data

def main():
    parser = argparse.ArgumentParser(description='Convierte el HTML del CD-ROM del DCR a JSON.')
    parser.add_argument('--src', default='/core_dataset/dcr/cuervo/html',
                        help='Directorio con los .htm del CD-ROM')
    parser.add_argument('--out', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'json'),
                        help='Directorio de salida de los .json')
    args = parser.parse_args()

    html_dir = args.src
    json_dir = args.out
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
