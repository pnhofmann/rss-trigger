import schedule
import time
import sys
import argparse

from helper import *
import action
from config import Check
import config_parser


def get_cli_args_parser():
    parser = argparse.ArgumentParser(description='Trigger events on new rss entries.')
    parser.add_argument('config_file', metavar='N', type=str, help='Config file')
    parser.add_argument('--daemon', action='store_true', help='Fork and run in background')
    parser.add_argument('--once', nargs='+', help='')
    return parser


def run(args):
    config = config_parser.try_parse(args.config_file)

    log_init(config.log_file)

    if args.daemon and os.fork():
        sys.exit()

    if args.once:
        run_once(config)
    else:
        daemon(config)

    log_close()


def run_once(config):
    for feed in config.get_feed():
        printlog("Running {}".format(str(feed)))
        action.check_feed(feed, Check([]), config.cache)


def daemon(config):
    for feed in config.get_feeds():
        for check in feed.check:
            for day in check.days:
                day.at(check.time).do(action.check_feed, feed, check, config.cache)

    while 1:
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    args = get_cli_args_parser().parse_args()
    run(args)
