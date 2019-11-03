"""
Automatic tests for test_alert_timeframe_checker.py script.
Prerequisites:
* The above script is expected to be in same directory as this test file.
* Machine should have python 3 and unittest module.
* Executed from same directory by:
    python -m unittest -v test_alert_timeframe_checker.py
"""
import unittest
from unittest.mock import patch
from io import StringIO
import sys
import datetime

from alert_timeframe_checker import WEEK_DAYS
from alert_timeframe_checker import valid_time_frames_string
from alert_timeframe_checker import parse_time_frames
from alert_timeframe_checker import within_time_frames
from alert_timeframe_checker import next_valid_date_time
from alert_timeframe_checker import main as atc_main


class TestAlertTimeFrameChecker(unittest.TestCase):
    # Prepare datetime.time objects for reuse
    test_time = {
        '07:07': datetime.time.fromisoformat('07:07'),
        '09:00': datetime.time.fromisoformat('09:00'),
        '10:00': datetime.time.fromisoformat('10:00'),
        '15:00': datetime.time.fromisoformat('15:00'),
        '17:17': datetime.time.fromisoformat('17:17'),
        '18:00': datetime.time.fromisoformat('18:00'),
        '19:00': datetime.time.fromisoformat('19:00'),
        '19:30': datetime.time.fromisoformat('19:30'),
        '23:45': datetime.time.fromisoformat('23:45'),
    }
    # Prepare test cases - raw input string and expected parsed result of time-frames dict.
    test_cases = (
        # [0] Single day; single time-frame.
        ("Sun@09:00-18:00", {
            0: [(test_time['09:00'], test_time['18:00'])]
        }),
        # [1] 2 segments; Day range & single day (single time-frame each).
        ("Sun-Thu@09:00-18:00&Fri@10:00-15:00", {
            0: [(test_time['09:00'], test_time['18:00'])],
            1: [(test_time['09:00'], test_time['18:00'])],
            2: [(test_time['09:00'], test_time['18:00'])],
            3: [(test_time['09:00'], test_time['18:00'])],
            4: [(test_time['09:00'], test_time['18:00'])],
            5: [(test_time['10:00'], test_time['15:00'])],
        }),
        # [2] Revers day range; single time-frame.
        ("Fri-Sun@10:00-18:00", {
            0: [(test_time['10:00'], test_time['18:00'])],
            5: [(test_time['10:00'], test_time['18:00'])],
            6: [(test_time['10:00'], test_time['18:00'])],
        }),
        # [3] 3 segments; Day range & single day; Mon with 2 time-frames.
        ("Sun-Mon@09:00-15:00&Mon@18:00-19:30&Tue-Thu@09:00-19:30", {
            0: [(test_time['09:00'], test_time['15:00'])],
            1: [(test_time['09:00'], test_time['15:00']), (test_time['18:00'], test_time['19:30'])],
            2: [(test_time['09:00'], test_time['19:30'])],
            3: [(test_time['09:00'], test_time['19:30'])],
            4: [(test_time['09:00'], test_time['19:30'])],
        }),
    )

    def test01_valid_time_frames_string(self):
        """Testing the RegEx validation function for time-frames string"""
        with self.subTest('Valid time-frames strings'):
            for day in WEEK_DAYS:
                self.assertTrue(valid_time_frames_string(f'{day}@09:00-18:00'), f'Single segment, single day - {day}')
            for h in range(24):
                self.assertTrue(valid_time_frames_string(f'Sun@{h:02}:00-23:59'), f'Single segment hours "{h:02}:00"')
            for m in range(60):
                self.assertTrue(valid_time_frames_string(f'Sun@10:00-23:{m:02}'), f'Single segment minutes "23:{m:02}"')
            self.assertTrue(valid_time_frames_string('Sun-Wed@09:00-18:00'), 'Single segment, day range')
            self.assertTrue(valid_time_frames_string('Wed-Sun@09:00-18:00'), 'Single segment, reverse day range')
            self.assertTrue(valid_time_frames_string('Sun-Thu@09:00-18:00&Fri@10:00-15:00'), '2 segments (the example)')
            self.assertTrue(valid_time_frames_string('Sun@09:00-18:00&Mon@11:11-22:22&Tue@03:33-04:44'), '3 segments')
            self.assertTrue(valid_time_frames_string(
                'Sun-Thu@08:00-14:00&Mon@16:00-18:30&Wed@16:00-18:30&Fri-Sat@03:15-05:45'),
                '4 segments with mixed day range'
            )

        with self.subTest('Invalid time-frames strings'):
            for day in ('Bla', 'Sunday', 'Mond', 'sun'):
                self.assertFalse(valid_time_frames_string(f'{day}@09:00-18:00'), f'Invalid (single) day: {day}')
                self.assertFalse(valid_time_frames_string(f'Sun-{day}@09:00-18:00'), f'Invalid day range: Sun-{day}')
            self.assertFalse(valid_time_frames_string('Sun@09:00'), 'Invalid time format (single time)')
            for t in ('09:0', '9:00', '24:00', '10:61'):
                self.assertFalse(valid_time_frames_string(f'Sun@{t}-18:00'), f'Invalid time format: {t}-18:00')
                self.assertFalse(valid_time_frames_string(f'Sun@08:00-{t}'), f'Invalid time format: 08:00-{t}')
            self.assertFalse(valid_time_frames_string('Sun@09:00-18:00Mon@11:11-22:22'), '2 segments without separator')

    def test02_parse_time_frames(self):
        """Test parsing of time-frames strings

        Relies on this class test_cases dict (4 cases).
        """
        for case in self.test_cases:
            input_string, expected_res = case
            self.assertDictEqual(expected_res, parse_time_frames(input_string), f'Validating "{input_string}"')

    def test03_within_time_frames(self):
        """Testing the check for "now" within time-frames

        Relies on this class test_cases and test_time dicts.
        """
        # [0] expected result, [1] time-frames, [2] "now" day-of-week, [3] "now" time, [4] Description.
        wtf_cases = (
            # simple single day single time-frame
            (False, self.test_cases[0][1], 0, self.test_time['07:07'], 'Before time-frame'),
            (True, self.test_cases[0][1], 0, self.test_time['15:00'], 'Within simple single time-frame'),
            (False, self.test_cases[0][1], 0, self.test_time['23:45'], 'After time-frame'),
            (False, self.test_cases[0][1], 1, self.test_time['15:00'], 'Day with no time-frame'),

            # Complex multi-day frames with 2 time-frames in single day (on Mon).
            (False, self.test_cases[3][1], 1, self.test_time['07:07'], 'Before 2 time-frames in day'),
            (True, self.test_cases[3][1], 1, self.test_time['10:00'], 'Within 1st time-frame in day'),
            (False, self.test_cases[3][1], 1, self.test_time['17:17'], 'Between 2 time-frames in a day'),
            (True, self.test_cases[3][1], 1, self.test_time['19:00'], 'Within 2nd time-frame in day'),
            (False, self.test_cases[3][1], 1, self.test_time['23:45'], 'After 2 time-frames in day'),
        )

        for case in wtf_cases:
            self.assertEqual(case[0], within_time_frames(case[1], case[2], case[3]), case[4])

    def test04_next_valid_date_time(self):
        """Testing retrieval of next possible date-time for times outside time-frames

        Relies on this class test_cases and test_time dicts.
        """
        nvdt_cases = (
            # [0] Desc; [1] expected; [2] time-frames index; [3] "now" weekday; [4] "now" time; [5] "now" date-time.
            ('Next is tomorrow morning', '2019-11-03 09:00', 0, 6, '17:17', datetime.datetime(2019, 11, 2, 17, 17)),
            ('Next is later that day', '2019-11-05 09:00', 1, 2, '07:07', datetime.datetime(2019, 11, 5, 7, 7)),
            ('Next is earlier same weekday (only)', '2019-11-10 09:00', 0, 0, '23:45', datetime.datetime(2019, 11, 3, 23, 45)),
            ('Between 2 time-frame day', '2019-11-04 18:00', 3, 1, '17:17', datetime.datetime(2019, 11, 4, 17, 17)),
            ('Next month', '2019-11-03 09:00', 3, 4, '23:45', datetime.datetime(2019, 10, 31, 23, 45)),
        )
        for case in nvdt_cases:
            self.assertEqual(
                case[1],
                next_valid_date_time(self.test_cases[case[2]][1], case[3], self.test_time[case[4]], case[5]),
                case[0]
            )

    def test05_end_to_end(self):
        """Simulate the whole script by calling its main function mocking argv and stdout

        If executed at midnight, there's a slim chance for failure (starting test in one day and finishing at the next).
        """
        test_now = datetime.datetime.now()
        cur_day_of_week = test_now.isoweekday()
        if cur_day_of_week == 7:  # Normalize Sunday
            cur_day_of_week = 0

        # Within time-frames test
        time_frames_string = WEEK_DAYS[cur_day_of_week] + '@00:00-23:59'
        with patch('sys.stdout', new=StringIO()) as fake_stdout:
            with patch.object(sys, 'argv', ['--no-log', time_frames_string]):
                atc_main()
            self.assertEqual(fake_stdout.getvalue(), 'Now', 'Within time-frames')

        # Outside time-frames test
        next_day_of_week = cur_day_of_week + 1 if cur_day_of_week < 6 else 0
        time_frames_string = WEEK_DAYS[next_day_of_week] + '@10:00-20:20'
        next_date_time = datetime.datetime.combine(test_now + datetime.timedelta(days=1), self.test_time['10:00'])
        expected_output = next_date_time.isoformat(sep=' ', timespec='minutes')
        with patch('sys.stdout', new=StringIO()) as fake_stdout:
            with patch.object(sys, 'argv', ['--no-log', time_frames_string]):
                atc_main()
            self.assertEqual(fake_stdout.getvalue(), expected_output, 'Reschedule to next morning')


if __name__ == '__main__':
    unittest.main()
