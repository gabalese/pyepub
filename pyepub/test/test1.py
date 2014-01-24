from pyepub import EPUB

x = EPUB("pyepub/diavolo.epub")

print x.info["metadata"]["dc:language"]
x.info["metadata"]["dc:language"] = "bag"
print x.info["metadata"]["dc:language"]
print [(x.tag, x.text) for x in x.opf.iter()]
