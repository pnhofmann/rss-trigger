import os
import schedule
from helper import *


class ConfigObject:
    def validate_field(self, field, find_function):
        ret = []
        for item_name in field:
            item = find_function(item_name)
            if item is None:
                fail("Object not found: {}".format(item_name))
            ret.append(item)
        return ret


class Check(ConfigObject):
    def __init__(self, times, days=[], time=[]):
        self.times = times
        self.days = days
        self.time = time

    def init(self, days, time):
        return Check([x for x in self.times], days, time)

    def clone(self):
        return Check([x for x in self.times])

    def next(self):
        if len(self.times) == 0:
            return False
        ret = self.times[0]
        self.times = self.times[1:]
        return ret


class ActionCMD:
    def __init__(self, cmd):
        self.cmd = cmd

    def get_actions(self):
        yield self


class ActionCompose(ConfigObject):
    def __init__(self, children):
        self._children_cache = children
        self.children = []

    def validate(self, config):
        self.children = self.validate_field(self._children_cache, config.get_action)
        self._children_cache = []

    def get_actions(self):
        yield from self.children


class Feed(ConfigObject):
    def __init__(self, url, check, action):
        self.url = url
        self._check_cache = check
        self.check = []
        self._action_cache = action
        self.action = []

        self.path = False
        self.cache_file = False
        self.last_id = None

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
                days = [schedule.every().sunday,
                        schedule.every().monday,
                        schedule.every().tuesday,
                        schedule.every().wednesday,
                        schedule.every().thursday,
                        schedule.every().friday,
                        schedule.every().saturday]
                return days[num]

            days_list = []
            if days == "daily":
                days = "Mon-Sun"

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
        self._wd = False
        self._checks = {}
        self._actions = {}
        self._feeds = {}

        self._actions_compose = []

        self._ok = False

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

        self._checks.update({name: Check(times_diff)})
        return True

    def get_check(self, name):
        name = name.replace('*', '')
        if not self._ok:
            fail("Call Config.validate() before get_action()")
        if name not in self._checks:
            fail("No such Check {}".format(name))
        return self._checks[name]

    def add_action(self, name, call=False, cmd=False):
        if call is not False:
            action = ActionCompose(call)
            self._actions_compose.append(action)
        elif cmd is not False:
            action = ActionCMD(cmd)
        else:
            return "Invalid Action"

        self._ok = False
        self._actions.update({name: action})
        return True

    def get_action(self, name):
        if not self._ok:
            fail("Call Config.validate() before get_action()")
        if name not in self._actions:
            fail("No such Action {}".format(name))
        return self._actions[name]

    def add_feed(self, name, url, check=[], action=[]):
        self._feeds.update({name: Feed(url, check, action)})
        return True

    def get_feeds(self):
        if not self._ok:
            fail("Call Config.validate() before get_feed()")
        return self._feeds.values()

    def set_wd(self, wd):
        self._wd = wd

    def get_wd(self):
        return self._wd

    def validate(self):
        if self._wd is False:
            fail("Config invalid: working directory not set!")

        self._ok = True
        for action in self._actions_compose:
            action.validate(self)

        for name, feed in self._feeds.items():
            feed.validate(self)
            self.init_feed_path(name, feed)


    def init_feed_path(self, name, feed):
        path = os.path.join(self._wd, name)
        if not os.path.isdir(path):
            os.mkdir(path)
        cache_file = os.path.join(path, "cache")
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as reader:
                feed.last_id = reader.read().splitlines()[0]

        feed.path = path
        feed.cache_file = cache_file
