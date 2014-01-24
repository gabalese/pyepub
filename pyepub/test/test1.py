from pyepub import EPUB
import xml.etree.ElementTree as ET

x = EPUB("diavolo.epub", "a")

print x.info
print " "
x.info["metadata"].register_namespace("po", "{http://www.alese.it/opf}")
x.info["metadata"]["po:dio"] = "ciao"
print ET.tostring(x.opf)