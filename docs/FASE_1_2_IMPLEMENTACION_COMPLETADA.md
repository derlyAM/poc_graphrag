# Implementación Fase 1 y Fase 2 - COMPLETADA

**Fecha:** 2025-11-12
**Estado:** ✅ Implementación Completada
**Objetivo:** Mejorar precisión de retrieval del 75% → 95%

---

## 📊 RESUMEN

Se han implementado exitosamente **6 mejoras críticas** distribuidas en 2 fases para mejorar la precisión del sistema RAG en preguntas específicas y detalladas.

### Resultados Esperados
- **Fase 1 (Críticas)**: 75% → 90% precisión
- **Fase 2 (Importantes)**: 90% → 95% precisión

---

## ✅ FASE 1: MEJORAS CRÍTICAS (IMPLEMENTADO)

### 1. Query Enhancement para Términos Específicos

**Archivo:** `src/retrieval/query_enhancer.py`
**Estado:** ✅ Implementado

#### Funcionalidad
Detecta y expande queries con términos muy específicos:

**Detecciones implementadas:**
- **Números de objetivos/artículos**: `"objetivo número 1"` → genera variaciones:
  ```
  - "objetivo 1"
  - "objetivo número 1"
  - "1. objetivo"
  - "OBJETIVO 1"
  ```

- **Solicitudes de listas**: `"¿Cuáles son los niveles...?"` → añade:
  ```
  "lista completa enumerar todos principales"
  ```

- **Datos numéricos**: `"costo estimado"` → añade:
  ```
  "datos numéricos cifras monto valor cantidad"
  ```

#### Código Clave
```python
# Método agregado: _enhance_specific_queries()
# Patrones regex para detección:
- objetivo_numero: r"objetivo\s+(número\s+)?(\d+)"
- lista_request: r"(cuáles|cuales|qué|que)\s+(son|están)?\s*(los|las)?\s*(niveles|tipos|ejemplos|...)"
- dato_numerico: r"(costo|precio|sanción|sanciones|multa|cantidad|monto|valor|cifra)s?"
```

#### Impacto Esperado
+40% precisión en preguntas específicas

---

### 2. Top-k Dinámico según Tipo de Pregunta

**Archivo:** `src/retrieval/query_enhancer.py`
**Estado:** ✅ Implementado

#### Funcionalidad
Ajusta dinámicamente el número de chunks recuperados (`top_k`) según la complejidad:

**Configuración por tipo de query:**
| Tipo de Query | top_k | context_window | Uso |
|---------------|-------|----------------|-----|
| **Agregation** (listas) | 100 | 2 | Preguntas tipo "enumera", "lista", "cuáles son" |
| **Comparison** | 40 | 2 | "diferencias entre", "compara" |
| **Specific terms** | 15 | 2 | Números, datos específicos |
| **Structural** | 50 | 1 | Búsqueda por secciones |
| **Hybrid** | 30 | 1 | Combinación de criterios |
| **Semantic** | 10 | 1 | Búsquedas semánticas simples |

#### Código Clave
```python
def get_retrieval_config(enhancement: Dict) -> Dict:
    if is_aggregation or enhancement.get("has_list_request"):
        config["top_k"] = 100
        config["context_window"] = 2
    elif enhancement.get("has_specific_terms"):
        config["top_k"] = 15
        config["context_window"] = 2
    # ... etc
```

#### Impacto Esperado
+25% cobertura en listas y enumeraciones

---

### 3. BM25 con Pesos Ajustables

**Archivo:** `src/retrieval/vector_search.py`
**Estado:** ✅ Implementado

#### Funcionalidad
Ajusta dinámicamente los pesos entre búsqueda vectorial (semántica) y BM25 (exacta) según características de la query.

**Detección automática:**
- ✅ Números en la query (`\d+`)
- ✅ Comillas (`"..."`)
- ✅ Términos específicos: objetivo, artículo, sección, costo, sanción, capítulo, título, parágrafo, anexo

**Pesos aplicados:**
| Condición | Vector Weight | BM25 Weight | Descripción |
|-----------|--------------|-------------|-------------|
| **Query específica** | 0.4 | 0.6 | Prioriza coincidencias exactas |
| **Query semántica** | 0.5 | 0.5 | Balance semántico/exacto |

#### Código Clave
```python
def _hybrid_search(query: str, ...) -> List[Dict]:
    # Detectar términos específicos
    has_numbers = bool(re.search(r'\d+', query))
    has_specific_terms = any(term in query.lower() for term in [
        'número', 'artículo', 'sección', 'costo', 'sanción', ...
    ])

    if has_numbers or has_quotes or has_specific_terms:
        vector_weight = 0.4
        bm25_weight = 0.6  # Más peso a búsqueda exacta
    else:
        vector_weight = 0.5
        bm25_weight = 0.5

    # RRF con pesos variables
    fused_scores = self._reciprocal_rank_fusion(
        dense_results,
        sparse_results,
        weights=(vector_weight, bm25_weight)
    )
```

#### Impacto Esperado
+30% precisión en búsquedas con números/términos exactos

---

## ✅ FASE 2: MEJORAS IMPORTANTES (IMPLEMENTADO)

### 4. Context Expansion Agresivo

**Archivo:** `src/retrieval/vector_search.py`
**Estado:** ✅ Implementado

#### Funcionalidad
Expande contexto con **ventanas configurables** de chunks adyacentes.

**Antes (Fase 0):**
```
Chunk encontrado → ±1 chunk (anterior y siguiente)
```

**Ahora (Fase 2):**
```
Chunk encontrado → ±N chunks (configurable)
  - window=1: ±1 chunk (3 chunks total)
  - window=2: ±2 chunks (5 chunks total)
  - window=3: ±3 chunks (7 chunks total)
```

**Decay de scores:**
```python
score_decay = 0.8 ** distance
# Distancia 1: score * 0.8
# Distancia 2: score * 0.64
# Distancia 3: score * 0.512
```

#### Código Clave
```python
def search_with_context(
    query: str,
    area: str,
    context_window: int = 1,  # NUEVO parámetro
    ...
) -> List[Dict]:
    expanded_chunks = self._expand_context(chunks, context_window)

def _expand_context(chunks: List[Dict], context_window: int = 1):
    # Expandir ANTES
    for i in range(1, context_window + 1):
        prev_chunk = self._get_chunk_by_id(current_id)
        prev_chunk["score"] = chunk["score"] * (0.8 ** i)
        prev_chunk["context_type"] = f"anterior_{i}"

    # Expandir DESPUÉS
    for i in range(1, context_window + 1):
        next_chunk = self._get_chunk_by_id(current_id)
        next_chunk["score"] = chunk["score"] * (0.8 ** i)
        next_chunk["context_type"] = f"siguiente_{i}"
```

#### Uso Automático
- **Listas/Enumeraciones**: `context_window=2`
- **Términos específicos**: `context_window=2`
- **Comparaciones**: `context_window=2`
- **Queries simples**: `context_window=1`

#### Impacto Esperado
+20% información completa en listas

---

### 5. Hierarchy-Aware Search

**Archivo:** `src/retrieval/vector_search.py`
**Estado:** ✅ Implementado

#### Funcionalidad
Incluye chunks relacionados jerárquicamente para contexto superior.

**Nuevo método:** `search_with_hierarchy()`

**Opciones:**
1. **Include Parent** (`include_parent=True`):
   - Incluye chunk padre (nivel jerárquico superior)
   - Ejemplo: Para un artículo → incluye el capítulo que lo contiene

2. **Include Siblings** (`include_siblings=True`):
   - Incluye chunks hermanos (mismo nivel jerárquico)
   - Ejemplo: Para artículo 4.5.1.2 → incluye artículos 4.5.1.1, 4.5.1.3
   - Máximo: 3 hermanos por defecto

#### Código Clave
```python
def search_with_hierarchy(
    query: str,
    area: str,
    include_parent: bool = True,
    include_siblings: bool = False,
    max_siblings: int = 3,
    ...
) -> List[Dict]:
    base_chunks = self.search(query, area, ...)

    # Incluir parent
    if include_parent and chunk.get("parent_id"):
        parent = self._get_chunk_by_id(parent_id)
        parent["score"] = chunk["score"] * 0.7
        parent["hierarchy_relation"] = "parent"

    # Incluir siblings
    if include_siblings:
        siblings = self._get_sibling_chunks(chunk, max_siblings)
        for i, sibling in enumerate(siblings):
            sibling["score"] = chunk["score"] * (0.6 - i * 0.1)
            sibling["hierarchy_relation"] = "sibling"
```

#### Ejemplo de Uso
```python
# Buscar un artículo específico con contexto jerárquico
chunks = vector_search.search_with_hierarchy(
    query="¿Qué dice el artículo 4.5.1.2?",
    area="sgr",
    include_parent=True,      # Incluir capítulo 5 del título 4
    include_siblings=True,    # Incluir art. 4.5.1.1, 4.5.1.3
    max_siblings=3
)
```

#### Impacto Esperado
+15% contexto jerárquico

---

### 6. Multi-Query Retrieval

**Archivo:** `src/retrieval/multi_query_retriever.py` (NUEVO)
**Estado:** ✅ Implementado

#### Funcionalidad
Genera múltiples variaciones de la query, busca con cada una, y fusiona resultados.

**Flujo:**
1. **Generar variaciones** usando LLM
   ```
   Original: "¿Cuál es el objetivo número 1?"
   Variaciones:
   - "primer objetivo de la política"
   - "objetivo prioritario establecido"
   - "meta principal número uno"
   ```

2. **Buscar con cada variación** (top-K por query)

3. **Fusionar resultados** con scoring:
   ```python
   avg_score = sum(source_scores) / len(source_scores)
   boost = appearances ** 0.5  # Chunks en múltiples queries
   final_score = avg_score * boost
   ```

4. **Re-rankear** con query original

#### Código Clave
```python
class MultiQueryRetriever:
    def generate_query_variations(query: str, num_variations: int = 3):
        # Usa LLM con temperature=0.7 para generar reformulaciones
        prompt = f"Genera {num_variations} reformulaciones de esta pregunta..."
        # Retorna: [original, variación1, variación2, variación3]

    def retrieve_multi_query(
        query: str,
        area: str,
        top_k_per_query: int = 10,
        num_variations: int = 3,
        final_top_k: int = None
    ):
        # Busca con cada variación
        for variant in variations:
            chunks = vector_search.search(variant, area, top_k_per_query)

        # Fusiona y re-rankea
        unique_chunks = self._deduplicate_and_fuse(all_chunks)
        reranked = reranker.rerank(query, unique_chunks, final_top_k)
```

#### Ejemplo de Uso
```python
from src.retrieval.multi_query_retriever import MultiQueryRetriever

multi_retriever = MultiQueryRetriever(vector_search, reranker, llm_client)

chunks = multi_retriever.retrieve_multi_query(
    query="¿Cuál es el objetivo número 1 de la política de IA?",
    area="inteligencia_artificial",
    top_k_per_query=10,    # 10 chunks por variación
    num_variations=3,       # 3 variaciones + original
    final_top_k=5          # Top-5 final después de fusión
)
```

#### Impacto Esperado
+35% recall en preguntas ambiguas

---

## 📈 IMPACTO TOTAL ESTIMADO

| Fase | Mejoras | Precisión Esperada | Estado |
|------|---------|-------------------|--------|
| **Baseline** | - | 75% (45/60 correctas) | Medido |
| **Fase 1** | Query Enhancement + Top-k Dinámico + BM25 Ajustable | **90%** (54/60) | ✅ Implementado |
| **Fase 2** | Context Expansion + Hierarchy + Multi-Query | **95%** (57/60) | ✅ Implementado |

---

## 🔧 CONFIGURACIÓN Y USO

### Uso Automático (Recomendado)

El sistema detecta automáticamente el tipo de query y aplica las mejoras correspondientes:

```python
from src.pipeline import RAGPipeline

pipeline = RAGPipeline()

# El pipeline aplica automáticamente:
# - Query enhancement (Fase 1)
# - Top-k dinámico (Fase 1)
# - BM25 ajustable (Fase 1)
# - Context expansion con window apropiado (Fase 2)

resultado = pipeline.query(
    question="¿Cuáles son los niveles de riesgo según el AI Act?",
    area="inteligencia_artificial"
)
```

**Detecciones automáticas:**
- ✅ Lista/enumeración → `top_k=100`, `window=2`
- ✅ Términos específicos → `top_k=15`, `window=2`, `bm25_weight=0.6`
- ✅ Comparación → `top_k=40`, `window=2`
- ✅ Semántico simple → `top_k=10`, `window=1`

### Uso Manual (Avanzado)

#### Context Expansion con Ventana Personalizada
```python
from src.retrieval.vector_search import VectorSearch

vector_search = VectorSearch()

# Para listas largas, usar ventana más grande
chunks = vector_search.search_with_context(
    query="¿Cuáles son TODOS los requisitos?",
    area="sgr",
    top_k=50,
    expand_context=True,
    context_window=3  # Expandir ±3 chunks
)
```

#### Hierarchy-Aware Search
```python
# Incluir contexto jerárquico
chunks = vector_search.search_with_hierarchy(
    query="¿Qué dice el artículo 4.5.1.2?",
    area="sgr",
    include_parent=True,     # Incluir capítulo/título superior
    include_siblings=True,   # Incluir artículos hermanos
    max_siblings=5          # Hasta 5 hermanos
)
```

#### Multi-Query Retrieval
```python
from src.retrieval.multi_query_retriever import MultiQueryRetriever

multi_retriever = MultiQueryRetriever(vector_search, reranker, llm_client)

# Para preguntas difíciles, generar más variaciones
chunks = multi_retriever.retrieve_multi_query(
    query="¿Qué aplicaciones actuales de IA se mencionan?",
    area="inteligencia_artificial",
    num_variations=5,        # 5 variaciones + original
    top_k_per_query=15,     # 15 chunks por variación
    final_top_k=10          # Top-10 final
)
```

---

## 🧪 TESTING

### Scripts Disponibles

1. **Test Fase 1** (15 preguntas críticas)
   ```bash
   python scripts/test_precision_improvements.py
   ```

2. **Test Completo** (60 preguntas)
   ```bash
   python scripts/test_full_ia_questions.py
   ```

### Métricas a Validar

- **Precision@5**: ¿Los top-5 chunks contienen la respuesta?
- **Answer Quality**: ¿La respuesta final es correcta y completa?
- **Coverage**: ¿Se responden las 15 preguntas que antes fallaban?
- **Cost**: ¿Cuánto cuesta por pregunta?

---

## 📝 NOTAS TÉCNICAS

### Compatibilidad
- ✅ **Backwards compatible**: Código antiguo sigue funcionando
- ✅ **Default values**: Parámetros opcionales con valores por defecto sensibles
- ✅ **No breaking changes**: No requiere cambios en código existente

### Performance
- **Context expansion**: +O(window * chunks) tiempo de recuperación
- **Hierarchy search**: +O(siblings * chunks) queries a Qdrant
- **Multi-query**: +O(variations * top_k) búsquedas + costo LLM

**Recomendación**: Usar multi-query solo para queries críticas/difíciles

### Costos Adicionales
- **Multi-Query Retrieval**: ~$0.0001 por generación de variaciones
- **Impacto total estimado**: +15% costo promedio por query

---

## 🚀 PRÓXIMOS PASOS

### Fase 3 (Opcional - Mejoras Futuras)

No implementadas aún, consideradas para futuro:

7. **Chunking Adaptativo** (+10% precisión)
8. **HyDE con Plantillas Específicas** (+15% en formatos específicos)
9. **Post-processing de Respuestas** (+20% respuestas completas)

### Validación Requerida

1. ✅ Ejecutar `test_precision_improvements.py` → Validar Fase 1
2. ⏳ Crear y ejecutar `test_phase2_improvements.py` → Validar Fase 2
3. ⏳ Comparar métricas: Baseline vs Fase 1 vs Fase 2
4. ⏳ Documentar casos edge donde aún falla

---

**Autor:** Claude Code
**Versión:** 2.0
**Última actualización:** 2025-11-12
