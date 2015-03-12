About
=====

triggerd is a sysadmin/automation tool used to trigger an event or notification upon the output of a command.

An event file containing the trigger criteria is created. Ideally, you'll create an entry in cron to execute ``triggerd EVENTFOLDER`` at a regular interval. If the command status or output matches the trigger criteria, a trigger event or notification is executed and the event file is marked triggered.

triggerd is perfect for querying a webpage for matching text or anything of the sort. I originally created it for use with a modified version of urlwatch to notify me upon certain changes to webpages, however the potential uses are limitless.

The script was originally written as a Bash shell script before it was rewritten in Python. The Bash version is nearly identical and is a great alternative if Python 3 is not available in your environment. It is included in this repository under ``scripts/triggerd.sh``.


Installation
============

The easiest way to install triggerd is via pip:

::

  pip3 install --user triggerd

FYI: The shell version of triggerd will be installed to your local bin folder as ``triggerd.sh``


Update
=======

Run the following command to update to the most recent version:

::

  pip3 install --upgrade --user triggerd


Usage
===========

triggerd is controlled via configuration files called event files. You can execute it as follows:

::

  triggerd FILE1 FILE2 FILE3...

Or against entire directories of event files:

::

  triggerd EVENTFOLDER1 EVENTFOLDER2...

You can test your event file configuration without actually executing it:

::

  triggerd --verify FILE

The --verbose option can be used to display execution details:

::

  triggerd --verbose FILE


Event Files
===========

FYI: Basic documentation (sample event file and trigger template file) is installed to *$PREFIX/share/triggerd/examples*

Here is a sample event file:

::

  COMMAND=curl -s google.com | grep -q google
  EVENT_NAME=Google
  MATCH_CONTENT=0
  MATCH_CRITERIA=eq
  STATUS=enabled
  TEST_TYPE=status
  TRIGGER_CUSTOM=notify-send "Google is alive!"

**TEST_TYPE** options:

::

  arithmetic
  content
  status    # exit code

**MATCH_CRITERIA** for arithmetic and status tests:

::

  eq
  ge
  gt
  le
  lt
  ne

**MATCH_CRITERIA** for content tests:

::

  contains
  does_not_contain

  matches
  does_not_match

  null
  not_null

**STATUS** indicates whether the event is active:

::

  enabled
  disabled
  triggered    # this will be set by triggerd upon a trigger event


Triggers
========

There are two types of triggers available.

``TRIGGER_CUSTOM`` is used to indicate a shell command.

i.e. ``TRIGGER_CUSTOM=notify-send "Trigger Notification"``

``TRIGGER_NAMED`` is used to indicate the name of a trigger template.

i.e. ``TRIGGER_NAMED=special``

The trigger templates may be defined in ``$HOME/.config/scripts/triggerd/triggers.conf``

ie. ``special=notify-send --icon=~/.config/scripts/triggerd/icons/special.png --urgency=critical "triggerd: $EVENT_NAME" "special event was triggered!"``

The event name can be used in either trigger as ``$EVENT_NAME``.

If no trigger is indicated, a default notification will be displayed via notify-send.


License
=======

Copyright (c) 2015 Six (brbsix@gmail.com).

Licensed under the GPLv3 license.
