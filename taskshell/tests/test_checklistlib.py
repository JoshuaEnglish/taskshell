import unittest
import pathlib
import logging
import warnings

from taskshell import TaskLib

from configparser import ConfigParser, ExtendedInterpolation

tmp_dir = pathlib.Path(__file__).parent / 'tmp'
tmp_dir.mkdir(exist_ok=True)


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
      <_template name="onboarding" version="1.0">
        <header>
          <input idsource="true" key="name" label="Employee Name"/>
        </header>
        <phase id="setup" label="Initial Setup">
          <task id="crmadd" label="Add to CRM">
            <?oncreate add_task (A) Add {instanceid} to CRM +{instanceid}Hire?>
            <?oncomplete unlock crmt?>
            <action>Fill out New Employee Template</action>
            <action>Submit Case</action>
            <input label="Case #"/>
          </task>
          <task id="crmt" label="Add Territories in CRM" status="onhold">
            <?onopen add_task (A) Add {instanceid} Territories in CRM +{instanceid}Hire?>
            <action>Fill out Territory assignment template</action>
            <action>Submit Case</action>
            <input label="Case #"/>
          </task>
        </phase>
      </_template>
    </checklist>
"""

checklist_dir = tmp_dir / 'checklists'

bak_dir = checklist_dir / 'backup'
bak_dir.mkdir(exist_ok=True)

# logging.basicConfig(level=logging.DEBUG)
class ChecklistTestCase(unittest.TestCase):
    def setUp(self):
        with open(checklist_dir / 'onboarding.xml', 'w') as ch:
            ch.write(test_checklist)
        with open(CONFIG['Files']['task-path'], 'w') as fp:
            fp.write('')

        self.task_lib = TaskLib(CONFIG)
        self.check_lib = self.task_lib.libraries['checklist']

    def tearDown(self):
        del self.check_lib
        del self.task_lib

    def test_list_inputs(self):
        self.check_lib.create_instance('onboarding', name='Some Guy')
        inputs = self.check_lib.list_inputs('onboarding', 'SomeGuy', 'crmadd')
        self.assertIsInstance(inputs, list, 
            'list_inputs did not return a list')
        self.assertEqual(len(inputs), 1, 
            'list_inputs returned list with the wrong length')
        self.assertIsInstance(inputs[0], tuple, 
            'list_inputs did not return a tuple')
        self.assertEqual(len(inputs[0]), 3, 
            'list_inputs returned tuples of wrong length')


class ChecklistIntegrationTestCase(unittest.TestCase):
    def setUp(self):
        with open(checklist_dir / 'onboarding.xml', 'w') as ch:
            ch.write(test_checklist)
        with open(CONFIG['Files']['task-path'], 'w') as fp:
            fp.write('')

        self.task_lib = TaskLib(CONFIG)
        self.check_lib = self.task_lib.libraries['checklist']

    def tearDown(self):
        del self.check_lib
        del self.task_lib

    def test_add_task_on_instantiation(self):
        '''Test that creating a checklist instance creates a new task as
        necessary'''
        self.check_lib.create_instance('onboarding', **{'name': 'New Employee'})
        tasks = self.task_lib.sort_tasks(filters="{cid:crmadd}")
        self.assertEqual(len(tasks), 1)
        generated_task = tasks[0][1]
        target_uid = generated_task.extensions.get('uid')
        checklist = self.check_lib.checklists['onboarding']
        instance = checklist.find('./instance[@id="NewEmployee"]')
        ch_task = instance.find('.//task[@id="crmadd"]')
        self.assertEqual(target_uid, ch_task.attrib.get('uid'))
        
    def test_complete_task_to_checklist_warning(self):
        '''Test that completing a task in task_lib raises a warning'''
        # In this example, there are inputs that are not automatically filled in
        self.check_lib.create_instance('onboarding', name='New Employee')
        with self.assertWarns(UserWarning):
            self.task_lib.complete_task(1)
        self.assertFalse(self.check_lib._is_task_complete(
            self.check_lib._get_task('onboarding', 'NewEmployee', 'crmadd')))

    def test_is_task_complete(self):
        '''Test is_task_complete works as expected'''
        self.check_lib.create_instance('onboarding', name='NewEmployee')
        self.assertFalse(self.check_lib._is_task_complete(
            self.check_lib._get_task('onboarding', 'NewEmployee', 'crmadd')))
        self.complete_crm_add()
        self.assertTrue(self.check_lib._is_task_complete(
            self.check_lib._get_task('onboarding', 'NewEmployee', 'crmadd')))

    def test_complete_checklist_to_task(self):
        '''Test completing a task in the checklist marks the task as
        complete'''
        self.check_lib.create_instance('onboarding', name='NewEmployee')
        ch_task = self.check_lib._get_task(
            'onboarding', 'NewEmployee', 'crmadd')
        logging.debug('ch_task uid %s', ch_task.get('uid', 'NOTHING'))
        self.assertFalse(self.check_lib._is_task_complete(ch_task))
        self.complete_crm_add()

        res = self.task_lib.sort_tasks(
                filters=[f"{{uid:{ch_task.get('uid')}}}"],
            showcomplete=True)
        logging.debug('found tasks: %s', res)
        task = res[0][1]
        self.assertTrue(task.complete, "Task was not marked as complete")

    def test_complete_task_unlocks_next_task(self):
        """oncomplete unlocks the next task"""
        self.check_lib.create_instance('onboarding', name="New Employee")
        instance = self.check_lib._get_instance('onboarding', 'NewEmployee')
        crm_add = self.check_lib._get_task('onboarding', 'NewEmployee', 'crmadd')
        crmt = self.check_lib._get_task('onboarding', 'NewEmployee', 'crmt')
        self.assertEqual(crmt.get('status'), 'onhold')
        self.complete_crm_add()

        self.assertEqual(crmt.get('status'), 'open')
        res = self.task_lib.sort_tasks(filters=[f"{{uid:{crmt.get('uid')}}}"])
        task = res[0][1]
        self.assertFalse(task.complete, "task was added as complete")

        
    def complete_crm_add(self):
        """Several tests require a task to be marked as closed, this 
        should do this consistently"""
        self.check_lib.complete_action(
            'onboarding', 'NewEmployee', 'crmadd', 1)
        self.check_lib.complete_action(
            'onboarding', 'NewEmployee', 'crmadd', 2)
        self.check_lib.fill_input(
            'onboarding', 'NewEmployee', 'crmadd', 1, 'some input')

if __name__ == "__main__":
    unittest.main()
