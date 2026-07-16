from pathlib import Path

from config.settings import RAW_DATA_DIR


class DocumentManager:

    SUPPORTED_EXTENSIONS = {
        ".txt",
        ".md",
        ".pdf",
        ".docx",
    }

    def discover_documents(self):

        files = []

        for file in RAW_DATA_DIR.iterdir():

            if (
                file.is_file()
                and file.suffix.lower()
                in self.SUPPORTED_EXTENSIONS
            ):

                files.append(file)

        return sorted(files)