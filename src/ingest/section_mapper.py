"""
Section Mapper Module.
Extrae y mapea nombres de secciones/capítulos a números durante ingestión.
"""
import re
import json
from pathlib import Path
from typing import Dict, Optional, Set
from loguru import logger
import unicodedata


class SectionMapper:
    """Mapea nombres de secciones/capítulos/títulos a números."""

    def __init__(self, storage_path: str = "./storage/section_mappings.json"):
        """
        Initialize section mapper.

        Args:
            storage_path: Path to store/load mappings
        """
        self.storage_path = Path(storage_path)
        self.mappings: Dict[str, Dict[str, Dict[str, str]]] = {}

        # Cargar mappings existentes
        self._load_mappings()

    def _normalize_text(self, text: str) -> str:
        """
        Normaliza texto para búsqueda.

        - Lowercase
        - Sin tildes
        - Sin caracteres especiales
        - Espacios simples

        Args:
            text: Texto a normalizar

        Returns:
            Texto normalizado
        """
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

    def extract_from_hierarchy_path(self, hierarchy_path: str) -> Dict[str, str]:
        """
        Extrae nombres de secciones/capítulos del hierarchy_path.

        Ejemplos:
        - "Acuerdo 03/2021 > Título 4 - Proyectos de Inversión"
          → {"titulo_numero": "4", "titulo_nombre": "Proyectos de Inversión"}

        - "Documentotecnico V2 > Sección 6 - ANTECEDENTES"
          → {"seccion": "6", "seccion_nombre": "ANTECEDENTES"}

        Args:
            hierarchy_path: Path jerárquico completo

        Returns:
            Diccionario con extracciones
        """
        result = {}

        if not hierarchy_path:
            return result

        # Patterns para extraer sección/capítulo/título con nombre
        patterns = {
            "seccion": re.compile(
                r'Secci[óo]n\s+(\d+(?:\.\d+)?)\s*[-–—]\s*([A-Z\s]+)',
                re.IGNORECASE
            ),
            "capitulo": re.compile(
                r'Cap[íi]tulo\s+(\d+|[IVXLCDM]+)\s*[-–—]\s*(.+?)(?:\s*>|$)',
                re.IGNORECASE
            ),
            "titulo": re.compile(
                r'T[íi]tulo\s+(\d+|[IVXLCDM]+)\s*[-–—]\s*(.+?)(?:\s*>|$)',
                re.IGNORECASE
            ),
            "subseccion": re.compile(
                r'Subsecci[óo]n\s+(\d+(?:\.\d+)?)\s*[-–—]\s*(.+?)(?:\s*>|$)',
                re.IGNORECASE
            ),
            "anexo": re.compile(
                r'Anexo\s+([a-zA-Z0-9]+)\s*[-–—]?\s*(.+?)(?:\s*>|$)',
                re.IGNORECASE
            ),
        }

        for field_name, pattern in patterns.items():
            match = pattern.search(hierarchy_path)
            if match:
                numero = match.group(1).strip()
                nombre = match.group(2).strip() if len(match.groups()) > 1 else ""

                # Normalizar número romano a arábigo si aplica
                numero = self._normalize_roman_numeral(numero)

                # Guardar número y nombre
                result[field_name] = numero
                if nombre:
                    result[f"{field_name}_nombre"] = nombre
                    result[f"{field_name}_nombre_norm"] = self._normalize_text(nombre)

        return result

    def _normalize_roman_numeral(self, num_str: str) -> str:
        """
        Convierte romano a arábigo.

        Args:
            num_str: Número como string

        Returns:
            Número normalizado
        """
        roman_to_int = {
            "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
            "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10,
        }

        num_str = num_str.strip().upper()

        if num_str in roman_to_int:
            return str(roman_to_int[num_str])

        return num_str

    def add_mapping(
        self,
        documento_id: str,
        field_type: str,  # "seccion" | "capitulo" | "titulo" | "subseccion"
        numero: str,
        nombre: str
    ):
        """
        Agrega un mapeo nombre → número.

        Args:
            documento_id: ID del documento
            field_type: Tipo de campo (seccion, capitulo, titulo)
            numero: Número (ej: "6", "4")
            nombre: Nombre (ej: "ANTECEDENTES", "Proyectos de Inversión")
        """
        if documento_id not in self.mappings:
            self.mappings[documento_id] = {}

        if field_type not in self.mappings[documento_id]:
            self.mappings[documento_id][field_type] = {}

        # Normalizar nombre para búsqueda
        nombre_norm = self._normalize_text(nombre)

        # Guardar mapeo
        self.mappings[documento_id][field_type][nombre_norm] = numero

        logger.debug(
            f"Mapeo agregado: {documento_id}.{field_type}['{nombre_norm}'] = '{numero}'"
        )

    def get_numero_by_nombre(
        self,
        documento_id: str,
        field_type: str,
        nombre: str
    ) -> Optional[str]:
        """
        Busca número por nombre.

        Args:
            documento_id: ID del documento
            field_type: Tipo de campo
            nombre: Nombre a buscar

        Returns:
            Número o None
        """
        if documento_id not in self.mappings:
            return None

        if field_type not in self.mappings[documento_id]:
            return None

        nombre_norm = self._normalize_text(nombre)

        return self.mappings[documento_id][field_type].get(nombre_norm)

    def search_numero_fuzzy(
        self,
        documento_id: str,
        field_type: str,
        nombre: str
    ) -> Optional[str]:
        """
        Búsqueda fuzzy: busca número incluso si nombre es parcial.

        Ejemplo:
        - Mapeo: "antecedentes y contexto" → "6"
        - Búsqueda: "antecedentes" → Encuentra "6"

        Args:
            documento_id: ID del documento
            field_type: Tipo de campo
            nombre: Nombre a buscar (puede ser parcial)

        Returns:
            Número o None
        """
        if documento_id not in self.mappings:
            return None

        if field_type not in self.mappings[documento_id]:
            return None

        nombre_norm = self._normalize_text(nombre)

        # 1. Búsqueda exacta
        if nombre_norm in self.mappings[documento_id][field_type]:
            return self.mappings[documento_id][field_type][nombre_norm]

        # 2. Búsqueda por substring (el nombre buscado está contenido en alguna key)
        for key, numero in self.mappings[documento_id][field_type].items():
            if nombre_norm in key:
                logger.debug(f"Fuzzy match: '{nombre_norm}' in '{key}' → '{numero}'")
                return numero

        # 3. Búsqueda inversa (alguna key está contenida en el nombre buscado)
        for key, numero in self.mappings[documento_id][field_type].items():
            if key in nombre_norm:
                logger.debug(f"Fuzzy match: '{key}' in '{nombre_norm}' → '{numero}'")
                return numero

        return None

    def build_from_chunks(self, chunks: list):
        """
        Construye mappings desde lista de chunks.

        Args:
            chunks: Lista de chunks procesados
        """
        logger.info("Construyendo mappings desde chunks...")

        for chunk in chunks:
            documento_id = chunk.get("documento_id")
            hierarchy_path = chunk.get("hierarchy_path", "")

            if not documento_id or not hierarchy_path:
                continue

            # Extraer nombres del path
            extracted = self.extract_from_hierarchy_path(hierarchy_path)

            # Agregar mappings
            for key, value in extracted.items():
                if key.endswith("_nombre") or key.endswith("_nombre_norm"):
                    continue  # Skip nombre fields

                # key es el tipo (seccion, capitulo, etc)
                # value es el número
                nombre_field = f"{key}_nombre"
                if nombre_field in extracted:
                    self.add_mapping(
                        documento_id=documento_id,
                        field_type=key,
                        numero=value,
                        nombre=extracted[nombre_field]
                    )

        logger.info(f"Mappings construidos para {len(self.mappings)} documentos")

        # Guardar a disco
        self._save_mappings()

    def _save_mappings(self):
        """Guarda mappings a archivo JSON."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.mappings, f, ensure_ascii=False, indent=2)

            logger.info(f"Mappings guardados en {self.storage_path}")

        except Exception as e:
            logger.error(f"Error guardando mappings: {e}")

    def _load_mappings(self):
        """Carga mappings desde archivo JSON."""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    self.mappings = json.load(f)

                logger.info(
                    f"Mappings cargados desde {self.storage_path}: "
                    f"{len(self.mappings)} documentos"
                )
            else:
                logger.info("No hay mappings previos, iniciando vacío")

        except Exception as e:
            logger.warning(f"Error cargando mappings: {e}")
            self.mappings = {}

    def get_all_nombres(self, documento_id: str, field_type: str) -> Set[str]:
        """
        Obtiene todos los nombres disponibles para un tipo de campo.

        Args:
            documento_id: ID del documento
            field_type: Tipo de campo

        Returns:
            Set de nombres normalizados
        """
        if documento_id not in self.mappings:
            return set()

        if field_type not in self.mappings[documento_id]:
            return set()

        return set(self.mappings[documento_id][field_type].keys())

    def get_stats(self) -> Dict:
        """
        Obtiene estadísticas de mappings.

        Returns:
            Diccionario con stats
        """
        stats = {
            "total_documentos": len(self.mappings),
            "por_documento": {}
        }

        for doc_id, doc_mappings in self.mappings.items():
            stats["por_documento"][doc_id] = {
                field_type: len(mappings)
                for field_type, mappings in doc_mappings.items()
            }

        return stats
