About
=====

triggerd is a sysadmin/automation tool used to trigger an event or notification upon the output of a command.

An event file containing the trigger criteria is created. Ideally, you'll create a cron entry or systemd timer to execute ``triggerd EVENTFOLDER`` at a regular interval. If the command status or output matches the trigger criteria, a trigger event or notification is executed and the event file is marked triggered.

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

*Please note: Event files are parsed manually, they are not 'sourced' by the shell. Contents are executed by the shell exactly as they appear.*

Basic documentation (sample event file and trigger template file) is installed to *$PREFIX/share/triggerd/examples*

Here is a sample event file that triggers when *google.com* is not accessible via ``curl``:

::

  COMMAND=curl -sL google.com
  EVENT_NAME=Google Availability
  MATCH_CONTENT=0
  MATCH_CRITERIA=ne
  STATUS=enabled
  TEST_TYPE=status
  TRIGGER_CUSTOM=notify-send --urgency=critical "$EVENT_NAME" "Google is not available!"

Here is a sample event file that triggers when the *google.com* homepage source code contains the word *surprise*:

::

  COMMAND=curl -sL google.com
  EVENT_NAME=Google Surprise
  MATCH_CONTENT=surprise
  MATCH_CRITERIA=contains
  STATUS=enabled
  TEST_TYPE=content
  TRIGGER_CUSTOM=notify-send --urgency=critical "$EVENT_NAME" "Google contains a surprise!"

Here is a sample event file that triggers when */tmp* is greater than or equal to 10M in size:

::

  COMMAND=du -ms /tmp | cut -f1
  EVENT_NAME=Size Check
  MATCH_CONTENT=10
  MATCH_CRITERIA=ge
  STATUS=enabled
  TEST_TYPE=arithmetic
  TRIGGER_CUSTOM=notify-send --urgency=critical "$EVENT_NAME" "/tmp is >= 10M in size!"

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

The event name can be referenced in either trigger as ``$EVENT_NAME``. The same goes for ``$MATCH_CONTENT``.

If no trigger is indicated, a default notification will be displayed via notify-send.


License
=======

Copyright (c) 2015 Six (brbsix@gmail.com).

Licensed under the GPLv3 license.
