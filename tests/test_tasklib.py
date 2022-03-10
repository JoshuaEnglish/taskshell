import unittest
import pathlib

from taskshell import TaskLib

from configparser import ConfigParser, ExtendedInterpolation

tmp_dir = pathlib.Path(__file__).parent / 'tmp'
if not tmp_dir.exists():
    tmp_dir.mkdir()

TEST_CONFIG = ConfigParser(interpolation=ExtendedInterpolation())

TEST_CONFIG['Files'] = {
    'done-path': '${tasker-dir}/done.txt',
    'task-path': '${tasker-dir}/todo.txt',
    'tasker-dir': str(tmp_dir)
    }

TEST_CONFIG['Tasker'] = {
    'wrap-width': '78',
    'show-priority-z': 'true',
    'priority-z-last': 'true',
    'wrap-behavior': 'wrap',
    'hidden-extensions': 'uid,hide',
    'theme-name': 'default',
    'archive-days': 7
    }
    

class TaskLibTestCase(unittest.TestCase):
    def setUp(self):
        self.test_lib = TaskLib(TEST_CONFIG)
        with open(TEST_CONFIG['Files']['task-path'], 'w') as fp:
            fp.write('')

    def tearDown(self):
        del self.test_lib

    def test_add_task_returns_dictionary(self):
        res = self.test_lib.add_task('This is a test task')
        self.assertIsInstance(res, dict)

    def test_do_task_returns_tuple(self):
        self.test_lib.add_task('this is a test task')
        res = self.test_lib.complete_task(1)
        self.assertIsInstance(res, tuple)
        self.assertIsInstance(res[0], int)
        self.assertIsInstance(res[1], dict)
       

if __name__ == '__main__':
    unittest.main()
