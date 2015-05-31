#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""Trigger an event or notification upon the output of a command"""

__program__ = 'triggerd'
__version__ = '0.4.4'


class EventHandler:

    def __init__(self, paths, config=None, verify=False):
        action = self.EventVerifier if verify else self.EventRunner

        for path in paths:
            action(path, config)

    class EventFile:
        """Manipulate event file configuration."""
        def __init__(self, path, config=None):
            import os
            from configobj import ConfigObj

            # event file path
            self.path = path

            # event file basename
            self.basename = os.path.basename(self.path)

            # open event as a config file
            self.data = ConfigObj(self.path)

            # trigger config file path
            self.config = config or "{0}/.config/scripts/{1}/triggers.conf" \
                                    .format(os.environ['HOME'], __program__)

        class TriggerFile:
            """Manipulate event trigger configuration."""
            def __init__(self, event):
                """Configure trigger."""

                self.event = event

                default = "declare -A event && event[EVENT_NAME]='{0}' && " \
                          "EVENT_NAME='{0}' && {1}"

                trigger = "notify-send --icon=notification-message-im " \
                          "--urgency=critical 'triggerd: {0}' 'We have " \
                          "a trigger event!'"

                event_name = self.event.data.get('EVENT_NAME')
                trigger_custom = self.event.data.get('TRIGGER_CUSTOM')
                trigger_named = self.event.data.get('TRIGGER_NAMED')

                self.default_string = trigger.format(event_name)

                if trigger_custom:
                    self.trigger_string = default.format(event_name,
                                                         trigger_custom)
                    EVENTLOG.info("Configured to use TRIGGER_CUSTOM (%s)",
                                  trigger_custom, extra=self.event.__dict__)
                elif trigger_named:
                    from configobj import ConfigObj
                    trigger_file = ConfigObj(self.event.config)
                    trigger_definition = trigger_file.get(trigger_named)
                    if trigger_definition:
                        self.trigger_string = default \
                            .format(event_name, trigger_definition)
                        EVENTLOG.info(
                            "Configured to use TRIGGER_NAMED '%s' (%s)",
                            trigger_named, trigger_definition,
                            extra=self.event.__dict__)
                    else:
                        EVENTLOG.info(
                            "TRIGGER_NAMED '%s' is not defined in '%s'",
                            trigger_named, self.event.config,
                            extra=self.event.__dict__)

                # resort to default trigger
                if self.trigger_string is None:
                    self.trigger_string = self.default_string
                    EVENTLOG.warning(
                        "No trigger configured (will use default)",
                        extra=self.event.__dict__)

            def execute(self):
                """Manage execution of event's trigger."""

                EVENTLOG.info("Executing trigger (%s)", self.trigger_string,
                              extra=self.event.__dict__)

                # update event STATUS upon success
                if self.helper():
                    self.writer()

            def helper(self):
                """Execute event's trigger and return success status."""

                _, status = _bash(self.trigger_string)

                if status == 0:

                    if self.is_default:
                        EVENTLOG.info("Successfully executed default trigger",
                                      extra=self.event.__dict__)
                    else:
                        EVENTLOG.info("Successfully executed configured "
                                      "trigger", extra=self.event.__dict__)
                    return True

                elif not self.is_default:

                    EVENTLOG.error("Failed to execute custom or named trigger",
                                   extra=self.event.__dict__)

                    _, retry = _bash(self.default_string)

                    if retry == 0:
                        EVENTLOG.info("Retry successfully executed default "
                                      "trigger", extra=self.event.__dict__)
                        return True

                    else:
                        EVENTLOG.error("Retry failed to execute default "
                                       "trigger", extra=self.event.__dict__)

                else:

                    EVENTLOG.error("Failed to execute default trigger",
                                   extra=self.event.__dict__)

                return False

            @property
            def is_default(self):
                """Check whether currently trigger is the default."""
                return self.trigger_string == self.default_string

            def writer(self):
                """Update event's config file upon trigger."""

                EVENTLOG.debug("Updating event file STATUS to triggered",
                               extra=self.event.__dict__)

                # ensure STATUS is not already set to triggered
                if self.event.data.get('STATUS') == 'triggered':
                    EVENTLOG.error("Event file STATUS not updated (it was alre"
                                   "ady changed)", extra=self.event.__dict__)
                    return

                # update STATUS to triggered
                try:
                    self.event.data['STATUS'] = 'triggered'
                    self.event.data.write()
                except:  # pylint: disable=W0702
                    EVENTLOG.error("Exception while updating STATUS to "
                                   "triggered", extra=self.event.__dict__)

                # # ensure STATUS was set to triggered
                # try:
                #     assert self.event.data.get('STATUS') == 'triggered'
                #     EVENTLOG.info("Event file STATUS successfully updated to "
                #                   "triggered", extra=self.event.__dict__)
                #     return
                # except AssertionError:
                #     EVENTLOG.error("Event file STATUS unsuccessfully updated "
                #                    "to triggered!", extra=self.event.__dict__)
                #     return

                # ensure STATUS was set to triggered
                if self.event.data.get('STATUS') == 'triggered':
                    EVENTLOG.info("Event file STATUS successfully updated to "
                                  "triggered", extra=self.event.__dict__)
                    return
                else:
                    EVENTLOG.error("Event file STATUS unsuccessfully updated "
                                   "to triggered!", extra=self.event.__dict__)
                    return

            # def writer(self):
            #     """Update event's config file upon trigger."""
            #     EVENTLOG.debug("Executing writer", extra=self.event.__dict__)

            #     try:
            #         with open(self.event.path) as readfile:
            #             original = readfile.read()

            #         edited = re.sub(r'(?<=STATUS)(\ ?)=(\ ?)enabled',
            #                         '\\1=\\2triggered', original)

            #         if edited != original:
            #             with open(self.event.path, 'w') as writefile:
            #                 writefile.write(edited)

            #             with open(self.event.path) as readfile:
            #                 if re.search(r'STATUS(\ ?)=(\ ?)triggered', readfile.read()):
            #                     EVENTLOG.info("Event file STATUS successfully updated to "
            #                                  "triggered", extra=self.event.__dict__)
            #                     return
            #                 else:
            #                     EVENTLOG.error("Event file STATUS unsuccessfully updated "
            #                                   "to triggered!", extra=self.event.__dict__)
            #                     return
            #         else:
            #             EVENTLOG.error("Event file STATUS not updated (it was already "
            #                           "changed)", extra=self.event.__dict__)
            #             return
            #     except:  # pylint: disable=W0702
            #         EVENTLOG.error("Exception while updating STATUS to triggered",
            #                       extra=self.event.__dict__)

        def _contains(self, match, content):
            """content contains match (match in content)."""
            result = match in content
            EVENTLOG.info("CONTENT TEST | '%s' in '%s' => %s", match, content,
                          result, extra=self.__dict__)
            return result

        def _matches(self, match, content):
            """match matches content (match == content)."""
            result = match == content
            EVENTLOG.info("CONTENT TEST | '%s' matches '%s' => %s", match, content,
                          result, extra=self.__dict__)
            return result

        def _notcontains(self, match, content):
            """content does not contain match (match not in content)."""
            result = match not in content
            EVENTLOG.info("CONTENT TEST | '%s' not in '%s' => %s", match, content,
                          result, extra=self.__dict__)
            return result

        def _notmatch(self, match, content):
            """match does not match content (match != content)."""
            result = match != content
            EVENTLOG.info("CONTENT TEST | '%s' does not match '%s' => %s", match,
                          content, result, extra=self.__dict__)
            return result

        def _notnull(self, match, content):  # pylint: disable=W0613
            """content is not null (content != '')."""
            result = content != ''
            EVENTLOG.info("CONTENT TEST | '%s' is not null => '%s'", content,
                          result, extra=self.__dict__)
            return result

        def _null(self, match, content):  # pylint: disable=W0613
            """content is null (content == '')."""
            result = content == ''
            EVENTLOG.info("CONTENT TEST | '%s' is null => '%s'", content,
                          result, extra=self.__dict__)
            return result

        def arithmetic(self, content):
            """Perform an arithmetic evaluation."""
            import operator

            operations = {
                'eq': operator.eq, 'ge': operator.ge, 'gt': operator.gt,
                'le': operator.le, 'lt': operator.lt, 'ne': operator.ne
                }

            criteria = self.data.get('MATCH_CRITERIA')

            try:
                content = int(content)
            except ValueError:
                EVENTLOG.info("'%s' is not an integer (required for arithmetic "
                              "operations)", content, extra=self.__dict__)
                return False

            try:
                match = int(self.data.get('MATCH_CONTENT'))
            except ValueError:
                EVENTLOG.error("MATCH_CONTENT must be an integer for arithmetic "
                               "operations", extra=self.__dict__)
                return False

            result = operations[criteria](content, match)

            test_type = self.data.get('TEST_TYPE').upper()

            EVENTLOG.info("%s TEST | '%s' %s '%s' => %s", test_type, content,
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
            "Execute and evaluate output of COMMAND per TEST_TYPE."""

            output, exit = _bash(self.data.get('COMMAND'))

            test_type = self.data.get('TEST_TYPE')

            if (test_type == 'arithmetic' and self.arithmetic(output)) or \
               (test_type == 'content' and self.content(output)) or \
               (test_type == 'status' and self.arithmetic(exit)):
                return True

        def verify(self):  # pylint: disable=R0912
            """Verify  that an event file is formatted correctly."""
            import re

            problems = 0

            test_types = ['arithmetic', 'content', 'status', None, '']
            arithmetic_criteria = ['eq', 'ge', 'gt', 'le', 'lt', 'ne', None, '']
            content_criteria = ['contains', 'does_not_contain', 'matches',
                                'does_not_match', 'null', 'not_null', None, '']

            required = ['COMMAND', 'EVENT_NAME', 'MATCH_CRITERIA',
                        'STATUS', 'TEST_TYPE']

            missing = [f for f in required if self.data.get(f) is None or self.data.get(f) is '']

            try:
                # ensure MATCH_CONTENT exists (unless MATCH_CRITERIA is null or not_null)
                assert self.data.get('MATCH_CONTENT') is not None or \
                    re.search('^(not_)?null$', self.data.get('MATCH_CRITERIA')) \
                    is not None
            except AssertionError:
                missing.append('MATCH_CONTENT')

            # identify missing mandatory fields
            if missing:
                EVENTLOG.error("Missing %s", ' '.join(missing),
                               extra=self.__dict__)
                problems += 1

            try:
                # ensure TEST_TYPE is a valid test type
                assert self.data.get('TEST_TYPE') in test_types
            except AssertionError:
                EVENTLOG.error("Invalid TEST_TYPE", extra=self.__dict__)
                problems += 1

            # perform verification for arithmetic and status tests
            if self.data.get('TEST_TYPE') in ('arithmetic', 'status'):

                try:
                    # ensure MATCH_CONTENT is an integer
                    assert self.data.get('MATCH_CONTENT') is None or \
                        isinstance(self.data.get('MATCH_CONTENT'), int)
                except AssertionError:
                    elogger.error("MATCH_CONTENT must be an integer for "
                                  "arithmetic operations", extra=self.__dict__)
                    problems += 1

                try:
                    # ensure MATCH_CRITERIA is an arithmetic operation
                    assert self.data.get('MATCH_CRITERIA') in \
                        arithmetic_criteria
                except AssertionError:
                    EVENTLOG.error("Invalid MATCH_CRITERIA for arithmetic "
                                   "operations", extra=self.__dict__)
                    problems += 1

            # perform verification for content tests
            elif self.data.get('TEST_TYPE') == 'content':

                try:
                    # ensure MATCH_CRITERIA is a content operation
                    assert self.data.get('MATCH_CRITERIA') in content_criteria
                except AssertionError:
                    EVENTLOG.error("Invalid MATCH_CRITERIA for content "
                                   "operations", extra=self.__dict__)
                    problems += 1

            # ensure custom and named triggers are not used concurrently
            if self.data.get('TRIGGER_CUSTOM') and self.data.get('TRIGGER_NAMED'):
                EVENTLOG.error("TRIGGER_CUSTOM and TRIGGER_NAMED are both "
                               "indicated (choose one or neither)",
                               extra=self.__dict__)
                problems += 1

            if problems == 1:
                EVENTLOG.warning("Encountered 1 issue verifying event file",
                                 extra=self.__dict__)
            elif problems >= 2:
                EVENTLOG.warning("Encountered %s issues verifying event file",
                                 problems, extra=self.__dict__)

            return problems == 0

    class EventRunner:
        def __init__(self, path, config=None):
            eventfile = EventHandler.EventFile(path, config)

            EVENTLOG.info("Processing event", extra=eventfile.__dict__)

            # ensure event is enabled
            if not eventfile.enabled:

                EVENTLOG.info("Not enabled (skipping)",
                              extra=eventfile.__dict__)
                return

            # ensure event verification is successful
            elif not eventfile.verify():

                EVENTLOG.info("Failed verification (skipping)",
                              extra=eventfile.__dict__)
                return

            if eventfile.test():
                trigger = EventHandler.EventFile.TriggerFile(eventfile)
                trigger.execute()

    class EventVerifier:
        def __init__(self, path, config=None):
            import logging

            eventfile = EventHandler.EventFile(path, config)

            EVENTLOG.info("Verifying only", extra=eventfile.__dict__)

            # store the original log level
            level = EVENTLOG.getEffectiveLevel()

            # ensure verification messages are displayed
            EVENTLOG.setLevel(logging.INFO)

            status = eventfile.verify()

            # initialize trigger (to display configuration warnings)
            EventHandler.EventFile.TriggerFile(eventfile)

            if status:
                EVENTLOG.info("Verification OK", extra=eventfile.__dict__)
            else:
                EVENTLOG.info("Verification NOT OK", extra=eventfile.__dict__)

            # restore original log level
            EVENTLOG.setLevel(level)


def _bash(args):
    """Execute bash command returning output and exit status."""
    import subprocess

    process = subprocess.Popen(args,
                               executable='bash',
                               shell=True,
                               stderr=subprocess.PIPE,
                               stdout=subprocess.PIPE)

    output = process.stdout.read().decode().strip()
    exit = process.wait()

    return output, exit


def _configure():
    """Prepare initial configuration."""
    import logging
    import os
    import sys
    from batchpath import GeneratePaths

    options, arguments = _parser()

    config = options.config
    verify = options.verify

    level = logging.DEBUG if options.debug else logging.INFO if \
        options.verbose else logging.WARNING

    EVENTLOG.setLevel(level)
    LOGGER.setLevel(level)

    events = GeneratePaths().files(arguments,
                                   access=os.W_OK,
                                   extensions=['conf', 'txt'],
                                   minsize=0,
                                   recursion=True)

    LOGGER.info("processing %s events", len(events))
    LOGGER.debug("events = %s", events)
    LOGGER.debug("verify = %s", verify)
    LOGGER.debug("triggerfile = %s", config)
    LOGGER.debug("loglevel = %s", level)

    if not events:
        LOGGER.error("You have not supplied any valid targets")
        LOGGER.error("Try '%s --help' for more information.", __program__)
        sys.exit(1)

    EventHandler(events, config, verify)


def _logging():
    """Initialize program and event LOGGERs."""
    # NOTE: There may be significant room for improvement with the logging
    #       functionality. Is there a way to do it without global?
    import logging

    global EVENTLOG
    EVENTLOG = logging.getLogger('event')
    estream = logging.StreamHandler()
    eformat = logging.Formatter('[%(basename)s] %(levelname)s: %(message)s')
    estream.setFormatter(eformat)
    EVENTLOG.addHandler(estream)

    global LOGGER
    LOGGER = logging.getLogger(__program__)
    tstream = logging.StreamHandler()
    tformat = logging.Formatter('(%(name)s) %(levelname)s: %(message)s')
    tstream.setFormatter(tformat)
    LOGGER.addHandler(tstream)


def _parser():
    """Parse script arguments and options."""
    import argparse
    import os

    config = '{0}/.config/scripts/{1}/triggers.conf' \
             .format(os.environ['HOME'], __program__)

    parser = argparse.ArgumentParser(
        add_help=False,
        description='Trigger an event or notification upon the output '
                    'of a command.',
        usage='%(prog)s [OPTION] <event files|folders>')
    parser.add_argument(
        '-f', '--file',
        default=config,
        dest='config',
        help='indicate a trigger config file to '
             'be used (default: %s)' % config)
    parser.add_argument(
        '--debug',
        action='store_true',
        dest='debug',
        help='set the logging level to debug')
    parser.add_argument(
        '--verbose',
        action='store_true',
        dest='verbose',
        help='set the logging level to verbose')
    parser.add_argument(
        '--verify',
        action='store_true',
        dest='verify',
        help='verify event files without execution')
    parser.add_argument(
        '-h', '--help',
        action='help',
        help=argparse.SUPPRESS)
    parser.add_argument(
        '--version',
        action='version',
        version='{0} {1}'.format(__program__, __version__))
    parser.add_argument(
        action='append',
        dest='targets',
        help=argparse.SUPPRESS,
        nargs='*')

    options = parser.parse_args()
    arguments = options.targets[0]

    return options, arguments


def main():
    """Start application."""
    _logging()
    _configure()


if __name__ == '__main__':
    main()
