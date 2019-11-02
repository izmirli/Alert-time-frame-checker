"""
Check whether an alert that was triggered now is:
* within valid time-frames and should be sent "Now".
* outside time-frames and should be reschedule to the next valid "date-time".

Script gets a valid-time-frames string as an argument and output (to stdout): "Now" if within valid time-frame,
otherwise a "YYYY-MM-DD HH:mm" format date-time of next valid time.
On error, script will exit with 2 (command line syntax errors) or 1 (all other errors) and print message
to stderr.

This script will log to a file in same directory.
Time zones are ignored - assume all is machine local time-zone.

Usage: alert_timeframe_checker.py [-h] [-d] [--no-log] "<time_frames>"

Mandatory (positional) arguments:
  time_frames    a string of all valid time frames.
            time-frames format: one or more segments of "<Day>[-Day]@<time>-<time>" separated by ampersand (&).
            Day: a 3-letter weekday (Sun, Mon, etc.), time: a zero-padded 24-hour clock time HH:mm (08:00, 20:08, etc.)
            Examples: "Sun@09:00-17:00", "Sun-Thu@08:00-18:00&Fri@08:00-14:30"

Optional arguments:
  --debug, -d       Turns debug mode on, printing debug info to log. Implicitly turns verbose mode on.
  --no-log          Turns logging mode off, canceling all writes to log (including verbose and debug).
  --help, -h        Show usage help message and exit.

Example: alert_timeframe_checker.py "Sun-Thu@08:00-18:00&Fri@08:00-14:30"
"""
import argparse
import re
import datetime
import sys
import logging
from collections import defaultdict

WEEK_DAYS = ('Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat')
LOG_FILE = 'alert_timeframe_checker.log'
_logger: logging.Logger = None


def main():
    """Main script function - top level algorithm.

    1. Get user given script arguments.
    2. Setup logging and debug modes according to user arguments.
    3. Validate given time-frames string.
    4. Parse time-frames string into a traversable structure.
    5. Get current day of the week and time.
    6. Check if within given time-frames. If so, output "Now".
    7. Else, get next valid date-time and output it.

    :return: None
    """
    global _logger
    args = get_args()

    if args['logging']:
        _logger = setup_logger(LOG_FILE)
        if args['debug']:
            _logger.setLevel(logging.DEBUG)
            _logger.debug(f'- - - - - START - - - - - {args}')
        else:
            _logger.setLevel(logging.INFO)

    time_frames_match = valid_time_frames_string(args['time_frames'])
    if not time_frames_match:
        if _logger and args['debug']:
            _logger.fatal(f'Invalid working time-frames argument: "{args["time_frames"]}"')
        sys.exit(
            'Invalid working time-frames argument.\n'
            'time-frames format: one or more segments of "<Day>[-Day]@<time>-<time>" separated by ampersand (&).\n'
            'Day: a 3-letter weekday (Sun, Mon, etc.), time: a zero-padded 24-hour time HH:mm (08:00, 20:08, etc.)\n'
            'Examples: "Sun@09:00-17:00", "Sun-Thu@08:00-18:00&Fri@08:00-14:30"'
        )
    elif _logger:
        _logger.debug('Valid time-frames string. groups: ' + str(time_frames_match.groups()))

    working_time_frames = parse_time_frames(args['time_frames'])
    if _logger:
        _logger.debug(working_time_frames)

    now = datetime.datetime.now()
    cur_time = now.time()
    cur_day_of_week = now.isoweekday()
    if cur_day_of_week == 7:  # Normalize Sunday
        cur_day_of_week = 0
    if _logger:
        _logger.debug(f'now: {now}, cur_day_of_week: {cur_day_of_week}, cur_time: {cur_time}')

    if within_time_frames(working_time_frames, cur_day_of_week, cur_time):
        output = 'Now'
        if _logger:
            _logger.info(f'Alert should be sent now (TF: {args["time_frames"]})')
    else:
        output = next_valid_date_time(working_time_frames, cur_day_of_week, cur_time, now)
        if _logger:
            _logger.info(f'Reschedule alert to: "{output}"')

    print(output, end='')


def get_args():
    """Parse and return script arguments

    Check sys.argv for expected mandatory and optional arguments, and if all is well, assign them as attributes.
    Return arguments as a populated dict (including default values for optional arguments).
    Note! if mandatory arguments are missing/invalid, a sys.exit is called implicitly.

    :return: dict with arguments
    """
    parser = argparse.ArgumentParser(description='Check if now is withing working time-frame, '
                                                 'or return next available working date-time.')
    parser.add_argument('time_frames', help='Time-frames string.')
    parser.add_argument('-d', '--debug', action='store_true', help='Debug mode: on.')
    parser.add_argument('--no-log', action='store_false', dest='logging', help='Logging mode: off.')
    args = parser.parse_args()
    return vars(args)


def setup_logger(log_file, log_name='ATC'):
    """Config and return logger

    Format example:
    2019-11-02 11:24:24,453 [ATC::INFO] Message.

    :param log_file: string of log file path.
    :param log_name: string of logger name. Default is 'ATC'.
    :return: logging.Logger object
    """
    logging.basicConfig(filename=log_file, format='%(asctime)s [%(name)s::%(levelname)s] %(message)s')
    return logging.getLogger(log_name)


def valid_time_frames_string(time_frames_str):
    """Test if given time-frames string is valid format.

    Example of valid time-frames string: "Sun-Thu@09:00-18:00&Fri@10:00-15:00"
    Note! Same-day range (e.g. Sun-Sun) is considered valid.

    :param time_frames_str: a string of the given time-frames argument.
    :return: a re.Match object that evaluates to True if valid, None otherwise.
    """
    time_pattern = r'(?:[01]\d|2[0-3]):[0-5]\d'
    one_of_all_days = '(?:' + '|'.join(WEEK_DAYS) + ')'
    days_optional_range = f'{one_of_all_days}(?:-{one_of_all_days})?'
    time_frame_segment = f'({days_optional_range}@{time_pattern}-{time_pattern})'  # with group capturing
    valid_time_frames_pattern = f'^{time_frame_segment}(?:&{time_frame_segment})*$'
    if _logger:
        _logger.debug(f'valid_time_frames_pattern: {valid_time_frames_pattern}')
    return re.search(valid_time_frames_pattern, time_frames_str)


def parse_time_frames(raw_time_frames):
    """Parse the raw time-frames string given by user, and return traversable structure.

    :param raw_time_frames: string of given time-frames.
    :return: A dict with weekday index as keys, values are lists of tuples holding start and end times.
    {int: [(datetime.time, datetime.time), ...], ...}
    """
    time_frames = defaultdict(list)

    for segment in raw_time_frames.split('&'):
        days, times = segment.split('@')
        days_range = days.split('-')
        times_range = times.split('-')
        start_day, end_day = WEEK_DAYS.index(days_range[0]), WEEK_DAYS.index(days_range[-1])
        start_time, end_time = datetime.time.fromisoformat(times_range[0]), datetime.time.fromisoformat(times_range[-1])
        if _logger:
            _logger.debug(f'segment: {segment}, days: {days} ({start_day}, {end_day}), '
                          f'times: {times} ({start_time}, {end_time})')

        day_index = start_day
        while (start_day <= end_day and start_day <= day_index <= end_day) or \
                (start_day > end_day and (start_day <= day_index or day_index <= end_day)):
            time_frames[day_index].append((start_time, end_time))
            day_index = day_index + 1 if day_index < 6 else 0

    return dict(time_frames)


def within_time_frames(all_time_frames, day_of_week, the_time):
    """Check if "now" is within the given time-frames

    :param all_time_frames: dict of all time-frames.
    :param day_of_week: int index for "now" weekday.
    :param the_time: datetime.time for "now" time.
    :return: True if "now" is within the given time-frames. False otherwise.
    """
    if day_of_week not in all_time_frames:
        return False

    for time_frame in all_time_frames[day_of_week]:
        if time_frame[0] <= the_time <= time_frame[1]:
            return True

    return False


def next_valid_date_time(all_time_frames, cur_day_of_week, cur_time, now_datetime):
    """Find and return closest date-time valid for sending alert

    Assuming current day-of-week and time isn't within any of all_time_frames.

    :param all_time_frames: all valid time-frames. A dict with weekday index as keys, values are lists of tuples
                            holding start and end times. {int: [(datetime.time, datetime.time), ...], ...}
    :param cur_day_of_week: 0-6 int of current weekday index.
    :param cur_time: datetime.time object of current time.
    :param now_datetime: datetime.datetime object of current date-time.
    :return: string in format "YYYY-MM-DD HH:mm" for next valid date-time.
    """
    for next_days in range(8):  # traverse up to 7 days (returning to same week-day).
        day_index = cur_day_of_week + next_days
        if day_index > 6:  # normalize day index.
            day_index -= 7

        if day_index not in all_time_frames:
            continue

        for time_frame in all_time_frames[day_index]:
            if 0 == next_days and time_frame[1] < cur_time:  # skip if "now" day, but not if its next week.
                continue

            next_date_time = datetime.datetime.combine(
                now_datetime.date() + datetime.timedelta(days=next_days),
                time_frame[0]
            )
            return next_date_time.isoformat(sep=' ', timespec='minutes')

    # not expected to get here, but if it does, this is a fatal error.
    if _logger:
        _logger.fatal('Failed to find any valid time for alert sending.')
    sys.exit('Failed to find any valid time for alert sending.')


if __name__ == '__main__':
    main()
