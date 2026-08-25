# Estructura del Diccionario Cuervo (JSON)

Para facilitar la comprensión y futura expansión del proyecto, aquí se detalla la jerarquía y los campos extraídos del diccionario original:

## Jerarquía de Datos

El diccionario se organiza de forma jerárquica para preservar la lógica lexicográfica original:

1.  **Lema (Palabra Principal)**: El término que se define (ej. "ABANDONAR").
2.  **Categoría Gramatical**: Indica si es verbo, sustantivo, etc.
3.  **Introducción**: Texto introductorio con definiciones generales o breves sinónimos.
4.  **Acepciones (Grupos Principales)**: Marcadas con letras latinas minúsculas o números (**1, 2...** o **a, b, c...**).
    - **Definición**: El significado específico de esa acepción.
    - **Ejemplos/Citas**: Fragmentos literarios o frases de ejemplo que ilustran el uso.
5.  **Sub-acepciones / Construcciones**: Marcadas con letras griegas (**α, β, γ...** o **α α, β β...**).
    - Cuelgan de una acepción principal o sub-acepción.
    - Contienen su propia definición y su propio set de ejemplos.
6.  **Sub-acepciones de tercer nivel**: Marcadas con un guion largo (**—**).
    - Pueden colgar de una acepción, de una sub-acepción o de una sub-subacepción.
    - Corresponden al "— subacepción de tercer nivel" de la metodología de la microestructura.
7.  **Secciones Especiales y Apéndices (Cola del Artículo)**: Estructuras opcionales de gran valor filológico y lexicográfico:
    - **Periodo Anteclásico**: Testimonios del español medieval y preclásico.
    - **Testimonios Latino-Hispánicos**: Citas y referencias en latín de la península ibérica.
    - **Etimología**: Origen y evolución etimológica de la palabra.
    - **Nota**: Aclaraciones lexicográficas y de uso.
    - **Forma**: Variaciones morfológicas e históricas.
    - **Ortografía**: Aspectos ortográficos históricos y modernos.
    - **Conjugación**: Observaciones y tablas de flexión verbal.
    - **Construcciones Sintácticas**: Régimen, enlaces sintácticos y preposiciones asociadas.
    - **Prosodia**: Acentuación y pronunciación.
    - **Colocación y Concordancia**: Combinaciones habituales y concordancia gramatical.

## Campos del Objeto JSON

```json
{
  "lema": "String (con HTML)",
  "categoria_gramatical": "String",
  "introduccion": "String (HTML)",
  "acepciones": [
    {
      "id": "1., 2... o a), b)...",
      "definicion": "String",
      "marca": "\"X\", \"+\" o \"\" (marca sin ejemplo que introducir)",
      "ejemplos_citas": [
        {
          "marca": "\"X\", \"+\" o \"\"",
          "texto_cita": "String",
          "autor": "String",
          "referencia_obra": "String"
        }
      ],
      "subsubsubacepciones": [
        {
          "id_limpio": "—",
          "definicion": "...",
          "marca": "...",
          "ejemplos_citas": [...]
        }
      ],
      "subacepciones": [
        {
          "id_marcador_html": "String",
          "id_limpio": "— α )",
          "definicion": "...",
          "marca": "...",
          "ejemplos_citas": [...],
          "subsubacepciones": [...],
          "subsubsubacepciones": [...]
        }
      ]
    }
  ],
  "periodo_anteclasico": "String (HTML)",
  "testimonios_latino_hispanicos": "String (HTML)",
  "etimologia": "String (HTML)",
  "nota": "String (HTML)",
  "forma": "String (HTML)",
  "ortografia": "String (HTML)",
  "conjugacion": "String (HTML)",
  "construccion_sintactica": "String (HTML)",
  "prosodia": "String (HTML)",
  "colocacion_concordancia": "String (HTML)"
}
```

## Notas Técnicas

- **HTML**: Los campos se entregan en texto plano. La única excepción es `etimologia`, que conserva sus etiquetas `<i>`: en el original sólo van en cursiva las formas citadas, no el bloque entero, y el visor no debe aplicar cursiva global a esa sección.
- **Marcas de los ejemplos**: `marca` recoge el signo que **antecede** al ejemplo en el original. Según la página de Signos del CD-ROM, `+` señala los ejemplos de Martínez y `X` los del Departamento de Lexicografía. En el HTML fuente la `X` va dentro del run azul (`#000080`) que abre la cita y el `+` al final del run negro anterior; por eso una extracción ingenua los dejaba pegados al final del campo previo.
- **Símbolos**: Los caracteres especiales de la fuente original se han mapeado a sus equivalentes Unicode estándar (ej. `¾` -> `—`).
- **Robustez de Extracción**: El convertidor normaliza variaciones tipográficas u ortográficas provenientes de la digitalización original en CD-ROM (por ejemplo, emparejando "Per. antecel.", "Per. antecl.", "Test. latin. hisp." o "Conj." a sus llaves normalizadas correspondientes).
