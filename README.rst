triggerd is a Python script that is used to trigger an event or notification upon the output of a command

An 'event file' containing the trigger criteria is created. Ideally, you'll create an entry in cron to execute `triggerd EVENTFILE` on a regular basis. If the command status or output matches the trigger criteria, a trigger even or notification is executed and the event file is marked triggered.

triggerd is perfect for querying a webpage for matching text or anything of the sort. I originally created it for use with a modified version of urlwatch to notify me upon certain changes, however the potential uses are limitless.

The script was originally written in Bash shell script which is included in this repository if a Python environment is not available.

Here is a sample event file:

    COMMAND=curl -s google.com | grep -q google
    EVENT_NAME=Google
    MATCH_CONTENT=0
    MATCH_CRITERIA=eq
    STATUS=enabled
    TEST_TYPE=status
    TRIGGER_CUSTOM=notify-send "Google is alive!"

TEST_TYPES options:
arithmetic
content
status (exit code)

MATCH_CRITERIA for arithmetic and status tests:
eq
ge
gt
le
lt
ne

MATCH_CRITERIA for content tests:
contains
does_not_contain
does_not_match
matches

STATUS:
enabled
disabled
triggered (this will be set by triggerd upon a trigger event)

Trigger may be specified via TRIGGER_CUSTOM for the exact shell command to execute.

Trigger may also be specified via TRIGGER_NAMED for the name of a trigger template.
i.e. `TRIGGER_NAMED=special`

The trigger templates may be defined in `$HOME/.config/scripts/triggerd/triggers.conf`
ie. `special=notify-send --icon=$HOME/.config/scripts/triggerd/icons/special.png --urgency=critical "triggerd: $EVENT_NAME" "special event was triggered!"`
