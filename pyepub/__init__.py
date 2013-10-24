import zipfile
import os
import uuid
from StringIO import StringIO
import datetime

try:
    import lxml.etree as ET
except ImportError:
    import xml.etree.ElementTree as ET

from metadata import Metadata

TMP = {"opf": None, "ncx": None}
FLO = None

NAMESPACE = {
    "dc": "{http://purl.org/dc/elements/1.1/}",
    "opf": "{http://www.idpf.org/2007/opf}",
    "ncx": "{http://www.daisy.org/z3986/2005/ncx/}"
}

ET.register_namespace('dc', "http://purl.org/dc/elements/1.1/")
ET.register_namespace('opf', "http://www.idpf.org/2007/opf")
ET.register_namespace('ncx', "http://www.daisy.org/z3986/2005/ncx/")


class InvalidEpub(Exception):
    pass


class EPUB(zipfile.ZipFile):
    """
    EPUB file representation class.

    """

    def __init__(self, filename, mode="r"):
        """
        Global Init Switch

        :type filename: str or StringIO() or file like object for read or add
        :param filename: File to be processed
        :type mode: str
        :param mode: "w" or "r", mode to init the zipfile
        """
        if mode == "w":
            if not isinstance(filename, StringIO):
                assert not os.path.exists(filename), \
                    "Can't overwrite existing file: %s" % filename
            self.filename = filename
            zipfile.ZipFile.__init__(self, self.filename, mode="w")
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
            zipfile.ZipFile.__init__(self, initfile, mode="a")
            self.__init__read(initfile)
        else:  # retrocompatibility?
            zipfile.ZipFile.__init__(self, filename, mode="r")
            self.__init__read(filename)

    def __init__read(self, filename):
        """
        Constructor to initialize the zipfile in read-only mode

        :type filename: str or StringIO()
        :param filename: File to be processed
        """
        self.filename = filename
        try:
            # Read the container
            f = self.read("META-INF/container.xml")
        except KeyError:
            # By specification, there MUST be a container.xml in EPUB
            print "The %s file is not a valid OCF." % str(filename)
            raise InvalidEpub
        try:
            # There MUST be a full path attribute on first grandchild...
            self.opf_path = ET.fromstring(f)[0][0].get("full-path")
        except IndexError:
            #  ...else the file is invalid.
            print "The %s file is not a valid OCF." % str(filename)
            raise InvalidEpub

        self.root_folder = os.path.dirname(self.opf_path)   # Used to compose absolute paths for reading in zip archive
        self.opf = ET.fromstring(self.read(self.opf_path))  # OPF tree

        self._info = {"metadata": Metadata(self.opf),
                     "manifest": [],
                     "spine": [],
                     "guide": []}

        # Get id of the cover in <meta name="cover" />
        try:
            coverid = self.opf.find('.//{0}meta[@name="cover"]'.format(NAMESPACE["opf"])).get("content")
        except AttributeError:
            # It's a facultative field, after all
            coverid = None
        self.cover = coverid  # This is the manifest ID of the cover

        self._info["manifest"] = [{"id": x.get("id"),  # Build a list of manifest items
                                  "href": x.get("href"),
                                  "mimetype": x.get("media-type")}
                                 for x in self.opf.find("{0}manifest".format(NAMESPACE["opf"])) if x.get("id")]

        self._info["spine"] = [{"idref": x.get("idref")}             # Build a list of spine items
                              for x in self.opf.find("{0}spine".format(NAMESPACE["opf"])) if x.get("idref")]

        # this looks expensive...
        # ... but less expensive than doing a lookup with ElementTree.find()
        for i in self._info["spine"]:
            ref = i.get("idref")
            for m in self._info["manifest"]:
                if m.get("id") == ref:
                    i["href"] = m.get("href")

        try:
            self._info["guide"] = [{"href": x.get("href"),  # Build a list of guide items
                                   "type": x.get("type"),
                                   "title": x.get("title")}
                                  for x in self.opf.find("{0}guide".format(NAMESPACE["opf"])) if x.get("href")]
        except TypeError:                                           # The guide element is optional
            self._info["guide"] = None

        # Document identifier
        try:
            self.id = self.opf.find('.//{0}identifier[@id="{1}"]'.format(NAMESPACE["dc"],
                                                                         self.opf.get("unique-identifier"))).text
        except AttributeError:
            raise InvalidEpub  # Cannot process an EPUB without unique-identifier
            # attribute of the package element
        # Get and parse the TOC
        toc_id = self.opf[2].get("toc")
        expr = ".//{0}item[@id='{1:s}']".format(NAMESPACE["opf"], toc_id)
        toc_name = self.opf.find(expr).get("href")
        self.ncx_path = os.path.join(self.root_folder, toc_name)
        self.ncx = ET.fromstring(self.read(self.ncx_path))
        self.contents = [{"name": i[0][0].text or "None",  # Build a list of toc elements
                          "src": os.path.join(self.root_folder, i[1].get("src")),
                          "id": i.get("id")}
                         for i in self.ncx.iter("{0}navPoint".format(NAMESPACE["ncx"]))]    # The iter method
        # loops over nested
        # navPoints

    def __init__write(self):
        """
        Init an empty EPUB

        """
        self.opf_path = "OEBPS/content.opf"  # Define a default folder for contents
        self.ncx_path = "OEBPS/toc.ncx"
        self.root_folder = "OEBPS"
        self.uid = '%s' % uuid.uuid4()

        self._info = {"metadata": {},
                     "manifest": [],
                     "spine": [],
                     "guide": []}

        self.writestr('mimetype', "application/epub+zip")
        self.writestr('META-INF/container.xml', self._containerxml())
        self._info["metadata"]["creator"] = "py-clave server"
        self._info["metadata"]["title"] = ""
        self._info["metadata"]["language"] = ""

        # Problem is: you can't overwrite file contents with python ZipFile
        # so you must add contents BEFORE finalizing the file
        # calling close() method.

        self.opf = ET.fromstring(self._init_opf())  # opf property is always a ElementTree
        self.ncx = ET.fromstring(self._init_ncx())  # so is ncx. Consistent with self.(opf|ncx) built by __init_read()

        self.writestr(self.opf_path, ET.tostring(self.opf, encoding="UTF-8"))  # temporary opf & ncx
        self.writestr(self.ncx_path, ET.tostring(self.ncx, encoding="UTF-8"))  # will be re-init on close()

    @property
    def author(self):
        return self._info["metadata"]["creator"]

    @author.setter
    def author(self, value):
        tmp = self.opf.find(".//{0}creator".format(NAMESPACE["dc"]))
        tmp.text = value
        self._info["metadata"]["creator"] = value

    @property
    def info(self):
        return self._info

    @property
    def title(self):
        return self._info["metadata"]["title"]

    @title.setter
    def title(self, value):
        tmp = self.opf.find(".//{0}title".format(NAMESPACE["dc"]))
        tmp.text = value
        ncx_title = self.ncx.find("{http://www.daisy.org/z3986/2005/ncx/}docTitle")[0]
        ncx_title.text = value
        self._info["metadata"]["title"] = value

    @property
    def language(self):
        return self._info["metadata"]["language"]

    @language.setter
    def language(self, value):
        tmp = self.opf.find(".//{0}language".format(NAMESPACE["dc"]))
        tmp.text = value
        self._info["metadata"]["language"] = value

    def close(self):
        if self.fp is None:     # Check file status
            return
        if self.mode == "r":    # check file mode
            zipfile.ZipFile.close(self)
            return
        else:
            try:
                global TMP                  # in-memory copy of existing opf-ncx. When the epub gets re-init,
                                            # it loses track of modifications
                TMP["opf"] = self.opf
                TMP["ncx"] = self.ncx
                self._safeclose()
                zipfile.ZipFile.close(self)     # give back control to superclass close method
            except RuntimeError:            # zipfile.__del__ destructor calls close(), ignore
                return

    def _safeclose(self):
        """
        Preliminary operations before closing an EPUB
        Writes the empty or modified opf-ncx files before closing the zipfile
        """
        if self.mode != "r":
            self._delete(self.opf_path, self.ncx_path)  # see following horrible hack:
                                                        # zipfile cannot manage overwriting on the archive
                                                        # this basically RECREATES the epub from scratch
                                                        # and is sure slow as hell
                                                        # ... and a recipe for disaster.
            self.opf = TMP["opf"]
            self.ncx = TMP["ncx"]  # get back the temporary copies

        self.writestr(self.opf_path, ET.tostring(self.opf, encoding="UTF-8"))
        self.writestr(self.ncx_path, ET.tostring(self.ncx, encoding="UTF-8"))
        self.__init__read(FLO)  # We may still need info dict of a closed EPUB

    def _init_opf(self):
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

    def _init_ncx(self):
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

    def _containerxml(self):
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
        Basically a hack: zince zipfile can't natively overwrite or delete resources,
        a new archive is created from scratch to a StringIO file object.
        The starting file is *never* overwritten.
        To write the new file to disk, use the writefiletodisk() instance method.

        :type paths: str
        :param paths: files to be deleted inside EPUB file
        """
        global FLO  # File-Like-Object: this is obviously wrong: any better idea?
                    # Also, the variable name is questionable
        FLO = StringIO()
        new_zip = zipfile.ZipFile(FLO, 'w')
        for item in self.infolist():
            if item.filename not in paths:
                try:
                    new_zip.writestr(item.filename, self.read(item.filename))
                except zipfile.BadZipfile:
                    pass
        zipfile.ZipFile.close(self)     # Don't know why
        new_zip.close()                 # but it works, don't ever touch
        zipfile.ZipFile.__init__(self, FLO, mode="a")

    def addmetadata(self, term, value, namespace='dc'):
        """
        Add an metadata entry 

        :type term: str
        :param term: element name/tag for metadata item
        :type value: str
        :param value: a value
        :type namespace: str
        :param namespace. either a '{URI}' or a registered prefix ('dc', 'opf', 'ncx') are currently built-in
        """
        raise DeprecationWarning("addmetadata is deprecated. Add items to info dict.")
        assert self.mode != "r", "%s is not writable" % self
        namespace = NAMESPACE.get(namespace, namespace)
        element = ET.Element(namespace + term, attrib={})
        element.text = value
        self.opf[0].append(element)
        # note that info is ignoring namespace entirely
        if term in self._info["metadata"]:
            self._info["metadata"][term] = [self._info["metadata"][term], value]
        else:
            self._info["metadata"][term] = value

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
        element = ET.Element("item",
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
        itemref = ET.Element("itemref", attrib={"idref": fileid, "linear": linear})
        reference = ET.Element("reference", attrib={"title": href, "href": href, "type": reftype})
        if position is None or position > len(self.opf[2]):
            self.opf[2].append(itemref)
            if self._info["guide"]:
                self.opf[3].append(reference)
        else:
            self.opf[2].insert(position, itemref)
            if self._info["guide"] and len(self.opf[3]) >= position + 1:
                self.opf[3].insert(position, reference)

    def writetodisk(self, filename):
        """
        Writes the in-memory archive to disk

        :type filename: str
        :param filename: name of the file to be writte
        """
        if self.mode == "r":
            # The inferface should be consistent
            new_zip = zipfile.ZipFile(filename, 'w')
            for item in self.infolist():
                new_zip.writestr(item.filename, self.read(item.filename))
            new_zip.close()
            return  # this is a bad habit
        f = open(filename, "w")
        try:
            self.filename.seek(0)
        except AttributeError:  # file must be closed first
            self.close()
            self.filename.seek(0)
        f.write(self.filename.read())
        f.close()

    def __del__(self):
        try:
            self.fp.close()
        except (ValueError, AttributeError):
            pass
