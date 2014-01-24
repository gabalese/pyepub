from pyepub import EPUB
import xml.etree.ElementTree as ET

x = EPUB("diavolo.epub", "a")

print x.info.metadata["dc:date"]
print " "
x.info["metadata"].register_namespace("po", "{http://www.alese.it/opf}")
x.info["metadata"]["po:dio"] = "ciao"
print x.info.metadata["po:dio"]

x.info.metadata["po:dio"] = {"name": "ciao"}
print ET.tostring(x.opf[0])
x.close()
x.writetodisk("prova.epub")