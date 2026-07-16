class RAGPipeline:
    """
    Orchestrates the complete Retrieval-Augmented Generation workflow.

    Flow:
        User Question
              │
              ▼
        Retrieve Documents
              │
              ▼
        Build Context
              │
              ▼
          Generate Answer
    """

    def __init__(self, retriever, llm):
        self.retriever = retriever
        self.llm = llm

    def ask(self, question: str) -> dict:
        """
        Executes the complete RAG pipeline.

        Args:
            question: User question.

        Returns:
            Dictionary containing:
                - question
                - retrieved_documents
                - context
                - answer
        """

        retrieved_documents = self.retriever.retrieve(question)

        context = "\n\n".join(
            document.page_content
            for document in retrieved_documents
        )

        answer = self.llm.generate(
            context=context,
            question=question,
        )

        return {
            "question": question,
            "retrieved_documents": retrieved_documents,
            "context": context,
            "answer": answer,
        }