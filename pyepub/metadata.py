import re

try:
    import lxml.etree as ET
except ImportError:
    import xml.etree.ElementTree as ET

NAMESPACE = {
    "dc": "{http://purl.org/dc/elements/1.1/}",
    "opf": "{http://www.idpf.org/2007/opf}",
    "ncx": "{http://www.daisy.org/z3986/2005/ncx/}"
}


class Info(dict):
    def __init__(self, opf):
        """
        Init
        :param opf: xml.etree.ElementTree.ElementTree
        """
        ns = re.compile(r"\{.*?\}")
        tempo = {"metadata": {},
                 "manifest": [],
                 "spine": [],
                 "guide": []}

        for i in opf.find("{0}metadata".format(NAMESPACE["opf"])):
            tag = ns.sub('', i.tag)

            if tag not in tempo["metadata"]:
                tempo["metadata"][tag] = i.text or i.attrib
            else:
                tempo["metadata"][tag] = [tempo["metadata"][tag], i.text or i.attrib]

        dict.__init__(self, tempo)

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)

    def __getitem__(self, key):
        return dict.__getitem__(self, key)
