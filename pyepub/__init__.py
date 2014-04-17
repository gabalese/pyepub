import zipfile
import os
import uuid
from itertools import izip
from StringIO import StringIO
from metadata import NAMESPACES, InfoDict, Metadata, Manifest, Spine, Guide

import lxml.etree as elementtree


class InvalidEpub(Exception):
    pass


class EPUB(zipfile.ZipFile):
    def __new__(cls, filename, mode="r"):
        if mode == "a":
            return super(EPUB, cls).__new__(AppendeableEPUB, filename, mode)
        if mode == "w":
            return super(EPUB, cls).__new__(EmptyEPUB, filename, mode)
        if mode == "r":
            return super(EPUB, cls).__new__(ReadableEPUB, filename, mode)
        else:
            raise RuntimeError("Invalid mode: {mode}".format(mode=mode))


class ReadableEPUB(EPUB):
    def __init__(self, filename, mode="r"):
        super(EPUB, self).__init__(filename, mode)
        try:
            container = self.read("META-INF/container.xml")
            self._opf_path = elementtree.fromstring(container)[0][0].get("full-path")
        except (KeyError, IndexError, elementtree.XMLSyntaxError):
            raise InvalidEpub("Unable to read container.xml")

        try:
            self.root_folder = os.path.dirname(self._opf_path)
            self.opf = elementtree.fromstring(self.read(self._opf_path))
        except elementtree.XMLSyntaxError:
            raise InvalidEpub

        try:
            find = r'.//{0}identifier[@id="{1}"]'.format(NAMESPACES["dc"], self.opf.get("unique-identifier"))
            self.id = self.opf.find(find).text
        except AttributeError:
            raise InvalidEpub("No unique identifier supplied")

        self.info = self.info_dict()
        self.__link_spine_elements()
        self.ncx = self.__parse_toc()
        self.contents = self.__parse_contents()

    def __link_spine_elements(self):
        for spine_element, manifest_element in izip(self.info.spine, self.info.manifest):
            if manifest_element.get("id") == spine_element.get("idref"):
                spine_element["href"] = manifest_element.get("href")

    def __parse_toc(self):
        toc_id = self.opf[2].get("toc")
        expr = ".//{0}item[@id='{1:s}']".format(NAMESPACES["opf"], toc_id)
        toc_name = self.opf.find(expr).get("href")
        self._ncx_path = os.path.join(self.root_folder, toc_name)
        ncx = elementtree.fromstring(self.read(self._ncx_path))
        return ncx

    def __parse_contents(self):
        try:
            contents = [{"name": i[0][0].text or None,
                         "src": os.path.join(self.root_folder, i[1].get("src")),
                         "id": i.get("id")}
                        for i in self.ncx.iter("{0}navPoint".format(NAMESPACES["ncx"]))]
        except IndexError:
            return []
        else:
            return contents

    def info_dict(self):
        return InfoDict(
            {
                "metadata": Metadata(self.opf),
                "manifest": Manifest(self.opf),
                "spine": Spine(self.opf),
                "guide": Guide(self.opf)
            }
        )

    @property
    def filenames(self):
        return (item.filename for item in self.filelist if not item.filename.endswith("/"))


class AppendeableEPUB(ReadableEPUB):
    def __init__(self, filename, mode):
        self.mode = mode
        super(AppendeableEPUB, self).__init__(filename, "a")
        self.appended_files = []
        self.starting_files = filter(lambda x: not (x.filename.endswith("opf") or x.filename.endswith("ncx")),
                                     self.infolist())

    def additem(self, fileobject, href, mediatype):
        assert self.mode != "r", "%s is not writable" % self
        element = elementtree.Element("item", attrib={
            "id": "id_" + str(uuid.uuid4())[:5],
            "href": href,
            "media-type": mediatype
        })

        try:
            self.writestr(os.path.join(self.root_folder, element.attrib["href"]), fileobject.getvalue())
        except AttributeError:
            self.writestr(os.path.join(self.root_folder, element.attrib["href"]), fileobject.read())
        finally:
            self.appended_files.append(
                {
                    "path": os.path.join(self.root_folder, element.attrib["href"]),
                    "file": fileobject
                }
            )
        self.info["manifest"].append(element)
        return element.attrib["id"]

    def addpart(self, fileobject, href, mediatype, position=None, reftype="text", linear="yes"):
        assert self.mode != "r", "%s is not writable" % self
        fileid = self.additem(fileobject, href, mediatype)
        itemref = elementtree.Element("itemref", attrib={"idref": fileid, "linear": linear})
        reference = elementtree.Element("reference", attrib={"title": href, "href": href, "type": reftype})
        if position is None or position > len(self.opf[2]):
            self.opf[2].append(itemref)
            if self.info["guide"]:
                self.info["guide"].append(reference)
        else:
            self.opf[2].insert(position, itemref)
            if self.info["guide"] and len(self.opf[3]) >= position + 1:
                self.opf[3].insert(position, reference)

    def writetodisk(self, filename):
        new_zip_file = zipfile.ZipFile(filename, "w")
        self.__add_current_opf_and_ncx()
        for item in self.starting_files:
            new_zip_file.writestr(item, self.read(item.filename))
        for new_file in self.appended_files:
            new_zip_file.writestr(new_file["path"], new_file["file"].read())
        new_zip_file.close()

    def __add_current_opf_and_ncx(self):
        self.appended_files.extend(
            [
                {
                    "path": self._opf_path,
                    "file": StringIO(elementtree.tostring(self.opf))
                },
                {
                    "path": self._ncx_path,
                    "file": StringIO(elementtree.tostring(self.ncx))
                }
            ]
        )


class EmptyEPUB(AppendeableEPUB):
    def __init__(self, filename, mode):
        super(EPUB, self).__init__(filename, mode)
        self._opf_path = "OEBPS/content.opf"  # Define a default folder for contents
        self._ncx_path = "OEBPS/toc.ncx"
        self.root_folder = "OEBPS"
        self.uid = '%s' % uuid.uuid4()
        self.opf = elementtree.fromstring(self.__empty_opf())
        self.ncx = elementtree.fromstring(self.__empty_ncx())
        self.container = self.__empty_container_xml()
        self.writestr("mimetype", "epub+zip")
        self.writestr("META-INF/container.xml", self.container)
        self.writestr(self._opf_path, elementtree.tostring(self.opf))
        self.writestr(self._ncx_path, elementtree.tostring(self.ncx))
        self.close()
        super(EmptyEPUB, self).__init__(filename, mode)

    def __empty_ncx(self):
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
                        <navPoint>
                        </navPoint>
                        </navMap>
                        </ncx>"""

        ncx = ncx_tmpl.format(uid=self.uid, title="Default")
        return ncx

    def __empty_container_xml(self):
        template = """<?xml version="1.0" encoding="UTF-8"?>
                    <container version="1.0"
                               xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
                        <rootfiles>
                             <rootfile full-path="%s"
                                       media-type="application/oebps-package+xml"/>
                        </rootfiles>
                    </container>"""
        return template % self._opf_path

    def __empty_opf(self):
        import datetime
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
