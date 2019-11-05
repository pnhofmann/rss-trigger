from helper import *

import feedparser
import schedule
import threading
import datetime


def check_feed(feed_config):
    repeat = [x for x in feed_config.check.times]
    check_feed_impl(feed_config, repeat)


def check_feed_impl(feed_config, times_to_do):
    feeds = check(feed_config)

    if len(feeds) == 0:
        if len(times_to_do) > 0:
            time = datetime.datetime.now()
            time += datetime.timedelta(minutes=times_to_do[0])
            time = time.strftime("%h:%m")
            times_to_do = times_to_do[1:]

            schedule.every().day.at(time).do(check_feed_impl, feed_config, times_to_do)
    else:
        for feed in feeds:
            loging.log("Found Feed {}".format(str(feed)))
            for action in feed_config.action:
                logging.log("Execute {} for feed {}".format(str(action), str(feed)))
                threading.Thread(target=execute_recursive).start(feed, action)

    return schedule.CancelJob


def check(feed_config):
    feed = feedparser.parse(feed_config.url)
    entries = feed['entries']

    interesting_feeds = []
    index = 0
    while index < len(entries) and entries[index]['id'] != feed_config.last_id:
        interesting_feeds.append(entries[index])
        index += 1

    return interesting_feeds


def execute_recursive(feed, action):
    for action in action.get_actions():
        execute(feed, action)


def execute(feed, action):
    if is_instance(action, ActionCMD):
        shell(action.cmd, feed.get_dir())
    else:
        fail("Fatal error! Unknown action type: {}".format(action))
