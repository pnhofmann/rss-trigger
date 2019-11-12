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
    parser.add_argument('--daemon', action='store_true', help='Fork and run in background; implies --silent')
    parser.add_argument('--silent', action='store_true', help='Do not print to cli')
    parser.add_argument('--once', help='Comma separated list of feeds or "all"')
    return parser


def run(args):
    config = config_parser.try_parse(args.config_file)

    log_init(config.log_file, print_cli=not (args.daemon or args.silent))

    if args.daemon and os.fork():
        sys.exit()

    if args.once:
        run_once(config, args.once)
    else:
        daemon(config)

    log_close()


def run_once(config, to_run):
    for feed in config.get_feeds():
        if to_run == "all" or feed.name in to_run.split('.'):
            printlog("Running {}".format(str(feed)))
            action.check_feed(feed, Check('single', []), config.cache, fork=False)


def daemon(config):
    section("INIT SCHEDULES")
    for feed in config.get_feeds():
        for check in feed.check:
            for day in check.days:
                printlog("Scheduling {} at {} - {}".format(feed, day[0], check.time))
                day[1].at(check.time).do(action.check_feed, feed, check, config.cache)

    section("RUN LOOP")
    while 1:
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    args = get_cli_args_parser().parse_args()
    run(args)
