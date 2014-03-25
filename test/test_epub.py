import unittest
from tempfile import NamedTemporaryFile
from pyepub import EPUB


class TestsEpubFileOpen(unittest.TestCase):

    def setUp(self):
        self.epubfile = NamedTemporaryFile(delete=True)
        with open("test_assets/uragano.epub") as input_file:
            self.epubfile.write(input_file.read())

    def test_valid_file_should_be_parsed(self):
        self.epub = EPUB(self.epubfile, "r")


class TestEpubFileInit(unittest.TestCase):

    def setUp(self):
        self.epubfile = EPUB(open("test_assets/uragano.epub"), "r")


if __name__ == "__main__":
    unittest.main()
