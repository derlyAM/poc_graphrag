# Análisis: Implementación de Chatbot IA Conversacional

**Fecha**: 2025-11-13
**Objetivo**: Chatbot interactivo sobre Inteligencia Artificial con modos de respuesta (corto/largo)

---

## 📋 Requerimientos del Usuario

### Funcionalidad Esperada

1. **Área fija**: Solo documentos del área "inteligencia_artificial"
2. **Conversacional**: Interacción multi-turno (historial de mensajes)
3. **Anti-alucinación**: Respuestas estrictamente basadas en documentos del RAG
4. **Dos modos de respuesta**:
   - **Modo Corto**:
     - Respuestas concisas (2-3 oraciones)
     - Lista de documentos fuente (sin citas detalladas)
   - **Modo Largo**:
     - Respuestas detalladas
     - Citaciones inline específicas [Art. X, Documento]

---

## ✅ Lo que YA Existe (Componentes Reutilizables)

### 1. Pipeline RAG Completo
```python
# src/pipeline.py
- ✅ QueryEnhancer: Detección de intención
- ✅ QueryDecomposer: Multihop para preguntas complejas
- ✅ HyDERetriever: HyDE Mejorado con templates especializados
- ✅ MultihopRetriever: Búsquedas iterativas
- ✅ VectorSearch: Búsqueda vectorial + BM25 híbrida
- ✅ Reranker: Cross-encoder para re-ranking
- ✅ LLMClient: Generación de respuestas
- ✅ CitationManager: Sistema de citaciones legales
- ✅ ResponseValidator: Validación de completitud (Fase 3)
```

### 2. Documentos de IA Procesados
```
✅ data_topic_IA/:
   - CONPES Colombia - Política nacional de inteligencia artificial.pdf
   - IEEE - Estándar global de ética en sistemas autónomos.pdf
   - La Inteligencia Artificial y su uso en el sector público.pdf
   - INTELIGENCIA ARTIFICIAL - historia, evolución y aplicaciones.pdf
   - European Union Artificial Intelligence Act.pdf
   - UNESCO – La inteligencia artificial ¿Necesitamos una nueva educación?.pdf
   - Introducción a la IA Generativa Ametic.pdf
   - Guía sobre IA para estudiantes 2025.pdf
   - Facultad de IA Universidad de Caldas.pdf
```

### 3. Interfaz Streamlit Existente
```python
# app/streamlit_app.py
- ✅ Selector de área
- ✅ Filtro de documentos
- ✅ Input de pregunta
- ✅ Display de respuesta + fuentes
- ✅ Métricas de costos/tiempo
```

---

## ❌ Lo que FALTA Implementar

### 1. **Gestión de Historial Conversacional** (CRÍTICO)

**Problema actual**: El pipeline es stateless - cada query es independiente

**Ejemplos de limitaciones**:
```
Usuario: "¿Qué es la inteligencia artificial?"
Bot: [Respuesta con definición de IA]

Usuario: "¿Cuáles son sus aplicaciones?"  ❌ NO FUNCIONA
# El sistema no sabe que "sus" se refiere a "inteligencia artificial"
```

**Solución requerida**:
```python
class ConversationHistory:
    """
    Gestiona el historial de mensajes usuario-bot.
    """
    def __init__(self):
        self.messages = []  # Lista de {role: user/assistant, content: str}

    def add_message(self, role: str, content: str):
        """Agrega mensaje al historial."""

    def get_last_n_messages(self, n: int = 5):
        """Obtiene últimos N mensajes."""

    def clear(self):
        """Limpia el historial."""
```

**Archivos a crear**:
- `src/chatbot/conversation_manager.py`

---

### 2. **Reformulación Contextual de Queries** (CRÍTICO)

**Problema**: Queries con referencias ("eso", "lo anterior", "sus aplicaciones") no funcionan

**Solución**: Query Reformulation con LLM

```python
class QueryReformulator:
    """
    Reformula queries usando contexto conversacional.

    Convierte queries dependientes del contexto en queries standalone.
    """

    def reformulate_with_context(
        self,
        current_query: str,
        conversation_history: List[Dict]
    ) -> str:
        """
        Reformula query usando historial.

        Ejemplo:
            History:
                User: "¿Qué es la IA?"
                Bot: "La IA es..."
            Current: "¿Cuáles son sus aplicaciones?"
            Output: "¿Cuáles son las aplicaciones de la inteligencia artificial?"
        """
```

**Prompt de reformulación**:
```python
REFORMULATION_PROMPT = """Dada la siguiente conversación, reformula la última pregunta
del usuario para que sea independiente del contexto (standalone).

Conversación previa:
{conversation_history}

Pregunta actual del usuario:
{current_query}

Reformula la pregunta para que pueda entenderse sin el contexto anterior.
Si ya es standalone, devuélvela tal cual.

Pregunta reformulada:"""
```

**Archivos a crear**:
- `src/chatbot/query_reformulator.py`

---

### 3. **Modos de Respuesta (Corto vs Largo)** (NUEVO)

**Diferencias entre modos**:

| Aspecto | Modo Corto | Modo Largo |
|---------|-----------|------------|
| **Longitud** | 2-3 oraciones (50-100 tokens) | Completa (200-500 tokens) |
| **Citaciones** | NO inline | Inline completas [Art. X, Doc] |
| **Fuentes** | Lista al final (solo nombres) | Integradas en texto |
| **Temperatura** | 0.0 (más determinística) | 0.1 (actual) |
| **Max tokens** | 150 | 600 (actual) |

**Implementación**:

```python
class ResponseFormatter:
    """
    Formatea respuestas según el modo seleccionado.
    """

    def format_short_response(
        self,
        answer: str,
        chunks: List[Dict]
    ) -> Dict:
        """
        Modo Corto:
        - Extrae solo los primeros 2-3 párrafos
        - Remueve citaciones inline
        - Agrega lista de documentos únicos al final

        Returns:
            {
                "formatted_answer": str,
                "source_documents": List[str]  # Solo nombres
            }
        """

    def format_long_response(
        self,
        answer: str,
        chunks: List[Dict]
    ) -> Dict:
        """
        Modo Largo:
        - Mantiene respuesta completa
        - Mantiene citaciones inline
        - Agrega referencias detalladas

        Returns:
            {
                "formatted_answer": str,
                "detailed_sources": List[Dict]  # Con metadatos
            }
        """
```

**System prompts diferenciados**:

```python
# Modo Corto
SHORT_MODE_SYSTEM_PROMPT = """Eres un asistente experto en Inteligencia Artificial.

IMPORTANTE - MODO RESPUESTA CORTA:
1. Responde en MÁXIMO 2-3 oraciones concisas
2. NO incluyas citaciones en el texto (ej: [Art. X, Doc])
3. Ve directo al punto, sin introducciones largas
4. Si no hay información, di "No encontré información sobre esto"
5. Usa ÚNICAMENTE el contexto proporcionado

Contexto: {context}

Pregunta: {question}"""

# Modo Largo
LONG_MODE_SYSTEM_PROMPT = """Eres un asistente experto en Inteligencia Artificial.

IMPORTANTE - MODO RESPUESTA DETALLADA:
1. Proporciona una respuesta completa y bien estructurada
2. TODA afirmación DEBE incluir citación: [Documento, Sección/Página]
3. Organiza en secciones si aplica
4. Explica conceptos con detalle
5. Usa ÚNICAMENTE el contexto proporcionado

Contexto: {context}

Pregunta: {question}"""
```

**Archivos a modificar**:
- `src/generation/llm_client.py` → Agregar `generate_answer_short()` y `generate_answer_long()`
- `src/chatbot/response_formatter.py` → NUEVO

---

### 4. **Reforzamiento Anti-Alucinación** (MEJORAR)

**Estrategias adicionales**:

#### A. Temperatura más baja
```python
# Modo Corto: temperatura = 0.0 (determinística)
# Modo Largo: temperatura = 0.05 (más baja que actual 0.1)
```

#### B. Prompt más estricto
```python
ANTI_HALLUCINATION_RULES = """
REGLAS ESTRICTAS - NO ALUCINAR:
1. Si el contexto NO contiene la información, di explícitamente:
   "No encontré información sobre [tema] en los documentos disponibles."
2. NUNCA uses conocimiento externo o general
3. NUNCA asumas o extrapoles más allá del contexto
4. Si el contexto es ambiguo, indica la ambigüedad
5. NO inventes datos, fechas, nombres o cifras
"""
```

#### C. Validación post-generación (ya existe)
```python
# ResponseValidator (Fase 3) - ya implementado
# - Valida completitud
# - Detecta respuestas vagas
# - Auto-retry si incompleto
```

#### D. Chunking con evidencia
```python
def build_context_with_evidence(chunks: List[Dict]) -> str:
    """
    Construye contexto marcando claramente qué es evidencia real.
    """
    context = "=== EVIDENCIA DISPONIBLE ===\n\n"

    for i, chunk in enumerate(chunks):
        context += f"[EVIDENCIA {i+1}]\n"
        context += f"Documento: {chunk['documento_nombre']}\n"
        context += f"Sección: {chunk.get('seccion_nombre', 'N/A')}\n"
        context += f"Contenido:\n{chunk['texto']}\n\n"

    context += "=== FIN DE EVIDENCIA ===\n"
    context += "IMPORTANTE: Solo usa la EVIDENCIA anterior. No agregues información externa.\n"

    return context
```

**Archivos a modificar**:
- `src/generation/llm_client.py` → Agregar prompts anti-alucinación
- `src/chatbot/anti_hallucination.py` → NUEVO (validadores adicionales)

---

### 5. **Interfaz de Chatbot en Streamlit** (NUEVO)

**Diseño propuesto**:

```python
# app/pages/2_Chatbot_IA.py (NUEVO ARCHIVO)

import streamlit as st
from src.chatbot.conversational_pipeline import ConversationalPipeline

st.set_page_config(page_title="Chatbot IA", page_icon="🤖")

# Título
st.title("🤖 Chatbot de Inteligencia Artificial")
st.caption("Pregúntame sobre IA - respuestas basadas en documentos académicos")

# Configuración en sidebar
with st.sidebar:
    st.header("⚙️ Configuración")

    # Modo de respuesta
    response_mode = st.radio(
        "Modo de respuesta",
        ["Corto", "Largo"],
        help="Corto: conciso + lista docs. Largo: detallado + citas"
    )

    # Filtro de documentos (opcional)
    available_docs = get_ia_documents()
    selected_docs = st.multiselect(
        "Filtrar documentos (opcional)",
        options=[doc['nombre'] for doc in available_docs],
        help="Vacío = todos los documentos de IA"
    )

    # Botón limpiar chat
    if st.button("🗑️ Limpiar conversación"):
        st.session_state.messages = []
        st.session_state.conversation_history.clear()
        st.rerun()

# Inicializar pipeline y historial
if "chatbot_pipeline" not in st.session_state:
    st.session_state.chatbot_pipeline = ConversationalPipeline(area="inteligencia_artificial")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        # Mostrar fuentes si es mensaje del asistente
        if message["role"] == "assistant" and "sources" in message:
            with st.expander("📚 Fuentes"):
                for source in message["sources"]:
                    st.write(f"- {source}")

# Chat input
if prompt := st.chat_input("Pregúntame sobre Inteligencia Artificial..."):
    # Agregar mensaje del usuario
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    # Generar respuesta
    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            # Usar pipeline conversacional
            result = st.session_state.chatbot_pipeline.query(
                question=prompt,
                response_mode=response_mode.lower(),
                documento_ids=selected_doc_ids if selected_docs else None
            )

            # Mostrar respuesta
            st.markdown(result["answer"])

            # Mostrar fuentes
            with st.expander("📚 Fuentes"):
                for source in result["sources"]:
                    st.write(f"- {source}")

            # Agregar a historial
            st.session_state.messages.append({
                "role": "assistant",
                "content": result["answer"],
                "sources": result["sources"]
            })
```

**Archivos a crear**:
- `app/pages/2_Chatbot_IA.py`

**Beneficios de Streamlit Pages**:
- Navegación automática en sidebar
- Estado independiente por página
- Mejor organización

---

### 6. **Pipeline Conversacional** (NUEVO - COMPONENTE PRINCIPAL)

```python
# src/chatbot/conversational_pipeline.py

from typing import List, Dict, Optional
from loguru import logger

from src.pipeline import Pipeline
from src.chatbot.conversation_manager import ConversationHistory
from src.chatbot.query_reformulator import QueryReformulator
from src.chatbot.response_formatter import ResponseFormatter


class ConversationalPipeline:
    """
    Pipeline especializado para chatbot conversacional.

    Extiende Pipeline base con:
    - Gestión de historial
    - Reformulación contextual de queries
    - Formateo según modo (corto/largo)
    """

    def __init__(self, area: str = "inteligencia_artificial"):
        """
        Inicializa pipeline conversacional.

        Args:
            area: Área fija (por defecto IA)
        """
        self.area = area
        self.base_pipeline = Pipeline()
        self.conversation_history = ConversationHistory()
        self.query_reformulator = QueryReformulator()
        self.response_formatter = ResponseFormatter()

        logger.info(f"ConversationalPipeline initialized for area: {area}")

    def query(
        self,
        question: str,
        response_mode: str = "long",  # "short" or "long"
        documento_ids: Optional[List[str]] = None,
        max_history: int = 5
    ) -> Dict:
        """
        Procesa query conversacional.

        Steps:
        1. Reformula query con contexto del historial
        2. Ejecuta RAG pipeline base
        3. Formatea respuesta según modo
        4. Actualiza historial

        Args:
            question: Pregunta del usuario
            response_mode: "short" o "long"
            documento_ids: Filtro de documentos (opcional)
            max_history: Número de mensajes previos a considerar

        Returns:
            {
                "answer": str,
                "sources": List[str],  # Nombres de documentos
                "reformulated_query": str,
                "chunks_used": int,
                "cost": float,
                "response_mode": str
            }
        """
        logger.info(f"Processing conversational query (mode: {response_mode})")

        # STEP 1: Reformular query con contexto
        history = self.conversation_history.get_last_n_messages(max_history)

        if history:
            reformulated_query = self.query_reformulator.reformulate_with_context(
                current_query=question,
                conversation_history=history
            )
            logger.info(f"Query reformulated: '{question}' → '{reformulated_query}'")
        else:
            reformulated_query = question

        # STEP 2: Ejecutar RAG pipeline
        # Configurar según modo
        if response_mode == "short":
            # Modo corto: menos chunks, temperatura más baja
            rag_result = self.base_pipeline.query(
                question=reformulated_query,
                area=self.area,
                documento_ids=documento_ids,
                top_k_retrieval=10,  # Menos chunks
                enable_reranking=True,
                enable_multihop=False,  # Respuestas cortas no necesitan multihop
                enable_hyde=True,
                enable_validation=False  # Validación solo en modo largo
            )
        else:  # long
            # Modo largo: más chunks, validación activa
            rag_result = self.base_pipeline.query(
                question=reformulated_query,
                area=self.area,
                documento_ids=documento_ids,
                top_k_retrieval=20,
                enable_reranking=True,
                enable_multihop=True,
                enable_hyde=True,
                enable_validation=True  # Validación de completitud
            )

        # STEP 3: Formatear respuesta según modo
        if response_mode == "short":
            formatted = self.response_formatter.format_short_response(
                answer=rag_result["answer"],
                chunks=rag_result["chunks"]
            )
        else:
            formatted = self.response_formatter.format_long_response(
                answer=rag_result["answer"],
                chunks=rag_result["chunks"]
            )

        # STEP 4: Actualizar historial
        self.conversation_history.add_message("user", question)
        self.conversation_history.add_message("assistant", formatted["formatted_answer"])

        # Return result
        return {
            "answer": formatted["formatted_answer"],
            "sources": formatted.get("source_documents", formatted.get("detailed_sources", [])),
            "reformulated_query": reformulated_query,
            "chunks_used": len(rag_result["chunks"]),
            "cost": rag_result["total_cost"],
            "response_mode": response_mode,
            "original_query": question
        }

    def clear_history(self):
        """Limpia el historial de conversación."""
        self.conversation_history.clear()
        logger.info("Conversation history cleared")

    def get_history(self) -> List[Dict]:
        """Obtiene el historial completo."""
        return self.conversation_history.messages
```

**Archivos a crear**:
- `src/chatbot/conversational_pipeline.py`

---

## 📁 Estructura de Archivos a Crear/Modificar

### Nuevos Archivos

```
src/chatbot/
├── __init__.py
├── conversational_pipeline.py     # Pipeline principal del chatbot
├── conversation_manager.py        # Gestión de historial
├── query_reformulator.py          # Reformulación contextual
├── response_formatter.py          # Formateo corto/largo
└── anti_hallucination.py          # Validadores anti-alucinación

app/pages/
└── 2_Chatbot_IA.py                # Interfaz Streamlit del chatbot

tests/
└── test_chatbot.py                # Tests del chatbot
```

### Archivos a Modificar

```
src/generation/llm_client.py
  ↳ Agregar: generate_answer_short(), generate_answer_long()
  ↳ Agregar: system prompts diferenciados

src/pipeline.py
  ↳ Modificar: Agregar parámetro response_mode (opcional, para compatibilidad)

app/streamlit_app.py
  ↳ Modificar: Agregar link/botón a página de chatbot
```

---

## 🔄 Flujo de Interacción

```
┌─────────────────────────────────────────────────────────────────┐
│  USUARIO: "¿Qué es la inteligencia artificial?"                 │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│  ConversationalPipeline                                          │
│  1. Historial vacío → Query no cambia                           │
│  2. RAG Pipeline: Retrieval + Generation                        │
│  3. Formato según modo (corto/largo)                            │
│  4. Guarda en historial: user + assistant                       │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│  RESPUESTA (Modo Corto):                                         │
│  "La IA es la capacidad de máquinas para realizar tareas que    │
│  normalmente requieren inteligencia humana, como aprendizaje    │
│  y toma de decisiones."                                          │
│                                                                  │
│  📚 Fuentes:                                                     │
│  - CONPES Colombia - Política nacional de IA                    │
│  - Introducción a la IA Generativa Ametic                       │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│  USUARIO: "¿Cuáles son sus aplicaciones en el sector público?" │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│  ConversationalPipeline                                          │
│  1. Historial: [Q: "¿Qué es IA?", A: "La IA es..."]            │
│  2. QueryReformulator:                                           │
│     "sus aplicaciones" → "aplicaciones de la inteligencia       │
│      artificial en el sector público"                           │
│  3. RAG Pipeline con query reformulada                          │
│  4. Formato según modo                                           │
│  5. Guarda en historial                                          │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
                    [Respuesta...]
```

---

## 💰 Estimación de Costos

### Por Conversación (estimado)

| Componente | Tokens | Costo |
|------------|--------|-------|
| Query Reformulation (si aplica) | 200-300 | $0.00003 |
| RAG Pipeline (retrieval + generation) | 2000-3000 | $0.00045 |
| Validación (solo modo largo) | 300-400 | $0.00006 |
| **Total por turno** | **2500-3700** | **~$0.00054** |

**Conversación típica (5 turnos)**: ~$0.0027 (menos de 1 centavo)

**1000 conversaciones/mes**: ~$2.70

---

## ⏱️ Estimación de Esfuerzo

| Tarea | Complejidad | Tiempo Estimado |
|-------|-------------|-----------------|
| 1. ConversationHistory | Baja | 30 min |
| 2. QueryReformulator | Media | 1.5 horas |
| 3. ResponseFormatter | Baja | 1 hora |
| 4. Prompts anti-alucinación | Media | 1 hora |
| 5. ConversationalPipeline | Alta | 2 horas |
| 6. Interfaz Streamlit Chatbot | Media | 1.5 horas |
| 7. Tests y debugging | Media | 2 horas |
| **TOTAL** | - | **9-10 horas** |

---

## 🎯 Prioridades de Implementación

### Fase 1 (MVP - 4 horas)
1. ✅ ConversationHistory básico
2. ✅ ConversationalPipeline sin reformulación
3. ✅ Interfaz Streamlit básica
4. ✅ Modo largo (reusar pipeline actual)

**Resultado**: Chatbot funcional con historial básico, solo modo largo

### Fase 2 (Modos - 3 horas)
5. ✅ ResponseFormatter (corto/largo)
6. ✅ Prompts diferenciados
7. ✅ Selector de modo en UI

**Resultado**: Chatbot con modos corto/largo

### Fase 3 (Contextual - 3 horas)
8. ✅ QueryReformulator
9. ✅ Integración en ConversationalPipeline
10. ✅ Tests de reformulación

**Resultado**: Chatbot completamente conversacional

---

## 🧪 Plan de Testing

### Tests Unitarios

```python
# tests/test_chatbot.py

def test_conversation_history():
    """Test que historial se almacena correctamente."""

def test_query_reformulation():
    """Test reformulación con contexto."""
    # Input: "¿Cuáles son sus aplicaciones?"
    # History: [User: "¿Qué es IA?", Bot: "..."]
    # Expected: "¿Cuáles son las aplicaciones de la IA?"

def test_short_mode():
    """Test modo corto: máx 3 oraciones, sin citas inline."""

def test_long_mode():
    """Test modo largo: citas inline presentes."""

def test_anti_hallucination():
    """Test que no alucina cuando no hay contexto."""
    # Query sobre tema no en documentos
    # Expected: "No encontré información sobre..."
```

### Tests de Integración

```python
def test_full_conversation():
    """Test conversación completa multi-turno."""
    # Turno 1: Pregunta sobre definición
    # Turno 2: Pregunta con referencia ("sus aplicaciones")
    # Turno 3: Pregunta de seguimiento
    # Validar: reformulación correcta, respuestas coherentes
```

---

## 🚀 Cómo Empezar

### Orden de Implementación Sugerido

**Día 1: Base conversacional** (4 horas)
1. Crear `src/chatbot/conversation_manager.py`
2. Crear `src/chatbot/conversational_pipeline.py` (versión simple)
3. Crear `app/pages/2_Chatbot_IA.py` (interfaz básica)
4. Testing: Chatbot funcional sin reformulación

**Día 2: Modos de respuesta** (3 horas)
5. Crear `src/chatbot/response_formatter.py`
6. Modificar `src/generation/llm_client.py` (prompts)
7. Integrar en ConversationalPipeline
8. Testing: Modos corto/largo funcionan

**Día 3: Contextual** (3 horas)
9. Crear `src/chatbot/query_reformulator.py`
10. Integrar en ConversationalPipeline
11. Testing completo
12. Documentación

---

## 📝 Notas Adicionales

### Consideraciones de UX

1. **Indicador de pensamiento**: Mostrar "Pensando..." mientras procesa
2. **Streaming (opcional)**: Respuestas palabra por palabra (requiere SSE)
3. **Botón de retry**: Si respuesta no satisface, regenerar
4. **Exportar conversación**: Botón para descargar chat como TXT/MD
5. **Sugerencias de preguntas**: Mostrar 3-4 preguntas frecuentes

### Mejoras Futuras (No prioritarias)

- **Memoria a largo plazo**: Guardar conversaciones en base de datos
- **Personalización**: Tono de respuestas (formal/informal)
- **Multi-idioma**: Soporte para inglés
- **Feedback**: Thumbs up/down en respuestas
- **Analytics**: Dashboard de preguntas frecuentes

---

## ✅ Checklist de Implementación

- [ ] 1. ConversationHistory creado
- [ ] 2. QueryReformulator creado
- [ ] 3. ResponseFormatter creado
- [ ] 4. Prompts anti-alucinación agregados
- [ ] 5. ConversationalPipeline creado
- [ ] 6. Interfaz Streamlit creada
- [ ] 7. Tests unitarios pasando
- [ ] 8. Tests de integración pasando
- [ ] 9. Documentación actualizada
- [ ] 10. README con instrucciones de uso

---

**Fecha de análisis**: 2025-11-13
**Autor**: Claude Code
**Versión**: 1.0
