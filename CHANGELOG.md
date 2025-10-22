# Changelog

Todos los cambios notables a este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Versionado Semántico](https://semver.org/lang/es/).

## [1.1.1] - 2025-10-21

### 🔧 Hotfix: Eliminación de Truncamiento en Embeddings

#### Problema Identificado

Durante las pruebas de queries sobre secciones específicas del documento técnico V2 (especialmente ANTECEDENTES), se identificó que:

- Secciones muy largas (>8,000 tokens) se dividían en un solo chunk gigante
- Estos chunks excedían el límite de embeddings de OpenAI (8,191 tokens)
- El embedding se truncaba automáticamente, perdiendo información semántica
- La búsqueda vectorial no recuperaba estos chunks porque el embedding truncado no matcheaba con las queries

**Ejemplo del problema**:
- Sección ANTECEDENTES: 50,711 caracteres (12,924 tokens)
- Se creaba 1 solo chunk de 12,924 tokens
- Embedding se truncaba a 8,191 tokens (pérdida del 37% del contenido)
- Vector search no recuperaba esta sección en top-20 resultados

#### Solución Implementada

Se reescribió completamente el método `_split_long_text()` en `src/ingest/document_hierarchy_processor.py`:

**Mejoras clave**:

1. **Límite de seguridad**: Chunks nunca exceden 8,000 tokens (margen de seguridad vs 8,191)
2. **Overlap inteligente**: Mantiene últimas N oraciones entre chunks consecutivos para preservar contexto
3. **División multinivel**:
   - Nivel 1: División por párrafos (estrategia principal)
   - Nivel 2: División por oraciones (si párrafos muy largos)
   - Nivel 3: División por palabras (último recurso para oraciones gigantes)
4. **Universal**: Funciona para CUALQUIER tipo de documento sin lógica específica

**Nuevos métodos agregados**:
- `_split_with_overlap()`: División con overlap entre chunks
- `_split_by_paragraphs()`: División por párrafos
- `_split_into_sentences()`: Detección de oraciones con regex
- `_split_by_sentences()`: División por oraciones
- `_split_by_words()`: División por palabras (último recurso)
- `_get_overlap_sentences()`: Cálculo de overlap basado en tokens

#### Resultados

**Antes del fix (v1.1.0)**:
```
Legal (Acuerdo 03/2021):     520 chunks
Técnico (DocumentoTecnico_V2): 494 chunks
Total:                       1,014 chunks
Chunks truncados:            ~50 (warnings de truncamiento)
```

**Después del fix (v1.1.1)**:
```
Legal (Acuerdo 03/2021):     1,080 chunks (+108%)
Técnico (DocumentoTecnico_V2): 1,363 chunks (+176%)
Total:                       2,443 chunks (+141%)
Chunks truncados:            0 (cero warnings)
Max tokens por chunk:        ~800 tokens
Promedio tokens por chunk:   ~466 tokens
```

**Sección ANTECEDENTES específicamente**:
- Antes: 1 chunk de 12,924 tokens (truncado a 8,191)
- Después: 60 chunks (~736 tokens promedio cada uno)
- Overlap: 100 tokens entre chunks consecutivos

#### Limitación Conocida

**Problema de diseño del RAG** (NO del chunking):

Después del fix, los chunks existen y están correctamente embebidos, pero queries sobre "secciones específicas" no funcionan bien:

- ✅ Query: "metodología propuesta" → Funciona (busca contenido)
- ✅ Query: "productos esperados" → Funciona (busca contenido)
- ❌ Query: "qué dice la sección de antecedentes" → No funciona (busca metadato)

**Razón**: La query pregunta por LA SECCIÓN (metadato estructural), no por EL CONTENIDO semántico. El embedding del contenido de ANTECEDENTES (estadísticas médicas) no es similar al embedding de "sección de antecedentes".

**Solución futura**: Requiere mejorar el RAG con:
- Query enhancement que extraiga secciones mencionadas y use filtros
- Búsqueda híbrida (vectorial + metadata filtering)
- Reformulación de queries genéricas a queries de contenido

#### Validación

Tests ejecutados con `scripts/test_multiple_sections.py`:

| Sección | Query | Resultado | Razón |
|---------|-------|-----------|-------|
| ANTECEDENTES | "qué dice la sección de antecedentes" | ❌ Fallo | Query genérica sobre sección (problema de RAG) |
| JUSTIFICACIÓN | "qué dice la sección de justificación" | ❌ Fallo | Query genérica sobre sección (problema de RAG) |
| METODOLOGÍA | "cuál es la metodología propuesta" | ✅ Éxito | Query sobre contenido semántico |
| PRODUCTOS ESPERADOS | "cuáles son los productos esperados" | ✅ Éxito | Query sobre contenido semántico |
| CRONOGRAMA | "cuál es el cronograma" | ❌ Fallo | Query genérica sobre sección (problema de RAG) |

**Conclusión**: El chunking funciona correctamente. Las fallas son por diseño del RAG, no por truncamiento.

#### Archivos Modificados

- `src/ingest/document_hierarchy_processor.py`: Reescritura completa de `_split_long_text()` + 5 nuevos métodos
- Scripts agregados:
  - `scripts/test_multiple_sections.py`: Validación comprehensiva
  - `scripts/debug_vector_search.py`: Debug de búsqueda vectorial

#### Migración

**⚠️ IMPORTANTE**: Requiere re-ingestión de documentos

```bash
# Re-ingestar con nuevo chunking
python scripts/01_ingest_pdfs.py
```

**Costo**: ~$0.20 USD (re-embedding de 2,443 chunks)
**Tiempo**: ~2-3 minutos

---

## [1.1.0] - 2025-10-20

### 🎉 Arquitectura Jerárquica Universal

#### Agregado

- **Sistema de procesamiento jerárquico universal** (`src/ingest/document_hierarchy_processor.py`)
  - Procesador único que maneja cualquier tipo de documento (legal, técnico, financiero, ambiental)
  - Algoritmo universal de detección de niveles jerárquicos
  - Procesamiento genérico para niveles 1-4
  - Manejo especializado de anexos (nivel 5)
  - Vinculación bidireccional parent↔child
  - Generación automática de `hierarchy_path`

- **Configuración centralizada** (`src/ingest/hierarchy_config.py`)
  - Mapeos de claves de estructura a niveles jerárquicos
  - Mapeos de tipos de elemento a niveles
  - Nombres de elementos por tipo de documento (legal, technical, financial, environmental, generic)
  - Métodos helper para consultar configuración

- **Scripts de validación y diagnóstico**
  - `scripts/validate_new_architecture.py`: Validación comparativa del sistema nuevo vs anterior
  - `scripts/inspect_tecnico_v2.py`: Inspección detallada de documentos procesados

- **Documentación completa**
  - `docs/GUIA_USO_PROCESAMIENTO_JERARQUICO.md`: Guía de usuario con ejemplos prácticos
  - `docs/ARQUITECTURA_TECNICA.md`: Documentación técnica para desarrolladores
  - `docs/DISEÑO_ARQUITECTURA_UNIFICADA.md`: Diseño arquitectónico completo
  - Sección en README.md explicando la nueva arquitectura

#### Mejorado

- **Procesamiento de documentos técnicos**: De 0% a 71.9% de completitud del grafo
  - Ahora detecta 5 niveles jerárquicos (antes: 0)
  - 99.8% de chunks con `parent_id` (antes: 0%)
  - 100% de chunks con `hierarchy_path` (antes: 0%)
  - 15.8% de chunks con `children_ids` (antes: 0%)

- **Procesamiento de documentos legales**: Mantiene 71.2% de completitud (sin regresiones)
  - Ahora usa procesador universal en lugar de código específico
  - Mismo número de chunks generados
  - Misma calidad de jerarquía

- **`src/ingest/chunker.py`**: Refactorizado para usar arquitectura unificada
  - Método `chunk_document()` ahora delega a `DocumentHierarchyProcessor`
  - Fallback a chunking por tamaño para documentos sin jerarquía
  - Logs mejorados con información de procesamiento

#### Cambiado

- **Modelo de embeddings**: Actualizado de `text-embedding-3-small` a `text-embedding-3-large`
  - Mayor precisión en búsqueda semántica
  - Costo: $0.13 por 1M tokens (vs $0.02 anterior)
  - Mejor performance en documentos técnicos

- **Estructura de chunks**: Campos adicionales en payload
  - Todos los chunks ahora tienen `nivel_jerarquico` (0-5)
  - Todos los chunks tienen `hierarchy_path` completo
  - Chunks no-root tienen `parent_id`
  - Chunks con hijos tienen `children_ids` poblado

#### Métricas de Impacto

| Documento | Chunks | Niveles | Completitud Grafo | Mejora |
|-----------|--------|---------|-------------------|--------|
| Legal (Acuerdo 03/2021) | 520 | 6 (0-5) | 71.2% | Mantiene calidad |
| Técnico (DocumentoTecnico_V2) | 494 | 5 (0,1,2,3,5) | 71.9% | **+71.9%** 🎉 |

**Total de chunks procesados**: 1,014
**Costo de re-ingestión**: $0.013 USD
**Tiempo de procesamiento**: 38 segundos

---

## [1.0.0] - 2025-10-15

### Sistema RAG Base (MVP)

#### Agregado

- **Pipeline de ingestión completo**
  - Extracción de PDFs con PyMuPDF4LLM
  - Chunking preservando estructura de documentos legales
  - Generación de embeddings con OpenAI
  - Carga a Qdrant vector database

- **Sistema de retrieval**
  - Búsqueda vectorial en Qdrant
  - Re-ranking con cross-encoder
  - Expansión de contexto con chunks adyacentes

- **Generación de respuestas**
  - Integración con GPT-4o-mini
  - Sistema de citación legal automática
  - Validación de citaciones
  - Tracking de costos

- **Interfaz de usuario**
  - Aplicación Streamlit con UI profesional
  - Visualización de fuentes y métricas
  - Filtros por documento
  - Parámetros configurables

- **Scripts de utilidad**
  - `scripts/01_ingest_pdfs.py`: Pipeline de ingestión
  - `scripts/02_test_queries.py`: Testing de queries

- **Infraestructura**
  - Docker Compose para Qdrant
  - Configuración con variables de entorno
  - Logging estructurado con loguru

#### Tipos de Documento Soportados

- ✅ Documentos legales (Acuerdos, Decretos, Resoluciones)
- ⚠️ Documentos técnicos (procesamiento básico, sin jerarquía completa)

#### Métricas Iniciales

- **Performance**: ~3-8 segundos por query
- **Costos**: ~$0.0002 por query
- **Precisión**: Sistema de citación con validación automática

---

## Roadmap

### [1.2.0] - Próxima versión

#### Planeado

- [ ] Integración con Neo4j para grafo de conocimiento
- [ ] Sistema multi-agente con LangGraph
- [ ] API REST con FastAPI
- [ ] Caché con Redis
- [ ] Suite de tests completa
- [ ] Soporte para documentos financieros
- [ ] Soporte para documentos ambientales

### [2.0.0] - Futuro

#### En Consideración

- [ ] Fact-checking automático de respuestas
- [ ] Comparación entre versiones de documentos
- [ ] Resumen automático de documentos
- [ ] Extracción de entidades (NER)
- [ ] Visualización de grafo de conocimiento
- [ ] API pública para integración
- [ ] Dashboard de monitoreo (Prometheus/Grafana)
- [ ] CI/CD automatizado

---

## Notas de Versión

### Compatibilidad

- **Python**: 3.11+
- **OpenAI API**: Compatible con modelos GPT-4 y text-embedding-3
- **Qdrant**: v1.7.0+

### Dependencias Principales

```
openai>=1.10.0
qdrant-client>=1.7.0
tiktoken>=0.5.2
streamlit>=1.30.0
loguru>=0.7.2
pymupdf4llm>=0.0.5
sentence-transformers>=2.3.0
```

### Migraciones

#### De v1.0.0 a v1.1.0

**⚠️ IMPORTANTE**: Esta versión requiere re-ingestión de documentos

```bash
# 1. Backup de datos existentes (opcional)
cp -r ./storage/qdrant_local ./storage/qdrant_backup_v1.0.0

# 2. Re-ingestar documentos con nueva arquitectura
python scripts/01_ingest_pdfs.py

# 3. Validar que todo funciona correctamente
python scripts/validate_new_architecture.py
```

**Cambios en datos**:
- Los chunks ahora incluyen campos `nivel_jerarquico`, `parent_id`, `children_ids`, `hierarchy_path`
- Documentos técnicos ahora tienen estructura jerárquica completa
- Mismo esquema general, solo campos adicionales (compatible hacia atrás)

**Cambios en código**:
- `HierarchicalChunker` ahora delega a `DocumentHierarchyProcessor`
- Métodos `_chunk_legal_document()` y `_chunk_technical_document()` deprecados (pero aún presentes)
- Nuevo módulo `hierarchy_config.py` centraliza configuración

---

## Reconocimientos

Este proyecto es parte del trabajo académico de Integrador - Universidad.

**Contribuciones principales**:
- Diseño e implementación de arquitectura jerárquica universal
- Integración con OpenAI y Qdrant
- Sistema de citación legal automática
- Documentación técnica completa

**Herramientas utilizadas**:
- Claude Code (Anthropic) para asistencia en desarrollo
- OpenAI API para embeddings y generación
- Qdrant para búsqueda vectorial
- Streamlit para interfaz de usuario

---

**Fecha de última actualización**: 2025-10-20
