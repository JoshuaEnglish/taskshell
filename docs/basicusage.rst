Basic Usage
===========

Tasker is a text based task manager that runs at the command line or within
Python. It is written in Python 3.5 but will most likely run in earlier
versions.

Tasker manager manages two files: ``todo.txt`` and ``done.txt``.  Each task is
saved on a single line in either file. Tasker follows the task formatting rules
set out by Gina Trapani's `Todo.txt format`_ with the addition of using
full datetime stamps instead of just dates.

The Anatomy of a Task
---------------------

Tasks consist of a single line of text:

    * 'x ' if the task is completed
    * '(p)' if the task has a priority. Priorities are A-Z.
    * 'datetime stamp' for the start of the task (default to time 
       task is created)
    * 'datetime stamp' for the time the task was completed (if completed)
    * remaining text is the actual task
    * '# ' indicates the start of a note or comment

Tasks are organized by projects (words that begin with '+') and contexts (words
that begin with '@'). Tasks may also have extensions which are key:value pairs
wrapped in brackets (for example ``{uid:221112080316}``).

Here is an example of a pending task::

    (A) 2020-03-08T09:51:38 Finish +TaskerDocumentation @code # It's getting late

This task has a priority. It has a project (TaskerDocumentation) and a context
(code) and a comment.

Here is an example of a completed task::

    x 2020-03-07T11:45:08 2020-03-08T21:35:12 Call mom @phone

This task is complete and won't appear in the task list unless requested.

.. note:: Samples in this document

    In the command line samples, only a simple prompt ``>`` is presented for
    the command line.

    The interactive prompts include their name.

    ``>t list`` and ``tasker>list`` are the same thing, the first from the
    command line and the second from the interactive prompt.

Basic Commands
--------------

The three basic commands are ``list``, ``add``, and ``do``. If no command is
given, the program lists all open tasks::

    >tasker
    1 2020-03-04T22:04:30 test from cli
    2 2015-03-06T19:37:12 test add
    --
    2 tasks shown

    >tasker add go to bed
    '2020-04-08T22:11:12 go to bed {uid:221112080316}'

    >tasker list
    1 2020-03-04T22:04:30 test from cli
    2 2020-03-06T19:37:12 test add
    5 2020-03-08T22:11:12 go to bed
    --
    3 tasks shown

    >tasker do 1
    'x 2020-03-08T22:16:02 2020-03-08T22:16:01 test from cli {uid:220430040316}'

    >tasker
    2 2020-03-06T19:27:12 test add
    5 2020-03-08T22:11:12 go to bed
    --
    2 tasks shown

Tasker adds a ``uid`` extension to each task it creates but does not list this
when it prints the task list. The ``uid`` is used to chain tasks together.

.. note:: Task Numbers

    Task numbers are simply the line number in the current file. This provides
    a quick reference to tasks. Be warned that archiving tasks will renumber
    your files.



Interactive Mode
----------------

You can also run tasker in an interactive prompt::

    >t -i
    tasker> list
    2 2020-03-06T19:27:12 test add
    5 2020-03-08T22:11:12 go to bed
    --
    2 tasks shown

For most commands, the interactive prompt uses the same input as the command
line interface.

Listing Tasks
-------------

The simple ``list`` command will show only currently open tasks, but you can
filter tasks by including search terms::

    >t
    13 (B) 2020-03-20T18:33:23 Get complete information for +HomeQuote @quote
    12 2020-03-17T22:54:20 redo +Documentation
    16 2020-03-21T20:57:51 third useless thing
    ---
    3 tasks shown

    >t list thing
    16 2020-03-21T20:57:51 third useless thing
    ---
    1 tasks shown

    >t list information
    13 (B) 2020-03-20T18:33:23 Get complete information for +HomeQuote @quote
    ---
    1 tasks shown

However, if you try to search for more than one keyword, tasker will only list
open tasks that match all those keywords::

    >t list thing information
    0 tasks shown

You can use the ``-y`` flag to match any filter keyword::

    >t list -y thing information
    13 (B) 2020-03-20T18:33:23 Get complete information for +HomeQuote @quote
    16 2020-03-21T20:57:51 third useless thing
    ---
    2 tasks shown

You can exclude terms with ``~``::

   >t list ~thing
    13 (B) 2020-03-20T18:33:23 Get complete information for +HomeQuote @quote
    12 2020-03-17T22:54:20 redo +Documentation
    ---
    2 tasks shown


Sorting Tasks
^^^^^^^^^^^^^

The default behavior is to list tasks by priority. Using the ``-n`` switch will
display tasks in numerical order::

    >t list -n
    12 2020-03-17T22:54:20 redo +Documentation
    13 (B) 2020-03-20T18:33:23 Get complete information for +HomeQuote @quote
    16 2020-03-21T20:57:51 third useless thing
    ---
    3 tasks shown


Showing Completed Tasks
^^^^^^^^^^^^^^^^^^^^^^^

The default behavior is to only list open tasks, but you can see completed
tasks with the ``-a`` switch::

    >t list -a
    13 (B) 2020-03-20T18:33:23 Get complete information for +HomeQuote @quote
    12 2020-03-17T22:54:20 redo +Documentation
    16 2020-03-21T20:57:51 third useless thing
     2 x 2020-03-06T19:27:12 2020-03-21T20:52:25 test add # test complete
    ...
    ---
    16 tasks shown


Showing Extensions
^^^^^^^^^^^^^^^^^^

The default behavior is to hide extensions that are used by the program to
relate tasks to each other. You can show these extensions with the ``-x``
switch::

    >t list -x
    13 (B) 2020-03-20T18:33:23 Get complete information for +HomeQuote @quote
           {wn:quote} {ws:2} {wid:5} {uid:183323200316}
    12 2020-03-17T22:54:20 redo +Documentation {uid:225420170316}
    16 2020-03-21T20:57:51 third useless thing {uid:205751210316}
    ---
    3 tasks shown


.. note:: The ``list`` command uses text wrap to a default of 78 characters.


Adding Tasks
------------

The default behavior is to add whatever text you include. However, if ``x``
is the first character of the new task, it will be created as a closed task::

    >t add x is this complete?
    x 2020-03-22T21:39:42 2020-03-22T21:39:42 is this complete? {uid:213942220316}

    > t
    13 (B) 2020-03-20T18:33:23 Get complete information for +HomeQuote @quote
    12 2020-03-17T22:54:20 redo +Documentation
    16 2020-03-21T20:57:51 third useless thing
    ---
    3 tasks shown

    >t list -a complete
    17 x 2020-03-22T21:39:42 2020-03-22T21:39:42 is this complete?
    ---
    1 tasks shown

Marking tasks as Complete
-------------------------

You can close a task with the ``do`` command. The input string should be
the TASK NUMBER and any EXTRA COMMENT::

    >t
    32 2020-03-24T15:30:19 unprioritized task # This should be done soon
    ---
    1 task shown

    >t do 32 This is now done
    x 2020-03-24T15:30:19 2020-03-24T15:43:52 unprioritized task {uid:153019240316} # This should be done soon # This is now done

    >t
    0 tasks shown


List Projects and Contexts
---------------------------

It is also possible to list your open and closed projects::

    >t projects
    No open projects.

    >t projects --closed
    Project             Open Closed
    ------------------- ---- ------
    +BogusQuote         0    5
    +BookingsAdjustment 0    1
    ...
    +SaratogaEval       0    1
    +TMQuotes           0    1
    NO PROJECT          0    14

    >t contexts
    No open contexts.

    >t contexts --closed
    Context    Open Closed
    ---------- ---- ------
    @bookings  0    1
    @orders    0    1
    @quote     0    19
    @test      0    2
    NO CONTEXT 0    13


Changing Task Priorities
------------------------

You can change the priority of a task by using the ``pri`` command::

    >t
    32 2020-03-24T15:30:19 unprioritized task
    ---
    1 task shown

    >t pri 32 A This should be done soon
    (A) 2020-03-24T15:30:19 unprioritized task {uid:153019240316} # This should be done soon

    >t
    32 (A) 2020-03-24T15:30:19 unprioritized task # This should be done soon
    ---
    1 task shown

You can remove the proirity on a task using an underscore::

    >t pri 32 _
     2020-03-24T15:30:19 unprioritized task {uid:153019240316} # This should be done soon


Hiding Tasks
------------

Some tasks can't be acted on for some time, and so it is helpful to hide a task
from the list until a certain date.

There are two commands to handle this:

    - ``hide num YYYY-MM-DD`` Hides a task until a given date
    - ``unhide num`` Removes the hide date from a task.

You can use the ``--showhidden`` flag to the list command to all tasks despite
the hide date.

You can use the ``--hidedate YYYY-MM-DD`` to preview the output list for a
given date. If you have a task hidden on 2017-10-05, as of October 5, that
task will appear in the list. On October 4, it will not show up by default,
but you can use ``--hidedate tomorrow`` to see that task.

Getting Details on the Process
------------------------------

You can get more information about what Tasker is doing using the ``-d`` flag
on the command line. 

.. _Todo.txt format: http://github.com/ginatrapani/todo.txt-cli/wiki/The-Todo.txt-Format

