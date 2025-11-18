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

        # NUEVO: Patterns for specific terms (Phase 1 improvement)
        self.specific_patterns = {
            # "objetivo número 1", "objetivo 4"
            "objetivo_numero": re.compile(
                r"objetivo\s+(número\s+)?(\d+)",
                re.IGNORECASE
            ),
            # "niveles de riesgo", "tipos de", "ejemplos de"
            "lista_request": re.compile(
                r"(cuáles|cuales|qué|que)\s+(son|están)?\s*(los|las)?\s*(niveles|tipos|ejemplos|prácticas|requisitos|elementos|cambios|riesgos)",
                re.IGNORECASE
            ),
            # "costo", "precio", "sanción", "multa"
            "dato_numerico": re.compile(
                r"(costo|precio|sanción|sanciones|multa|cantidad|monto|valor|cifra)s?",
                re.IGNORECASE
            ),
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
            "has_specific_terms": False,  # NUEVO: indica si tiene términos muy específicos
            "has_list_request": False,  # NUEVO: indica si pide una lista
            "has_numeric_data": False,  # NUEVO: indica si pide datos numéricos
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

        # NUEVO: Detect and enhance specific terms (Phase 1)
        specific_enhancement = self._enhance_specific_queries(query)
        if specific_enhancement:
            enhancement["enhanced_query"] = specific_enhancement["enhanced_query"]
            enhancement["has_specific_terms"] = specific_enhancement.get("has_specific_terms", False)
            enhancement["has_list_request"] = specific_enhancement.get("has_list_request", False)
            enhancement["has_numeric_data"] = specific_enhancement.get("has_numeric_data", False)
            logger.info(f"Query enhanced with specific terms: '{enhancement['enhanced_query'][:80]}...'")

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

    def _enhance_specific_queries(self, query: str) -> Optional[Dict]:
        """
        Detect and enhance queries with very specific terms (Phase 1 improvement).

        Examples:
            "objetivo número 1" → "objetivo 1" + "1. objetivo" + "OBJETIVO 1"
            "¿Cuáles niveles?" → query + "lista completa enumerar todos"
            "costo estimado" → query + "datos numéricos cifras monto"

        Args:
            query: Original query

        Returns:
            Enhancement dict with enhanced_query or None
        """
        enhancements = []
        has_specific = False
        has_list = False
        has_numeric = False

        # Detect "objetivo número X", "artículo número Y"
        objetivo_match = self.specific_patterns["objetivo_numero"].search(query)
        if objetivo_match:
            numero = objetivo_match.group(2)
            # Generate variations
            enhancements.extend([
                f"objetivo {numero}",
                f"objetivo número {numero}",
                f"{numero}. objetivo",
                f"OBJETIVO {numero}",
            ])
            has_specific = True
            logger.debug(f"Detected objetivo número: {numero}")

        # Detect list/enumeration requests
        lista_match = self.specific_patterns["lista_request"].search(query)
        if lista_match:
            enhancements.append("lista completa enumerar todos principales")
            has_list = True
            logger.debug("Detected list request")

        # Detect numeric data requests
        numerico_match = self.specific_patterns["dato_numerico"].search(query)
        if numerico_match:
            enhancements.append("datos numéricos cifras monto valor cantidad")
            has_numeric = True
            logger.debug("Detected numeric data request")

        # If no enhancements, return None
        if not enhancements:
            return None

        # Build enhanced query
        enhanced_query = query + " " + " ".join(enhancements)

        return {
            "enhanced_query": enhanced_query,
            "expansions": enhancements,
            "has_specific_terms": has_specific or has_numeric,
            "has_list_request": has_list,
            "has_numeric_data": has_numeric,
        }

    def should_use_structural_search(self, enhancement: Dict) -> bool:
        """
        Determine if structural search should be used.

        Args:
            enhancement: Enhancement metadata

        Returns:
            True if structural search should be used
        """
        return enhancement["query_type"] in ["structural", "hybrid"]

    def get_retrieval_config(
        self,
        enhancement: Dict,
        default_top_k: int = 20,
        documento_ids: Optional[List[str]] = None,
        area: Optional[str] = None
    ) -> Dict:
        """
        Get retrieval configuration based on enhancement.

        Dynamically adjusts top_k and context_window based on query type:
        - Simple semantic: top_k=10, window=1
        - Specific terms (numbers, data): top_k=15, window=1 (Phase 1)
        - List requests: top_k=100, window=2 (Phase 1 + Phase 2)
        - Structural: top_k=50, window=1
        - Aggregation (list/enumerate): top_k=100, window=2 (Phase 2)
        - Comparison: top_k=40, window=2 (Phase 2)

        PHASE 2.5 IMPROVEMENT: Adjusts top_k proportionally when filtering by documents.

        Args:
            enhancement: Enhancement metadata
            default_top_k: Default top_k value
            documento_ids: Optional list of document IDs being filtered
            area: Optional area for calculating corpus size

        Returns:
            Retrieval configuration with top_k, expand_context, context_window, filters
        """
        query = enhancement["original_query"].lower()

        config = {
            "top_k": default_top_k,
            "expand_context": True,
            "context_window": 1,  # PHASE 2: Default window size
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

        # PHASE 1 + 2: Priority-based top_k and context_window selection
        # Priority 1: Aggregation (needs most chunks + wider context)
        if is_aggregation or enhancement.get("has_list_request"):
            config["top_k"] = 100  # Maximum chunks for complete lists
            config["expand_context"] = True
            config["context_window"] = 2  # PHASE 2: Expand ±2 chunks for lists
            logger.info("Using aggregation strategy (top_k=100, window=2)")

        # Priority 2: Comparison (needs chunks from both sides + context)
        elif is_comparison:
            config["top_k"] = 40  # Need chunks from both sides
            config["expand_context"] = True
            config["context_window"] = 2  # PHASE 2: Wider context for comparisons
            logger.info("Using comparison strategy (top_k=40, window=2)")

        # Priority 3: Structural/exhaustive
        elif enhancement["retrieval_strategy"] == "exhaustive":
            config["top_k"] = 50  # Get more chunks for full section
            config["expand_context"] = True  # Always expand
            config["context_window"] = 1  # Standard window
            logger.info("Using exhaustive retrieval strategy (top_k=50, window=1)")

        # Priority 4: Hybrid
        elif enhancement["query_type"] == "hybrid":
            config["top_k"] = 30
            config["context_window"] = 1
            logger.info("Using hybrid retrieval strategy (top_k=30, window=1)")

        # PHASE 1: Priority 5: Specific terms (numbers, numeric data)
        elif enhancement.get("has_specific_terms") or enhancement.get("has_numeric_data"):
            config["top_k"] = 15  # More chunks to find specific data
            config["expand_context"] = True  # Always expand for context
            config["context_window"] = 2  # PHASE 2: Wider window for specific searches
            logger.info("Using specific terms strategy (top_k=15, window=2)")

        # Priority 6: Simple semantic (least chunks, minimal context)
        elif enhancement["query_type"] == "semantic":
            config["top_k"] = 10
            config["context_window"] = 1
            logger.info("Using semantic strategy (top_k=10, window=1)")

        # PHASE 2.5: Adjust top_k based on corpus size (document filtering)
        if documento_ids and area:
            original_top_k = config["top_k"]
            adjusted_top_k = self._adjust_top_k_for_corpus_size(
                base_top_k=original_top_k,
                documento_ids=documento_ids,
                area=area
            )
            if adjusted_top_k != original_top_k:
                config["top_k"] = adjusted_top_k
                logger.info(
                    f"Adjusted top_k for filtered corpus: {original_top_k} → {adjusted_top_k} "
                    f"({len(documento_ids)} docs selected)"
                )

        return config

    def _adjust_top_k_for_corpus_size(
        self,
        base_top_k: int,
        documento_ids: List[str],
        area: str
    ) -> int:
        """
        Adjust top_k proportionally based on corpus size reduction.

        PHASE 2.5 IMPROVEMENT: When filtering by documents, reduce top_k
        proportionally to avoid requesting more chunks than available.

        Args:
            base_top_k: Original top_k value
            documento_ids: List of filtered document IDs
            area: Area to determine total documents count

        Returns:
            Adjusted top_k value (minimum 5)

        Example:
            Area has 10 documents, user filters by 2 docs:
            base_top_k=100 → adjusted=100 * (2/10) = 20
        """
        from src.config import get_documents_for_area

        # Get total documents in area
        try:
            all_docs = get_documents_for_area(area)
            total_docs = len(all_docs)

            if total_docs == 0:
                logger.warning(f"No documents found in area '{area}', using base top_k")
                return base_top_k

            # Calculate reduction factor
            num_filtered_docs = len(documento_ids)
            reduction_factor = num_filtered_docs / total_docs

            # Apply reduction
            adjusted_top_k = int(base_top_k * reduction_factor)

            # Ensure minimum reasonable value
            MIN_TOP_K = 5
            adjusted_top_k = max(MIN_TOP_K, adjusted_top_k)

            logger.debug(
                f"Corpus size adjustment: {num_filtered_docs}/{total_docs} docs "
                f"→ reduction factor {reduction_factor:.2f} "
                f"→ top_k {base_top_k} → {adjusted_top_k}"
            )

            return adjusted_top_k

        except Exception as e:
            logger.warning(f"Could not adjust top_k for corpus size: {e}")
            return base_top_k


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
