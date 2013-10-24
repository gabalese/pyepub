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
        temporary_dict = {"metadata": {},
                          "manifest": [],
                          "spine": [],
                          "guide": []}

        for i in opf.find("{0}metadata".format(NAMESPACE["opf"])):
            tag = ns.sub('', i.tag)  # TODO: find a way to preserve namespaces!
            if tag not in temporary_dict["metadata"]:
                temporary_dict["metadata"][tag] = i.text or i.attrib
            else:
                temporary_dict["metadata"][tag] = [temporary_dict["metadata"][tag], i.text or i.attrib]

        dict.__init__(self, temporary_dict)

    def __setitem__(self, key, value):
        # Do something fancy in the OPF
        # TODO: Is the opf copied or just pointed to when creating a Info class?
        dict.__setitem__(self, key, value)

    def __getitem__(self, key):
        # Leave this alone
        return dict.__getitem__(self, key)
