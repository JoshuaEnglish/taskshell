Plugins
=======

Plugins are defined at minimum of two of the following:

    * A class object to serve as the library
    * An argparse.ArgumentParser instance
    * A minioncmd.MinionCmd subclass

It may be helpful to define other classes and helper functions. Both the built
in Checklist plugin and Quotidia plugin define classes and helper functions.

The main application loads plugins at startup using three entry points:

#. ``tasker_library`` defines a plugin library, one that could manage a 
   separate source file. 
#. ``tasker_minions`` defines a MinionCmd object to handle CLI interaction
#. ``tasker_commands`` defines an argparse.ArgumentParser.

Libraries
---------

Libraries can be written to add new features and interact with the main Tasker
application. All libraries are given an ``._tasklib`` attribute reference to the
main library. 

All libraries are passed a ``directory`` attribute on creation.


Hook Methods
^^^^^^^^^^^^

There are three hook methods plugins can define to interact with the main 
library.

.. function:: on_complete_task(task: Task object) -> Task object

    This function is called when the library completes a task. It provides
    the task object and expects a task object in return.

    The main library manages the task list. When a task is completed it scans
    the attached libraries for an ``on_complete_task`` method and calls it with
    the Task object. Plugin libraries can change the task, or do some other
    action based on the task. To add another task in response, the library
    needs to append items to the ``.tasklib.queue``::

        def on_complete_task(self, task):
            ...

            self._tasklib.queue.append((
                'add_task',
                {'text': '(A) Now go do THIS thing as well'}))
            return task

    Plugins must return the task object back to the main application. There is
    no guarantee on the order which these hook methods are called.


.. function:: on_add_task(task: Task Object) -> Task object
    
    Similarly, when the application creates a new task, it scans the attached
    libraries for an ``on_add_task`` method, calling this method with the task
    object and expecting a task in return.
    
    Plugins can add tasks in response to an added task by appending 
    ('add_task', <text of task>) to the ``_tasklib.queue`` object.

.. function:: on_startup()

    This is called when the library is created. It has access to the 
    tasker library and can add tasks or do any other prepwork as needed.

Argumnet Parsers
----------------

Plugins can define their own argument parser to supplement the shell commands.

Here is a template from the quotidia plugin::

    quotidiaparser = parser = argparse.ArgumentParser('quotidia',
        description="Manage regularly scheduled tasks")
    quotidia_command = parser.add_subparsers(title="Quotidia Commands",
        dest='subcommand', metavar='')

    # these arguments should be standard with any plugins
    directory = quotidiaparser.add_argument('--directory', action="store_true",
        default=False, help='show directory of the quotidia and quit')

    version = quotidiaparser.add_argument('--version', action="store_true",
        default=False, help='show version of the quotidia plugin and quit')

    list_cmd = quotidia_command.add_parser(
        'list', help='lists current quotidia')
    list_cmd.add_argument('columns', nargs=argparse.REMAINDER,
        help="optional extra colums")

.. note::
    
    The ArgumentParser instance is connected through the ``tasker_commands``
    entry point.


Minions
-------

Tasker's default interface is the command line. The interactive prompt is run
by MinionCmd. MinionCmd is a subclass of
the cmd.Cmd object that allows separate subprograms to be created and while the
command loop is ative, the user can switch between plugins.

Plugins should define a subclass of minioncmd.MinionCmd with the following
class attributes::

    .. class PluginCmd(minioncmd.MinionCmd)

        .. attribute:: prompt = "plugin>"

        .. attribute:: doc_leader = """Plugin Help ..."""

        Use the following template 




