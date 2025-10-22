"""
BM25 Encoder for Sparse Vectors.
Implements BM25 algorithm for keyword-based search with Qdrant.
"""
import re
import math
from typing import List, Dict, Tuple
from collections import Counter
from loguru import logger


class BM25Encoder:
    """
    BM25 encoder for generating sparse vectors.

    Sparse vectors are ideal for exact keyword matching and complement
    dense semantic vectors (OpenAI embeddings).
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        Initialize BM25 encoder.

        Args:
            k1: Term frequency saturation parameter (default 1.5)
            b: Length normalization parameter (default 0.75)
        """
        self.k1 = k1
        self.b = b
        self.vocabulary = {}  # term -> term_id
        self.term_id_counter = 0
        self.doc_count = 0
        self.avgdl = 0  # Average document length
        self.doc_freqs = Counter()  # term -> number of documents containing term
        self.idf = {}  # term -> IDF score

    def fit(self, texts: List[str]) -> None:
        """
        Build vocabulary and calculate IDF scores.

        Args:
            texts: List of document texts
        """
        logger.info(f"Building BM25 vocabulary from {len(texts)} documents")

        self.doc_count = len(texts)
        doc_lengths = []

        # First pass: build vocabulary and count document frequencies
        for text in texts:
            tokens = self._tokenize(text)
            doc_lengths.append(len(tokens))

            # Count unique terms in this document
            unique_tokens = set(tokens)
            for token in unique_tokens:
                self.doc_freqs[token] += 1

                # Add to vocabulary if new
                if token not in self.vocabulary:
                    self.vocabulary[token] = self.term_id_counter
                    self.term_id_counter += 1

        # Calculate average document length
        self.avgdl = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 0

        # Calculate IDF scores
        for term, doc_freq in self.doc_freqs.items():
            # IDF = log((N - df + 0.5) / (df + 0.5) + 1)
            self.idf[term] = math.log(
                (self.doc_count - doc_freq + 0.5) / (doc_freq + 0.5) + 1
            )

        logger.info(f"✓ Vocabulary size: {len(self.vocabulary)} terms")
        logger.info(f"✓ Average document length: {self.avgdl:.1f} tokens")

    def encode_documents(self, texts: List[str]) -> List[Dict]:
        """
        Encode documents to sparse vectors.

        Args:
            texts: List of document texts

        Returns:
            List of sparse vectors in Qdrant format
        """
        sparse_vectors = []

        for text in texts:
            sparse_vector = self.encode_query(text)
            sparse_vectors.append(sparse_vector)

        return sparse_vectors

    def encode_query(self, text: str) -> Dict:
        """
        Encode a single text/query to sparse vector.

        Args:
            text: Input text

        Returns:
            Sparse vector dict with 'indices' and 'values'
        """
        tokens = self._tokenize(text)
        doc_length = len(tokens)

        # Count term frequencies
        term_freqs = Counter(tokens)

        # Calculate BM25 scores
        indices = []
        values = []

        for term, tf in term_freqs.items():
            if term not in self.vocabulary:
                continue  # Skip OOV terms

            term_id = self.vocabulary[term]
            idf_score = self.idf.get(term, 0)

            # BM25 score = IDF * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avgdl))
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (
                1 - self.b + self.b * doc_length / self.avgdl
            )
            bm25_score = idf_score * (numerator / denominator)

            if bm25_score > 0:  # Only include non-zero scores
                indices.append(term_id)
                values.append(bm25_score)

        return {
            "indices": indices,
            "values": values
        }

    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text for BM25.

        Args:
            text: Input text

        Returns:
            List of tokens (lowercased, alphanumeric only)
        """
        # Lowercase
        text = text.lower()

        # Remove special characters, keep only alphanumeric and spaces
        text = re.sub(r'[^a-záéíóúñ0-9\s]', ' ', text)

        # Split into tokens
        tokens = text.split()

        # Filter out very short tokens and stopwords
        tokens = [
            t for t in tokens
            if len(t) >= 2 and t not in self._get_stopwords()
        ]

        return tokens

    def _get_stopwords(self) -> set:
        """
        Get Spanish stopwords.

        Returns:
            Set of common Spanish stopwords
        """
        return {
            'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'ser', 'se', 'no',
            'lo', 'un', 'por', 'con', 'para', 'su', 'al', 'del', 'las', 'los',
            'una', 'como', 'del', 'esto', 'ese', 'este', 'esta', 'estos',
            'estas', 'esos', 'esas', 'mi', 'tu', 'su', 'nos', 'vos', 'os',
            'le', 'les', 'me', 'te', 'si', 'pero', 'mas', 'o', 'u', 'ni',
            'ya', 'muy', 'mas', 'aun', 'mas', 'si', 'solo', 'solo', 'yo',
            'tu', 'el', 'ella', 'nosotros', 'vosotros', 'ellos', 'ellas'
        }

    def save_vocabulary(self, filepath: str) -> None:
        """
        Save vocabulary to file.

        Args:
            filepath: Path to save vocabulary
        """
        import json

        data = {
            'vocabulary': self.vocabulary,
            'idf': self.idf,
            'doc_count': self.doc_count,
            'avgdl': self.avgdl,
            'doc_freqs': dict(self.doc_freqs),
            'k1': self.k1,
            'b': self.b
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Vocabulary saved to {filepath}")

    def load_vocabulary(self, filepath: str) -> None:
        """
        Load vocabulary from file.

        Args:
            filepath: Path to vocabulary file
        """
        import json

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.vocabulary = data['vocabulary']
        self.idf = data['idf']
        self.doc_count = data['doc_count']
        self.avgdl = data['avgdl']
        self.doc_freqs = Counter(data['doc_freqs'])
        self.k1 = data['k1']
        self.b = data['b']
        self.term_id_counter = max(self.vocabulary.values()) + 1 if self.vocabulary else 0

        logger.info(f"Vocabulary loaded from {filepath}")
        logger.info(f"  Vocabulary size: {len(self.vocabulary)}")
