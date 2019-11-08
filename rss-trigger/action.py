from helper import *
import config

import feedparser
import schedule
import threading
import datetime


def check_feed(feed_config, check, cache):
    check_feed_impl(feed_config, check.clone(), cache)


def check_feed_impl(feed_config, check, cache):
    printlog("Trigger")
    feeds = do_check(feed_config, cache)

    if len(feeds) == 0:
        next = check.next()
        if next is not None:
            time = datetime.datetime.now()
            time += datetime.timedelta(minutes=next)
            time = time.strftime("%H:%M")

            schedule.every().day.at(time).do(check_feed_impl, feed_config, check, cache)
    else:
        for feed in feeds:
            log("Found Feed {}".format(str(feed)))
            for action in feed_config.action:
                log("Execute {} for feed {}".format(str(action), str(feed)))
                threading.Thread(target=execute_recursive, args=(feed_config, feed, action)).start()
        # update cache
        cache.update_cache(feed_config.name, feeds[0]['id'])
    return schedule.CancelJob


def do_check(feed_config, cache):
    feed = feedparser.parse(feed_config.url)
    entries = feed['entries']

    last_id = cache.get__last_id(feed.name)
    if last_id is None:
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


def handle_env_and_var(var, add_env, add_var):
    feed_entry['feed_name'] = feed_url.name
    feed_entry['feed_url'] = feed_config.url
    feed_entry['feed_path'] = feed_config.path

    for add_var_key, add_var_value in feed_config.environ.var.items():
        add_var_value = add_var_value.format(**feed_entry)
        feed_entry[add_var_key] = eval(add_var_value)

    env = os.environ.clone()
    for env_key, env_value in feed_config.environ.env.items():
        env_value = env_value.format(**feed_entry)
        env[env_value] = eval(env_value)
    return env


def execute(feed_config, feed_entry, action):
    # update feed_entry
    var = feed_entry
    env = handle_env_and_var(var, feed_config.environ.env, feed_config.environ.var)

    # execute
    if isinstance(action, config.ActionCMD):
        cmd = action.cmd.format(**feed_entry)
        path = feed_config.path.format(**feed_entry)

        if not os.path.isdir(path):
            os.mkdir(path)

        printlog("# ({}) # {}".format(path, cmd))
        shell(action.cmd.format(**feed_entry), path, env)
    elif isinstance(action, config.ActionPython):
        cmd = action.cmd.format(**feed_entry)
        printlog("Python # {}".format(cmd))
        eval(cmd)
    else:
        fail("Fatal error! Unknown action type: {}".format(action))
