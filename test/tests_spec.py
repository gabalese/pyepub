import unittest
import urllib2
from tempfile import NamedTemporaryFile
from StringIO import StringIO
from pyepub import EPUB, InvalidEpub
from zipfile import ZipFile, BadZipfile
import lxml.etree as elementtree
import os


class EpubNewTests(unittest.TestCase):
    def setUp(self):
        self.epub_file = EPUB("test_assets/test_epub.epub", mode="r")

    def test_epub_should_expose_filenames(self):
        self.assertIsInstance(self.epub_file.list_of_files, list)

    def test_list_of_files_must_equal_manifest_contents(self):
        self.assertEquals(len(self.epub_file.list_of_files), len(self.epub_file.opf[1]))

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


class TestNewEPUB(unittest.TestCase):
    @unittest.skip("To implement")
    def test_new_epub_creation(self):
        self.epub_file = EPUB("ciao.epub", "w")


if __name__ == '__main__':
    unittest.main()
