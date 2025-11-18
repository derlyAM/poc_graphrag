"""
Chatbot Conversacional de Inteligencia Artificial.

Interfaz multi-turno para consultas sobre documentos de IA.
Completamente desacoplada del sistema RAG principal.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import warnings
import streamlit as st
from loguru import logger
from src.chatbot.conversational_pipeline import ConversationalPipeline
from src.config import get_documents_for_area
from src.shared_resources import get_shared_pipeline

# Suppress warnings
warnings.filterwarnings("ignore", message=".*ScriptRunContext.*")

# Configure page
st.set_page_config(
    page_title="Chatbot IA",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Configure logging
logger.remove()
logger.add(sys.stderr, level="WARNING")


# Custom CSS (consistent with main app)
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .user-message {
        background-color: #e8f4f8;
        border-left: 3px solid #1f77b4;
    }
    .assistant-message {
        background-color: #f0f2f6;
        border-left: 3px solid #28a745;
    }
    .source-doc {
        background-color: #fff3cd;
        color: #856404;
        padding: 0.5rem;
        border-radius: 0.25rem;
        margin: 0.25rem 0;
        font-size: 0.9rem;
    }
    .source-detail {
        background-color: #f8f9fa;
        color: #212529;
        padding: 0.75rem;
        border-radius: 0.25rem;
        margin: 0.5rem 0;
        border: 1px solid #dee2e6;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def load_chatbot():
    """
    Load and cache the conversational pipeline.

    Uses global singleton RAGPipeline to avoid multiple Qdrant connections.
    """
    with st.spinner("Inicializando chatbot de IA..."):
        # Obtener pipeline compartido global (singleton)
        shared_pipeline = get_shared_pipeline()

        # Crear chatbot reutilizando el pipeline
        chatbot = ConversationalPipeline(
            area="inteligencia_artificial",
            shared_pipeline=shared_pipeline
        )
        return chatbot


def initialize_session_state():
    """Initialize session state variables."""
    if "chatbot_messages" not in st.session_state:
        st.session_state.chatbot_messages = []

    if "chatbot_mode" not in st.session_state:
        st.session_state.chatbot_mode = "long"

    if "chatbot_stats" not in st.session_state:
        st.session_state.chatbot_stats = {
            "total_queries": 0,
            "reformulations": 0
        }


def clear_conversation(chatbot_instance):
    """
    Clear conversation history.

    Args:
        chatbot_instance: ConversationalPipeline instance
    """
    st.session_state.chatbot_messages = []
    st.session_state.chatbot_stats = {
        "total_queries": 0,
        "reformulations": 0
    }
    chatbot_instance.clear_history()
    st.success("Conversación reiniciada")


def render_sources_short(sources: list):
    """Render sources for short mode (simple list)."""
    st.markdown("**📚 Fuentes:**")
    if sources:
        for doc in sources:
            # Usar st.info para mejor compatibilidad con temas
            st.markdown(f":orange[• {doc}]")
    else:
        st.info("Sin fuentes disponibles")


def render_sources_long(sources: list):
    """Render sources for long mode (detailed metadata)."""
    st.markdown("**📚 Fuentes Detalladas:**")

    if not sources:
        st.info("Sin fuentes disponibles")
        return

    for i, source in enumerate(sources, 1):
        if isinstance(source, dict):
            # Usar expander para fuentes detalladas
            with st.expander(f"📄 {i}. {source['documento']}", expanded=False):
                st.markdown(f"**Citación:** `{source['citacion']}`")
                st.markdown(f"**Sección:** {source['seccion']}")
                st.markdown(f"**Relevancia:** {source.get('score', 0):.3f}")
        else:
            st.markdown(f"{i}. {source}")


def main():
    """Main application."""

    # Initialize
    initialize_session_state()

    # Load chatbot (usa pipeline singleton internamente)
    chatbot = load_chatbot()

    # Header
    st.markdown('<p class="main-header">🤖 Chatbot de Inteligencia Artificial</p>',
                unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">Asistente conversacional especializado en documentos de IA</p>',
        unsafe_allow_html=True
    )

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuración")

        # Response mode
        st.subheader("Modo de Respuesta")
        mode = st.radio(
            "Selecciona el tipo de respuesta:",
            options=["long", "short"],
            format_func=lambda x: "📝 Respuesta Larga (con citaciones)" if x == "long"
                                   else "⚡ Respuesta Corta (solo documentos)",
            index=0 if st.session_state.chatbot_mode == "long" else 1,
            key="mode_selector"
        )
        st.session_state.chatbot_mode = mode

        if mode == "short":
            st.info(
                "**Modo Corto:**\n"
                "- 2-3 oraciones concisas\n"
                "- Sin citaciones inline\n"
                "- Lista de documentos usados"
            )
        else:
            st.info(
                "**Modo Largo:**\n"
                "- Respuesta completa y detallada\n"
                "- Citaciones inline [Doc, Sec]\n"
                "- Metadata de fuentes"
            )

        st.divider()

        # Document filter (optional)
        st.subheader("Filtros (Opcional)")

        # Get IA documents using shared pipeline's Qdrant client
        try:
            # Obtener cliente de Qdrant del pipeline compartido
            shared_pipeline = get_shared_pipeline()
            qdrant_client = shared_pipeline.vector_search.qdrant_client

            # Cargar documentos reutilizando la conexión existente
            ia_docs = get_documents_for_area(
                "inteligencia_artificial",
                qdrant_client=qdrant_client
            )

            # La estructura es: {"id": "doc_id", "nombre": "Doc Name", "tipo": "legal"}
            doc_options = {doc["nombre"]: doc["id"] for doc in ia_docs}

            selected_docs = st.multiselect(
                "Filtrar por documentos específicos:",
                options=list(doc_options.keys()),
                default=None,
                help="Deja vacío para buscar en todos los documentos de IA"
            )

            # Convert to IDs
            selected_doc_ids = [doc_options[name] for name in selected_docs] if selected_docs else None

        except Exception as e:
            st.warning(f"No se pudieron cargar documentos: {e}")
            logger.error(f"Error loading IA documents: {e}", exc_info=True)
            selected_doc_ids = None

        st.divider()

        # Advanced settings
        with st.expander("🔧 Configuración Avanzada"):
            enable_multihop = st.checkbox("Multihop Retrieval", value=True)
            enable_hyde = st.checkbox("HyDE", value=True)
            enable_validation = st.checkbox("Validación de Respuesta (Phase 3)", value=True)
            expand_context = st.checkbox("Expandir Contexto", value=True,
                                        help="Incluir chunks adyacentes en la jerarquía")
            top_k_retrieval = st.slider("Top-K Retrieval", min_value=5, max_value=50, value=15,
                                       help="Chunks a recuperar antes de reranking")
            top_k_rerank = st.slider("Top-K Rerank", min_value=3, max_value=20, value=10,
                                    help="Chunks finales después de reranking")

        st.divider()

        # Stats
        st.subheader("📊 Estadísticas")
        st.metric("Consultas", st.session_state.chatbot_stats["total_queries"])
        st.metric("Reformulaciones", st.session_state.chatbot_stats["reformulations"])

        if st.session_state.chatbot_stats["total_queries"] > 0:
            reform_rate = (st.session_state.chatbot_stats["reformulations"] /
                          st.session_state.chatbot_stats["total_queries"] * 100)
            st.metric("Tasa Reformulación", f"{reform_rate:.1f}%")

        st.divider()

        # Clear button
        if st.button("🗑️ Reiniciar Conversación", type="secondary", use_container_width=True):
            clear_conversation(chatbot)
            st.rerun()

    # Main chat area
    st.markdown("---")

    # Display conversation history
    for message in st.session_state.chatbot_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            # Show sources if it's an assistant message
            if message["role"] == "assistant" and "sources" in message:
                st.markdown("---")
                if message.get("mode") == "short":
                    render_sources_short(message["sources"])
                else:
                    render_sources_long(message["sources"])

    # Chat input
    if prompt := st.chat_input("Escribe tu pregunta sobre Inteligencia Artificial..."):

        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Add to history
        st.session_state.chatbot_messages.append({
            "role": "user",
            "content": prompt
        })

        # Get response
        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                try:
                    result = chatbot.query(
                        question=prompt,
                        response_mode=st.session_state.chatbot_mode,
                        documento_ids=selected_doc_ids,
                        top_k_retrieval=top_k_retrieval,
                        top_k_rerank=top_k_rerank,
                        expand_context=expand_context,
                        enable_multihop=enable_multihop,
                        enable_hyde=enable_hyde,
                        enable_validation=enable_validation
                    )

                    # Display answer
                    st.markdown(result["answer"])

                    # Display sources
                    st.markdown("---")
                    if result["mode"] == "short":
                        render_sources_short(result["sources"])
                    else:
                        render_sources_long(result["sources"])

                    # Show if reformulated (in expander)
                    if result["was_reformulated"]:
                        with st.expander("🔄 Query Reformulada"):
                            st.info(
                                f"**Original:** {result['original_question']}\n\n"
                                f"**Reformulada:** {result['reformulated_question']}"
                            )

                    # Add to history
                    st.session_state.chatbot_messages.append({
                        "role": "assistant",
                        "content": result["answer"],
                        "sources": result["sources"],
                        "mode": result["mode"]
                    })

                    # Update stats
                    st.session_state.chatbot_stats["total_queries"] += 1
                    if result["was_reformulated"]:
                        st.session_state.chatbot_stats["reformulations"] += 1

                except Exception as e:
                    st.error(f"Error al procesar la consulta: {str(e)}")
                    logger.error(f"Chatbot error: {e}", exc_info=True)

    # Help section
    with st.expander("❓ Cómo usar el chatbot"):
        st.markdown("""
        ### Características del Chatbot

        **Conversación Multi-turno:**
        - El chatbot recuerda el contexto de la conversación
        - Puedes hacer preguntas de seguimiento
        - Reformula automáticamente preguntas con referencias ("sus", "eso", etc.)

        **Modos de Respuesta:**

        - **Modo Largo (📝):**
          - Respuestas detalladas y completas
          - Citaciones inline en formato [Documento, Sección]
          - Metadata completa de fuentes
          - Ideal para análisis profundo

        - **Modo Corto (⚡):**
          - Respuestas concisas (2-3 oraciones)
          - Sin citaciones en el texto
          - Lista simple de documentos consultados
          - Ideal para respuestas rápidas

        **Ejemplos de Preguntas:**
        - "¿Qué es la inteligencia artificial?"
        - "Explica los principios éticos de la IA"
        - "¿Cuáles son sus aplicaciones?" (referencia al tema anterior)
        - "Compara IA simbólica y conexionista"

        **Anti-alucinación:**
        - El chatbot SOLO usa información de los documentos
        - Si no encuentra información, lo indica claramente
        - No inventa datos ni usa conocimiento externo
        """)


if __name__ == "__main__":
    main()
