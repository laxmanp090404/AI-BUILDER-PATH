from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter


class DocumentChunker:

    def __init__(
        self,
        chunk_size,
        chunk_overlap
    ):

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

    def split(self, documents):

        chunks = self.splitter.split_documents(documents)
        source_chunk_counts = {}

        for chunk in chunks:
            raw_source = chunk.metadata.get("source", "Unknown")
            if raw_source != "Unknown":
                source_path = Path(raw_source)
                filename = source_path.name
                file_type = source_path.suffix.lower()
            else:
                filename = "Unknown"
                file_type = "Unknown"

            chunk.metadata["source"] = filename
            chunk.metadata["file_type"] = file_type

            # Calculate chunk ID relative to its source document
            if filename not in source_chunk_counts:
                source_chunk_counts[filename] = 1
            else:
                source_chunk_counts[filename] += 1

            chunk.metadata["chunk_id"] = source_chunk_counts[filename]

            # Format page number: PyPDFLoader provides 0-indexed page numbers
            if "page" in chunk.metadata:
                p = chunk.metadata["page"]
                if isinstance(p, int):
                    chunk.metadata["page"] = p + 1
            else:
                chunk.metadata["page"] = "N/A"

        return chunks