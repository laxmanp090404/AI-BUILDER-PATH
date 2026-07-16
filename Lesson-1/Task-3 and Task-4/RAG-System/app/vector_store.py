import shutil
from pathlib import Path
from langchain_chroma import Chroma
from config.settings import VECTOR_STORE_DIR

class VectorStore:

    def __init__(
        self,
        embeddings
    ):

        self.embeddings = embeddings

    def create(self, chunks, clear_existing=True):

        if clear_existing and VECTOR_STORE_DIR.exists():
            try:
                shutil.rmtree(VECTOR_STORE_DIR)
            except Exception as e:
                print(f"Warning: Could not clear vector store directory: {e}")

        db = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=str(VECTOR_STORE_DIR)
        )

        return db