#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""Trigger an event or notification upon the output of a command"""

from configobj import ConfigObj
import logging
import os
import re

__program__ = 'triggerd'
__version__ = '0.4'


class Config:  # pylint: disable=R0903
    """Store global script configuration values."""

    default = "declare -A event && event[EVENT_NAME]='{0}' && " \
              "EVENT_NAME='{0}' && {1}"

    trigger = "notify-send --icon=notification-message-im --urgency=" \
              "critical 'triggerd: {0}' 'We have a trigger event!'"

    debug = False
    verbose = False
    verify = False

    events = []
    file = None


class Event:
    """Store per-event configuration details."""
    def __init__(self, path):
        self.exit = None
        self.output = None
        self.skip = False

        self.basename = os.path.basename(path)
        self.path = path

        self.data = ConfigObj(path)

        if Config.verify:
            self.skip = True
            eventlog.info("Verifying only", extra=self.__dict__)
            # TBD: is there a way to wrap eventlog to ensure that all info
            #      messages are delivered when Config.verify is True
            level = eventlog.getEffectiveLevel()
            eventlog.setLevel(logging.INFO)
            if self.verify():
                eventlog.info("Verification OK", extra=self.__dict__)
            else:
                eventlog.info("Verification NOT OK", extra=self.__dict__)
            eventlog.setLevel(level)
            Trigger(self)
        elif self.data.get('STATUS') != 'enabled':
            self.skip = True
            eventlog.info("Not enabled (skipping)", extra=self.__dict__)
        elif not self.verify():
            self.skip = True
            eventlog.info("Failed verification (skipping)",
                          extra=self.__dict__)

    def _contains(self, match, content):
        """content contains match (match in content)."""
        result = match in content
        eventlog.info("CONTENT TEST | '%s' in '%s' => %s", match, content,
                      result, extra=self.__dict__)
        return result

    def _matches(self, match, content):
        """match matches content (match == content)."""
        result = match == content
        eventlog.info("CONTENT TEST | '%s' matches '%s' => %s", match, content,
                      result, extra=self.__dict__)
        return result

    def _notcontains(self, match, content):
        """content does not contain match (match not in content)."""
        result = match not in content
        eventlog.info("CONTENT TEST | '%s' not in '%s' => %s", match, content,
                      result, extra=self.__dict__)
        return result

    def _notmatch(self, match, content):
        """match does not match content (match != content)."""
        result = match != content
        eventlog.info("CONTENT TEST | '%s' does not match '%s' => %s", match,
                      content, result, extra=self.__dict__)
        return result

    def _notnull(self, match, content):  # pylint: disable=W0613
        """content is not null (content != '')."""
        result = content != ''
        eventlog.info("CONTENT TEST | '%s' is not null => '%s'", content,
                      result, extra=self.__dict__)
        return result

    def _null(self, match, content):  # pylint: disable=W0613
        """content is null (content == '')."""
        result = content == ''
        eventlog.info("CONTENT TEST | '%s' is null => '%s'", content,
                      result, extra=self.__dict__)
        return result

    def arithmetic(self, content):
        """Perform an arithmetic evaluation."""
        import operator

        criteria = self.data.get('MATCH_CRITERIA')
        match = self.data.get('MATCH_CONTENT')
        operations = {'eq': operator.eq, 'ge': operator.ge, 'gt': operator.gt,
                      'le': operator.le, 'lt': operator.lt, 'ne': operator.ne}

        result = operations[criteria](content, match) and content and \
            re.search('^-?[0-9]+$', content) is not None

        ttype = self.data.get('TEST_TYPE').upper()
        eventlog.info("%s TEST | '%s' %s '%s' => %s", ttype, content, criteria,
                      match, result, extra=self.__dict__)

        return result

    def content(self, content):
        """Perform a content evaluation."""
        criteria = self.data.get('MATCH_CRITERIA')
        match = self.data.get('MATCH_CONTENT')
        operations = {'contains': self._contains,
                      'does_not_contain': self._notcontains,
                      'matches': self._matches,
                      'does_not_match': self._notmatch,
                      'null': self._null,
                      'not_null': self._notnull}

        result = operations[criteria](match, content)

        return result

    def test(self):
        """Perform evaluation of COMMAND output per TEST_TYPE."""
        ttype = self.data.get('TEST_TYPE')

        if (ttype == 'arithmetic' and self.arithmetic(self.output)) or \
           (ttype == 'content' and self.content(self.output)) or \
           (ttype == 'status' and self.arithmetic(str(self.exit))):
            return True

    def execute(self):
        """Execute COMMAND."""
        process = _bash(self.data.get('COMMAND'))
        self.output = process.stdout.read().decode().strip()
        self.exit = process.wait()

    def verify(self):  # pylint: disable=R0912
        """Verify  that an event file is formatted correctly."""
        problems = 0
        arithmetic_criteria = ['eq', 'ge', 'gt', 'le', 'lt', 'ne', None]
        content_criteria = ['contains', 'does_not_contain', 'matches',
                            'does_not_match', 'null', 'not_null', None]
        required = ['COMMAND', 'EVENT_NAME', 'MATCH_CRITERIA',
                    'STATUS', 'TEST_TYPE']

        ttype = self.data.get('TEST_TYPE')
        mcontent = self.data.get('MATCH_CONTENT')
        mcriteria = self.data.get('MATCH_CRITERIA')
        tcustom = self.data.get('TRIGGER_CUSTOM')
        tnamed = self.data.get('TRIGGER_NAMED')

        missing = [f for f in required if self.data.get(f) is None]

        # check whether MATCH_CONTENT field is necessary
        if not re.search('^(not_)?null$', self.data.get('MATCH_CRITERIA')) \
           and not self.data.get('MATCH_CONTENT'):
            missing.append('MATCH_CONTENT')

        if missing:
            eventlog.error("Missing: %s", ' '.join(missing),
                           extra=self.__dict__)
            problems += 1

        if ttype not in ('arithmetic', 'content', 'status', None):
            eventlog.error("Invalid TEST_TYPE", extra=self.__dict__)
            problems += 1

        if ttype not in ('arithmetic', 'status', None):
            if mcontent and not mcontent.lstrip('-').isdigit():
                eventlog.error("MATCH_CONTENT must be an integer for "
                               "arithmetic operations", extra=self.__dict__)
                problems += 1

            if mcriteria not in arithmetic_criteria:
                eventlog.error("Invalid MATCH_CRITERIA for arithmetic "
                               "operations", extra=self.__dict__)
                problems += 1

        if ttype == 'content' and mcriteria not in content_criteria:
            eventlog.error("Invalid MATCH_CRITERIA for content operations",
                           extra=self.__dict__)
            problems += 1

        if tcustom and tnamed:
            eventlog.error("TRIGGER_CUSTOM and TRIGGER_NAMED are both "
                           "specified (choose one or neither)",
                           extra=self.__dict__)
            problems += 1

        if tnamed:
            if not os.path.isfile(Config.file):
                logger.error("TRIGGER_NAMED must be defined in '%s'",
                             Config.file)
                problems += 1
            elif not os.access(Config.file, os.R_OK):
                logger.error("No read access to '%s'", Config.file)
                problems += 1

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

        eventname = event.data.get('EVENT_NAME')
        customtrigger = event.data.get('TRIGGER_CUSTOM')
        tname = event.data.get('TRIGGER_NAMED')

        self.default = Config.trigger.format(eventname)

        if customtrigger:
            self.set = Config.default.format(eventname, customtrigger)
            eventlog.info("Configured TRIGGER_CUSTOM (%s)", customtrigger,
                          extra=event.__dict__)
        elif tname:
            tro = ConfigObj(Config.file)
            definition = tro.get(tname)
            if definition:
                self.set = Config.default.format(eventname, definition)
                eventlog.info("Configured TRIGGER_NAMED '%s' (%s)", tname,
                              definition, extra=event.__dict__)
            else:
                eventlog.warning("TRIGGER_NAMED '%s' is not defined in '%s'",
                                 tname, Config.file, extra=event.__dict__)

        if self.set is None:
            self.type = 'default'
            self.set = self.default
            eventlog.warning("No trigger configured (will use default)",
                             extra=event.__dict__)

    def execute(self):
        """Manage execution of event's trigger."""
        eventlog.info("Executing trigger (%s)", self.set,
                      extra=self.event.__dict__)

        if self.helper():
            try:
                eventlog.info("Updating event file STATUS to triggered",
                              extra=self.event.__dict__)
                self.writer()
            except:
                eventlog.error("Exception while updating STATUS to triggered",
                               extra=self.event.__dict__)

    def helper(self):
        """Execute event's trigger and return success status."""

        status = _bash(self.set).wait()
        if status != 0 and self.type != 'default':
            eventlog.error("Failed to execute custom or named trigger",
                           extra=self.event.__dict__)

            retry = _bash(self.default).wait()
            if retry != 0:
                eventlog.error("Retry failed to execute default trigger",
                               extra=self.event.__dict__)
            elif retry == 0:
                eventlog.info("Retry successfully executed default trigger",
                              extra=self.event.__dict__)
                return True
        elif status == 0:
            if self.type == 'default':
                eventlog.info("Successfully executed default trigger",
                              extra=self.event.__dict__)
            else:
                eventlog.info("Successfully executed configured trigger",
                              extra=self.event.__dict__)
            return True

    def writer(self):
        """Update event's config file upon trigger."""
        with open(self.event.path) as readfile:
            original_text = readfile.read()

        temp = original_text.replace('STATUS=enabled', 'STATUS=triggered')
        edited_text = temp.replace('STATUS = enabled', 'STATUS = triggered')

        if edited_text != original_text:
            with open(self.event.path, 'w') as writefile:
                writefile.write(edited_text)

            with open(self.event.path) as readfile:
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

    eventlog.setLevel(level)
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


# def _logging():
#     """Initialize program and event loggers."""
#     # NOTE: There may be significant room for improvement with the logging
#     #       functionality. Is there a way to do it without global?

#     global eventlog
#     eventlog = logging.getLogger('event')
#     estream = logging.StreamHandler()
#     eformat = logging.Formatter('[%(basename)s] %(levelname)s: %(message)s')
#     estream.setFormatter(eformat)
#     eventlog.addHandler(estream)

#     global logger
#     logger = logging.getLogger(__program__)
#     tstream = logging.StreamHandler()
#     tformat = logging.Formatter('(%(name)s) %(levelname)s: %(message)s')
#     tstream.setFormatter(tformat)
#     logger.addHandler(tstream)


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
    # _logging()
    _configure()
    _events()


if __name__ == '__main__':
    # NOTE: There may be significant room for improvement with this
    #       logging implementation. Is there a way?
    eventlog = logging.getLogger('event')
    estream = logging.StreamHandler()
    eformat = logging.Formatter('[%(basename)s] %(levelname)s: %(message)s')
    estream.setFormatter(eformat)
    eventlog.addHandler(estream)

    logger = logging.getLogger(__program__)
    tstream = logging.StreamHandler()
    tformat = logging.Formatter('(%(name)s) %(levelname)s: %(message)s')
    tstream.setFormatter(tformat)
    logger.addHandler(tstream)

    main()
