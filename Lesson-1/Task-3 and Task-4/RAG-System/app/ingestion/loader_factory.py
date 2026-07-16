from pathlib import Path

from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    Docx2txtLoader,
)


class LoaderFactory:

    @staticmethod
    def get_loader(file_path: Path):

        extension = file_path.suffix.lower()

        if extension == ".txt":
            return TextLoader(str(file_path))

        if extension == ".md":
            return TextLoader(str(file_path))

        if extension == ".pdf":
            return PyPDFLoader(str(file_path))

        if extension == ".docx":
            return Docx2txtLoader(str(file_path))

        raise ValueError(
            f"Unsupported file type: {extension}"
        )