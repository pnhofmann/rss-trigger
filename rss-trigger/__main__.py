import schedule
import time
import sys

from helper import *
import action
import config_parser


def daemon(config):
    for feed in config.get_feeds():
        for check in feed.check:
            for day in check.days:
                day.at(check.time).do(action.check_feed, feed, check)

    while 1:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    log_init()
    config = config_parser.try_parse(sys.argv[1])
    daemon(config)
    log_close()
