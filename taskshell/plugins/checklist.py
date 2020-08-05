"""Tasker Checklist

Plugin for tasker (taskshell, specfically) to manage repeatable checklists
using an XML database.

Checklists of a particular type are in a single file, so there will be a file
for monthlyfinancereview.xml, or newhireprocess.xml, etc.

Checklists can optionally create tasks in the main task list and
respond when those tasks are closed from the main list.


"""
import os
import argparse
import pathlib
import logging
import copy
import datetime
import warnings

from lxml import etree

import minioncmd

from taskshell import lister

#constants for return values
GOOD = 0
BAD = 1
ERROR = -1

__version__ = '0.0.1'

checklistparser = parser = argparse.ArgumentParser('checklist',
    description="Manage checklists in the tasklist")
checklist_command = parser.add_subparsers(title='Checklist Commands',
        dest='subcommand', metavar='')

list_cmd = checklist_command.add_parser(
    'list', help='lists current checklists')
list_cmd.add_argument('name', nargs='?',
        help='if given, lists instances of the checklist')

# these arguments should be standard with any plugins
directory = checklistparser.add_argument('--directory', action="store_true",
    default=False, help='show directory of the checklists and quit')

version = checklistparser.add_argument('--version', action="store_true",
    default=False, help='show version of the checklist plugin and quit')

# Minions are assiged a local variable of .lib that corresponds
# to the libarry of the same name, according to the entry points

class ChecklistCmd(minioncmd.MinionCmd):
    prompt = "checklist>"
    doc_leader = """Checklist Help

    Store complex repetitive tasks witohut cluttering the task list"""

    def __init__(self, completekey='tab',
                 stdin=None, stdout=None,
                 checklib=None):
        super().__init__('checklist',
                         completekey=completekey,
                         stdin=stdin,
                         stdout=stdout)
        self.lib = checklib

    def do_html(self, text):
        """create and open an html report"""
        self.lib.html_report()

    def do_list(self, text):
        '''list instances of a checklist, or checklists if no name given'''
        if text:
            for idx, name in enumerate(
                    self.lib.list_instances(text.strip()), 1):
                print(idx, name)
            if not self.lib.list_instances(text.strip()):
                print(f"No instances of {text.strip()}")
        else:
            for key in self.lib.checklists:
                print(key)

    def do_report(self, text):
        '''print a report of checklists and instances'''
        header = "Checklist Instance Tasks Open Progess".split()
        lister.print_list(
            [(c, i, str(g), str(o), f'{r:02f}%') for c, i, g, o, r in
             self.lib.create_report()],
            header)

    def do_create(self, text):
        '''create a new checklist'''
        if len(text) == 0:
            print("Please provide a checklist name")
            return
        text = text.split()[0]
        self.lib.new_template(text)
        msg = f"Checklist '{text}' created."
        print(msg)

    def do_new(self, text):
        """Create a new instance of a checklist"""
        this = self.lib.checklists[text.strip()]
        if this is None:
            print(f"No checklish for '{text}' found")
            return None
        header = this.find('_template/header')
        data = {}
        idx = None
        for query in header.findall('input'):
            answer = input(f"{query.get('name')}: ")
            if query.get('idsource', 'false') == 'true':
                idx = answer
            data[query.get('key')] = answer
        self.lib.create_instance(text.strip(), **data)
        if idx is None:
            print('Created but probably broken')
        else:
            print('Created checklist for', idx)

    def do_opentasks(self, text):
        '''Usage: opentasks CHECKLIST INSTANCE
        List open tasks (collections of actions) for an instance of a checklist.
        Also notes if the task has separate inputs or an information block.
        '''
        try:
            clist, inst, *junk = text.split(maxsplit=2)
        except ValueError as E:
            self.log.error(E)
            return False
        headers = ['ID', 'Name', 'Inputs', 'Info']
        if clist not in self.lib.checklists:
            print(f"No checklist named {clist}")
            return False
        instance = self.lib._get_instance(clist, inst)
        if instance is None:
            print(f"No instance '{inst}' found")
            return False
        print(clist, inst)
        for gname, nodes in self.lib.get_open_tasks(clist, inst):
            print(gname)
            print('-'*len(gname))
            stuff = [(node.get('id'), node.get('name'),
                     str(node.find('input') is not None),
                     str(node.find('information') is not None))
                     for node in nodes]
            lister.print_list(stuff, headers)

    def do_actions(self, text):
        """Usage: actions CHECKLIST INSTANCE TASKID
        List actions under a particular task
        """
        try:
            clist, inst, taskid, *junk = text.split(maxsplit=3)
        except ValueError as E:
            print(E)
            return False
        task = self.lib._get_task(clist, inst, taskid)
        if task is None:
            print("No task found")
            return False

        lister.print_list(
            [(str(idx), node.text, node.get('completed'),
              node.get('dated', 'false'))
             for idx, node in enumerate(task.findall('action'), 1)],
            "# Action Completed Dated".split())

    def do_getheader(self, text):
        """Usage: getheader CHECKLIST INSTANCE
        Lists the header information.
        """
        try:
            clist, inst, *junk = text.split(maxsplit=2)
        except ValueError as E:
            self.log.error(E)
            return False
        if clist not in self.lib.checklists:
            print(f"No checklist named {clist}")
            return False
        instance = self.lib._get_instance(clist, inst)
        if instance is None:
            print(f'No instance "{inst}" found')
            return False

        header = 'Name Value'.split()
        lister.print_list(
            [(i.get('name'), i.text.strip()) for i in
                instance.findall('header/input')],
            header)

    def do_inputs(self, text):
        """Usage: inputs CHECKLIST INSTANCE TASKID
        Lists inputs related to a task.
        """
        try:
            clist, inst, sgid, *junk = text.split(maxsplit=3)
        except ValueError as E:
            self.log.error(E)
            return False

        header = "# Input Value".split()
        lister.print_list(
            [(str(i), n, str(t)) for i, n, t in
                self.lib.list_inputs(clist, inst, sgid)],
            header)

    def do_getinfo(self, text):
        """Usage: getinfo CHECKLIST INSTANCE TASKID
        List information about a task.
        """
        try:
            clist, inst, taskid, *junk = text.split(maxsplit=3)
        except ValueError as E:
            print(E)
            return False
        task = self.lib._get_task(clist, inst, taskid)
        if task is None:
            print("No task found")
            return False
        if task.find('information') is None:
            print("No information block")
            return False
        for info in task.findall('information'):
            print(info.text)

    def do_fill(self, text):
        """Usage: fill CHECKLIST INSTANCE SUBGROUP NUMBER VALUE"""
        try:
            clist, inst, taskid, num, *value = text.split(maxsplit=4)
        except ValueError as E:
            print(E)
            return False
        res, msg = self.lib.fill_input(
            clist, inst, taskid, int(num), ''.join(value))
        if res:
            print(res, msg)
        else:
            print(msg)

    def do_do(self, text):
        """Usage: do CHECKLIST INSTANCE TASKID NUMBER [DATE]
        Mark a specific action as complete. Will default to today's date
        if date is required but no date given.
        Date should be in ISO format: YYYY-MM-DD
        """
        try:
            clist, inst, taskid, num, *stuff = text.split(maxsplit=4)
        except ValueError as E:
            print(E)
            return False
        if len(stuff) == 0:
            stuff.append(datetime.date.today().isoformat())
        try:
            datetime.date.fromisoformat(stuff[0])
            this_date = stuff[0]
        except (ValueError, TypeError):
            thisdate = datetime.date.today().isoformat()
        res, msg = self.lib.complete_action(clist, inst, taskid, int(num),
            this_date)
        print(res, msg)

class TaskColorizer(etree.XSLTExtension):
    red = "#ff0000"
    green = "#00ff00"
    black = "#333333"
    grey = "#cccccc"

    def execute(self, context, self_node, input_node, output_parent):
        # input node is the node being examined (in this case a task)
        # output parent is the xslt parent (in this case, the td)
        task_node = copy.deepcopy(input_node)
        if self.lib._is_task_complete(task_node):
            output_parent.text = self.green
        else:
            output_parent.text = self.red
        output_parent.extend(list(self_node))

checklist_xslt = etree.XML('''
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:my="testns"
    extension-element-prefixes="my">
<xsl:output method="html" encoding="UTF-8" indent="no"/>
<xsl:template match="checklist">
   <table border="1">
   <thead>
   <tr>
   <th>Key</th>
   <xsl:for-each select="_template/phase">
    <th>
      <xsl:attribute name="colspan">
        <xsl:value-of select='count(task)'/>
      </xsl:attribute>
      <xsl:value-of select="@name"/></th>
   </xsl:for-each>
   </tr>
   <tr><th></th>
   <xsl:for-each select="_template/phase/task">
   <th><xsl:value-of select="@name"/></th>
   </xsl:for-each>
   </tr>
   </thead>
   <tbody>
   <xsl:for-each select="instance">
   <tr>
   <td><xsl:value-of select="@id"/></td>
   <xsl:for-each select="phase/task">
     <td>
       <xsl:attribute name="bgcolor"><my:ext/></xsl:attribute>
     </td>
   </xsl:for-each>
   </tr>
   </xsl:for-each>
   </tbody>
   </table>
</xsl:template>
</xsl:stylesheet>''')


class ChecklistLib(object):
    """Checlist Library
    This does the massive work of checklists. It is imported by the
    main tasklib"""

    __version__ = __version__

    def __init__(self, directory):
        """takes the directory, the top level tasker directory, so plugins
        can add files and subfolders as needed"""
        self.log = logging.getLogger('checklist')
        self.log.info('creating checklistlib')

        self.directory = pathlib.Path(directory) / 'checklists'
        if not self.directory.exists():
            self.log.debug('creating default checklist folder')
            self.directory.mkdir(exist_ok=True)
        self.checklists = {}
        self.paths = {}
        for path in self.directory.glob('*.xml'):
            node = etree.parse(str(path))
            root = node.getroot()
            self.checklists[path.stem] = root
            self.paths[path.stem] = path.resolve()
            node.write(str(self.directory / "backup" / f"{path.stem}.bak"),
                    encoding='utf-8',
                    xml_declaration=True)

    def create_report(self):
        '''return a list of checklists, instances, number of tasks, and
        number of open tasks, and a completion ratio'''
        res = []
        self.log.info('Creating Checklist Report')
        for clist in self.checklists:

            for inst in self.list_instances(clist):
                this = self.checklists[clist].find(f'instance[@id="{inst}"]')
                groupcnt = 0
                opencnt = 0
                for group in this.iterfind('phase/task'):
                    groupcnt += 1
                    if not self._is_task_complete(group):
                        opencnt += 1
                res.append((clist, inst, groupcnt, opencnt,
                    1.0 - float(opencnt)/groupcnt))

        return res

    def list_instances(self, checklistname):
        '''returns a list of IDs for the given checklist'''
        self.log.info('Listing instances of %s', checklistname)
        if checklistname not in self.checklists:
            msg = 'No checklist named %s' % checklistname
            self.log.error(msg)
            return ERROR

        this = self.checklists[checklistname]
        return [i.get('id') for i in this.findall('instance')]

    def new_template(self, name):
        """creates a default empty checklist file"""
        if name in self.checklists:
            msg = f'Checklist for {name} already exists'
            self.log.error(msg)
            return ERROR, msg
        ch = etree.Element('checklist')
        tm = etree.SubElement(ch, '_template', name=name, version="1.0")
        hd = etree.SubElement(tm, 'header')
        etree.SubElement(hd, 'input', idsource='true', key='thing',
                      name='thing')
        gr = etree.SubElement(tm, 'phase', id='firstphase',
                           name='First Phase')
        sg = etree.SubElement(gr, 'task', id='sb', name='First Subphase')
        act = etree.SubElement(sg, 'action', completed='false', dated='false')
        act.text = 'First Action'
        self.checklists[name] = ch
        self.paths[name] = self.directory / f'{name}.xml'
        self._write_checklist(name)
        self.log.info("Created %s checklist" % name)

    def _write_checklist(self, checklistname):
        self.log.info('Writing %s to file', checklistname)
        with open(self.paths[checklistname], 'w') as f:
            f.write(etree.tostring(self.checklists[checklistname]).decode())

    def _get_instance(self, checklistname, instanceid):
        '''return the instance node if it exists'''
        if checklistname not in self.checklists:
            self.log.error('No checklist named %s', checklistname)
            return None
        this = self.checklists[checklistname].find(
            f'instance[@id="{instanceid}"]')
        if this is None:
            self.log.error('No %s checklist instance for %s',
                            checklistname, instanceid)
            return None
        return this


    def _get_task(self, checklistname, instanceid, taskid):
        """return the node for a task. Return None if no
        task is found"""

        this = self._get_instance(checklistname, instanceid)
        if this is None:
            return None

        res = this.find(f'phase/task[@id="{taskid}"]')
        if res is None:
            self.log.error('No task under %s with id %s', instanceid, taskid)
        return res

    def create_instance(self, checklistname, **kwargs):
        """create_instance(checklistname, **kwargs)
        Create a new instace of a checklist
        """
        if checklistname not in self.checklists:
            self.log.error('No checklist named %s', checklistname)
            return BAD, "No checklist named %s" % checklistname
        this = self.checklists[checklistname]
        template = this.find('_template')
        header = template.find('header')
        inputs = header.findall('input')
        emptykeys = [i.get('key') for i in inputs]
        # candidate is the node for the new instance
        candidate = copy.deepcopy(template)
        candidate.tag='instance'
        newheader = candidate.find('header')
        for key, value in kwargs.items():
            if key in emptykeys:
                newheader.find(f'input[@key="{key}"]').text = value
                emptykeys.remove(key)
            else:
                msg = f"Checklist {checklistname} has no header key {key}"
                self.log.error(msg)
                return BAD, msg
        if emptykeys:
            self.log.error('Checklist header missing: %s', emptykeys)
            return BAD, f"Checklist header missing {emptykeys}"
        idnode = newheader.find('input[@idsource="true"]')
        newid = ''.join(idnode.text.split())
        candidate.set('id', ''.join(newid))
        current_ids = [i.get('id') for i in this.findall('instance')]
        if newid in current_ids:
            msg = 'Checklist id%s already exists', newid
            self.log.error(msg)
            return BAD, msg
        for action in candidate.findall(".//action"):
            if 'completed' not in action.attrib:
                action.attrib['completed'] = 'false'
            if 'dated' not in action.attrib:
                action.attrib['dated'] = 'false'

        for task in candidate.findall(".//task"):
            for pi in task.xpath("processing-instruction('oncreate')"):
                command, text = pi.text.split(maxsplit=1)
                added_task = False
                if command == 'add_task':
                    res = self.add_task_to_tasklist(pi)
                    if res is None:
                        self.log.error('Did not successfully add task during oncreate instruction')

        # ready to add the new node to the checklist
        this.append(candidate)
        self._write_checklist(checklistname)
        msg = f"Created {checklistname} instance for {newid}"
        self.log.info(msg)
        return True, msg

    def _is_task_complete(self, node: etree.Element) -> bool:
        """Returns true if all the actions in a node are complete and all
        inputs are filled"""
        completed = True
        for action in node.findall('action'):
            if action.get('completed', 'false') == 'false':
                completed = False
        for inode in node.findall('input'):
            if inode.text is None:
                completed = False
        return completed

    def complete_action(self, checklistname, instance, taskid, number,
                        value=None):
        """complete_action(checklist, instance, taskid, idx [,value])
        Marks a particular action complete.
        If the action is dated, must pass the date of the action.
        """
        value = value or 'true'
        self.log.info('Marking %s:%d complete in %s (%s)',
                       taskid, number, instance, checklistname)
        task = self._get_task(checklistname, instance, taskid)
        if task is None:
            msg = f"No subgroup {taskid} in {instance} of {checklistname}"
            return ERROR, msg
        actions = {}
        for idx, node in enumerate(task.findall('action'), 1):
            actions[idx] = node
        if number not in actions:
            msg = 'No action number {number} in {subgroup}'
            self.log.error(msg)
            return ERROR, msg
        if node.get('dated', False) == 'true':
            try:
                datetime.date.fromisoformat(value)
                actions[number].set('completed', value)
            except ValueError:
                msg = 'Action is dated and must have valid date'
                self.log.error(msg)
                return ERROR, msg
        else:
            actions[number].set('completed', 'true')
        self.complete_task(task)
        self._write_checklist(checklistname)
        return GOOD, 'Marked complete'

    def complete_task(self, task):
        taskdone = self._is_task_complete(task)
        if taskdone:
            # complete the corresponding main task
            if task.attrib.get('uid'):
                tasks = self._tasklib.sort_tasks(
                    filters=[f"uid:{task.attrib.get('uid')}"])
                if len(tasks) == 1:
                    self.log.info(
                        'Checklist task complete, marking linked tast as done')
                    self._tasklib.complete_task(tasks[0][0],
                        'marked as done from checklist')
        # process any oncomplete processing instructions
        for pi in task.xpath('processing-instruction("oncomplete")'):
            command, targets = pi.text.split(maxsplit=1)
            if command == 'unlock':
                for target in targets.split():
                    self.unlock_task(
                        self._get_task(
                            task.getparent().getparent().get('name'),
                            task.getparent().getparent().get('id'),
                            target.strip()))

    def unlock_task(self, task):
        task.set('status', 'open')
        for pi in task.xpath('processing-instruction("onopen")'):
            command, text = pi.text.split(maxsplit=1)
            if command == 'add_task':
                res = self.add_task_to_tasklist(pi)
                if res is None:
                    self.log.error(
                        'Did not successfully create main task during unlock instruction')

    def add_task_to_tasklist(self, pi):
        """if the processing instruction is either oncreate or onopen,
        add a task to the task lib and return the uid of the new task.
        Returns None if it can't be added."""
        command, text = pi.text.split(maxsplit=1)
        if pi.target not in ['oncreate', 'onopen']:
            warnings.warn(
                'should only add main task in oncreate or onopen instructions')
            return None
        task = pi.getparent()
        phase = task.getparent()
        instance = phase.getparent()
        stuff = {'instanceid': instance.get('id')}
        for node in instance.findall('header/input'):
            stuff[node.get('key')] = node.text

        text = text.format(**stuff)

        if task.get('uid') is not None:
            warnings.warn('associated task already has a linked uid')
            return None

        cntag = f"{{cn:{instance.get('name')}}}"
        cidtag = f"{{cid:{instance.get('id')}}}"
        steptag = f"{{cstep:{task.get('id')}}}"

        # check if a task already exists?
        # probably don't need to worry about it, because I check if there's
        # a link via uid already
        for tag in [cntag, cidtag, steptag]:
            if tag not in text:
                text = text + " " + tag
        rdict = self._tasklib.add_task(text)
        newtask = next(iter(rdict.values()))
        task.set('uid', str(newtask.extensions['uid']))
        return newtask.extensions['uid']

    def list_inputs(self, checklistname, instance, task):
        task = self._get_task(checklistname, instance, task)
        if task is None:
            return none
        res = []
        for idx, node in enumerate(task.findall('input'), 1):
            res.append((idx, node.get('name'), node.text))
        return res

    def fill_input(self, checklistname, instance, task, number, value):
        """Fills inputs on a checklist task.
        Returns (Code, message) tuple.
        """
        self.log.info(f"Filling {value} into {task} for {instance}")
        tasknode = self._get_task(checklistname, instance, task)
        if task is None:
            msg = f"No task {task} in {instance} of {checklistname}"
            self.log.error(msg)
            return ERROR, msg
        inputs = {}
        for idx, node in enumerate(tasknode.findall('input'), 1):
            inputs[idx] = node
        if number not in inputs:
            msg = f"No input numebr {number} in {task}"
            self.log.error(msg)
            return ERROR, msg
        inputs[number].text = value
        self.complete_task(tasknode)
        self._write_checklist(checklistname)
        return GOOD, 'Input recorded'

    def get_open_tasks(self, checklistname, checklistid):
        """get_open_tasks(checklistname, checklistid)
        Returns a list of (NAME, NODELIST) tuples, where NAME is the
        ID of the task, and NODELIST is a list of task nodes
        """
        self.log.info('Listing open tasks for %s', checklistid)
        if checklistname not in self.checklists:
            self.log.error('No checklist name %s', checklistname)
            return None
        this = self.checklists[checklistname].find(
            f'instance[@id="{checklistid}"]')
        if this is None:
            self.log.error('No %s checklist instance for %s',
                checklistnaem, checklistid)
            return False
        groups = [(g.get('name'), g) for g in this.iterfind('phase')]
        res = []
        for gname, gnode in groups:
            opentasks = [sg for sg in gnode.iterfind('task')
                        if not self._is_task_complete(sg)]
            if opentasks:
                res.append((gname, opentasks))

        return res

    def html_report(self):
        """Create and open an HTML report of the current checklists"""
        colorizer = TaskColorizer()
        colorizer.lib = self
        extensions = { ('testns', 'ext'): colorizer }
        transform = etree.XSLT(checklist_xslt, extensions=extensions)
        report_name = self.directory / 'report.html'
        with open(report_name, 'wb') as fp:
            fp.write(b'<html><body>')
            for checklist in self.checklists:
                fp.write(bytes(f'<h1>{checklist}</h1>', 'utf-8'))
                fp.write(etree.tostring(transform(self.checklists[checklist])))
            fp.write(b'</body></html>')
        os.startfile(report_name)

    def on_complete_task(self, task):
        """check if the task is linked to a checklist task, and
        mark that action as complete if necessary"""
        self.log.debug('checklib.on_complete_task with %s', task)
        uid = task.extensions['uid']
        local_tasks = None

        for checklist in self.checklists:
            local_tasks = self.checklists[checklist].findall(
                f'.//task[@uid="{uid}"]')
            if len(local_tasks) == 0:
                continue
            # at this point we've found at least one task, but should only be one
            for local_task in local_tasks:
                logging.debug('oct: %s', local_task.attrib)
                for action in local_task.findall('action'):
                    if action.get('dated', False) == 'true':
                        action.set('completed', datetime.date.today().isoformat())
                    else:
                        action.set('completed', 'by task')
                
                # If the task has a final comment, and an input has a
                # commenttarget attribute, fill the input text with the comment
                __, ___, final_comment = task.text.partition("#")
                the_input = local_task.findall('input[@commenttarget]')
                for inp in the_input:
                    if inp.get('commenttarget').lower() == 'true':
                        inp.text = final_comment.strip()

                # warn the user if there are unfilled inputs
                inputs_okay = True
                for inode in local_task.findall('input'):
                    if inode.text is None:
                        inputs_okay = False
                if not inputs_okay:
                    warnings.warn(
                        'Completed task has inputs that need to be filled in')
            self._write_checklist(checklist)

        ### sample code on adding a new task in response to closing a task
        # self._tasklib.queue.append((
        #         'add_task',
        #         {'text': '(C) Sample addition from checklist plugin'}))
        return task

