"""Document processing and chunking."""
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
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
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
        """
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )
    
    async def process_file(self, file_path: str) -> List[Document]:
        """
        Process a file and return Document objects.
        
        Args:
            file_path: Path to the file
        
        Returns:
            List of Document objects
        """
        # Read file content
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            content = await f.read()
        
        # Create document with metadata
        doc = Document(
            page_content=content,
            metadata={
                "source": file_path,
                "filename": os.path.basename(file_path),
                "file_type": os.path.splitext(file_path)[1]
            }
        )
        
        # Split into chunks
        chunks = self.text_splitter.split_documents([doc])
        
        # Add chunk index to metadata
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = i
            chunk.metadata["total_chunks"] = len(chunks)
        
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
        
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = i
            chunk.metadata["total_chunks"] = len(chunks)
        
        return chunks


# Global instance
document_processor = DocumentProcessor()

