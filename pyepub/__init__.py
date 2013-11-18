import zipfile
import os
import re
import uuid
from StringIO import StringIO
import datetime

try:
    import lxml.etree as ET
except ImportError:
    import xml.etree.ElementTree as ET

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
        self._write_files = {}  # a dict of files written to the archive  
        self._delete_files = [] # a list of files to delete from the archive
        self.epub_mode = mode
        self.writename = None
        if mode == "w":
            if isinstance(filename, str):
                self.writename = open(filename, "w")  # on close, we'll overwrite on this file
            else:
                # filename is already a file like object
                self.writename = filename
            dummy= StringIO()
            zipfile.ZipFile.__init__(self, dummy, mode="w")  # fake
            self.__init__write()
        elif mode == "a":
            # we're not going to write to the file until the very end
            if isinstance(filename, str):
                self.filename = open(filename, "w")  # on close, we'll overwrite on this file
            else:
                # filename is already a file like object
                self.filename = filename
            self.filename.seek(0)
            temp = StringIO()
            temp.write(self.filename.read())
            zipfile.ZipFile.__init__(self, self.filename, mode="r") # r mode doesn't set the filename
            self.__init__read(temp)
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

        # NEW: json-able info tree
        self.info = {"metadata": {},
                     "manifest": [],
                     "spine": [],
                     "guide": []}

        self.root_folder = os.path.dirname(self.opf_path)   # Used to compose absolute paths for reading in zip archive
        self.opf = ET.fromstring(self.read(self.opf_path))  # OPF tree

        ns = re.compile(r'\{.*?\}')  # RE to strip {namespace} mess

        # Iterate over <metadata> section, fill EPUB.info["metadata"] dictionary
        for i in self.opf.find("{0}metadata".format(NAMESPACE["opf"])):
            tag = ns.sub('', i.tag)
            if tag not in self.info["metadata"]:
                self.info["metadata"][tag] = i.text or i.attrib
            else:
                self.info["metadata"][tag] = [self.info["metadata"][tag], i.text or i.attrib]

        # Get id of the cover in <meta name="cover" />
        try:
            coverid = self.opf.find('.//{0}meta[@name="cover"]'.format(NAMESPACE["opf"])).get("content")
        except AttributeError:
            # It's a facultative field, after all
            coverid = None
        self.cover = coverid  # This is the manifest ID of the cover

        self.info["manifest"] = [{"id": x.get("id"),                # Build a list of manifest items
                                  "href": x.get("href"),
                                  "mimetype": x.get("media-type")}
                                 for x in self.opf.find("{0}manifest".format(NAMESPACE["opf"])) if x.get("id")]

        self.info["spine"] = [{"idref": x.get("idref")}             # Build a list of spine items
                              for x in self.opf.find("{0}spine".format(NAMESPACE["opf"])) if x.get("idref")]
        try:
            self.info["guide"] = [{"href": x.get("href"),           # Build a list of guide items
                                   "type": x.get("type"),
                                   "title": x.get("title")}
                                  for x in self.opf.find("{0}guide".format(NAMESPACE["opf"])) if x.get("href")]
        except TypeError:                                           # The guide element is optional
            self.info["guide"] = None

        # Document identifier
        try:
            self.id = self.opf.find('.//{0}identifier[@id="{1}"]'.format(NAMESPACE["dc"],
                                                                         self.opf.get("unique-identifier"))).text
        except AttributeError:
            raise InvalidEpub("Cannot process an EPUB without unique-identifier attribute of the package element")
        # Get and parse the TOC
        toc_id = self.opf[2].get("toc")
        expr = ".//{0}item[@id='{1:s}']".format(NAMESPACE["opf"], toc_id)
        toc_name = self.opf.find(expr).get("href")
        self.ncx_path = os.path.join(self.root_folder, toc_name)
        self.ncx = ET.fromstring(self.read(self.ncx_path))
        self.contents = [{"name": i[0][0].text or "None",           # Build a list of toc elements
                          "src": os.path.join(self.root_folder, i[1].get("src")),
                          "id":i.get("id")}
                         for i in self.ncx.iter("{0}navPoint".format(NAMESPACE["ncx"]))]    # The iter method
                                                                                            # loops over nested
                                                                                                  
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

        self.info["metadata"]["creator"] = "py-clave server"
        self.info["metadata"]["title"] = ""
        self.info["metadata"]["language"] = ""

        self.opf = ET.fromstring(self._init_opf())  # opf property is always a ElementTree
        self.ncx = ET.fromstring(self._init_ncx())  # so is ncx. Consistent with self.(opf|ncx) built by __init_read()

    def close(self):
        if self.fp is None:     # Check file status
            return
        if self.mode == "r":    # check file mode
            zipfile.ZipFile.close(self)
            return
        else:
            try:
                self._safeclose()
                zipfile.ZipFile.close(self)     # give back control to superclass close method
            except RuntimeError:            # zipfile.__del__ destructor calls close(), ignore
                return

    def _safeclose(self):
        """
        Preliminary operations before closing an EPUB
        Writes the empty or modified opf-ncx files before closing the zipfile
        """
        if self.epub_mode == 'w':
            self.writetodisk(self.writename)
        else:
            self.writetodisk(self.filename)

    def _write_epub_zip(self, epub_zip):
        """
        writes the epub to the specified writable zipfile instance

        :type epub_zip: an empty instance of zipfile.Zipfile, mode=w
        :param epub_zip: zip file to write
        """
        epub_zip.writestr('mimetype', "application/epub+zip")       # requirement of epub container format
        epub_zip.writestr('META-INF/container.xml', self._containerxml())
        epub_zip.writestr(self.opf_path, ET.tostring(self.opf, encoding="UTF-8"))  
        epub_zip.writestr(self.ncx_path, ET.tostring(self.ncx, encoding="UTF-8"))  
        paths = ['mimetype','META-INF/container.xml',self.opf_path,self.ncx_path]+ self._write_files.keys() + self._delete_files
        if self.epub_mode != 'w':
            for item in self.infolist():
                if item.filename not in paths:
                    epub_zip.writestr(item.filename, self.read(item.filename))
        for key in self._write_files.keys():
            epub_zip.writestr(key, self._write_files[key])

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
                            <dc:title>{title}</dc:title>
                            <dc:language>{lang}</dc:language>
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

        doc = opf_tmpl.format(uid=self.uid,
                              date=today,
                              title=self.info["metadata"]["title"],
                              lang=self.info["metadata"]["language"])
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

        :type paths: [str]
        :param paths: files to be deleted inside EPUB file
        """
        for path in paths:
            try:
                del self._write_files[path]
            except KeyError:
                pass
            self._delete_files.append(path)
    
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
        assert self.epub_mode != "r", "%s is not writable" % self
        namespace = NAMESPACE.get(namespace,namespace)
        element = ET.Element(namespace+term, attrib={})
        element.text = value
        self.opf[0].append(element)
        # note that info is ignoring namespace entirely
        if self.info["metadata"].has_key(term):
            self.info["metadata"][term] = [self.info["metadata"][term] , value]
        else:
            self.info["metadata"][term] = value
    
    def _writestr(self, filepath, filebytes):
        self._write_files[filepath] = filebytes   
        
    def additem(self, fileObject, href, mediatype):
        """
        Add a file to manifest only

        :type fileObject: StringIO
        :param fileObject:
        :type href: str
        :param href:
        :type mediatype: str
        :param mediatype:
        """
        assert self.epub_mode != "r", "%s is not writable" % self
        element = ET.Element("item",
                             attrib={"id": "id_"+str(uuid.uuid4())[:5], "href": href, "media-type": mediatype})

        try:
            self._writestr(os.path.join(self.root_folder, element.attrib["href"]), fileObject.getvalue().encode('utf-8'))
        except AttributeError:
            self._writestr(os.path.join(self.root_folder, element.attrib["href"]), fileObject)
        self.opf[1].append(element)
        return element.attrib["id"]

    def addpart(self, fileObject, href, mediatype, position=None, reftype="text", linear="yes"):
        """
        Add a file as part of the epub file, i.e. to manifest and spine (and guide?)

        :param fileObject: file to be inserted
        :param href: path inside the epub archive
        :param mediatype: mimetype of the fileObject
        :type position: int
        :param position: order in spine [from 0 to len(opf/manifest))]
        :param linear: linear="yes" or "no"
        :param reftype: type to assign in guide/reference
        """
        assert self.epub_mode != "r", "%s is not writable" % self
        fileid = self.additem(fileObject, href, mediatype)
        itemref = ET.Element("itemref", attrib={"idref": fileid, "linear": linear})
        reference = ET.Element("reference", attrib={"title": href, "href": href, "type": reftype})
        if position is None or position>len(self.opf[2]):
            self.opf[2].append(itemref)
            if self.info["guide"]:
                self.opf[3].append(reference)
        else:
            self.opf[2].insert(position, itemref)
            if self.info["guide"] and len(self.opf[3]) >= position+1:
                self.opf[3].insert(position, reference) 
                                                                                                  
    def writetodisk(self, filename):
        """
        Writes the in-memory archive to disk

        :type filename: str
        :param filename: name of the file to be writte
        """
        filename.seek(0)
        new_zip = zipfile.ZipFile(filename, 'w')
        self._write_epub_zip(new_zip)
        new_zip.close()
        return
