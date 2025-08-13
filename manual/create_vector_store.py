import os
import shutil
from typing import List
from pathlib import Path
import logging
import json
from datetime import datetime

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.schema import Document

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VectorStoreManager:
    """Manages the creation and maintenance of the vector store for technical manuals."""
    
    def __init__(self, 
                 chunk_size: int = 1000,
                 chunk_overlap: int = 200,
                 embedding_model: str = "all-MiniLM-L6-v2"):
        # Define root-relative paths
        base_dir = Path(__file__).resolve().parents[1]
        self.pdf_source_dir = base_dir / "data" / "pdf_manuals"
        self.vector_store_dir = base_dir / "data" / "vector_store"
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embedding_model = embedding_model

        # Create required directories
        self.pdf_source_dir.mkdir(parents=True, exist_ok=True)

        # Text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

        # Embeddings
        logger.info(f"Using HuggingFace embeddings: {self.embedding_model}")
        self.embeddings = HuggingFaceEmbeddings(
            model_name=self.embedding_model,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )

    def clean_existing_store(self) -> None:
        if self.vector_store_dir.exists():
            logger.info(f"Removing existing vector store at {self.vector_store_dir}")
            shutil.rmtree(self.vector_store_dir)

    def load_pdf_documents(self) -> List[Document]:
        logger.info(f"Loading PDFs from {self.pdf_source_dir}")
        documents = []
        pdf_files = list(self.pdf_source_dir.glob("*.pdf"))

        if not pdf_files:
            logger.warning("No PDF files found.")
            return []

        for pdf in pdf_files:
            try:
                loader = PyPDFLoader(str(pdf))
                pdf_docs = loader.load()
                for i, doc in enumerate(pdf_docs):
                    doc.metadata.update({
                        'source_file': pdf.name,
                        'file_path': str(pdf),
                        'page_number': i + 1,
                        'total_pages': len(pdf_docs),
                        'equipment_type': self._extract_equipment_type(pdf.name),
                        'processed_date': datetime.now().isoformat()
                    })
                documents.extend(pdf_docs)
            except Exception as e:
                logger.error(f"Failed to load {pdf.name}: {str(e)}")

        logger.info(f"Loaded {len(documents)} documents")
        return documents

    def _extract_equipment_type(self, filename: str) -> str:
        keywords = {
            'kuka': 'Robot', 'fanuc': 'Robot', 'siemens': 'PLC',
            'allen-bradley': 'VFD', 'powerflex': 'VFD',
            'simatic': 'PLC', 'schneider': 'VFD', 'abb': 'Motor Control',
            'mitsubishi': 'PLC'
        }
        name = filename.lower()
        for key, val in keywords.items():
            if key in name:
                return val
        return 'Industrial Equipment'

    def create_chunks(self, docs: List[Document]) -> List[Document]:
        chunks = self.text_splitter.split_documents(docs)
        for i, chunk in enumerate(chunks):
            chunk.metadata.update({
                'chunk_id': f"chunk_{i:06d}",
                'chunk_size': len(chunk.page_content),
                'chunk_index': i
            })
        return chunks

    def create_vector_store(self, chunks: List[Document]) -> Chroma:
        return Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=str(self.vector_store_dir),
            collection_name="technical_manuals"
        )

    def save_metadata(self, docs: List[Document], chunks: List[Document]) -> None:
        meta = {
            "processing_date": datetime.now().isoformat(),
            "total_documents": len(docs),
            "total_chunks": len(chunks),
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "embedding_model": self.embedding_model,
            "source_files": list({d.metadata.get("source_file", "unknown") for d in docs})
        }
        with open(self.vector_store_dir / "processing_metadata.json", "w") as f:
            json.dump(meta, f, indent=2)

    def _verify_vector_store(self) -> None:
        try:
            vs = Chroma(
                persist_directory=str(self.vector_store_dir),
                embedding_function=self.embeddings,
                collection_name="technical_manuals"
            )
            results = vs.similarity_search("troubleshooting high temperature error", k=3)
            for i, r in enumerate(results):
                logger.info(f"Result {i+1}: {r.metadata.get('source_file', 'Unknown')} - Page {r.metadata.get('page_number', '?')}")
        except Exception as e:
            logger.error(f"Verification failed: {str(e)}")

    def run_full_pipeline(self) -> None:
        logger.info("Starting vector store pipeline")
        self.clean_existing_store()
        docs = self.load_pdf_documents()
        if not docs:
            logger.error("No documents loaded. Add PDFs to data/pdf_manuals.")
            return
        chunks = self.create_chunks(docs)
        self.create_vector_store(chunks)
        self.save_metadata(docs, chunks)
        self._verify_vector_store()
        logger.info("Vector store pipeline complete")

def main():
    manager = VectorStoreManager()
    manager.run_full_pipeline()

if __name__ == "__main__":
    main()
