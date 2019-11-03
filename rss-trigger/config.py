

class Check:
    def __init__(self, times):
        self._times = times

    def clone(self):
        return Check([x for x in self._times])

    def next(self):
        ret = self._times[0]
        self._times = self._times[1:]
        return ret


class ActionCMD:
    def __init__(self, cmd):
        self._cmd = cmd


class ActionCompose:
    def __init__(self, children):
        self._children_cache = children
        self._children = []

    def validate(config):
        for child in self._children_cache:
            child = config.get_action(child)
            if child is None:
                self._children = []
                return False
            self._children.append(child)
        self._children_cache = []


class Feed:
    def __init__(self, url, check, trigger):
        self._url = url
        self._check = check
        self._trigger = trigger


class Config:
    def __init__(self):
        self._wd = ""
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

        self._checks.update({name: Check(times)})
        return True

    def get_check(self, name):
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
            return NOne
        return self._actions[name]

    def add_feed(self, name, url, check=[], trigger=[]):
        self._feeds.update({name: Feed(url, check, trigger)})
        return True

    def get_feed(self, name):
        if not self._ok:
            fail("Call Config.validate() before get_feed()")
        return self._feeds[name]

    def set_wd(self, wd):
        self._wd = wd

    def get_wd(self):
        return self._wd

    def validate(self):
        self._is_ok = True
        for action in self._actions_compose:
            if not action.validate(self):
                self._is_ok = False
                return False



