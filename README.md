# Alert time-frame checker

Check whether an alert that was triggered now is:
* Within valid time-frames and should be sent "Now".
* Outside time-frames and should be reschedule to the next valid "date-time".


## Requirements

Python 3.7+


## Files

* alert_timeframe_checker.py -		Main script.
* test_alert_timeframe_checker.py -	Automatic tests for main scripts.
* README.text - 			This file.


## alert_timeframe_checker.py

Script gets a valid-time-frames string as an argument and output (to stdout): "Now" if within valid time-frame,
otherwise a "YYYY-MM-DD HH:mm" format date-time of next valid time.

On error, script will exit with 2 (command line syntax errors) or 1 (all other errors) and print message
to stderr.

This script will log to a file in same directory.

Time zones are ignored - assume all is machine local time-zone.

Usage: ```alert_timeframe_checker.py [-h] [-d] [--no-log] "<time_frames>"```

Mandatory (positional) arguments:
* time_frames    a string of all valid time frames.
  time-frames format: one or more segments of ```"<Day>[-Day]@<time>-<time>"``` separated by ampersand (&).
  Day: a 3-letter weekday (Sun, Mon, etc.), time: a zero-padded 24-hour clock time HH:mm (08:00, 20:08, etc.)
  Examples: ```"Sun@09:00-17:00"```, ```"Sun-Thu@08:00-18:00&Fri@08:00-14:30"```

Optional arguments:
* --debug, -d: Turns debug mode on, printing debug info to log. Implicitly turns verbose mode on.
* --no-log: Turns logging mode off, canceling all writes to log (including verbose and debug).
* --help, -h: Show usage help message and exit.

Example: ```alert_timeframe_checker.py "Sun-Thu@08:00-18:00&Fri@08:00-14:30"```


## test_alert_timeframe_checker.py

Automatic tests for test_alert_timeframe_checker.py script.

Prerequisites:
* The above script is expected to be in same directory as this test file.
* Machine should have python 3.4+ (unittest.mock.patch module).
* Executed from same directory by:
    ```python -m unittest -v test_alert_timeframe_checker.py```
