from pyepub import EPUB
import xml.etree.ElementTree as ET

x = EPUB("diavolo.epub", "a")

print len(x.info.manifest)
x.info.manifest.insert(0, ET.Element("boh"))
print x.info.manifest[-1]
print len(x.info.manifest)

print ET.tostring(x.opf[1])

x.close()
x.writetodisk("Ciao.epub")