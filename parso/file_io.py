import os


class FileIO:
    def __init__(self, path):
        self.path = path

    def read(self):
        with open(self.path) as f:
            return f.read()

    def get_last_modified(self):
        """
        Returns float - timestamp
        Might raise FileNotFoundError
        """
        return os.path.getmtime(self.path)


class KnownContentFileIO(FileIO):
    def __init__(self, path, content):
        super(KnownContentFileIO, self).__init__(path)
        self._content = content

    def read(self):
        return self._content
