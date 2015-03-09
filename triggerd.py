#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""Trigger an event or notification upon the output of a command"""

__program__ = 'triggerd'
__version__ = '0.1'


class Config:
    """Store global script configuration values."""
    events = []
    verbose = False
    verify = False


class Event:
    """Store per-event configuration details."""
    def __init__(self, file):
        self.exit = None
        self.file = file
        self.output = None
        self.skip = False

        self.loader = ConfigObj(file)
        self.COMMAND = self.loader.get('COMMAND')
        self.EVENT_NAME = self.loader.get('EVENT_NAME')
        self.MATCH_CONTENT = self.loader.get('MATCH_CONTENT')
        self.MATCH_CRITERIA = self.loader.get('MATCH_CRITERIA')
        self.STATUS = self.loader.get('STATUS')
        self.TEST_TYPE = self.loader.get('TEST_TYPE')
        self.TRIGGER_CUSTOM = self.loader.get('TRIGGER_CUSTOM')
        self.TRIGGER_NAMED = self.loader.get('TRIGGER_NAMED')

        if Config.verify:
            self.verify()
            self.skip = True
        elif self.STATUS != 'enabled' or not self.verify():
            self.skip = True

    def _contains(self, match, content):
        """content contains match (match in content)."""
        test_result = match in content
        log(self.file, "(content test)    '%s' in '%s' => %s" % (match, content, test_result))
        return test_result

    def _matches(self, match, content):
        """match matches content (match == content)."""
        test_result = match == content
        log(self.file, "(content test)    '%s' matches '%s' => %s" % (match, content, test_result))
        return test_result

    def _notcontains(self, match, content):
        """content does not contain match (match not in content)."""
        test_result = match not in content
        log(self.file, "(content test)    '%s' not in '%s' => %s" % (match, content, test_result))
        return test_result

    def _notmatch(self, match, content):
        """match does not match content (match != content)."""
        test_result = match != content
        log(self.file, "(content test)    '%s' does not match '%s' => %s" % (match, content, test_result))
        return test_result

    def _notnull(self, match, content):
        """content is not null (content != '')."""
        test_result = content != ''
        log(self.file, "(content test)    '%s' is not null => %s" % (content, test_result))
        return test_result

    def _null(self, match, content):
        """content is null (content == '')."""
        test_result = content == ''
        log(self.file, "(content test)    '%s' is null => %s" % (content, test_result))
        return test_result

    def arithmetic(self, content):  # load all version
        """Perform an arithmetic evaluation."""
        import operator

        criteria = self.MATCH_CRITERIA
        match = self.MATCH_CONTENT
        operations = {'eq': operator.eq, 'ge': operator.ge, 'gt': operator.gt,
                      'le': operator.le, 'lt': operator.lt, 'ne': operator.ne}

        test_result = operations[criteria](content, match) and content and \
            re.search('^-?[0-9]+$', content)

        log(self.file, "(%s test)    '%s' %s '%s' => %s" % (self.TEST_TYPE, content, criteria, match, test_result))

        return test_result

    def content(self, content):    # custom functions load all version
        """Perform a content evaluation."""
        criteria = self.MATCH_CRITERIA
        match = self.MATCH_CONTENT
        operations = {'contains': self._contains, 'does_not_contain': self._notcontains,
                      'does_not_match': self._notmatch, 'matches': self._matches,
                      'not_null': self._notnull, 'null': self._null}

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
        process = bash(self.COMMAND)
        self.output = process.stdout.read().decode().strip()
        self.exit = process.wait()

    def verify(self):
        """Verify event file."""
        missing = []
        problems = 0

        if not self.MATCH_CONTENT and \
           not re.search('^(null|not_null)$', self.MATCH_CRITERIA):
            missing.append('MATCH_CONTENT')

        for element in ['COMMAND', 'EVENT_NAME', 'MATCH_CRITERIA', 'STATUS', 'TEST_TYPE']:
            if not getattr(self, element):
                missing.append(element)

        if len(missing) > 0:
            error("'{0}' is missing {1}".format(self.file, ' '.join(missing)))
            problems += 1

        if self.TEST_TYPE and not re.search('^(arithmetic|content|status)$', self.TEST_TYPE):
            error("'{0}' does not contain a valid TEST_TYPE".format(self.file))
            problems += 1

        if self.TEST_TYPE and re.search('^(arithmetic|status)$', self.TEST_TYPE):
            if self.MATCH_CONTENT and not re.search('^-?[0-9]+$', self.MATCH_CONTENT):
                error("'{0}' MATCH_CONTENT must be an integer when performing arithmetic operations".format(self.file))
                problems += 1

            if self.MATCH_CRITERIA and not re.search('^(eq|ge|gt|le|lt|ne)$', self.MATCH_CRITERIA):
                error("'{0}' does not contain valid MATCH_CRITERIA for arithmetic operations".format(self.file))
                problems += 1

        if self.TEST_TYPE == 'content' and self.MATCH_CRITERIA and not re.search('^(contains|does_not_contain|matches|does_not_match|null|not_null)$', self.MATCH_CRITERIA):
            error("'{0}' does not contain valid MATCH_CRITERIA for content operations".format(self.file))
            problems += 1

        if self.TRIGGER_CUSTOM and self.TRIGGER_NAMED:
            error("'{0}' specifies both TRIGGER_CUSTOM and TRIGGER_NAMED (choose one or neither)".format(self.file))
            problems += 1

        if self.TRIGGER_NAMED:
            if not os.path.isfile(Config.file):
                error("TRIGGER_NAMED must be defined in '{0}'".format(Config.file))
                problems += 1
            elif not os.access(Config.file, os.R_OK):
                error("No read access to '{0}'".format(Config.file))
                problems += 1

        if problems == 1:
            warning("Encountered 1 issue verifying '{0}'".format(self.file))
        elif problems >= 2:
            warning("Encountered {0} issues verifying '{1}'".format(problems, self.file))

        return False if problems > 0 else True


class Trigger:
    """Store per-event trigger configuration details."""
    def __init__(self, event_object):
        self.event = event_object
        self.set = None
        self.type = None

        self.default = 'notify-send --icon=notification-message-im --urgency=critical "triggerd: {0}" "We have a trigger event!"'.format(self.event.EVENT_NAME)
        if self.event.TRIGGER_CUSTOM:
            self.set = "declare -A event && event[EVENT_NAME]='{0}' && EVENT_NAME='{0}' && {1}".format(self.event.EVENT_NAME, self.event.TRIGGER_CUSTOM)
        elif self.event.TRIGGER_NAMED:
            tro = ConfigObj(Config.file)
            named = self.event.TRIGGER_NAMED
            defined = tro.get(named)
            if defined:
                self.set = "declare -A event && event[EVENT_NAME]='{0}' && EVENT_NAME='{0}' && {1}".format(self.event.EVENT_NAME, defined)
            else:
                warning("TRIGGER_NAMED '{0}' not defined in '{1}' for '{2}'".format(named, Config.file, self.event.path))

        if not self.set:
            self.type = 'default'
            self.set = self.default
            warning('Resorting to default trigger')

    def execute(self):
        """Execute event's trigger."""
        failure = None
        log(self.event.file, "(executing trigger)    '%s'" % self.set)
        if bash(self.set).wait() != 0 and self.type != 'default':
            log(self.event.file, "(failed to execute custom or named trigger)")
            if bash(self.default).wait() != 0:
                log(self.event.file, "(failed to execute default trigger)")
                failure = True
        if not failure:
            log(self.event.file, "(successful trigger)")
            self.writer()

    def writer(self):
        """Update event's config file upon trigger."""
        with open(self.event.file) as readfile:
            text = readfile.read()
        text = text.replace('STATUS=enabled', 'STATUS=triggered')
        text = text.replace('STATUS = enabled', 'STATUS = triggered')
        with open(self.event.file, 'w') as writefile:
            writefile.write(text)


def _parser():
    """Parse script arguments and options."""
    import argparse

    parser = argparse.ArgumentParser(
        add_help=False,
        description="Trigger an event or notification upon the output of a command.",
        usage="%(prog)s [OPTION] <event files|folders>")
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


def bash(args):
    """Execute bash command."""
    import subprocess
    return subprocess.Popen(['bash', '-c', args],
                            stderr=subprocess.PIPE,
                            stdout=subprocess.PIPE)


def _configure():
    """Prepare initial configuration."""
    Config.home = os.environ['HOME']
    Config.script = os.path.basename(sys.argv[0])
    Config.file = '{0}/.config/scripts/{1}/triggers.conf'.format(Config.home,
                                                                 __program__)


def error(*objs):
    """Print error message to stderr."""
    print('ERROR:', *objs, file=sys.stderr)


def eventhandler(events):
    """Process list of event files."""
    for path in events:
        event = Event(path)

        if event.skip:
            continue

        event.execute()

        if event.test():
            trigger = Trigger(event)
            trigger.execute()


def log(filename, message):
    """Print verbose logging to console."""
    if Config.verbose:
        stderr("{0:<20} {1}".format(os.path.basename(filename), message))


def main():
    """Start application."""
    from batchpath import GeneratePaths

    _configure()

    opts, args = _parser()

    Config.verbose = opts.verbose
    Config.verify = opts.verify
    Config.events = GeneratePaths().files(args, os.W_OK, ['conf', 'txt'], 0)

    if len(Config.events) == 0:
        error('You have not supplied any valid targets')
        stderr("Try '{0} --help' for more information.".format(Config.script))
        sys.exit(1)

    eventhandler(Config.events)


def stderr(*objs):
    """Print message to stderr."""
    print(*objs, file=sys.stderr)


def warning(*objs):
    """Print warning message to stderr."""
    print('WARNING:', *objs, file=sys.stderr)


from configobj import ConfigObj
import os
import re
import sys

if __name__ == '__main__':
    main()
