"""
PDF Ingestion Script.
Orchestrates the complete pipeline: extraction → chunking → vectorization.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from src.config import config
from src.ingest.pdf_extractor import extract_all_pdfs
from src.ingest.chunker import chunk_documents
from src.ingest.vectorizer import vectorize_chunks
from src.ingest.section_mapper import SectionMapper
import time


def setup_logging():
    """Configure logging."""
    logger.remove()  # Remove default handler
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=config.logging.level,
    )
    logger.add(
        config.logging.file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
        level=config.logging.level,
        rotation="10 MB",
    )


def main():
    """Main ingestion pipeline."""
    setup_logging()

    logger.info("=" * 60)
    logger.info("RAG INGESTION PIPELINE - STARTING")
    logger.info("=" * 60)

    start_time = time.time()

    try:
        # Validate configuration
        config.validate()
        logger.info("Configuration validated successfully")
        logger.info(f"Data directory: {config.data_dir}")

        # PHASE 1: Extract PDFs
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 1: EXTRACTING PDFs")
        logger.info("=" * 60)

        documents = extract_all_pdfs(config.data_dir)

        if not documents:
            logger.error("No documents extracted. Exiting.")
            return

        logger.info(f"✓ Extracted {len(documents)} documents")

        # Show document summaries
        for doc in documents:
            metadata = doc["metadata"]
            logger.info(
                f"  - {metadata['documento_nombre']} "
                f"({len(doc['content'])} characters, "
                f"{len(doc['structure']['articulos'])} artículos)"
            )

        # PHASE 2: Chunk documents
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 2: CHUNKING DOCUMENTS")
        logger.info("=" * 60)

        chunks = chunk_documents(
            documents, chunk_size=config.retrieval.chunk_size
        )

        logger.info(f"✓ Created {len(chunks)} chunks")

        # Show chunk statistics
        total_tokens = sum(chunk["longitud_tokens"] for chunk in chunks)
        avg_tokens = total_tokens / len(chunks) if chunks else 0

        logger.info(f"  - Total tokens: {total_tokens:,}")
        logger.info(f"  - Average tokens per chunk: {avg_tokens:.1f}")

        # Count chunks per document
        doc_counts = {}
        for chunk in chunks:
            doc_id = chunk["documento_id"]
            doc_counts[doc_id] = doc_counts.get(doc_id, 0) + 1

        for doc_id, count in doc_counts.items():
            logger.info(f"  - {doc_id}: {count} chunks")

        # PHASE 2.5: Build section mappings (nombre → número)
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 2.5: BUILDING SECTION MAPPINGS")
        logger.info("=" * 60)

        section_mapper = SectionMapper()
        section_mapper.build_from_chunks(chunks)

        # Show mapping stats
        stats = section_mapper.get_stats()
        logger.info(f"✓ Mappings created for {stats['total_documentos']} documents")
        for doc_id, doc_stats in stats['por_documento'].items():
            logger.info(f"  - {doc_id}:")
            for field_type, count in doc_stats.items():
                logger.info(f"      {field_type}: {count} mappings")

        # PHASE 3: Generate embeddings and upload
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 3: VECTORIZING AND UPLOADING")
        logger.info("=" * 60)

        vectorizer = vectorize_chunks(chunks, recreate_collection=True)

        logger.info("✓ Vectorization completed")

        # Show collection info
        info = vectorizer.get_collection_info()
        logger.info(f"  - Collection: {info.get('name')}")
        logger.info(f"  - Vectors: {info.get('vectors_count')}")
        logger.info(f"  - Status: {info.get('status')}")
        logger.info(f"  - Total cost: ${vectorizer.total_cost:.6f}")

        # Final summary
        elapsed_time = time.time() - start_time

        logger.info("\n" + "=" * 60)
        logger.info("PIPELINE COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
        logger.info(f"✓ Documents processed: {len(documents)}")
        logger.info(f"✓ Chunks created: {len(chunks)}")
        logger.info(f"✓ Vectors uploaded: {info.get('vectors_count', 0)}")
        logger.info(f"✓ Total cost: ${vectorizer.total_cost:.6f}")
        logger.info(f"✓ Time elapsed: {elapsed_time:.2f} seconds")

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        logger.exception("Full traceback:")
        sys.exit(1)


if __name__ == "__main__":
    main()
