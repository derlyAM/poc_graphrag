"""
Procesador universal de jerarquías documentales.
Maneja documentos legales, técnicos, híbridos y cualquier tipo con estructura jerárquica.
"""
import uuid
from datetime import datetime
from typing import Dict, List, Set, Optional, Tuple
from loguru import logger
import tiktoken

from src.ingest.hierarchy_config import HierarchyConfig


class DocumentHierarchyProcessor:
    """
    Procesador universal para crear grafos jerárquicos de documentos.

    Funciona con CUALQUIER tipo de documento que tenga estructura jerárquica:
    - Documentos legales (títulos, capítulos, artículos)
    - Documentos técnicos (secciones, subsecciones)
    - Documentos híbridos
    - Documentos financieros, ambientales, etc.
    """

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        """
        Inicializar procesador.

        Args:
            chunk_size: Tamaño máximo de tokens por chunk
            chunk_overlap: Solapamiento en palabras entre chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.config = HierarchyConfig()

    def _normalize_text(self, text: str) -> str:
        """
        Normaliza texto para búsqueda.

        - Lowercase
        - Sin tildes
        - Sin caracteres especiales

        Args:
            text: Texto a normalizar

        Returns:
            Texto normalizado
        """
        import unicodedata
        import re

        if not text:
            return ""

        # Lowercase
        text = text.lower()

        # Remover tildes
        text = unicodedata.normalize('NFKD', text)
        text = text.encode('ASCII', 'ignore').decode('ASCII')

        # Remover caracteres especiales (mantener letras, números, espacios)
        text = re.sub(r'[^a-z0-9\s]', '', text)

        # Espacios simples
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def process_document(self, document: Dict) -> List[Dict]:
        """
        Procesa un documento y genera chunks con estructura jerárquica completa.

        Args:
            document: Diccionario con:
                - content: Texto completo
                - structure: Elementos estructurales detectados
                - metadata: Metadatos del documento
                - document_type: Tipo de documento

        Returns:
            Lista de chunks con grafo jerárquico completo
        """
        structure = document["structure"]
        metadata = document["metadata"]
        content = document["content"]
        doc_type = document.get("document_type", "generic")

        logger.info(f"Procesando documento: {metadata['documento_nombre']} (tipo: {doc_type})")

        chunks = []
        lines = content.split("\n")

        # === PASO 1: DETECTAR NIVELES PRESENTES ===
        detected_levels = self._detect_levels(structure)
        logger.info(f"Niveles jerárquicos detectados: {sorted(detected_levels)}")

        if not detected_levels or detected_levels == {0}:
            logger.warning("No se detectó jerarquía, documento será procesado sin estructura")
            # Crear solo nodo raíz y retornar
            doc_chunk = self._create_root_node(metadata, content)
            return [doc_chunk]

        # === PASO 2: CREAR NODO RAÍZ (Nivel 0) ===
        doc_chunk = self._create_root_node(metadata, content)
        chunks.append(doc_chunk)
        chunk_map = {doc_chunk["chunk_id"]: doc_chunk}

        logger.info(f"✓ Creado nodo raíz (Nivel 0): {doc_chunk['chunk_id'][:8]}...")

        # === PASO 3: PROCESAR NIVELES 1-4 EN ORDEN ===
        for level in sorted([l for l in detected_levels if 0 < l < 5]):
            level_chunks = self._process_level(
                level=level,
                structure=structure,
                content=content,
                lines=lines,
                metadata=metadata,
                doc_type=doc_type,
                existing_chunks=chunks,
                chunk_map=chunk_map
            )

            for chunk in level_chunks:
                chunks.append(chunk)
                chunk_map[chunk["chunk_id"]] = chunk

            logger.info(f"✓ Nivel {level}: Creados {len(level_chunks)} chunks")

        # === PASO 4: PROCESAR ANEXOS (Nivel 5) ===
        if 5 in detected_levels:
            anexo_chunks = self._process_anexos(
                structure=structure,
                content=content,
                lines=lines,
                metadata=metadata,
                doc_type=doc_type,
                doc_chunk=doc_chunk
            )
            chunks.extend(anexo_chunks)
            logger.info(f"✓ Nivel 5 (Anexos): Creados {len(anexo_chunks)} chunks")

        # === PASO 5: LINKING SECUENCIAL ===
        chunks = self._link_sequential(chunks)

        # === RESUMEN FINAL ===
        logger.info(f"\n{'='*60}")
        logger.info(f"RESUMEN DE PROCESAMIENTO JERÁRQUICO")
        logger.info(f"{'='*60}")
        logger.info(f"Total de chunks creados: {len(chunks)}")
        for level in range(6):
            count = sum(1 for c in chunks if c.get('nivel_jerarquico') == level)
            if count > 0:
                level_name = self.config.get_element_name(level, doc_type, plural=True)
                logger.info(f"  Nivel {level} ({level_name}): {count} chunks")
        logger.info(f"{'='*60}\n")

        return chunks

    def _detect_levels(self, structure: Dict) -> Set[int]:
        """
        Detecta qué niveles jerárquicos están presentes en el documento.

        Args:
            structure: Diccionario con elementos detectados por pdf_extractor

        Returns:
            Set de niveles presentes (ej: {0, 1, 2, 3, 5})
        """
        levels = {0}  # Nivel 0 (documento raíz) siempre existe

        for structure_key, elements in structure.items():
            if elements:
                level = self.config.get_level_for_structure_key(structure_key)
                if level is not None:
                    levels.add(level)
                    logger.debug(
                        f"Detectado nivel {level} con {len(elements)} elementos "
                        f"(clave: {structure_key})"
                    )

        return levels

    def _create_root_node(self, metadata: Dict, content: str) -> Dict:
        """
        Crea el nodo raíz del documento (Nivel 0).

        Args:
            metadata: Metadatos del documento
            content: Contenido completo

        Returns:
            Chunk del documento raíz
        """
        # Texto del nodo raíz: nombre + resumen inicial
        doc_text = f"{metadata['documento_nombre']}\n\n"
        doc_text += content[:500]  # Primeros 500 caracteres como resumen

        chunk_id = str(uuid.uuid4())

        return {
            # Identificación
            "chunk_id": chunk_id,
            "documento_id": metadata["documento_id"],
            "documento_nombre": metadata["documento_nombre"],

            # Jerarquía (NIVEL 0)
            "nivel_jerarquico": 0,
            "parent_id": None,
            "children_ids": [],
            "hierarchy_path": metadata["documento_nombre"],

            # Contenido
            "texto": doc_text,
            "longitud_tokens": self._count_tokens(doc_text),

            # Metadata específica (todas None para nivel 0)
            "titulo": None,
            "titulo_nombre": None,
            "capitulo": None,
            "capitulo_nombre": None,
            "articulo": None,
            "paragrafo": None,
            "seccion": None,
            "subseccion": None,
            "anexo_numero": None,
            "es_anexo": False,

            # Tipo
            "tipo_documento": metadata.get("documento_tipo", "generic"),

            # Navegación secuencial
            "chunk_anterior_id": None,
            "chunk_siguiente_id": None,

            # Citación y metadata
            "citacion_corta": metadata["documento_nombre"],
            "fecha_procesamiento": datetime.now().isoformat(),
            "tipo_contenido": "documento",
        }

    def _process_level(
        self,
        level: int,
        structure: Dict,
        content: str,
        lines: List[str],
        metadata: Dict,
        doc_type: str,
        existing_chunks: List[Dict],
        chunk_map: Dict
    ) -> List[Dict]:
        """
        Procesa un nivel jerárquico específico.
        GENÉRICO - funciona para cualquier tipo de elemento.

        Args:
            level: Nivel jerárquico a procesar (1-4)
            structure: Estructura detectada del documento
            content: Texto completo
            lines: Líneas del documento
            metadata: Metadatos
            doc_type: Tipo de documento
            existing_chunks: Chunks ya creados
            chunk_map: Mapa de chunk_id -> chunk

        Returns:
            Lista de chunks creados para este nivel
        """
        level_chunks = []

        # 1. Obtener elementos de este nivel
        elements = self._get_elements_for_level(level, structure)

        if not elements:
            logger.debug(f"Nivel {level}: Sin elementos")
            return []

        level_name = self.config.get_element_name(level, doc_type, plural=True)
        logger.info(f"Procesando nivel {level} ({level_name}): {len(elements)} elementos")

        # 2. Procesar cada elemento
        for i, element in enumerate(elements):
            # 2a. Encontrar padre
            parent_chunk = self._find_parent_for_element(
                element=element,
                level=level,
                existing_chunks=existing_chunks,
                structure=structure
            )

            # 2b. Extraer texto del elemento
            start_line = element["line_index"]
            end_line = (
                elements[i + 1]["line_index"] if i + 1 < len(elements)
                else len(lines)
            )
            element_text = "\n".join(lines[start_line:end_line]).strip()

            # 2c. Construir hierarchy_path
            hierarchy_path = self._build_hierarchy_path(
                element=element,
                level=level,
                parent_chunk=parent_chunk,
                metadata=metadata,
                doc_type=doc_type,
                structure=structure
            )

            # 2d. Extraer metadata específica del elemento
            element_metadata = self._extract_element_metadata(
                element=element,
                level=level,
                structure=structure,
                existing_chunks=existing_chunks
            )

            # 2e. Aplicar chunking adaptativo si es necesario
            token_count = self._count_tokens(element_text)

            if token_count <= 500:
                # Elemento pequeño: un solo chunk
                chunk = self._create_chunk(
                    text=element_text,
                    metadata=metadata,
                    nivel_jerarquico=level,
                    parent_id=parent_chunk["chunk_id"],
                    hierarchy_path=hierarchy_path,
                    doc_type=doc_type,
                    **element_metadata
                )
                level_chunks.append(chunk)
                parent_chunk["children_ids"].append(chunk["chunk_id"])

            else:
                # Elemento grande: dividir preservando jerarquía
                max_size = 800 if token_count > 2000 else self.chunk_size
                overlap = 100 if token_count > 2000 else self.chunk_overlap

                logger.debug(
                    f"Elemento largo ({token_count} tokens), dividiendo en chunks "
                    f"de {max_size} tokens con overlap {overlap}"
                )

                sub_chunks = self._split_long_text(
                    text=element_text,
                    metadata=metadata,
                    nivel_jerarquico=level,
                    parent_id=parent_chunk["chunk_id"],
                    hierarchy_path=hierarchy_path,
                    doc_type=doc_type,
                    max_chunk_size=max_size,
                    overlap=overlap,
                    **element_metadata
                )

                for sub_chunk in sub_chunks:
                    level_chunks.append(sub_chunk)
                    parent_chunk["children_ids"].append(sub_chunk["chunk_id"])

        return level_chunks

    def _get_elements_for_level(self, level: int, structure: Dict) -> List[Dict]:
        """
        Obtiene todos los elementos de un nivel jerárquico específico.

        Args:
            level: Nivel jerárquico
            structure: Estructura del documento

        Returns:
            Lista de elementos de ese nivel
        """
        # Buscar todas las claves de estructura que correspondan a este nivel
        elements = []

        for structure_key, structure_elements in structure.items():
            if self.config.get_level_for_structure_key(structure_key) == level:
                elements.extend(structure_elements)

        # Ordenar por line_index para procesar en orden
        elements.sort(key=lambda x: x.get("line_index", 0))

        return elements

    def _find_parent_for_element(
        self,
        element: Dict,
        level: int,
        existing_chunks: List[Dict],
        structure: Dict
    ) -> Dict:
        """
        Encuentra el chunk padre apropiado para un elemento.

        Estrategia:
        1. Buscar en nivel anterior (level - 1)
        2. El padre debe estar ANTES del elemento actual
        3. Usar _find_current_context() para determinar contexto

        Args:
            element: Elemento a procesar
            level: Nivel del elemento
            existing_chunks: Chunks ya creados
            structure: Estructura completa

        Returns:
            Chunk padre
        """
        parent_level = level - 1
        current_line = element["line_index"]

        # Obtener elementos del nivel padre
        parent_elements = self._get_elements_for_level(parent_level, structure)

        # Encontrar el elemento padre más reciente antes de current_line
        parent_element_numero = self._find_current_context(current_line, parent_elements)

        if parent_element_numero:
            # Buscar el chunk correspondiente
            for chunk in reversed(existing_chunks):
                if chunk.get("nivel_jerarquico") == parent_level:
                    # Verificar si coincide el número
                    if self._chunk_matches_element(chunk, parent_element_numero, parent_level):
                        return chunk

        # Fallback: buscar cualquier chunk del nivel padre
        for chunk in reversed(existing_chunks):
            if chunk.get("nivel_jerarquico") == parent_level:
                return chunk

        # Último fallback: documento raíz
        return next(c for c in existing_chunks if c["nivel_jerarquico"] == 0)

    def _find_current_context(
        self,
        current_line: int,
        context_list: List[Dict]
    ) -> Optional[str]:
        """
        Encuentra el contexto más reciente antes de current_line.
        (Método existente - se mantiene igual)
        """
        current_context = None
        for context in context_list:
            if context["line_index"] < current_line:
                current_context = context["numero"]
            else:
                break
        return current_context

    def _chunk_matches_element(
        self,
        chunk: Dict,
        element_numero: str,
        level: int
    ) -> bool:
        """
        Verifica si un chunk corresponde a un número de elemento.
        """
        # Mapeo de nivel a campo de metadata
        level_to_field = {
            1: ["titulo", "seccion"],
            2: ["capitulo", "subseccion"],
            3: ["articulo"],
            4: ["paragrafo"],
        }

        fields = level_to_field.get(level, [])

        for field in fields:
            if chunk.get(field) == element_numero:
                return True

        return False

    def _build_hierarchy_path(
        self,
        element: Dict,
        level: int,
        parent_chunk: Dict,
        metadata: Dict,
        doc_type: str,
        structure: Dict
    ) -> str:
        """
        Construye el path jerárquico completo del elemento.
        """
        if level == 0:
            return metadata["documento_nombre"]

        # Obtener path del padre
        parent_path = parent_chunk.get("hierarchy_path", metadata["documento_nombre"])

        # Construir nombre del elemento actual
        element_name = self._format_element_name(element, level, doc_type, structure)

        # Combinar
        return f"{parent_path} > {element_name}"

    def _format_element_name(
        self,
        element: Dict,
        level: int,
        doc_type: str,
        structure: Dict
    ) -> str:
        """
        Formatea el nombre del elemento para el path.
        """
        numero = element.get("numero", "")
        nombre = element.get("nombre", "") or element.get("titulo", "")

        # Inferir tipo de elemento
        element_type = self.config.infer_element_type(element, structure)

        # Obtener prefijo apropiado
        if element_type:
            prefixes = {
                "titulo": "Título",
                "capitulo": "Capítulo",
                "articulo": "Artículo",
                "paragrafo": "Parágrafo",
                "seccion": "Sección",
                "subseccion": "Subsección",
                "subsubseccion": "Sub-subsección",
                "anexo": "Anexo",
            }
            prefix = prefixes.get(element_type, "Elemento")
        else:
            prefix = self.config.get_element_name(level, doc_type, plural=False)

        # Construir nombre completo
        if nombre:
            return f"{prefix} {numero} - {nombre}"
        else:
            return f"{prefix} {numero}"

    def _extract_element_metadata(
        self,
        element: Dict,
        level: int,
        structure: Dict,
        existing_chunks: List[Dict]
    ) -> Dict:
        """
        Extrae metadata específica de un elemento.

        Returns:
            Diccionario con campos como: titulo, capitulo, articulo, etc.
        """
        metadata = {}

        # Inferir tipo de elemento
        element_type = self.config.infer_element_type(element, structure)
        numero = element.get("numero")
        nombre = element.get("nombre") or element.get("titulo")

        # Asignar a campos apropiados según tipo
        if element_type == "titulo":
            metadata["titulo"] = numero
            metadata["titulo_nombre"] = nombre
        elif element_type == "capitulo":
            metadata["capitulo"] = numero
            metadata["capitulo_nombre"] = nombre
            # Heredar título del padre
            parent = self._get_parent_metadata(existing_chunks, level - 1)
            metadata["titulo"] = parent.get("titulo")
            metadata["titulo_nombre"] = parent.get("titulo_nombre")
        elif element_type == "articulo":
            metadata["articulo"] = numero
            # Heredar título y capítulo
            parent = self._get_parent_metadata(existing_chunks, level - 1)
            metadata["titulo"] = parent.get("titulo")
            metadata["titulo_nombre"] = parent.get("titulo_nombre")
            metadata["capitulo"] = parent.get("capitulo")
            metadata["capitulo_nombre"] = parent.get("capitulo_nombre")
        elif element_type == "paragrafo":
            metadata["paragrafo"] = numero
            # Heredar todo del padre
            parent = self._get_parent_metadata(existing_chunks, level - 1)
            metadata["titulo"] = parent.get("titulo")
            metadata["titulo_nombre"] = parent.get("titulo_nombre")
            metadata["capitulo"] = parent.get("capitulo")
            metadata["capitulo_nombre"] = parent.get("capitulo_nombre")
            metadata["articulo"] = parent.get("articulo")
        elif element_type == "seccion":
            metadata["seccion"] = numero
            metadata["seccion_nombre"] = nombre
            if nombre:
                # Normalizar para búsqueda (sin tildes, lowercase)
                metadata["seccion_nombre_norm"] = self._normalize_text(nombre)
        elif element_type == "subseccion":
            metadata["subseccion"] = numero
            metadata["subseccion_nombre"] = nombre
            if nombre:
                metadata["subseccion_nombre_norm"] = self._normalize_text(nombre)
            # Heredar sección
            parent = self._get_parent_metadata(existing_chunks, level - 1)
            metadata["seccion"] = parent.get("seccion")
            metadata["seccion_nombre"] = parent.get("seccion_nombre")
            metadata["seccion_nombre_norm"] = parent.get("seccion_nombre_norm")

        return metadata

    def _get_parent_metadata(self, existing_chunks: List[Dict], parent_level: int) -> Dict:
        """
        Obtiene la metadata del último chunk del nivel padre.
        """
        for chunk in reversed(existing_chunks):
            if chunk.get("nivel_jerarquico") == parent_level:
                return chunk
        return {}

    def _process_anexos(
        self,
        structure: Dict,
        content: str,
        lines: List[str],
        metadata: Dict,
        doc_type: str,
        doc_chunk: Dict
    ) -> List[Dict]:
        """
        Procesa anexos (Nivel 5).
        Los anexos siempre apuntan directamente al documento (nivel 0).
        """
        anexos = structure.get("anexos", [])

        if not anexos:
            return []

        logger.info(f"Procesando {len(anexos)} anexos")

        chunks = []

        for i, anexo in enumerate(anexos):
            start_line = anexo["line_index"]
            end_line = (
                anexos[i + 1]["line_index"] if i + 1 < len(anexos)
                else len(lines)
            )

            anexo_text = "\n".join(lines[start_line:end_line]).strip()
            token_count = self._count_tokens(anexo_text)

            hierarchy_path = f"{metadata['documento_nombre']} > Anexo {anexo['numero']}"

            if token_count <= 500:
                # Anexo pequeño: un chunk
                chunk = self._create_chunk(
                    text=anexo_text,
                    metadata=metadata,
                    nivel_jerarquico=5,
                    parent_id=doc_chunk["chunk_id"],
                    hierarchy_path=hierarchy_path,
                    doc_type=doc_type,
                    anexo_numero=anexo["numero"],
                    es_anexo=True
                )
                chunks.append(chunk)
                doc_chunk["children_ids"].append(chunk["chunk_id"])
            else:
                # Anexo grande: dividir
                sub_chunks = self._split_long_text(
                    text=anexo_text,
                    metadata=metadata,
                    nivel_jerarquico=5,
                    parent_id=doc_chunk["chunk_id"],
                    hierarchy_path=hierarchy_path,
                    doc_type=doc_type,
                    max_chunk_size=800,
                    overlap=100,
                    anexo_numero=anexo["numero"],
                    es_anexo=True
                )
                for sub_chunk in sub_chunks:
                    chunks.append(sub_chunk)
                    doc_chunk["children_ids"].append(sub_chunk["chunk_id"])

        return chunks

    def _split_long_text(
        self,
        text: str,
        metadata: Dict,
        nivel_jerarquico: int,
        parent_id: str,
        hierarchy_path: str,
        doc_type: str,
        max_chunk_size: int,
        overlap: int,
        **additional_metadata
    ) -> List[Dict]:
        """
        Divide texto largo en chunks más pequeños preservando jerarquía.

        MEJORAS:
        - Garantiza que ningún chunk exceda 8000 tokens (límite de embedding)
        - Mantiene overlap entre chunks para preservar contexto
        - Divide por oraciones si los párrafos son muy grandes
        - Funcional para CUALQUIER tipo de documento

        Args:
            text: Texto a dividir
            max_chunk_size: Tamaño máximo por chunk (default: 500-800)
            overlap: Overlap en tokens entre chunks consecutivos
        """
        total_tokens = self._count_tokens(text)

        # Límite absoluto para evitar truncamiento en embeddings
        EMBEDDING_LIMIT = 8000  # Límite seguro (8191 - buffer)

        # Si el texto completo cabe en el límite de embedding, usar max_chunk_size normal
        if total_tokens <= EMBEDDING_LIMIT:
            return self._split_by_paragraphs(
                text=text,
                metadata=metadata,
                nivel_jerarquico=nivel_jerarquico,
                parent_id=parent_id,
                hierarchy_path=hierarchy_path,
                doc_type=doc_type,
                max_chunk_size=max_chunk_size,
                overlap=overlap,
                **additional_metadata
            )

        # Texto muy largo: dividir más agresivamente
        logger.warning(
            f"Texto muy largo ({total_tokens} tokens), dividiendo en chunks "
            f"de máximo {max_chunk_size} tokens con overlap {overlap}"
        )

        return self._split_with_overlap(
            text=text,
            metadata=metadata,
            nivel_jerarquico=nivel_jerarquico,
            parent_id=parent_id,
            hierarchy_path=hierarchy_path,
            doc_type=doc_type,
            max_chunk_size=max_chunk_size,
            overlap=overlap,
            **additional_metadata
        )

    def _split_by_paragraphs(
        self,
        text: str,
        metadata: Dict,
        nivel_jerarquico: int,
        parent_id: str,
        hierarchy_path: str,
        doc_type: str,
        max_chunk_size: int,
        overlap: int,
        **additional_metadata
    ) -> List[Dict]:
        """
        Divide texto por párrafos (método original mejorado).
        """
        chunks = []
        paragraphs = text.split("\n\n")

        current_chunk_text = ""
        current_tokens = 0

        for para in paragraphs:
            para_tokens = self._count_tokens(para)

            # Si un solo párrafo excede el límite, dividirlo por oraciones
            if para_tokens > max_chunk_size:
                # Guardar chunk actual primero
                if current_chunk_text:
                    chunk = self._create_chunk(
                        text=current_chunk_text.strip(),
                        metadata=metadata,
                        nivel_jerarquico=nivel_jerarquico,
                        parent_id=parent_id,
                        hierarchy_path=hierarchy_path,
                        doc_type=doc_type,
                        **additional_metadata
                    )
                    chunks.append(chunk)
                    current_chunk_text = ""
                    current_tokens = 0

                # Dividir párrafo grande por oraciones
                sentence_chunks = self._split_by_sentences(
                    para, max_chunk_size, overlap
                )

                for sent_chunk in sentence_chunks:
                    chunk = self._create_chunk(
                        text=sent_chunk.strip(),
                        metadata=metadata,
                        nivel_jerarquico=nivel_jerarquico,
                        parent_id=parent_id,
                        hierarchy_path=hierarchy_path,
                        doc_type=doc_type,
                        **additional_metadata
                    )
                    chunks.append(chunk)

                continue

            # Acumular párrafos normales
            if current_tokens + para_tokens > max_chunk_size:
                # Guardar chunk actual
                if current_chunk_text:
                    chunk = self._create_chunk(
                        text=current_chunk_text.strip(),
                        metadata=metadata,
                        nivel_jerarquico=nivel_jerarquico,
                        parent_id=parent_id,
                        hierarchy_path=hierarchy_path,
                        doc_type=doc_type,
                        **additional_metadata
                    )
                    chunks.append(chunk)

                # Nuevo chunk
                current_chunk_text = para
                current_tokens = para_tokens
            else:
                if current_chunk_text:
                    current_chunk_text += "\n\n" + para
                else:
                    current_chunk_text = para
                current_tokens += para_tokens

        # Último chunk
        if current_chunk_text:
            chunk = self._create_chunk(
                text=current_chunk_text.strip(),
                metadata=metadata,
                nivel_jerarquico=nivel_jerarquico,
                parent_id=parent_id,
                hierarchy_path=hierarchy_path,
                doc_type=doc_type,
                **additional_metadata
            )
            chunks.append(chunk)

        return chunks

    def _split_with_overlap(
        self,
        text: str,
        metadata: Dict,
        nivel_jerarquico: int,
        parent_id: str,
        hierarchy_path: str,
        doc_type: str,
        max_chunk_size: int,
        overlap: int,
        **additional_metadata
    ) -> List[Dict]:
        """
        Divide texto largo con overlap entre chunks.
        Garantiza que ningún chunk exceda max_chunk_size.
        """
        chunks = []

        # Dividir por oraciones primero
        sentences = self._split_into_sentences(text)

        current_chunk_sentences = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = self._count_tokens(sentence)

            # Si una sola oración excede el límite, dividirla por palabras
            if sentence_tokens > max_chunk_size:
                # Guardar chunk actual
                if current_chunk_sentences:
                    chunk_text = " ".join(current_chunk_sentences)
                    chunk = self._create_chunk(
                        text=chunk_text.strip(),
                        metadata=metadata,
                        nivel_jerarquico=nivel_jerarquico,
                        parent_id=parent_id,
                        hierarchy_path=hierarchy_path,
                        doc_type=doc_type,
                        **additional_metadata
                    )
                    chunks.append(chunk)
                    current_chunk_sentences = []
                    current_tokens = 0

                # Dividir oración muy larga por palabras
                word_chunks = self._split_by_words(sentence, max_chunk_size)
                for word_chunk in word_chunks:
                    chunk = self._create_chunk(
                        text=word_chunk.strip(),
                        metadata=metadata,
                        nivel_jerarquico=nivel_jerarquico,
                        parent_id=parent_id,
                        hierarchy_path=hierarchy_path,
                        doc_type=doc_type,
                        **additional_metadata
                    )
                    chunks.append(chunk)

                continue

            # Verificar si agregar esta oración excede el límite
            if current_tokens + sentence_tokens > max_chunk_size:
                # Guardar chunk actual
                if current_chunk_sentences:
                    chunk_text = " ".join(current_chunk_sentences)
                    chunk = self._create_chunk(
                        text=chunk_text.strip(),
                        metadata=metadata,
                        nivel_jerarquico=nivel_jerarquico,
                        parent_id=parent_id,
                        hierarchy_path=hierarchy_path,
                        doc_type=doc_type,
                        **additional_metadata
                    )
                    chunks.append(chunk)

                # Calcular overlap: mantener últimas N oraciones
                overlap_sentences = self._get_overlap_sentences(
                    current_chunk_sentences, overlap
                )

                # Nuevo chunk con overlap
                current_chunk_sentences = overlap_sentences + [sentence]
                current_tokens = sum(
                    self._count_tokens(s) for s in current_chunk_sentences
                )
            else:
                current_chunk_sentences.append(sentence)
                current_tokens += sentence_tokens

        # Último chunk
        if current_chunk_sentences:
            chunk_text = " ".join(current_chunk_sentences)
            chunk = self._create_chunk(
                text=chunk_text.strip(),
                metadata=metadata,
                nivel_jerarquico=nivel_jerarquico,
                parent_id=parent_id,
                hierarchy_path=hierarchy_path,
                doc_type=doc_type,
                **additional_metadata
            )
            chunks.append(chunk)

        logger.info(
            f"Texto dividido en {len(chunks)} chunks con overlap "
            f"(tokens promedio: {sum(c['longitud_tokens'] for c in chunks) // len(chunks) if chunks else 0})"
        )

        return chunks

    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Divide texto en oraciones.

        Detecta puntos finales, saltos de línea y otros delimitadores.
        """
        import re

        # Dividir por puntos seguidos de espacio/mayúscula o fin de línea
        # También dividir por saltos de línea
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])|(?<=[.!?])\n|(?<=\n)\n+', text)

        # Limpiar y filtrar oraciones vacías
        sentences = [s.strip() for s in sentences if s.strip()]

        return sentences

    def _split_by_sentences(self, text: str, max_size: int, overlap: int) -> List[str]:
        """
        Divide un párrafo grande en chunks por oraciones.
        """
        sentences = self._split_into_sentences(text)
        chunks = []

        current_chunk = ""
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = self._count_tokens(sentence)

            if current_tokens + sentence_tokens > max_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
                current_tokens = sentence_tokens
            else:
                current_chunk += " " + sentence if current_chunk else sentence
                current_tokens += sentence_tokens

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _split_by_words(self, text: str, max_size: int) -> List[str]:
        """
        Divide una oración muy larga por palabras.
        Último recurso para oraciones extremadamente largas.
        """
        words = text.split()
        chunks = []

        current_chunk = []
        current_tokens = 0

        for word in words:
            word_tokens = self._count_tokens(word)

            if current_tokens + word_tokens > max_size:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_tokens = word_tokens
            else:
                current_chunk.append(word)
                current_tokens += word_tokens

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def _get_overlap_sentences(
        self, sentences: List[str], overlap_tokens: int
    ) -> List[str]:
        """
        Obtiene las últimas N oraciones que sumen aproximadamente overlap_tokens.
        """
        if not sentences:
            return []

        overlap_sentences = []
        total_tokens = 0

        # Recorrer oraciones en orden inverso
        for sentence in reversed(sentences):
            sentence_tokens = self._count_tokens(sentence)

            if total_tokens + sentence_tokens > overlap_tokens:
                break

            overlap_sentences.insert(0, sentence)
            total_tokens += sentence_tokens

        return overlap_sentences

    def _create_chunk(
        self,
        text: str,
        metadata: Dict,
        nivel_jerarquico: int,
        parent_id: str,
        hierarchy_path: str,
        doc_type: str,
        **additional_fields
    ) -> Dict:
        """
        Crea un chunk con metadata completa.
        """
        chunk_id = str(uuid.uuid4())

        # Generar citación
        citation = self._generate_citation(
            metadata=metadata,
            doc_type=doc_type,
            **additional_fields
        )

        chunk = {
            # Identificación
            "chunk_id": chunk_id,
            "documento_id": metadata["documento_id"],
            "documento_nombre": metadata["documento_nombre"],

            # Jerarquía (UNIVERSAL)
            "nivel_jerarquico": nivel_jerarquico,
            "parent_id": parent_id,
            "children_ids": [],
            "hierarchy_path": hierarchy_path,

            # Contenido
            "texto": text,
            "longitud_tokens": self._count_tokens(text),

            # Tipo
            "tipo_documento": doc_type,

            # Navegación
            "chunk_anterior_id": None,
            "chunk_siguiente_id": None,

            # Citación
            "citacion_corta": citation,
            "fecha_procesamiento": datetime.now().isoformat(),
            "tipo_contenido": self._detect_content_type(text),
        }

        # Agregar campos adicionales (titulo, capitulo, articulo, etc.)
        for key, value in additional_fields.items():
            chunk[key] = value

        # Asegurar que todos los campos opcionales existan (para Qdrant)
        optional_fields = [
            "titulo", "titulo_nombre", "capitulo", "capitulo_nombre",
            "articulo", "paragrafo", "seccion", "seccion_nombre", "seccion_nombre_norm",
            "subseccion", "subseccion_nombre", "subseccion_nombre_norm", "anexo_numero", "es_anexo"
        ]
        for field in optional_fields:
            if field not in chunk:
                chunk[field] = None if field != "es_anexo" else False

        return chunk

    def _generate_citation(
        self,
        metadata: Dict,
        doc_type: str,
        **fields
    ) -> str:
        """
        Genera citación corta basada en el tipo de documento.
        """
        parts = []

        # Legal
        if fields.get("anexo_numero"):
            parts.append(f"Anexo {fields['anexo_numero']}")
        if fields.get("articulo"):
            parts.append(f"Art. {fields['articulo']}")
        if fields.get("paragrafo"):
            parts.append(f"Par. {fields['paragrafo']}")

        # Técnico
        if fields.get("subseccion"):
            parts.append(f"Sec. {fields['subseccion']}")
        elif fields.get("seccion"):
            parts.append(f"Sec. {fields['seccion']}")

        # Documento
        doc_ref = metadata.get("documento_tipo", "Documento")
        if metadata.get("documento_numero"):
            doc_ref += f" {metadata['documento_numero']}"
        if metadata.get("documento_año"):
            doc_ref += f"/{metadata['documento_año']}"

        if not doc_ref or doc_ref == metadata.get("documento_tipo"):
            doc_ref = metadata["documento_nombre"]

        parts.append(doc_ref)

        return ", ".join(parts) if parts else doc_ref

    def _detect_content_type(self, text: str) -> str:
        """
        Detecta el tipo de contenido del chunk.
        """
        text_lower = text.lower()

        if any(phrase in text_lower for phrase in ["se entiende por", "se define", "significa"]):
            return "definicion"

        if any(phrase in text_lower for phrase in ["deberá", "debe", "procedimiento", "proceso"]):
            return "procedimiento"

        if any(phrase in text_lower for phrase in ["requisito", "deberá cumplir", "debe contar"]):
            return "requisito"

        if text.startswith("ART") or "ARTÍCULO" in text[:50].upper():
            return "articulo"

        return "general"

    def _count_tokens(self, text: str) -> int:
        """
        Cuenta tokens en un texto.
        """
        try:
            return len(self.tokenizer.encode(text))
        except Exception:
            return int(len(text.split()) * 1.3)

    def _link_sequential(self, chunks: List[Dict]) -> List[Dict]:
        """
        Vincula chunks secuencialmente (anterior/siguiente).
        """
        for i, chunk in enumerate(chunks):
            if i > 0:
                chunk["chunk_anterior_id"] = chunks[i - 1]["chunk_id"]
            if i < len(chunks) - 1:
                chunk["chunk_siguiente_id"] = chunks[i + 1]["chunk_id"]

        return chunks
