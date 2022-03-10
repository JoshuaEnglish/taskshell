The Tasker Library
==================

This is the main standalone library that manages the to-do list.

.. class:: Task

    While the main storage of the todo list and archive are plain text files,
    the library converts these lines of text to objects that can be manipulated
    programatically.

    The parsed text has several attributes:

    * text - the full text as it appears in the file
    * complete - boolean
    * priority - a single letter for priority (empty string for no priority)
    * start - datetime.datetime object for the time the task was entered
    * end - datetime.datetime object for the time the task was completed
    * contexts - a list of contexts attached to the task
    * projects - a list of projects attached to the task
    * extensions - a dictionary of extension key: value pairs  

    Each task is assigned an ``uid`` extension automatically. The ``uid`` value
    is based on the timestamp. The default format is ``%H%M%S%d%m%y``. This 
    allows for milliseconds to be included in the uid. Some plugins can add
    multiple tasks quickly enough that the milliseconds are necessary.
    
    Tasks support simple filtering (i.e. `"bookplot" in T`) and simple 
    sorting by the string representation of the task.

    .. method:: from_text(text)
        :classmethod:

        Converts a text string into a Task object. This is the preferred 
        method of creating a task object, done automatically while reading
        files.

        Plugins can define new tasks as strings. See the section on plugins.

    .. method:: is_hidden
        :property:

        returns true if the Task has a {hide:} extension that is in
        the future. 

.. class:: TaskLib(config)

    This class is the main library.

    The main library reads the default configuration and `tasker.ini` file.
    The main library loads plugin libraries on the ``tasker_library`` 
    entry point.

    .. attribute:: tasks
        
        This is a dictionary of the tasks in the ``task-path`` file. Tasks
        in the file are simply listed one task per line. The dictionary uses
        the line number as the key and the parsed Task objects as the values

    .. method:: add_task(text: str) -> Task

        Converts a task-formatted string into a task object, writes it to the
        file, and stores it locally.

    .. method:: complete_task(tasknum: int [,comment])
        
        :param int tasknum: The number of the task
        :param str comment: Optional comment appended to the task text
        :return: (RES_CODE, task dictionary)
        :rtype: tuple(const, dict)

        Updates a task to be marked complete and saves it to the file
        immediately.

    .. method:: sort_tasks(by_pri, filters, filterop, showcomplete, opendate, closedate, hidedate)

       :param bool by_pri: Sort by priority (default) or by line number 
       :param list filters: List of strings to filty the list by
       :param filterop: default is ``all`` but could by ``any``
       :param bool showcomplete: If True, shows completed tasks. Default is to not show completed tasks
       :param date opendate: Limits to tasks opened on a given date
       :param date closedate: Limits to tasks closed on a give date
       :param date hidedate: Shows tasks hidden until up to and including this date.
       :returns: list of (idx, Task) tuples
       
       This method is the main sorting method of tasks. It returns the ordered
       list of tasks as requested.

    .. method:: list_tasks(by_pri, filters, filterop, showcomplete, showext,
                           opendate, closedate, hidedate)

      :param bool showext: Shows extensions that would otherwise be hidden.  
