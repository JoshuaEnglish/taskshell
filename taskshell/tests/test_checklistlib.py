import unittest
import pathlib

from taskshell import TaskLib

from configparser import ConfigParser, ExtendedInterpolation

tmp_dir = pathlib.Path(__file__).parent / 'tmp'
if not tmp_dir.exists():
    tmp_dir.mkdir()

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

test_checklist = """<checklist>
  <_template name="test" version="1.0">
    <header>
      <input idsource="true" key="test" name="testing purposes only"/>
    </header>
    <phase id='first' name="Fit the First">
      <task id='sb' name="First Task">
        <?oncreate add_task (A) Task from checklist {instanceid}?>
        <action>First Action</action>
      </task>
    </phase>
  </_template>
</checklist>"""

checklist_dir = tmp_dir / 'checklists'

class ChecklistTestCase(unittest.TestCase):
    def setUp(self):
        with open(checklist_dir / 'test.xml', 'w') as ch:
            ch.write(test_checklist)
        with open(CONFIG['Files']['task-path'], 'w') as fp:
            fp.write('')

        self.test_lib = TaskLib(CONFIG)
        self.check_lib = self.test_lib.libraries['checklist']

    def tearDown(self):
        del self.check_lib
        del self.test_lib

    def test_add_task_on_instantiation(self):
        '''Test that creating a checklist instance creates a new task as
        necessary'''
        self.check_lib.create_instance('test', **{'test': 'NewTask'})
        tasks = self.test_lib.sort_tasks(filters="{cid:sb}")
        self.assertEqual(len(tasks), 1)
        generated_task = tasks[0][1]
        target_uid = generated_task.extensions.get('uid')
        checklist = self.check_lib.checklists['test']
        instance = checklist.find('./instance[@id="NewTask"]')
        ch_task = instance.find('.//task[@id="sb"]')
        self.assertEqual(target_uid, ch_task.attrib.get('uid'))
        
    def test_complete_task_to_checklist(self):
        '''Test that completing a task in task_lib changes the checklist'''
        self.check_lib.create_instance('test', test='NewTask')
        self.test_lib.complete_task(1)
        self.assertTrue(self.check_lib._is_task_complete(
            self.check_lib._get_task('test', 'NewTask', 'sb')))

    def test_is_task_complete(self):
        '''Test is_task_complete works as expected'''
        self.check_lib.create_instance('test', test='NewTask')
        self.assertFalse(self.check_lib._is_task_complete(
            self.check_lib._get_task('test', 'NewTask', 'sb')))
        self.check_lib.complete_action('test', 'NewTask', 'sb', 1)
        self.assertTrue(self.check_lib._is_task_complete(
            self.check_lib._get_task('test', 'NewTask', 'sb')))

    def test_complete_checklist_to_task(self):
        '''Test completing a task in the checklist marks the task as
        complete'''
        self.check_lib.create_instance('test', test='NewTask')
        self.assertFalse(self.check_lib._is_task_complete(
            self.check_lib._get_task('test', 'NewTask', 'sb')))
        self.check_lib.complete_action('test', 'NewTask', 'sb', 1)

        res = self.test_lib.sort_tasks(filters=['checklist'],
            showcomplete=True)
        task = res[0][1]
        self.assertTrue(task.complete, "Task was not marked as complete")
        

if __name__ == "__main__":
    unittest.main()
