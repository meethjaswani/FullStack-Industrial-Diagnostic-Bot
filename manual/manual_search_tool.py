import os
import json
import requests
import tempfile
import shutil
from typing import List, Dict, Any, Optional
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.schema import Document
import logging
from pathlib import Path
import re
from datetime import datetime
from dotenv import load_dotenv
from pypdf import PdfReader

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ManualSearchTool:
    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2", custom_pdf_files: Optional[List[str]] = None):
        # Resolve data/vector_store relative to root
        base_dir = Path(__file__).resolve().parents[1]
        self.vector_store_dir = base_dir / "data" / "vector_store"
        self.embedding_model = embedding_model
        self.vector_store = None
        self.embeddings = None
        self.custom_pdf_files = custom_pdf_files
        self.temp_vector_store_dir = None
        self._initialize_tool()

    def _initialize_tool(self) -> None:
        logger.info("Initializing Manual Search Tool...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name=self.embedding_model,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        if self.custom_pdf_files:
            # Create temporary vector store for custom PDFs
            self._create_temporary_vector_store()
        else:
            # Use default vector store
            if not self.vector_store_dir.exists():
                raise FileNotFoundError(f"Vector store directory not found: {self.vector_store_dir}")
            self.vector_store = Chroma(
                persist_directory=str(self.vector_store_dir),
                embedding_function=self.embeddings,
                collection_name="technical_manuals"
            )
        
        logger.info("Manual Search Tool initialized successfully!")

    def _create_temporary_vector_store(self) -> None:
        """Create a temporary vector store from custom PDF files"""
        try:
            # Create temporary directory
            self.temp_vector_store_dir = tempfile.mkdtemp(prefix="manual_vector_store_")
            logger.info(f"Created temporary vector store at: {self.temp_vector_store_dir}")
            
            # Process PDF files and create documents
            documents = []
            for pdf_path in self.custom_pdf_files:
                try:
                    documents.extend(self._process_pdf_file(pdf_path))
                except Exception as e:
                    logger.error(f"Error processing PDF {pdf_path}: {str(e)}")
            
            if not documents:
                raise ValueError("No valid documents could be extracted from the uploaded PDFs")
            
            # Create vector store
            self.vector_store = Chroma.from_documents(
                documents=documents,
                embedding=self.embeddings,
                persist_directory=self.temp_vector_store_dir,
                collection_name="custom_manuals"
            )
            
            logger.info(f"Created temporary vector store with {len(documents)} documents")
            
        except Exception as e:
            logger.error(f"Error creating temporary vector store: {str(e)}")
            raise

    def _process_pdf_file(self, pdf_path: str) -> List[Document]:
        """Process a PDF file and extract text content"""
        documents = []
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages):
                    text = page.extract_text()
                    if text.strip():
                        # Create document with metadata
                        doc = Document(
                            page_content=text,
                            metadata={
                                'source': Path(pdf_path).name,
                                'page': page_num + 1,
                                'total_pages': len(pdf_reader.pages),
                                'uploaded_at': datetime.now().isoformat()
                            }
                        )
                        documents.append(doc)
                
                logger.info(f"Processed {pdf_path}: {len(documents)} pages with content")
                
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {str(e)}")
            raise
        
        return documents

    def cleanup(self) -> None:
        """Clean up temporary files and directories"""
        if self.temp_vector_store_dir and os.path.exists(self.temp_vector_store_dir):
            try:
                shutil.rmtree(self.temp_vector_store_dir)
                logger.info(f"Cleaned up temporary vector store: {self.temp_vector_store_dir}")
            except Exception as e:
                logger.error(f"Error cleaning up temporary vector store: {str(e)}")

    def _get_ai_explanation(self, query: str, search_results: List[Dict[str, Any]]) -> str:
        """Get AI-powered explanation using Groq API"""
        if not GROQ_API_KEY:
            return "⚠️ Groq API key not configured. Install dotenv and set GROQ_API_KEY for AI explanations."
        
        try:
            # Format search results for the AI
            results_text = "\n\n".join([
                f"Result {i+1} (Score: {result['relevance_score']:.3f}):\n"
                f"Source: {result['metadata']['source']} - Page {result['metadata']['page']}\n"
                f"Content: {result['content']}"
                for i, result in enumerate(search_results)
            ])
            
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama3-8b-8192",
                    "messages": [
                        {
                            "role": "system", 
                            "content": "You are a technical manual expert. Analyze the search results and provide a clear, helpful explanation. Focus on practical insights and actionable information."
                        },
                        {
                            "role": "user", 
                            "content": f"Query: {query}\n\nSearch Results:\n{results_text}\n\nPlease provide a clear explanation of what was found and any relevant insights."
                        }
                    ],
                    "temperature": 0.3
                }
            )
            
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                return f"❌ Groq API error: {response.status_code}"
                
        except Exception as e:
            logger.error(f"Error getting AI explanation: {str(e)}")
            return f"⚠️ AI explanation unavailable: {str(e)}"

    def search(self, query: str, top_k: int = 5, filter_metadata: Optional[Dict] = None, include_ai_explanation: bool = True) -> Dict[str, Any]:
        logger.info(f"Searching for: '{query}' (top_k={top_k})")
        if not query.strip():
            logger.warning("Empty query provided")
            return {"results": [], "ai_explanation": "No query provided"}

        processed_query = self._preprocess_query(query)

        results = self.vector_store.similarity_search_with_score(
            processed_query,
            k=top_k,
            filter=filter_metadata if filter_metadata else None
        )

        formatted_results = []
        for i, (doc, score) in enumerate(results):
            result = {
                "content": doc.page_content,
                "metadata": {
                    "source": doc.metadata.get('source', 'Unknown'),
                    "page": doc.metadata.get('page', 'Unknown'),
                },
                "relevance_score": float(1 - score),
                "rank": i + 1
            }
            formatted_results.append(result)

        # Get AI explanation if requested and API key is available
        ai_explanation = ""
        if include_ai_explanation and formatted_results:
            ai_explanation = self._get_ai_explanation(query, formatted_results)

        logger.info(f"Found {len(formatted_results)} results")
        return {
            "results": formatted_results,
            "ai_explanation": ai_explanation,
            "total_results": len(formatted_results)
        }

    def _preprocess_query(self, query: str) -> str:
        query_mapping = {
            'temp': 'temperature',
            'press': 'pressure',
            'vib': 'vibration',
            'rpm': 'rotations per minute',
            'psi': 'pressure',
            'err': 'error',
            'troubleshoot': 'troubleshooting diagnosis problem',
            'fix': 'repair solution troubleshooting',
            'alarm': 'error alarm warning',
            'fault': 'error fault problem',
            'maintenance': 'maintenance service repair',
            'calibration': 'calibration adjustment setup',
            'installation': 'installation setup configuration'
        }
        processed_query = query.lower()
        for abbr, full_form in query_mapping.items():
            processed_query = re.sub(r'\b' + abbr + r'\b', full_form, processed_query)
        return processed_query

    def search_by_error_code(self, error_code: str, top_k: int = 3) -> Dict[str, Any]:
        query = f"error code {error_code} troubleshooting diagnosis solution"
        return self.search(query, top_k)

    def search_by_equipment_type(self, equipment_type: str, query: str, top_k: int = 5) -> Dict[str, Any]:
        return self.search(query, top_k, {"equipment_type": equipment_type})

    def get_procedure_steps(self, procedure_name: str, top_k: int = 5) -> Dict[str, Any]:
        query = f"{procedure_name} procedure steps instructions method process"
        return self.search(query, top_k)

    def get_safety_information(self, context: str, top_k: int = 3) -> Dict[str, Any]:
        query = f"{context} safety precautions warning danger hazard protection"
        return self.search(query, top_k)

    def get_specifications(self, equipment_name: str, spec_type: str, top_k: int = 3) -> Dict[str, Any]:
        query = f"{equipment_name} {spec_type} specification limits range parameters"
        return self.search(query, top_k)

    def get_tool_info(self) -> Dict[str, Any]:
        try:
            metadata_path = self.vector_store_dir / "processing_metadata.json"
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    processing_metadata = json.load(f)
            else:
                processing_metadata = {}

            collection_info = self.vector_store._collection.count()

            return {
                "tool_name": "Manual Search Tool",
                "version": "2.0.0",
                "embedding_model": self.embedding_model,
                "ai_model": "llama3-8b-8192 (Groq API)" if GROQ_API_KEY else "Not configured",
                "vector_store_path": str(self.vector_store_dir),
                "total_documents": collection_info,
                "processing_metadata": processing_metadata,
                "groq_api_configured": bool(GROQ_API_KEY),
                "capabilities": [
                    "Semantic search across technical manuals",
                    "AI-powered result explanation and insights",
                    "Error code lookup",
                    "Equipment-specific search",
                    "Procedure step retrieval",
                    "Safety information search",
                    "Technical specifications lookup"
                ]
            }

        except Exception as e:
            logger.error(f"Error getting tool info: {str(e)}")
            return {"error": str(e)}

    def search_without_ai(self, query: str, top_k: int = 5, filter_metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Search without AI explanation for faster results"""
        return self.search(query, top_k, filter_metadata, include_ai_explanation=False)

# Run interactively
if __name__ == "__main__":
    print("🛠 Manual Search Tool Loaded ✅")
    print(f"🤖 AI Integration: {'Enabled' if GROQ_API_KEY else 'Disabled (set GROQ_API_KEY)'}")
    
    tool = ManualSearchTool()

    while True:
        print("\nChoose Search Type:")
        print("1. General Search (with AI explanation)")
        print("2. General Search (without AI - faster)")
        print("3. Error Code")
        print("4. Procedure")
        print("5. Safety Info")
        print("6. Specification")
        print("7. Tool Info")
        print("8. Exit")
        choice = input("Enter choice (1-8): ").strip()

        if choice == "8":
            print("👋 Exiting...")
            break

        if choice == "7":
            info = tool.get_tool_info()
            print(f"\n📊 Tool Information:")
            print(f"  Version: {info.get('version', 'Unknown')}")
            print(f"  Embedding Model: {info.get('embedding_model', 'Unknown')}")
            print(f"  AI Model: {info.get('ai_model', 'Unknown')}")
            print(f"  Groq API: {'✅ Configured' if info.get('groq_api_configured') else '❌ Not configured'}")
            print(f"  Total Documents: {info.get('total_documents', 'Unknown')}")
            continue

        query = input("\n🔍 Enter your query: ").strip()
        if not query:
            print("⚠️ Please enter a valid query.")
            continue

        try:
            if choice == "1":
                results = tool.search(query)
            elif choice == "2":
                results = tool.search_without_ai(query)
            elif choice == "3":
                results = tool.search_by_error_code(query)
            elif choice == "4":
                results = tool.get_procedure_steps(query)
            elif choice == "5":
                results = tool.get_safety_information(query)
            elif choice == "6":
                parts = query.split()
                if len(parts) >= 2:
                    equipment = parts[0]
                    spec_type = " ".join(parts[1:])
                    results = tool.get_specifications(equipment, spec_type)
                else:
                    print("⚠️ Please provide equipment and spec type (e.g., 'motor temperature').")
                    continue
            else:
                print("❌ Invalid choice.")
                continue

            print(f"\n📄 Found {results.get('total_results', 0)} Results:")
            
            # Display search results
            for i, result in enumerate(results["results"]):
                print(f"\nResult {i+1}:")
                print(f"  📘 Source: {result['metadata']['source']} - Page {result['metadata']['page']}")
                print(f"  🔍 Score: {result['relevance_score']:.3f}")
                print(f"  📝 Content: {result['content']}\n")

            # Display AI explanation if available
            if results.get("ai_explanation"):
                print("\n🤖 AI Explanation:")
                print("=" * 50)
                print(results["ai_explanation"])
                print("=" * 50)

        except Exception as e:
            print(f"❌ Error during search: {str(e)}")
            logger.error(f"Search error: {str(e)}")
