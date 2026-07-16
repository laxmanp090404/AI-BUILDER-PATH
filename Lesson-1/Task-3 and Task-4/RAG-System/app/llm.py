import re
from langchain_ollama import ChatOllama
from config.settings import LLM_MODEL, PROMPTS_DIR


class LLM:

    def __init__(self):

        self.llm = ChatOllama(
            model=LLM_MODEL,
            temperature=0
        )
        
        prompt_path = PROMPTS_DIR / "rag_prompt.txt"
        if prompt_path.exists():
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.prompt_template = f.read()
        else:
            # Fallback prompt template if file is missing
            self.prompt_template = (
                "You are an AI assistant.\n\n"
                "Context:\n{context}\n\n"
                "Question:\n{question}"
            )

    def generate(
        self,
        context,
        question
    ):

        prompt = self.prompt_template.format(
            context=context,
            question=question
        )

        response = self.llm.invoke(prompt)
        
        # Clean thinking tags from reasoning models (e.g. deepseek-r1)
        cleaned_content = re.sub(r'<thought>.*?</thought>', '', response.content, flags=re.DOTALL)

        return cleaned_content.strip()