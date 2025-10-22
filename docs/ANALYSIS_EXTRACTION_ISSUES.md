# 🔍 Análisis Profundo: Problemas de Extracción y Estructuración de PDFs

## 📊 Estado Actual de la Extracción

### ✅ Lo que SÍ funciona

1. **Detección de documentos legales**: 11 títulos, 19 capítulos, 345 artículos
2. **Detección de documentos técnicos**: 53 secciones, 158 subsecciones, 279 sub-subsecciones
3. **Chunking por artículos**: Cada artículo se convierte en un chunk con metadata de `capitulo` y `titulo`

### ❌ Problemas Críticos Identificados

## 1. **ANEXOS NO SE INDEXAN CORRECTAMENTE**

### El Problema

Los anexos se **detectan** en la extracción (línea 185-190 del extractor):
```python
if match := self.common_patterns["anexo"].search(line):
    structure["anexos"].append({
        "numero": match.group(1),
        "texto": line.strip(),
        "line_index": i,
    })
```

Pero **NO se usan** en el chunking. El chunker SOLO procesa:
- Para documentos legales: `articulos` (línea 79-86 del chunker)
- Para documentos técnicos: `secciones` y `subsecciones`
- **Los anexos nunca se convierten en chunks**

### Ejemplo del Problema

```
User: "Dame información del Anexo 8 del acuerdo único"
System: "No encontré información..."
```

**¿Por qué?** Porque el Anexo 8 nunca fue indexado. Los anexos están en el texto del PDF pero no en Qdrant.

---

## 2. **JERARQUÍA INCOMPLETA EN LOS CHUNKS**

### El Problema

Los chunks de artículos sí tienen `capitulo` y `titulo`, pero:

**FALTA información jerárquica del nombre/descripción:**
```python
chunk = {
    "capitulo": "2",        # ✅ Tiene el número
    "titulo": "4",          # ✅ Tiene el número
    "capitulo_nombre": ???  # ❌ NO EXISTE - ¿Cuál es el nombre del capítulo?
    "titulo_nombre": ???    # ❌ NO EXISTE - ¿Cuál es el nombre del título?
}
```

### Impacto

Cuando el LLM genera la respuesta, no puede decir:
> "El Capítulo 2 - Proyectos de Inversión trata sobre..."

Solo puede decir:
> "El Capítulo 2 trata sobre..."

**Pérdida de contexto semántico importante.**

---

## 3. **CHUNKS DEMASIADO LARGOS (9K-13K TOKENS)**

### El Problema

Según los logs:
```
WARNING | Chunk 399: Truncating from 11956 to 8191 tokens
WARNING | Chunk 544: Truncating from 12477 to 8191 tokens
WARNING | Chunk 551: Truncating from 13219 to 8191 tokens
```

Algunos chunks tienen **más de 13,000 tokens** (~52,000 caracteres).

### ¿Por qué?

El chunker usa **artículos completos** como chunks. Si un artículo es muy largo (tiene muchos parágrafos, incisos, tablas), el chunk es gigante.

### Impacto

1. **Pérdida de información**: Se truncan a 8191 tokens, perdiendo contenido
2. **Mala precisión de búsqueda**: Chunks muy grandes son menos específicos
3. **Contexto difuso**: El LLM recibe bloques enormes difíciles de procesar

---

## 4. **FALTA DETECCIÓN DE ELEMENTOS JERÁRQUICOS MENORES**

### Elementos NO Detectados

El extractor NO detecta:
- **Incisos** (numerales dentro de artículos: "1.", "2.", "3.")
- **Literales** (letras dentro de artículos: "a)", "b)", "c)")
- **Tablas** (contenido tabular importante)
- **Numerales romanos en contextos anidados**

### Ejemplo Real

```
ARTÍCULO 4.5.1.2 Variables susceptibles de ajuste

Los ajustes procederán cuando:
1. Existan modificaciones en el alcance del proyecto
2. Se requiera actualización de precios
3. Cambios en la normativa aplicable
   a) Normativa nacional
   b) Normativa regional
   c) Normativa local
```

**Actualmente**: Todo esto va en UN solo chunk gigante

**Debería**:
- Chunk principal con el artículo
- Chunks secundarios para cada numeral (vinculados al artículo padre)
- Chunks terciarios para cada literal (vinculados al numeral padre)

---

## 5. **CHUNKING POR ARTÍCULOS ES INFLEXIBLE**

### El Problema Conceptual

La estrategia actual es: **1 artículo = 1 chunk**

Esto falla cuando:
1. ✅ Artículos cortos (~100 tokens): Funciona bien
2. ❌ Artículos medianos (~1000 tokens): Pierde granularidad
3. ❌ Artículos largos (>5000 tokens): Se truncan, pierden información

### Ejemplo de Fallo

**Artículo largo sobre "Requisitos de viabilidad":**
- Tiene 15 requisitos enumerados
- Usuario pregunta: "¿Cuál es el requisito 7?"
- Sistema recupera chunk del artículo completo (8191 tokens truncado)
- LLM debe buscar el requisito 7 en un chunk gigante
- Puede no encontrarlo si fue truncado

**Mejor enfoque:**
- Chunk padre: Intro del artículo
- 15 chunks hijos: Uno por cada requisito
- Query enhancement detecta "requisito 7" y filtra

---

## 6. **ANEXOS NECESITAN TRATAMIENTO ESPECIAL**

### Características Únicas de los Anexos

1. **Contenido muy diferente**: Tablas, formularios, listas, diagramas
2. **Tamaño variable**: Desde 1 página hasta 50+ páginas
3. **Referencias cruzadas**: "Ver Anexo X" desde artículos
4. **Múltiples formatos**: Texto, tablas, imágenes

### Problema Actual

Los anexos se detectan pero:
- ❌ No se indexan como chunks
- ❌ No se vinculan a los artículos que los mencionan
- ❌ No se procesan según su contenido (tabla vs texto vs formulario)

---

## 7. **FALTA GRAFO DE RELACIONES**

### Lo que NO existe actualmente

No hay un grafo real de relaciones entre elementos:

```
Documento
  ├─ Título 1
  │   ├─ Capítulo 1
  │   │   ├─ Artículo 1.1.1
  │   │   │   ├─ Parágrafo 1
  │   │   │   └─ Parágrafo 2
  │   │   └─ Artículo 1.1.2
  │   └─ Capítulo 2
  └─ Anexos
      ├─ Anexo 1
      └─ Anexo 2
```

**Actualmente solo hay:**
- Chunks planos con metadata `capitulo=2, titulo=1`
- NO hay relaciones explícitas padre-hijo
- NO hay navegación jerárquica

### Impacto

No se puede hacer queries como:
- "Dame todos los artículos del Capítulo 2"
- "¿Qué parágrafos tiene el Artículo 4.5.1?"
- "Muestra la jerarquía completa del Título 3"

---

## 🎯 SOLUCIONES RECOMENDADAS

### Prioridad 1: ANEXOS (Crítico - bloquea queries actuales)

**Modificar el chunker para procesar anexos:**

```python
def _chunk_legal_document(self, content, structure, metadata):
    chunks = []

    # 1. Chunk articulos (ya existe)
    chunks.extend(self._chunk_articulos(...))

    # 2. Chunk anexos (NUEVO)
    chunks.extend(self._chunk_anexos(content, structure, metadata))

    return chunks

def _chunk_anexos(self, content, structure, metadata):
    chunks = []
    lines = content.split("\n")
    anexos = structure["anexos"]

    for i, anexo in enumerate(anexos):
        start_line = anexo["line_index"]
        # El anexo va desde su inicio hasta el próximo anexo o fin de documento
        end_line = (
            anexos[i + 1]["line_index"]
            if i + 1 < len(anexos)
            else len(lines)
        )

        anexo_text = "\n".join(lines[start_line:end_line]).strip()

        # Si el anexo es muy largo, dividirlo
        if self._count_tokens(anexo_text) > self.chunk_size:
            sub_chunks = self._split_long_text(
                anexo_text,
                metadata=metadata,
                anexo_numero=anexo["numero"],
                doc_type="legal"
            )
            chunks.extend(sub_chunks)
        else:
            chunk = self._create_chunk(
                text=anexo_text,
                metadata=metadata,
                anexo_numero=anexo["numero"],
                doc_type="legal"
            )
            chunks.append(chunk)

    return chunks
```

**Actualizar schema de chunks:**
```python
chunk = {
    # ... campos existentes ...
    "anexo_numero": "8",  # NUEVO
    "es_anexo": True,     # NUEVO
}
```

**Actualizar query enhancement:**
```python
# Detectar "Anexo 8", "anexo VIII"
"anexo": re.compile(
    r"anexo\s+(\d+|[IVXLCDM]+)",
    re.IGNORECASE
)
```

---

### Prioridad 2: NOMBRES DE CAPÍTULOS/TÍTULOS (Mejora UX)

**Guardar nombres junto con números:**

```python
def _chunk_legal_document(self, content, structure, metadata):
    # ... código existente ...

    # Extraer nombres de títulos y capítulos
    titulo_nombres = self._extract_nombres(structure["titulos"])
    capitulo_nombres = self._extract_nombres(structure["capitulos"])

    # Al crear chunk
    chunk = self._create_chunk(
        text=article_text,
        metadata=metadata,
        articulo=articulo["numero"],
        titulo=current_titulo,
        titulo_nombre=titulo_nombres.get(current_titulo),  # NUEVO
        capitulo=current_capitulo,
        capitulo_nombre=capitulo_nombres.get(current_capitulo),  # NUEVO
    )

def _extract_nombres(self, elements: List[Dict]) -> Dict[str, str]:
    """Extrae nombres de elementos jerárquicos."""
    nombres = {}
    for elem in elements:
        # "TÍTULO 4 PROYECTOS DE INVERSIÓN"
        # -> numero="4", nombre="PROYECTOS DE INVERSIÓN"
        numero = elem["numero"]
        texto_completo = elem["texto"]

        # Remover el prefijo "TÍTULO 4" para dejar solo el nombre
        nombre = re.sub(
            r"^(T[ÍI]TULO|CAP[ÍI]TULO)\s+\d+\s*:?\s*",
            "",
            texto_completo,
            flags=re.IGNORECASE
        ).strip()

        nombres[numero] = nombre

    return nombres
```

---

### Prioridad 3: CHUNKING INTELIGENTE (Performance + Precisión)

**Estrategia multi-nivel:**

```python
def _chunk_articulo_inteligente(self, article_text, articulo_numero, metadata, ...):
    """Chunking adaptativo según tamaño y estructura del artículo."""

    token_count = self._count_tokens(article_text)

    if token_count <= 500:
        # Artículo corto: 1 chunk completo
        return [self._create_chunk(text=article_text, ...)]

    elif token_count <= 2000:
        # Artículo mediano: dividir por parágrafos si existen
        if self._tiene_paragrafos(article_text):
            return self._chunk_por_paragrafos(article_text, ...)
        else:
            return [self._create_chunk(text=article_text, ...)]

    else:
        # Artículo largo: chunking jerárquico agresivo
        return self._chunk_jerarquico(
            article_text,
            max_chunk_size=800,  # Chunks más pequeños
            overlap=100,         # Mayor overlap para coherencia
            ...
        )
```

---

### Prioridad 4: DETECCIÓN DE INCISOS Y LITERALES (Granularidad)

```python
# Agregar patrones
self.legal_patterns = {
    # ... existentes ...
    "inciso": re.compile(r"^(\d+)\.\s+", re.MULTILINE),
    "literal": re.compile(r"^([a-z])\)\s+", re.MULTILINE),
}

# En chunking
def _chunk_con_incisos(self, article_text, ...):
    """Detecta y separa incisos dentro de artículos."""

    incisos = self.legal_patterns["inciso"].finditer(article_text)

    # Si tiene > 5 incisos, crear sub-chunks
    if len(list(incisos)) > 5:
        return self._split_by_incisos(article_text, ...)
    else:
        return [self._create_chunk(text=article_text, ...)]
```

---

### Prioridad 5: GRAFO DE RELACIONES (Feature completa)

**Esto es más complejo y sería Fase 2, pero el diseño sería:**

```python
# Chunk con relaciones
chunk = {
    # ... campos existentes ...
    "parent_id": "chunk_id_del_capitulo",   # Relación padre
    "children_ids": ["chunk_1", "chunk_2"], # Relaciones hijos
    "references": ["anexo_8_chunk_id"],     # Referencias cruzadas
    "hierarchy_path": "Título 4 > Capítulo 2 > Artículo 4.5.1",
}

# Query enhancement para navegación
if query == "Dame todos los artículos del Capítulo 2":
    # Buscar chunks con capitulo=2 y tipo=articulo
    # Ordenar por hierarchy_path
    # Retornar lista completa
```

---

## 📋 PLAN DE IMPLEMENTACIÓN SUGERIDO

### Fase Inmediata (Arregla queries actuales)
1. ✅ Implementar chunking de anexos
2. ✅ Actualizar query enhancement para detectar anexos
3. ✅ Actualizar vectorizer para incluir `anexo_numero` en payload
4. ✅ Re-ingestar documentos

### Fase 2 (Mejora UX)
1. ✅ Extraer y guardar nombres de capítulos/títulos
2. ✅ Actualizar prompts del LLM para usar nombres
3. ✅ Mejorar citaciones con nombres completos

### Fase 3 (Performance)
1. ✅ Implementar chunking inteligente adaptativo
2. ✅ Detectar y separar incisos/literales
3. ✅ Optimizar tamaño de chunks

### Fase 4 (Feature avanzada - opcional)
1. Crear grafo explícito de relaciones
2. Implementar navegación jerárquica
3. Visualización de estructura del documento

---

## 🎯 RECOMENDACIÓN FINAL

**Empezar con Prioridad 1 (ANEXOS) inmediatamente** porque:
- Es el problema más urgente (bloquea queries válidas)
- Es relativamente sencillo de implementar
- Tiene impacto inmediato visible para el usuario
- Es generalizable a otros documentos que tengan anexos

**Después implementar Prioridad 2 (NOMBRES)** porque:
- Mejora significativamente la calidad de las respuestas
- No requiere cambios en la arquitectura
- Compatible con solución de anexos

**Dejar Prioridades 3-4 para iteraciones futuras** basadas en:
- Feedback real de usuarios
- Análisis de queries más comunes
- Performance medida en producción
