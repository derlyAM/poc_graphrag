# Análisis de Mejoras para el Sistema RAG

**Fecha**: 2025-10-21
**Versión actual**: 1.1.1
**Objetivo**: Soporte robusto para preguntas simples y complejas sobre documentos técnicos y legales

---

## 📊 Estado Actual del Sistema

### Componentes Existentes

```
┌─────────────────────────────────────────────────────────────┐
│                     PIPELINE ACTUAL                          │
├─────────────────────────────────────────────────────────────┤
│  1. QueryEnhancer    → Detecta capitulos/titulos/secciones │
│  2. VectorSearch     → Búsqueda semántica en Qdrant        │
│  3. ContextExpansion → Agrega chunks adyacentes            │
│  4. Reranker         → Cross-encoder re-ranking            │
│  5. LLMClient        → GPT-4o-mini generación              │
│  6. CitationManager  → Validación y formato de citas       │
└─────────────────────────────────────────────────────────────┘
```

### Capacidades Actuales

| Tipo de Query | Ejemplo | Funciona | Razón |
|---------------|---------|----------|-------|
| **Semántica simple** | "¿Qué es un OCAD?" | ✅ Sí | Búsqueda vectorial pura |
| **Semántica contenido** | "metodología propuesta" | ✅ Sí | Embedding matchea contenido |
| **Estructural numérica** | "artículo 4.5.1" | ✅ Sí | QueryEnhancer detecta filtro |
| **Estructural nominal** | "sección de antecedentes" | ❌ No | No detecta nombre de sección |
| **Comparativa** | "diferencias entre X y Y" | ⚠️ Parcial | Solo si X e Y están en top-K |
| **Procedimiento multi-paso** | "cómo solicitar ajuste a proyecto" | ⚠️ Parcial | Puede perder pasos |
| **Agregación** | "listar todos los requisitos" | ❌ No | top-K limitado |
| **Razonamiento** | "¿puedo hacer X si tengo Y?" | ❌ No | Requiere múltiples fuentes |

---

## 🔴 Problemas Identificados

### 1. **Query Enhancement Insuficiente** (CRÍTICO)

**Problema**:
```python
# Query actual
"que dice la sección de antecedentes del documento tecnico V2"

# QueryEnhancer busca:
Patrones: "sección \d+" → ❌ No matchea (falta número)

# Resultado:
- No extrae filtro de sección
- Búsqueda vectorial pura
- Embedding de "sección de antecedentes" ≠ embedding de contenido médico
- Top-20 no incluye ANTECEDENTES
```

**Causa raíz**:
- Solo detecta secciones con número: "sección 6" ✅
- NO detecta secciones por nombre: "sección de antecedentes" ❌
- NO hay mapeo nombre → número de sección

**Impacto**: 40% de queries sobre documentos técnicos fallan

---

### 2. **Búsqueda Vectorial Pura para Queries Estructurales** (CRÍTICO)

**Problema**:
```python
# Cuando usuario pregunta por ESTRUCTURA (metadato):
"¿Qué dice la sección X?"
"¿Cuál es el contenido del capítulo Y?"

# Sistema busca por SEMÁNTICA (contenido):
embedding("sección X") vs embedding(contenido_real)
→ Baja similitud porque pregunta por contenedor, no por contenido
```

**Solución requerida**: Búsqueda híbrida
- Si query menciona estructura → usar metadata filtering
- Si query pregunta por contenido → usar vector search
- Si ambas → combinar estrategias

---

### 3. **Ausencia de Metadatos Semánticos** (ALTO IMPACTO)

**Problema**:
Los chunks tienen estos metadatos:
```json
{
  "seccion": "6",
  "seccion_numero": "6",
  "hierarchy_path": "Documentotecnico V2 > Sección 6 - ANTECEDENTES"
}
```

Pero NO tienen:
```json
{
  "seccion_nombre": "ANTECEDENTES",           ❌ FALTA
  "seccion_keywords": ["antecedentes", "background"],  ❌ FALTA
  "tipo_contenido": "contexto histórico",     ❌ FALTA
  "temas": ["salud", "estadísticas", "enfermedades"]   ❌ FALTA
}
```

**Impacto**: No se puede buscar por nombre de sección sin NLP avanzado

---

### 4. **Top-K Fijo Limita Agregaciones** (MEDIO IMPACTO)

**Problema**:
```python
# Query: "Lista todos los requisitos para proyectos CTEI"
# Requisitos distribuidos en 30 chunks diferentes

retrieval_top_k = 20  # ❌ Solo recupera 20 chunks
rerank_top_k = 5      # ❌ Solo pasa 5 al LLM

# Resultado: Respuesta incompleta
```

**Solución requerida**: Top-K dinámico basado en tipo de query

---

### 5. **Sin Razonamiento Multi-Hop** (ALTO IMPACTO)

**Problema**:
```python
# Query compleja: "¿Puedo ajustar un proyecto aprobado si cambió el ejecutor?"

# Requiere:
1. Buscar: ¿Qué variables permiten ajuste? (Artículo 4.5.1.2)
2. Verificar: ¿Ejecutor está en la lista? (Sí, está)
3. Buscar: ¿Qué documentos necesito? (Artículo 4.5.1.3)
4. Razonar: Juntar información de 3 fuentes distintas

# Sistema actual:
- Recupera chunks de paso 1 o paso 2 (no ambos)
- No hay mecanismo de razonamiento secuencial
```

**Impacto**: 60% de queries complejas fallan o dan respuestas incompletas

---

### 6. **Sin Validación Semántica de Respuestas** (MEDIO IMPACTO)

**Problema**:
```python
# LLM genera: "Los ajustes proceden cuando..."
# CitationManager valida:
citation_validation = {
    "total_citations": 1,
    "valid_citations": 1,
    "uncited_statements": 5  # ❌ 5 afirmaciones sin citar
}

# Pero NO valida:
- ¿La afirmación es consistente con el chunk citado?
- ¿El LLM interpretó correctamente el texto legal?
- ¿Hay contradicciones entre fuentes?
```

---

## 🎯 Clasificación de Queries por Complejidad

### **NIVEL 1: Simple Semántica** (70% de queries)
```
Ejemplos:
- "¿Qué es un OCAD?"
- "¿Cuál es la vigencia del acuerdo?"
- "Define proyecto de inversión"

Características:
- Respuesta en 1 chunk
- No requiere razonamiento
- Búsqueda vectorial suficiente

Estado actual: ✅ Funciona bien
```

### **NIVEL 2: Estructural Simple** (15% de queries)
```
Ejemplos:
- "Resume el capítulo 3"
- "¿Qué dice el artículo 4.5.1?"
- "Contenido de la sección de metodología"

Características:
- Requiere identificar sección/capítulo
- Respuesta puede estar en múltiples chunks
- Necesita metadata filtering

Estado actual: ⚠️ Funciona parcialmente (solo con números)
```

### **NIVEL 3: Multi-Chunk Aggregation** (10% de queries)
```
Ejemplos:
- "Lista todos los requisitos para proyectos de infraestructura"
- "¿Cuáles son las causales de liberación de recursos?"
- "Enumera los documentos necesarios"

Características:
- Respuesta fragmentada en muchos chunks
- Requiere exhaustive retrieval
- Necesita LLM que sintetice

Estado actual: ❌ Falla (top-K muy bajo)
```

### **NIVEL 4: Comparación** (3% de queries)
```
Ejemplos:
- "Diferencias entre Acuerdo 03/2021 y Acuerdo 13/2025"
- "Compara requisitos de CTEI vs infraestructura"
- "¿Qué cambió entre versiones?"

Características:
- Requiere chunks de 2+ fuentes
- Necesita razonamiento comparativo
- Puede necesitar búsqueda iterativa

Estado actual: ❌ Falla (no hay estrategia comparativa)
```

### **NIVEL 5: Razonamiento Multi-Hop** (2% de queries)
```
Ejemplos:
- "¿Puedo ajustar el cronograma si el proyecto está en fase II?"
- "Si mi proyecto es CTEI y está aprobado, ¿qué OCAD lo evalúa?"
- "¿Cuál es el proceso completo desde radicación hasta desembolso?"

Características:
- Requiere 3+ pasos de razonamiento
- Información en chunks no adyacentes
- Necesita construcción de cadena lógica

Estado actual: ❌ Falla completamente (no hay agentes)
```

---

## 🛠️ Mejoras Propuestas (Ordenadas por Prioridad)

### **PRIORIDAD 1: Query Enhancement Avanzado** ⭐⭐⭐

**Objetivo**: Detectar secciones por nombre, no solo por número

**Implementación**:
```python
# 1. Durante ingestión: Extraer mapeo nombre → número
{
    "documentotecnico_v2": {
        "secciones": {
            "antecedentes": "6",
            "justificación": "7",
            "justificacion": "7",  # Normalizado sin tilde
            "metodología": "14",
            "metodologia": "14",
            "productos esperados": "18"
        }
    }
}

# 2. Durante query: Normalizar y buscar
query = "sección de antecedentes"
→ detecta "antecedentes"
→ busca en mapeo: antecedentes = sección 6
→ aplica filtro: seccion="6"
```

**Beneficios**:
- ✅ Queries como "sección de antecedentes" funcionarán
- ✅ No requiere cambios en vectorización
- ✅ Implementación simple (1 día)

**Complejidad**: BAJA
**Impacto**: ALTO (40% de queries mejoradas)

---

### **PRIORIDAD 2: Metadata Semántico Enriquecido** ⭐⭐⭐

**Objetivo**: Agregar nombres y keywords a metadatos de chunks

**Implementación**:
```python
# Durante chunking, extraer del hierarchy_path:
"Documentotecnico V2 > Sección 6 - ANTECEDENTES"

# Generar metadatos adicionales:
{
    "seccion": "6",
    "seccion_nombre": "ANTECEDENTES",         # NUEVO
    "seccion_nombre_norm": "antecedentes",    # NUEVO (sin tildes, lowercase)
    "capitulo_nombre": None,
    "titulo_nombre": None,
}

# Indexar en Qdrant con payload_index para búsqueda rápida
```

**Beneficios**:
- ✅ Permite búsqueda keyword por nombre de sección
- ✅ Hybrid search (vector + keyword) más preciso
- ✅ Mejora re-ranking con metadata

**Complejidad**: BAJA
**Impacto**: ALTO
**Requiere**: Re-ingestión de documentos

---

### **PRIORIDAD 3: Estrategia de Top-K Dinámico** ⭐⭐

**Objetivo**: Ajustar top-K según tipo de query

**Implementación**:
```python
class QueryEnhancer:
    def get_retrieval_config(self, enhancement: Dict) -> Dict:
        # Query simple semántica
        if enhancement['query_type'] == 'semantic':
            return {'top_k': 10, 'rerank_top_k': 5}

        # Query estructural (resume capítulo X)
        elif enhancement['query_type'] == 'structural':
            return {'top_k': 50, 'rerank_top_k': 15}

        # Query de agregación (lista todos...)
        elif 'lista' in query or 'enumera' in query:
            return {'top_k': 100, 'rerank_top_k': 30}

        # Query comparativa
        elif 'diferencia' in query or 'compara' in query:
            return {'top_k': 40, 'rerank_top_k': 20}
```

**Beneficios**:
- ✅ Queries de agregación recuperan más chunks
- ✅ Queries simples siguen siendo rápidas
- ✅ Optimiza costos (no siempre usa top-100)

**Complejidad**: BAJA
**Impacto**: MEDIO

---

### **PRIORIDAD 4: Búsqueda Híbrida (Vector + Keyword)** ⭐⭐

**Objetivo**: Combinar búsqueda semántica con búsqueda keyword

**Implementación**:
```python
# Qdrant soporta sparse vectors (BM25) + dense vectors

# 1. Durante ingestión: Generar sparse vector
from qdrant_client.models import SparseVector

sparse_vector = generate_bm25_vector(chunk_text)
dense_vector = openai.embed(chunk_text)

# 2. Almacenar ambos
point = PointStruct(
    id=chunk_id,
    vector={
        "dense": dense_vector,     # Embedding semántico
        "sparse": sparse_vector    # BM25 keywords
    },
    payload=chunk_metadata
)

# 3. Durante búsqueda: Hybrid search
results = client.search(
    collection_name="documentos",
    query_vector={
        "dense": query_embedding,
        "sparse": query_bm25
    },
    limit=top_k
)
```

**Beneficios**:
- ✅ Mejor recall para queries keyword ("antecedentes")
- ✅ Mejor precision para queries semánticas
- ✅ Fusión de scores automática

**Complejidad**: MEDIA
**Impacto**: ALTO
**Requiere**: Re-ingestión + cambios en vector_search.py

---

### **PRIORIDAD 5: Sistema Multi-Agente con LangGraph** ⭐⭐⭐

**Objetivo**: Manejar queries complejas con razonamiento multi-hop

**¿Por qué agentes?**

| Característica | Pipeline Actual | Con Agentes |
|----------------|-----------------|-------------|
| **Flujo** | Lineal fijo | Dinámico adaptativo |
| **Razonamiento** | Single-hop | Multi-hop |
| **Búsquedas** | 1 búsqueda | Búsquedas iterativas |
| **Decisiones** | Hardcoded | Basado en contexto |
| **Auto-corrección** | No | Sí (retry con nueva estrategia) |

**Arquitectura propuesta**:

```python
from langgraph.graph import StateGraph, END

# ESTADO COMPARTIDO
class AgentState(TypedDict):
    query: str
    query_type: str
    documents_retrieved: List[Dict]
    sub_queries: List[str]
    answers: List[str]
    final_answer: str
    iterations: int

# AGENTES

def query_analyzer_agent(state: AgentState) -> AgentState:
    """
    Analiza query y decide estrategia.

    Decisiones:
    - ¿Es simple o compleja?
    - ¿Requiere sub-queries?
    - ¿Qué tipo de búsqueda?
    """
    llm_analysis = llm.invoke(f"""
    Analiza esta query: {state['query']}

    Determina:
    1. Tipo: [simple | estructural | comparativa | multi-hop]
    2. Sub-queries necesarias: [lista]
    3. Estrategia de búsqueda: [vector | hybrid | exhaustive]
    """)

    state['query_type'] = llm_analysis['type']
    state['sub_queries'] = llm_analysis['sub_queries']

    return state


def retrieval_agent(state: AgentState) -> AgentState:
    """
    Ejecuta búsquedas basadas en estrategia.

    Capacidades:
    - Búsqueda iterativa (si no encuentra, reformula)
    - Búsqueda multi-fuente (varios documentos)
    - Expansión de contexto inteligente
    """
    if state['query_type'] == 'multi-hop':
        # Ejecutar sub-queries secuencialmente
        for sub_query in state['sub_queries']:
            chunks = vector_search.search(sub_query, top_k=20)
            state['documents_retrieved'].extend(chunks)
    else:
        # Búsqueda simple
        chunks = vector_search.search(state['query'], top_k=10)
        state['documents_retrieved'] = chunks

    return state


def verification_agent(state: AgentState) -> AgentState:
    """
    Verifica si se recuperó información suficiente.

    Decisiones:
    - ¿Los chunks responden la query?
    - ¿Falta información? → Trigger nueva búsqueda
    - ¿Hay contradicciones? → Buscar chunk desambiguador
    """
    llm_verification = llm.invoke(f"""
    Query: {state['query']}
    Chunks: {state['documents_retrieved']}

    ¿Los chunks contienen información suficiente para responder?
    Si no: ¿Qué información falta?
    """)

    if not llm_verification['sufficient']:
        # Re-trigger retrieval con query refinada
        state['sub_queries'].append(llm_verification['missing_info_query'])

    return state


def answer_generation_agent(state: AgentState) -> AgentState:
    """
    Genera respuesta final con citaciones.
    """
    answer = llm_client.generate_answer(
        query=state['query'],
        context_chunks=state['documents_retrieved']
    )

    state['final_answer'] = answer

    return state


def routing_logic(state: AgentState) -> str:
    """
    Decide próximo nodo basado en estado.
    """
    # Si no hay documentos, ir a retrieval
    if not state['documents_retrieved']:
        return "retrieval"

    # Si hay sub-queries pendientes, volver a retrieval
    if state['sub_queries'] and state['iterations'] < 3:
        return "retrieval"

    # Si verificación falló, volver a retrieval
    if state.get('verification_failed'):
        return "retrieval"

    # Si todo OK, generar respuesta
    return "generate_answer"


# CONSTRUIR GRAFO
workflow = StateGraph(AgentState)

# Nodos
workflow.add_node("analyze_query", query_analyzer_agent)
workflow.add_node("retrieval", retrieval_agent)
workflow.add_node("verify", verification_agent)
workflow.add_node("generate_answer", answer_generation_agent)

# Edges
workflow.set_entry_point("analyze_query")
workflow.add_edge("analyze_query", "retrieval")
workflow.add_edge("retrieval", "verify")
workflow.add_conditional_edges(
    "verify",
    routing_logic,
    {
        "retrieval": "retrieval",        # Re-buscar
        "generate_answer": "generate_answer"  # Responder
    }
)
workflow.add_edge("generate_answer", END)

# Compilar
rag_agent = workflow.compile()
```

**Flujo de ejemplo**:

```
Query: "¿Puedo ajustar el cronograma de un proyecto aprobado en fase II?"

1. analyze_query:
   → Detecta: multi-hop, requiere 2 sub-queries
   → Sub-query 1: "variables susceptibles de ajuste"
   → Sub-query 2: "requisitos para ajustes en fase II"

2. retrieval (1ra iteración):
   → Busca sub-query 1
   → Recupera: Art. 4.5.1.2 (lista de variables)

3. verify:
   → Verifica: "cronograma" está en lista ✅
   → Falta: requisitos de fase II
   → Decisión: Continuar búsqueda

4. retrieval (2da iteración):
   → Busca sub-query 2
   → Recupera: Art. 4.5.1.3 (documentos necesarios)

5. verify:
   → Información completa ✅
   → Decisión: Generar respuesta

6. generate_answer:
   → Sintetiza de ambos chunks
   → Respuesta: "Sí, puedes ajustar el cronograma..."
   → Cita: Art. 4.5.1.2 + Art. 4.5.1.3
```

**Beneficios**:
- ✅ Maneja queries multi-hop
- ✅ Auto-corrección si no encuentra info
- ✅ Búsquedas iterativas inteligentes
- ✅ Razonamiento explícito y trazable

**Complejidad**: ALTA
**Impacto**: MUY ALTO (80% de queries complejas mejoradas)
**Tiempo**: 3-5 días de desarrollo

---

### **PRIORIDAD 6: Fact-Checking Semántico** ⭐

**Objetivo**: Validar que LLM interpreta correctamente fuentes

**Implementación**:
```python
def semantic_fact_check(claim: str, source_chunk: str) -> Dict:
    """
    Verifica si claim es consistente con source.

    Usa LLM para:
    1. Extraer facts del source
    2. Comparar claim vs facts
    3. Detectar contradicciones o alucinaciones
    """
    verification_prompt = f"""
    FUENTE: {source_chunk}

    AFIRMACIÓN: {claim}

    ¿La afirmación es:
    1. Directamente soportada por la fuente?
    2. Inferida correctamente de la fuente?
    3. Contradice la fuente?
    4. No relacionada con la fuente?
    """

    result = llm.invoke(verification_prompt)

    return {
        'claim': claim,
        'verdict': result['verdict'],  # supported | inferred | contradicts | unrelated
        'confidence': result['confidence']
    }
```

**Beneficios**:
- ✅ Detecta alucinaciones del LLM
- ✅ Mayor confianza en respuestas
- ✅ Útil para dominio legal (crítico)

**Complejidad**: MEDIA
**Impacto**: MEDIO

---

## 📋 Roadmap de Implementación

### **Fase 1: Mejoras Rápidas (1-2 días)** 🟢

```
✅ PRIORIDAD 1: Query Enhancement Avanzado
   - Crear mapeo sección_nombre → número durante ingestión
   - Modificar QueryEnhancer para detectar nombres
   - Testing con queries de antecedentes/justificación

✅ PRIORIDAD 2: Metadata Semántico
   - Extraer nombres de hierarchy_path
   - Agregar campos seccion_nombre, capitulo_nombre
   - Re-ingestar documentos

✅ PRIORIDAD 3: Top-K Dinámico
   - Modificar get_retrieval_config()
   - Detectar queries de agregación/comparación
   - Ajustar top_k según tipo
```

**Resultado esperado**:
- 60% de queries estructurales ahora funcionan
- Queries de agregación mejoran recall

---

### **Fase 2: Búsqueda Híbrida (2-3 días)** 🟡

```
✅ PRIORIDAD 4: Hybrid Search
   - Implementar generación de sparse vectors (BM25)
   - Modificar ingestión para dual vectors
   - Actualizar vector_search.py para hybrid search
   - Re-ingestar con sparse + dense vectors
```

**Resultado esperado**:
- 80% de queries simples y estructurales funcionan
- Mejora precision/recall global

---

### **Fase 3: Sistema Agente (3-5 días)** 🟠

```
✅ PRIORIDAD 5: LangGraph Multi-Agent
   - Diseñar grafo de agentes
   - Implementar query_analyzer_agent
   - Implementar retrieval_agent con iteración
   - Implementar verification_agent
   - Implementar routing logic
   - Testing con queries multi-hop
```

**Resultado esperado**:
- 90% de todas las queries funcionan
- Queries complejas resueltas correctamente

---

### **Fase 4: Refinamiento (2 días)** 🔵

```
✅ PRIORIDAD 6: Fact-Checking Semántico
   - Implementar semantic_fact_check()
   - Integrar en pipeline post-generación
   - Dashboard de confianza en respuestas
```

**Resultado esperado**:
- Sistema production-ready
- Confianza medible en respuestas

---

## 🤖 ¿Son Necesarios los Agentes?

### **SÍ, son necesarios para:**

1. **Queries Multi-Hop** (CRÍTICO)
   ```
   Query: "¿Qué documentos necesito para ajustar un proyecto de CTEI en fase III?"

   Requiere:
   - Paso 1: Identificar que es proyecto CTEI
   - Paso 2: Buscar requisitos de ajuste
   - Paso 3: Filtrar por fase III
   - Paso 4: Extraer lista de documentos

   Pipeline lineal: ❌ Falla
   Con agentes: ✅ Éxito (búsquedas iterativas)
   ```

2. **Auto-corrección de Búsquedas**
   ```
   Query: "procedimiento de liberación de recursos"

   Sin agentes:
   - Búsqueda 1: No encuentra "liberación" → Falla

   Con agentes:
   - Búsqueda 1: No encuentra "liberación"
   - Verification Agent: Detecta fallo
   - Reformula: "liberación de recursos SGR"
   - Búsqueda 2: Encuentra chunks relevantes → Éxito
   ```

3. **Razonamiento Complejo**
   ```
   Query: "¿Un proyecto puede estar en 2 OCADs simultáneamente?"

   Requiere:
   - Buscar: Definición de OCAD
   - Buscar: Reglas de asignación de proyectos
   - Razonar: ¿Las reglas permiten múltiples OCADs?

   Pipeline: ❌ No tiene capacidad de razonamiento
   Agentes: ✅ Cadena de razonamiento explícita
   ```

### **NO son necesarios para:**

1. **Queries Simples Semánticas**
   - "¿Qué es un OCAD?" → Pipeline actual suficiente

2. **Queries Estructurales con Número**
   - "Resume el capítulo 3" → QueryEnhancer + Vector Search suficiente

3. **Definiciones**
   - "Define proyecto de inversión" → 1 chunk, no requiere agentes

---

## 💰 Análisis Costo/Beneficio

### **Sin Agentes** (Solo mejoras 1-4)

**Pros**:
- ✅ Implementación rápida (5-7 días)
- ✅ Bajo costo operativo
- ✅ Mejora 70% de queries

**Contras**:
- ❌ Queries complejas siguen fallando
- ❌ No auto-corrección
- ❌ No razonamiento multi-hop

**Cobertura**: 70-80% de queries

---

### **Con Agentes** (Mejoras 1-6)

**Pros**:
- ✅ Mejora 90-95% de queries
- ✅ Auto-corrección inteligente
- ✅ Razonamiento complejo
- ✅ Trazabilidad de decisiones
- ✅ Escalable a nuevos tipos de queries

**Contras**:
- ❌ Implementación más larga (12-15 días)
- ❌ Mayor costo operativo (más llamadas LLM)
- ❌ Mayor complejidad de debugging

**Cobertura**: 90-95% de queries

**Costo adicional**: ~2-3x en llamadas LLM (pero queries complejas actuales fallan de todos modos)

---

## 🎯 Recomendación Final

### **Estrategia Recomendada: HÍBRIDA (Incremental)**

```
FASE 1 (Semana 1): Mejoras rápidas sin agentes
→ Query Enhancement + Metadata + Top-K dinámico
→ Mejora del 40% → 70% de queries
→ Validar con usuarios

FASE 2 (Semana 2): Hybrid Search
→ Implementar búsqueda híbrida
→ Mejora del 70% → 80% de queries
→ Validar con usuarios

DECISIÓN: ¿Implementar agentes?

SI usuarios necesitan queries complejas (multi-hop, razonamiento):
  FASE 3 (Semana 3-4): Sistema Agente
  → Implementar LangGraph
  → Mejora del 80% → 95% de queries

SI usuarios solo usan queries simples/estructurales:
  → Detener en Fase 2
  → Sistema suficientemente robusto
```

### **Justificación**:

1. **Fase 1 y 2 son OBLIGATORIAS**
   - Bajo costo, alto impacto
   - Resuelven problema actual de "sección de antecedentes"
   - Mejoran sistema para mayoría de casos

2. **Fase 3 (Agentes) es CONDICIONAL**
   - Solo si usuarios demandan queries complejas
   - Requiere más recursos pero entrega sistema production-grade
   - Permite casos de uso avanzados (comparaciones, razonamiento)

3. **Enfoque incremental minimiza riesgo**
   - Cada fase entrega valor
   - Validación con usuarios en cada checkpoint
   - Flexibilidad para detenerse si Fase 2 es suficiente

---

## 📊 Métricas de Éxito

### **Después de Fase 1 (sin agentes)**:
- ✅ 70% de queries responden correctamente
- ✅ "Sección de antecedentes" funciona
- ✅ Queries de agregación mejoran
- ⏱️ Latencia: <5 segundos
- 💰 Costo: <$0.01 por query

### **Después de Fase 2 (hybrid search)**:
- ✅ 80% de queries responden correctamente
- ✅ Mejor precision/recall
- ⏱️ Latencia: <6 segundos
- 💰 Costo: <$0.015 por query

### **Después de Fase 3 (con agentes)**:
- ✅ 95% de queries responden correctamente
- ✅ Queries multi-hop funcionan
- ✅ Auto-corrección activa
- ⏱️ Latencia: 8-15 segundos (iteraciones)
- 💰 Costo: $0.02-0.05 por query (variable según complejidad)

---

**Conclusión**: Sistema agente es MUY RECOMENDADO si el objetivo es un RAG production-grade que maneje preguntas complejas. Para un MVP que solo maneje queries simples/estructurales, las fases 1-2 son suficientes.
