from config.settings import (
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    VECTOR_STORE_DIR,
    PROCESSED_DATA_DIR,
)

from ingestion.document_manager import DocumentManager
from loader import DocumentLoader
from chunker import DocumentChunker

from embedder import EmbeddingModel
from vector_store import VectorStore
from retriever import Retriever
from llm import LLM

from pipeline.rag_pipeline import RAGPipeline


def build_database(embedding_model):
    """
    Builds the vector database from all supported
    documents found inside data/raw.
    """

    manager = DocumentManager()
    loader = DocumentLoader()

    try:
        files = manager.discover_documents()
    except FileNotFoundError:
        print("\nError: data/raw directory not found.")
        files = []

    if not files:
        raise FileNotFoundError(
            "No supported documents found in data/raw."
        )

    documents = []

    print("\nLoading Documents...\n")

    for file in files:
        try:
            print(f"Loading : {file.name}")
            loaded_docs = loader.load(file)
            if loaded_docs:
                documents.extend(loaded_docs)
            else:
                print(f"Warning: Document {file.name} is empty.")
        except Exception as e:
            print(f"Error loading {file.name}: {e}. Skipping this file.")

    if not documents:
        raise ValueError(
            "No valid document content was loaded. Cannot build knowledge base."
        )

    print(f"\nDocuments Loaded : {len(documents)}")

    chunker = DocumentChunker(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )

    chunks = chunker.split(documents)

    print(f"Chunks Created : {len(chunks)}")

    # Store processed data in data/processed
    import json
    try:
        PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
        chunks_by_source = {}
        for chunk in chunks:
            src = chunk.metadata.get("source", "Unknown")
            if src not in chunks_by_source:
                chunks_by_source[src] = []
            chunks_by_source[src].append({
                "page_content": chunk.page_content,
                "metadata": chunk.metadata
            })
        
        for src, src_chunks in chunks_by_source.items():
            processed_file_path = PROCESSED_DATA_DIR / f"{src}.json"
            with open(processed_file_path, "w", encoding="utf-8") as f:
                json.dump(src_chunks, f, indent=2, ensure_ascii=False)
            print(f"Saved processed chunks to: {processed_file_path}")
    except Exception as e:
        print(f"Warning: Could not save processed chunks to {PROCESSED_DATA_DIR}: {e}")

    vector_store = VectorStore(
        embedding_model.get_embeddings()
    )


    vector_store.create(chunks)

    print("\nKnowledge Base Created Successfully.\n")


def main():

    print("=" * 60)
    print("Local RAG System - Knowledge Base Setup")
    print("=" * 60)

    embedding_model = EmbeddingModel()
    
    # Check if vector store exists
    db_exists = VECTOR_STORE_DIR.exists() and (VECTOR_STORE_DIR / "chroma.sqlite3").exists()
    
    rebuild = True
    if db_exists:
        print("\nAn existing knowledge base was found.")
        print("1. Reuse existing knowledge base")
        print("2. Rebuild knowledge base (re-ingest documents)")
        choice = input("Select option (1/2) [default: 1]: ").strip()
        if choice == "2":
            rebuild = True
        else:
            rebuild = False
            print("\nReusing the existing knowledge base.")

    if rebuild:
        try:
            build_database(embedding_model)
        except Exception as e:
            print(f"\nFailed to build knowledge base: {e}")
            if db_exists:
                print("Falling back to reusing the existing knowledge base.")
            else:
                print("Cannot proceed without a knowledge base. Exiting.")
                return

    retriever = Retriever(
        embedding_model.get_embeddings()
    )

    llm = LLM()

    rag = RAGPipeline(
        retriever=retriever,
        llm=llm,
    )

    print("\nRAG System Ready\n")

    while True:
        try:
            question = input(
                "Question (type 'exit' to quit): "
            ).strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not question:
            continue

        if question.lower() == "exit":
            print("\nGoodbye!")
            break

        result = rag.ask(question)

        print("\n" + "=" * 60)
        print("Retrieved Documents")
        print("=" * 60)

        for index, document in enumerate(
            result["retrieved_documents"],
            start=1,
        ):
            metadata = document.metadata

            print(f"\nDocument {index}\n")
            print(f"Source : {metadata.get('source')}")
            print(f"Page   : {metadata.get('page')}")
            print(f"Chunk  : {metadata.get('chunk_id')}")

            print(f"\n{'-' * 60}")
            print(document.page_content)

        print("\n" + "=" * 60)
        print("Answer")
        print("=" * 60)

        print(result["answer"])
        print()


if __name__ == "__main__":
    main()