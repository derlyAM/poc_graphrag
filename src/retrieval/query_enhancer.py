"""
Query Enhancement module.
Detects structured queries (chapters, titles, sections) and enhances retrieval.
"""
import re
from typing import Dict, Optional, List, Tuple
from loguru import logger

from src.ingest.section_mapper import SectionMapper


class QueryEnhancer:
    """Enhances queries to detect structural requests (chapters, titles, etc.)."""

    def __init__(self, section_mapper: Optional[SectionMapper] = None):
        """
        Initialize query enhancer with patterns.

        Args:
            section_mapper: Optional SectionMapper for name→number mapping
        """
        # Section mapper for nombre→número
        self.section_mapper = section_mapper or SectionMapper()

        # Patterns for detecting chapter/title requests
        self.patterns = {
            # "capítulo 2", "capitulo II", "cap. 3"
            # Use word boundary \b after number to avoid matching "capítulo de"
            "capitulo": re.compile(
                r"cap[íi]tulo\s+(\d+|[IVXLCDM]+)\b|cap\.\s*(\d+)",
                re.IGNORECASE
            ),
            # "título 4", "titulo III", "tít. 2"
            "titulo": re.compile(
                r"t[íi]tulo\s+(\d+|[IVXLCDM]+)\b|t[íi]t\.\s*(\d+)",
                re.IGNORECASE
            ),
            # "artículo 5.2.1", "art. 10", "articulo 3"
            "articulo": re.compile(
                r"art[íi]culo\s+([\d\.]+)|art\.\s*([\d\.]+)",
                re.IGNORECASE
            ),
            # "sección 1.2", "seccion 3", "sec. 2.1"
            "seccion": re.compile(
                r"secci[óo]n\s+([\d\.]+)|sec\.\s*([\d\.]+)",
                re.IGNORECASE
            ),
            # "anexo 8", "anexo VIII", "anexo A" (NEW)
            "anexo": re.compile(
                r"anexo\s+(\d+|[IVXLCDM]+|[A-Z])\b",
                re.IGNORECASE
            ),
            # Detect summary requests
            "resumen": re.compile(
                r"resum[ea]|sintetiza|sinopsis|extracto",
                re.IGNORECASE
            ),
            # Detect section mentions by name (NO number) - NEW
            # Require at least 2 words to avoid false positives like "de X"
            "seccion_nombre": re.compile(
                r"secci[óo]n\s+(?:de\s+)?([a-záéíóúñ]+(?:\s+[a-záéíóúñ]+)+)(?:\s+del|\s+de\s+la|\s+en|\s+y|$)",
                re.IGNORECASE
            ),
            "capitulo_nombre": re.compile(
                r"cap[íi]tulo\s+(?:de\s+)?([a-záéíóúñ]+(?:\s+[a-záéíóúñ]+)+)(?:\s+del|\s+de\s+la|\s+en|\s+y|$)",
                re.IGNORECASE
            ),
        }

        # Roman numeral mapping
        self.roman_to_int = {
            "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
            "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10,
        }

    def enhance_query(self, query: str, documento_id: Optional[str] = None) -> Dict:
        """
        Analyze and enhance query.

        Args:
            query: User query
            documento_id: Optional document filter

        Returns:
            Dictionary with enhancement metadata
        """
        logger.info(f"Enhancing query: '{query[:80]}...'")

        enhancement = {
            "original_query": query,
            "enhanced_query": query,
            "query_type": "semantic",  # semantic | structural | hybrid
            "is_summary_request": False,
            "filters": {},
            "expand_to_full_section": False,
            "retrieval_strategy": "standard",  # standard | structural | exhaustive
        }

        # Detect if it's a summary request
        if self.patterns["resumen"].search(query):
            enhancement["is_summary_request"] = True
            logger.info("Detected summary request")

        # Detect structural elements
        capitulo_match = self.patterns["capitulo"].search(query)
        titulo_match = self.patterns["titulo"].search(query)
        articulo_match = self.patterns["articulo"].search(query)
        seccion_match = self.patterns["seccion"].search(query)
        anexo_match = self.patterns["anexo"].search(query)

        # Extract chapter number
        if capitulo_match:
            capitulo_num = capitulo_match.group(1) or capitulo_match.group(2)
            capitulo_normalized = self._normalize_number(capitulo_num)
            enhancement["filters"]["capitulo"] = capitulo_normalized
            enhancement["query_type"] = "structural"
            enhancement["expand_to_full_section"] = True
            enhancement["retrieval_strategy"] = "exhaustive"
            logger.info(f"Detected chapter filter: {capitulo_normalized}")

        # Extract title number
        if titulo_match:
            titulo_num = titulo_match.group(1) or titulo_match.group(2)
            titulo_normalized = self._normalize_number(titulo_num)
            enhancement["filters"]["titulo"] = titulo_normalized
            enhancement["query_type"] = "structural"
            enhancement["expand_to_full_section"] = True
            enhancement["retrieval_strategy"] = "exhaustive"
            logger.info(f"Detected title filter: {titulo_normalized}")

        # Extract article number
        if articulo_match:
            articulo_num = articulo_match.group(1) or articulo_match.group(2)
            enhancement["filters"]["articulo"] = articulo_num
            enhancement["query_type"] = "structural"
            logger.info(f"Detected article filter: {articulo_num}")

        # Extract section number (for technical docs)
        if seccion_match:
            seccion_num = seccion_match.group(1) or seccion_match.group(2)
            enhancement["filters"]["seccion"] = seccion_num
            enhancement["query_type"] = "structural"
            enhancement["expand_to_full_section"] = True
            enhancement["retrieval_strategy"] = "exhaustive"
            logger.info(f"Detected section filter: {seccion_num}")

        # Extract anexo number (NEW - CRITICAL)
        if anexo_match:
            anexo_num = anexo_match.group(1)
            anexo_normalized = self._normalize_number(anexo_num)
            enhancement["filters"]["anexo_numero"] = anexo_normalized
            enhancement["query_type"] = "structural"
            enhancement["expand_to_full_section"] = True
            enhancement["retrieval_strategy"] = "exhaustive"
            logger.info(f"Detected anexo filter: {anexo_normalized}")

        # NEW: Detect section/chapter by NAME (not number)
        # Only if not already detected by number
        if "seccion" not in enhancement["filters"]:
            seccion_nombre_match = self.patterns["seccion_nombre"].search(query)
            if seccion_nombre_match and documento_id:
                seccion_nombre = seccion_nombre_match.group(1).strip()
                # Try to map nombre → número
                seccion_num = self.section_mapper.search_numero_fuzzy(
                    documento_id=documento_id,
                    field_type="seccion",
                    nombre=seccion_nombre
                )
                if seccion_num:
                    enhancement["filters"]["seccion"] = seccion_num
                    enhancement["query_type"] = "structural"
                    enhancement["expand_to_full_section"] = True
                    enhancement["retrieval_strategy"] = "exhaustive"
                    logger.info(
                        f"Detected section by name: '{seccion_nombre}' → seccion={seccion_num}"
                    )
                else:
                    logger.warning(
                        f"Could not map section name '{seccion_nombre}' to number. "
                        f"Falling back to semantic search."
                    )

        # NEW: Detect chapter by NAME (not number)
        if "capitulo" not in enhancement["filters"]:
            capitulo_nombre_match = self.patterns["capitulo_nombre"].search(query)
            if capitulo_nombre_match and documento_id:
                capitulo_nombre = capitulo_nombre_match.group(1).strip()
                # Try to map nombre → número
                capitulo_num = self.section_mapper.search_numero_fuzzy(
                    documento_id=documento_id,
                    field_type="capitulo",
                    nombre=capitulo_nombre
                )
                if capitulo_num:
                    enhancement["filters"]["capitulo"] = capitulo_num
                    enhancement["query_type"] = "structural"
                    enhancement["expand_to_full_section"] = True
                    enhancement["retrieval_strategy"] = "exhaustive"
                    logger.info(
                        f"Detected chapter by name: '{capitulo_nombre}' → capitulo={capitulo_num}"
                    )
                else:
                    logger.warning(
                        f"Could not map chapter name '{capitulo_nombre}' to number. "
                        f"Falling back to semantic search."
                    )

        # If both semantic and structural elements, it's hybrid
        if enhancement["query_type"] == "structural":
            # Check if there's additional semantic content beyond the structural reference
            query_without_structure = self._remove_structural_patterns(query)
            if len(query_without_structure.strip()) > 10:  # Has meaningful content
                enhancement["query_type"] = "hybrid"
                enhancement["enhanced_query"] = query_without_structure
                logger.info(f"Hybrid query detected. Semantic part: '{query_without_structure[:50]}...'")

        return enhancement

    def _normalize_number(self, num_str: str) -> str:
        """
        Normalize number (convert roman to arabic, etc.).

        Args:
            num_str: Number string (could be "2", "II", etc.)

        Returns:
            Normalized number as string
        """
        num_str = num_str.strip().upper()

        # If it's roman numeral, convert to arabic
        if num_str in self.roman_to_int:
            return str(self.roman_to_int[num_str])

        # If it's already arabic, return as is
        if num_str.isdigit():
            return num_str

        # Try to extract first number
        match = re.search(r'\d+', num_str)
        if match:
            return match.group(0)

        return num_str

    def _remove_structural_patterns(self, query: str) -> str:
        """
        Remove structural patterns from query to get semantic part.

        Args:
            query: Original query

        Returns:
            Query without structural patterns
        """
        result = query

        # Remove all structural patterns
        for pattern_name, pattern in self.patterns.items():
            if pattern_name != "resumen":  # Keep summary keywords
                result = pattern.sub("", result)

        # Clean up extra whitespace
        result = re.sub(r'\s+', ' ', result).strip()

        return result

    def should_use_structural_search(self, enhancement: Dict) -> bool:
        """
        Determine if structural search should be used.

        Args:
            enhancement: Enhancement metadata

        Returns:
            True if structural search should be used
        """
        return enhancement["query_type"] in ["structural", "hybrid"]

    def get_retrieval_config(self, enhancement: Dict, default_top_k: int = 20) -> Dict:
        """
        Get retrieval configuration based on enhancement.

        Dynamically adjusts top_k based on query type:
        - Simple semantic: 10-20
        - Structural: 50
        - Aggregation (list/enumerate): 100
        - Comparison: 40

        Args:
            enhancement: Enhancement metadata
            default_top_k: Default top_k value

        Returns:
            Retrieval configuration
        """
        query = enhancement["original_query"].lower()

        config = {
            "top_k": default_top_k,
            "expand_context": True,
            "filters": enhancement["filters"],
        }

        # Detect aggregation queries (needs MANY chunks)
        aggregation_keywords = [
            "lista", "listar", "enumera", "enumerar", "todos",
            "cuales son", "cuáles son", "qué requisitos", "que requisitos"
        ]
        is_aggregation = any(keyword in query for keyword in aggregation_keywords)

        # Detect comparison queries
        comparison_keywords = [
            "diferencia", "diferencias", "compara", "comparar",
            "versus", "vs", "entre", "similar", "distinción"
        ]
        is_comparison = any(keyword in query for keyword in comparison_keywords)

        # Apply dynamic top_k
        if is_aggregation:
            config["top_k"] = 100  # Maximum chunks for complete lists
            config["expand_context"] = True
            logger.info("Using aggregation strategy (top_k=100)")

        elif is_comparison:
            config["top_k"] = 40  # Need chunks from both sides
            config["expand_context"] = True
            logger.info("Using comparison strategy (top_k=40)")

        # For structural queries, we want MORE results
        elif enhancement["retrieval_strategy"] == "exhaustive":
            config["top_k"] = 50  # Get more chunks for full section
            config["expand_context"] = True  # Always expand
            logger.info("Using exhaustive retrieval strategy (top_k=50)")

        # For hybrid queries, balance between semantic and structural
        elif enhancement["query_type"] == "hybrid":
            config["top_k"] = 30
            logger.info("Using hybrid retrieval strategy (top_k=30)")

        # For simple semantic queries, use minimal top_k for speed
        elif enhancement["query_type"] == "semantic":
            config["top_k"] = 10
            logger.info("Using semantic strategy (top_k=10)")

        return config


def enhance_query(query: str, documento_id: Optional[str] = None) -> Dict:
    """
    Convenience function to enhance a query.

    Args:
        query: User query
        documento_id: Optional document filter

    Returns:
        Enhancement metadata
    """
    enhancer = QueryEnhancer()
    return enhancer.enhance_query(query, documento_id)
