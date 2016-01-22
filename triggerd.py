#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""Trigger an event or notification upon the output of a command"""

import logging

__program__ = 'triggerd'
__version__ = '0.5.4'
__description__ = 'Trigger an event or notification ' \
                  'upon the output of a command.'


class EventFile:

    """Manipulate event file."""

    def __init__(self, path, config=None):

        import configobj
        import os

        # event file path
        self.path = path

        # event file basename
        self.basename = os.path.basename(self.path)

        # open event as a config file
        self.data = configobj.ConfigObj(
            self.path, interpolation=False, list_values=False)

        # trigger config file path
        self.config = config

    class TriggerFile:

        """Manipulate event trigger configuration."""

        def __init__(self, event):
            """Configure trigger."""

            import configobj

            log = logging.getLogger('event')

            self.event = event

            default = "declare -A event\n" \
                      "EVENT_NAME=$(cat <<'__EOF__'\n" \
                      "{0}\n" \
                      "__EOF__\n" \
                      ")\n" \
                      "event[EVENT_NAME]=$EVENT_NAME\n" \
                      "MATCH_CONTENT=$(cat <<'__EOF__'\n" \
                      "{1}\n" \
                      "__EOF__\n" \
                      ")\n" \
                      "event[MATCH_CONTENT]=$MATCH_CONTENT\n" \
                      "{2}"

            trigger = """notify-send --icon=notification-message-im """ \
                      """--urgency=critical "triggerd: $EVENT_NAME" """ \
                      """'We have a trigger event!'"""

            event_name = self.event.data.get('EVENT_NAME')
            match_content = self.event.data.get('MATCH_CONTENT')
            trigger_custom = self.event.data.get('TRIGGER_CUSTOM')
            trigger_named = self.event.data.get('TRIGGER_NAMED')

            self.default_string = trigger
            self.trigger_string = None

            if trigger_custom:
                self.trigger_string = default.format(
                    event_name, match_content, trigger_custom)
                log.info(
                    "Configured to use TRIGGER_CUSTOM (%s)",
                    trigger_custom, extra=self.event.__dict__)

            elif trigger_named:
                trigger_file = configobj.ConfigObj(self.event.config,
                                                   interpolation=False,
                                                   list_values=False)
                trigger_definition = trigger_file.get(trigger_named)
                if trigger_definition:
                    self.trigger_string = default.format(
                        event_name, match_content, trigger_definition)
                    log.info(
                        "Configured to use TRIGGER_NAMED '%s' (%s)",
                        trigger_named, trigger_definition,
                        extra=self.event.__dict__)
                else:
                    log.info(
                        "TRIGGER_NAMED '%s' is not defined in '%s'",
                        trigger_named, self.event.config,
                        extra=self.event.__dict__)

            # resort to default trigger
            if self.trigger_string is None:
                self.trigger_string = default.format(
                        event_name, match_content, self.default_string)
                log.warning(
                    "No trigger configured (will use default)",
                    extra=self.event.__dict__)

        def execute(self):
            """Manage execution of event's trigger."""

            log = logging.getLogger('event')
            log.info(
                "Executing trigger (%s)", self.trigger_string,
                extra=self.event.__dict__)

            # update event STATUS upon success
            if self.helper():
                self.writer()

        def helper(self):
            """Execute event's trigger and return success status."""

            log = logging.getLogger('event')

            if _getstatus(self.trigger_string) == 0:

                if self.is_default:
                    log.info("Successfully executed default trigger",
                             extra=self.event.__dict__)
                else:
                    log.info("Successfully executed configured trigger",
                             extra=self.event.__dict__)
                return True

            elif not self.is_default:

                log.error("Failed to execute custom or named trigger",
                          extra=self.event.__dict__)

                if _getstatus(self.default_string) == 0:
                    log.info("Retry successfully executed default trigger",
                             extra=self.event.__dict__)
                    return True

                else:
                    log.error("Retry failed to execute default trigger",
                              extra=self.event.__dict__)

            else:

                log.error("Failed to execute default trigger",
                          extra=self.event.__dict__)

            return False

        @property
        def is_default(self):
            """Check whether currently trigger is the default."""
            return self.trigger_string == self.default_string

        def writer(self):
            """Update event's config file upon trigger."""

            import configobj
            import subprocess

            log = logging.getLogger('event')

            log.debug("Updating event file STATUS to triggered",
                      extra=self.event.__dict__)

            # ensure STATUS is not already set to triggered
            if self.event.data.get('STATUS') == 'triggered':
                log.error("Event file STATUS not updated (it was already "
                          "changed)", extra=self.event.__dict__)
                return

            sedscript = 's/STATUS=enabled/STATUS=triggered/;' \
                        's/STATUS = enabled/STATUS = triggered/'

            try:
                # update STATUS to triggered
                subprocess.check_call(
                    ['sed', '-i', sedscript, self.event.data.filename],
                    stderr=subprocess.PIPE,
                    stdout=subprocess.PIPE)
            except subprocess.CalledProcessError:
                log.error("Exception while updating STATUS to triggered",
                          extra=self.event.__dict__)
                return

            try:
                # reload event
                self.event.data.reload()
            except configobj.ReloadError:
                log.error("Failed to reload event file after update",
                          extra=self.event.__dict__)
                return

            # ensure STATUS was set to triggered
            if self.event.data.get('STATUS') == 'triggered':
                log.info("STATUS successfully updated to triggered",
                         extra=self.event.__dict__)
                return
            else:
                log.error("STATUS unsuccessfully updated to triggered!",
                          extra=self.event.__dict__)
                return

    def _contains(self, match, content):
        """content contains match (match in content)."""
        result = match in content

        log = logging.getLogger('event')
        log.info("CONTENT TEST | '%s' in '%s' => %s", match,
                 content, result, extra=self.__dict__)

        return result

    def _matches(self, match, content):
        """match matches content (match == content)."""
        result = match == content

        log = logging.getLogger('event')
        log.info("CONTENT TEST | '%s' matches '%s' => %s", match,
                 content, result, extra=self.__dict__)

        return result

    def _notcontains(self, match, content):
        """content does not contain match (match not in content)."""
        result = match not in content

        log = logging.getLogger('event')
        log.info("CONTENT TEST | '%s' not in '%s' => %s", match,
                 content, result, extra=self.__dict__)

        return result

    def _notmatch(self, match, content):
        """match does not match content (match != content)."""
        result = match != content

        log = logging.getLogger('event')
        log.info("CONTENT TEST | '%s' does not match '%s' => %s",
                 match, content, result, extra=self.__dict__)

        return result

    def _notnull(self, match, content):  # pylint: disable=W0613
        """content is not null (content != '')."""
        result = content != ''

        log = logging.getLogger('event')
        log.info("CONTENT TEST | '%s' is not null => '%s'",
                 content, result, extra=self.__dict__)

        return result

    def _null(self, match, content):  # pylint: disable=W0613
        """content is null (content == '')."""
        result = content == ''

        log = logging.getLogger('event')
        log.info("CONTENT TEST | '%s' is null => '%s'", content,
                 result, extra=self.__dict__)

        return result

    def arithmetic(self, content):
        """Perform an arithmetic evaluation."""
        import operator

        log = logging.getLogger('event')

        operations = {
            'eq': operator.eq, 'ge': operator.ge, 'gt': operator.gt,
            'le': operator.le, 'lt': operator.lt, 'ne': operator.ne
            }

        criteria = self.data.get('MATCH_CRITERIA')

        try:
            content = int(content)
        except ValueError:
            log.info(
                "'%s' is not an integer (required for arithmetic "
                "operations)", content, extra=self.__dict__)
            return False

        try:
            match = int(self.data.get('MATCH_CONTENT'))
        except ValueError:
            log.error(
                "MATCH_CONTENT must be an integer for arithmetic "
                "operations", extra=self.__dict__)
            return False

        result = operations[criteria](content, match)

        test_type = self.data.get('TEST_TYPE').upper()

        log.info(
            "%s TEST | '%s' %s '%s' => %s", test_type, content,
            criteria, match, result, extra=self.__dict__)

        return result

    def content(self, content):
        """Perform a content evaluation."""

        operations = {
            'contains': self._contains,
            'does_not_contain': self._notcontains,
            'matches': self._matches,
            'does_not_match': self._notmatch,
            'null': self._null,
            'not_null': self._notnull
            }

        criteria = self.data.get('MATCH_CRITERIA')
        match = self.data.get('MATCH_CONTENT')

        result = operations[criteria](match, content)

        return result

    @property
    def enabled(self):
        """Check whether an event file is enabled."""
        return self.data.get('STATUS') == 'enabled'

    def test(self):
        """Execute and evaluate output of COMMAND per TEST_TYPE."""

        status, output = _getstatusoutput(self.data.get('COMMAND'))

        test_type = self.data.get('TEST_TYPE')

        if (test_type == 'arithmetic' and self.arithmetic(output)) or \
           (test_type == 'content' and self.content(output)) or \
           (test_type == 'status' and self.arithmetic(status)):
            return True

    def verify(self):
        """Verify  that an event file is formatted correctly."""

        import re

        log = logging.getLogger('event')

        problems = 0

        test_types = ['arithmetic', 'content', 'status']
        arithmetic_criteria = ['eq', 'ge', 'gt', 'le', 'lt', 'ne']
        content_criteria = ['contains', 'does_not_contain', 'matches',
                            'does_not_match', 'null', 'not_null']

        # ensure we don't display errors for missing fields
        for dummy in [test_types, arithmetic_criteria, content_criteria]:
            dummy += [None, '']

        required = ['COMMAND', 'EVENT_NAME', 'MATCH_CRITERIA',
                    'STATUS', 'TEST_TYPE']

        missing = [f for f in required if not self.data.get(f)]

        # ensure MATCH_CONTENT exists
        # (unless MATCH_CRITERIA is null or not_null)
        if self.data.get('MATCH_CONTENT') is None and \
            re.search('^(not_)?null$',
                      self.data.get('MATCH_CRITERIA')) is None:
            missing.append('MATCH_CONTENT')

        # identify missing mandatory fields
        if missing:
            log.error("Missing %s", ' '.join(missing), extra=self.__dict__)
            problems += 1

        # ensure TEST_TYPE is a valid test type
        if self.data.get('TEST_TYPE') not in test_types:
            log.error("Invalid TEST_TYPE", extra=self.__dict__)
            problems += 1

        # perform verification for arithmetic and status tests
        if self.data.get('TEST_TYPE') in ('arithmetic', 'status'):

            try:
                # ensure MATCH_CONTENT is an integer
                self.data.get('MATCH_CONTENT') is None or \
                    int(self.data.get('MATCH_CONTENT'))
            except ValueError:
                log.error(
                    "MATCH_CONTENT must be an integer for arithmetic "
                    "operations", extra=self.__dict__)
                problems += 1

            # ensure MATCH_CRITERIA is an arithmetic operation
            if self.data.get('MATCH_CRITERIA') not in arithmetic_criteria:
                log.error(
                    "Invalid MATCH_CRITERIA for arithmetic operations",
                    extra=self.__dict__)
                problems += 1

        # perform verification for content tests
        elif self.data.get('TEST_TYPE') == 'content':

            # ensure MATCH_CRITERIA is a content operation
            if self.data.get('MATCH_CRITERIA') not in content_criteria:
                log.error("Invalid MATCH_CRITERIA for content operations",
                          extra=self.__dict__)
                problems += 1

        # ensure custom and named triggers are not used concurrently
        if self.data.get('TRIGGER_CUSTOM') and \
           self.data.get('TRIGGER_NAMED'):
            log.error(
                "TRIGGER_CUSTOM and TRIGGER_NAMED are both indicated "
                "(choose one or neither)", extra=self.__dict__)
            problems += 1

        if problems == 1:
            log.warning("Encountered 1 issue verifying event file",
                        extra=self.__dict__)
        elif problems >= 2:
            log.warning("Encountered %s issues verifying event file",
                        problems, extra=self.__dict__)

        return problems == 0


class EventRunner:

    """Execute event file."""

    def __init__(self, path, config=None):

        log = logging.getLogger('event')

        eventfile = EventFile(path, config)

        log.info("Processing event", extra=eventfile.__dict__)

        # ensure event is enabled
        if not eventfile.enabled:

            log.info("Not enabled (skipping)", extra=eventfile.__dict__)
            return

        # ensure event verification is successful
        elif not eventfile.verify():

            log.info("Failed verification (skipping)",
                     extra=eventfile.__dict__)
            return

        if eventfile.test():
            trigger = EventFile.TriggerFile(eventfile)
            trigger.execute()


class EventVerifier:

    """Verify event file."""

    def __init__(self, path, config=None):

        log = logging.getLogger('event')

        eventfile = EventFile(path, config)

        log.info("Verifying only", extra=eventfile.__dict__)

        # store the original log level
        level = log.getEffectiveLevel()

        # ensure verification messages are displayed
        log.setLevel(logging.INFO)

        status = eventfile.verify()

        # initialize trigger (to display configuration warnings)
        EventFile.TriggerFile(eventfile)

        if status:
            log.info("Verification OK", extra=eventfile.__dict__)
        else:
            log.info("Verification NOT OK", extra=eventfile.__dict__)

        # restore original log level
        log.setLevel(level)


def _eventlogger(logfile=None, loglevel=logging.WARNING):
    """Configure event logger."""

    eventlogger = logging.getLogger('event')

    # ensure logger is not reconfigured
    if not eventlogger.hasHandlers():

        # set log level
        eventlogger.setLevel(loglevel)

        fmt = '[%(basename)s] %(levelname)s: %(message)s'

        # configure terminal log
        streamhandler = logging.StreamHandler()
        streamhandler.setFormatter(logging.Formatter(fmt))
        eventlogger.addHandler(streamhandler)

        # configure log file (if necessary)
        if logfile is not None:
            fileformatter = logging.Formatter(
                '%(asctime)s.%(msecs)03d ' + fmt,
                '%Y-%m-%d %H:%M:%S')
            filehandler = logging.FileHandler(logfile)
            filehandler.setFormatter(fileformatter)
            eventlogger.addHandler(filehandler)


def _getstatus(args):
    """Execute bash command returning exit status."""
    import subprocess

    return subprocess.call(args,
                           executable='bash',
                           shell=True,
                           stderr=subprocess.PIPE,
                           stdout=subprocess.PIPE)


def _getstatusoutput(args):
    """Execute bash command returning output and exit status."""
    import subprocess

    process = subprocess.Popen(args,
                               executable='bash',
                               shell=True,
                               stderr=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               universal_newlines=True)

    output = process.stdout.read().strip()
    status = process.wait()

    return status, output


def _parser(args):
    """Parse script arguments and options."""
    import argparse
    import os

    config = os.path.join(
        os.environ.get('XDG_CONFIG_DIR') or
        os.path.join(os.environ.get('HOME'), '.config'),
        __program__, 'triggers.conf')

    class SmartFormatter(argparse.HelpFormatter):
        """Permit the use of raw text in help messages with 'r|' prefix."""

        def _split_lines(self, text, width):
            """argparse.RawTextHelpFormatter._split_lines"""
            if text.startswith('r|'):
                return text[2:].splitlines()
            return argparse.HelpFormatter._split_lines(self, text, width)

    # pylint: disable=too-few-public-methods
    class NegateAction(argparse.Action):
        """Support --toggle and --no-toggle options."""

        def __call__(self, parser, namespace, values, option_string=None):
            setattr(namespace, self.dest, option_string[2:4] != 'no')

    def path(value):
        """Ensure path is a directory or file-like object."""
        if os.path.isdir(value):
            return value

        try:
            open(value)
            return value
        except:
            raise argparse.ArgumentTypeError(
                "invalid path value: '%s'" % value)

    parser = argparse.ArgumentParser(
        add_help=False,
        description=__description__,
        formatter_class=SmartFormatter,
        usage='%(prog)s [OPTION] <event files|folders>')
    parser.add_argument(
        '-f', '--file',
        default=config,
        dest='config',
        help='r|indicate trigger config file\n'
             'Default: %s' % config)
    parser.add_argument(
        '-h', '--help',
        action='help',
        help=argparse.SUPPRESS)
    parser.add_argument(
        '--parallel', '--no-parallel',
        action=NegateAction,
        default=None,
        dest='parallel',
        help='execute events in parallel (default)',
        nargs=0)
    parser.add_argument(
        '--verify',
        action='store_true',
        dest='verify',
        help='verify event files without execution')
    parser.add_argument(
        '--version',
        action='version',
        version='{0} {1}'.format(__program__, __version__))

    group = parser.add_argument_group('logging options')
    group.add_argument(
        '--debug',
        action='store_true',
        dest='debug',
        help='set the logging level to debug')
    group.add_argument(
        '-l', '--log',
        dest='logfile',
        help='set log file destination')
    group.add_argument(
        '--verbose',
        action='store_true',
        dest='verbose',
        help='set the logging level to verbose')

    parser.add_argument(
        dest='targets',
        help=argparse.SUPPRESS,
        nargs='*',
        type=path)

    options = parser.parse_args(args)
    arguments = options.targets

    return options, arguments


def _scriptlogger(logfile=None, loglevel=logging.WARNING):
    """Configure program logger."""

    scriptlogger = logging.getLogger(__program__)

    # ensure logger is not reconfigured
    if not scriptlogger.hasHandlers():

        # set log level
        scriptlogger.setLevel(loglevel)

        fmt = '(%(name)s) %(levelname)s: %(message)s'

        # configure terminal log
        streamhandler = logging.StreamHandler()
        streamhandler.setFormatter(logging.Formatter(fmt))
        scriptlogger.addHandler(streamhandler)

        # configure log file (if necessary)
        if logfile is not None:
            fileformatter = logging.Formatter(
                '%(asctime)s.%(msecs)03d ' + fmt,
                '%Y-%m-%d %H:%M:%S')
            filehandler = logging.FileHandler(logfile)
            filehandler.setFormatter(fileformatter)
            scriptlogger.addHandler(filehandler)


def eventhandler(paths,
                 config=None,
                 verify=False,
                 logfile=None,
                 loglevel=logging.WARNING,
                 parallel=False):
    """Execute or verify event files."""

    # configure event logger
    _eventlogger(logfile, loglevel)

    if not verify and parallel:

        # from multiprocessing import Pool, cpu_count
        import concurrent.futures
        from multiprocessing import cpu_count

        workers = cpu_count() * 4

        # define in global namespace to ensure it can be pickled
        global wrapper

        # use closure to permit use of wrapper with one argument
        # DEBUG: ensure config is accessible during runtime
        def wrapper(path):
            EventRunner(path, config)

        # pool = Pool(processes=workers)
        # pool.map(wrapper, paths)

        with concurrent.futures.ProcessPoolExecutor(workers) as executor:
            executor.map(wrapper, paths)

    else:

        action = EventVerifier if verify else EventRunner

        for path in paths:
            action(path, config)


def generate_paths(paths):
    """
    Iterates over `paths` (which may consist of files and/or directories)
    and return list of files.
    """

    import os
    import subprocess

    files = []
    for path in paths:
        if os.path.isdir(path):
            files += sorted(subprocess.check_output(
                ['find', path,
                 '-type', 'f',
                 '-readable',
                 '-writable',
                 '!', '-empty',
                 '(', '-name', '*.conf', '-o', '-name', '*.txt', ')',
                 '-print0'],
                stderr=subprocess.DEVNULL,
                universal_newlines=True).rstrip('\0').split('\0'))
        else:
            files.append(path)

    return files


def main(args=None):
    """Start and configure application."""

    import sys

    options, arguments = _parser(args)

    # determine log level
    options.loglevel = logging.DEBUG if options.debug else logging.INFO if \
        options.verbose else logging.WARNING

    # configure script logger
    _scriptlogger(options.logfile, options.loglevel)

    log = logging.getLogger(__program__)

    events = generate_paths(arguments)

    if not events:
        log.error("You have not supplied any valid targets")
        log.error("Try '%s --help' for more information.", __program__)
        sys.exit(1)
    elif options.verify and options.parallel:
        log.warning("Ignoring use of '--parallel' as it may slow verification")
    elif not options.verify and options.parallel is None:
        options.parallel = True

    log.info('processing %s events', len(events))
    log.debug('events = %s', events)
    log.debug('verify = %s', options.verify)
    log.debug('triggerfile = %s', options.config)
    log.debug('logfile = %s', options.logfile)
    log.debug('loglevel = %s', options.loglevel)
    log.debug('parallel = %s', options.parallel)

    eventhandler(events,
                 options.config,
                 options.verify,
                 options.logfile,
                 options.loglevel,
                 options.parallel)


if __name__ == '__main__':
    main()
