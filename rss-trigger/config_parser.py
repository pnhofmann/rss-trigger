import os
import traceback

from config import *
from yaml_wrapper import *


class Cache:
    def __init__(self, cache_file):
        self._file_path = cache_file
        self._cache = yaml_parse(cache_file)

    def get_last_id(self, feed_name):
        if feed_name in self._cache:
            return self._cache[feed_name]
        return None

    def update_cache(self, feed, last_id):
        self._cache[feed] = last_id
        yaml_write(self._file_path, self._cache)


def check_must_have_keys(yaml):
    yaml['config']
    yaml['config']['cache-file']
    yaml['config']['environ']
    yaml['checks']
    yaml['actions']
    yaml['feeds']


def try_parse(f):
    try:
        return parse(f)
    except Exception as e:
        error(str(e))
        traceback.print_exc()
        fail("Could not load config file!")


def parse(f):
    yaml = yaml_parse(f)
    if len(yaml) == 0:
        fail("Config file {} empty or does not exist!".format(f))

    try:
        check_must_have_keys(yaml)
    except KeyError as e:
        fail("Missing key: {}".format(str(e)))

    config = Config()
    if 'log-file' in yaml['config']:
        config.log_file = yaml['config']['log-file']

    config.cache = Cache(yaml['config']['cache-file'])

    for check in yaml['checks']:
        check = check.popitem()
        name = check[0]
        times = check[1]
        if not config.add_check(name, times):
            fail("Invalid: {}".format(str(check)))

    for action in yaml['actions']:
        action = action.popitem()
        name = action[0]

        call = False
        cmd = False
        python = False

        if 'exec' in action[1]:
            cmd = action[1]['exec']
        if 'call' in action[1]:
            call = action[1]['call']
        if 'python' in action[1]:
            python = action[1]['python']

        if not config.add_action(name, call=call, cmd=cmd, python=python):
            fail("Invalid: {}".format(str(check)))

    general_environ = Environ()
    general_environ.parse(yaml['config']['environ'])

    for feed in yaml['feeds']:
        feed = feed.popitem()
        name = feed[0]

        environ = general_environ.clone()
        if 'environ' in feed:
            environ.parse(feed['environ'])

        if "disabled" in feed[1] and feed[1]['disabled']:
            printlog("Skipping disabled feed: {}".format(name))
            continue

        try:
            url = feed[1]['url']
            check = feed[1]['check']

            action = feed[1]['action']
            if isinstance(action, str):
                action = [action]
        except KeyError as e:
            error("Invalid feed: {} -- {}".format(feed, str(e)))
            continue
        if not config.add_feed(name, url, check, action, environ):
            error("Inalid feed {}".format(str(check)))

    config.validate()
    return config
