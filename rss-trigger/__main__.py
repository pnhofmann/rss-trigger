import schedule
import time

from helper import *
import action
import config_parser


def daemon(config):
    for feed in config.get_feeds():
        for check in feed.check:
            for day in check.days:
                day.at(check.time).do(config_parser.check_feed, feed)

    while 1:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    log_init()
    config = try_parse('example.yml')
    daemon(config)
    log_close()
