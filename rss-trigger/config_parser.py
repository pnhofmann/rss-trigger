from yaml import load, dump, YAMLError
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

from helper import *
from config import *
import os



def parse_yaml(f):
    with open(f, 'r') as stream:
        try:
            return(load(stream))
        except YAMLError as exc:
            printlog(str(exc))
    fail("Could not load yaml file {}".format())


def check_must_have_keys(yaml):
    yaml['config']
    yaml['config']['checks']
    yaml['config']['actions']
    yaml['config']['paths']
    yaml['config']['paths']['working_directory']
    yaml['feeds']


def try_parse(f):
    try:
        return parse(f)
    except Exception as e:
        error(str(e))
        fail("Could not load config file!")


def parse(f):
    yaml = parse_yaml(f)

    try:
        check_must_have_keys(yaml)
    except KeyError as e:
        fail("Missing key: {}".format(str(e)))

    config = Config()
    for check in yaml['config']['checks']:
        check = check.popitem()
        name = check[0]
        times = check[1]
        if not config.add_check(name, times):
            fail("Invalid: {}".format(str(check)))

    for action in yaml['config']['actions']:
        action = action.popitem()
        name = action[0]
        call = False
        cmd = False

        if 'exec' in action[1]:
            cmd = action[1]['exec']
        if 'call' in action[1]:
            call = action[1]['call']

        if not config.add_action(name, call=call, cmd=cmd):
            fail("Invalid: {}".format(str(check)))

    for feed in yaml['feeds']:
        feed = feed.popitem()
        name = feed[0]
        try:
            url = feed[1]['url']
            check = feed[1]['check']
            action = feed[1]['action']
        except KeyError as e:
            error("Invalid feed: {} -- {}".format(feed, str(e)))
            continue
        if not config.add_feed(name, url, check, action):
            error("Inalid feed {}".format(str(check)))

    config.wd = yaml['config']['paths']['working_directory']
    if not os.path.exists(config.wd):
        fail("{} does not exist!".format(str(config.wd)))
