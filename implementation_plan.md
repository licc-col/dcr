# Plan de Mejoramiento de la Extracción — Microestructura DCR de Cuervo

Este documento presenta el plan de implementación y mejoramiento de la extracción y visualización del **Diccionario de construcción y régimen de la lengua castellana (DCR)** de Rufino José Cuervo, alineado rigurosamente con la terminología de [microestructura_actualizada.txt](file:///d:/ICC-2026/pasant%C3%ADa/microestructura_actualizada.txt).

Adicionalmente, detalla la solución técnica para lemas (tales como `abominar` y `abusar`) que carecen de acepción alfabética maestra (`a)`, `b)`) y comienzan directamente con `Subacepción con símbolo inicial` (`α`, `β`), las cuales contienen a su vez `subsubacepción con símbolo inicial` (`αα`, `ββ`).

---

## 1. Nomenclatura Oficial del DCR (España)

En cumplimiento con la microestructura actualizada del DCR, se adopta de forma mandatoria la siguiente terminología oficial en español para todos los comentarios del código, la base de datos y la interfaz de usuario:

*   **Lema**: El vocablo o palabra cabecera de la entrada (e.g. `ABOMINAR`, `ABUSAR`).
*   **Categoría gramatical**: Clasificación morfosintáctica de la palabra (e.g. *v.*, *s.*, *adj.*) tanto global como locales subordinadas.
*   **Introducción**: Sección opcional inicial que contiene la definición general, sinónimos y acepciones introductorias opcionales (**1 acepción**, **2 acepción**).
*   **Macrogrupo semántico**: Nivel superior jerárquico denotado por números romanos como `(I)`, `(II)`.
*   **Grupo de acepciones**: Nivel intermedio de agrupación denotado por números arábigos tipo `1.`, `2.`.
*   **Acepción**: Definición alfabética principal denotada por letras tipo `a)`, `b)`.
*   **Subacepción con símbolo inicial**: Subacepción de nivel 1 denotada por letras griegas simples (`α`, `β`).
*   **subsubacepción con símbolo inicial**: Subacepción de nivel 2 denotada por letras griegas dobles (`αα`, `ββ`) que se anidan jerárquicamente dentro de su respectiva subacepción de nivel 1.
*   **Per. antecl. (Período anteclásico)**: Sección histórica que detalla el uso y ejemplos de siglos antiguos (e.g. siglo XIV).
*   **Test. lat. hisp. (Testimonios latino-hispánicos)**: Menciones y citas en latín medieval o hispánico.
*   **Etim. (Etimología)**: Análisis filológico, histórico y de raíces de la palabra.
*   **Nota**: Advertencias lexicográficas o de uso especial.
*   **Forma**: Variantes gráficas, flexivas o fonéticas del lema.
*   **Ortografía**: Particularidades ortográficas del lema a lo largo de la historia.
*   **Conjugación**: Apéndice sobre la flexión verbal.
*   **Construcciones**: Lista de enlaces de régimen y sintaxis (e.g. Con *á*, Con *de*).

---

## 2. Diagnóstico del Problema: Lemas sin Acepción Principal

En lemas simples como `abominar` y `abusar`, la fuente original no introduce letras de acepción principales `a)`, `b)` en color morado. Tras la definición introductoria general del lema, el texto pasa directamente a subacepciones griegas de primer nivel (`— α)`) y luego de segundo nivel (`— αα)`):

```html
<p ALIGN="JUSTIFY"><b>ABOMINAR. </b>... <i>v</i>.</p>
<p ALIGN="JUSTIFY">Propiamente, Rechazar como cosa infausta...</p>
<p ALIGN="JUSTIFY"><font face="arial">- </font><font face="symbol">a</font><font face="arial"> ) <i>Trans</i>. ...</font></p>
```

### Comportamientos y desajustes detectados:
1.  **Contenedores Vacíos en el Frontend:** El parser actual genera un bloque artificial de acepción maestra con `letter: ""` y `definition: ""`. Esto hace que el frontend dibuje una tarjeta vacía (recuadro con borde y fondo blanco pero sin título), restando limpieza visual.
2.  **Estructura Plana Inadecuada:** Las sub-subacepciones griegas (`αα`, `ββ`) se guardan de forma plana en el mismo array lineal `subAcepciones` de la acepción en lugar de anidarse recursivamente dentro de su respectiva subacepción padre de nivel 1.
3.  **Direccionamiento de Ejemplos/Citas Defectuoso:** Las citas subsiguientes en azul (`#000080`) no se asocian correctamente a la sub-subacepción correspondiente.

---

## 3. Propuesta de Solución e Implementación Técnica

### A. Modificación del Esquema Mongoose (`importDCR.js`)

Se mantiene el esquema jerárquico donde `subSubAcepcionSchema` está anidado dentro de `subAcepcionSchema`:

```javascript
const subSubAcepcionSchema = new mongoose.Schema({
  letter:     String,  // "— αα)", etc.
  definition: String,
  examples:   [exampleSchema],
}, { _id: false });

const subAcepcionSchema = new mongoose.Schema({
  letter:           String,  // "— α)", etc.
  type:             String,  // "Refl.", "Part.", etc.
  definition:       String,
  examples:         [exampleSchema],
  subSubAcepciones: [subSubAcepcionSchema], // ¡Anidado jerárquico!
}, { _id: false });
```

### B. Parser con Seguimiento de Estado Jerárquico en `importDCR.js`

En la función `parseLemmaFile(filePath)`, implementamos una variable de control de estado `let currentSubAcep = null;` al inicio del bucle de párrafos:

```javascript
let currentAcep = null;
let currentSubAcep = null; // Rastreará la subacepción activa (nivel 1)
```

Al procesar cada párrafo:

1.  **Al detectar una Acepción Maestra (`a)`, `b)`):**
    *   Empujar la acepción anterior a la lista.
    *   Inicializar una nueva acepción principal.
    *   Resetear el estado de la subacepción: `currentSubAcep = null`.

2.  **Al detectar una letra griega (Subacepción / Subsubacepción):**
    *   Si no hay acepción activa (`currentAcep` es nulo), se inicializa una acepción ficticia neutra (`letter: ""`, `definition: ""`).
    *   **Nivel 1 (`level === 1`, e.g. `α`):**
        *   Crear el objeto `Subacepción con símbolo inicial`:
            `currentSubAcep = { letter, type, definition, examples: [], subSubAcepciones: [] };`
        *   Empujarlo directamente a `currentAcep.subAcepciones`.
    *   **Nivel 2 (`level === 2`, e.g. `αα`):**
        *   Si no hay un `currentSubAcep` de nivel 1 activo, se genera uno ficticio implícito.
        *   Crear el objeto `subsubacepción con símbolo inicial` y empujarlo en `currentSubAcep.subSubAcepciones`.

3.  **Al detectar citas/ejemplos en azul:**
    *   Asignar la cita al nodo activo más específico de la jerarquía:
        ```javascript
        if (currentSubAcep) {
          if (currentSubAcep.subSubAcepciones?.length) {
            // Asignar a la última sub-subacepción activa
            currentSubAcep.subSubAcepciones.at(-1).examples.push(ex);
          } else {
            // Asignar a la subacepción activa
            currentSubAcep.examples.push(ex);
          }
        } else if (currentAcep) {
          // Asignar a la acepción general activa
          currentAcep.examples.push(ex);
        }
        ```

### C. Frontend SPA (`public/js/app.js`)

1.  **Detección de Acepción Vacía (`isDummyParent`):**
    *   Si `!acep.letter && !acep.definition`, se renderiza una tarjeta invisible (sin fondo ni bordes de tarjeta) pintando las subacepciones de nivel 1 a primer nivel de manera fluida y limpia.
2.  **Renderizado Recursivo de Sub-subacepciones:**
    *   El frontend consumirá directamente la propiedad `subSubAcepciones` de cada subacepción y la renderizará adecuadamente indentada.

---

## 4. Plan de Verificación

### Pruebas Automatizadas
1.  **Poblar base de datos local:**
    ```bash
    node src/parser/importDCR.js
    ```
2.  **Consultar Lemas Clave en MongoDB Shell:**
    ```javascript
    db.lemmas.findOne({ slug: "abominar" })
    db.lemmas.findOne({ slug: "abusar" })
    ```
    *Verificar:*
    *   `acepciones` contiene un único elemento con `letter: ""` e `introduction` bien extraída.
    *   `subAcepciones` contiene las subacepciones griegas de nivel 1 (`α`, `β`).
    *   Cada subacepción tiene su respectivo array `subSubAcepciones` conteniendo los elementos `αα` o `ββ` anidados recursivamente junto con sus citas en `examples`.

### Pruebas Manuales
1.  Iniciar servidor: `npm run dev`.
2.  Abrir `http://localhost:3000/`.
3.  Buscar `abominar` y verificar que la estructura visual sea impecable: sin contenedores fantasmas y con una indentación en cascada perfecta.
