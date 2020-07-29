Plugins
=======

Plugins are found using entry points. There are three entry points used by the
application:

#. ``tasker_library`` defines a plugin library, one that could manage a separate source file. 
#. ``tasker_minions`` defines a MinionCmd object to handle CLI interaction
#. ``tasker_commands`` defines an argparse.ArgumentParser.

Libraries
---------

Libraries can be written to add new features and interact with the main Tasker
application. All libraries are given an ``._tasklib`` attribute reference to the
main library. 

The main library manages the task list. When a task is completed it scans
the attached libraries for an ``on_complete_task`` method and calls it with the
Task object. Plugin libraries can change the task, or do some other action
based on the task. To add another task in response, the library needs to 
append items to the ``.tasklib.queue``::

    def on_complete_task(self, task):
        ...

        self._tasklib.queue.append((
            'add_task',
            {'text': '(A) Now go do THIS thing as well'}))
        return task

Plugins must return the task object back to the main application. There is no
guarantee on the order which these hook methods are called.

Similarly, when the application creates a new task, it scans the attached 
libraries for an ``on_add_task`` method, calling this method with the task
object and expecting a task in return.

Minions
-------

Tasker's default interface is the command line. MinionCmd is a subclass of
the cmd.Cmd object that allows separate subprograms to be created and while the
command loop is ative, the user can switch between plugins.




