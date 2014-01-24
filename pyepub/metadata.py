import re
from collections import OrderedDict

NAMESPACES = {
    "dc": "{http://purl.org/dc/elements/1.1/}",
    "opf": "{http://www.idpf.org/2007/opf}",
    "ncx": "{http://www.daisy.org/z3986/2005/ncx/}"
}

try:
    import lxml.etree as Etree
except ImportError:
    import xml.etree.ElementTree as Etree
    for k, v in NAMESPACES.iteritems():
        Etree.register_namespace(k, v)

inv_namespace = {v: k for k, v in NAMESPACES.iteritems()}

ns = re.compile(r"{.*?}")


class Metadata(dict):
    def __init__(self, opf):
        """
        Init
        :param opf: xml.etree.ElementTree.ElementTree
        """
        self.opf = opf
        temporary_dict = {}

        for i in self.opf.find("{0}metadata".format(NAMESPACES["opf"])):
            tag = ns.sub(inv_namespace[ns.findall(i.tag)[0]] + ":" or '', i.tag)
            if tag not in temporary_dict:
                temporary_dict[tag] = i.text or i.attrib
            else:
                temporary_dict[tag] = [temporary_dict[tag], i.text or i.attrib]

        super(Metadata, self).__init__(temporary_dict)

    def __setitem__(self, key, value):
        if isinstance(value, dict):
            self._attrib(key, value)
            return
        super(Metadata, self).__setitem__(key, value)
        key_tuple = key.split(":")
        if len(key_tuple) < 2:
            key_tuple.insert(0, "")
        try:
            tmp = self.opf.find(".//{0}{1}".format(NAMESPACES[key_tuple[0]], key_tuple[1]))
        except KeyError:
            raise Exception("Unregistered namespace {0}".format(key_tuple[0]))
        try:
            tmp.text = value
        except AttributeError:
            new_key = Etree.Element(NAMESPACES[key_tuple[0]]+key_tuple[1])
            new_key.text = value
            self.opf[0].append(new_key)
            # The interface should be consistent with a xml.etree.Element

    def __delitem__(self, key):
        super(Metadata, self).__delitem__(key)
        key_tuple = key.split(":")
        if len(key_tuple) < 2:
            key_tuple.insert(0, "")
        try:
            tmp = self.opf.find(".//{0}{1}".format(NAMESPACES[key_tuple[0]], key_tuple[1]))
        except KeyError:
            raise Exception("Unregistered namespace {0}".format(key_tuple[0]))
        self.opf[0].remove(tmp)

    def _attrib(self, key, dic):
        assert isinstance(dic, dict), ".attrib expects a dictionary of attributes"
        key_tuple = key.split(":")
        if len(key_tuple) < 2:
            key_tuple.insert(0, "")
        try:
            tmp = self.opf.find(".//{0}{1}".format(NAMESPACES[key_tuple[0]], key_tuple[1]))
        except KeyError:
            raise Exception("Unregistered namespace {0}".format(key_tuple[0]))
        try:
            tmp.attrib = dic
        except AttributeError:
            new_key = Etree.Element(NAMESPACES[key_tuple[0]]+key_tuple[1], attrib=dic)
            new_key.text = tmp.value
            self.opf[0].append(new_key)

    def register_namespace(self, key, value):
        NAMESPACES[key] = value
        global inv_namespace
        inv_namespace = {v: k for k, v in NAMESPACES.iteritems()}
        try:
            self.opf.register_namespace(key, value)
        except AttributeError:
            pass


class Manifest(OrderedDict):
    pass


class Spine(dict):
    pass


class Guide(dict):
    pass
