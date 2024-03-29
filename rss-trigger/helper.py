import os
import sys
import distutils.spawn
import time, datetime
import subprocess
from threading import Thread
from tempfile import NamedTemporaryFile
from colorama import Fore


# python 2/3 compatibility
try:
    input = raw_input
except NameError:
    pass


def executable_exists(name):
    binary_path = distutils.spawn.find_executable(name)
    return binary_path is not None and os.access(binary_path, os.X_OK)


debug_log = None
debug_print_to_cli = True


def log_init(file=None, print_cli = True):
    global debug_log
    global debug_print_to_cli

    debug_print_to_cli = print_cli

    if file is None:
        debug_log = NamedTemporaryFile(delete=False, mode="w")
    else:
        debug_log = open(file, "a")
        log("{:=^60}".format(str(datetime.datetime.now())))
    print("Logging to {}".format(debug_log.name))


def log_close():
    global debug_log
    if debug_log is not None:
        debug_log.close()
    debug_log is None


def fail(msg, fatal=False):
    print(msg)
    print('')
    print('')
    if fatal:
        printlog("FATAL!")
        print("ABORT with unexpected error - This should not have happened.")
        print("Please check logs at \"{}\". If you open a bug report, please include this file.".format(debug_log.name))
    else:
        print("ABORT!")
    log_close()
    sys.exit(1)


def log(msg):
    debug_log.write(msg)
    debug_log.write('\n')

def error(msg):
    printlog(Fore.RED)
    printlog(msg)
    printlog(Fore.RESET)

def printlog(msg):
    if debug_log is not None:
        log(msg)
    if debug_print_to_cli:
        print(msg)


def section(title):
    printlog("\n{:=^50}".format(" {} ".format(title)))


spinning = True


def spinning_cursor_start():
    global spinning
    spinning = True

    def spin_start():
        time.sleep(0.1)
        while spinning:
            for cursor in '|/-\\':
                sys.stdout.write(cursor)
                sys.stdout.flush()
                time.sleep(0.1)
                sys.stdout.write('\b')

    Thread(target=spin_start).start()


def spinning_cursor_stop():
    global spinning
    spinning = False


def user_input(items):
    log("User input:")
    for x, item in enumerate(items):
        printlog("{}) {}".format((x + 1), item[0]))

    while True:
        number = input("Select number {}-{}: ".format(1, len(items)))
        try:
            number = int(number) - 1
        except ValueError:
            log("> User input {} - not a number".format(number))
            continue

        if number >= 0 and number < len(items):
            log("> User input {} - ok: {}".format(number, items[number][1]))
            return items[number][1]
        else:
            log("> User input {} - out of range {} - {}".format(number, 1, len(items)))


def shell(cmd, cwd=None, env=os.environ):
    class Fail:
        def should_not_fail(self, msg=''):
            fail(msg, fatal=True)

        def success(self):
            return False

        def __str__(self):
            return "FAIL {}".format(self.exception)

    class Success:
        def should_not_fail(self, msg=''):
            pass

        def success(self):
            return True

        def __str__(self):
            return "OK"

    exit_code = Success()

    log("_" * 40)
    log("Shell: {}".format(cmd))
    spinning_cursor_start()

    cli_output = ''
    try:
        cli_output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, cwd=cwd)
    except subprocess.CalledProcessError as e:
        exit_code = Fail()
        exit_code.exception = str(e)

    # python 2 compatibility
    try:
        cli_output = cli_output.decode("utf-8")
    except AttributeError:
        pass
    exit_code.cli_output = cli_output

    log(cli_output)
    log("Shell: Exit {}".format(str(exit_code)))
    log("-" * 40)
    log("")

    debug_log.flush()

    spinning_cursor_stop()
    time.sleep(0.5)
    sys.stdout.write(' \b')

    return exit_code
