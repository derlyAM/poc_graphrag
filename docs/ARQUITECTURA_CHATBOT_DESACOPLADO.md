# Arquitectura: Chatbot Desacoplado del RAG

**Fecha**: 2025-11-13
**Objetivo**: Chatbot independiente que reutiliza componentes RAG sin acoplar código

---

## 🎯 Principios de Diseño

### 1. **Separación Total de Responsabilidades**
- **RAG Query System**: Sistema actual sin modificar (consultas one-shot)
- **Chatbot System**: Sistema conversacional nuevo (multi-turno)
- **Shared Components**: Componentes reutilizables sin dependencias cruzadas

### 2. **Composición sobre Herencia**
```python
# ❌ MAL - Herencia crea acoplamiento
class ConversationalPipeline(Pipeline):
    pass

# ✅ BIEN - Composición mantiene independencia
class ConversationalPipeline:
    def __init__(self):
        self._base_pipeline = Pipeline()  # Contiene, no hereda
```

### 3. **No Modificar Archivos Existentes**
- Todo el código del chatbot en `src/chatbot/` (carpeta nueva)
- Cero cambios en `src/pipeline.py`, `src/retrieval/`, `src/generation/`
- Solo agregar nueva página en `app/pages/`

---

## 📂 Estructura de Carpetas (Separación Clara)

```
Poc_Rag_Graph/
│
├── src/
│   ├── config.py                    # ✅ COMPARTIDO (sin modificar)
│   ├── pipeline.py                  # ✅ COMPARTIDO (sin modificar)
│   │
│   ├── retrieval/                   # ✅ COMPARTIDO (sin modificar)
│   │   ├── vector_search.py
│   │   ├── hyde_retriever.py
│   │   ├── multihop_retriever.py
│   │   └── ...
│   │
│   ├── generation/                  # ✅ COMPARTIDO (sin modificar)
│   │   └── llm_client.py
│   │
│   └── chatbot/                     # ⭐ NUEVO - TODO EL CÓDIGO DEL CHATBOT
│       ├── __init__.py
│       ├── conversational_pipeline.py   # Pipeline del chatbot
│       ├── conversation_manager.py      # Gestión de historial
│       ├── query_reformulator.py        # Reformulación contextual
│       ├── response_formatter.py        # Formateo corto/largo
│       └── prompts.py                   # Prompts específicos del chatbot
│
├── app/
│   ├── streamlit_app.py             # ✅ RAG Query (SIN MODIFICAR)
│   │
│   └── pages/                       # Streamlit multi-page
│       └── 2_🤖_Chatbot_IA.py      # ⭐ NUEVO - Página del chatbot
│
└── docs/
    └── ARQUITECTURA_CHATBOT_DESACOPLADO.md  # Este documento
```

### Reglas de la Estructura

| Carpeta | Propósito | Modificable |
|---------|-----------|-------------|
| `src/config.py` | Configuración compartida | ❌ NO |
| `src/pipeline.py` | Pipeline RAG base | ❌ NO |
| `src/retrieval/*` | Componentes de retrieval | ❌ NO |
| `src/generation/*` | Generación LLM | ❌ NO |
| **`src/chatbot/*`** | **Todo el código del chatbot** | ✅ **SÍ** |
| `app/streamlit_app.py` | Página RAG Query | ❌ NO |
| **`app/pages/*`** | **Páginas adicionales** | ✅ **SÍ** |

---

## 🏗️ Arquitectura de Componentes

### Vista General

```
┌─────────────────────────────────────────────────────────────────┐
│                        STREAMLIT APP                             │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────┐  ┌──────────────────────┐            │
│  │  RAG Query           │  │  Chatbot IA          │            │
│  │  (streamlit_app.py)  │  │  (pages/2_*.py)      │            │
│  │                      │  │                      │            │
│  │  - One-shot queries  │  │  - Multi-turn chat   │            │
│  │  - All areas         │  │  - IA area only      │            │
│  │  - Document filters  │  │  - Response modes    │            │
│  └──────────┬───────────┘  └──────────┬───────────┘            │
│             │                         │                         │
│             ↓                         ↓                         │
│  ┌──────────────────────┐  ┌──────────────────────┐            │
│  │  Pipeline            │  │  ConversationalPipe  │            │
│  │  (src/pipeline.py)   │  │  (chatbot/conv_*.py) │            │
│  │                      │  │                      │            │
│  │  ✅ Sin modificar    │  │  ⭐ Nuevo            │            │
│  └──────────┬───────────┘  └──────────┬───────────┘            │
│             │                         │                         │
│             │          ┌──────────────┘                         │
│             │          │                                        │
│             ↓          ↓                                        │
│  ┌─────────────────────────────────────────────────┐           │
│  │         SHARED COMPONENTS (Reutilizables)        │           │
│  │  ✅ Sin modificar ninguno                        │           │
│  ├─────────────────────────────────────────────────┤           │
│  │  - VectorSearch                                  │           │
│  │  - HyDERetriever                                 │           │
│  │  - MultihopRetriever                             │           │
│  │  - LLMClient                                     │           │
│  │  - CitationManager                               │           │
│  │  - ResponseValidator                             │           │
│  └─────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔌 Interfaces de Integración

### Interface 1: Streamlit Multi-Page

**Separación automática por páginas**

```python
# app/streamlit_app.py (PÁGINA PRINCIPAL - SIN MODIFICAR)
import streamlit as st
from src.pipeline import Pipeline

st.set_page_config(
    page_title="RAG System",
    page_icon="📚",
    layout="wide"
)

# ... código actual sin cambios ...
```

```python
# app/pages/2_🤖_Chatbot_IA.py (NUEVA PÁGINA)
import streamlit as st
from src.chatbot.conversational_pipeline import ConversationalPipeline

st.set_page_config(
    page_title="Chatbot IA",
    page_icon="🤖"
)

# ... código del chatbot (completamente separado) ...
```

**Beneficio**: Streamlit automáticamente crea navegación en sidebar

```
Sidebar automático:
├── 📚 Rag System          ← streamlit_app.py
└── 🤖 Chatbot Ia          ← pages/2_*.py
```

**Estado independiente**: Cada página tiene su propio `st.session_state`

---

### Interface 2: ConversationalPipeline → Pipeline

**Composición limpia sin acoplamiento**

```python
# src/chatbot/conversational_pipeline.py

from src.pipeline import Pipeline  # ✅ Import del pipeline base
from src.chatbot.conversation_manager import ConversationHistory
from src.chatbot.query_reformulator import QueryReformulator
from src.chatbot.response_formatter import ResponseFormatter


class ConversationalPipeline:
    """
    Pipeline del chatbot que ENVUELVE (no hereda) Pipeline base.

    Principio: Composición sobre herencia.
    """

    def __init__(self, area: str = "inteligencia_artificial"):
        """
        Inicializa pipeline conversacional.

        IMPORTANTE: Crea instancia PRIVADA del pipeline base.
        No modifica el pipeline base, solo lo usa.
        """
        # Componente compartido (composición)
        self._base_pipeline = Pipeline()  # ✅ Instancia privada

        # Componentes exclusivos del chatbot
        self._conversation_history = ConversationHistory()
        self._query_reformulator = QueryReformulator()
        self._response_formatter = ResponseFormatter()

        # Configuración del chatbot
        self.area = area  # Área fija para chatbot

    def query(
        self,
        question: str,
        response_mode: str = "long",
        documento_ids: Optional[List[str]] = None
    ) -> Dict:
        """
        Procesa query conversacional.

        FLUJO:
        1. Reformula query con historial (chatbot-specific)
        2. Llama a pipeline base (reutilización)
        3. Formatea respuesta según modo (chatbot-specific)
        4. Actualiza historial (chatbot-specific)
        """
        # STEP 1: Reformulación (chatbot-specific)
        history = self._conversation_history.get_last_n_messages(5)

        if history:
            reformulated_query = self._query_reformulator.reformulate(
                current_query=question,
                history=history
            )
        else:
            reformulated_query = question

        # STEP 2: RAG Pipeline (reutilización sin modificar)
        rag_result = self._base_pipeline.query(
            question=reformulated_query,
            area=self.area,  # Área fija
            documento_ids=documento_ids,
            top_k_retrieval=10 if response_mode == "short" else 20,
            enable_multihop=response_mode == "long",
            enable_hyde=True,
            enable_validation=response_mode == "long"
        )

        # STEP 3: Formateo (chatbot-specific)
        formatted = self._response_formatter.format(
            answer=rag_result["answer"],
            chunks=rag_result["chunks"],
            mode=response_mode
        )

        # STEP 4: Historial (chatbot-specific)
        self._conversation_history.add_message("user", question)
        self._conversation_history.add_message("assistant", formatted["answer"])

        return {
            "answer": formatted["answer"],
            "sources": formatted["sources"],
            "reformulated_query": reformulated_query,
            "cost": rag_result["total_cost"]
        }

    def clear_history(self):
        """Limpia historial (método exclusivo del chatbot)."""
        self._conversation_history.clear()
```

**Ventajas de esta arquitectura**:
- ✅ Pipeline base **no se modifica**
- ✅ Chatbot **reutiliza** toda la funcionalidad RAG
- ✅ Cambios en Pipeline **automáticamente** benefician al chatbot
- ✅ Chatbot puede **sobrescribir** parámetros (top_k, multihop, etc.)
- ✅ Fácil de **testear** independientemente

---

### Interface 3: Componentes Compartidos

**Reutilización sin dependencias**

Todos estos componentes son **stateless** o tienen **estado interno independiente**:

```python
# ✅ COMPARTIDOS - Usados por ambos sistemas sin conflicto

VectorSearch
├── Stateless: Recibe query, devuelve chunks
└── Sin estado compartido entre llamadas

HyDERetriever
├── Estado interno: Contadores (hyde_used_count, etc.)
└── Sin conflicto: Cada sistema puede tener su instancia

MultihopRetriever
├── Stateless: Procesa sub-queries y devuelve chunks
└── Sin estado compartido

LLMClient
├── Estado interno: total_cost (acumulador)
└── Sin conflicto: Cada sistema suma independientemente

CitationManager
├── Stateless: Valida y formatea citaciones
└── Sin estado compartido

ResponseValidator
├── Estado interno: Contadores (total_validations, etc.)
└── Sin conflicto: Cada sistema puede tener su instancia
```

**Regla de oro**: Ningún componente compartido guarda referencias cruzadas entre RAG y Chatbot

---

## 🔒 Garantías de No-Acoplamiento

### Checklist de Verificación

#### ✅ Separación de Código
- [ ] Todo código del chatbot en `src/chatbot/`
- [ ] Cero imports de chatbot en archivos existentes
- [ ] Cero modificaciones en `src/pipeline.py`
- [ ] Cero modificaciones en `src/retrieval/*`
- [ ] Cero modificaciones en `src/generation/*`

#### ✅ Separación de Estado
- [ ] RAG usa `st.session_state` de página principal
- [ ] Chatbot usa `st.session_state` de página 2
- [ ] No hay variables compartidas en session_state
- [ ] Historial del chatbot NO afecta queries RAG

#### ✅ Separación de Configuración
- [ ] RAG permite seleccionar cualquier área
- [ ] Chatbot fija área = "inteligencia_artificial"
- [ ] RAG permite enable/disable features
- [ ] Chatbot decide sus propios parámetros

#### ✅ Testeo Independiente
- [ ] Tests de RAG corren sin chatbot
- [ ] Tests de chatbot corren sin modificar RAG
- [ ] CI/CD puede deployar RAG sin chatbot (y viceversa)

---

## 📦 Instalación y Dependencias

**Sin nuevas dependencias!** Todo reutiliza lo existente:

```python
# requirements.txt - SIN CAMBIOS

# Todas estas dependencias YA existen:
streamlit>=1.30.0           # Multi-page support
openai>=1.0.0               # LLM para reformulación
qdrant-client>=1.7.0        # Vector search
sentence-transformers       # Reranking
```

**Única "dependencia" nueva**: Organización de código

---

## 🚀 Flujo de Implementación (Sin Romper Nada)

### Fase 1: Estructura Base (30 min)

```bash
# 1. Crear carpeta del chatbot
mkdir -p src/chatbot
touch src/chatbot/__init__.py

# 2. Crear página Streamlit
mkdir -p app/pages
touch "app/pages/2_🤖_Chatbot_IA.py"

# 3. Verificar que RAG sigue funcionando
streamlit run app/streamlit_app.py
# ✅ Todo funciona igual
```

### Fase 2: Componentes Base (2 horas)

```bash
# 1. ConversationManager (stateful, independiente)
touch src/chatbot/conversation_manager.py

# 2. ResponseFormatter (stateless, sin dependencias)
touch src/chatbot/response_formatter.py

# 3. Prompts del chatbot (constantes)
touch src/chatbot/prompts.py
```

**Test**: Cada componente se testea aisladamente

### Fase 3: Pipeline Conversacional (1.5 horas)

```bash
# ConversationalPipeline (composición de Pipeline)
touch src/chatbot/conversational_pipeline.py
```

**Test**: Verifica que Pipeline base NO fue modificado

### Fase 4: Query Reformulator (1.5 horas)

```bash
# Reformulador contextual (usa LLM)
touch src/chatbot/query_reformulator.py
```

**Test**: Reformulación sin afectar queries RAG

### Fase 5: Interfaz Streamlit (1 hora)

```bash
# Implementar página del chatbot
# Editar: app/pages/2_🤖_Chatbot_IA.py
```

**Test**: Navegación entre páginas sin interferencia

---

## 🧪 Testing de No-Regresión

### Test 1: RAG No Afectado

```python
# tests/test_no_regression.py

def test_rag_pipeline_unchanged():
    """Verifica que Pipeline RAG sigue funcionando igual."""
    from src.pipeline import Pipeline

    pipeline = Pipeline()
    result = pipeline.query(
        question="¿Qué es un OCAD?",
        area="sgr"
    )

    assert "answer" in result
    assert "chunks" in result
    # Pipeline NO debe tener atributos del chatbot
    assert not hasattr(pipeline, 'conversation_history')
    assert not hasattr(pipeline, 'query_reformulator')


def test_streamlit_rag_page_works():
    """Verifica que página RAG sigue funcionando."""
    # Simular ejecución de streamlit_app.py
    # Verificar que NO importa nada de chatbot

    with open("app/streamlit_app.py") as f:
        content = f.read()
        assert "chatbot" not in content.lower()
```

### Test 2: Chatbot Independiente

```python
def test_chatbot_pipeline_isolated():
    """Verifica que chatbot funciona independientemente."""
    from src.chatbot.conversational_pipeline import ConversationalPipeline

    chatbot = ConversationalPipeline()
    result = chatbot.query(
        question="¿Qué es la IA?",
        response_mode="short"
    )

    assert "answer" in result
    # Chatbot tiene métodos exclusivos
    assert hasattr(chatbot, 'clear_history')
    assert hasattr(chatbot, '_conversation_history')
```

### Test 3: No Interferencia de Estado

```python
def test_no_state_interference():
    """Verifica que RAG y Chatbot no comparten estado."""
    from src.pipeline import Pipeline
    from src.chatbot.conversational_pipeline import ConversationalPipeline

    # Usar RAG
    rag = Pipeline()
    rag.query("Pregunta RAG", area="sgr")

    # Usar Chatbot
    chatbot = ConversationalPipeline()
    chatbot.query("Pregunta Chatbot")

    # Verificar independencia
    # Los contadores/estados NO deben interferir
    assert rag.llm_client.total_cost != chatbot._base_pipeline.llm_client.total_cost
```

---

## 📊 Comparación: RAG vs Chatbot

| Aspecto | RAG Query System | Chatbot IA System |
|---------|------------------|-------------------|
| **Ubicación** | `app/streamlit_app.py` | `app/pages/2_*.py` |
| **Código fuente** | `src/pipeline.py` | `src/chatbot/conversational_pipeline.py` |
| **Estado** | Stateless (cada query independiente) | Stateful (historial conversacional) |
| **Áreas** | Todas (sgr, IA, general) | Solo IA (fijo) |
| **Modos** | Uno (respuesta completa con citas) | Dos (corto/largo) |
| **Queries** | One-shot | Multi-turn (contexto) |
| **Modificable** | ❌ NO (sistema estable) | ✅ SÍ (sistema experimental) |
| **Dependencies** | Ninguna externa | Usa Pipeline internamente |
| **Testing** | Tests existentes | Tests nuevos independientes |

---

## 💡 Ventajas de esta Arquitectura

### 1. **Cero Riesgo para RAG Existente**
- RAG sigue funcionando exactamente igual
- Todos los tests existentes pasan
- Producción no se afecta

### 2. **Máxima Reutilización**
- Chatbot aprovecha TODA la funcionalidad RAG
- HyDE Mejorado, Multihop, Validación, etc.
- Mejoras futuras en Pipeline benefician ambos

### 3. **Desarrollo Independiente**
- Chatbot se puede iterar rápidamente
- Experimentar sin miedo a romper RAG
- Rollback fácil (solo borrar `src/chatbot/`)

### 4. **Mantenibilidad**
- Separación clara de responsabilidades
- Fácil entender qué hace cada sistema
- Debugging aislado

### 5. **Escalabilidad**
- Agregar más páginas (Chatbot Legal, Chatbot Técnico)
- Cada una reutiliza Pipeline
- Sin duplicar código

---

## 🎯 Ejemplo de Uso Dual

### Usuario 1: Usa RAG Query

```python
# app/streamlit_app.py
# Usuario hace query one-shot sobre SGR

Pipeline().query(
    question="¿Qué es un OCAD?",
    area="sgr",
    documento_id="acuerdo_03_2021"
)

# ✅ Funciona exactamente como antes
```

### Usuario 2: Usa Chatbot IA

```python
# app/pages/2_*.py
# Usuario tiene conversación sobre IA

chatbot = ConversationalPipeline(area="inteligencia_artificial")

# Turno 1
chatbot.query("¿Qué es la IA?", response_mode="short")
# Historial: [User: "¿Qué es IA?", Bot: "..."]

# Turno 2
chatbot.query("¿Cuáles son sus aplicaciones?", response_mode="long")
# Reformula: "¿Cuáles son las aplicaciones de la IA?"
# Historial actualizado

# ✅ Funcionalidad completamente nueva, sin afectar RAG
```

---

## ✅ Checklist Final de Desacoplamiento

Antes de empezar implementación, verificar:

- [ ] **Carpetas separadas**: `src/chatbot/` creada
- [ ] **Sin modificar RAG**: Ningún archivo en `src/` modificado (excepto agregar carpeta)
- [ ] **Composición, no herencia**: ConversationalPipeline CONTIENE Pipeline
- [ ] **Estado independiente**: session_state separado por página
- [ ] **Tests independientes**: Pueden correr sin dependencias cruzadas
- [ ] **Rollback fácil**: Borrar `src/chatbot/` y `app/pages/2_*.py` = vuelta a RAG puro
- [ ] **Documentación clara**: Este documento explica la separación

---

## 🚀 ¿Listo para Implementar?

Con esta arquitectura garantizamos:

1. ✅ **RAG intacto**: Cero cambios en código existente
2. ✅ **Reutilización total**: Chatbot usa todos los componentes RAG
3. ✅ **Independencia**: Cada sistema tiene su ciclo de vida
4. ✅ **Escalabilidad**: Fácil agregar más funcionalidades

**Siguiente paso**: Implementar siguiendo este diseño, garantizando que cada commit NO rompe RAG.

---

**Autor**: Claude Code
**Fecha**: 2025-11-13
**Versión**: 1.0
