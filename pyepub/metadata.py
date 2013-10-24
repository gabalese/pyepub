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

inv_NAMESPACE = {v: k for k, v in NAMESPACE.iteritems()}

ns = re.compile(r"\{.*?\}")


class Metadata(dict):
    def __init__(self, opf):
        """
        Init
        :param opf: xml.etree.ElementTree.ElementTree
        """
        self.opf = opf
        temporary_dict = {}

        for i in self.opf.find("{0}metadata".format(NAMESPACE["opf"])):
            tag = ns.sub(inv_NAMESPACE[ns.findall(i.tag)[0]] + ":" or '', i.tag)
            if tag not in temporary_dict:
                temporary_dict[tag] = i.text or i.attrib
            else:
                temporary_dict[tag] = [temporary_dict[tag], i.text or i.attrib]

        dict.__init__(self, temporary_dict)

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        key_tuple = key.split(":")
        if len(key_tuple) < 2:
            key_tuple.insert(0, "")
        tmp = self.opf.find(".//{0}{1}".format(NAMESPACE[key_tuple[0]], key_tuple[1]))
        tmp.text = value
        # The interface should be consistent with a xml.etree.Element


class Manifest(dict):
    pass


class Spine(dict):
    pass


class Guide(dict):
    pass
