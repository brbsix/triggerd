#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""Trigger an event or notification upon the output of a command"""

from configobj import ConfigObj
import logging
import os
import re

__program__ = 'triggerd'
__version__ = '0.3'


class Config:  # pylint: disable=R0903
    """Store global script configuration values."""
    debug = False
    verbose = False
    verify = False

    events = []
    file = None


class Event:  # pylint: disable=R0902
    """Store per-event configuration details."""
    def __init__(self, filename):
        self.exit = None
        self.output = None
        self.skip = False

        self.basename = os.path.basename(filename)
        self.file = filename

        self.loader = ConfigObj(filename)
        self.COMMAND = self.loader.get('COMMAND')
        self.EVENT_NAME = self.loader.get('EVENT_NAME')
        self.MATCH_CONTENT = self.loader.get('MATCH_CONTENT')
        self.MATCH_CRITERIA = self.loader.get('MATCH_CRITERIA')
        self.STATUS = self.loader.get('STATUS')
        self.TEST_TYPE = self.loader.get('TEST_TYPE')
        self.TRIGGER_CUSTOM = self.loader.get('TRIGGER_CUSTOM')
        self.TRIGGER_NAMED = self.loader.get('TRIGGER_NAMED')

        if Config.verify:
            self.skip = True
            eventlog.info("Verifying only", extra=self.__dict__)
            level = eventlog.getEffectiveLevel()
            eventlog.setLevel(logging.INFO)
            if self.verify():
                eventlog.info("Verification OK", extra=self.__dict__)
            else:
                eventlog.info("Verification NOT OK", extra=self.__dict__)
            eventlog.setLevel(level)
            Trigger(self)
        elif self.STATUS != 'enabled':
            self.skip = True
            eventlog.info("Not enabled (skipping)", extra=self.__dict__)
        elif not self.verify():
            self.skip = True
            eventlog.info("Failed verification (skipping)",
                          extra=self.__dict__)

    def _contains(self, match, content):
        """content contains match (match in content)."""
        test_result = match in content
        eventlog.info("CONTENT TEST | '%s' in '%s' => %s", match, content,
                      test_result, extra=self.__dict__)
        return test_result

    def _matches(self, match, content):
        """match matches content (match == content)."""
        test_result = match == content
        eventlog.info("CONTENT TEST | '%s' matches '%s' => %s", match, content,
                      test_result, extra=self.__dict__)
        return test_result

    def _notcontains(self, match, content):
        """content does not contain match (match not in content)."""
        test_result = match not in content
        eventlog.info("CONTENT TEST | '%s' not in '%s' => %s", match, content,
                      test_result, extra=self.__dict__)
        return test_result

    def _notmatch(self, match, content):
        """match does not match content (match != content)."""
        test_result = match != content
        eventlog.info("CONTENT TEST | '%s' does not match '%s' => %s", match,
                      content, test_result, extra=self.__dict__)
        return test_result

    def _notnull(self, match, content):  # pylint: disable=W0613
        """content is not null (content != '')."""
        test_result = content != ''
        eventlog.info("CONTENT TEST | '%s' is not null => '%s'", content,
                      test_result, extra=self.__dict__)
        return test_result

    def _null(self, match, content):  # pylint: disable=W0613
        """content is null (content == '')."""
        test_result = content == ''
        eventlog.info("CONTENT TEST | '%s' is null => '%s'", content,
                      test_result, extra=self.__dict__)
        return test_result

    def arithmetic(self, content):
        """Perform an arithmetic evaluation."""
        import operator

        criteria = self.MATCH_CRITERIA
        match = self.MATCH_CONTENT
        operations = {'eq': operator.eq, 'ge': operator.ge, 'gt': operator.gt,
                      'le': operator.le, 'lt': operator.lt, 'ne': operator.ne}

        test_result = operations[criteria](content, match) and content and \
            re.search('^-?[0-9]+$', content) is not None

        eventlog.info("%s TEST | '%s' %s '%s' => %s", self.TEST_TYPE.upper(),
                      content, criteria, match, test_result,
                      extra=self.__dict__)

        return test_result

    def content(self, content):
        """Perform a content evaluation."""
        criteria = self.MATCH_CRITERIA
        match = self.MATCH_CONTENT
        operations = {'contains': self._contains,
                      'does_not_contain': self._notcontains,
                      'matches': self._matches,
                      'does_not_match': self._notmatch,
                      'null': self._null,
                      'not_null': self._notnull}

        test_result = operations[criteria](match, content)

        return test_result

    def test(self):
        """Perform evaluation of COMMAND output per TEST_TYPE."""
        if (self.TEST_TYPE == 'arithmetic' and self.arithmetic(self.output)) or \
           (self.TEST_TYPE == 'content' and self.content(self.output)) or \
           (self.TEST_TYPE == 'status' and self.arithmetic(str(self.exit))):
            return True

    def execute(self):
        """Execute COMMAND."""
        process = _bash(self.COMMAND)
        self.output = process.stdout.read().decode().strip()
        self.exit = process.wait()

    def verify(self):  # pylint: disable=R0912
        """Verify  that an event file is formatted correctly."""
        elements = ['COMMAND', 'EVENT_NAME', 'MATCH_CRITERIA',
                    'STATUS', 'TEST_TYPE']
        missing = []
        problems = 0

        if not self.MATCH_CONTENT and not re.search('^(null|not_null)$',
                                                    self.MATCH_CRITERIA):
            missing.append('MATCH_CONTENT')

        for element in elements:
            if not getattr(self, element):
                missing.append(element)

        if missing:
            eventlog.error("Missing: %s", ' '.join(missing),
                           extra=self.__dict__)
            problems += 1

        if self.TEST_TYPE and not re.search('^(arithmetic|content|status)$',
                                            self.TEST_TYPE):
            eventlog.error("Invalid TEST_TYPE", extra=self.__dict__)
            problems += 1

        if self.TEST_TYPE and re.search('^(arithmetic|status)$',
                                        self.TEST_TYPE):
            if self.MATCH_CONTENT and not re.search('^-?[0-9]+$',
                                                    self.MATCH_CONTENT):
                eventlog.error("MATCH_CONTENT must be an integer for "
                               "arithmetic operations", extra=self.__dict__)
                problems += 1

            if self.MATCH_CRITERIA and not re.search('^(eq|ge|gt|le|lt|ne)$',
                                                     self.MATCH_CRITERIA):
                eventlog.error("Invalid MATCH_CRITERIA for arithmetic "
                               "operations", extra=self.__dict__)
                problems += 1

        if self.TEST_TYPE == 'content' and self.MATCH_CRITERIA and not \
            re.search('^(contains|does_not_contain|matches|does_not_match|'
                      'null|not_null)$', self.MATCH_CRITERIA):
            eventlog.error("Invalid MATCH_CRITERIA for content operations",
                           extra=self.__dict__)
            problems += 1

        if self.TRIGGER_CUSTOM and self.TRIGGER_NAMED:
            eventlog.error("TRIGGER_CUSTOM and TRIGGER_NAMED are both "
                           "specified (choose one or neither)",
                           extra=self.__dict__)
            problems += 1

        if self.TRIGGER_NAMED:
            if not os.path.isfile(Config.file):
                logger.error("TRIGGER_NAMED must be defined in '%s'",
                             Config.file)
                problems += 1
            elif not os.access(Config.file, os.R_OK):
                logger.error("No read access to '%s'", Config.file)
                problems += 1

        # if not self.TRIGGER_CUSTOM and not self.TRIGGER_NAMED:
        #     eventlog.warning("No trigger configured (will use default)",
        #                      extra=self.__dict__)

        if problems == 1:
            eventlog.warning("Encountered 1 issue verifying event file",
                             extra=self.__dict__)
        elif problems >= 2:
            eventlog.warning("Encountered %s issues verifying event file",
                             problems, extra=self.__dict__)

        return False if problems > 0 else True


class Trigger:
    """Store per-event trigger configuration details."""
    def __init__(self, event):
        self.event = event
        self.set = None
        self.type = None

        self.default = "notify-send --icon=notification-message-im " \
                       "--urgency=critical 'triggerd: {0}' 'We have a " \
                       "trigger event!'".format(self.event.EVENT_NAME)
        if self.event.TRIGGER_CUSTOM:
            self.set = "declare -A event && event[EVENT_NAME]='{0}' && EVENT" \
                       "_NAME='{0}' && {1}".format(self.event.EVENT_NAME,
                                                   self.event.TRIGGER_CUSTOM)
        elif self.event.TRIGGER_NAMED:
            tro = ConfigObj(Config.file)
            named = self.event.TRIGGER_NAMED
            defined = tro.get(named)
            if defined:
                self.set = "declare -A event && event[EVENT_NAME]='{0}' && E" \
                           "VENT_NAME='{0}' && {1}".format \
                           (self.event.EVENT_NAME, defined)
            else:
                eventlog.warning("TRIGGER_NAMED '%s' is not defined in '%s'",
                                 named, Config.file, extra=self.event.__dict__)

        if not self.set:
            eventlog.warning("No trigger configured (will use default)",
                             extra=self.event.__dict__)
            self.type = 'default'
            self.set = self.default

    def execute(self):
        """Execute event's trigger."""
        failure = False
        eventlog.info("Executing trigger (%s)", self.set,
                      extra=self.event.__dict__)

        if _bash(self.set).wait() != 0 and self.type != 'default':
            eventlog.error("Failed to execute custom or named trigger",
                           extra=self.event.__dict__)
            eventlog.error("Executing default trigger...",
                           extra=self.event.__dict__)
            if _bash(self.default).wait() != 0:
                eventlog.error("Failed to execute default trigger",
                               extra=self.event.__dict__)
                failure = True

        if not failure:
            eventlog.info("Successful trigger execution",
                          extra=self.event.__dict__)
            try:
                self.writer()
            except:  # pylint: disable=W0702
                eventlog.error("Exception while updating STATUS to triggered",
                               extra=self.event.__dict__)

    def writer(self):
        """Update event's config file upon trigger."""
        with open(self.event.file) as readfile:
            original_text = readfile.read()

        temp = original_text.replace('STATUS=enabled', 'STATUS=triggered')
        edited_text = temp.replace('STATUS = enabled', 'STATUS = triggered')

        if edited_text != original_text:
            with open(self.event.file, 'w') as writefile:
                writefile.write(edited_text)

            with open(self.event.file) as readfile:
                if re.search('(STATUS=triggered|STATUS = triggered)',
                             readfile.read()):
                    eventlog.info("Event file STATUS successfully updated to "
                                  "triggered", extra=self.event.__dict__)
                else:
                    eventlog.error("Event file STATUS unsuccessfully updated "
                                   "to triggered!", extra=self.event.__dict__)
        else:
            eventlog.error("Event file STATUS not updated (it was already "
                           "changed)", extra=self.event.__dict__)


def _bash(args):
    """Execute bash command."""
    import subprocess
    return subprocess.Popen(['bash', '-c', args],
                            stderr=subprocess.PIPE,
                            stdout=subprocess.PIPE)


def _configure():
    """Prepare initial configuration."""
    from batchpath import GeneratePaths

    opts, args = _parser()

    Config.debug = opts.debug
    Config.verbose = opts.verbose
    Config.verify = opts.verify

    level = logging.DEBUG if Config.debug else logging.INFO if \
        Config.verbose else logging.WARNING

    # global eventlog
    eventlog.setLevel(level)
    # global logger
    logger.setLevel(level)

    Config.file = "{0}/.config/scripts/{1}/triggers.conf" \
                  .format(os.environ['HOME'], __program__)
    Config.events = GeneratePaths().files(args, os.W_OK, ['conf', 'txt'], 0)

    logger.debug("debug = %s", Config.debug)
    logger.debug("verbose = %s", Config.verbose)
    logger.debug("verify = %s", Config.verbose)
    logger.debug("triggerfile = %s", Config.file)
    logger.debug("events = %s", Config.events)
    logger.debug("loglevel = %s", level)


def _events():
    """Process list of event files."""
    import sys

    if not Config.events:
        logger.error("You have not supplied any valid targets")
        logger.error("Try '%s --help' for more information.", __program__)
        sys.exit(1)

    for path in Config.events:
        event = Event(path)

        if event.skip:
            continue

        event.execute()

        if event.test():
            trigger = Trigger(event)
            trigger.execute()


def _logging():
    """Initialize program and event loggers."""
    # NOTE: There may be significant room for improvement with the logging
    #       functionality. Is there a way to do it without global?

    global eventlog
    eventlog = logging.getLogger('event')
    estream = logging.StreamHandler()
    eformat = logging.Formatter('[%(basename)s] %(levelname)s: %(message)s')
    estream.setFormatter(eformat)
    eventlog.addHandler(estream)

    global logger
    logger = logging.getLogger(__program__)
    tstream = logging.StreamHandler()
    tformat = logging.Formatter('(%(name)s) %(levelname)s: %(message)s')
    tstream.setFormatter(tformat)
    logger.addHandler(tstream)


def _parser():
    """Parse script arguments and options."""
    import argparse

    parser = argparse.ArgumentParser(
        add_help=False,
        description="Trigger an event or notification upon the output "
                    "of a command.",
        usage="%(prog)s [OPTION] <event files|folders>")
    parser.add_argument(
        "--debug",
        action="store_true",
        dest="debug",
        help="set the logging level to debug")
    parser.add_argument(
        "--verbose",
        action="store_true",
        dest="verbose",
        help="show event execution details")
    parser.add_argument(
        "--verify",
        action="store_true",
        dest="verify",
        help="verify event files without execution")
    parser.add_argument(
        "-h", "--help",
        action="help",
        help=argparse.SUPPRESS)
    parser.add_argument(
        "--version",
        action="version",
        version="{0} {1}".format(__program__, __version__))
    parser.add_argument(
        action="append",
        dest="targets",
        help=argparse.SUPPRESS,
        nargs="*")

    opts = parser.parse_args()
    args = opts.targets[0]

    return opts, args


def main():
    """Start application."""
    _logging()
    _configure()
    _events()


if __name__ == '__main__':
    main()
