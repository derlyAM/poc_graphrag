"""
Streamlit UI for RAG Document Q&A System.
Professional interface for querying legal documents.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from loguru import logger
from src.pipeline import RAGPipeline
from src.config import config

# Configure page
st.set_page_config(
    page_title="RAG Document Q&A",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Configure logging
logger.remove()
logger.add(sys.stderr, level="WARNING")  # Only show warnings in Streamlit


# Custom CSS
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
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .citation {
        background-color: #e8f4f8;
        padding: 0.5rem;
        border-left: 3px solid #1f77b4;
        margin: 0.5rem 0;
        border-radius: 0.25rem;
    }
    .source-chunk {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border: 1px solid #dee2e6;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def load_pipeline():
    """Load and cache the RAG pipeline."""
    with st.spinner("Inicializando sistema RAG..."):
        pipeline = RAGPipeline()
        return pipeline


def render_sidebar():
    """Render sidebar with configuration."""
    with st.sidebar:
        st.markdown("## ⚙️ Configuración")

        # Document filter
        st.markdown("### Filtros")
        documento_filter = st.selectbox(
            "Filtrar por documento",
            ["Todos", "Acuerdo Único 2025", "Documento Técnico V2"],
            help="Selecciona un documento específico o busca en todos"
        )

        # Map selection to documento_id
        documento_map = {
            "Todos": None,
            "Acuerdo Único 2025": "acuerdo_unico_comision_rectora_2025_07_15",
            "Documento Técnico V2": "documentotecnico_v2"
        }
        documento_id = documento_map[documento_filter]

        st.markdown("---")

        # Advanced settings
        with st.expander("⚙️ Configuración Avanzada"):
            top_k_retrieval = st.slider(
                "Chunks a recuperar",
                min_value=5,
                max_value=50,
                value=config.retrieval.top_k_retrieval,
                help="Número de chunks iniciales de búsqueda vectorial"
            )

            top_k_rerank = st.slider(
                "Chunks finales (re-ranking)",
                min_value=3,
                max_value=10,
                value=config.retrieval.top_k_rerank,
                help="Número de chunks después del re-ranking"
            )

            expand_context = st.checkbox(
                "Expandir contexto",
                value=True,
                help="Incluir chunks adyacentes para más contexto"
            )

        st.markdown("---")

        # System info
        st.markdown("### 📊 Sistema")
        pipeline = st.session_state.get("pipeline")
        if pipeline:
            stats = pipeline.get_stats()
            collection_stats = stats["collection"]

            st.metric(
                "Documentos Indexados",
                collection_stats.get("points_count", 0)
            )
            st.metric(
                "Modelo LLM",
                stats["model"].replace("gpt-", "GPT-")
            )

            if "total_cost" in st.session_state:
                st.metric(
                    "Costo Total Sesión",
                    f"${st.session_state.total_cost:.6f}"
                )

        st.markdown("---")

        # Example queries
        st.markdown("### 💡 Ejemplos")
        st.markdown("""
        - ¿Qué es un OCAD?
        - ¿Cuáles son los requisitos para viabilizar un proyecto?
        - Explica el proceso de ajuste de proyectos
        - ¿Qué es el Sistema General de Regalías?
        """)

        return {
            "documento_id": documento_id,
            "top_k_retrieval": top_k_retrieval,
            "top_k_rerank": top_k_rerank,
            "expand_context": expand_context,
        }


def render_answer(result):
    """Render the answer section."""
    st.markdown("## 💬 Respuesta")

    # Answer text
    answer = result.get("answer", "")
    st.markdown(answer)

    # Citation report in expander
    if result.get("citation_report"):
        with st.expander("📋 Reporte de Citaciones"):
            st.markdown(result["citation_report"])


def render_sources(sources):
    """Render source chunks."""
    st.markdown("## 📚 Fuentes Consultadas")

    for i, chunk in enumerate(sources, 1):
        with st.expander(
            f"Fuente {i}: {chunk.get('citacion_corta', 'N/A')} "
            f"(Score: {chunk.get('rerank_score', chunk.get('score', 0)):.3f})"
        ):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(f"**Documento:** {chunk.get('documento_nombre', 'N/A')}")
                st.markdown(f"**Artículo:** {chunk.get('articulo', 'N/A')}")
                st.markdown(f"**Tipo:** {chunk.get('tipo_contenido', 'N/A').title()}")

            with col2:
                st.markdown(f"**Tokens:** {chunk.get('longitud_tokens', 0)}")
                if chunk.get('rerank_score'):
                    st.markdown(f"**Score Vectorial:** {chunk.get('original_score', 0):.3f}")
                    st.markdown(f"**Score Re-rank:** {chunk.get('rerank_score', 0):.3f}")

            st.markdown("---")
            st.markdown("**Contenido:**")
            text = chunk.get('texto', '')
            # Show first 500 chars with option to see more
            if len(text) > 500:
                st.text(text[:500] + "...")
                if st.button(f"Ver completo", key=f"show_full_{i}"):
                    st.text(text)
            else:
                st.text(text)


def render_metrics(metrics):
    """Render performance metrics."""
    st.markdown("## ⏱️ Métricas de Performance")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Tiempo Total",
            f"{metrics.get('total_time', 0):.2f}s"
        )

    with col2:
        st.metric(
            "Búsqueda",
            f"{metrics.get('search_time', 0):.2f}s"
        )

    with col3:
        st.metric(
            "Generación",
            f"{metrics.get('generation_time', 0):.2f}s"
        )

    with col4:
        st.metric(
            "Costo",
            f"${metrics.get('llm_cost', 0):.6f}"
        )

    # Detailed metrics in expander
    with st.expander("📊 Métricas Detalladas"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Retrieval:**")
            st.write(f"- Chunks recuperados: {metrics.get('chunks_retrieved', 0)}")
            st.write(f"- Chunks finales: {metrics.get('chunks_reranked', 0)}")
            st.write(f"- Tiempo re-ranking: {metrics.get('rerank_time', 0):.2f}s")

        with col2:
            st.markdown("**Generación:**")
            st.write(f"- Tokens entrada: {metrics.get('input_tokens', 0):,}")
            st.write(f"- Tokens salida: {metrics.get('output_tokens', 0):,}")
            st.write(f"- Costo: ${metrics.get('llm_cost', 0):.6f}")


def main():
    """Main Streamlit app."""

    # Header
    st.markdown('<p class="main-header">📚 Sistema RAG para Documentos Normativos</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">Consulta inteligente de documentos del Sistema General de Regalías con citación legal precisa</p>',
        unsafe_allow_html=True
    )

    # Initialize pipeline
    if "pipeline" not in st.session_state:
        st.session_state.pipeline = load_pipeline()
        st.session_state.total_cost = 0.0
        st.success("✅ Sistema inicializado correctamente")

    pipeline = st.session_state.pipeline

    # Sidebar
    config_params = render_sidebar()

    # Main content
    st.markdown("---")

    # Query input
    st.markdown("## 🔍 Consulta")

    col1, col2 = st.columns([4, 1])

    with col1:
        query = st.text_input(
            "Escribe tu pregunta:",
            placeholder="Ejemplo: ¿Qué es un OCAD?",
            label_visibility="collapsed"
        )

    with col2:
        search_button = st.button("🔍 Buscar", type="primary", use_container_width=True)

    # Process query
    if search_button and query:
        with st.spinner("Procesando consulta..."):
            try:
                # Execute pipeline
                result = pipeline.query(
                    question=query,
                    documento_id=config_params["documento_id"],
                    top_k_retrieval=config_params["top_k_retrieval"],
                    top_k_rerank=config_params["top_k_rerank"],
                    expand_context=config_params["expand_context"],
                )

                # Update total cost
                if result.get("success") and result.get("metrics"):
                    st.session_state.total_cost += result["metrics"].get("llm_cost", 0)

                # Store result
                st.session_state.last_result = result

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                return

    # Display results
    if "last_result" in st.session_state:
        result = st.session_state.last_result

        if result.get("success"):
            st.markdown("---")

            # Answer
            render_answer(result)

            st.markdown("---")

            # Metrics
            render_metrics(result.get("metrics", {}))

            st.markdown("---")

            # Sources
            if result.get("sources"):
                render_sources(result["sources"])
        else:
            st.error(f"❌ Error: {result.get('error', 'Unknown error')}")

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 2rem;'>
        <p>Sistema RAG MVP - Documentos Normativos SGR</p>
        <p style='font-size: 0.8rem;'>Desarrollado con Qdrant, OpenAI GPT-4o-mini y Streamlit</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
