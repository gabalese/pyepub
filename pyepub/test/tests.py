import unittest
import urllib2
from tempfile import NamedTemporaryFile
from StringIO import StringIO
from pyepub import EPUB
from lxml import etree


class EpubNewTests(unittest.TestCase):
    def setUp(self):
        remotefile = urllib2.urlopen('http://dev.alese.it/book/urn:uuid:c72fb312-f83e-11e2-82c4-001cc0a62c0b/download')
        testfile = NamedTemporaryFile(delete=True)
        testfile.write(remotefile.read())
        testfile.seek(0)
        self.file = EPUB(testfile)

    def test_metadata(self):
        self.assertEqual(len(self.file.info.manifest), 31)
        self.assertGreaterEqual(len(self.file.info), 3)
        if len(self.file.info) > 3:
            self.assertIsInstance(self.file.info.spine, list)

    def test_writetodisk(self):
        tmp = NamedTemporaryFile(delete=True)
        self.file.writetodisk(tmp)
        self.assertIsNot(tmp.name, None)

    def test_write_new_file(self):
        fakefile = StringIO()
        output = EPUB(fakefile, "w")
        tmp = NamedTemporaryFile(delete=True)
        output.writetodisk(tmp)


class EpubTests(unittest.TestCase):
    def setUp(self):
        # get a small epub test file as a file-like object
        self.epub2file = NamedTemporaryFile(delete=False)
        test_file_content = urllib2.urlopen('http://dev.alese.it/book/urn:uuid:d928ac1a-f3c3-11e2-94df-001cc0a62c0b/download')
        self.epub2file.write(test_file_content.read())
        self.epub2file.seek(0)
        # get an epub with no guide element
        self.epub2file2 = NamedTemporaryFile(delete=False)
        test_file_content2 = urllib2.urlopen('http://dev.alese.it/book/EO_EB_00001/download')
        self.epub2file2.write(test_file_content2.read())
        self.epub2file2.seek(0)

    def test_instantiation(self):
        epub = EPUB(self.epub2file)
        self.assertNotEqual(epub.filename, None)
        self.assertEqual(len(epub.opf), 4)
        self.assertEqual(len(epub.opf[0]), 15)  # metadata items
        self.assertEqual(len(epub.opf[1]), 49)  # manifest items
        self.assertEqual(len(epub.opf[2]), 35)   # spine items
        self.assertEqual(len(epub.opf[3]), 35)   # guide items

    def test_addpart(self):
        epub = EPUB(self.epub2file, mode='a')
        self.assertNotEqual(epub.filename, None)
        part = StringIO('<?xml version="1.0" encoding="utf-8" standalone="yes"?>')
        epub.addpart(part, "testpart.xhtml", "application/xhtml+xml", 2)
        self.assertEqual(len(epub.opf[2]), 36)  # spine items

    def test_addpart_noguide(self):
        epub2 = EPUB(self.epub2file2, mode='a')
        self.assertEqual(len(epub2.opf), 3)
        self.assertEqual(epub2.info['guide'], None)
        num_spine_items = len(epub2.opf[2])
        part = StringIO('<?xml version="1.0" encoding="utf-8" standalone="yes"?>')
        epub2.addpart(part, "testpart.xhtml", "application/xhtml+xml", 2)
        self.assertEqual(len(epub2.opf[2]), num_spine_items + 1)  # spine items

    def test_addmetadata(self):
        epub = EPUB(self.epub2file, mode='a')
        epub.info["metadata"]["dc:test"] = "GOOD"
        epub.info["metadata"]['dc:prova'] = {"token": "token_content"}
        epub.info["metadata"]['dc:prova'] = "contenuto"
        self.assertTrue(epub.opf.find('.//{http://purl.org/dc/elements/1.1/}test') is not None)
        self.assertEqual(epub.info.metadata['dc:test'].text, 'GOOD')
        self.assertEqual(epub.info["metadata"]['dc:prova'].attrib, {"token": "token_content"})
        self.assertEqual(epub.info["metadata"]['dc:prova'].text, "contenuto")
        self.assertEqual(epub.opf.find(".//{http://purl.org/dc/elements/1.1/}prova").text, "contenuto")
        self.assertEqual(epub.opf.find(".//{http://purl.org/dc/elements/1.1/}prova").attrib["token"], "token_content")

if __name__ == '__main__':
    unittest.main()
