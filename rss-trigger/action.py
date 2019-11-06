from helper import *
import config

import feedparser
import schedule
import threading
import datetime


def check_feed(feed_config, check):
    printlog("Trigger")
    check_feed_impl(feed_config, check.clone())


def check_feed_impl(feed_config, check):
    feeds = do_check(feed_config)

    if len(feeds) == 0:
        next = check.next()
        if next is not None:
            time = datetime.datetime.now()
            time += datetime.timedelta(minutes=next)
            time = time.strftime("%H:%M")

            schedule.every().day.at(time).do(check_feed_impl, feed_config, check)
    else:
        for feed in feeds:
            log("Found Feed {}".format(str(feed)))
            for action in feed_config.action:
                log("Execute {} for feed {}".format(str(action), str(feed)))
                threading.Thread(target=execute_recursive, args=(feed_config, feed, action)).start()
        # update cache
        feed_config.last_id = feeds[0]['id']
        with open(feed_config.cache_file, 'w') as writer:
            writer.write(feed_config.last_id)

    return schedule.CancelJob


def do_check(feed_config):
    feed = feedparser.parse(feed_config.url)
    entries = feed['entries']

    if feed_config.last_id is None:
        return [entries[0]]

    interesting_feeds = []
    index = 0
    while index < len(entries) and entries[index]['id'] != feed_config.last_id:
        interesting_feeds.append(entries[index])
        index += 1

    return interesting_feeds


def execute_recursive(feed_config, feed_entry, action):
    for action in action.get_actions():
        execute(feed_config, feed_entry, action)


def execute(feed_config, feed_entry, action):
    if isinstance(action, config.ActionCMD):
        cmd = action.cmd.format(**feed_entry)
        printlog("# {}".format(cmd))
        shell(action.cmd.format(**feed_entry), feed_config.path)
    else:
        fail("Fatal error! Unknown action type: {}".format(action))
