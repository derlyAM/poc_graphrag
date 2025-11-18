"""
Chunker module.
Creates hierarchical chunks from documents respecting legal structure.

NUEVA ARQUITECTURA: Utiliza DocumentHierarchyProcessor para procesamiento unificado.
"""
import re
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger
import tiktoken

from src.ingest.document_hierarchy_processor import DocumentHierarchyProcessor


class HierarchicalChunker:
    """Creates chunks respecting document hierarchy."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        """
        Initialize chunker.

        Args:
            chunk_size: Maximum tokens per chunk
            chunk_overlap: Overlap in words between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

        # NUEVO: Procesador unificado de jerarqu\u00edas
        self.hierarchy_processor = DocumentHierarchyProcessor(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

    def chunk_document(self, document: Dict) -> List[Dict]:
        """
        Chunk document preserving hierarchy.

        NUEVA IMPLEMENTACIÓN: Usa DocumentHierarchyProcessor universal.

        Args:
            document: Document dictionary from PDF extractor

        Returns:
            List of chunks with metadata
        """
        logger.info(f"Chunking document: {document['metadata']['documento_nombre']}")

        structure = document["structure"]
        doc_type = document.get("document_type", "generic")

        # Verificar si el documento tiene jerarquía
        has_hierarchy = self._has_hierarchy(structure)

        if has_hierarchy:
            # NUEVO: Usar procesador unificado para TODOS los tipos con jerarquía
            logger.info("Usando procesador jerárquico unificado")
            chunks = self.hierarchy_processor.process_document(document)
        else:
            # Fallback: chunking simple por tamaño
            logger.warning("No se detectó jerarquía, usando chunking por tamaño")
            chunks = self._chunk_by_size(
                document["content"],
                document["metadata"],
                doc_type
            )
            # Agregar linking secuencial
            chunks = self._link_chunks(chunks)

        logger.info(f"Created {len(chunks)} chunks for {doc_type} document")

        return chunks

    def _has_hierarchy(self, structure: Dict) -> bool:
        """
        Verifica si un documento tiene estructura jerárquica.

        Args:
            structure: Estructura detectada del documento

        Returns:
            True si tiene jerarquía, False si no
        """
        # Verificar si hay algún elemento estructural
        hierarchical_keys = [
            "titulos", "capitulos", "articulos", "paragrafos",
            "secciones", "subsecciones", "subsubsecciones",
            "anexos"
        ]

        for key in hierarchical_keys:
            if structure.get(key) and len(structure[key]) > 0:
                return True

        return False

    def _chunk_legal_document(
        self, content: str, structure: Dict, metadata: Dict
    ) -> List[Dict]:
        """
        Chunk legal document with full hierarchical graph structure.

        Creates chunks for ALL levels:
        - Level 0: Document
        - Level 1: Títulos
        - Level 2: Capítulos
        - Level 3: Artículos
        - Level 5: Anexos

        Args:
            content: Document text
            structure: Detected structure
            metadata: Document metadata

        Returns:
            List of chunks with full graph relationships
        """
        chunks = []
        chunk_map = {}  # For fast lookup by ID
        lines = content.split("\n")

        articulos = structure["articulos"]
        titulos = structure["titulos"]
        capitulos = structure["capitulos"]
        anexos = structure.get("anexos", [])

        # Build name mappings
        titulo_nombres = self._build_name_mapping(titulos)
        capitulo_nombres = self._build_name_mapping(capitulos)

        # LEVEL 0: DOCUMENT NODE
        doc_text = f"{metadata['documento_nombre']}\n\n" + content[:500]  # Summary
        doc_chunk = self._create_chunk(
            text=doc_text,
            metadata=metadata,
            doc_type="legal",
            nivel_jerarquico=0,
            parent_id=None,
            hierarchy_path=metadata['documento_nombre'],
        )
        chunks.append(doc_chunk)
        chunk_map[doc_chunk["chunk_id"]] = doc_chunk
        doc_id = doc_chunk["chunk_id"]

        logger.info(f"Created document node (Level 0)")

        # LEVEL 1: TÍTULOS
        for titulo in titulos:
            titulo_nombre = titulo.get("nombre", f"Título {titulo['numero']}")
            titulo_text = f"TÍTULO {titulo['numero']} - {titulo_nombre}\n\n{titulo.get('texto', '')}"

            hierarchy_path = self._build_hierarchy_path([
                metadata['documento_nombre'],
                f"Título {titulo['numero']} - {titulo_nombre}"
            ])

            titulo_chunk = self._create_chunk(
                text=titulo_text,
                metadata=metadata,
                titulo=titulo["numero"],
                titulo_nombre=titulo_nombre,
                doc_type="legal",
                nivel_jerarquico=1,
                parent_id=doc_id,
                hierarchy_path=hierarchy_path,
            )
            chunks.append(titulo_chunk)
            chunk_map[titulo_chunk["chunk_id"]] = titulo_chunk

            # Link to parent
            doc_chunk["children_ids"].append(titulo_chunk["chunk_id"])

        logger.info(f"Created {len(titulos)} título nodes (Level 1)")

        # LEVEL 2: CAPÍTULOS
        for capitulo in capitulos:
            # Find parent título
            current_titulo = self._find_current_context(capitulo["line_index"], titulos)
            titulo_nombre = titulo_nombres.get(current_titulo, "")

            # Find parent chunk
            parent_chunk = next(
                (c for c in chunks if c.get("titulo") == current_titulo and c.get("nivel_jerarquico") == 1),
                doc_chunk
            )

            capitulo_nombre = capitulo.get("nombre", f"Capítulo {capitulo['numero']}")
            capitulo_text = f"CAPÍTULO {capitulo['numero']} - {capitulo_nombre}\n\n{capitulo.get('texto', '')}"

            hierarchy_path = self._build_hierarchy_path([
                metadata['documento_nombre'],
                f"Título {current_titulo} - {titulo_nombre}" if current_titulo else None,
                f"Capítulo {capitulo['numero']} - {capitulo_nombre}"
            ])

            capitulo_chunk = self._create_chunk(
                text=capitulo_text,
                metadata=metadata,
                titulo=current_titulo,
                titulo_nombre=titulo_nombre,
                capitulo=capitulo["numero"],
                capitulo_nombre=capitulo_nombre,
                doc_type="legal",
                nivel_jerarquico=2,
                parent_id=parent_chunk["chunk_id"],
                hierarchy_path=hierarchy_path,
            )
            chunks.append(capitulo_chunk)
            chunk_map[capitulo_chunk["chunk_id"]] = capitulo_chunk

            # Link to parent
            parent_chunk["children_ids"].append(capitulo_chunk["chunk_id"])

        logger.info(f"Created {len(capitulos)} capítulo nodes (Level 2)")

        # LEVEL 3: ARTÍCULOS (with intelligent chunking)
        for i, articulo in enumerate(articulos):
            start_line = articulo["line_index"]
            end_line = (
                articulos[i + 1]["line_index"]
                if i + 1 < len(articulos)
                else len(lines)
            )

            # Find context
            current_titulo = self._find_current_context(start_line, titulos)
            current_capitulo = self._find_current_context(start_line, capitulos)

            # Find parent chunk (capítulo or título)
            parent_chunk = next(
                (c for c in chunks if c.get("capitulo") == current_capitulo and c.get("nivel_jerarquico") == 2),
                next(
                    (c for c in chunks if c.get("titulo") == current_titulo and c.get("nivel_jerarquico") == 1),
                    doc_chunk
                )
            )

            # Get names
            titulo_nombre = titulo_nombres.get(current_titulo)
            capitulo_nombre = capitulo_nombres.get(current_capitulo)

            # Extract article text
            article_lines = lines[start_line:end_line]
            article_text = "\n".join(article_lines).strip()

            # Build hierarchy path
            hierarchy_path = self._build_hierarchy_path([
                metadata['documento_nombre'],
                f"Título {current_titulo} - {titulo_nombre}" if current_titulo and titulo_nombre else None,
                f"Capítulo {current_capitulo} - {capitulo_nombre}" if current_capitulo and capitulo_nombre else None,
                f"Artículo {articulo['numero']}"
            ])

            # Count tokens
            token_count = self._count_tokens(article_text)

            # INTELLIGENT ADAPTIVE CHUNKING
            if token_count <= 500:
                # Small article: single chunk
                chunk = self._create_chunk(
                    text=article_text,
                    metadata=metadata,
                    articulo=articulo["numero"],
                    titulo=current_titulo,
                    capitulo=current_capitulo,
                    titulo_nombre=titulo_nombre,
                    capitulo_nombre=capitulo_nombre,
                    doc_type="legal",
                    nivel_jerarquico=3,
                    parent_id=parent_chunk["chunk_id"],
                    hierarchy_path=hierarchy_path,
                )
                chunks.append(chunk)
                parent_chunk["children_ids"].append(chunk["chunk_id"])
            else:
                # Large article: split but maintain hierarchy
                max_size = 800 if token_count > 2000 else self.chunk_size
                overlap = 100 if token_count > 2000 else self.chunk_overlap

                sub_chunks = self._split_long_text(
                    article_text, articulo["numero"], metadata,
                    titulo=current_titulo, capitulo=current_capitulo,
                    titulo_nombre=titulo_nombre, capitulo_nombre=capitulo_nombre,
                    doc_type="legal",
                    max_chunk_size=max_size,
                    overlap=overlap,
                    nivel_jerarquico=3,
                    parent_id=parent_chunk["chunk_id"],
                    hierarchy_path=hierarchy_path,
                )
                for sub_chunk in sub_chunks:
                    chunks.append(sub_chunk)
                    parent_chunk["children_ids"].append(sub_chunk["chunk_id"])

        logger.info(f"Created chunks for {len(articulos)} artículos (Level 3)")

        # LEVEL 5: ANEXOS
        if anexos:
            logger.info(f"Processing {len(anexos)} anexos")
            anexo_chunks = self._chunk_anexos_hierarchical(
                content, anexos, metadata, lines, doc_chunk
            )
            chunks.extend(anexo_chunks)

        logger.info(f"Total hierarchical chunks created: {len(chunks)}")
        return chunks

    def _find_current_context(
        self, current_line: int, context_list: List[Dict]
    ) -> Optional[str]:
        """
        Find the most recent context element before current line.

        Args:
            current_line: Current line index
            context_list: List of context elements (títulos, capítulos, etc.)

        Returns:
            Context number or None
        """
        current_context = None
        for context in context_list:
            if context["line_index"] < current_line:
                current_context = context["numero"]
            else:
                break
        return current_context

    def _build_hierarchy_index(
        self, titulos: List[Dict], capitulos: List[Dict]
    ) -> Dict:
        """Build index of hierarchical elements for fast lookup."""
        return {
            "titulos": sorted(titulos, key=lambda x: x["line_index"]),
            "capitulos": sorted(capitulos, key=lambda x: x["line_index"]),
        }

    def _build_name_mapping(self, elements: List[Dict]) -> Dict[str, str]:
        """
        Build mapping from element number to element name.

        Args:
            elements: List of hierarchical elements (títulos, capítulos, etc.)

        Returns:
            Dictionary mapping numero -> nombre
        """
        mapping = {}
        for elem in elements:
            numero = elem.get("numero")
            nombre = elem.get("nombre", "")
            if numero and nombre:
                mapping[numero] = nombre
        return mapping

    def _build_hierarchy_path(self, parts: List[str]) -> str:
        """
        Build hierarchy path from parts.

        Args:
            parts: List of hierarchy parts

        Returns:
            Formatted hierarchy path
        """
        return " > ".join(filter(None, parts))

    def _get_articulos_de_capitulo(
        self, capitulo_numero: str, articulos: List[Dict], capitulos: List[Dict]
    ) -> List[Dict]:
        """
        Get articles belonging to a specific chapter.

        Args:
            capitulo_numero: Chapter number
            articulos: List of all articles
            capitulos: List of all chapters

        Returns:
            List of articles in this chapter
        """
        # Find chapter start and end lines
        cap_index = next(
            (i for i, c in enumerate(capitulos) if c["numero"] == capitulo_numero),
            None
        )
        if cap_index is None:
            return []

        cap_start = capitulos[cap_index]["line_index"]
        cap_end = (
            capitulos[cap_index + 1]["line_index"]
            if cap_index + 1 < len(capitulos)
            else float('inf')
        )

        # Filter articles in range
        return [
            art for art in articulos
            if cap_start <= art["line_index"] < cap_end
        ]

    def _get_capitulos_de_titulo(
        self, titulo_numero: str, capitulos: List[Dict], titulos: List[Dict]
    ) -> List[Dict]:
        """
        Get chapters belonging to a specific title.

        Args:
            titulo_numero: Title number
            capitulos: List of all chapters
            titulos: List of all titles

        Returns:
            List of chapters in this title
        """
        # Find title start and end lines
        tit_index = next(
            (i for i, t in enumerate(titulos) if t["numero"] == titulo_numero),
            None
        )
        if tit_index is None:
            return []

        tit_start = titulos[tit_index]["line_index"]
        tit_end = (
            titulos[tit_index + 1]["line_index"]
            if tit_index + 1 < len(titulos)
            else float('inf')
        )

        # Filter chapters in range
        return [
            cap for cap in capitulos
            if tit_start <= cap["line_index"] < tit_end
        ]

    def _chunk_anexos_hierarchical(
        self, content: str, anexos: List[Dict], metadata: Dict, lines: List[str], doc_chunk: Dict
    ) -> List[Dict]:
        """
        Chunk anexos (appendices) with hierarchical structure.

        Args:
            content: Full document text
            anexos: List of detected anexos
            metadata: Document metadata
            lines: Pre-split lines
            doc_chunk: Document root chunk

        Returns:
            List of anexo chunks
        """
        chunks = []

        for i, anexo in enumerate(anexos):
            start_line = anexo["line_index"]

            # Find end line (next anexo or end of document)
            if i + 1 < len(anexos):
                end_line = anexos[i + 1]["line_index"]
            else:
                end_line = len(lines)

            # Extract anexo text
            anexo_lines = lines[start_line:end_line]
            anexo_text = "\n".join(anexo_lines).strip()

            # Build hierarchy path
            hierarchy_path = self._build_hierarchy_path([
                metadata['documento_nombre'],
                f"Anexo {anexo['numero']}"
            ])

            # Count tokens
            token_count = self._count_tokens(anexo_text)

            # If anexo is too long, split it into sub-chunks
            if token_count > self.chunk_size:
                logger.info(f"Anexo {anexo['numero']} is large ({token_count} tokens), splitting")
                sub_chunks = self._split_long_text(
                    anexo_text,
                    articulo=None,
                    metadata=metadata,
                    anexo_numero=anexo["numero"],
                    doc_type="legal",
                    max_chunk_size=800,
                    overlap=100,
                    nivel_jerarquico=5,
                    parent_id=doc_chunk["chunk_id"],
                    hierarchy_path=hierarchy_path,
                )
                for sub_chunk in sub_chunks:
                    chunks.append(sub_chunk)
                    doc_chunk["children_ids"].append(sub_chunk["chunk_id"])
            else:
                # Create single chunk for anexo
                chunk = self._create_chunk(
                    text=anexo_text,
                    metadata=metadata,
                    anexo_numero=anexo["numero"],
                    doc_type="legal",
                    nivel_jerarquico=5,
                    parent_id=doc_chunk["chunk_id"],
                    hierarchy_path=hierarchy_path,
                )
                chunks.append(chunk)
                doc_chunk["children_ids"].append(chunk["chunk_id"])

        logger.info(f"Created {len(chunks)} chunks from {len(anexos)} anexos")
        return chunks

    def _chunk_anexos(
        self, content: str, anexos: List[Dict], metadata: Dict, lines: List[str]
    ) -> List[Dict]:
        """
        DEPRECATED: Use _chunk_anexos_hierarchical instead.

        Chunk anexos (appendices) into searchable chunks.

        Args:
            content: Full document text
            anexos: List of detected anexos
            metadata: Document metadata
            lines: Pre-split lines

        Returns:
            List of anexo chunks
        """
        chunks = []

        for i, anexo in enumerate(anexos):
            start_line = anexo["line_index"]

            # Find end line (next anexo or end of document)
            if i + 1 < len(anexos):
                end_line = anexos[i + 1]["line_index"]
            else:
                end_line = len(lines)

            # Extract anexo text
            anexo_lines = lines[start_line:end_line]
            anexo_text = "\n".join(anexo_lines).strip()

            # Count tokens
            token_count = self._count_tokens(anexo_text)

            # If anexo is too long, split it into sub-chunks
            if token_count > self.chunk_size:
                logger.info(f"Anexo {anexo['numero']} is large ({token_count} tokens), splitting")
                sub_chunks = self._split_long_text(
                    anexo_text,
                    articulo=None,
                    metadata=metadata,
                    anexo_numero=anexo["numero"],
                    doc_type="legal",
                    max_chunk_size=800,
                    overlap=100
                )
                chunks.extend(sub_chunks)
            else:
                # Create single chunk for anexo
                chunk = self._create_chunk(
                    text=anexo_text,
                    metadata=metadata,
                    anexo_numero=anexo["numero"],
                    doc_type="legal",
                )
                chunks.append(chunk)

        logger.info(f"Created {len(chunks)} chunks from {len(anexos)} anexos")
        return chunks

    def _chunk_technical_document(
        self, content: str, structure: Dict, metadata: Dict
    ) -> List[Dict]:
        """
        Chunk technical document by sections with dynamic context.

        Args:
            content: Document text
            structure: Detected structure
            metadata: Document metadata

        Returns:
            List of chunks
        """
        chunks = []
        lines = content.split("\n")
        secciones = structure["secciones"]
        subsecciones = structure["subsecciones"]

        # Combine all sectioning elements and sort by line
        all_sections = []

        for sec in secciones:
            all_sections.append({
                "type": "seccion",
                "numero": sec["numero"],
                "line_index": sec["line_index"],
                "texto": sec.get("titulo", sec["texto"]),
            })

        for subsec in subsecciones:
            all_sections.append({
                "type": "subseccion",
                "numero": subsec["numero"],
                "line_index": subsec["line_index"],
                "texto": subsec.get("titulo", subsec["texto"]),
            })

        all_sections.sort(key=lambda x: x["line_index"])

        # Chunk by sections
        for i, section in enumerate(all_sections):
            start_line = section["line_index"]
            end_line = (
                all_sections[i + 1]["line_index"]
                if i + 1 < len(all_sections)
                else len(lines)
            )

            # DYNAMIC CONTEXT: Find current section and subsection
            current_seccion = None
            current_subseccion = None

            if section["type"] == "seccion":
                current_seccion = section["numero"]
            else:  # subseccion
                current_subseccion = section["numero"]
                # Find parent section
                current_seccion = self._find_current_context(start_line, secciones)

            # Extract section text
            section_lines = lines[start_line:end_line]
            section_text = "\n".join(section_lines).strip()

            # Count tokens
            token_count = self._count_tokens(section_text)

            # If section is too long, split it
            if token_count > self.chunk_size:
                sub_chunks = self._split_long_text(
                    section_text, None, metadata,
                    seccion=current_seccion,
                    subseccion=current_subseccion,
                    doc_type="technical"
                )
                chunks.extend(sub_chunks)
            else:
                # Create single chunk for section
                chunk = self._create_chunk(
                    text=section_text,
                    metadata=metadata,
                    seccion=current_seccion,
                    subseccion=current_subseccion,
                    doc_type="technical",
                )
                chunks.append(chunk)

        return chunks

    def _chunk_by_size(self, content: str, metadata: Dict, doc_type: str = "generic") -> List[Dict]:
        """
        Fallback: chunk by fixed size.

        Args:
            content: Document text
            metadata: Document metadata
            doc_type: Document type

        Returns:
            List of chunks
        """
        chunks = []
        words = content.split()
        chunk_size_words = self.chunk_size  # Approximate

        for i in range(0, len(words), chunk_size_words - self.chunk_overlap):
            chunk_words = words[i : i + chunk_size_words]
            chunk_text = " ".join(chunk_words)

            chunk = self._create_chunk(
                text=chunk_text,
                metadata=metadata,
                doc_type=doc_type,
            )
            chunks.append(chunk)

        return chunks

    def _split_long_text(
        self,
        text: str,
        articulo: Optional[str],
        metadata: Dict,
        titulo: Optional[str] = None,
        capitulo: Optional[str] = None,
        titulo_nombre: Optional[str] = None,
        capitulo_nombre: Optional[str] = None,
        seccion: Optional[str] = None,
        subseccion: Optional[str] = None,
        anexo_numero: Optional[str] = None,
        doc_type: str = "legal",
        max_chunk_size: Optional[int] = None,
        overlap: Optional[int] = None,
        nivel_jerarquico: Optional[int] = None,
        parent_id: Optional[str] = None,
        hierarchy_path: Optional[str] = None,
    ) -> List[Dict]:
        """
        Split long text into smaller chunks.

        Args:
            text: Text to split
            articulo: Article number (for legal docs)
            metadata: Document metadata
            titulo: Title number
            capitulo: Chapter number
            titulo_nombre: Title name
            capitulo_nombre: Chapter name
            seccion: Section number (for technical docs)
            subseccion: Subsection number
            anexo_numero: Anexo number
            doc_type: Document type
            max_chunk_size: Override default chunk size
            overlap: Override default overlap

        Returns:
            List of sub-chunks
        """
        chunks = []

        # Use custom size/overlap if provided
        chunk_size = max_chunk_size if max_chunk_size else self.chunk_size
        chunk_overlap = overlap if overlap else self.chunk_overlap

        # Try to split by paragraphs first
        paragraphs = text.split("\n\n")

        current_chunk_text = ""
        current_tokens = 0

        for para in paragraphs:
            para_tokens = self._count_tokens(para)

            if current_tokens + para_tokens > chunk_size:
                # Save current chunk
                if current_chunk_text:
                    chunk = self._create_chunk(
                        text=current_chunk_text.strip(),
                        metadata=metadata,
                        articulo=articulo,
                        titulo=titulo,
                        capitulo=capitulo,
                        titulo_nombre=titulo_nombre,
                        capitulo_nombre=capitulo_nombre,
                        seccion=seccion,
                        subseccion=subseccion,
                        anexo_numero=anexo_numero,
                        doc_type=doc_type,
                        nivel_jerarquico=nivel_jerarquico,
                        parent_id=parent_id,
                        hierarchy_path=hierarchy_path,
                    )
                    chunks.append(chunk)

                # Start new chunk
                current_chunk_text = para
                current_tokens = para_tokens
            else:
                current_chunk_text += "\n\n" + para
                current_tokens += para_tokens

        # Add last chunk
        if current_chunk_text:
            chunk = self._create_chunk(
                text=current_chunk_text.strip(),
                metadata=metadata,
                articulo=articulo,
                titulo=titulo,
                capitulo=capitulo,
                titulo_nombre=titulo_nombre,
                capitulo_nombre=capitulo_nombre,
                seccion=seccion,
                subseccion=subseccion,
                anexo_numero=anexo_numero,
                doc_type=doc_type,
                nivel_jerarquico=nivel_jerarquico,
                parent_id=parent_id,
                hierarchy_path=hierarchy_path,
            )
            chunks.append(chunk)

        return chunks

    def _create_chunk(
        self,
        text: str,
        metadata: Dict,
        articulo: Optional[str] = None,
        paragrafo: Optional[str] = None,
        titulo: Optional[str] = None,
        capitulo: Optional[str] = None,
        titulo_nombre: Optional[str] = None,
        capitulo_nombre: Optional[str] = None,
        seccion: Optional[str] = None,
        subseccion: Optional[str] = None,
        anexo_numero: Optional[str] = None,
        doc_type: str = "legal",
        nivel_jerarquico: Optional[int] = None,
        parent_id: Optional[str] = None,
        hierarchy_path: Optional[str] = None,
    ) -> Dict:
        """
        Create chunk with full metadata.

        Args:
            text: Chunk text
            metadata: Document metadata
            articulo: Article number
            paragrafo: Paragraph number
            titulo: Title number
            capitulo: Chapter number
            titulo_nombre: Title name
            capitulo_nombre: Chapter name
            seccion: Section number (for technical docs)
            subseccion: Subsection number
            anexo_numero: Anexo number
            doc_type: Document type

        Returns:
            Chunk dictionary
        """
        chunk_id = str(uuid.uuid4())

        # Generate citation
        citation = self._generate_citation(
            metadata=metadata,
            articulo=articulo,
            paragrafo=paragrafo,
            seccion=seccion,
            subseccion=subseccion,
            anexo_numero=anexo_numero,
            doc_type=doc_type,
        )

        chunk = {
            # Identification
            "chunk_id": chunk_id,
            "documento_id": metadata["documento_id"],
            "documento_nombre": metadata["documento_nombre"],
            # Legal hierarchy
            "articulo": articulo,
            "paragrafo": paragrafo,
            "titulo": titulo,
            "capitulo": capitulo,
            "titulo_nombre": titulo_nombre,
            "capitulo_nombre": capitulo_nombre,
            # Technical hierarchy
            "seccion": seccion,
            "subseccion": subseccion,
            # Anexos
            "anexo_numero": anexo_numero,
            "es_anexo": bool(anexo_numero),
            # Document type
            "tipo_documento": doc_type,
            # Área de conocimiento (v1.3.0 - separación por dominio)
            "area": metadata.get("area", "general"),
            # GRAPH FIELDS (NEW - FASE 1)
            "nivel_jerarquico": nivel_jerarquico,  # 0=doc, 1=titulo, 2=cap, 3=art, 4=para, 5=anexo
            "parent_id": parent_id,  # UUID del chunk padre
            "children_ids": [],  # Se llenará después al vincular
            "hierarchy_path": hierarchy_path,  # Path completo en el grafo
            # Content
            "texto": text,
            "longitud_tokens": self._count_tokens(text),
            # Context (will be filled later)
            "chunk_anterior_id": None,
            "chunk_siguiente_id": None,
            # Citation
            "citacion_corta": citation,
            # Processing
            "fecha_procesamiento": datetime.now().isoformat(),
            "tipo_contenido": self._detect_content_type(text),
        }

        return chunk

    def _generate_citation(
        self,
        metadata: Dict,
        articulo: Optional[str] = None,
        paragrafo: Optional[str] = None,
        seccion: Optional[str] = None,
        subseccion: Optional[str] = None,
        anexo_numero: Optional[str] = None,
        doc_type: str = "legal",
    ) -> str:
        """
        Generate citation based on document type.

        Args:
            metadata: Document metadata
            articulo: Article number
            paragrafo: Paragraph number
            seccion: Section number
            subseccion: Subsection number
            anexo_numero: Anexo number
            doc_type: Document type

        Returns:
            Citation string
        """
        parts = []

        # Legal citations
        if doc_type == "legal":
            if anexo_numero:
                parts.append(f"Anexo {anexo_numero}")
            if articulo:
                parts.append(f"Art. {articulo}")
            if paragrafo:
                parts.append(f"Par. {paragrafo}")

        # Technical citations
        elif doc_type == "technical":
            if subseccion:
                parts.append(f"Sec. {subseccion}")
            elif seccion:
                parts.append(f"Sec. {seccion}")

        # Add document reference
        doc_ref = metadata["documento_tipo"]
        if metadata.get("documento_numero"):
            doc_ref += f" {metadata['documento_numero']}"
        if metadata.get("documento_año"):
            doc_ref += f"/{metadata['documento_año']}"

        if not doc_ref or doc_ref == metadata["documento_tipo"]:
            doc_ref = metadata["documento_nombre"]

        parts.append(doc_ref)

        return ", ".join(parts) if parts else doc_ref

    def _detect_content_type(self, text: str) -> str:
        """
        Detect content type of chunk.

        Args:
            text: Chunk text

        Returns:
            Content type
        """
        text_lower = text.lower()

        # Check for definitions
        if any(
            phrase in text_lower
            for phrase in ["se entiende por", "se define", "significa"]
        ):
            return "definicion"

        # Check for procedures
        if any(
            phrase in text_lower
            for phrase in ["deberá", "debe", "procedimiento", "proceso"]
        ):
            return "procedimiento"

        # Check for requirements
        if any(
            phrase in text_lower
            for phrase in ["requisito", "deberá cumplir", "debe contar"]
        ):
            return "requisito"

        # Check for articles
        if text.startswith("ART") or "ARTÍCULO" in text[:50].upper():
            return "articulo"

        return "general"

    def _count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: Text to count

        Returns:
            Number of tokens
        """
        try:
            return len(self.tokenizer.encode(text))
        except Exception:
            # Fallback: approximate by words
            return len(text.split()) * 1.3

    def _link_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """
        Link chunks sequentially.

        Args:
            chunks: List of chunks

        Returns:
            Chunks with prev/next IDs
        """
        for i, chunk in enumerate(chunks):
            if i > 0:
                chunk["chunk_anterior_id"] = chunks[i - 1]["chunk_id"]
            if i < len(chunks) - 1:
                chunk["chunk_siguiente_id"] = chunks[i + 1]["chunk_id"]

        return chunks


def chunk_documents(documents: List[Dict], chunk_size: int = 500) -> List[Dict]:
    """
    Convenience function to chunk multiple documents.

    Args:
        documents: List of documents from PDF extractor
        chunk_size: Maximum tokens per chunk

    Returns:
        List of all chunks
    """
    chunker = HierarchicalChunker(chunk_size=chunk_size)
    all_chunks = []

    for doc in documents:
        chunks = chunker.chunk_document(doc)
        all_chunks.extend(chunks)

    logger.info(f"Created {len(all_chunks)} total chunks from {len(documents)} documents")

    return all_chunks
