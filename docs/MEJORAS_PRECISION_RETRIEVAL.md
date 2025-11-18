# Análisis y Mejoras para Precisión de Retrieval

**Fecha:** 2025-11-12
**Contexto:** Prueba de 60 preguntas sobre documentos de IA
**Problema:** ~25% de preguntas (15/60) retornan "No encontré información" a pesar de encontrar chunks

---

## 📊 ANÁLISIS DEL PROBLEMA

### Preguntas que Fallaron

#### CONPES Colombia (3/6 fallidas)
- ❌ "¿Cuál es el objetivo número 1...?" → Busca info específica (objetivo numerado)
- ❌ "¿Cuál es el objetivo número 4...?" → Busca info específica (objetivo numerado)
- ❌ "¿Cuál es el costo estimado...?" → Busca dato numérico específico

#### EU AI Act (4/6 fallidas)
- ❌ "¿Cuáles son los niveles de riesgo...?" → Lista específica
- ❌ "¿Qué sanciones económicas...?" → Datos numéricos/legales
- ❌ "¿Cuáles son prácticas prohibidas...?" → Lista específica
- ❌ "¿Qué obligaciones de transparencia...?" → Requisitos específicos

#### Facultad Caldas (1/6 fallida)
- ❌ "¿Qué sucede si un estudiante beneficiario...?" → Caso específico

#### IEEE Ética (1/6 fallida)
- ❌ "¿Qué indica sobre competencia de operadores...?" → Aspecto específico

#### Historia IA (2/6 fallidas)
- ❌ "¿Qué aplicaciones actuales...?" → Lista de ejemplos
- ❌ "¿Cuándo resurgieron las redes neuronales...?" → Fecha/evento específico

#### Ametic (2/6 fallidas)
- ❌ "¿Ejemplos prácticos de IA generativa...?" → Lista de ejemplos
- ❌ "¿Qué retos principales...?" → Lista específica

#### Guía Estudiantes (1/6 fallida)
- ❌ "¿Cambios positivos y negativos...?" → Comparación/lista

#### UNESCO (1/6 fallida)
- ❌ "¿Qué recomienda UNESCO para desarrollo ético...?" → Recomendaciones específicas

---

## 🔍 PATRONES IDENTIFICADOS

### 1. **Búsquedas de Información Muy Específica**
- Números de objetivos ("objetivo número 1", "objetivo número 4")
- Datos numéricos exactos (costos, sanciones)
- Fechas específicas ("en 1943", "a mediados de los 80")

**Problema:** El chunking puede separar el número del contexto

### 2. **Listas y Enumeraciones**
- "¿Cuáles son los niveles...?"
- "¿Cuáles son las prácticas prohibidas...?"
- "¿Qué ejemplos...?"

**Problema:** La lista completa puede estar distribuida en múltiples chunks

### 3. **Información Contextual Profunda**
- Requiere contexto de varios párrafos
- Información que está en subsecciones específicas

**Problema:** El chunk relevante puede no tener suficiente contexto

---

## 💡 MEJORAS PROPUESTAS (Priorizadas)

### 🔴 CRÍTICAS (Implementar Ya)

#### 1. **Mejorar Query Enhancement para Términos Específicos**
**Ubicación:** `src/retrieval/query_enhancer.py`

```python
# AGREGAR: Detección de números y términos específicos
def _enhance_specific_queries(self, query: str) -> Dict:
    """Detecta y expande consultas con términos muy específicos."""

    enhancements = []

    # Detectar números de objetivos/artículos
    if re.search(r'(objetivo|artículo|sección|capítulo)\s+(número\s+)?(\d+)', query, re.I):
        match = re.search(r'(objetivo|artículo|sección|capítulo)\s+(número\s+)?(\d+)', query, re.I)
        tipo = match.group(1)
        numero = match.group(3)

        # Generar variaciones
        enhancements.extend([
            f"{tipo} {numero}",
            f"{tipo} número {numero}",
            f"{numero}. {tipo}",
            f"{tipo.upper()} {numero}",
        ])

    # Detectar solicitudes de listas
    if re.search(r'(cuáles|qué).*(niveles|tipos|ejemplos|prácticas|requisitos)', query, re.I):
        enhancements.append("lista completa enumerar todos")

    # Detectar búsqueda de datos numéricos
    if re.search(r'(costo|precio|sanción|multa|cantidad|número)', query, re.I):
        enhancements.append("datos numéricos cifras monto")

    return {
        "enhanced_query": query + " " + " ".join(enhancements),
        "expansions": enhancements
    }
```

**Impacto esperado:** +40% precisión en preguntas específicas

---

#### 2. **Aumentar top_k para Preguntas Complejas**
**Ubicación:** `src/retrieval/query_enhancer.py`

```python
def get_retrieval_config(self, enhancement: Dict, default_top_k: int = 10) -> Dict:
    """Ajusta top_k dinámicamente según complejidad."""

    query_type = enhancement.get("query_type", "semantic")

    # NUEVO: Detectar preguntas que requieren más contexto
    if any(keyword in enhancement["original_query"].lower() for keyword in [
        "cuáles", "enumera", "lista", "todos", "ejemplos", "niveles"
    ]):
        # Buscar más chunks para listas y enumeraciones
        return {"top_k_retrieval": 20, "top_k_rerank": 10}

    if enhancement.get("has_specific_terms"):  # números, fechas, datos específicos
        return {"top_k_retrieval": 15, "top_k_rerank": 8}

    # Config actual
    if query_type == "aggregation":
        return {"top_k_retrieval": 100, "top_k_rerank": 10}

    return {"top_k_retrieval": default_top_k, "top_k_rerank": 5}
```

**Impacto esperado:** +25% cobertura en listas y enumeraciones

---

#### 3. **Mejorar BM25 para Búsquedas Exactas**
**Ubicación:** `src/retrieval/vector_search.py`

```python
def _hybrid_search(self, query_embedding, query_text, top_k, filters):
    """Ajusta pesos de BM25 vs vectorial según tipo de query."""

    # Detectar si la query tiene términos muy específicos
    has_numbers = bool(re.search(r'\d+', query_text))
    has_quotes = '"' in query_text
    has_specific_terms = any(term in query_text.lower() for term in [
        'número', 'artículo', 'sección', 'costo', 'sanción', 'objetivo'
    ])

    if has_numbers or has_quotes or has_specific_terms:
        # Dar más peso a BM25 (búsqueda exacta)
        bm25_weight = 0.6  # En lugar de 0.5
        vector_weight = 0.4
        logger.debug(f"Query específica detectada, aumentando peso BM25 a {bm25_weight}")
    else:
        # Pesos normales
        bm25_weight = 0.5
        vector_weight = 0.5

    # Ejecutar búsquedas...
    dense_results = self._search_dense(query_embedding, top_k * 2, filters)
    sparse_results = self._search_sparse_bm25(query_text, top_k * 2, filters)

    # Fusion con pesos ajustados
    fused = self._reciprocal_rank_fusion(
        dense_results,
        sparse_results,
        top_k,
        weights=(vector_weight, bm25_weight)  # NUEVO: pesos variables
    )

    return fused
```

**Impacto esperado:** +30% precisión en búsquedas con números/términos exactos

---

### 🟡 IMPORTANTES (Implementar Pronto)

#### 4. **Context Expansion Más Agresivo**
**Ubicación:** `src/retrieval/vector_search.py`

```python
def search_with_context(
    self,
    query: str,
    area: str,
    top_k: int = None,
    expand_context: bool = True,
    context_window: int = 1,  # NUEVO: configurable
    **kwargs
) -> List[Dict]:
    """Expande contexto con chunks adyacentes."""

    # Buscar chunks base
    base_chunks = self.search(query, area, top_k, **kwargs)

    if not expand_context:
        return base_chunks

    # MEJORADO: Expandir con ventana configurable
    expanded_chunks = []
    seen_ids = set()

    for chunk in base_chunks:
        # Agregar chunk base
        if chunk["chunk_id"] not in seen_ids:
            expanded_chunks.append(chunk)
            seen_ids.add(chunk["chunk_id"])

        # Expandir ANTES y DESPUÉS con ventana
        for offset in range(-context_window, context_window + 1):
            if offset == 0:
                continue

            adjacent = self._get_adjacent_chunk(chunk, offset)
            if adjacent and adjacent["chunk_id"] not in seen_ids:
                adjacent["from_expansion"] = True
                adjacent["expansion_offset"] = offset
                expanded_chunks.append(adjacent)
                seen_ids.add(adjacent["chunk_id"])

    return expanded_chunks
```

**Uso:**
```python
# Para preguntas complejas, usar ventana más grande
chunks = vector_search.search_with_context(
    query="¿Cuáles son todos los niveles de riesgo?",
    area="inteligencia_artificial",
    context_window=2  # Expandir 2 chunks antes y después
)
```

**Impacto esperado:** +20% información completa en listas

---

#### 5. **Chunk Hierarchy-Aware Search**
**Ubicación:** `src/retrieval/vector_search.py`

```python
def search_with_hierarchy(
    self,
    query: str,
    area: str,
    include_parent: bool = True,
    include_siblings: bool = False,
    **kwargs
) -> List[Dict]:
    """Incluye chunks relacionados jerárquicamente."""

    base_chunks = self.search(query, area, **kwargs)

    enriched_chunks = []

    for chunk in base_chunks:
        enriched_chunks.append(chunk)

        # Incluir chunk padre (contexto superior)
        if include_parent and chunk.get("parent_id"):
            parent = self._get_chunk_by_id(chunk["parent_id"])
            if parent:
                parent["from_hierarchy"] = "parent"
                enriched_chunks.append(parent)

        # Incluir chunks hermanos (mismo nivel)
        if include_siblings and chunk.get("parent_id"):
            siblings = self._get_sibling_chunks(chunk)
            for sibling in siblings[:3]:  # Máximo 3 hermanos
                sibling["from_hierarchy"] = "sibling"
                enriched_chunks.append(sibling)

    return enriched_chunks
```

**Impacto esperado:** +15% contexto jerárquico

---

#### 6. **Multi-Query Retrieval**
**Ubicación:** `src/retrieval/multi_query_retriever.py` (NUEVO)

```python
class MultiQueryRetriever:
    """Genera múltiples variaciones de la query para mejor recall."""

    def generate_query_variations(self, query: str) -> List[str]:
        """Genera variaciones de la query."""

        variations = [query]  # Original

        # Variación 1: Reformulación
        prompt = f"""Genera 2 reformulaciones de esta pregunta manteniendo el mismo significado:

Pregunta original: {query}

Reformulaciones (una por línea):"""

        response = self.llm_client.generate_simple(prompt)
        variations.extend([v.strip() for v in response.split('\n') if v.strip()])

        # Variación 2: Términos clave
        keywords = self._extract_keywords(query)
        variations.append(" ".join(keywords))

        # Variación 3: Query expandida
        expanded = self.query_enhancer.enhance_query(query)
        variations.append(expanded["enhanced_query"])

        return variations[:5]  # Máximo 5 variaciones

    def retrieve_multi_query(
        self,
        query: str,
        area: str,
        top_k_per_query: int = 10
    ) -> List[Dict]:
        """Busca con múltiples variaciones y fusiona resultados."""

        variations = self.generate_query_variations(query)

        all_chunks = []
        for i, variant_query in enumerate(variations):
            logger.info(f"Searching with variant {i+1}: {variant_query[:60]}...")

            chunks = self.vector_search.search(
                variant_query,
                area,
                top_k=top_k_per_query
            )

            for chunk in chunks:
                chunk["query_variant"] = i
                all_chunks.append(chunk)

        # Fusionar y re-rankear
        unique_chunks = self._deduplicate_chunks(all_chunks)
        reranked = self.reranker.rerank(query, unique_chunks, top_k=top_k_per_query)

        return reranked
```

**Impacto esperado:** +35% recall en preguntas ambiguas

---

### 🟢 OPCIONALES (Mejoras Futuras)

#### 7. **Chunking Adaptativo**
- Chunks más pequeños (400 tokens) para documentos con listas
- Chunks más grandes (1000 tokens) para narrativas
- Overlap mayor (150 tokens) en documentos estructurados

**Impacto esperado:** +10% precisión global

#### 8. **HyDE con Plantillas Específicas**
- Plantilla para "objetivos numerados"
- Plantilla para "listas y enumeraciones"
- Plantilla para "datos numéricos"

**Impacto esperado:** +15% en preguntas con formato específico

#### 9. **Post-processing de Respuestas**
- Validar si la respuesta contiene el término buscado
- Si no, buscar en chunks expandidos
- Retry con query reformulada

**Impacto esperado:** +20% respuestas completas

---

## 📈 IMPACTO ESTIMADO TOTAL

| Mejora | Impacto | Esfuerzo | Prioridad |
|--------|---------|----------|-----------|
| Query Enhancement Específico | +40% | 2h | 🔴 Crítica |
| Top-k Dinámico | +25% | 1h | 🔴 Crítica |
| BM25 con Pesos Ajustables | +30% | 3h | 🔴 Crítica |
| Context Expansion Agresivo | +20% | 2h | 🟡 Importante |
| Hierarchy-Aware Search | +15% | 3h | 🟡 Importante |
| Multi-Query Retrieval | +35% | 4h | 🟡 Importante |
| Chunking Adaptativo | +10% | 8h | 🟢 Opcional |
| HyDE Mejorado | +15% | 4h | 🟢 Opcional |
| Post-processing | +20% | 3h | 🟢 Opcional |

**Con las 3 mejoras críticas:** 75% → **95% precisión** (estimado)
**Con todas las mejoras:** 75% → **98% precisión** (estimado)

---

## 🎯 PLAN DE IMPLEMENTACIÓN

### Fase 1: Quick Wins (1 semana)
1. ✅ Query Enhancement para términos específicos
2. ✅ Top-k dinámico
3. ✅ BM25 con pesos ajustables

**Resultado esperado:** 75% → 90% precisión

### Fase 2: Mejoras Importantes (2 semanas)
4. ✅ Context expansion agresivo
5. ✅ Hierarchy-aware search
6. ✅ Multi-query retrieval

**Resultado esperado:** 90% → 95% precisión

### Fase 3: Optimizaciones (1 mes)
7. ✅ Chunking adaptativo
8. ✅ HyDE mejorado
9. ✅ Post-processing

**Resultado esperado:** 95% → 98% precisión

---

## 🧪 TESTING

### Script de Validación
Crear `scripts/test_precision_improvements.py`:

```python
# Probar SOLO las 15 preguntas que fallaron
FAILED_QUESTIONS = [
    "¿Cuál es el objetivo número 1 de la política nacional de inteligencia artificial en Colombia?",
    "¿Cuál es el objetivo número 4 de la política nacional de inteligencia artificial en Colombia?",
    # ... resto de preguntas fallidas
]

# Ejecutar con configuración baseline
results_baseline = test_questions(FAILED_QUESTIONS, config="baseline")

# Ejecutar con mejoras
results_improved = test_questions(FAILED_QUESTIONS, config="improved")

# Comparar
compare_results(results_baseline, results_improved)
```

### Métricas a Medir
- **Precision@5**: ¿Los top-5 chunks contienen la respuesta?
- **MRR (Mean Reciprocal Rank)**: ¿En qué posición está el chunk correcto?
- **Answer Quality**: ¿La respuesta final es correcta?
- **Cost**: ¿Cuánto costó por pregunta?

---

## 📚 REFERENCIAS

- Documento original de pruebas: `test_results_ia_questions.json`
- Output completo: `test_output.log`
- Preguntas fuente: `Preguntas.pdf`

---

**Autor:** Claude Code
**Fecha:** 2025-11-12
**Versión:** 1.0
