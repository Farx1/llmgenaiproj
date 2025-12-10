"""Document processing and chunking."""
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter

try:
    from langchain_core.documents import Document
except ImportError:
    from langchain_core.documents import Document

from typing import List
import aiofiles
import os


class DocumentProcessor:
    """Processes documents for vectorization."""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        """
        Initialize the document processor.
        
        Args:
            chunk_size: Size of text chunks (default: 1000 as in notebook)
            chunk_overlap: Overlap between chunks (default: 200 as in notebook)
        """
        # Use better separators for cleaner chunking - prioritize complete sentences
        # Priority: paragraphs, complete sentences, lines, words
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=[
                "\n\n\n",  # Multiple paragraphs
                "\n\n",    # Paragraphs
                ".\n",     # Sentence followed by newline
                ". ",      # Complete sentences
                "!\n",     # Exclamation with newline
                "?\n",     # Question with newline
                "\n",      # Lines
                " ",       # Words
                ""         # Characters (last resort)
            ],
            length_function=len,
            keep_separator=True,  # Keep separators to preserve structure
        )
    
    async def process_file(self, file_path: str) -> List[Document]:
        """
        Process a file and return Document objects.
        Supports PDFs using PyPDFLoader (as in the notebook).
        
        Args:
            file_path: Path to the file
        
        Returns:
            List of Document objects
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Handle PDFs with PyPDFLoader (as shown in the notebook)
        if file_ext == '.pdf':
            try:
                from langchain_community.document_loaders import PyPDFLoader
                loader = PyPDFLoader(file_path)
                docs = loader.load()
                
                # Split into chunks
                chunks = self.text_splitter.split_documents(docs)
                
                # Add rich metadata to each chunk (as recommended in the guide)
                for i, chunk in enumerate(chunks):
                    # Basic chunk info
                    chunk.metadata["chunk_index"] = i
                    chunk.metadata["total_chunks"] = len(chunks)
                    
                    # Source information
                    if "source" not in chunk.metadata:
                        chunk.metadata["source"] = file_path
                    if "filename" not in chunk.metadata:
                        chunk.metadata["filename"] = os.path.basename(file_path)
                    
                    # Enhanced metadata for better structure
                    chunk.metadata["chunk_id"] = f"{os.path.basename(file_path)}_chunk_{i}"
                    chunk.metadata["content_type"] = "document"
                    chunk.metadata["chunk_length"] = len(chunk.page_content)
                    chunk.metadata["file_type"] = "pdf"
                
                return chunks
            except ImportError:
                # Fallback if PyPDFLoader is not available
                import logging
                logger = logging.getLogger(__name__)
                logger.warning("PyPDFLoader not available, falling back to text reading")
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error loading PDF: {str(e)}")
                raise
        
        # Handle text files
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            async with aiofiles.open(file_path, 'r', encoding='latin-1') as f:
                content = await f.read()
        
        # Create document with metadata
        doc = Document(
            page_content=content,
            metadata={
                "source": file_path,
                "filename": os.path.basename(file_path),
                "file_type": file_ext
            }
        )
        
        # Split into chunks
        chunks = self.text_splitter.split_documents([doc])
        
        # Add rich metadata to each chunk
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = i
            chunk.metadata["total_chunks"] = len(chunks)
            chunk.metadata["chunk_id"] = f"{os.path.basename(file_path)}_chunk_{i}"
            chunk.metadata["content_type"] = "text"
            chunk.metadata["chunk_length"] = len(chunk.page_content)
            
            # Preserve original metadata from doc
            if "file_type" not in chunk.metadata:
                chunk.metadata["file_type"] = file_ext
        
        return chunks
    
    def process_text(self, text: str, metadata: dict = None) -> List[Document]:
        """
        Process text and return Document objects.
        
        Args:
            text: Text content
            metadata: Optional metadata
        
        Returns:
            List of Document objects
        """
        metadata = metadata or {}
        doc = Document(page_content=text, metadata=metadata)
        chunks = self.text_splitter.split_documents([doc])
        
        # Add rich structured metadata to each chunk
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = i
            chunk.metadata["total_chunks"] = len(chunks)
            chunk.metadata["chunk_id"] = f"{metadata.get('title', 'text')}_chunk_{i}".replace(' ', '_')
            chunk.metadata["content_type"] = metadata.get("content_type", "text")
            chunk.metadata["chunk_length"] = len(chunk.page_content)
            
            # Preserve original metadata
            for key, value in metadata.items():
                if key not in chunk.metadata:
                    chunk.metadata[key] = value
        
        return chunks


# Global instance
document_processor = DocumentProcessor()

