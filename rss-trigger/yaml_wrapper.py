from yaml import load, dump, YAMLError
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper
import os

from helper import *


def yaml_parse(f):
    if not os.path.exists(f):
        return {}

    with open(f, 'r') as stream:
        try:
            yml = load(stream)
            if yml is None:
                yml = {}
            return yml
        except YAMLError as exc:
            printlog(str(exc))
    fail("Could not load yaml file {}".format())


def yaml_write(f, yml):
    with open(f, 'w') as writer:
        writer.write(dump(yml))


