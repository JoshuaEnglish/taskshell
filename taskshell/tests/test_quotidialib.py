import unittest
import unittest.mock as mock
import pathlib
import logging
import datetime

from taskshell import TaskLib
from taskshell.plugins import quotidia

from configparser import ConfigParser, ExtendedInterpolation

tmp_dir = pathlib.Path(__file__).parent / 'tmp'
tmp_dir.mkdir(exist_ok=True)

q_dir = tmp_dir / 'quotidia'
q_dir.mkdir(exist_ok=True)

CONFIG = ConfigParser(interpolation=ExtendedInterpolation())

CONFIG['Files'] = {
    'done-path': '${tasker-dir}/done.txt',
    'task-path': '${tasker-dir}/todo.txt',
    'tasker-dir': str(tmp_dir)
    }


CONFIG['Tasker'] = {
    'wrap-width': '78',
    'show-priority-z': 'true',
    'priority-z-last': 'true',
    'wrap-behavior': 'wrap',
    'hidden-extensions': 'uid,hide',
    'theme-name': 'default',
    'archive-days': 7
    }
    
test_quotidia = (
    ('alex', """{"__quotidium__": true, "qid": "alex", 
    "text": "Pay Alex {qid:alex}", "days": "1", "active": true, 
    "history": []}"""),
    ('monday', """{"__quotidium__": true, "qid": "monday",
    "text": "Monday morning task", "days": "M", "active": true,
    "history": []}"""),
    ('tuesday', """{"__quotidium__": true, "qid": "tuesday",
    "text": "Tuesday afternoon task", "days": "T", "active": false,
    "history": []}"""),
    )


# Mocking datetime.date.today via
# https://stackoverflow.com/a/20155202/2658278
def fixed_today(today):
    from datetime import date

    class FakeDateType(type):
        def __instancecheck__(self, instance):
            return isinstance(instance, date)

    class FakeDate(date, metaclass=FakeDateType):

        def __new__(cls, *args, **kwargs):
            return date.__new__(date, *args, **kwargs)

        @staticmethod
        def today():
            return today

    return mock.patch("datetime.date", FakeDate)


class QuotidiaTestCase(unittest.TestCase):
    def setUp(self):
        for qname, qtext in test_quotidia:
            with open(q_dir / f'{qname}.quotidia', 'w') as qf:
                qf.write(qtext)
        with open(CONFIG['Files']['task-path'], 'w') as fp:
            fp.write('')

    def loadlibs(self):
        # many tests are dependent on faking the date, so creating
        # the libraries needs to be controlled.
        # quotidia runs
        self.task_lib = TaskLib(CONFIG)
        self.q_lib = self.task_lib.libraries['quotidia']


    def tearDown(self):
        del self.q_lib
        del self.task_lib

        logging.getLogger().setLevel(logging.WARNING)

    def test_add_quotidia(self):
        self.loadlibs()
        self.assertRaises(ValueError, self.q_lib.add_quotidia, 
            "monday", "error", "M")

    def test_load_quotidia(self):
        self.loadlibs()
        for (qid, q) in self.q_lib.qids.items():
            self.assertIsInstance(q, quotidia.Quotidium, 
                "json did not load quotidium object")

    def test_get_todays_quotidia_dom(self):
        with fixed_today(datetime.date(2020, 6, 2)):
            self.loadlibs()
            # deactivate the test dow quotidium for this test
            self.q_lib.deactivate_quotidium('monday')
            # mark a dom quotidium as done on a day of the month
            self.q_lib.run_quotidium('alex')
            self.assertEqual(self.q_lib.qids['alex'].last_run,
                datetime.date(2020, 6, 2))
        
        # logging.getLogger().setLevel(logging.DEBUG)

        with fixed_today(datetime.date(2020, 6, 30)):
            self.assertNotIn('alex',
                (a for a, b in self.q_lib.get_todays_quotidia()))
        with fixed_today(datetime.date(2020, 7, 1)):
            self.assertIn('alex',
                [a for a, b in self.q_lib.get_todays_quotidia()])
        
    def test_get_today_quotidia_dow(self):
        # mark a quotidium as run on a Monday
        with fixed_today(datetime.date(2020, 7, 20)):
            self.loadlibs()
            self.q_lib.run_quotidium('monday')
            self.assertEqual(self.q_lib.qids['monday'].last_run, 
                datetime.date(2020, 7, 20))

        with fixed_today(datetime.date(2020, 7, 21)):
            self.assertNotIn('monday', 
                (a for a, b in self.q_lib.get_todays_quotidia()))
         
        with fixed_today(datetime.date(2020, 7, 26)):
            self.assertNotIn('monday', 
                (a for a,b in self.q_lib.get_todays_quotidia()))
         
        with fixed_today(datetime.date(2020, 7, 27)):
            self.assertIn('monday', 
                (a for a,b in self.q_lib.get_todays_quotidia()))
        
        with fixed_today(datetime.date(2020, 7, 28)):
            quotidia = self.q_lib.get_todays_quotidia()
            self.assertIn('monday', 
                (a for a,b in quotidia))
            for (a, b) in quotidia:
                self.q_lib.run_quotidium(a)
            self.assertNotIn('monday',
                (a for a, b in self.q_lib.get_todays_quotidia()))
            

    def test_quotidia_adds_task(self):
        # quotidia should be checked on startup
        self.loadlibs()
        tasks = self.task_lib.sort_tasks(filters=["{qid:alex}"])
        self.assertEqual(len(tasks), 1)
