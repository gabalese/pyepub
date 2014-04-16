from pyepub import EPUB
import os
import unittest


class TestNewEPUB(unittest.TestCase):

    def setUp(self):
        self.epub_file = EPUB("new_epub.epub", "w")

    def test_new_epub_can_be_written(self):
        self.epub_file.close()
        self.assertTrue(os.path.exists("new_epub.epub"))

    def tearDown(self):
        os.remove("new_epub.epub")


if __name__ == '__main__':
    unittest.main()
