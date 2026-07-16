from langchain_chroma import Chroma
from config.settings import VECTOR_STORE_DIR, TOP_K_RESULTS
class Retriever:

    def __init__(self, embeddings):

        self.db = Chroma(
            persist_directory=VECTOR_STORE_DIR,
            embedding_function=embeddings
        )

    def retrieve(
        self,
        query,
        k=TOP_K_RESULTS
    ):

        return self.db.similarity_search(
            query,
            k=k
        )