"""
Citation Manager module.
Handles validation and formatting of legal citations.
"""
import re
from typing import List, Dict, Set
from loguru import logger


class CitationManager:
    """Manages citation extraction, validation and formatting."""

    def __init__(self):
        """Initialize citation manager."""
        # Pattern to match citations like [Art. X, Documento]
        self.citation_pattern = re.compile(
            r'\[([^\]]+)\]'
        )

    def validate_answer(
        self, answer: str, source_chunks: List[Dict]
    ) -> Dict:
        """
        Validate that answer has proper citations.

        Args:
            answer: Generated answer text
            source_chunks: Source chunks used for generation

        Returns:
            Validation results dictionary
        """
        logger.info("Validating citations in answer")

        # Extract citations from answer
        citations = self.extract_citations(answer)

        # Get available sources
        available_citations = {
            chunk.get("citacion_corta", "") for chunk in source_chunks
        }

        # Check if answer has citations
        has_citations = len(citations) > 0

        # Check for uncited statements (simplified heuristic)
        sentences = self._split_sentences(answer)
        uncited_sentences = []

        for sentence in sentences:
            # Skip very short sentences or questions
            if len(sentence.split()) < 5 or sentence.strip().endswith("?"):
                continue

            # Check if sentence has a citation
            if not self.citation_pattern.search(sentence):
                uncited_sentences.append(sentence[:80] + "...")

        validation = {
            "has_citations": has_citations,
            "citation_count": len(citations),
            "unique_citations": len(set(citations)),
            "available_sources": len(available_citations),
            "uncited_statements": len(uncited_sentences),
            "warnings": [],
        }

        # Generate warnings
        if not has_citations:
            validation["warnings"].append(
                "⚠️ No se encontraron citaciones en la respuesta"
            )

        if uncited_sentences:
            validation["warnings"].append(
                f"⚠️ {len(uncited_sentences)} oraciones sin citación aparente"
            )

        logger.info(
            f"Validation: {len(citations)} citations, {len(uncited_sentences)} uncited statements"
        )

        return validation

    def extract_citations(self, text: str) -> List[str]:
        """
        Extract all citations from text.

        Args:
            text: Text to extract from

        Returns:
            List of citation strings
        """
        matches = self.citation_pattern.findall(text)
        return [match.strip() for match in matches]

    def format_references_section(
        self, source_chunks: List[Dict]
    ) -> str:
        """
        Generate formatted references section.

        Args:
            source_chunks: Chunks used in answer

        Returns:
            Formatted references text
        """
        if not source_chunks:
            return ""

        references = ["## Referencias\n"]

        for i, chunk in enumerate(source_chunks, 1):
            ref = f"{i}. **{chunk.get('citacion_corta', 'N/A')}**\n"
            ref += f"   - Documento: {chunk.get('documento_nombre', 'N/A')}\n"

            articulo = chunk.get('articulo')
            if articulo:
                ref += f"   - Artículo: {articulo}\n"

            tipo = chunk.get('tipo_contenido')
            if tipo:
                ref += f"   - Tipo: {tipo.title()}\n"

            references.append(ref)

        return "\n".join(references)

    def enhance_answer(
        self, answer: str, source_chunks: List[Dict], add_references: bool = True
    ) -> str:
        """
        Enhance answer with formatted references.

        Args:
            answer: Original answer
            source_chunks: Source chunks
            add_references: Whether to add references section

        Returns:
            Enhanced answer
        """
        enhanced = answer

        # Add references section if requested
        if add_references and source_chunks:
            references = self.format_references_section(source_chunks)
            if references:
                enhanced += f"\n\n---\n\n{references}"

        return enhanced

    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences (simple heuristic).

        Args:
            text: Text to split

        Returns:
            List of sentences
        """
        # Simple sentence splitting
        text = text.replace('\n', ' ')
        sentences = re.split(r'[.!?]+\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def generate_citation_report(
        self, answer: str, validation: Dict
    ) -> str:
        """
        Generate human-readable citation report.

        Args:
            answer: Generated answer
            validation: Validation results

        Returns:
            Report string
        """
        report = ["### Reporte de Citaciones\n"]

        # Citation stats
        report.append(
            f"✓ Citaciones encontradas: {validation['citation_count']}"
        )
        report.append(
            f"✓ Fuentes únicas: {validation['unique_citations']}"
        )
        report.append(
            f"✓ Fuentes disponibles: {validation['available_sources']}"
        )

        # Warnings
        if validation.get("warnings"):
            report.append("\n⚠️ Advertencias:")
            for warning in validation["warnings"]:
                report.append(f"  - {warning}")

        # Extract and list citations
        citations = self.extract_citations(answer)
        if citations:
            report.append(f"\n📝 Citaciones usadas:")
            for cit in set(citations):
                count = citations.count(cit)
                report.append(f"  - {cit} ({count}x)")

        return "\n".join(report)


def validate_and_enhance(
    answer: str, source_chunks: List[Dict]
) -> Dict:
    """
    Convenience function for validation and enhancement.

    Args:
        answer: Generated answer
        source_chunks: Source chunks

    Returns:
        Dictionary with enhanced answer and validation
    """
    manager = CitationManager()

    validation = manager.validate_answer(answer, source_chunks)
    enhanced_answer = manager.enhance_answer(answer, source_chunks)
    report = manager.generate_citation_report(answer, validation)

    return {
        "answer": enhanced_answer,
        "validation": validation,
        "report": report,
        "original_answer": answer,
    }
