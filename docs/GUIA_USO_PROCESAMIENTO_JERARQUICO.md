# Guía de Uso: Sistema de Procesamiento Jerárquico Unificado

## 📖 Índice

1. [Introducción](#introducción)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Guía de Uso Básico](#guía-de-uso-básico)
4. [Agregar Nuevos Tipos de Documento](#agregar-nuevos-tipos-de-documento)
5. [Scripts Disponibles](#scripts-disponibles)
6. [Validación y Testing](#validación-y-testing)
7. [Troubleshooting](#troubleshooting)
8. [Ejemplos Prácticos](#ejemplos-prácticos)

---

## Introducción

El sistema de procesamiento jerárquico unificado es una arquitectura genérica que permite procesar **cualquier tipo de documento** con estructura jerárquica (legal, técnico, financiero, ambiental, etc.) usando un único código base.

### Características Principales

- ✅ **Universal**: Un solo procesador para todos los tipos de documento
- ✅ **Configurable**: Agregar nuevos tipos solo requiere actualizar configuración
- ✅ **Jerárquico**: Mantiene relaciones parent-child multinivel (0-5 niveles)
- ✅ **Trazable**: Genera `hierarchy_path` completo para cada chunk
- ✅ **Adaptativo**: Chunking inteligente basado en tamaño de tokens
- ✅ **Validado**: Sistema de validación automática incluido

### Tipos de Documento Soportados

| Tipo | Niveles | Ejemplo de Estructura |
|------|---------|----------------------|
| **Legal** | 0-5 | Documento → Título → Capítulo → Artículo → Parágrafo → Anexo |
| **Técnico** | 0-5 | Documento → Sección → Subsección → Sub-subsección → Anexo |
| **Financiero** | 0-5 | Documento → Sección → Categoría → Subcategoría → Cuenta → Nota |
| **Ambiental** | 0-5 | Documento → Componente → Factor → Impacto → Medida → Anexo |
| **Genérico** | 0-5 | Documento → Sección → Subsección → Elemento → Sub-elemento → Anexo |

---

## Arquitectura del Sistema

### Componentes Principales

```
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE INGESTA                          │
│                                                             │
│  scripts/01_ingest_pdfs.py                                 │
│  └─> Orquesta todo el pipeline                            │
└─────────────────────┬───────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────┐
│               CAPA DE EXTRACCIÓN                            │
│                                                             │
│  src/ingest/pdf_extractor.py                               │
│  ├─> Detecta tipo de documento (legal/technical/etc)      │
│  ├─> Extrae estructura jerárquica                         │
│  └─> Genera metadata inicial                              │
└─────────────────────┬───────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────┐
│               CAPA DE CHUNKING                              │
│                                                             │
│  src/ingest/chunker.py (Orquestador)                       │
│  └─> Delega a DocumentHierarchyProcessor                  │
└─────────────────────┬───────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────┐
│          CAPA DE PROCESAMIENTO JERÁRQUICO                   │
│                                                             │
│  src/ingest/document_hierarchy_processor.py                │
│  ├─> process_document()       [Orquestador principal]     │
│  ├─> _detect_levels()         [Detecta niveles presentes] │
│  ├─> _create_root_node()      [Crea nodo raíz nivel 0]    │
│  ├─> _process_level()         [Procesa niveles 1-4]       │
│  └─> _process_anexos()        [Procesa anexos nivel 5]    │
└─────────────────────┬───────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────┐
│            CAPA DE CONFIGURACIÓN                            │
│                                                             │
│  src/ingest/hierarchy_config.py                            │
│  ├─> HIERARCHY_LEVELS          [Definición de niveles]    │
│  ├─> STRUCTURE_KEY_TO_LEVEL    [Mapeo claves→niveles]     │
│  ├─> ELEMENT_TYPE_TO_LEVEL     [Mapeo elementos→niveles]  │
│  └─> ELEMENT_NAMES             [Nombres por tipo doc]     │
└─────────────────────────────────────────────────────────────┘
```

### Flujo de Procesamiento

```
1. PDF → PDFExtractor
   ↓
   Detecta tipo: legal | technical | financial | environmental | generic
   Extrae estructura: {titulos: [...], capitulos: [...], ...}

2. Estructura → HierarchicalChunker
   ↓
   Verifica si tiene jerarquía (_has_hierarchy)

3. Si tiene jerarquía → DocumentHierarchyProcessor
   ↓
   a) Detecta niveles presentes (0-5)
   b) Crea nodo raíz (nivel 0)
   c) Procesa niveles 1-4 secuencialmente
   d) Procesa anexos (nivel 5)
   e) Vincula parent↔children
   f) Genera hierarchy_path

4. Chunks → Vectorizer
   ↓
   Genera embeddings y sube a Qdrant
```

---

## Guía de Uso Básico

### 1. Procesar Nuevos Documentos

#### Paso 1: Colocar PDFs en el directorio

```bash
# Copiar tus PDFs al directorio de datos
cp mi_documento.pdf data/

# Verificar que están en el directorio correcto
ls data/*.pdf
```

#### Paso 2: Ejecutar el pipeline de ingestión

```bash
# Activar entorno virtual
source venv/bin/activate

# Ejecutar pipeline completo
python scripts/01_ingest_pdfs.py
```

**Salida esperada:**

```
============================================================
RAG INGESTION PIPELINE - STARTING
============================================================

PHASE 1: EXTRACTING PDFs
✓ Extracted 2 documents

PHASE 2: CHUNKING DOCUMENTS
Usando procesador jerárquico unificado
Procesando documento: Mi Documento (tipo: legal)
Niveles jerárquicos detectados: [0, 1, 2, 3, 4]
✓ Creado nodo raíz (Nivel 0)
✓ Nivel 1: Creados 10 chunks
✓ Nivel 2: Creados 25 chunks
...

PHASE 3: VECTORIZING AND UPLOADING
✓ Vectorization completed
```

### 2. Validar Procesamiento

```bash
# Validar que la arquitectura funciona correctamente
python scripts/validate_new_architecture.py
```

**Verifica:**
- ✅ Niveles jerárquicos detectados
- ✅ Completitud del grafo (parent_id, children_ids, hierarchy_path)
- ✅ No hay regresiones en documentos existentes

### 3. Inspeccionar Documento Específico

Para inspeccionar cómo se procesó un documento específico, edita y ejecuta:

```bash
# Crear script personalizado basado en inspect_tecnico_v2.py
python scripts/inspect_mi_documento.py
```

---

## Agregar Nuevos Tipos de Documento

### Caso: Agregar Documentos Financieros

#### Paso 1: Actualizar `hierarchy_config.py`

Edita: `src/ingest/hierarchy_config.py`

```python
# 1. Agregar mapeo de estructura a nivel
STRUCTURE_KEY_TO_LEVEL = {
    # Documentos Legales (existentes)
    "titulos": 1,
    "capitulos": 2,
    "articulos": 3,
    "paragrafos": 4,

    # Documentos Técnicos (existentes)
    "secciones": 1,
    "subsecciones": 2,
    "subsubsecciones": 3,

    # NUEVOS: Documentos Financieros
    "categorias": 2,
    "subcategorias": 3,
    "cuentas": 4,
    "notas": 5,

    # Anexos (universal)
    "anexos": 5,
}

# 2. Agregar mapeo de tipo de elemento
ELEMENT_TYPE_TO_LEVEL = {
    # Legal (existentes)
    "titulo": 1,
    "capitulo": 2,
    "articulo": 3,
    "paragrafo": 4,

    # Técnico (existentes)
    "seccion": 1,
    "subseccion": 2,
    "subsubseccion": 3,

    # NUEVOS: Financiero
    "categoria": 2,
    "subcategoria": 3,
    "cuenta": 4,
    "nota": 5,

    # Genérico (existentes)
    "heading_1": 1,
    "heading_2": 2,
    ...
}

# 3. Agregar nombres de elementos
ELEMENT_NAMES = {
    "legal": {...},  # Existentes
    "technical": {...},  # Existentes

    # NUEVO: Financial
    "financial": {
        1: {"singular": "Sección", "plural": "Secciones"},
        2: {"singular": "Categoría", "plural": "Categorías"},
        3: {"singular": "Subcategoría", "plural": "Subcategorías"},
        4: {"singular": "Cuenta", "plural": "Cuentas"},
        5: {"singular": "Nota", "plural": "Notas"},
    },

    "environmental": {...},  # Existentes
    "generic": {...},  # Existentes
}
```

#### Paso 2: Actualizar `pdf_extractor.py` (si es necesario)

Edita: `src/ingest/pdf_extractor.py`

```python
def _detect_document_type(self, text: str, structure: Dict) -> str:
    """Detecta el tipo de documento basado en su contenido."""

    # Legal
    if structure.get("titulos") or structure.get("articulos"):
        return "legal"

    # Technical
    if structure.get("secciones") and structure.get("subsecciones"):
        return "technical"

    # NUEVO: Financial
    if structure.get("categorias") or structure.get("cuentas"):
        return "financial"

    # Environmental
    if structure.get("componentes") or structure.get("factores"):
        return "environmental"

    return "generic"
```

#### Paso 3: Agregar patrones de extracción (si es necesario)

Si tu documento financiero tiene patrones específicos para detectar categorías/cuentas:

```python
def _extract_financial_structure(self, text: str) -> Dict:
    """Extrae estructura de documentos financieros."""

    structure = {
        "categorias": [],
        "subcategorias": [],
        "cuentas": [],
        "notas": [],
        "anexos": []
    }

    # Patrón: "Categoría 1: Activos"
    categoria_pattern = r"Categoría\s+(\d+)\s*:\s*(.+?)(?=\n)"

    # Patrón: "Cuenta 1.1.1 - Efectivo"
    cuenta_pattern = r"Cuenta\s+([\d.]+)\s*[-–]\s*(.+?)(?=\n)"

    # ... extraer usando patrones

    return structure
```

#### Paso 4: Probar con Documento Real

```bash
# 1. Colocar PDF financiero en data/
cp estado_financiero_2024.pdf data/

# 2. Ejecutar ingesta
python scripts/01_ingest_pdfs.py

# 3. Validar
python scripts/validate_new_architecture.py
```

#### Paso 5: Inspeccionar Resultados

```python
# Crear scripts/inspect_financiero.py
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

client = QdrantClient(path="./storage/qdrant_local")

result = client.scroll(
    collection_name="normativa_sgr",
    scroll_filter=Filter(
        must=[FieldCondition(key="tipo_documento", match=MatchValue(value="financial"))]
    ),
    limit=10,
    with_payload=True,
)

for chunk in result[0]:
    print(f"Nivel: {chunk.payload.get('nivel_jerarquico')}")
    print(f"Categoría: {chunk.payload.get('categoria')}")
    print(f"Cuenta: {chunk.payload.get('cuenta')}")
    print(f"Path: {chunk.payload.get('hierarchy_path')}")
    print("-" * 80)
```

---

## Scripts Disponibles

### 1. `scripts/01_ingest_pdfs.py`

**Propósito**: Pipeline completo de ingestión (extracción → chunking → vectorización)

**Uso:**
```bash
python scripts/01_ingest_pdfs.py
```

**Qué hace:**
1. Extrae todos los PDFs del directorio `data/`
2. Detecta tipo de documento automáticamente
3. Procesa con arquitectura jerárquica unificada
4. Genera embeddings con OpenAI
5. Sube a Qdrant

**Parámetros configurables en `src/config.py`:**
- `chunk_size`: Tamaño máximo de chunk (default: 500 tokens)
- `chunk_overlap`: Solapamiento entre chunks (default: 50 tokens)
- `embedding_model`: Modelo de OpenAI (default: "text-embedding-3-large")

### 2. `scripts/validate_new_architecture.py`

**Propósito**: Validar que la arquitectura funciona correctamente

**Uso:**
```bash
python scripts/validate_new_architecture.py
```

**Qué valida:**
- ✅ Niveles jerárquicos detectados correctamente
- ✅ Completitud del grafo (parent_id, children_ids, hierarchy_path)
- ✅ No hay chunks sin jerarquía
- ✅ Distribución de chunks por nivel
- ✅ Mejoras vs sistema anterior

**Salida:**
```
VALIDACIÓN: DOCUMENTO LEGAL
✓ Tiene nodo raíz (nivel 0)
✓ Tiene títulos (nivel 1)
✓ Todos los chunks tienen jerarquía
Completitud del grafo: 71.2%

VALIDACIÓN: DOCUMENTO TÉCNICO
✓ Tiene secciones (nivel 1)
✓ MEJORA: Completitud del grafo moderada (71.9%)
✓ EXCELENTE: Todos los chunks tienen jerarquía

DECISIÓN:
✅ VALIDACIÓN EXITOSA
✓ Seguro proceder con re-ingestión
```

### 3. `scripts/inspect_tecnico_v2.py`

**Propósito**: Inspeccionar procesamiento de DocumentoTecnico_V2

**Uso:**
```bash
python scripts/inspect_tecnico_v2.py
```

**Qué muestra:**
- Total de chunks
- Distribución por niveles jerárquicos
- Secciones/subsecciones detectadas
- Completitud del grafo
- Ejemplos de chunks
- Problemas detectados

**Crear script personalizado:**
```python
# scripts/inspect_mi_documento.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from src.config import config

# Cambiar este valor por tu documento_id
DOCUMENTO_ID = "mi_documento"

# Conectar a Qdrant
client = QdrantClient(path=config.qdrant.path)

# Buscar chunks
result = client.scroll(
    collection_name=config.qdrant.collection_name,
    scroll_filter=Filter(
        must=[FieldCondition(key="documento_id", match=MatchValue(value=DOCUMENTO_ID))]
    ),
    limit=10000,
    with_payload=True,
)

chunks = result[0]
print(f"Total chunks: {len(chunks)}")

# Analizar niveles
niveles = {}
for chunk in chunks:
    nivel = chunk.payload.get('nivel_jerarquico', 'N/A')
    niveles[nivel] = niveles.get(nivel, 0) + 1

print("\nDistribución por nivel:")
for nivel, count in sorted(niveles.items()):
    print(f"  Nivel {nivel}: {count} chunks")
```

---

## Validación y Testing

### Checklist de Validación Pre-Producción

Antes de usar en producción, verifica:

- [ ] **Extracción correcta**
  ```bash
  # Los PDFs se extraen sin errores
  python -c "from src.ingest.pdf_extractor import extract_all_pdfs; from pathlib import Path; docs = extract_all_pdfs(Path('data')); print(f'Extraídos: {len(docs)}')"
  ```

- [ ] **Detección de tipo correcta**
  ```bash
  # Verifica que el tipo detectado sea correcto
  # Busca en logs: "Document type detected: legal/technical/etc"
  ```

- [ ] **Niveles jerárquicos completos**
  ```bash
  # Debe detectar al menos nivel 0 (root) y nivel 1
  python scripts/validate_new_architecture.py
  ```

- [ ] **Completitud del grafo > 50%**
  ```bash
  # Busca en salida: "Completitud del grafo: X%"
  # Debe ser > 50% para considerarse aceptable
  ```

- [ ] **Chunks vinculados correctamente**
  ```bash
  # parent_id debe estar presente en >90% de chunks
  # hierarchy_path debe estar en 100% de chunks
  ```

### Pruebas de Consulta

```python
# Test de búsqueda vectorial + jerarquía
from qdrant_client import QdrantClient
from src.config import config

client = QdrantClient(path=config.qdrant.path)

# Buscar chunks de un artículo específico
result = client.scroll(
    collection_name=config.qdrant.collection_name,
    scroll_filter=Filter(
        must=[
            FieldCondition(key="articulo", match=MatchValue(value="4.5.1.2")),
            FieldCondition(key="nivel_jerarquico", match=MatchValue(value=3))
        ]
    ),
    limit=10,
    with_payload=True,
)

for chunk in result[0]:
    print(f"Artículo: {chunk.payload['articulo']}")
    print(f"Path: {chunk.payload['hierarchy_path']}")
    print(f"Parent: {chunk.payload.get('parent_id', 'N/A')[:16]}")
    print(f"Children: {len(chunk.payload.get('children_ids', []))}")
    print("-" * 80)
```

---

## Troubleshooting

### Problema 1: "No se detectaron niveles jerárquicos"

**Síntoma:**
```
⚠️ NO SE ENCONTRARON CAMPOS nivel_jerarquico
El documento NO fue procesado con estructura jerárquica
```

**Causa**: El PDF no tiene estructura detectable o los patrones de extracción no coinciden

**Solución:**
1. Verificar que el PDF tiene estructura (no es imagen escaneada)
2. Revisar patrones en `pdf_extractor.py`:
   ```bash
   # Ver qué estructura se detectó
   python -c "
   from src.ingest.pdf_extractor import PDFExtractor
   from pathlib import Path
   extractor = PDFExtractor()
   doc = extractor.extract_pdf(Path('data/mi_documento.pdf'))
   print(doc['structure'])
   "
   ```
3. Agregar patrones personalizados si es necesario

### Problema 2: "Chunks muy grandes (truncados)"

**Síntoma:**
```
WARNING: Chunk 10: Truncating from 15000 to 8191 tokens
```

**Causa**: Elementos jerárquicos con mucho contenido (ej: anexos largos)

**Solución:**
1. Ajustar `aggressive_chunk_size` en `document_hierarchy_processor.py`:
   ```python
   # Línea ~50
   self.aggressive_chunk_size = 500  # Reducir de 800 a 500
   ```
2. O implementar chunking recursivo para anexos grandes

### Problema 3: "Completitud del grafo muy baja (<30%)"

**Síntoma:**
```
Completitud del grafo: 25.0%
⚠️ ALTO: Ningún chunk tiene children_ids asignados
```

**Causa**: Estructura plana o errores en vinculación parent-child

**Solución:**
1. Verificar que `_link_parent_child()` se ejecuta correctamente
2. Agregar logs de debugging:
   ```python
   # En document_hierarchy_processor.py, método _process_level()
   logger.debug(f"Parent encontrado: {parent_chunk['chunk_id'][:16]}")
   logger.debug(f"Agregando hijo: {chunk['chunk_id'][:16]}")
   ```

### Problema 4: "Documento no se procesa con jerarquía"

**Síntoma:**
```
Usando chunking por tamaño
No se detectó jerarquía
```

**Causa**: Método `_has_hierarchy()` no detecta estructura

**Solución:**
```python
# Verificar qué devuelve _has_hierarchy()
from src.ingest.chunker import HierarchicalChunker
chunker = HierarchicalChunker()

# Simular estructura
structure = {
    "secciones": [{"numero": "1", "texto": "..."}],
    "subsecciones": []
}

print(chunker._has_hierarchy(structure))  # Debe ser True
```

### Problema 5: "Error al generar embeddings"

**Síntoma:**
```
openai.error.RateLimitError: Rate limit exceeded
```

**Solución:**
1. Agregar rate limiting en `vectorizer.py`:
   ```python
   import time

   # En generate_embeddings()
   for i in range(0, len(texts), batch_size):
       batch = texts[i:i+batch_size]
       response = self.client.embeddings.create(...)
       time.sleep(0.5)  # Pausa entre batches
   ```

---

## Ejemplos Prácticos

### Ejemplo 1: Procesar Documento Legal Nuevo

```bash
# 1. Copiar PDF
cp "Decreto_123_2025.pdf" data/

# 2. Ejecutar ingesta
python scripts/01_ingest_pdfs.py

# 3. Verificar en logs
# Buscar: "Document type detected: legal"
# Buscar: "✓ Nivel 1: Creados X chunks"

# 4. Validar
python scripts/validate_new_architecture.py

# 5. Consultar
python -c "
from qdrant_client import QdrantClient
client = QdrantClient(path='./storage/qdrant_local')
result = client.scroll(
    collection_name='normativa_sgr',
    scroll_filter={'must': [{'key': 'documento_nombre', 'match': {'value': 'Decreto 123 2025'}}]},
    limit=5
)
for chunk in result[0]:
    print(chunk.payload['hierarchy_path'])
"
```

### Ejemplo 2: Buscar Todos los Artículos de un Capítulo

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

client = QdrantClient(path="./storage/qdrant_local")

# Buscar todos los artículos del Capítulo 5
result = client.scroll(
    collection_name="normativa_sgr",
    scroll_filter=Filter(
        must=[
            FieldCondition(key="capitulo", match=MatchValue(value="5")),
            FieldCondition(key="nivel_jerarquico", match=MatchValue(value=3)),  # Nivel artículo
            FieldCondition(key="documento_id", match=MatchValue(value="acuerdo_03_2021"))
        ]
    ),
    limit=100,
    with_payload=True,
)

print(f"Encontrados {len(result[0])} artículos en el Capítulo 5\n")

for chunk in result[0]:
    articulo = chunk.payload.get('articulo', 'N/A')
    titulo = chunk.payload.get('articulo_titulo', 'Sin título')
    print(f"Artículo {articulo}: {titulo}")
```

### Ejemplo 3: Navegar Jerarquía Completa

```python
def get_chunk_hierarchy(client, chunk_id, collection_name):
    """Obtiene la jerarquía completa de un chunk."""

    # Obtener chunk actual
    chunk = client.retrieve(
        collection_name=collection_name,
        ids=[chunk_id],
        with_payload=True
    )[0]

    hierarchy = []
    current = chunk

    # Navegar hacia arriba hasta el root
    while current:
        hierarchy.insert(0, {
            'nivel': current.payload['nivel_jerarquico'],
            'texto': current.payload['texto'][:100],
            'path': current.payload['hierarchy_path']
        })

        parent_id = current.payload.get('parent_id')
        if not parent_id:
            break

        current = client.retrieve(
            collection_name=collection_name,
            ids=[parent_id],
            with_payload=True
        )[0]

    return hierarchy

# Uso
from qdrant_client import QdrantClient
client = QdrantClient(path="./storage/qdrant_local")

chunk_id = "abc123..."  # ID de un chunk
hierarchy = get_chunk_hierarchy(client, chunk_id, "normativa_sgr")

for item in hierarchy:
    print(f"{'  ' * item['nivel']}Nivel {item['nivel']}: {item['path']}")
```

### Ejemplo 4: Obtener Todos los Hijos de un Nodo

```python
def get_children_recursive(client, chunk_id, collection_name, max_depth=3):
    """Obtiene todos los hijos de un nodo recursivamente."""

    chunk = client.retrieve(
        collection_name=collection_name,
        ids=[chunk_id],
        with_payload=True
    )[0]

    children_ids = chunk.payload.get('children_ids', [])

    if not children_ids or max_depth == 0:
        return []

    children = client.retrieve(
        collection_name=collection_name,
        ids=children_ids,
        with_payload=True
    )

    result = []
    for child in children:
        result.append({
            'id': child.id,
            'nivel': child.payload['nivel_jerarquico'],
            'path': child.payload['hierarchy_path'],
            'texto': child.payload['texto'][:100]
        })

        # Recursivo
        grandchildren = get_children_recursive(
            client, child.id, collection_name, max_depth - 1
        )
        result.extend(grandchildren)

    return result

# Uso
root_id = "..."  # ID del nodo raíz o título
children = get_children_recursive(client, root_id, "normativa_sgr")

print(f"Total de descendientes: {len(children)}\n")
for child in children[:10]:  # Mostrar primeros 10
    print(f"Nivel {child['nivel']}: {child['path']}")
```

---

## Mejores Prácticas

### 1. Nomenclatura de Archivos PDF

```
✅ Bueno:
- Acuerdo_03_2021.pdf
- Decreto_1234_2024.pdf
- EstadoFinanciero_Q4_2024.pdf

❌ Evitar:
- documento.pdf (muy genérico)
- version final final v2.pdf (espacios, caracteres especiales)
- Doc123.pdf (sin contexto)
```

### 2. Validar Después de Cada Ingesta

```bash
# Pipeline recomendado
python scripts/01_ingest_pdfs.py && \
python scripts/validate_new_architecture.py
```

### 3. Monitorear Costos

```bash
# Verificar costo en logs
grep "Total cost:" logs/ingestion.log

# Estimar costo antes de procesar
python -c "
import tiktoken
from pathlib import Path

enc = tiktoken.get_encoding('cl100k_base')
total_tokens = 0

for pdf in Path('data').glob('*.pdf'):
    # Estimación: 1 página ≈ 500 tokens
    # Ajustar según tu caso
    estimated_tokens = 500 * 100  # 100 páginas
    total_tokens += estimated_tokens

cost_per_million = 0.13  # text-embedding-3-large
estimated_cost = (total_tokens / 1_000_000) * cost_per_million
print(f'Tokens estimados: {total_tokens:,}')
print(f'Costo estimado: ${estimated_cost:.4f}')
"
```

### 4. Backup Antes de Re-ingestar

```bash
# Backup de Qdrant
cp -r ./storage/qdrant_local ./storage/qdrant_backup_$(date +%Y%m%d)

# Re-ingestar
python scripts/01_ingest_pdfs.py

# Si hay problemas, restaurar
# rm -rf ./storage/qdrant_local
# cp -r ./storage/qdrant_backup_YYYYMMDD ./storage/qdrant_local
```

### 5. Logs Detallados

```python
# En src/config.py, ajustar nivel de logs
import logging

# Para debugging
logging.basicConfig(level=logging.DEBUG)

# Para producción
logging.basicConfig(level=logging.INFO)
```

---

## Recursos Adicionales

### Documentación Relacionada

- [`DISEÑO_ARQUITECTURA_UNIFICADA.md`](../DISEÑO_ARQUITECTURA_UNIFICADA.md) - Diseño arquitectónico completo
- [`ANALISIS_COMPLETO_ARQUITECTURA_GRAFO.md`](../ANALISIS_COMPLETO_ARQUITECTURA_GRAFO.md) - Análisis del sistema anterior
- [`CLAUDE.md`](../CLAUDE.md) - Contexto general del proyecto

### Código Fuente Clave

- `src/ingest/hierarchy_config.py` - Configuración de jerarquías
- `src/ingest/document_hierarchy_processor.py` - Procesador principal
- `src/ingest/chunker.py` - Orquestador de chunking
- `src/ingest/pdf_extractor.py` - Extractor de PDFs

### Contacto y Soporte

Si encuentras problemas no documentados aquí:

1. Revisa los logs en `logs/` para mensajes de error detallados
2. Ejecuta el script de validación para diagnóstico automático
3. Verifica la configuración en `src/config.py`
4. Consulta ejemplos en `scripts/`

---

**Última actualización**: 2025-10-20
**Versión del sistema**: 1.0
**Estado**: ✅ Producción
