import os
import schedule
from helper import *


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


class Environ:
    def __init__(self, cwd='.', env={}, var={}):
        self.cwd = cwd
        self.env = env
        self.var = var

    def parse(self, config):
        if 'cwd' in config:
            self.cwd = config['cwd']
        if 'env' in config:
            for env in config['env']:
                env = env.popitem()
                key = env[0]
                value = env[1]

                self.env[key] = value
        if 'var' in config:
            for var in config['var']:
                var = var.popitem()
                key = var[0]
                value = var[1]

                self.var[key] = value

    def clone(self):
        return Environ(self.cwd, self.env.copy(), self.var.copy())


class ConfigObject:
    def validate_field(self, field, find_function):
        ret = []
        for item_name in field:
            item = find_function(item_name)
            if item is None:
                fail("Object not found: {}".format(item_name))
            ret.append(item)
        return ret

    def __str__(self):
        return self.name


class Check(ConfigObject):
    def __init__(self, name, times, days=[], time=[]):
        self.name = name
        self.times = times
        self.days = days
        self.time = time

    def init(self, days, time):
        return Check(self.name, [x for x in self.times], days, time)

    def clone(self):
        return Check(self.name, [x for x in self.times])

    def next(self):
        if len(self.times) == 0:
            return False
        ret = self.times[0]
        self.times = self.times[1:]
        return ret


class Action(ConfigObject):
    def __init__(self, name):
        self.name = name

    def get_actions(self):
        yield self


class ActionCMD(Action):
    def __init__(self, name, cmd):
        super().__init__(name)
        self.cmd = cmd


class ActionPython(Action):
    def __init__(self, name, cmd):
        super().__init__(name)
        self.cmd = cmd


class ActionCompose(Action):
    def __init__(self, name, children):
        super().__init__(name)
        self._children_cache = children
        self.children = []

    def validate(self, config):
        self.children = self.validate_field(self._children_cache, config.get_action)
        self._children_cache = []

    def get_actions(self):
        yield from self.children


class Feed(ConfigObject):
    def __init__(self, name, url, check, action, environ):
        self.name = name
        self.url = url
        self._check_cache = check
        self.check = []
        self._action_cache = action
        self.action = []
        self.environ = environ

    def validate(self, config):
        def create_check(name):
            name = name.split()
            days = name[0]

            def str_to_num(string):
                string = string.lower()
                days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
                if string not in days:
                    fail("No day: {}".format(string))
                return days.index(string)

            def num_to_day(num):
                days = [('monday', schedule.every().monday),
                        ('tuesday', schedule.every().tuesday),
                        ('wednesday', schedule.every().wednesday),
                        ('thursday', schedule.every().thursday),
                        ('friday', schedule.every().friday),
                        ('saturday', schedule.every().saturday),
                        ('sunday', schedule.every().sunday)]
                return days[num]

            days_list = []
            if days == "daily":
                days = "Mon-Sun"
            if days == "workday":
                days = "Mon-Fri"

            days_add = days.split("+")
            for day in days_add:
                day = day.split('-')
                if len(day) == 1:
                    days_list.append(str_to_num(day[0]))
                else:
                    day0 = str_to_num(day[0])
                    day1 = str_to_num(day[1])

                    if day0 > day1:
                        days_list.extend(range(day0, day1+1))
                    else:
                        days_list.extend(range(0, day1+1))
                        days_list.extend(range(day0, 7))

            days = [num_to_day(num) for num in days_list]
            time = name[1]

            schedule.every().monday

            name = name[2]
            return config.get_check(name).init(days, time)

        self.check = self.validate_field(self._check_cache, create_check)
        self._check_cache = []
        self.action = self.validate_field(self._action_cache, config.get_action)
        self._action_cache = []


class Config:
    def __init__(self):
        self._checks = {}
        self._actions = {}
        self._feeds = {}

        self._actions_compose = []
        self._ok = False

        self.log_file = None
        self.cache_file = None

    def add_check(self, name, times):
        # validate times
        try:
            times = [int(x) for x in times]
        except ValueError:
            return "Not a number"

        time_last = 0
        times_diff = []
        for time in times:
            if time <= time_last:
                fail("Invalid sequence {} - must be ascending!".format(str(times)))
            times_diff.append(time - time_last)
            time_last = time

        self._checks.update({name: Check(name, times_diff)})
        return True

    def get_check(self, name):
        name = name.replace('*', '')
        if not self._ok:
            fail("Call Config.validate() before get_action()")
        if name not in self._checks:
            fail("No such Check {}".format(name))
        return self._checks[name]

    def add_action(self, name, call=False, cmd=False, python=False):
        if call is not False:
            action = ActionCompose(name, call)
            self._actions_compose.append(action)
        elif cmd is not False:
            action = ActionCMD(name, cmd)
        elif python is not False:
            action = ActionPython(name, python)
        else:
            fail("Invalid action {}!".format(name))

        self._ok = False
        self._actions.update({name: action})
        return True

    def get_action(self, name):
        if not self._ok:
            fail("Call Config.validate() before get_action()")
        if name not in self._actions:
            fail("No such Action {}".format(name))
        return self._actions[name]

    def add_feed(self, name, url, check, action, environ):
        self._feeds.update({name: Feed(name, url, check, action, environ)})
        return True

    def get_feeds(self):
        if not self._ok:
            fail("Call Config.validate() before get_feed()")
        return self._feeds.values()

    def validate(self):
        self._ok = True
        for action in self._actions_compose:
            action.validate(self)

        for name, feed in self._feeds.items():
            feed.validate(self)
