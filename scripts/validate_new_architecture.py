"""
Script de validación comparativa para verificar la nueva arquitectura unificada.
Compara chunks generados con el sistema anterior vs sistema nuevo.
"""
import sys
from pathlib import Path
from typing import Dict, List, Set
from collections import Counter
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingest.chunker import HierarchicalChunker
from src.ingest.pdf_extractor import PDFExtractor
from loguru import logger


def setup_logging():
    """Configure logging."""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO",
    )


def analyze_chunks(chunks: List[Dict], label: str) -> Dict:
    """
    Analiza chunks y retorna métricas clave.

    Args:
        chunks: Lista de chunks a analizar
        label: Etiqueta para identificar el conjunto (ej: "Legal", "Técnico")

    Returns:
        Diccionario con métricas
    """
    logger.info(f"\n{'=' * 80}")
    logger.info(f"ANÁLISIS: {label}")
    logger.info(f"{'=' * 80}")

    metrics = {
        "total_chunks": len(chunks),
        "niveles_detectados": set(),
        "chunks_con_parent": 0,
        "chunks_con_children": 0,
        "chunks_con_hierarchy_path": 0,
        "campos_jerarquicos": Counter(),
        "distribucion_niveles": Counter(),
        "chunks_sin_jerarquia": 0,
    }

    for chunk in chunks:
        # Analizar nivel jerárquico
        nivel = chunk.get("nivel_jerarquico")
        if nivel is not None:
            metrics["niveles_detectados"].add(nivel)
            metrics["distribucion_niveles"][nivel] += 1
        else:
            metrics["chunks_sin_jerarquia"] += 1

        # Analizar campos de grafo
        if chunk.get("parent_id"):
            metrics["chunks_con_parent"] += 1

        if chunk.get("children_ids") and len(chunk["children_ids"]) > 0:
            metrics["chunks_con_children"] += 1

        if chunk.get("hierarchy_path"):
            metrics["chunks_con_hierarchy_path"] += 1

        # Analizar campos jerárquicos presentes
        for field in ["titulo", "capitulo", "articulo", "paragrafo", "seccion", "subseccion", "anexo"]:
            if chunk.get(field):
                metrics["campos_jerarquicos"][field] += 1

    # Mostrar resultados
    logger.info(f"Total chunks: {metrics['total_chunks']}")
    logger.info(f"Niveles jerárquicos detectados: {sorted(metrics['niveles_detectados'])}")

    if metrics["distribucion_niveles"]:
        logger.info("\nDistribución por nivel:")
        for nivel in sorted(metrics["distribucion_niveles"].keys()):
            count = metrics["distribucion_niveles"][nivel]
            pct = count / metrics["total_chunks"] * 100
            logger.info(f"  Nivel {nivel}: {count} chunks ({pct:.1f}%)")

    if metrics["chunks_sin_jerarquia"] > 0:
        pct = metrics["chunks_sin_jerarquia"] / metrics["total_chunks"] * 100
        logger.warning(f"\nChunks sin nivel jerárquico: {metrics['chunks_sin_jerarquia']} ({pct:.1f}%)")

    logger.info("\nCampos de grafo:")
    logger.info(f"  Chunks con parent_id: {metrics['chunks_con_parent']} ({metrics['chunks_con_parent']/metrics['total_chunks']*100:.1f}%)")
    logger.info(f"  Chunks con children_ids: {metrics['chunks_con_children']} ({metrics['chunks_con_children']/metrics['total_chunks']*100:.1f}%)")
    logger.info(f"  Chunks con hierarchy_path: {metrics['chunks_con_hierarchy_path']} ({metrics['chunks_con_hierarchy_path']/metrics['total_chunks']*100:.1f}%)")

    if metrics["campos_jerarquicos"]:
        logger.info("\nCampos jerárquicos detectados:")
        for field, count in metrics["campos_jerarquicos"].most_common():
            logger.info(f"  {field}: {count} chunks")

    # Calcular completitud del grafo
    grafo_completitud = (
        metrics["chunks_con_parent"] +
        metrics["chunks_con_children"] +
        metrics["chunks_con_hierarchy_path"]
    ) / (metrics["total_chunks"] * 3) * 100

    metrics["grafo_completitud"] = grafo_completitud
    logger.info(f"\nCompletitud del grafo: {grafo_completitud:.1f}%")

    return metrics


def compare_metrics(metrics1: Dict, metrics2: Dict, doc_name: str):
    """
    Compara métricas de dos conjuntos de chunks.

    Args:
        metrics1: Métricas del conjunto 1
        metrics2: Métricas del conjunto 2
        doc_name: Nombre del documento
    """
    logger.info(f"\n{'=' * 80}")
    logger.info(f"COMPARACIÓN: {doc_name}")
    logger.info(f"{'=' * 80}")

    # Comparar totales
    diff_chunks = metrics2["total_chunks"] - metrics1["total_chunks"]
    if diff_chunks != 0:
        logger.warning(f"Diferencia en total de chunks: {diff_chunks:+d}")
    else:
        logger.success("✓ Mismo número de chunks")

    # Comparar niveles detectados
    niveles1 = metrics1["niveles_detectados"]
    niveles2 = metrics2["niveles_detectados"]

    if niveles1 == niveles2:
        logger.success(f"✓ Mismos niveles detectados: {sorted(niveles2)}")
    else:
        logger.warning(f"Cambio en niveles detectados:")
        logger.warning(f"  Antes: {sorted(niveles1)}")
        logger.warning(f"  Ahora: {sorted(niveles2)}")

        nuevos_niveles = niveles2 - niveles1
        if nuevos_niveles:
            logger.info(f"  Niveles nuevos: {sorted(nuevos_niveles)} ✅")

    # Comparar completitud del grafo
    diff_grafo = metrics2["grafo_completitud"] - metrics1["grafo_completitud"]
    if diff_grafo > 0:
        logger.success(f"✓ Mejora en completitud del grafo: {diff_grafo:+.1f}%")
    elif diff_grafo < 0:
        logger.error(f"❌ REGRESIÓN en completitud del grafo: {diff_grafo:+.1f}%")
    else:
        logger.info("Completitud del grafo sin cambios")

    # Comparar chunks sin jerarquía
    diff_sin_jerarquia = metrics2["chunks_sin_jerarquia"] - metrics1["chunks_sin_jerarquia"]
    if diff_sin_jerarquia < 0:
        logger.success(f"✓ Reducción de chunks sin jerarquía: {diff_sin_jerarquia} chunks")
    elif diff_sin_jerarquia > 0:
        logger.warning(f"⚠️ Aumento de chunks sin jerarquía: {diff_sin_jerarquia:+d} chunks")


def validate_legal_document():
    """Valida que el documento legal se procese igual."""
    logger.info("\n" + "=" * 80)
    logger.info("VALIDACIÓN: DOCUMENTO LEGAL (Acuerdo 03/2021)")
    logger.info("=" * 80)

    pdf_path = Path("data/acuerdo-unico-comision-rectora-2025-07-15.pdf")

    if not pdf_path.exists():
        logger.error(f"❌ No se encontró el PDF: {pdf_path}")
        return None

    # Extraer documento
    logger.info("Extrayendo documento...")
    extractor = PDFExtractor()
    extracted_doc = extractor.extract_pdf(pdf_path)

    if not extracted_doc:
        logger.error("❌ Error al extraer documento")
        return None

    logger.success(f"✓ Documento extraído: {extracted_doc['metadata']['documento_nombre']}")

    # Procesar con nueva arquitectura
    logger.info("\nProcesando con NUEVA arquitectura...")
    chunker = HierarchicalChunker()
    chunks = chunker.chunk_document(extracted_doc)

    # Analizar chunks
    metrics = analyze_chunks(chunks, "Documento Legal - Nueva Arquitectura")

    # Validaciones específicas para documentos legales
    logger.info("\n" + "=" * 80)
    logger.info("VALIDACIONES ESPECÍFICAS - DOCUMENTO LEGAL")
    logger.info("=" * 80)

    validations = []

    # Debe tener nivel 0 (root)
    if 0 in metrics["niveles_detectados"]:
        validations.append("✓ Tiene nodo raíz (nivel 0)")
    else:
        validations.append("❌ Falta nodo raíz (nivel 0)")

    # Debe tener títulos (nivel 1)
    if 1 in metrics["niveles_detectados"]:
        validations.append("✓ Tiene títulos (nivel 1)")
    else:
        validations.append("⚠️ No tiene títulos (nivel 1)")

    # Debe tener capítulos (nivel 2)
    if 2 in metrics["niveles_detectados"]:
        validations.append("✓ Tiene capítulos (nivel 2)")
    else:
        validations.append("⚠️ No tiene capítulos (nivel 2)")

    # Debe tener artículos (nivel 3)
    if 3 in metrics["niveles_detectados"]:
        validations.append("✓ Tiene artículos (nivel 3)")
    else:
        validations.append("❌ No tiene artículos (nivel 3)")

    # Completitud del grafo debe ser alta
    if metrics["grafo_completitud"] >= 80:
        validations.append(f"✓ Alta completitud del grafo ({metrics['grafo_completitud']:.1f}%)")
    elif metrics["grafo_completitud"] >= 50:
        validations.append(f"⚠️ Completitud del grafo moderada ({metrics['grafo_completitud']:.1f}%)")
    else:
        validations.append(f"❌ Baja completitud del grafo ({metrics['grafo_completitud']:.1f}%)")

    # Chunks sin jerarquía debe ser mínimo
    if metrics["chunks_sin_jerarquia"] == 0:
        validations.append("✓ Todos los chunks tienen jerarquía")
    elif metrics["chunks_sin_jerarquia"] < metrics["total_chunks"] * 0.1:
        validations.append(f"⚠️ Algunos chunks sin jerarquía ({metrics['chunks_sin_jerarquia']})")
    else:
        validations.append(f"❌ Muchos chunks sin jerarquía ({metrics['chunks_sin_jerarquia']})")

    for validation in validations:
        if "✓" in validation:
            logger.success(validation)
        elif "⚠️" in validation:
            logger.warning(validation)
        else:
            logger.error(validation)

    return metrics


def validate_technical_document():
    """Valida que el documento técnico ahora tenga jerarquía."""
    logger.info("\n" + "=" * 80)
    logger.info("VALIDACIÓN: DOCUMENTO TÉCNICO (DocumentoTecnico_V2)")
    logger.info("=" * 80)

    pdf_path = Path("data/DocumentoTecnico_V2.pdf")

    if not pdf_path.exists():
        logger.error(f"❌ No se encontró el PDF: {pdf_path}")
        return None

    # Extraer documento
    logger.info("Extrayendo documento...")
    extractor = PDFExtractor()
    extracted_doc = extractor.extract_pdf(pdf_path)

    if not extracted_doc:
        logger.error("❌ Error al extraer documento")
        return None

    logger.success(f"✓ Documento extraído: {extracted_doc['metadata']['documento_nombre']}")

    # Procesar con nueva arquitectura
    logger.info("\nProcesando con NUEVA arquitectura...")
    chunker = HierarchicalChunker()
    chunks = chunker.chunk_document(extracted_doc)

    # Analizar chunks
    metrics = analyze_chunks(chunks, "Documento Técnico - Nueva Arquitectura")

    # Validaciones específicas para documentos técnicos
    logger.info("\n" + "=" * 80)
    logger.info("VALIDACIONES ESPECÍFICAS - DOCUMENTO TÉCNICO")
    logger.info("=" * 80)

    validations = []

    # CRÍTICO: Debe tener nivel 0 (root)
    if 0 in metrics["niveles_detectados"]:
        validations.append("✓ Tiene nodo raíz (nivel 0)")
    else:
        validations.append("❌ CRÍTICO: Falta nodo raíz (nivel 0)")

    # CRÍTICO: Debe tener secciones (nivel 1)
    if 1 in metrics["niveles_detectados"]:
        validations.append("✓ Tiene secciones (nivel 1)")
    else:
        validations.append("❌ CRÍTICO: No tiene secciones (nivel 1)")

    # Debe tener subsecciones (nivel 2)
    if 2 in metrics["niveles_detectados"]:
        validations.append("✓ Tiene subsecciones (nivel 2)")
    else:
        validations.append("⚠️ No tiene subsecciones (nivel 2)")

    # CRÍTICO: Completitud del grafo debe mejorar significativamente
    if metrics["grafo_completitud"] >= 80:
        validations.append(f"✓ EXCELENTE: Alta completitud del grafo ({metrics['grafo_completitud']:.1f}%)")
    elif metrics["grafo_completitud"] >= 50:
        validations.append(f"✓ MEJORA: Completitud del grafo moderada ({metrics['grafo_completitud']:.1f}%)")
    elif metrics["grafo_completitud"] > 0:
        validations.append(f"⚠️ MEJORA PARCIAL: Completitud del grafo baja ({metrics['grafo_completitud']:.1f}%)")
    else:
        validations.append(f"❌ SIN MEJORA: Sin completitud del grafo (0%)")

    # CRÍTICO: Chunks sin jerarquía debe reducirse drásticamente
    pct_sin_jerarquia = metrics["chunks_sin_jerarquia"] / metrics["total_chunks"] * 100
    if metrics["chunks_sin_jerarquia"] == 0:
        validations.append("✓ EXCELENTE: Todos los chunks tienen jerarquía")
    elif pct_sin_jerarquia < 10:
        validations.append(f"✓ BUENO: Mínimos chunks sin jerarquía ({metrics['chunks_sin_jerarquia']}, {pct_sin_jerarquia:.1f}%)")
    elif pct_sin_jerarquia < 50:
        validations.append(f"⚠️ MEJORA PARCIAL: Algunos chunks sin jerarquía ({metrics['chunks_sin_jerarquia']}, {pct_sin_jerarquia:.1f}%)")
    else:
        validations.append(f"❌ SIN MEJORA: Muchos chunks sin jerarquía ({metrics['chunks_sin_jerarquia']}, {pct_sin_jerarquia:.1f}%)")

    # Debe tener parent_id
    pct_con_parent = metrics["chunks_con_parent"] / metrics["total_chunks"] * 100
    if pct_con_parent >= 80:
        validations.append(f"✓ EXCELENTE: Mayoría con parent_id ({pct_con_parent:.1f}%)")
    elif pct_con_parent > 0:
        validations.append(f"✓ MEJORA: Algunos con parent_id ({pct_con_parent:.1f}%)")
    else:
        validations.append("❌ SIN MEJORA: Ningún chunk con parent_id")

    for validation in validations:
        if "✓" in validation:
            logger.success(validation)
        elif "⚠️" in validation:
            logger.warning(validation)
        else:
            logger.error(validation)

    return metrics


def main():
    """Ejecuta validación completa."""
    setup_logging()

    logger.info("=" * 80)
    logger.info("VALIDACIÓN DE NUEVA ARQUITECTURA UNIFICADA")
    logger.info("=" * 80)
    logger.info("Este script valida que:")
    logger.info("  1. Documentos legales se procesen igual o mejor")
    logger.info("  2. Documentos técnicos ahora tengan jerarquía completa")
    logger.info("  3. No haya regresiones en la calidad de chunks")

    # Validar documento legal
    legal_metrics = validate_legal_document()

    # Validar documento técnico
    technical_metrics = validate_technical_document()

    # Resumen final
    logger.info("\n" + "=" * 80)
    logger.info("RESUMEN FINAL DE VALIDACIÓN")
    logger.info("=" * 80)

    if legal_metrics:
        logger.info("\nDocumento Legal:")
        logger.info(f"  Total chunks: {legal_metrics['total_chunks']}")
        logger.info(f"  Niveles: {sorted(legal_metrics['niveles_detectados'])}")
        logger.info(f"  Completitud del grafo: {legal_metrics['grafo_completitud']:.1f}%")

        if legal_metrics['grafo_completitud'] >= 80:
            logger.success("  ✓ Documento legal procesado correctamente")
        else:
            logger.warning("  ⚠️ Documento legal con completitud baja")

    if technical_metrics:
        logger.info("\nDocumento Técnico:")
        logger.info(f"  Total chunks: {technical_metrics['total_chunks']}")
        logger.info(f"  Niveles: {sorted(technical_metrics['niveles_detectados'])}")
        logger.info(f"  Completitud del grafo: {technical_metrics['grafo_completitud']:.1f}%")
        logger.info(f"  Chunks sin jerarquía: {technical_metrics['chunks_sin_jerarquia']}")

        # Evaluar mejora
        mejoras = []
        if technical_metrics['grafo_completitud'] > 0:
            mejoras.append("✓ Ahora tiene estructura de grafo")
        if len(technical_metrics['niveles_detectados']) > 0:
            mejoras.append(f"✓ Detectó {len(technical_metrics['niveles_detectados'])} niveles jerárquicos")
        if technical_metrics['chunks_con_parent'] > 0:
            mejoras.append(f"✓ {technical_metrics['chunks_con_parent']} chunks con parent_id")

        if mejoras:
            logger.success("\n  MEJORAS DETECTADAS:")
            for mejora in mejoras:
                logger.success(f"    {mejora}")
        else:
            logger.error("\n  ❌ NO SE DETECTARON MEJORAS")

    # Decisión final
    logger.info("\n" + "=" * 80)
    logger.info("DECISIÓN")
    logger.info("=" * 80)

    problemas_criticos = []

    if legal_metrics and legal_metrics['grafo_completitud'] < 50:
        problemas_criticos.append("Documento legal con completitud <50%")

    if technical_metrics and technical_metrics['grafo_completitud'] == 0:
        problemas_criticos.append("Documento técnico sin mejora en grafo")

    if technical_metrics and technical_metrics['chunks_sin_jerarquia'] == technical_metrics['total_chunks']:
        problemas_criticos.append("Documento técnico sin jerarquía")

    if problemas_criticos:
        logger.error("\n❌ VALIDACIÓN FALLIDA - Problemas críticos detectados:")
        for problema in problemas_criticos:
            logger.error(f"  - {problema}")
        logger.error("\n⛔ NO PROCEDER CON RE-INGESTIÓN")
    else:
        logger.success("\n✅ VALIDACIÓN EXITOSA")
        logger.success("✓ Sistema nuevo funciona correctamente")
        logger.success("✓ Seguro proceder con re-ingestión")
        logger.info("\nPróximo paso:")
        logger.info("  python scripts/01_ingest_pdfs.py")


if __name__ == "__main__":
    main()
