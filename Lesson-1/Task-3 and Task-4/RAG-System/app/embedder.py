from langchain_ollama import OllamaEmbeddings
from config.settings import EMBEDDING_MODEL


class EmbeddingModel:
    """
    Generates embeddings using Ollama.
    """

    def __init__(self):

        self.embedding_model = OllamaEmbeddings(
            model=EMBEDDING_MODEL,
        )

    def get_embeddings(self):
        return self.embedding_model