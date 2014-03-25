import zipfile
import os
import uuid
from StringIO import StringIO
import datetime
from metadata import NAMESPACES, Metadata, Manifest, Spine

import lxml.etree as Etree

TMP = {"opf": None, "ncx": None}
file_like_object = None


class EPUB(zipfile.ZipFile):
    """
    EPUB file representation class.

    """
    _write_files = {}
    _delete_files = []

    def __init__(self, filename, mode="r"):
        """
        Global Init Switch

        :type filename: str or StringIO() or file like object for read or add
        :param filename: File to be processed
        :type mode: str
        :param mode: "w" or "r", mode to init the zipfile
        """

        self.epub_mode = mode
        self.filename = filename

        if mode == "w":

            if not isinstance(self.filename, StringIO):
                assert not os.path.exists(self.filename), \
                    "Can't overwrite existing file: %s" % self.filename

            super(EPUB, self).__init__(self.filename, mode="w")
            self.__init__write()

        elif mode == "a":

            assert not isinstance(filename, StringIO), \
                "Can't append to StringIO object, use write instead: %s" % filename
            if isinstance(filename, str):
                tmp = open(filename, "r")  # ensure that the input file is never-ever overwritten
            else:
                # filename is already a file like object
                tmp = filename
            tmp.seek(0)
            initfile = StringIO()
            initfile.write(tmp.read())
            tmp.close()
            super(EPUB, self).__init__(initfile, mode="a")
            self.__init__read(initfile)
        else:  # retrocompatibility?
            super(EPUB, self).__init__(filename, mode="r")
            self.__init__read(filename)

    def __init__read(self, filename):
        """
        Constructor to initialize the zipfile in read-only mode

        :type filename: str or StringIO()
        :param filename: File to be processed
        """
        try:
            f = self.read("META-INF/container.xml")
        except KeyError:
            # By specification, there MUST be a container.xml in EPUB
            print "The %s file is not a valid OCF." % str(filename)
            raise InvalidEpub
        try:
            # There MUST be a full path attribute on first grandchild...
            self.opf_path = Etree.fromstring(f)[0][0].get("full-path")
        except IndexError:
            #  ...else the file is invalid.
            print "The %s file is not a valid OCF." % str(filename)
            raise InvalidEpub

        self.root_folder = os.path.dirname(self.opf_path)   # Used to compose absolute paths for reading in zip archive
        self.opf = Etree.fromstring(self.read(self.opf_path))  # OPF tree

        try:
            identifier_xpath_expression = r'.//{0}identifier[@id="{1}"]'.format(NAMESPACES["dc"], self.opf.get("unique-identifier"))
            self.id = self.opf.find(identifier_xpath_expression).text
        except AttributeError:
            # Cannot process an EPUB without unique-identifier
            raise InvalidEpub

        try:
            cover_xpath_expression = r'.//{0}meta[@name="cover"]'.format(NAMESPACES["opf"])
            self.cover = self.opf.find(cover_xpath_expression).get("content")
        except AttributeError:
            self.cover = None

        self.info = InfoDict({"metadata": Metadata(self.opf),
                              "manifest": Manifest(self.opf),
                              "spine": Spine(self.opf),
                              "guide": []})

        # Link spine elements with manifest id
        for spine_element in self.info["spine"]:
            ref = spine_element.get("idref")
            for manifest_element in self.info["manifest"]:
                if manifest_element.get("id") == ref:
                    spine_element["href"] = manifest_element.get("href")

        try:
            self.info["guide"] = [
                {"href": x.get("href"), "type": x.get("type"), "title": x.get("title")}
                for x in self.opf.find("{0}guide".format(NAMESPACES["opf"])) if x.get("href")
            ]
        except TypeError:  # The guide element is optional
            # TODO: Why TypeError?
            self.info["guide"] = []

            # Get and parse the TOC
        toc_id = self.opf[2].get("toc")
        expr = ".//{0}item[@id='{1:s}']".format(NAMESPACES["opf"], toc_id)
        toc_name = self.opf.find(expr).get("href")
        self.ncx_path = os.path.join(self.root_folder, toc_name)
        self.ncx = Etree.fromstring(self.read(self.ncx_path))
        self.contents = [{"name": i[0][0].text or "None",
                          "src": os.path.join(self.root_folder, i[1].get("src")),
                          "id": i.get("id")}
                         for i in self.ncx.iter("{0}navPoint".format(NAMESPACES["ncx"]))]

    def __init__write(self):
        """
        Init an empty EPUB

        """
        self.opf_path = "OEBPS/content.opf"  # Define a default folder for contents
        self.ncx_path = "OEBPS/toc.ncx"
        self.root_folder = "OEBPS"
        self.uid = '%s' % uuid.uuid4()

        self.info = {"metadata": {},
                     "manifest": [],
                     "spine": [],
                     "guide": []}

        self.writestr('mimetype', "application/epub+zip")
        self.writestr('META-INF/container.xml', self._empty_container_xml())
        self.info["metadata"]["title"] = ""
        self.info["metadata"]["language"] = ""

        self.opf = Etree.fromstring(self._empty_opf())
        self.ncx = Etree.fromstring(self._empty_ncx())

        self.writestr(self.opf_path, Etree.tostring(self.opf, encoding="UTF-8"))
        self.writestr(self.ncx_path, Etree.tostring(self.ncx, encoding="UTF-8"))

    @property
    def author(self):
        return self.info["metadata"]["creator"]

    @author.setter
    def author(self, value):
        tmp = self.opf.find(".//{0}creator".format(NAMESPACES["dc"]))
        tmp.text = value
        self.info["metadata"]["creator"] = value

    @property
    def title(self):
        return self.info["metadata"]["title"]

    @title.setter
    def title(self, value):
        tmp = self.opf.find(".//{0}title".format(NAMESPACES["dc"]))
        tmp.text = value
        ncx_title = self.ncx.find("{http://www.daisy.org/z3986/2005/ncx/}docTitle")[0]
        ncx_title.text = value
        self.info["metadata"]["title"] = value

    @property
    def language(self):
        return self.info["metadata"]["language"]

    @language.setter
    def language(self, value):
        tmp = self.opf.find(".//{0}language".format(NAMESPACES["dc"]))
        tmp.text = value
        self.info["metadata"]["language"] = value

    def _safeclose(self):
        """
        Preliminary operations before closing an EPUB
        Writes the empty or modified opf-ncx files before closing the zipfile
        """
        assert self.epub_mode == 'w'
        self.writetodisk(self.filename)

    def _write_epub_zip(self, epub_zip):
        """
        writes the epub to the specified writable zipfile instance

        :type epub_zip: an empty instance of zipfile.Zipfile, mode=w
        :param epub_zip: zip file to write
        """
        epub_zip.writestr('mimetype', "application/epub+zip")       # requirement of epub container format
        epub_zip.writestr('META-INF/container.xml', self._empty_container_xml())
        epub_zip.writestr(self.opf_path, Etree.tostring(self.opf, encoding="UTF-8"))
        epub_zip.writestr(self.ncx_path, Etree.tostring(self.ncx, encoding="UTF-8"))
        paths = ['mimetype', 'META-INF/container.xml',
                 self.opf_path, self.ncx_path] + self._write_files.keys() + self._delete_files

        if self.epub_mode != 'r':
            for item in self.filelist:
                if item.filename not in paths:
                    epub_zip.writestr(item.filename, self.read(item.filename))

        for key in self._write_files.keys():
            epub_zip.writestr(key, self._write_files[key])

    def _empty_opf(self):
        """
        Constructor for empty OPF
        :type return: xml.minidom.Document
        :return: xml.minidom.Document
        """
        today = datetime.date.today()
        opf_tmpl = """<?xml version="1.0" encoding="utf-8" standalone="yes"?>
                        <package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="2.0">
                        <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
                            <dc:identifier id="BookId" opf:scheme="UUID">{uid}</dc:identifier>
                            <dc:title></dc:title>
                            <dc:creator></dc:creator>
                            <dc:language></dc:language>
                            <dc:date opf:event="modification">{date}</dc:date>
                        </metadata>
                        <manifest>
                            <item href="toc.ncx" id="ncx" media-type="application/x-dtbncx+xml" />
                        </manifest>
                        <spine toc="ncx">
                        </spine>
                        <guide>
                        </guide>
                        </package>"""

        doc = opf_tmpl.format(uid=self.uid, date=today)
        return doc

    def _empty_ncx(self):
        """
        Constructor for empty OPF
        :type return: xml.minidom.Document
        :return: xml.minidom.Document
        """
        ncx_tmpl = """<?xml version="1.0" encoding="utf-8"?>
                        <!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN"
                           "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
                        <ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
                        <head>
                           <meta name="dtb:uid" content="{uid}" />
                           <meta name="dtb:depth" content="0" />
                           <meta name="dtb:totalPageCount" content="0" />
                           <meta name="dtb:maxPageNumber" content="0" />
                        </head>
                        <docTitle>
                           <text>{title}</text>
                        </docTitle>
                        <navMap>
                        </navMap>
                        </ncx>"""

        ncx = ncx_tmpl.format(uid=self.uid, title="Default")
        return ncx

    def _empty_container_xml(self):
        template = """<?xml version="1.0" encoding="UTF-8"?>
                    <container version="1.0"
                               xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
                        <rootfiles>
                             <rootfile full-path="%s"
                                       media-type="application/oebps-package+xml"/>
                        </rootfiles>
                    </container>"""
        return template % self.opf_path

    def _delete(self, *paths):
        """
        Delete archive member

        :type paths: [str]
        :param paths: files to be deleted inside EPUB file
        """
        for path in paths:
            try:
                del self._write_files[path]
            except KeyError:
                pass
            self._delete_files.append(path)

    def additem(self, fileobject, href, mediatype):
        """
        Add a file to manifest only

        :type fileobject: StringIO
        :param fileobject:
        :type href: str
        :param href:
        :type mediatype: str
        :param mediatype:
        """
        assert self.mode != "r", "%s is not writable" % self
        element = Etree.Element("item",
                                attrib={"id": "id_" + str(uuid.uuid4())[:5], "href": href, "media-type": mediatype})

        try:
            self.writestr(os.path.join(self.root_folder, element.attrib["href"]), fileobject.getvalue())
        except AttributeError:
            self.writestr(os.path.join(self.root_folder, element.attrib["href"]), fileobject)
        self.opf[1].append(element)
        return element.attrib["id"]

    def addpart(self, fileobject, href, mediatype, position=None, reftype="text", linear="yes"):
        """
        Add a file as part of the epub file, i.e. to manifest and spine (and guide?)

        :param fileobject: file to be inserted
        :param href: path inside the epub archive
        :param mediatype: mimetype of the fileObject
        :type position: int
        :param position: order in spine [from 0 to len(opf/manifest))]
        :param linear: linear="yes" or "no"
        :param reftype: type to assign in guide/reference
        """
        assert self.mode != "r", "%s is not writable" % self
        fileid = self.additem(fileobject, href, mediatype)
        itemref = Etree.Element("itemref", attrib={"idref": fileid, "linear": linear})
        reference = Etree.Element("reference", attrib={"title": href, "href": href, "type": reftype})
        if position is None or position > len(self.opf[2]):
            self.opf[2].append(itemref)
            if self.info["guide"]:
                self.opf[3].append(reference)
        else:
            self.opf[2].insert(position, itemref)
            if self.info["guide"] and len(self.opf[3]) >= position + 1:
                self.opf[3].insert(position, reference)

    def writetodisk(self, filename):
        """
        Writes the in-memory archive to disk

        """
        if isinstance(filename, file) or isinstance(filename, StringIO):
            filename.seek(0)
        new_zip = zipfile.ZipFile(filename, 'w')
        self._write_epub_zip(new_zip)
        new_zip.close()


class InfoDict(dict):
    def __getattr__(self, item):
        return self[item]


class InvalidEpub(Exception):
    pass
