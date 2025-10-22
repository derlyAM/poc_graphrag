# 🏗️ DISEÑO DE ARQUITECTURA UNIFICADA PARA PROCESAMIENTO JERÁRQUICO

**Fecha**: 2025-01-20
**Versión**: 1.0
**Estado**: En implementación

---

## 📋 OBJETIVOS

1. **Generalización**: Procesar CUALQUIER tipo de documento con estructura jerárquica
2. **Robustez**: Mantener precisión actual y escalar sin degradación
3. **No-ruptura**: Preservar funcionalidad existente de documentos legales
4. **Extensibilidad**: Facilitar adición de nuevos tipos de documentos

---

## 🎯 PRINCIPIOS DE DISEÑO

### 1. **Separation of Concerns**
```
Detección de Estructura ≠ Procesamiento de Jerarquía ≠ Chunking de Contenido
```

### 2. **Configuration over Code**
```python
# Mapeos configurables en lugar de if/else hardcodeados
ELEMENT_TO_LEVEL = {
    "titulo": 1,
    "seccion": 1,
    # Nuevos tipos se agregan aquí sin cambiar el core
}
```

### 3. **Fail Gracefully**
```python
# Si no se detecta jerarquía → fallback a chunking simple
# Si falta metadata → usar valores por defecto
# Si hay inconsistencias → log warning pero continuar
```

### 4. **Test-First Refactoring**
```
1. Crear tests con salida actual (golden output)
2. Refactorizar código
3. Validar que tests pasan (misma salida)
4. Agregar nuevas features
```

---

## 🏛️ ARQUITECTURA PROPUESTA

### Componentes Principales

```
┌─────────────────────────────────────────────────────────────┐
│                    HierarchicalChunker                       │
│  (Clase existente - SE MANTIENE como orquestador)            │
│                                                               │
│  + chunk_document(document) → List[Dict]                     │
│    └─> Delega a DocumentHierarchyProcessor                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              DocumentHierarchyProcessor (NUEVO)              │
│  Procesador universal de jerarquías documentales             │
│                                                               │
│  + process_document(document) → List[Dict]                   │
│    ├─> _detect_levels(structure) → Set[int]                 │
│    ├─> _create_root_node(metadata, content) → Dict          │
│    ├─> _process_level(level, ...) → List[Dict]              │
│    └─> _process_anexos(...) → List[Dict]                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  HierarchyConfig (NUEVO)                     │
│  Configuración centralizada de jerarquías                    │
│                                                               │
│  HIERARCHY_LEVELS = {0: "Documento", 1: "División", ...}     │
│  ELEMENT_TO_LEVEL = {"titulo": 1, "seccion": 1, ...}         │
│  LEVEL_NAMES = {"legal": {...}, "technical": {...}}          │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 SCHEMA DE DATOS UNIVERSAL

### Chunk Schema (Actualizado)

```python
{
    # === CAMPOS UNIVERSALES (OBLIGATORIOS) ===
    "chunk_id": str,              # UUID
    "documento_id": str,          # ID del documento
    "documento_nombre": str,      # Nombre del documento

    "nivel_jerarquico": int,      # 0-5 (SIEMPRE presente)
    "parent_id": str | None,      # UUID del padre (None solo para nivel 0)
    "children_ids": List[str],    # UUIDs de hijos ([] si no tiene)
    "hierarchy_path": str,        # Path completo (SIEMPRE presente)

    "texto": str,                 # Contenido del chunk
    "longitud_tokens": int,       # Tokens del texto
    "tipo_documento": str,        # "legal" | "technical" | "hybrid" | ...

    # === CAMPOS ESPECÍFICOS POR TIPO (OPCIONALES) ===
    # Legal
    "titulo": str | None,
    "titulo_nombre": str | None,
    "capitulo": str | None,
    "capitulo_nombre": str | None,
    "articulo": str | None,
    "paragrafo": str | None,

    # Técnico
    "seccion": str | None,
    "subseccion": str | None,

    # Anexos (todos los tipos)
    "anexo_numero": str | None,
    "es_anexo": bool,

    # === CAMPOS DE NAVEGACIÓN ===
    "chunk_anterior_id": str | None,
    "chunk_siguiente_id": str | None,

    # === CAMPOS DE METADATA ===
    "citacion_corta": str,
    "fecha_procesamiento": str,
    "tipo_contenido": str,
}
```

---

## 🔄 FLUJO DE PROCESAMIENTO

### Flujo Detallado

```python
def chunk_document(document: Dict) -> List[Dict]:
    """
    Punto de entrada principal (EXISTENTE).
    Se mantiene firma para compatibilidad.
    """
    # 1. Determinar estrategia de procesamiento
    doc_type = document.get("document_type", "generic")
    structure = document["structure"]

    # 2. Usar procesador unificado
    if self._tiene_jerarquia(structure):
        processor = DocumentHierarchyProcessor(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        return processor.process_document(document)
    else:
        # Fallback a chunking simple
        return self._chunk_by_size(document["content"], document["metadata"])


class DocumentHierarchyProcessor:

    def process_document(self, document: Dict) -> List[Dict]:
        """
        Procesamiento unificado de CUALQUIER documento jerárquico.
        """
        chunks = []
        structure = document["structure"]
        metadata = document["metadata"]
        content = document["content"]
        lines = content.split("\n")

        # === PASO 1: DETECTAR NIVELES ===
        detected_levels = self._detect_levels(structure)
        logger.info(f"Niveles jerárquicos detectados: {sorted(detected_levels)}")

        # === PASO 2: CREAR NODO RAÍZ (Nivel 0) ===
        doc_chunk = self._create_root_node(metadata, content)
        chunks.append(doc_chunk)
        chunk_map = {doc_chunk["chunk_id"]: doc_chunk}

        # === PASO 3: PROCESAR NIVELES 1-4 EN ORDEN ===
        for level in sorted([l for l in detected_levels if 0 < l < 5]):
            level_chunks = self._process_level(
                level=level,
                structure=structure,
                content=content,
                lines=lines,
                metadata=metadata,
                existing_chunks=chunks,
                chunk_map=chunk_map
            )

            for chunk in level_chunks:
                chunks.append(chunk)
                chunk_map[chunk["chunk_id"]] = chunk

        # === PASO 4: PROCESAR ANEXOS (Nivel 5) ===
        if 5 in detected_levels:
            anexo_chunks = self._process_anexos(
                structure=structure,
                content=content,
                lines=lines,
                metadata=metadata,
                doc_chunk=doc_chunk
            )
            chunks.extend(anexo_chunks)

        # === PASO 5: LINKING SECUENCIAL ===
        chunks = self._link_sequential(chunks)

        logger.info(f"Total de chunks creados: {len(chunks)}")
        logger.info(f"  Nivel 0 (Documento): {sum(1 for c in chunks if c['nivel_jerarquico'] == 0)}")
        logger.info(f"  Nivel 1: {sum(1 for c in chunks if c['nivel_jerarquico'] == 1)}")
        logger.info(f"  Nivel 2: {sum(1 for c in chunks if c['nivel_jerarquico'] == 2)}")
        logger.info(f"  Nivel 3: {sum(1 for c in chunks if c['nivel_jerarquico'] == 3)}")
        logger.info(f"  Nivel 4: {sum(1 for c in chunks if c['nivel_jerarquico'] == 4)}")
        logger.info(f"  Nivel 5 (Anexos): {sum(1 for c in chunks if c['nivel_jerarquico'] == 5)}")

        return chunks
```

---

## 🔍 DETECCIÓN DE NIVELES

### Lógica de Detección

```python
def _detect_levels(self, structure: Dict) -> Set[int]:
    """
    Detecta qué niveles jerárquicos están presentes en el documento.

    Args:
        structure: Diccionario con elementos detectados por pdf_extractor

    Returns:
        Set de niveles presentes (ej: {0, 1, 2, 3, 5})
    """
    levels = {0}  # Nivel 0 (documento) siempre existe

    # Mapeo de elementos a niveles
    element_level_map = {
        # Legal
        "titulos": 1,
        "capitulos": 2,
        "articulos": 3,
        "paragrafos": 4,

        # Técnico
        "secciones": 1,
        "subsecciones": 2,
        "subsubsecciones": 3,

        # Anexos (todos los tipos)
        "anexos": 5,
    }

    # Detectar niveles presentes
    for element_type, elements in structure.items():
        if elements and element_type in element_level_map:
            level = element_level_map[element_type]
            levels.add(level)
            logger.debug(f"Detectado nivel {level} con {len(elements)} elementos ({element_type})")

    return levels
```

---

## 🔧 PROCESAMIENTO POR NIVEL

### Algoritmo Genérico

```python
def _process_level(
    self,
    level: int,
    structure: Dict,
    content: str,
    lines: List[str],
    metadata: Dict,
    existing_chunks: List[Dict],
    chunk_map: Dict
) -> List[Dict]:
    """
    Procesa un nivel jerárquico específico.
    GENÉRICO - funciona para cualquier tipo de elemento.
    """
    level_chunks = []

    # 1. Obtener elementos de este nivel
    elements = self._get_elements_for_level(level, structure)

    if not elements:
        return []

    logger.info(f"Procesando nivel {level}: {len(elements)} elementos")

    # 2. Procesar cada elemento
    for i, element in enumerate(elements):
        # 2a. Encontrar padre (chunk del nivel anterior)
        parent_chunk = self._find_parent_for_element(
            element=element,
            level=level,
            existing_chunks=existing_chunks,
            structure=structure
        )

        # 2b. Extraer texto del elemento
        start_line = element["line_index"]
        end_line = (
            elements[i + 1]["line_index"] if i + 1 < len(elements)
            else len(lines)
        )
        element_text = "\n".join(lines[start_line:end_line]).strip()

        # 2c. Construir hierarchy_path
        hierarchy_path = self._build_hierarchy_path(
            element=element,
            level=level,
            parent_chunk=parent_chunk,
            metadata=metadata
        )

        # 2d. Determinar metadata específica del elemento
        element_metadata = self._extract_element_metadata(element, level)

        # 2e. Aplicar chunking adaptativo si es necesario
        token_count = self._count_tokens(element_text)

        if token_count <= 500:
            # Elemento pequeño: un solo chunk
            chunk = self._create_chunk(
                text=element_text,
                metadata=metadata,
                nivel_jerarquico=level,
                parent_id=parent_chunk["chunk_id"],
                hierarchy_path=hierarchy_path,
                **element_metadata
            )
            level_chunks.append(chunk)
            parent_chunk["children_ids"].append(chunk["chunk_id"])

        else:
            # Elemento grande: dividir preservando jerarquía
            max_size = 800 if token_count > 2000 else 500
            overlap = 100 if token_count > 2000 else 50

            sub_chunks = self._split_long_text(
                text=element_text,
                metadata=metadata,
                nivel_jerarquico=level,
                parent_id=parent_chunk["chunk_id"],
                hierarchy_path=hierarchy_path,
                max_chunk_size=max_size,
                overlap=overlap,
                **element_metadata
            )

            for sub_chunk in sub_chunks:
                level_chunks.append(sub_chunk)
                parent_chunk["children_ids"].append(sub_chunk["chunk_id"])

    return level_chunks
```

---

## 🎨 CONSTRUCCIÓN DE HIERARCHY_PATH

### Algoritmo Universal

```python
def _build_hierarchy_path(
    self,
    element: Dict,
    level: int,
    parent_chunk: Dict,
    metadata: Dict
) -> str:
    """
    Construye el path jerárquico completo del elemento.

    Ejemplos:
    - "Acuerdo 03/2021"
    - "Acuerdo 03/2021 > Título 4 - PROYECTOS DE INVERSIÓN"
    - "... > Capítulo 2 - AJUSTES > Artículo 4.5.1"
    - "DocumentoTécnico_V2 > Sección 1 - IDENTIFICACIÓN > Subsección 1.1"
    """
    if level == 0:
        # Nivel raíz
        return metadata["documento_nombre"]

    # Obtener path del padre
    parent_path = parent_chunk.get("hierarchy_path", metadata["documento_nombre"])

    # Construir nombre del elemento actual
    element_name = self._format_element_name(element, level)

    # Combinar
    return f"{parent_path} > {element_name}"


def _format_element_name(self, element: Dict, level: int) -> str:
    """
    Formatea el nombre del elemento para el path.
    """
    numero = element.get("numero", "")
    nombre = element.get("nombre", "") or element.get("titulo", "")

    # Determinar prefijo según tipo de elemento
    element_type = self._get_element_type_for_level(level, element)

    prefixes = {
        "titulo": "Título",
        "capitulo": "Capítulo",
        "articulo": "Artículo",
        "paragrafo": "Parágrafo",
        "seccion": "Sección",
        "subseccion": "Subsección",
        "subsubseccion": "Sub-subsección",
        "anexo": "Anexo",
    }

    prefix = prefixes.get(element_type, "Elemento")

    if nombre:
        return f"{prefix} {numero} - {nombre}"
    else:
        return f"{prefix} {numero}"
```

---

## 🔗 VINCULACIÓN PADRE-HIJO

### Algoritmo de Búsqueda de Padre

```python
def _find_parent_for_element(
    self,
    element: Dict,
    level: int,
    existing_chunks: List[Dict],
    structure: Dict
) -> Dict:
    """
    Encuentra el chunk padre más apropiado para un elemento.

    Estrategia:
    1. Buscar en nivel anterior (level - 1)
    2. El padre debe estar ANTES del elemento actual (line_index)
    3. El padre debe ser el MÁS CERCANO (último antes del elemento)
    """
    current_line = element["line_index"]
    parent_level = level - 1

    # Candidatos: chunks del nivel anterior que están ANTES del elemento actual
    candidates = [
        chunk for chunk in existing_chunks
        if chunk.get("nivel_jerarquico") == parent_level
        and self._is_before(chunk, current_line, structure)
    ]

    if not candidates:
        # Fallback: buscar en nivel 0 (documento raíz)
        return next(c for c in existing_chunks if c["nivel_jerarquico"] == 0)

    # Retornar el más cercano (último en la lista)
    return candidates[-1]


def _is_before(self, chunk: Dict, current_line: int, structure: Dict) -> bool:
    """
    Determina si un chunk está antes de una línea dada.
    """
    # Obtener line_index del chunk basado en su metadata
    # (esto requiere buscar en structure)

    # Estrategia simplificada: usar el orden de creación
    # Los chunks se crean en orden, así que si ya existe, está antes
    return True  # Simplificación - mejorar en implementación real
```

---

## 📝 MEJORAS SOBRE SISTEMA ACTUAL

### 1. Menos Código Duplicado
```
ANTES:
- _chunk_legal_document(): 200 líneas
- _chunk_technical_document(): 150 líneas
- Total código duplicado: ~70%

DESPUÉS:
- process_document(): lógica universal
- Código específico: solo configuración
- Reducción: ~50% menos líneas
```

### 2. Mayor Mantenibilidad
```
ANTES: Agregar nuevo tipo → Copiar/pegar método completo
DESPUÉS: Agregar nuevo tipo → Actualizar config (5 líneas)
```

### 3. Mejor Testing
```
ANTES: Test cada método por separado
DESPUÉS: Test único del flujo universal + test de configs
```

### 4. Trazabilidad Mejorada
```
ANTES: hierarchy_path solo en documentos legales
DESPUÉS: hierarchy_path UNIVERSAL para todos los tipos
```

---

## ✅ CRITERIOS DE VALIDACIÓN

### Tests de Regresión

```python
def test_legal_document_unchanged():
    """Validar que documentos legales se procesan igual que antes."""
    # Cargar acuerdo-unico
    # Procesar con sistema NUEVO
    # Comparar con salida ANTERIOR (golden output)
    # Asegurar:
    #   - Mismo número de chunks
    #   - Misma estructura de grafo
    #   - Mismos hierarchy_paths
    #   - Mismas relaciones padre-hijo


def test_technical_document_now_works():
    """Validar que documentoTecnico_V2 ahora tiene jerarquía."""
    # Cargar documentoTecnico_V2
    # Procesar con sistema NUEVO
    # Validar:
    #   - nivel_jerarquico presente en TODOS los chunks
    #   - parent_id presente (excepto nivel 0)
    #   - children_ids poblados
    #   - hierarchy_path presente
    #   - Niveles 0, 1, 2, 3 presentes


def test_hybrid_document():
    """Validar soporte para documentos híbridos."""
    # Crear documento de prueba con:
    #   - TÍTULO I (legal)
    #   - 1. SECCIÓN TÉCNICA (técnico)
    #   - ANEXO A (anexo)
    # Validar que todos se procesan correctamente
```

---

## 🚀 PLAN DE MIGRACIÓN

### Fase 1: Implementación Base (Día 1)
- [ ] Crear `HierarchyConfig` con mapeos
- [ ] Crear `DocumentHierarchyProcessor` clase
- [ ] Implementar `_detect_levels()`
- [ ] Implementar `_create_root_node()`
- [ ] Implementar `_process_level()` básico
- [ ] Testing inicial con documento legal

### Fase 2: Migración Técnicos (Día 2)
- [ ] Actualizar `chunk_document()` para usar procesador unificado
- [ ] Migrar lógica técnica a sistema universal
- [ ] Testing con documentoTecnico_V2
- [ ] Validar jerarquía generada

### Fase 3: Refinamiento (Día 3)
- [ ] Optimizar `_find_parent_for_element()`
- [ ] Mejorar `_build_hierarchy_path()`
- [ ] Agregar manejo de edge cases
- [ ] Testing exhaustivo
- [ ] Documentación final

### Fase 4: Despliegue
- [ ] Re-ingestar documentos
- [ ] Validar en queries reales
- [ ] Monitorear métricas
- [ ] Ajustar si es necesario

---

## 📚 REFERENCIAS

- Código actual: `src/ingest/chunker.py`
- Especificación: `CLAUDE.md`
- Análisis previo: `ANALISIS_COMPLETO_ARQUITECTURA_GRAFO.md`
- Testing: `scripts/test_hierarchy.py`

---

**Estado**: ✅ Diseño aprobado - Listo para implementación
