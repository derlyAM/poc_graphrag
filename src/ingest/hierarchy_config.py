"""
Configuración centralizada para procesamiento jerárquico de documentos.
Define mapeos entre tipos de elementos y niveles jerárquicos.
"""
from typing import Dict, Optional


class HierarchyConfig:
    """Configuración de jerarquías documentales."""

    # Definición de niveles jerárquicos universales
    HIERARCHY_LEVELS = {
        0: {
            "nombre": "Documento",
            "nombre_corto": "Doc",
            "obligatorio": True,
            "descripcion": "Nodo raíz del documento completo"
        },
        1: {
            "nombre": "División Mayor",
            "nombre_corto": "Div1",
            "obligatorio": False,
            "descripcion": "Títulos, Secciones principales, Componentes"
        },
        2: {
            "nombre": "División Media",
            "nombre_corto": "Div2",
            "obligatorio": False,
            "descripcion": "Capítulos, Subsecciones, Factores"
        },
        3: {
            "nombre": "Unidad Básica",
            "nombre_corto": "Unidad",
            "obligatorio": False,
            "descripcion": "Artículos, Ítems numerados, Elementos"
        },
        4: {
            "nombre": "Detalle",
            "nombre_corto": "Detalle",
            "obligatorio": False,
            "descripcion": "Parágrafos, Sub-ítems, Medidas"
        },
        5: {
            "nombre": "Anexo",
            "nombre_corto": "Anexo",
            "obligatorio": False,
            "descripcion": "Anexos, Apéndices, Material complementario"
        }
    }

    # Mapeo de tipos de elementos estructurales a niveles jerárquicos
    STRUCTURE_KEY_TO_LEVEL = {
        # Documentos Legales
        "titulos": 1,
        "capitulos": 2,
        "articulos": 3,
        "paragrafos": 4,

        # Documentos Técnicos
        "secciones": 1,
        "subsecciones": 2,
        "subsubsecciones": 3,

        # Anexos (todos los tipos)
        "anexos": 5,
    }

    # Mapeo de tipo de elemento individual a nivel
    ELEMENT_TYPE_TO_LEVEL = {
        # Legal
        "titulo": 1,
        "capitulo": 2,
        "articulo": 3,
        "paragrafo": 4,
        "seccion_legal": 2,  # Sección dentro de capítulo (legal)

        # Técnico
        "seccion": 1,
        "subseccion": 2,
        "subsubseccion": 3,
        "detalle": 4,

        # Anexos
        "anexo": 5,

        # Genérico (fallback)
        "heading_1": 1,
        "heading_2": 2,
        "heading_3": 3,
        "heading_4": 4,
    }

    # Nombres de elementos por tipo de documento
    ELEMENT_NAMES = {
        "legal": {
            1: {"singular": "Título", "plural": "Títulos"},
            2: {"singular": "Capítulo", "plural": "Capítulos"},
            3: {"singular": "Artículo", "plural": "Artículos"},
            4: {"singular": "Parágrafo", "plural": "Parágrafos"},
            5: {"singular": "Anexo", "plural": "Anexos"},
        },
        "technical": {
            1: {"singular": "Sección", "plural": "Secciones"},
            2: {"singular": "Subsección", "plural": "Subsecciones"},
            3: {"singular": "Sub-subsección", "plural": "Sub-subsecciones"},
            4: {"singular": "Detalle", "plural": "Detalles"},
            5: {"singular": "Anexo", "plural": "Anexos"},
        },
        "financial": {
            1: {"singular": "Sección", "plural": "Secciones"},
            2: {"singular": "Categoría", "plural": "Categorías"},
            3: {"singular": "Subcategoría", "plural": "Subcategorías"},
            4: {"singular": "Cuenta", "plural": "Cuentas"},
            5: {"singular": "Nota", "plural": "Notas"},
        },
        "environmental": {
            1: {"singular": "Componente", "plural": "Componentes"},
            2: {"singular": "Factor", "plural": "Factores"},
            3: {"singular": "Impacto", "plural": "Impactos"},
            4: {"singular": "Medida", "plural": "Medidas"},
            5: {"singular": "Anexo", "plural": "Anexos"},
        },
        "generic": {
            1: {"singular": "Sección", "plural": "Secciones"},
            2: {"singular": "Subsección", "plural": "Subsecciones"},
            3: {"singular": "Elemento", "plural": "Elementos"},
            4: {"singular": "Sub-elemento", "plural": "Sub-elementos"},
            5: {"singular": "Anexo", "plural": "Anexos"},
        }
    }

    @classmethod
    def get_level_for_structure_key(cls, key: str) -> Optional[int]:
        """
        Obtiene el nivel jerárquico para una clave de estructura.

        Args:
            key: Clave de estructura (ej: "titulos", "secciones")

        Returns:
            Nivel jerárquico (0-5) o None si no se encuentra
        """
        return cls.STRUCTURE_KEY_TO_LEVEL.get(key)

    @classmethod
    def get_level_for_element_type(cls, element_type: str) -> Optional[int]:
        """
        Obtiene el nivel jerárquico para un tipo de elemento.

        Args:
            element_type: Tipo de elemento (ej: "titulo", "seccion")

        Returns:
            Nivel jerárquico (0-5) o None si no se encuentra
        """
        return cls.ELEMENT_TYPE_TO_LEVEL.get(element_type)

    @classmethod
    def get_element_name(
        cls,
        level: int,
        doc_type: str = "generic",
        plural: bool = False
    ) -> str:
        """
        Obtiene el nombre de un elemento para un nivel y tipo de documento.

        Args:
            level: Nivel jerárquico (0-5)
            doc_type: Tipo de documento ("legal", "technical", etc.)
            plural: Si True, retorna forma plural

        Returns:
            Nombre del elemento
        """
        if doc_type not in cls.ELEMENT_NAMES:
            doc_type = "generic"

        if level not in cls.ELEMENT_NAMES[doc_type]:
            return "Elemento" if not plural else "Elementos"

        form = "plural" if plural else "singular"
        return cls.ELEMENT_NAMES[doc_type][level][form]

    @classmethod
    def infer_element_type(cls, element: Dict, structure: Dict) -> Optional[str]:
        """
        Infiere el tipo de elemento basándose en su estructura.

        Args:
            element: Diccionario con datos del elemento
            structure: Estructura completa del documento

        Returns:
            Tipo de elemento o None
        """
        # Buscar en qué lista de la estructura está el elemento
        for key, elements in structure.items():
            if element in elements:
                # Mapear clave plural a tipo singular
                type_map = {
                    "titulos": "titulo",
                    "capitulos": "capitulo",
                    "articulos": "articulo",
                    "paragrafos": "paragrafo",
                    "secciones": "seccion",
                    "subsecciones": "subseccion",
                    "subsubsecciones": "subsubseccion",
                    "anexos": "anexo",
                }
                return type_map.get(key)

        return None

    @classmethod
    def validate_level(cls, level: int) -> bool:
        """
        Valida que un nivel sea válido.

        Args:
            level: Nivel a validar

        Returns:
            True si el nivel es válido (0-5)
        """
        return 0 <= level <= 5

    @classmethod
    def get_level_info(cls, level: int) -> Dict:
        """
        Obtiene información completa sobre un nivel.

        Args:
            level: Nivel jerárquico

        Returns:
            Diccionario con información del nivel
        """
        return cls.HIERARCHY_LEVELS.get(level, {})
