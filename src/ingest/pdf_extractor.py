"""
PDF Extractor module.
Extracts text from PDFs preserving hierarchical structure for multiple document types.
"""
import re
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger
import pymupdf


class PDFExtractor:
    """Extracts structured text from PDF documents."""

    def __init__(self):
        """Initialize PDF extractor."""
        # Patterns for legal documents
        self.legal_patterns = {
            "titulo": re.compile(r"T[ÍI]TULO\s+(\d+|[IVXLCDM]+)", re.IGNORECASE),
            "capitulo": re.compile(r"CAP[ÍI]TULO\s+(\d+|[IVXLCDM]+)", re.IGNORECASE),
            "articulo": re.compile(r"ART[ÍI]CULO\s+([\d\.]+)", re.IGNORECASE),
            "paragrafo": re.compile(r"PAR[ÁA]GRAFO\s+(\d+)", re.IGNORECASE),
            "seccion": re.compile(r"SECCI[ÓO]N\s+(\d+|[IVXLCDM]+)", re.IGNORECASE),
        }

        # Patterns for technical/structured documents (numbered sections)
        self.technical_patterns = {
            # Matches: "1. TITLE", "12. SECTION NAME"
            "seccion": re.compile(r"^(\d+)\.\s+([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{10,})", re.MULTILINE),
            # Matches: "1.1 Subtitle", "5.2 Problem description"
            "subseccion": re.compile(r"^(\d+\.\d+)\s+([A-Za-záéíóúñÁÉÍÓÚÑ][^\n]{10,})", re.MULTILINE),
            # Matches: "1.1.1 Detail"
            "subsubseccion": re.compile(r"^(\d+\.\d+\.\d+)\s+([A-Za-záéíóúñÁÉÍÓÚÑ][^\n]{5,})", re.MULTILINE),
        }

        # Common patterns for all documents
        self.common_patterns = {
            "numeral": re.compile(r"^(\d+)\.\s+", re.MULTILINE),
            "literal": re.compile(r"^([a-z])\)\s+", re.MULTILINE),
            "anexo": re.compile(r"ANEXO\s+(\d+|[IVXLCDM]+)", re.IGNORECASE),
        }

    def extract_pdf(self, pdf_path: Path) -> Dict:
        """
        Extract text from PDF with structure preservation.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary with document metadata and content
        """
        logger.info(f"Extracting PDF: {pdf_path.name}")

        try:
            # Use pymupdf to extract text (preserves structure better than pymupdf4llm)
            doc = pymupdf.open(str(pdf_path))

            # Extract text from all pages
            text = ""
            for page in doc:
                text += page.get_text()

            doc.close()

            # Extract metadata
            metadata = self._extract_metadata(pdf_path)

            # Detect document type and structure
            doc_type = self._detect_document_type(text)
            structure = self._detect_structure(text, doc_type)

            result = {
                "metadata": metadata,
                "content": text,
                "structure": structure,
                "document_type": doc_type,  # NEW: tipo de documento
                "source_file": str(pdf_path),
            }

            logger.info(
                f"Extracted {len(text)} characters from {pdf_path.name}"
            )
            logger.info(f"Document type detected: {doc_type}")

            return result

        except Exception as e:
            logger.error(f"Error extracting PDF {pdf_path}: {e}")
            raise

    def _extract_metadata(self, pdf_path: Path) -> Dict:
        """
        Extract metadata from PDF filename and content.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary with metadata
        """
        filename = pdf_path.stem

        # Try to parse document type from filename
        doc_type = "unknown"
        doc_number = None
        doc_year = None

        # Match patterns like "acuerdo-unico-comision-rectora-2025-07-15"
        if "acuerdo" in filename.lower():
            doc_type = "Acuerdo"
            year_match = re.search(r"(\d{4})", filename)
            if year_match:
                doc_year = int(year_match.group(1))
        elif "decreto" in filename.lower():
            doc_type = "Decreto"
        elif "resolucion" in filename.lower():
            doc_type = "Resolución"
        elif "tecnico" in filename.lower() or "technical" in filename.lower():
            doc_type = "Documento Técnico"

        # Generate document ID
        doc_id = filename.lower().replace(" ", "_").replace("-", "_")

        metadata = {
            "documento_id": doc_id,
            "documento_nombre": filename.replace("-", " ").replace("_", " ").title(),
            "documento_tipo": doc_type,
            "documento_numero": doc_number,
            "documento_año": doc_year,
            "archivo": pdf_path.name,
        }

        return metadata

    def _detect_document_type(self, text: str) -> str:
        """
        Detect document type based on content patterns.

        Args:
            text: Document text

        Returns:
            Document type: 'legal', 'technical', or 'generic'
        """
        # Count legal patterns
        legal_count = 0
        legal_count += len(self.legal_patterns["articulo"].findall(text))
        legal_count += len(self.legal_patterns["titulo"].findall(text))
        legal_count += len(self.legal_patterns["capitulo"].findall(text))

        # Count technical patterns
        technical_count = 0
        technical_count += len(self.technical_patterns["seccion"].findall(text))
        technical_count += len(self.technical_patterns["subseccion"].findall(text))

        # Determine type based on counts
        if legal_count >= 5:  # Has significant legal structure
            return "legal"
        elif technical_count >= 5:  # Has numbered sections
            return "technical"
        else:
            return "generic"

    def _detect_structure(self, text: str, doc_type: str) -> Dict:
        """
        Detect hierarchical structure in document based on type.

        Args:
            text: Document text
            doc_type: Document type ('legal', 'technical', 'generic')

        Returns:
            Dictionary with detected structure elements
        """
        structure = {
            # Legal structure
            "titulos": [],
            "capitulos": [],
            "articulos": [],
            "paragrafos": [],
            # Technical structure
            "secciones": [],
            "subsecciones": [],
            "subsubsecciones": [],
            # Common
            "anexos": [],
        }

        lines = text.split("\n")

        if doc_type == "legal":
            structure = self._detect_legal_structure(text, lines)
        elif doc_type == "technical":
            structure = self._detect_technical_structure(text, lines)

        # Always detect common elements
        for i, line in enumerate(lines):
            if match := self.common_patterns["anexo"].search(line):
                structure["anexos"].append({
                    "numero": match.group(1),
                    "texto": line.strip(),
                    "line_index": i,
                })

        self._log_structure(structure, doc_type)
        return structure

    def _detect_legal_structure(self, text: str, lines: List[str]) -> Dict:
        """Detect legal document structure."""
        structure = {
            "titulos": [],
            "capitulos": [],
            "articulos": [],
            "paragrafos": [],
            "secciones": [],
            "subsecciones": [],
            "subsubsecciones": [],
            "anexos": [],
        }

        for i, line in enumerate(lines):
            # Detect titles
            if match := self.legal_patterns["titulo"].search(line):
                numero = match.group(1)
                # Try to extract name from same line first
                nombre = self._extract_nombre(line, "TÍTULO", numero)

                # If empty, try next line (common in PDFs)
                if not nombre and i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    # Check if next line looks like a title (all caps, reasonable length)
                    if next_line and next_line.isupper() and 3 < len(next_line) < 100:
                        nombre = next_line

                structure["titulos"].append({
                    "numero": numero,
                    "nombre": nombre,
                    "texto": line.strip(),
                    "line_index": i,
                })

            # Detect chapters
            if match := self.legal_patterns["capitulo"].search(line):
                numero = match.group(1)
                nombre = self._extract_nombre(line, "CAPÍTULO", numero)

                # If empty, try next line
                if not nombre and i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line and next_line.isupper() and 3 < len(next_line) < 150:
                        nombre = next_line

                structure["capitulos"].append({
                    "numero": numero,
                    "nombre": nombre,
                    "texto": line.strip(),
                    "line_index": i,
                })

            # Detect articles
            if match := self.legal_patterns["articulo"].search(line):
                numero = match.group(1)
                nombre = self._extract_nombre(line, "ARTÍCULO", numero)

                # If empty, try next line (but be more flexible for articles)
                if not nombre and i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    # Articles might have title case or mixed case
                    if next_line and len(next_line) > 3:
                        nombre = next_line

                structure["articulos"].append({
                    "numero": numero,
                    "nombre": nombre,
                    "texto": line.strip(),
                    "line_index": i,
                })

            # Detect paragraphs
            if match := self.legal_patterns["paragrafo"].search(line):
                numero = match.group(1)
                nombre = self._extract_nombre(line, "PARÁGRAFO", numero)

                # If empty, try next line
                if not nombre and i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line and len(next_line) > 3:
                        nombre = next_line

                structure["paragrafos"].append({
                    "numero": numero,
                    "nombre": nombre,
                    "texto": line.strip(),
                    "line_index": i,
                })

        return structure

    def _detect_technical_structure(self, text: str, lines: List[str]) -> Dict:
        """Detect technical document structure (numbered sections)."""
        structure = {
            "titulos": [],
            "capitulos": [],
            "articulos": [],
            "paragrafos": [],
            "secciones": [],
            "subsecciones": [],
            "subsubsecciones": [],
            "anexos": [],
        }

        # Detect sections (e.g., "1. SECTION NAME")
        for match in self.technical_patterns["seccion"].finditer(text):
            line_index = text[:match.start()].count('\n')
            structure["secciones"].append({
                "numero": match.group(1),
                "nombre": match.group(2).strip(),  # Changed from "titulo" to "nombre" for consistency
                "texto": match.group(0).strip(),
                "line_index": line_index,
            })

        # Detect subsections (e.g., "1.1 Subsection")
        for match in self.technical_patterns["subseccion"].finditer(text):
            line_index = text[:match.start()].count('\n')
            structure["subsecciones"].append({
                "numero": match.group(1),
                "nombre": match.group(2).strip(),  # Changed from "titulo" to "nombre"
                "texto": match.group(0).strip(),
                "line_index": line_index,
            })

        # Detect sub-subsections (e.g., "1.1.1 Detail")
        for match in self.technical_patterns["subsubseccion"].finditer(text):
            line_index = text[:match.start()].count('\n')
            structure["subsubsecciones"].append({
                "numero": match.group(1),
                "nombre": match.group(2).strip(),  # Changed from "titulo" to "nombre"
                "texto": match.group(0).strip(),
                "line_index": line_index,
            })

        return structure

    def _extract_nombre(self, line: str, prefix: str, numero: str) -> str:
        """
        Extract name/description from hierarchical element.

        Args:
            line: Full line text
            prefix: Element prefix (TÍTULO, CAPÍTULO, etc.)
            numero: Element number

        Returns:
            Extracted name or empty string
        """
        # Remove prefix and number to get just the name
        # Example: "TÍTULO 4 PROYECTOS DE INVERSIÓN" -> "PROYECTOS DE INVERSIÓN"
        pattern = rf"{prefix}\s+{re.escape(str(numero))}\s*[-:\.]?\s*"
        nombre = re.sub(pattern, "", line, flags=re.IGNORECASE).strip()

        # Also try with roman numerals if numero contains them
        if numero.upper() in ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X']:
            pattern_roman = rf"{prefix}\s+[IVXLCDM]+\s*[-:\.]?\s*"
            nombre = re.sub(pattern_roman, "", line, flags=re.IGNORECASE).strip()

        # Clean up any remaining special chars at start
        nombre = re.sub(r"^[-:\.\s]+", "", nombre).strip()

        return nombre if nombre and nombre != line.strip() else ""

    def _log_structure(self, structure: Dict, doc_type: str):
        """Log detected structure."""
        if doc_type == "legal":
            logger.info(
                f"Legal structure: {len(structure['titulos'])} títulos, "
                f"{len(structure['capitulos'])} capítulos, "
                f"{len(structure['articulos'])} artículos, "
                f"{len(structure['paragrafos'])} parágrafos"
            )
        elif doc_type == "technical":
            logger.info(
                f"Technical structure: {len(structure['secciones'])} secciones, "
                f"{len(structure['subsecciones'])} subsecciones, "
                f"{len(structure['subsubsecciones'])} sub-subsecciones"
            )
        else:
            logger.info("Generic document structure")

    def extract_page_numbers(self, text: str) -> List[int]:
        """
        Extract page numbers from text.

        Args:
            text: Document text

        Returns:
            List of page numbers found
        """
        # Try to find page number patterns
        page_pattern = re.compile(r"(?:Página|Page|Pág\.?)\s+(\d+)", re.IGNORECASE)
        matches = page_pattern.findall(text)
        return [int(m) for m in matches]


def extract_single_pdf(pdf_path: Path) -> Dict:
    """
    Convenience function to extract a single PDF.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Extracted document dictionary
    """
    extractor = PDFExtractor()
    return extractor.extract_pdf(pdf_path)


def extract_all_pdfs(data_dir: Path) -> List[Dict]:
    """
    Extract all PDFs from a directory.

    Args:
        data_dir: Directory containing PDF files

    Returns:
        List of extracted documents
    """
    extractor = PDFExtractor()
    documents = []

    pdf_files = list(data_dir.glob("*.pdf"))
    logger.info(f"Found {len(pdf_files)} PDF files in {data_dir}")

    for pdf_file in pdf_files:
        try:
            doc = extractor.extract_pdf(pdf_file)
            documents.append(doc)
        except Exception as e:
            logger.error(f"Failed to extract {pdf_file.name}: {e}")
            continue

    logger.info(f"Successfully extracted {len(documents)} documents")
    return documents
