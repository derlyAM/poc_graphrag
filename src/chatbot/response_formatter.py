"""
Response Formatter - Formateo de respuestas según modo.

Formatea respuestas del Pipeline RAG según el modo seleccionado (corto/largo).
NO duplica lógica de generación, solo post-procesa el output.
"""
from typing import List, Dict
from loguru import logger
import re


class ResponseFormatter:
    """
    Formatea respuestas según modo de interacción.

    Modos:
    - short: Respuesta concisa + lista de documentos
    - long: Respuesta completa + citaciones detalladas

    NO duplica generación - solo formatea el output del Pipeline.
    """

    def __init__(self):
        """Inicializa response formatter."""
        logger.debug("ResponseFormatter initialized")

    def format_response(
        self,
        answer: str,
        chunks: List[Dict],
        mode: str = "long"
    ) -> Dict:
        """
        Formatea respuesta según modo.

        Args:
            answer: Respuesta generada por LLM
            chunks: Chunks recuperados (con metadata)
            mode: "short" o "long"

        Returns:
            {
                "formatted_answer": str,
                "sources": List[str] o List[Dict],
                "mode": str
            }
        """
        if mode == "short":
            return self.format_short_response(answer, chunks)
        elif mode == "long":
            return self.format_long_response(answer, chunks)
        else:
            logger.warning(f"Unknown mode: {mode}, defaulting to long")
            return self.format_long_response(answer, chunks)

    def format_short_response(
        self,
        answer: str,
        chunks: List[Dict]
    ) -> Dict:
        """
        Formato corto:
        - Solo primeros 2-3 párrafos
        - Sin citaciones inline (se remueven)
        - Lista simple de documentos únicos

        Args:
            answer: Respuesta del LLM
            chunks: Chunks recuperados

        Returns:
            Dict con respuesta formateada y lista de documentos
        """
        logger.debug("Formatting response in SHORT mode")

        # 1. Truncar a primeros 2-3 párrafos
        paragraphs = answer.split('\n\n')
        short_answer = '\n\n'.join(paragraphs[:2])

        # 2. Remover citaciones inline si existen
        # Patrón: [Documento, Sección] o [Art. X, Doc]
        short_answer = re.sub(r'\[([^\]]+)\]', '', short_answer)

        # 3. Limpiar espacios múltiples
        short_answer = re.sub(r'\s+', ' ', short_answer).strip()

        # 4. Extraer documentos únicos
        unique_docs = set()
        for chunk in chunks[:10]:  # Top 10 fuentes
            doc_name = chunk.get('documento_nombre', 'Documento desconocido')
            unique_docs.add(doc_name)

        # Ordenar alfabéticamente
        source_documents = sorted(list(unique_docs))

        logger.info(f"Short response: {len(short_answer)} chars, {len(source_documents)} docs")

        return {
            "formatted_answer": short_answer,
            "sources": source_documents,
            "mode": "short",
            "num_sources": len(source_documents)
        }

    def format_long_response(
        self,
        answer: str,
        chunks: List[Dict]
    ) -> Dict:
        """
        Formato largo:
        - Respuesta completa sin modificar
        - Citaciones inline preservadas
        - Fuentes detalladas con metadata

        Args:
            answer: Respuesta del LLM
            chunks: Chunks recuperados

        Returns:
            Dict con respuesta completa y fuentes detalladas
        """
        logger.debug("Formatting response in LONG mode")

        # En modo largo, la respuesta se usa tal cual
        # (ya viene con citaciones del LLM)

        # Extraer metadata detallada de fuentes
        detailed_sources = []
        seen_citations = set()

        for chunk in chunks[:10]:  # Top 10 fuentes
            citacion = chunk.get('citacion_corta', 'N/A')

            # Evitar duplicados
            if citacion in seen_citations:
                continue
            seen_citations.add(citacion)

            source_info = {
                "documento": chunk.get('documento_nombre', 'N/A'),
                "citacion": citacion,
                "seccion": chunk.get('seccion_nombre') or chunk.get('capitulo_nombre') or 'N/A',
                "score": chunk.get('score', 0.0)
            }
            detailed_sources.append(source_info)

        logger.info(f"Long response: {len(answer)} chars, {len(detailed_sources)} sources")

        return {
            "formatted_answer": answer,  # Sin modificar
            "sources": detailed_sources,
            "mode": "long",
            "num_sources": len(detailed_sources)
        }

    def extract_citations_from_answer(self, answer: str) -> List[str]:
        """
        Extrae citaciones inline del texto.

        Útil para análisis o validación.

        Args:
            answer: Texto con potenciales citaciones

        Returns:
            Lista de citaciones encontradas
        """
        # Patrón: [Algo, Algo más]
        pattern = r'\[([^\]]+)\]'
        citations = re.findall(pattern, answer)

        return citations

    def format_sources_for_display(
        self,
        sources: List,
        mode: str
    ) -> str:
        """
        Formatea fuentes para display en UI.

        Args:
            sources: Lista de fuentes (str o Dict según modo)
            mode: "short" o "long"

        Returns:
            String formateado para mostrar
        """
        if mode == "short":
            # Sources es lista de strings (nombres de documentos)
            if not sources:
                return "Sin fuentes"

            return "\n".join([f"• {doc}" for doc in sources])

        else:  # long
            # Sources es lista de dicts con metadata
            if not sources:
                return "Sin fuentes"

            formatted = []
            for i, source in enumerate(sources, 1):
                if isinstance(source, dict):
                    formatted.append(
                        f"{i}. **{source['documento']}**\n"
                        f"   Citación: {source['citacion']}\n"
                        f"   Sección: {source['seccion']}"
                    )
                else:
                    formatted.append(f"{i}. {source}")

            return "\n\n".join(formatted)
