import unittest
import os
from tempfile import NamedTemporaryFile
from StringIO import StringIO
from pyepub import EPUB
from zipfile import ZipFile


class EpubNewTests(unittest.TestCase):
    def setUp(self):
        remotefile = open("test_assets/test_epub.epub")
        testfile = NamedTemporaryFile(delete=True)
        testfile.write(remotefile.read())
        testfile.seek(0)
        self.file = EPUB(testfile, "a")

    def test_metadata(self):
        self.assertEqual(len(self.file.info.manifest), 31)
        self.assertGreaterEqual(len(self.file.info), 3)
        if len(self.file.info) > 3:
            self.assertIsInstance(self.file.info.spine, list)

    def test_writetodisk(self):
        part = StringIO('<?xml version="1.0" encoding="utf-8" standalone="yes"?>')
        tmp = NamedTemporaryFile(delete=True)
        self.file.addpart(part, "testpart.xhtml", "application/xhtml+xml", 2)
        self.file.writetodisk(tmp.name)
        reparse = EPUB(tmp.name, "r")
        self.assertIn("OPS/testpart.xhtml", reparse.filenames)

    def test_write_new_file(self):
        fakefile = StringIO()
        output = EPUB(fakefile, "w")
        tmp = NamedTemporaryFile(delete=True)
        part = StringIO('<?xml version="1.0" encoding="utf-8" standalone="yes"?>')
        output.addpart(part, "testpart.xhtml", "application/xhtml+xml", 2)
        output.writetodisk(tmp.name)
        rezip = ZipFile(tmp, "r")
        self.assertTrue(len(rezip.filelist) == 5)

    def tearDown(self):
        self.file.close()


class EputTestFileWriteWithClose(unittest.TestCase):
    def setUp(self):
        test_file_content = open("test_assets/test_epub.epub", "rb")
        file_on_disk = open("written.epub", "wb")
        file_on_disk.write(test_file_content.read())
        file_on_disk.close()
        self.epub = EPUB("written.epub", "a")

    def test_close_and_write(self):
        part = StringIO('<?xml version="1.0" encoding="utf-8" standalone="yes"?>')
        self.epub.addpart(part, "testpart.xhtml", "application/xhtml+xml", 2)
        self.epub.writetodisk("written_ex.epub")
        self.check_epub = EPUB("written_ex.epub", "r")
        self.assertEquals(len(self.epub.infolist()), len(self.check_epub.infolist()))

    def tearDown(self):
        os.remove("written_ex.epub")
        os.remove("written.epub")


class EpubTests(unittest.TestCase):
    def setUp(self):
        # get a small epub test file as a file-like object
        self.epub2file = NamedTemporaryFile(delete=False)
        test_file_content = open("test_assets/chrome_yellow.epub", "rb")
        self.epub2file.write(test_file_content.read())
        self.epub2file.seek(0)
        # get an epub with no guide element
        self.epub2file2 = NamedTemporaryFile(delete=False)
        test_file_content2 = open("test_assets/amore_in_ostaggio.epub", "rb")
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
        part = StringIO('<?xml version="1.0" encoding="utf-8" standalone="yes"?>')
        epub.addpart(part, "testpart.xhtml", "application/xhtml+xml", 2)
        self.assertEqual(len(epub.opf[2]), 36)  # spine items

    def test_addpart_no_position(self):
        epub = EPUB(self.epub2file, mode='a')
        part = StringIO('<?xml version="1.0" encoding="utf-8" standalone="yes"?>')
        epub.addpart(part, "testpart.xhtml", "application/xhtml+xml")
        self.assertEqual(len(epub.opf[2]), 36)  # spine items

    def test_add_item(self):
        epub = EPUB(self.epub2file, mode='a')
        len_before = len(epub.opf[1])
        part = StringIO('<?xml version="1.0" encoding="utf-8" standalone="yes"?>')
        epub.additem(part, "testpart.xhtml", "application/xhtml+xml")
        self.assertEqual(len_before+1, len(epub.opf[1]))  # spine items

    def test_addpart_noguide(self):
        epub2 = EPUB(self.epub2file2, mode='a')
        self.assertEqual(len(epub2.opf), 3)
        self.assertEqual(len(epub2.info['guide']), 0)
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
