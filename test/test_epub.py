import unittest
from tempfile import NamedTemporaryFile
from pyepub import EPUB


class TestEpubFileOpen(unittest.TestCase):

    def setUp(self):
        self.epubfile = NamedTemporaryFile(delete=True)
        with open("test_assets/uragano.epub") as input_file:
            self.epubfile.write(input_file.read())

    def test_valid_file_should_be_parsed(self):
        self.epub = EPUB(self.epubfile, "r")


class TestEpubFileInit(unittest.TestCase):

    def setUp(self):
        self.epubfile = EPUB(open("test_assets/uragano.epub"), "r")

    def test_epub_file_must_have_title(self):
        self.assertEqual(u'L\u2019uragano di novembre', self.epubfile.info.metadata["dc:title"].text)

    def test_epub_file_must_have_identifier(self):
        self.assertEqual("9788866322702", self.epubfile.id)

    def test_epub_file_must_have_identifier_with_attributes(self):
        self.assertIsNot(len(self.epubfile.info.metadata["dc:creator"].attrib), 0)

    def test_epub_file_must_have_identifier_from_opf(self):
        self.assertEqual(self.epubfile.id, self.epubfile.info["metadata"]["dc:identifier"].text)

if __name__ == "__main__":
    unittest.main()
