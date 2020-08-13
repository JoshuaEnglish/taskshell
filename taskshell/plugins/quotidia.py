"""Quotidia Checklist

Plugin for tasker (taskshell, specifically) to manage time-based scheduled
tasks.

Ideal for adding tasks that have to be run regurlarly, such as

    (A) Check Human Resources Report

every Tuesday.

"""

import os
import argparse
import pathlib
import logging
import datetime
import json
import operator
import re
import calendar

import minioncmd

from taskshell import lister

__version__ = '0.0.1'

quotidiaparser = parser = argparse.ArgumentParser('quotidia',
    description="Manage regularly scheduled tasks")
quotidia_command = parser.add_subparsers(title="Quotidia Commands",
    dest='subcommand', metavar='')


list_cmd = quotidia_command.add_parser(
    'list', help='lists current quotidia')
list_cmd.add_argument('columns', nargs=argparse.REMAINDER,
    help="optional extra colums")

# these arguments should be standard with any plugins
directory = quotidiaparser.add_argument('--directory', action="store_true",
    default=False, help='show directory of the quotidia and quit')

version = quotidiaparser.add_argument('--version', action="store_true",
    default=False, help='show version of the quotidia plugin and quit')


class QuotidiaCmd(minioncmd.MinionCmd):
    prompt="quotidia>"
    doc_leader = """Quotidia Help

    Manage scheduled tasks"""

    def __init__(self, completekey="tab", stdin=None, stdout=None,
                 qlib = None):
        super().__init__('quotidia', completekey=completekey, stdin=stdin,
                         stdout=stdout)
        self.lib = qlib

    def do_list(self, text):
        """Usage: list [fields...]

        Lists current quotidia, can add fields to include in the reprot
        such as `last_run` or `task_text`
        """
        fields = text.split()
        res = []
        if 'qid' not in fields:
            fields.insert(0, 'qid')
        getter = operator.attrgetter(*fields)
        lister.print_list([getter(q) for q in self.lib.qids.values()],
                fields)

    def do_new(self, text):
        """Usage: new NAME

        Create a new quotidium. Extra information is asked for"""
        newname = text.strip().split()
        if not newname:
            print("Please enter a name for the new quotidium")
            return None

        newname = newname[0]

        if newname in self.lib.qids:
            self.lib.log.error('Quotidia %s already exists', newname)
            print(f"Quotidia `{newname}` already exists")
            return None
        text = input("Enter text for new quotidium: ")
        if not text:
            print("Cancelling")
            return None

        days_ok = False
        while not days_ok:
            days = input("Enter days to run [SMTWRFY or 1;2; ...] ")
            if not days:
                continue
            days_ok = re.match(r"^S?M?T?W?R?F?Y?$|^(\d{1,2};?)+$", days)

        fname = "%s.quotidia"
        self.lib.add_quotidia(newname, text, days)
        print("Created new quotidia in", fname)


class Quotidium:
    """Quotidium(qid: str, text: str, days: str, active: bool=True,
                 history=None)
       Create a Quotidium object"""

    def __init__(self, qid: str, text: str, days: str,
                    active: bool = True, history=None):
       self.qid = qid
       self.text = text
       self.days = days
       self.active = active
       self.history = history if history else []

       if f"{{qid:{qid}}}" not in self.text:
           self.text += f" {{qid:{qid}}}"

    @property
    def as_dict(self):
        return {
            '__quotidium__': True,
            'qid': self.qid,
            'text': self.text,
            'days': self.days,
            'active': self.active,
            'history': [d.isoformat() for d in self.history]
            }

    def __str__(self):
        return f"{self.qid}: `{self.text}` on {self.days}"

    @property
    def task_text(self):
        return self.text

    @property
    def last_run(self):
        return max(self.history, default=datetime.date.min)

    @property
    def run_count(self):
        return len(self.history)

    @property
    def recurrencetype(self):
        return "DOW" if self.days.isalpha() else "DOM"


class QuotidiaEncoder(json.JSONEncoder):
    """Custome JSON Encoder"""
    def default(self, quotidium):
        if isinstance(quotidium, Quotidium):
            return quotidium.as_dict
        else:
            return super().default(quotidium)

def load_quotidium(dct):
    if "__quotidium__" in dct:
        if 'active' not in dct:
            dct['active'] = True
        return Quotidium(dct['qid'], dct['text'], dct['days'], dct['active'],
                         [datetime.date.fromisoformat(d)
                             for d in dct['history']])
    return dct


class QuotidiaLib(object):
    """Quotidia Library
    This manages scheduled tasks. It is imported by the main tasklib.
    """

    __version__ = __version__

    def __init__(self, directory):
        self.log = logging.getLogger('quotidia')
        self.log.info('creating quotidialib')

        self.directory = pathlib.Path(directory) / 'quotidia'
        self.directory.mkdir(exist_ok=True)

        self.qids = {}
        self.now = datetime.datetime.now()
        self.get_quotidia()

    @property
    def quotidia(self):
        return self.qids

    def get_quotidia(self):
        for qfile in list(self.directory.glob("*.quotidia")):
            self.qids[qfile.stem] = json.loads(qfile.read_text(),
                                               object_hook=load_quotidium)

    def add_quotidia(self, qid, text, days):
        if qid in self.qids:
            self.log.error("QID `%s` already exists", qid)
            raise ValueError("QID %s already exists" % qid)
            return None
        q = Quotidium(qid, text, days)
        fname = f"{qid}.quotidia"
        json.dump(q, (self.directory / fname).open(mode='w'),
            cls=QuotidiaEncoder)
        self.log.info('Created %s', fname)
        self.qids[qid] = q

    def save_quotidium(self, q):
        fname = f"{q.qid}.quotidia"
        with open(self.directory / fname, 'w') as qf:
            json.dump(q, qf, cls=QuotidiaEncoder)
        self.log.info('Saved %s', fname)

    def activate_quotidium(self, qid):
        q = self.qids[qid]
        self.log.debug('Activating quotidium %s', qid)
        q.active = True
        self.save_quotidium(q)

    def deactivate_quotidium(self, qid):
        q = self.qids[qid]
        self.log.debug('Deactivating quotidium %s', qid)
        q.active = False
        self.save_quotidium(q)

    def get_todays_quotidia(self):
        "return a dictionary of {qid: quotidium} that could be run today"
        dayinits = "MTWRFYS"

        def daysago(startday, dinit):
            return (startday - dayinits.index(dinit)) % 7

        today = datetime.date.today()
        tasks_to_add = set()
        for qid, q in self.qids.items():
            if not q.active:
                continue
            days_since_run = (today - q.last_run).days
            self.log.debug('checking qid %s', qid)
            self.log.debug("%s last run on %s (%s days ago)",
                           qid, q.last_run, days_since_run)
            if q.recurrencetype == 'DOW':
                self.log.debug('Trying by Day of Week')
                should_have_run = min(
                    (daysago(today.weekday(), d) for d in q.days))
                if (should_have_run < days_since_run):
                    tasks_to_add.add((qid, q))

            if q.recurrencetype == 'DOM':
                self.log.debug('trying by day of month')
                for day in sorted(q.days.split(';')):
                    dom = int(day)
                    if today.day < dom:
                        continue
                    days_since_dom = today.day - dom

                if days_since_run > days_since_dom:
                    tasks_to_add.add((qid, q))

        return tasks_to_add

    def process_quotidia(self):
        q_to_run = []
        for (qid, q) in self.get_todays_quotidia():
            days = (self.now.date() - q.last_run).days
            if days > 0:
                q_to_run.append(q)
        return q_to_run

    def run_quotidium(self, qid):
        if qid not in self.qids:
            self.log.critical('Cannot run qid %s: does not exist', qid)
            raise ValueError('Cannot run qid %s: does not exist' % qid)
        self.qids[qid].history.insert(0, datetime.date.today())
        self.save_quotidium(self.qids[qid])

    def on_startup(self):
        for (a, b) in self.get_todays_quotidia():
            # check if an open task on that quotidia exists
            qtasks = self._tasklib.list_tasks(filters=[f"{{qid:{a}}}"])
            if qtasks:
                continue
            self.run_quotidium(a)
            rdict = self._tasklib.add_task(b.task_text)
            self.log.info("Adding Quotidia for %s", a)


        # rdict = self._tasklib.add_task(text)
