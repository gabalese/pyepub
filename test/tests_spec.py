import unittest
import os
from pyepub import EPUB, InvalidEpub
from zipfile import ZipFile, BadZipfile


class EpubNewTests(unittest.TestCase):
    def setUp(self):
        self.epub_file = EPUB("test_assets/test_epub.epub", mode="r")

    def test_epub_should_have_a_opf(self):
        self.assertTrue(self.epub_file.opf[0].tag == "{http://www.idpf.org/2007/opf}metadata")

    def test_epub_should_expose_metadata_as_dictionary(self):
        metadata = self.epub_file.info
        self.assertIsInstance(metadata, dict)

    def test_spine_elements_must_link_with_manifest(self):
        for element in self.epub_file.info["spine"]:
            self.assertIsInstance(element, dict)

    def test_contents_must_equal_toc_list(self):
        self.assertEquals(len(self.epub_file.contents), len(self.epub_file.ncx[3]))

    def tearDown(self):
        self.epub_file.close()


class EpubTestModes(unittest.TestCase):
    def test_read_mode_should_be_read(self):
        self.epubfile = EPUB("test_assets/test_epub.epub", "r")
        self.assertEquals("r", self.epubfile.mode)

    def test_append_mode_should_be_append(self):
        self.epubfile = EPUB("test_assets/test_epub.epub", "a")
        self.assertEquals("a", self.epubfile.mode)

    def test_write_mode_should_be_write(self):
        self.epubfile = EPUB("test_assets/new_file.epub", "w")
        self.assertEquals("w", self.epubfile.mode)

    def tearDown(self):
        if os.path.exists("test_assets/new_file.epub"):
            os.remove("test_assets/new_file.epub")


class NoSuchFilename(unittest.TestCase):
    def test_no_such_filename_returns_ioerror(self):
        with self.assertRaises(IOError):
            self.epub_file = EPUB("random_file", "r")

    def test_invalid_zipfile_throws_badzipfile(self):
        with self.assertRaises(BadZipfile):
            self.epub_file = EPUB(__file__)

    def test_invalid_epub_file_throws_invalid_epubfile(self):
        with self.assertRaises(InvalidEpub):
            self.epub_file = EPUB("test_assets/invalid_epub.epub", "r")

    def test_ill_formed_opf_should_raise_invalid_epub(self):
        with self.assertRaises(InvalidEpub):
            self.epub_file = EPUB("test_assets/illformed_opf.epub", "r")

    def test_epub_must_have_a_id_or_fail(self):
        with self.assertRaises(InvalidEpub):
            self.epub_file = EPUB("test_assets/epub_with_no_id.epub", "r")


if __name__ == '__main__':
    unittest.main()
