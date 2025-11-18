"""
Streamlit UI for RAG Document Q&A System.
Professional interface for querying legal documents.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import warnings
import streamlit as st
from loguru import logger
from src.pipeline import RAGPipeline
from src.config import config, VALID_AREAS, get_area_display_name
from src.shared_resources import get_shared_pipeline

# Suppress Streamlit ScriptRunContext warning
warnings.filterwarnings("ignore", message=".*ScriptRunContext.*")

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
    """
    Load and cache the RAG pipeline.

    Uses global singleton to avoid multiple Qdrant connections
    when switching between pages.
    """
    with st.spinner("Inicializando sistema RAG..."):
        pipeline = get_shared_pipeline()
        return pipeline


@st.cache_data(ttl=600)  # Cache for 10 minutes
def get_cached_documents(area: str, _pipeline=None) -> list[dict]:
    """
    Get and cache documents for an area.

    PHASE 2.5: Cached to avoid multiple Qdrant connections.
    Uses pipeline's Qdrant client if available.

    Args:
        area: Area code
        _pipeline: Pipeline instance (prefixed with _ to exclude from cache key)
    """
    from src.config import get_documents_for_area

    # Try to reuse pipeline's Qdrant client
    if _pipeline is not None:
        try:
            qdrant_client = _pipeline.vector_search.qdrant_client
            return get_documents_for_area(area, qdrant_client=qdrant_client)
        except Exception as e:
            # If pipeline client fails, fall back to creating new connection
            pass

    # Fallback: create temporary connection
    # This will only be called once per area (cached)
    return get_documents_for_area(area)


def render_sidebar():
    """Render sidebar with configuration."""
    with st.sidebar:
        st.markdown("## ⚙️ Configuración")

        # Area selector (NUEVO v1.3.0 - separación por dominio)
        st.markdown("### 🎯 Área de Consulta")

        # Create dropdown options with display names
        area_options = {area_code: get_area_display_name(area_code) for area_code in VALID_AREAS.keys()}

        area_display = st.selectbox(
            "Seleccionar área",
            options=list(area_options.values()),
            index=0,  # Default to first option (SGR)
            help="⚠️ IMPORTANTE: Solo se buscarán documentos del área seleccionada. Esto garantiza que no se mezclen resultados de diferentes dominios."
        )

        # Get area code from display name
        area = [code for code, name in area_options.items() if name == area_display][0]

        st.info(f"📚 Consultando: **{area_display}**")

        st.markdown("---")

        # PHASE 2.5: Multi-document filter
        st.markdown("### 📑 Documentos")

        # Get available documents for the selected area (cached)
        # Only show if pipeline is initialized (avoids Qdrant lock issues)
        pipeline = st.session_state.get("pipeline")
        documento_ids = None  # Default value

        if pipeline is None:
            st.info("⏳ Cargando documentos disponibles...")
            available_docs = []
        else:
            available_docs = get_cached_documents(area, _pipeline=pipeline)

        if available_docs:
            # Create dict for display name → doc_id mapping
            docs_dict = {doc["nombre"]: doc["id"] for doc in available_docs}

            selected_doc_names = st.multiselect(
                "Filtrar por documentos (vacío = todos)",
                options=list(docs_dict.keys()),
                default=[],
                help=f"📚 {len(available_docs)} documentos disponibles. Selecciona uno o varios, o deja vacío para buscar en todos los documentos del área."
            )

            # Convert selected names to IDs
            documento_ids = [docs_dict[name] for name in selected_doc_names] if selected_doc_names else None

            # Show selection info
            if documento_ids:
                st.success(f"✓ Buscando en {len(documento_ids)} documento(s) seleccionado(s)")
            else:
                st.info(f"ℹ️ Buscando en TODOS los {len(available_docs)} documentos del área")
        elif pipeline is not None:
            # Pipeline loaded but no documents found
            st.warning(f"⚠️ No hay documentos disponibles en el área '{area_display}'")

        # DEPRECATED: Keep for backward compatibility (not displayed)
        documento_id = None

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

            # Multihop settings (v1.2.0)
            enable_multihop = st.checkbox(
                "Multihop Retrieval",
                value=True,
                help="🚀 Activa razonamiento multi-paso para queries complejas (condicionales, comparativas, procedurales). Más lento pero más preciso."
            )

            if enable_multihop:
                st.info("💡 Multihop detecta automáticamente queries complejas y las descompone en sub-queries para mejor precisión.")

            st.markdown("---")

            # HyDE settings (NEW v1.3.0)
            enable_hyde = st.checkbox(
                "HyDE (Hypothetical Document Embeddings)",
                value=True,
                help="🔬 NUEVO: Genera documentos hipotéticos para mejorar búsqueda semántica. Especialmente útil para queries con terminología incorrecta o definiciones. Incrementa costo ~15%."
            )

            if enable_hyde:
                st.info("💡 HyDE traduce automáticamente tu query al estilo del documento y activa fallback si los resultados son pobres.")

            st.markdown("---")

            # Response Validation settings (PHASE 3)
            enable_validation = st.checkbox(
                "⚡ Validación de Completitud (FASE 3)",
                value=True,
                help="🎯 NUEVO: Valida automáticamente si la respuesta está completa y hace retry si detecta información faltante. Mejora precisión +20% en queries complejas. Incrementa costo ~10-20%."
            )

            if enable_validation:
                st.info("💡 FASE 3: Sistema valida la respuesta y busca información adicional si detecta gaps. Ideal para queries con múltiples aspectos.")

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
        st.markdown("### 💡 Ejemplos de Queries")

        with st.expander("📝 Queries Simples"):
            st.markdown("""
            - ¿Qué es un OCAD?
            - ¿Qué es el Sistema General de Regalías?
            - Define proyecto de inversión
            """)

        with st.expander("🔄 Queries Multihop (Complejas)"):
            st.markdown("""
            **Condicionales:**
            - ¿Puedo ajustar el cronograma si estoy en fase II?
            - Si mi proyecto es de salud, ¿qué OCAD lo evalúa?

            **Comparativas:**
            - Diferencias entre Acuerdo 03/2021 y 13/2025
            - Compara requisitos de CTEI vs infraestructura

            **Procedurales:**
            - Proceso completo desde radicación hasta desembolso
            - ¿Cómo solicitar ajuste a proyecto aprobado?
            """)

        with st.expander("💡 Cómo Formular Queries Efectivas"):
            st.markdown("""
            **Para mejores resultados:**

            ✅ **SÍ - Menciona secciones específicas:**
            - "sección 18 productos esperados"
            - "sección 25 fuentes de financiación"

            ✅ **SÍ - Usa terminología del documento:**
            - "productos esperados" en vez de "productos construidos"
            - "fuentes de financiación" en vez de "presupuesto"

            ✅ **SÍ - Sé específico:**
            - "¿Qué requisitos hay para proyectos de CTEI en fase III?"
            - En vez de: "¿Qué requisitos hay?"

            ❌ **NO - Queries muy genéricas:**
            - "cuéntame del documento"
            - "qué dice aquí"
            """)

        # Query tips button
        if st.button("📖 Ver Guía Completa de Queries"):
            st.session_state.show_guide = True

        return {
            "area": area,  # v1.3.0 - Área de conocimiento obligatoria
            "documento_ids": documento_ids,  # PHASE 2.5 - Filtro multi-documento
            "documento_id": documento_id,  # DEPRECATED - Mantener compatibilidad
            "top_k_retrieval": top_k_retrieval,
            "top_k_rerank": top_k_rerank,
            "expand_context": expand_context,
            "enable_multihop": enable_multihop,
            "enable_hyde": enable_hyde,
            "enable_validation": enable_validation,  # PHASE 3 - Response validation
        }


def render_answer(result):
    """Render the answer section."""
    st.markdown("## 💬 Respuesta")

    # Show HyDE info if used (NEW v1.3.0)
    hyde_metadata = result.get("hyde_metadata", {})
    if hyde_metadata.get("hyde_used"):
        with st.expander("🔬 Análisis HyDE (Click para detalles)", expanded=False):
            col1, col2 = st.columns(2)

            with col1:
                st.metric("HyDE Activado", "Sí")
                st.metric("Fallback Usado", "Sí" if hyde_metadata.get("hyde_fallback_used") else "No")

            with col2:
                st.metric("Score Promedio", f"{hyde_metadata.get('hyde_avg_score', 0):.3f}")

            if hyde_metadata.get("hyde_doc"):
                st.markdown("**Documento Hipotético Generado:**")
                st.text(hyde_metadata["hyde_doc"][:300] + "..." if len(hyde_metadata["hyde_doc"]) > 300 else hyde_metadata["hyde_doc"])

            if hyde_metadata.get("hyde_fallback_used"):
                st.success("✅ HyDE fallback mejoró los resultados automáticamente")

    # Show multihop info if used (v1.2.0)
    if result.get("multihop_used"):
        decomposition = result.get("query_decomposition", {})

        with st.expander("🚀 Análisis Multihop (Click para detalles)", expanded=False):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Tipo de Query", decomposition.get("query_type", "N/A").title())

            with col2:
                st.metric("Complejidad", decomposition.get("complexity", "N/A").title())

            with col3:
                st.metric("Sub-queries", len(decomposition.get("sub_queries", [])))

            if decomposition.get("sub_queries"):
                st.markdown("**Sub-queries ejecutadas:**")
                for i, sq in enumerate(decomposition["sub_queries"], 1):
                    st.markdown(f"{i}. {sq}")

            # Show multihop stats if available
            multihop_stats = result.get("metrics", {}).get("multihop_stats")
            if multihop_stats:
                st.markdown("---")
                st.markdown("**Estadísticas de Retrieval:**")
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"- Total chunks únicos: {multihop_stats.get('total_chunks', 0)}")
                    st.write(f"- Score promedio: {multihop_stats.get('avg_score', 0):.4f}")
                with col2:
                    chunks_by_sources = multihop_stats.get('chunks_by_num_sources', {})
                    if chunks_by_sources:
                        st.write("- Chunks por # de fuentes:")
                        for num, count in sorted(chunks_by_sources.items()):
                            st.write(f"  • {num} fuente(s): {count} chunks")

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
        # Check if this chunk was found by multiple sub-queries (multihop)
        sub_query_sources = chunk.get('sub_query_source', [])
        is_multihop_chunk = len(sub_query_sources) > 1

        # Build title with multihop indicator
        title = f"Fuente {i}: {chunk.get('citacion_corta', 'N/A')}"
        score = chunk.get('fused_score', chunk.get('rerank_score', chunk.get('score', 0)))
        title += f" (Score: {score:.3f})"

        if is_multihop_chunk:
            title += f" 🔗 {len(sub_query_sources)} fuentes"

        with st.expander(title):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(f"**Documento:** {chunk.get('documento_nombre', 'N/A')}")
                st.markdown(f"**Artículo:** {chunk.get('articulo', 'N/A')}")
                st.markdown(f"**Tipo:** {chunk.get('tipo_contenido', 'N/A').title()}")

                # Show sub-query sources if multihop
                if sub_query_sources:
                    st.markdown(f"**Encontrado por {len(sub_query_sources)} sub-query(s):**")
                    for sq in sub_query_sources[:3]:  # Show max 3
                        st.markdown(f"- _{sq[:80]}..._" if len(sq) > 80 else f"- _{sq}_")

            with col2:
                st.markdown(f"**Tokens:** {chunk.get('longitud_tokens', 0)}")
                if chunk.get('fused_score'):
                    st.markdown(f"**Score Original:** {chunk.get('score', 0):.3f}")
                    st.markdown(f"**Score Fusionado:** {chunk.get('fused_score', 0):.3f}")
                    if chunk.get('boost_factor'):
                        st.markdown(f"**Boost:** {chunk.get('boost_factor', 1.0):.1f}x")
                elif chunk.get('rerank_score'):
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


def render_query_guide():
    """Render complete query guide (NEW v1.2.0)."""
    st.markdown("# 📖 Guía Completa: Cómo Formular Queries Efectivas")

    st.markdown("""
    Esta guía te ayudará a obtener mejores resultados del sistema RAG.
    """)

    st.markdown("---")

    # Section 1: Query Types
    st.markdown("## 1️⃣ Tipos de Queries")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### ✅ Queries Simples (Single-hop)")
        st.markdown("""
        **Características:**
        - Una sola pregunta directa
        - Respuesta en 1-2 fuentes
        - Rápidas (3-5 segundos)

        **Ejemplos:**
        ```
        ✓ ¿Qué es un OCAD?
        ✓ Define proyecto de inversión
        ✓ ¿Qué es el SGR?
        ```
        """)

    with col2:
        st.markdown("### 🚀 Queries Complejas (Multihop)")
        st.markdown("""
        **Características:**
        - Requieren múltiples pasos
        - Información de varias fuentes
        - Más lentas (8-15 segundos)

        **Ejemplos:**
        ```
        ✓ ¿Puedo ajustar X si tengo Y?
        ✓ Diferencias entre A y B
        ✓ Proceso completo de X a Z
        ```
        """)

    st.markdown("---")

    # Section 2: Best Practices
    st.markdown("## 2️⃣ Mejores Prácticas")

    st.success("""
    ### ✅ SÍ - Menciona secciones específicas

    Para **Documento Técnico V2**, usa números de sección:
    - "sección 18 productos esperados"
    - "sección 25 fuentes de financiación"
    - "sección 6 antecedentes"

    Para **Acuerdo Único 2025**, usa capítulos/artículos:
    - "capítulo 4 ajustes de proyectos"
    - "artículo 4.5.1.2"
    - "título 3"
    """)

    st.success("""
    ### ✅ SÍ - Usa terminología del documento

    **Documento Técnico:**
    - "productos esperados" (no "productos construidos")
    - "fuentes de financiación" (no "presupuesto")
    - "resultados e impactos" (no "resultados del proyecto")

    **Acuerdo Único:**
    - "viabilización de proyectos" (no "aprobación")
    - "ajustes a proyectos" (no "modificaciones")
    - "OCAD" (no "comité")
    """)

    st.success("""
    ### ✅ SÍ - Sé específico y contextual

    **Mal:**
    - "¿Qué requisitos hay?"

    **Bien:**
    - "¿Qué requisitos hay para proyectos de CTEI en fase III?"

    **Mal:**
    - "cuéntame del proyecto"

    **Bien:**
    - "¿Cuáles son los productos esperados del proyecto en la sección 18?"
    """)

    st.error("""
    ### ❌ NO - Queries muy genéricas

    Estas queries suelen fallar:
    - "cuéntame del documento"
    - "qué dice aquí"
    - "dame información"
    - "resumen" (sin especificar qué resumir)
    """)

    st.markdown("---")

    # Section 3: Examples by Document
    st.markdown("## 3️⃣ Ejemplos por Documento")

    with st.expander("📄 Documento Técnico V2", expanded=True):
        st.markdown("""
        **Queries Efectivas:**

        1. **Sobre productos:**
           - ✅ "sección 18 productos esperados del proyecto"
           - ✅ "¿cuáles son los entregables en la sección 18?"

        2. **Sobre presupuesto:**
           - ✅ "sección 25 resumen de fuentes de financiación"
           - ✅ "¿cuál es el valor total del proyecto en la sección 25?"

        3. **Sobre metodología:**
           - ✅ "sección 14 metodología propuesta"
           - ✅ "¿cuál es la metodología en la sección 14?"

        4. **Queries Complejas (Multihop):**
           - ✅ "¿cuáles son los productos esperados y cuál es el valor total del proyecto?"
           - ✅ "compara la metodología de la sección 14 con los resultados de la sección 17"
        """)

    with st.expander("📄 Acuerdo Único 2025"):
        st.markdown("""
        **Queries Efectivas:**

        1. **Sobre ajustes:**
           - ✅ "capítulo 4 ajustes a proyectos aprobados"
           - ✅ "¿qué variables puedo ajustar según el artículo 4.5.1.2?"

        2. **Sobre procedimientos:**
           - ✅ "proceso de viabilización de proyectos"
           - ✅ "¿cómo se solicita un ajuste a un proyecto aprobado?"

        3. **Queries Complejas (Multihop):**
           - ✅ "¿puedo ajustar el cronograma de un proyecto en fase II?"
           - ✅ "diferencias entre proyectos de CTEI y de infraestructura"
        """)

    st.markdown("---")

    # Section 4: Understanding Results
    st.markdown("## 4️⃣ Interpretando Resultados")

    st.info("""
    ### 🔍 Scores de Relevancia

    - **> 0.8**: Excelente coincidencia
    - **0.6 - 0.8**: Buena coincidencia
    - **0.3 - 0.6**: Coincidencia moderada
    - **< 0.3**: Baja coincidencia (considera reformular)

    Si todos los scores son < 0.3, intenta:
    1. Mencionar la sección/capítulo específico
    2. Usar terminología exacta del documento
    3. Ser más específico en tu pregunta
    """)

    st.info("""
    ### 🚀 Indicadores Multihop

    Cuando ves **"🚀 Multihop Retrieval"**:
    - El sistema detectó que tu query es compleja
    - Se ejecutaron múltiples búsquedas (sub-queries)
    - Chunks marcados con **🔗** fueron encontrados por varias sub-queries (más relevantes)

    **Boost Factor:**
    - 1.0x: Encontrado por 1 sub-query
    - 1.3x: Encontrado por 2 sub-queries (más relevante)
    - 1.5x: Encontrado por 3+ sub-queries (muy relevante)
    """)

    st.markdown("---")

    # Section 5: Tips
    st.markdown("## 5️⃣ Tips Avanzados")

    st.markdown("""
    ### 💡 Para Queries Multihop (Complejas)

    1. **Condicionales ("¿Puedo X si Y?"):**
       - El sistema verificará automáticamente ambas condiciones
       - Ejemplo: "¿Puedo ajustar el cronograma si estoy en fase II?"

    2. **Comparativas ("Diferencias entre A y B"):**
       - El sistema buscará información de ambos lados
       - Ejemplo: "Diferencias entre proyectos de CTEI y de infraestructura"

    3. **Procedurales ("Proceso de X"):**
       - El sistema buscará múltiples pasos del proceso
       - Ejemplo: "Proceso completo desde radicación hasta desembolso"

    ### ⚡ Para Mejor Performance

    - Queries simples: Desactiva Multihop (más rápido)
    - Queries complejas: Activa Multihop (más preciso)
    - Si no estás seguro: Déjalo activado (se activa solo cuando es necesario)
    """)


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
        total_cost = metrics.get('total_cost', metrics.get('llm_cost', 0))
        st.metric(
            "Costo Total",
            f"${total_cost:.6f}"
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
            st.write(f"- Costo LLM: ${metrics.get('llm_cost', 0):.6f}")

            # HyDE cost if used
            if metrics.get('hyde_cost', 0) > 0:
                st.write(f"- Costo HyDE: ${metrics.get('hyde_cost', 0):.6f}")
                st.write(f"- **Costo Total: ${metrics.get('total_cost', 0):.6f}**")

        # Show indicators for advanced features
        features_used = []
        if metrics.get('multihop_used'):
            features_used.append("🚀 **Multihop Retrieval** (búsquedas múltiples)")
        if metrics.get('hyde_used'):
            features_used.append("🔬 **HyDE** (documento hipotético)")

        if features_used:
            st.markdown("---")
            st.markdown("**Características Avanzadas Usadas:**")
            for feature in features_used:
                st.info(feature)


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

    # Show query guide if requested
    if st.session_state.get("show_guide", False):
        render_query_guide()
        if st.button("❌ Cerrar Guía"):
            st.session_state.show_guide = False
            st.rerun()
        return

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
                    area=config_params["area"],  # v1.3.0 - Filtro por área obligatorio
                    documento_ids=config_params["documento_ids"],  # PHASE 2.5 - Filtro multi-documento
                    documento_id=config_params["documento_id"],  # DEPRECATED
                    top_k_retrieval=config_params["top_k_retrieval"],
                    top_k_rerank=config_params["top_k_rerank"],
                    expand_context=config_params["expand_context"],
                    enable_multihop=config_params["enable_multihop"],  # v1.2.0
                    enable_hyde=config_params["enable_hyde"],  # v1.3.0
                    enable_validation=config_params["enable_validation"],  # PHASE 3
                )

                # Update total cost (including HyDE)
                if result.get("success") and result.get("metrics"):
                    st.session_state.total_cost += result["metrics"].get("total_cost", result["metrics"].get("llm_cost", 0))

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
