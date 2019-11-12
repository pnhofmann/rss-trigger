from helper import *
import config

import feedparser
import schedule
import threading
import datetime


def check_feed(feed_config, check, cache, fork=True):
    check_feed_impl(feed_config, check.clone(), cache, fork)


def check_feed_impl(feed_config, check, cache, fork=True):
    section("{} at {}".format(feed_config, datetime.datetime.now().strftime("%Y:%m:%d - %H:%M")))

    feeds = do_check(feed_config, cache)
    printlog("Found {} new feeds".format(len(feeds)))

    if len(feeds) == 0:
        next = check.next()
        if next is not None:
            printlog("Schedule recheck at {}".format(str(next)))

            time = datetime.datetime.now()
            time += datetime.timedelta(minutes=next)
            time = time.strftime("%H:%M")

            schedule.every().day.at(time).do(check_feed_impl, feed_config, check, cache, fork)
        else:
            printlog("CANCEL WITH NO NEW FEED FOUND")
    else:
        for feed in feeds:
            printlog("Found Feed {}".format(str(feed)))
            for action in feed_config.action:
                printlog("Execute {}".format(str(action)))
                if fork:
                    threading.Thread(target=execute_recursive, args=(feed_config, feed, action)).start()
                else:
                    execute_recursive(feed_config, feed, action)
        # update cache
        cache.update_cache(feed_config.name, feeds[0]['id'])
    section("FINISH")
    printlog("\n\n\n")
    return schedule.CancelJob


def do_check(feed_config, cache):
    feed = feedparser.parse(feed_config.url)
    entries = feed['entries']

    last_id = cache.get_last_id(feed_config.name)
    if last_id is None:
        return [entries[0]]

    interesting_feeds = []
    index = 0
    while index < len(entries) and entries[index]['id'] != last_id:
        interesting_feeds.append(entries[index])
        index += 1

    return interesting_feeds


def execute_recursive(feed_config, feed_entry, action):
    for a in action.get_actions():
        printlog("Execute {} because of {}".format(str(a), str(action)))
        execute(feed_config, feed_entry, a)


def handle_env_and_var(feed_config, var, add_env, add_var):
    var['feed_name'] = feed_config.name
    var['feed_url'] = feed_config.url
    var['feed_dir'] = feed_config.environ.cwd

    for add_var_key, add_var_value in feed_config.environ.var.items():
        add_var_value = add_var_value.format(**var)
        var[add_var_key] = eval(add_var_value)

    env = os.environ.copy()
    for env_key, env_value in feed_config.environ.env.items():
        env_value = env_value.format(**var)
        env[env_value] = env_value
    return env


def execute(feed_config, feed_entry, action):
    # update feed_entry
    var = feed_entry
    env = handle_env_and_var(feed_config, var, feed_config.environ.env, feed_config.environ.var)

    printlog("ENV: {}".format(env))
    printlog("VAR: {}".format(var))

    # execute
    if isinstance(action, config.ActionCMD):
        cmd = action.cmd.format(**feed_entry)
        path = feed_config.environ.cwd.format(**feed_entry)

        if not os.path.isdir(path):
            os.makedirs(path)

        printlog("# ({}) # {}".format(path, cmd))
        shell(action.cmd.format(**feed_entry), path, env)
    elif isinstance(action, config.ActionPython):
        cmd = action.cmd.format(**feed_entry)
        printlog("Python # {}".format(cmd))
        eval(cmd)
    else:
        fail("Fatal error! Unknown action type: {}".format(action))
