# -*- coding: utf-8 -*-
"""
Tasker

Extensible task-based todo-list manager based on Gina Trapani's todo.txt
format.
Extensions can be installed using entry points.
"""

import os
import sys
import re
import datetime
import logging
import textwrap
import pkg_resources
import time

from operator import itemgetter, attrgetter
from collections import defaultdict, Counter
from functools import partial
from configparser import ConfigParser, ExtendedInterpolation

__version__ = "2.0.dev"
__updated__ = "2020-07-01"
__history__ = """

"""

DEFAULT_CONFIG = ConfigParser(interpolation=ExtendedInterpolation())

if hasattr(sys, "frozen"):
    INSTALL_DIR = os.path.dirname(sys.executable)
else:
    INSTALL_DIR = os.path.dirname(__file__)

sys.path.insert(0, os.path.abspath(INSTALL_DIR))

CONFIGPATH = os.path.join(INSTALL_DIR, 'tasker.ini')

DEFAULT_CONFIG.read([
    os.path.join(INSTALL_DIR, 'defaults.ini'),
    CONFIGPATH])


def save_config():
    """Save configuation to the local file"""
    with open(CONFIGPATH, 'w') as fp:
        DEFAULT_CONFIG.write(fp)


TIMEFMT = '%Y-%m-%dT%H:%M:%S'
# IDFMT = '%H%M%S%f%d%m%y'
IDFMT = '%y%m%d%H%M%S%f'
DATEFMT = '%Y-%m-%d'


def make_uid(dt=None):
    """utility for creating UIDs"""
    if dt:
        return dt.strftime(IDFMT)
    else:
        time.sleep(0.001)
        return datetime.datetime.now().strftime(IDFMT)


re_task = re.compile(
    r"(?P<complete>x\s)?"
    r"(?P<priority>[(][A-Z][)]\s)?"
    r"(?P<start>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\s)?"
    r"(?P<end>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\s)?"
    r"(?P<text>.*)"
)

re_context = re.compile(r"\s([@][-\w]+)")
re_project = re.compile(r"\s([+][-\w]+)")

re_ext = re.compile(r"\s{\w+:[^}]*}")
re_uid = re.compile(r"\s{uid:[^}]*}")
re_hide = re.compile(r"\s{hide:(\d{4}-\d{2}-\d{2})}")
re_note = re.compile(r'\s#\s.*$')

re_pri_filter = re.compile(r"~?\(([A-Z])\)")

TASK_OK = 0
TASK_ERROR = 1
TASK_EXTENSION_ERROR = 2


class Task(object):
    """Simple container for parsed tasks"""

    __slots__ = ('complete', 'priority', 'start', 'end', 'text',
                 'contexts', 'projects', 'extensions')

    def __init__(self, complete, priority, start, end, text,
                 contexts, projects, extensions):
        self.complete = complete
        self.priority = priority
        self.start = start
        self.end = end
        self.text = text
        self.contexts = contexts
        self.projects = projects
        self.extensions = extensions

    def __str__(self):
        res = []
        if self.complete:
            res.append('x')
        if self.priority and not self.complete:
            res.append('(%s)' % self.priority)
        if self.start:
            res.append(self.start.strftime(TIMEFMT))
        if self.end:
            res.append(self.end.strftime(TIMEFMT))
        res.append(self.text.strip())
        return " ".join(res)

    # __contains__ allows for filtering tasks by content
    def __contains__(self, searchtext):
        return searchtext.lower() in self.text.lower()

    # __lt__ is required for sorting tasks
    def __lt__(self, other):
        return str(self) < str(other)

    @classmethod
    def from_text(cls, text):
        """from_text(text)
        Returns a parsed task from a line of text.
        If text starts with *x* and no end time is given, current time
        will be used as end time.
        """
        text = text.strip()
        match = re_task.match(text)
        if not any(match.groups()):
            raise ValueError('Task did not parse')
        complete = bool(match.group('complete'))

        if match.group('priority'):
            priority = match.group('priority')[1]
        else:
            priority = ''

        if match.group('start'):
            start = datetime.datetime.strptime(match.group('start').strip(),
                                               TIMEFMT)
        else:
            start = datetime.datetime.now()

        if match.group('end'):
            end = datetime.datetime.strptime(match.group('end').strip(),
                                             TIMEFMT)
        else:
            end = None

        if complete and not end:
            end = datetime.datetime.now()

        task = match.group('text').strip()

        context = [t.strip() for t in re_context.findall(text)]
        projects = [t.strip() for t in re_project.findall(text)]
        extensions = re_ext.findall(text)
        edict = {}
        for ext in extensions:
            key, val = ext.split(':', 1)
            key = key.replace(' {', '')
            val = val.replace('}', '')
            edict[key] = val.strip()
        if 'uid' not in edict:
            edict['uid'] = start.strftime(IDFMT)
            task += " {uid:%s}" % edict['uid']

        return cls(complete, priority, start, end, task,
                   context, projects, edict)

    @property
    def is_hidden(self):
        "Returns true if the hidden flag exists and shows a future date"
        if 'hide' not in self.extensions:
            return False
        hide_date = datetime.datetime.strptime(self.extensions['hide'],
                                               DATEFMT)
        today = datetime.datetime.now()
        return today < hide_date

    def archiveable(self, days=None, projects=None):
        if not self.complete:
            return False, "Task still open"
        days = days or 7
        projects = projects or []
        now = datetime.datetime.now()
        delta = now - self.end
        if delta.days <= days:
            return False, "Task recently closed"
        if self.projects and self.projects not in projects:
            return False, "Task part of a project"
        return True, "Task archiveable"


def include_task(filterop, filters, task):
    "return a boolean value to include the task or not"
    yeas = []
    for word in filters:
        yea = word.startswith('~')
        testword = word.replace('~', '').lower()
        if testword in task.text.lower():
            yea = not yea
        pri = re_pri_filter.match(word)
        if pri and pri.group(1) == task.priority:
            yea = not yea
        yeas.append(yea)
    return filterop(yeas)


class TaskLib(object):
    """TaskLib

    Main application.
    On load, looks for all entry_points of 'tasker_library' and creates
    a local instance of those libraries. Also assigns itself as the
    ._tasklib attribute on all new libraries
    """
    def __init__(self, config=None):
        super().__init__()

        self.log = logging.getLogger('taskerLogger')

        self.config = config = config or DEFAULT_CONFIG
        if not self.config['Files']['tasker-dir']:
            self.config['Files']['tasker-dir'] = os.path.join(
                    os.path.expanduser('~'), 'tasker')
            self.log.info(
                'setting default tasker-dir %s',
                self.config['Files']['tasker-dir'])

        if not os.path.exists(config['Files']['tasker-dir']):
            try:
                os.mkdir(config['Files']['tasker-dir'])
            except FileNotFoundError:
                self.log.error("Default file not found, resetting")
                config['Files']['tasker-dir'] = os.path.join(
                                                  os.environ['USERPROFILE'],
                                                  'tasker')
                if not os.path.exists(config['Files']['tasker-dir']):
                    os.mkdir(config['Files']['tasker-dir'])

        for path in ['task-path', 'done-path']:
            if not os.path.exists(config['Files'][path]):
                fd = open(config['Files'][path], 'w')
                fd.close()

        self.extension_hiders = {}

        self.libraries = {}
        for entry_point in pkg_resources.iter_entry_points('tasker_library'):
            libclass = entry_point.load()
            self.libraries[entry_point.name] = libclass(
                    self.config['Files']['tasker-dir'])
            self.libraries[entry_point.name]._tasklib = self
            # grab a list of extensions to hide

        self._textwrapper = None
        self.log.debug('tasker-dir %s', config['Files']['tasker-dir'])

        self.theme = {}
        # dictionary of PRI: Color Descriptors

        self.queue = []
        # list of (function name, text)

        for libname, library in self.libraries.items():
            if hasattr(library, 'on_startup'):
                self.log.debug(f'calling library.on_startup ({libname})')
                library.on_startup()

    def set_theme(self, theme_name=None):
        '''set_theme(name)
        Applies format-strings from the local configuration file
        format strings are in the form of '<qualifier> <textcolor> ["on"
        <backgroundcolor>'.
        Themes are stored in the configuration file.
        It is up to an application to determine how to display this data.
        '''

        if not theme_name:
            return
        theme_name = theme_name.title()
        if theme_name == 'None':
            self.theme = {}
            return

        config_name = f"Theme: {theme_name}"
        if self.config.has_section(config_name):
            self.log.info('Setting %s color theme', theme_name)
            self.theme = dict((k.title(), v)
                              for k, v in self.config.items(config_name))
        else:
            self.log.info('Theme not found: %s', theme_name)

    def get_extensions_to_hide(self):
        """get_extensions_to_hide()
        Compile a list of all extensions from the config file
        """
        ext_list = ','.join([self.config[section].get('hidden-extensions', '')
                             for section in self.config])
        ext_list = [ext.strip() for ext in ext_list.split(',') if ext]
        return ext_list

    def hide_extension(self, ext):
        """hide_extension(ext)
        Adds the extension to tasker's list of hidden extensions.
        Hidden extensions will not appear in task lists.
        """
        if not self.config:
            self.log.error('Cannot add hidden extension: No configuration')
            return None

        extensions = self.config['Tasker']['hidden_extensions'].split(',')
        extensions = [e.strip() for e in extensions]
        ext = ext.strip()
        if ext not in extensions:
            extensions.append(ext)

        self.config['Tasker']['hidden_extensions'] = ','.join(extensions)

    def show_extension(self, ext):
        """show_extension(ext)
        Removes the extension from tasker's list of hidden extensions.
        Does not issue an error if the extension is not in the list
        """
        if not self.config:
            self.log.error('Cannot add hidden extension: No configuration')
            return None

        extensions = self.config['Tasker']['hidden_extensions'].split(',')
        extensions = [e.strip() for e in extensions]
        ext = ext.strip()
        if ext in extensions:
            extensions.remove(ext)

        self.config['Tasker']['hidden_extensions'] = ','.join(extensions)

    def get_tasks(self, path):
        """Get tasks from either todo.txt or done.txt

        :param path: path to the file to read
        :rtype: dict
        :return: dictionary of line number, task instance pairs
        """
        res = {}
        with open(path, 'r') as fp:
            idx = 1
            for line in fp.readlines():
                if line.strip():
                    res[idx] = Task.from_text(line.strip())
                    idx += 1
        return res

    def write_tasks(self, task_dict, local_path):
        """write_tasks(task_dict, local_path)
        Writes the working task_dictionary to the appropriate file
        :param dict task_dict: dictionary of (line: task) pairs
        :param filepath local_path: file path to write to
        """
        self.log.info('Writing tasks to %s', local_path)
        with open(local_path, 'w') as fp:
            for linenum in sorted(task_dict):
                fp.write("{}{}".format(task_dict[linenum], '\n'))
        return TASK_OK, "{:d} Tasks written".format(len(task_dict))

    def add_task(self, text: str) -> Task:
        """Adds a task to the current file.
        Returns {idx: taskobj"""
        if not hasattr(self, 'tasks') or self.tasks is None:
            tasks = self.tasks = self.get_tasks(
                self.config['Files']['task-path'])
        else:
            tasks = self.tasks
        this = Task.from_text(text)
        idx = (max(tasks) + 1) if len(tasks) > 0 else 1
        tasks[idx] = this

        # check for on_add_task hooks
        # these methods can functionally change the task
        self.queue = []
        for libname, library in self.libraries.items():
            if hasattr(library, 'on_add_task'):
                self.log.debug(f'calling library.on_add_task ({libname})')
                this = library.on_add_task(this)

        # Issue: Plugins cannot add a task in response.
        # tasks is a local dictionary being written, so new tasks
        # are overridden
        tasks[idx] = this
        self.write_tasks(tasks, self.config['Files']['task-path'])
        self.process_queue()

        return {idx: this}

    def complete_task(self, tasknum, comment=None):
        """Completes an open task if task is not already closed.
        returns TASK_OK, dictionary of {tasknum, taskobject} if successful,
        returns TASK_ERROR, message if not
        """
        # Check if self.tasks has been established
        if not hasattr(self, 'tasks') or self.tasks is None:
            tasks = self.tasks = self.get_tasks(
                self.config['Files']['task-path'])
        else:
            tasks = self.tasks

        if tasknum not in tasks:
            del self.tasks
            return TASK_ERROR, "Task number not in task list"
        if tasks[tasknum].complete:
            del self.tasks
            return TASK_ERROR, "Task already completed"

        this = tasks[tasknum]
        this.complete = True
        this.end = datetime.datetime.now()
        if comment:
            this.text += " # {}".format(comment)

        # check for on_complete_task hooks
        # these methods can functionally change the task
        self.queue = []
        for libname, library in self.libraries.items():
            if hasattr(library, 'on_complete_task'):
                self.log.debug(f'calling library.on_complete_task ({libname})')
                this = library.on_complete_task(this)
                if this is None:
                    self.log.error(
                        ("Plugin %s.on_complete_task failed "
                         "to return task object"),
                        libname)
                    raise RuntimeError(
                        "Plugin failed to return task in on_complete_task")

        # Issue: Plugins cannot add a task in response.
        # tasks is a local dictionary being written, so new tasks
        # are overridden
        tasks[tasknum] = this
        self.write_tasks(tasks, self.config['Files']['task-path'])
        self.process_queue()
        return TASK_OK, {tasknum: tasks[tasknum]}

    def process_queue(self):
        if not hasattr(self, 'queue'):
            return
        for func, args in self.queue:
            getattr(self, func)(**args)
            time.sleep(0.005)

        self.queue = []

    def sort_tasks(self, by_pri=True, filters=None, filterop=None,
                   showcomplete=None, opendate=None, closedate=None,
                   hidedate=None):
        """sort_tasks([by_pri, filters, filteropp, showcomplete])
        Returns a list of (line, task) tuples.
        Default behavior sorts by priority.
        Default behavior does no filtering.
        Default filter operation is all (all must match).
        Default behavior does not list completed tasks
        Default behavior does not look in the done.txt file.
        To filter, provide a list of strings to filter by.
        """

        filters = filters or []
        filterop = filterop if filterop in (all, any) else all
        if filterop not in (any, all):
            self.log.error('Bad filterop parameter in sort_tasks')
            return TASK_ERROR, "Filter Operation must by 'any' or 'all'."
        showcomplete = showcomplete or closedate or False
        hidedate = hidedate or datetime.date.today()

        everything = [(key, val)
                      for key, val in list(self.get_tasks(
                          self.config['Files']['task-path']).items())
                      if (showcomplete or not val.complete)]

        if filters:
            self.log.info('Filtering tasks by keywords')
            everything = [(key, val) for key, val in everything
                          if include_task(filterop, filters, val)]

        if not self.config['Tasker'].getboolean('show-priority-z', True):
            self.log.info("Hiding priority Z tasks")
            everything = [(key, val) for key, val in everything
                          if val.priority != "Z"]

        if opendate:
            self.log.info("Showing items opened on %s", opendate)
            everything = [(key, val) for key, val in everything
                          if val.start.date() == opendate]

        if closedate:
            self.log.info("Showing items closed on %s", closedate)
            everything = [(key, val) for key, val in everything
                          if val.end and val.end.date() == closedate]

        # if the task has a hide extension and the value of that extension
        # is greater than the current day, do not show task.

        # show task unless there is a hide extension and the value is greater
        # than the current day

        everything = [(key, task) for key, task in everything
                      if datetime.datetime.strptime(
                          task.extensions.get('hide',
                                              hidedate.strftime(DATEFMT)),
                          DATEFMT).date() <= hidedate]

        if by_pri:
            plist, zlist, ulist = [], [], []
            for key, val in everything:
                pri = val.priority
                if pri and pri != 'Z':
                    plist.append((key, val))
                elif not pri:
                    ulist.append((key, val))
                else:
                    zlist.append((key, val))

            getter = itemgetter(1)
            if self.config['Tasker'].getboolean('priority-z-last', True):
                stuff = (sorted(plist, key=getter) +
                         sorted(ulist, key=getter) +
                         sorted(zlist, key=getter))
            else:
                stuff = (sorted(plist, key=getter) +
                         sorted(zlist, key=getter) +
                         sorted(ulist, key=getter))

        else:
            stuff = sorted(everything, key=itemgetter(0))
        return stuff

    def prep_extension_hiders(self):
        """create the regex substitutions to hide extensionss"""
        for ext in self.get_extensions_to_hide():
            if ext not in self.extension_hiders:
                self.extension_hiders[ext] = re.compile(r"\s{%s:[^}]*}" % ext)

    def list_tasks(self, by_pri=True, filters: str = None, filterop=None,
                   showcomplete=None, showext=None,
                   opendate=None, closedate=None, hidedate=None):
        """list_tasks([by_pri, filters, filterop, showcomplete, showuid)
        Returns a list of formatted tasks.

        :type by_pri: Boolean
        :param bool by_pri: If true, sorts by priority,
                            if false, sorts by order in file
        :param str filters: Words to filter the list
        :param func filterop: all or any (the functions, not strings
        :param bool showcomplete: If true, shows completed tasks
        :param bool showext: If true, shows the normally hidden
                             extensions of the task.
        :param date opendate: If not None, filters tasks opened on opendate
        :param date closedate: If not None, filters tasks closed on closedate
        :param date hidedate: The date to filter extensions marked to hide
        :rtype: dictionary
        """
        showext = showext or False
        # colorize = self.config['Tasker'].getboolean('use-color', True)
        shown_tasks = self.sort_tasks(by_pri, filters, filterop, showcomplete,
                                      opendate, closedate, hidedate)
        self.log.info('Listing %s tasks %s',
                      'all' if showcomplete else 'open',
                      'by priority' if by_pri else 'by number')

        self.prep_extension_hiders()

        wrap_width = self.config['Tasker'].getint('wrap-width', 78)
        if not self._textwrapper:
            self._textwrapper = textwrap.TextWrapper(width=wrap_width)

        res = dict()

        if shown_tasks:
            maxid = max([a for a, b in shown_tasks])
            idlen = len(str(maxid))
            self._textwrapper.subsequent_indent = ' ' * (idlen+5)
            wrap = self.config['Tasker'].get('wrap-behavior', 'none')
            wrapfunc = str
            if wrap == 'wrap':
                self.log.info("Wrapping long lines of each task")
                wrapfunc = self._textwrapper.fill
            elif wrap == 'shorten':
                self.log.info("Shortening each task")
                wrapfunc = partial(textwrap.shorten, width=wrap_width,
                                   placeholder='...')
            elif wrap == 'none':
                wrapfunc = str
            else:
                self.log.error("Unknown textwrap preference %s", wrap)

            for idx, task in shown_tasks:
                if not showext:
                    for ext in self.extension_hiders:
                        task.text = self.extension_hiders[ext].sub(
                                "", task.text)
                res[idx] = wrapfunc(str(task))

        count = len(res)
        msg = ("{:d} task{:s} shown".format(count, '' if count == 1 else 's'))
        self.log.info(msg)
        return res

    def hide_extensions(self, task: Task) -> str:
        """accepts a task object and returns a string representation without
        the extensions"""
        text = str(task)
        for ext in self.extension_hiders:
            text = self.extension_hiders[ext].sub("", text)
        return text

    def get_color(self, pri):
        color = self.theme.get(pri, 'default')
        # self.log.debug('getting color for %s (%s)', pri, color)
        return color

    def note_task(self, tasknum, note=None):
        """Updates the note on a task by task number."""
        tasks = self.get_tasks(self.config['Files']['task-path'])
        if tasknum not in tasks:
            self.log.error('Task %s not in list', tasknum)
            return TASK_ERROR, "Task number not in task list"
        t = tasks[tasknum]
        t.text = self.update_note(t.text, note)
        tasks[tasknum] = t
        self.write_tasks(tasks, self.config['Files']['task-path'])
        return TASK_OK, {tasknum: tasks[tasknum]}

    def update_note(self, text, note=None):
        """updates the note from a line of text. If note is None or blank,
        removes the note from the text entirely.
        """
        if note:
            return "{} # {}".format(re_note.sub('', text), note)
        else:
            return re_note.sub('', text)

    def prioritize_task(self, tasknum, priority, note=None):
        """prioritize_task(tasknum, new_pri [,note]

        Change the priority of a task. Will do nothing if task is closed.
        New priority can be A-Z but should be A-W.

        :param int tasknum: Number of task to update
        :param str priority: New priority character
        :param str note: Optional note to append
        """
        tasks = self.get_tasks(self.config['Files']['task-path'])
        if tasknum not in tasks:
            self.log.error('Task %s not in list', tasknum)
            return TASK_ERROR, "Task number not in task list"
        if tasks[tasknum].complete:
            self.log.error('Task %s already completed', tasknum)
            return TASK_ERROR, "Task already completed"

        t = self.reprioritize_task(tasks[tasknum], priority)
        t.text = self.update_note(t.text, ' '.join(note))
        tasks[tasknum] = t
        self.write_tasks(tasks, self.config['Files']['task-path'])
        return TASK_OK, {tasknum: tasks[tasknum]}

    def write_current_tasks(self):
        """write the current tasks to the correct file"""
        self.write_tasks(self.tasks, self.config['Files']['task-path'])

    def reprioritize_task(self, task, priority):
        """reprioritize_task(task, new_priority)
        """
        if task.complete:
            self.log.warn("Cannot reprioritize completed task")
            return task

        np = priority.strip()
        match = re.match(r'^[A-Z_]$', np)
        if not match:
            self.log.error("New priority must be A-Z or _")
            return task

        if match.group() == '_':
            task.priority = ''
        else:
            task.priority = match.group()

        self.log.info("Reprioritized task: %s", task)

        return task

    def hide_task(self, tasknum, hidedate):
        tasks = self.get_tasks(self.config['Files']['task-path'])
        if tasknum not in tasks:
            self.log.error('Task %s not in list', tasknum)
            return TASK_ERROR, "Task number not in task list"
        if tasks[tasknum].complete:
            self.log.error('Task %s already completed. Cannot hide')
            return TASK_ERROR, "Cannot hide closed task"
        if 'hide' not in tasks[tasknum].extensions:
            tasks[tasknum].text += " {hide:%s}" % hidedate.strftime(DATEFMT)
        else:
            tasks[tasknum].text = re_hide.sub(
                " {hide:%s}" % hidedate.strftime(DATEFMT), tasks[tasknum].text)
        self.write_tasks(tasks, self.config['Files']['task-path'])
        return TASK_OK, {tasknum: tasks[tasknum]}

    def unhide_task(self, tasknum):
        tasks = self.get_tasks(self.config['Files']['task-path'])
        if tasknum not in tasks:
            self.log.error('Task %s not in list', tasknum)
            return TASK_ERROR, "Task number not in task list"
        if tasks[tasknum].complete:
            self.log.error('Task %s already completed. Cannot unhide')
            return TASK_ERROR, "Cannot unhide completed task"
        tasks[tasknum].text = re_hide.sub("", tasks[tasknum].text)
        self.write_tasks(tasks, self.config['Files']['task-path'])
        return TASK_OK, {tasknum: tasks[tasknum]}

    def build_task_dict(self, include_archive=False, only_archive=False):
        """build_task_dict(include_archive, only_archive)
        Builds a dictionary of tasks, much like :meth:`get_tasks` but will
        read either file, or both.
        """
        if only_archive:
            tasks = self.get_tasks(self.config['Files']['done-path'])
        else:
            tasks = self.get_tasks(self.config['Files']['task-path'])
            if include_archive:
                done = self.get_tasks(self.config['Files']['done-path'])
                for key, val in done.items():
                    tasks['x%d' % key] = val

        return tasks

    def get_counts(self, kind, include_archive=False, only_archive=False):
        """get_counts(kind, include_archive, only_archive)
        Returns a dictionary of :class:`collections.Counter` objects.


        :param str kind: 'project' or 'context'
        :param bool include_archive: passed to :meth:`build_task_dict`
        :param bool only_archive: passet to :meth:`build_task_dict`

        The resulting dictionary looks like::

            {'+SomeProject': Counter({'open': 2, 'closed': 1})}

        """
        kind = kind.upper()

        if kind == 'PROJECT':
            getter = attrgetter('projects')
        elif kind == 'CONTEXT':
            getter = attrgetter('contexts')
        else:
            raise ValueError(
                "Should pass 'project' or 'context' to get_counts")
        res = defaultdict(Counter)
        nothing = 'NO {}'.format(kind)

        tasks = self.build_task_dict(include_archive, only_archive)

        for task in tasks.values():
            items = getter(task)  # projects and contexts are lists

            key = 'closed' if task.complete else 'open'

            if not items:
                res[nothing][key] += 1
                if task.is_hidden:
                    res[nothing]['hidden'] += 1

            for item in items:
                res[item][key] += 1
                res[item][task.priority] += 1
                if task.is_hidden:
                    res[item]['hidden'] += 1

        return res

    def archive_tasks(self, tasks_to_archive):
        """archive_tasks(list of task IDS)
        This does the actual archiving. It assumes the calling method
        has already confirmed tasks are archiveable.
        """
        tasks = self.get_tasks(self.config['Files']['task-path'])
        done = self.get_tasks(self.config['Files']['done-path'])

        next_done = max(done) + 1 if done else 1

        for key in tasks_to_archive:
            done[next_done] = tasks[key]
            next_done += 1
            tasks.pop(key)

        self.write_tasks(tasks, self.config['Files']['task-path'])
        self.write_tasks(done, self.config['Files']['done-path'])

        msg = f"Archived {len(tasks_to_archive)} tasks"
        self.log.info(msg)


if __name__ == '__main__':
    task = Task.from_text("x check for approval on +OUMeridianMaps @quote")
    print(task, task.complete)
