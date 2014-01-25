from pyepub import EPUB
import xml.etree.ElementTree as ET

x = EPUB("diavolo.epub", "a")

x.info["metadata"].register_namespace("po", "{http://www.alese.it/opf}")
x.info["metadata"]["po:dio"] = "ciao"
print x.info.metadata["dc:date"].text
x.info.metadata["dc:date"] = "2014-20-10"
x.info.metadata["dc:date"] = {"opf:event": "modification"}
print x.info.metadata["dc:date"].text
print x.info.metadata["dc:date"].attrib
x.info.metadata["po:dio"].attrib = {"porco": "dio"}
x.info.metadata["po:dio"].attrib.update({"name": "ciao"})
print x.info.metadata["po:dio"].attrib
print ET.tostring(x.opf[0])
#x.close()
#x.writetodisk("prova.epub")