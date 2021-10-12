import sys
import argparse
import pkg_resources
import datetime
import re
import logging
import logging.config
import pathlib

from collections import defaultdict

import colorama

import minioncmd
from lister import print_list

from taskshell import TaskLib, config, TASK_OK, TASK_ERROR, __version__

logconfigpath = pathlib.Path(__file__).parent / "logging.conf"

logging.config.fileConfig(logconfigpath)

logger = logging.getLogger("taskerLogger")


def add_subparser(subparser):
    """add_subparser(subparser [,helpstr])
    Adds an argparse.ArgumentParser instance to the main parser.

    :param argparse.ArgumentParser subparser: Instance to add
    :param str helpstr: public help string
    """

    global commands

    if not isinstance(subparser, argparse.ArgumentParser):
        raise TypeError("Subparser must be an instance of ArgumentParser")

    name = subparser.prog  # assume no prefix commands have been put in

    subparser.prog = "%s %s" % (parser.prog, name)
    commands.choices[name] = subparser

    # to include this in help we need include the help string
    choice_action = commands._ChoicesPseudoAction(
        name, (), subparser.description
    )
    commands._choices_actions.append(choice_action)


def valid_date(string):
    """Confirm dates in the arguments work as dates, and allows for
    three strings: today, yesterday, and tomorrow"""
    if string.lower() == "today":
        return datetime.date.today()
    elif string.lower() == "yesterday":
        return datetime.date.today() - datetime.timedelta(days=1)
    elif string.lower() == "tomorrow":
        return datetime.date.today() + datetime.timedelta(days=1)

    try:
        return datetime.datetime.strptime(string, "%Y-%m-%d").date()
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(string)
        logger.error(msg)
        raise argparse.ArgumentTypeError(msg)


parser = argparse.ArgumentParser(
    "t",
    description="Extensible text-based todo-manager",
    usage="t [app options] command [command options] [command arguments]",
)

commands = parser.add_subparsers(
    title="supported commands", dest="command", metavar=""
)

list_cmd = commands.add_parser(
    "list", help="list tasks", description="tool for listing tasks"
)

list_cmd.add_argument(
    "-n",
    action="store_false",
    dest="by_pri",
    default=True,
    help="Prints task list in numerical order, otherwise by priority",
)

list_cmd.add_argument(
    "-y",
    dest="filterop",
    action="store_true",
    default=False,
    help="Shows tasks matching any filter word. Default is to match all",
)

list_cmd.add_argument(
    "-a",
    dest="showcomplete",
    action="store_true",
    default=False,
    help="Show completed (but not archived) tasks.",
)

list_cmd.add_argument(
    "-x",
    dest="showext",
    action="store_true",
    default=False,
    help="Shows hidden text extensions",
)

list_cmd.add_argument(
    "-o",
    dest="opendate",
    type=valid_date,
    help="Lists tasks opened on a given date.",
)

list_cmd.add_argument(
    "-c",
    dest="closedate",
    type=valid_date,
    help="Lists tasks closed on a given date.",
)

list_cmd.add_argument(
    "--hidedate",
    dest="hidedate",
    type=valid_date,
    default=datetime.date.today(),
    help="Sets preview date for hidden tasks",
)

list_cmd.add_argument(
    "--showhidden",
    dest="hidedate",
    action="store_const",
    const=datetime.date.max,
    help="Shows all hidden tasks",
)

list_cmd.add_argument(
    "filters",
    nargs=argparse.REMAINDER,
    help="Only lists tasks containing these words (or ~word to exclude)",
)


add_cmd = commands.add_parser("add", help="add a task")
add_cmd.add_argument(
    "-d",
    "--done",
    action="store_true",
    default=False,
    help="Adds task as completed",
)
add_cmd.add_argument(nargs="+", dest="text", help="text of the new task")

do_cmd = commands.add_parser("do", help="mark a task as complete")
do_cmd.add_argument("tasknum", type=int, help="number of the task to complete")
do_cmd.add_argument(
    "comment",
    nargs=argparse.REMAINDER,
    help="optional comment to add to the completed task",
)

note = commands.add_parser("note", help="Add a note to a task")
note.add_argument("tasknum", type=int, help="number of the task to note")
note.add_argument("note", nargs=argparse.REMAINDER, help="note to add to task")

pri = commands.add_parser("pri", help="Prioritize a task")
pri.add_argument("tasknum", type=int, help="number of the task to prioritize")
pri.add_argument("priority", type=str, help="new priority or _ to clear")
pri.add_argument("note", nargs=argparse.REMAINDER, help="additional comment")

hide_cmd = commands.add_parser("hide", help="hide a task until a given date")
hide_cmd.add_argument("tasknum", type=int, help="number of the task to hide")
hide_cmd.add_argument(
    "date", type=valid_date, help="date the task will appear"
)

archive_cmd = commands.add_parser("archive", help="archive a task")
archive_cmd.add_argument(
    "tasknum",
    type=int,
    nargs=argparse.REMAINDER,
    help="number of the task to archive",
)
archive_cmd.add_argument(
    "-p",
    "--project",
    help="archive by project",
    nargs=argparse.REMAINDER,
    default=[],
)
archive_cmd.add_argument(
    "-c",
    "--context",
    help="archive by context",
    nargs=argparse.REMAINDER,
    default=[],
)

proj_cmd = commands.add_parser("projects", help="print a project report")

for e_point in pkg_resources.iter_entry_points("tasker_commands"):
    new_cmd = e_point.load()
    add_subparser(new_cmd)

parser.add_argument(
    "-i",
    "--interactive",
    dest="interact",
    action="store_true",
    default=False,
    help="enter an interactive loop",
)

parser.add_argument(
    "--power", action="store_true", default=False, help=argparse.SUPPRESS
)

parser.add_argument(
    "--wrap",
    choices=["wrap", "shorten", "none"],
    default=config["Tasker"].get("wrap-behavior"),
    help="how to handle long lines",
)

parser.add_argument(
    "--width",
    type=int,
    default=78,
    help="width to wrap or shorten text when printing",
)

parser.add_argument(
    "-z",
    action="store_const",
    default=config["Tasker"].getboolean("show-priority-z"),
    dest="showz",
    const=not config["Tasker"].getboolean("show-priority-z"),
    help="Toggles visibilyt of Z-priority tasks",
)

parser.add_argument(
    "-l",
    action="store_false",
    default=True,
    dest="integrate",
    help="Show Z-priority tasks before unprioritized tasks",
)

theme = parser.add_mutually_exclusive_group()
theme.add_argument(
    "-t",
    "--theme",
    action="store",
    dest="theme",
    default="default",
    help="sets color scheme",
)
theme.add_argument(
    "-n",
    "--no-color",
    action="store_const",
    dest="theme",
    const="none",
    help="removes colorization of output",
)

feedback = parser.add_mutually_exclusive_group()
feedback.add_argument(
    "-d",
    "--debug",
    action="store_true",
    default=False,
    help="show all debug messages in the console",
)
feedback.add_argument(
    "-v",
    "--verbose",
    action="store_true",
    default=False,
    help="show more process details (can repeat)",
)

folder = parser.add_argument(
    "--directory",
    action="store_true",
    default=False,
    help="List directory and quit",
)

version = parser.add_argument(
    "--version",
    action="store_true",
    default=False,
    help="List version and quit",
)

re_color = re.compile(
    r"""
(?P<style>bright|dim|normal|resetall)?\s*
(?P<fore>black|blue|cyan|green|lightblack|magenta|red|reset|white|yellow)?
(\s+on\s+(?P<back>black|blue|cyan|green|lightblack|magenta|red|reset|white|yellow))?
""",
    re.VERBOSE + re.IGNORECASE,
)


def get_color(text):
    """Convert a textLib theme string to a colorama color"""
    stuff = re_color.match(text).groupdict()
    style = stuff.get("style") or ""
    if style.upper() == "RESETALL":
        style = "RESET_ALL"

    fore = stuff.get("fore") or ""
    if fore.upper() == "LIGHTBLACK":

        fore = "LIGHTBLACK_EX"

    back = stuff.get("back") or ""
    if back.upper() == "LIGHTBLACK":
        back = "LIGHTBLACK_EX"

    res = []
    if style:
        res.append(getattr(colorama.Style, style.upper()))
    if fore:
        res.append(getattr(colorama.Fore, fore.upper()))
    if back:
        res.append(getattr(colorama.Back, back.upper()))
    return "".join(res)


class TaskCmd(minioncmd.BossCmd):
    prompt = "tasker>"
    doc_leader = "Tasker Help"
    doc_header = "Top-level commands (type help <command>)"
    minion_header = "Subprogramns (type <subprogram> help)"

    def __init__(self, config=None, lib=None):
        super().__init__()

        self.config = config
        self.lib = lib

    def do_list(self, text):
        """Lists tasks [-nayx] [-o DATE] [-c DATE] [FILTERS]
        Can use ~word to filter out tasks containing that word
        """
        args = commands.choices["list"].parse_args(text.split())
        args.filterop = any if args.filterop else all
        args = vars(args)
        showext = args.pop("showext")
        tasks = self.lib.sort_tasks(**args)
        self.print_tasks(dict(tasks), showext)

    def do_add(self, text):
        """Add a task"""
        args = commands.choices["add"].parse_args(text.split())
        if args.done:
            res = self.lib.add_done(" ".join(args.text))
        else:
            res = self.lib.add_task(" ".join(args.text))
        self.print_tasks(res)

    def do_do(self, text):
        """Complete a task"""
        args = commands.choices["do"].parse_args(text.split())
        res, td = self.lib.complete_task(args.tasknum, " ".join(args.comment))
        if res == TASK_OK:
            self.print_tasks(td)
        elif res == TASK_ERROR:
            print("Error:", td)

    def do_note(self, text):
        """Add a note to a task"""
        args = commands.choices["note"].parse_args(text.split())
        res, td = self.lib.note_task(args.tasknum, " ".join(args.note))
        if res == TASK_OK:
            self.print_tasks(td)
        elif res == TASK_ERROR:
            print("Error:", td)

    def do_pri(self, text):
        """Prioritize a task"""
        args = commands.choices["pri"].parse_args(text.split())
        print(args)
        res, td = self.lib.prioritize_task(
            args.tasknum, args.priority, " ".join(args.note)
        )
        if res == TASK_OK:
            self.print_tasks(td)
        elif res == TASK_ERROR:
            print("Error:", td)

    def do_hide(self, text):
        """hides a task"""
        args = commands.choices["hide"].parse_args(text.split())
        res, td = self.lib.hide_task(args.tasknum, args.date)
        if res == TASK_OK:
            self.print_tasks(td)
        elif res == TASK_ERROR:
            print("Error:", td)

    def do_archive(self, text):
        """archives a task by number"""
        args = commands.choices["archive"].parse_args(text.split())
        tasks = self.lib.get_tasks(self.config["Files"]["task-path"])
        print(args)

        good = []
        bad = []
        reasons = defaultdict(list)
        tasks_to_check = args.tasknum

        for project in args.project:
            victims = [
                tasknum
                for tasknum, task in tasks.items()
                if project in task.projects
            ]
            print("Project Tasks:", victims)
            tasks_to_check.extend(victims)

        for context in args.context:
            victims = [
                tasknum
                for tasknum, task in tasks.items()
                if context in task.contexts
            ]
            print("Context Tasks:", victims)
            tasks_to_check.extend(victims)

        for tasknum in tasks_to_check:
            print(tasknum, tasks[tasknum])
            okay, reason = tasks[tasknum].archiveable(projects=args.project)
            if okay:
                good.append(tasknum)
            else:
                bad.append((tasknum, reason))
                reasons[reason].append(tasknum)

        if good:
            self.lib.archive_tasks(good)
        print(f"Archived {len(good)} tasks")
        if bad:
            print(f"{len(bad)} tasks not archived")
            for reason in reasons:
                print(f"{reason}: {len(reasons[reason])}")

    def do_projects(self, text):
        "print a report of projects"
        stuff = []
        for thing, counts in self.lib.get_counts("PROJECT").items():
            stuff.append((thing, counts["open"], counts["closed"]))

        print_list(stuff, ["Project", "Open", "Closed"])

    def print_tasks(self, taskdict, showext=False):
        if not taskdict:
            print("No tasks found")
            return
        idlen = len(str(max(taskdict)))
        self.lib.prep_extension_hiders()
        for key, task in taskdict.items():
            if not showext:
                text = self.lib.hide_extensions(task)
            else:
                text = str(task)
            if task.complete:
                color = get_color(self.lib.get_color("Closed"))
            else:
                color = get_color(self.lib.get_color(task.priority))
            print("{3}{1:{0}d} {2}".format(idlen, key, text, color))
        print("{0}{1}".format(colorama.Fore.RESET, "_" * (idlen + 1)))
        print(
            "{:d} task{:s} shown".format(
                len(taskdict), "" if len(taskdict) == 1 else "s"
            )
        )


def main():
    args = parser.parse_args()
    logging.debug(args)

    if args.verbose:
        logger.setLevel(logging.INFO)
    if args.debug:
        logger.setLevel(logging.DEBUG)

    config.set("Tasker", "wrap-behavior", args.wrap)
    config.set("Tasker", "wrap-width", str(args.width))

    config.set("Tasker", "show-priority-z", str(args.showz))
    config.set("Tasker", "priority-z-last", str(args.integrate))

    config.set("Tasker", "theme-name", args.theme)

    tasklib = TaskLib(config)
    tasklib.set_theme(args.theme)

    colorama.init(strip=True, autoreset=True)

    cli = TaskCmd(config=config, lib=tasklib)
    for e_point in pkg_resources.iter_entry_points("tasker_minions"):
        minion = e_point.load()
        cli.add_minion(e_point.name, minion())
        # the main library should have already loaded a library for the
        # plugin, if one exists.
        # the minion should now have a master
        if e_point.name in cli.lib.libraries:
            cli.minions[e_point.name].lib = cli.lib.libraries.get(e_point.name)

    if args.directory:
        if args.command:
            print(tasklib.libraries[args.command].directory)
        else:
            print(config["Files"]["tasker-dir"])
        return 0
    if args.version:
        if args.command:
            print(tasklib.libraries[args.command].__version__)
        else:
            print(__version__)
        return 0

    if args.power:
        print("WE HAVE THE POWER")
        import powercmd

        pcmd = powercmd.PowerCmd("poweruser", cli)
        pcmd.config = config
        args.interact = True
        cli.args = args
        cli.cmdqueue.append("poweruser")

    if args.interact:
        cli.cmdloop()
    elif not args.command:
        cli.onecmd("list")
    else:
        cli.onecmd(" ".join(sys.argv[sys.argv.index(args.command) :]))

    return 0


if __name__ == "__main__":
    sys.exit(main())
