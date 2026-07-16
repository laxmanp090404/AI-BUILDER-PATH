from ingestion.loader_factory import LoaderFactory


class DocumentLoader:

    def load(self, file_path):

        loader = LoaderFactory.get_loader(file_path)

        return loader.load()