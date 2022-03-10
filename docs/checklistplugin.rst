Checklist Plugin
================

This is a standard plugin for Tasker. 

Checklists are stored in xml files. Each xml file stores a particular type
of checklist, including the basic template and all of its instances.

Checklists organize tasks in phases, and each task has specific actions
to be taken. The design principle is that a single task may require several
specific actions. For example, as part of an onboarding process, putting a 
sales rep on new hire draw requires 2 cases in one system, a task in a second
system (after one of the first tasks was completed), and at least seven steps
in four subsystems of another system, with a fourth system involved.

This is a single task from a mangement point of view but from an operations
perspective this is several descrete tasks, each task having specific 
actions. There could be a dozen specific actions to take that will not be
remembered every time the process is done (hence the need for checklists), 
The main Tasker list should not, as a rule, be cluttered with a dozen tasks
to cover something that in "one thing" in general but "a dozen thing" in the
details.

The onboarding checklist looks something like this:

#. Phase 1 - Initial Hire

    #. Submit Case to add _ to CRM
    #. Submit Case to assign territories to _ in CRM
    #. Provision _ in Reporting
    #. Add _ to compensation system
    #. Put _ on draw in compensation system

#. Phase 2 - Complete onboarding

    #. Put _ on full payment plan in compensation system
    #. Confirm _ signs sales agreement

In the real world usage, the phases are seperated by three months.

These steps are the ones that should appear in the main task list as clear 
tasks. The actual actions needed to get all of that done may be a much longer
and more detailed list:

#. Phase 1 - Initial Hire

    #. Submit Case to add _ to CRM

        #. Case type: New User
        #. Case business group:
        #. Assigned sales role
        #. Assigned manager
        #. Case #


Some of these actions aren't really actions, but reminders, so they are 
nuggets of information to remind you (the user) how to do the task, because 
lets face it no one can remember all the little details. Be safe, put it in 
your checklist : ) 

Another one of these 'actions' is actually something the user may wish to 
record, because keeping track of case numbers can be important to trace back
when things go wrong. So *Case #* relies on user imput.

The XML for this would look like::

    <checklist>
      <_template name="onboarding" version="1.0">
        <header>
          <input idsource="true" key="name" label="Employee Name"/>
          <input key="eid" label="Employee ID"/>
          <input key="hiredate" label="Hire Date"/>
        </header>
        <phase id="setup" label="Initial Setup">
          <task id="crmadd" label="Add to CRM">
            <?oncreate add_task (A) Add {name} to CRM +{name}Hire?>
            <?oncomplete unlock crmt?>
            <action>Fill out New Employee Template</action>
            <action>Submit Case</action>
            <input label="Case #"/>
          </task>
          <task id="crmt" label="Add Territories in CRM" status="onhold">
            <?onopen add_task (A) Add {name} Territories in CRM +{name}Hire?>
            <action>Fill out Territory assignment template</action>
            <action>Submit Case</action>
            <input label="Case #"/>
        </phase>
      </_template>
    </checklist>

This is a sample of the first two tasks.
Things to note:

    * The *header* section is used to gather basic information about an 
      instance of the checklist. The ``idsource="true"`` attribute signifies
      that the value of that node is the id used by the system to identify
      the new instance

    * The header is filled out and copied to each instance.
    
    * The first task has two processing instructions.

        * The first triggers a task to be created in the main task list
        * The second triggers a status change in another task in that instance

    * The second task is created with a status of "onhold", meaning no actions
      will be taken. When the system recognizes the first task is completed, 
      the ``oncomplete`` processing instruction will remove the "onhold" status
      attribute from the second task and follow the ``onopen`` processing 
      instruction

    * These processing instructions describe the behavior of the checklist
      in its relationship with the main task list. The checklist interface
      can still complete a checklist task. If a checklist task is completed
      before being opened by an ``unlock`` processing instruction, then
      the main task may not be completed or will be created and automatically
      completed.

CLI Commands
============

.. argparse::
   :ref: taskshell.plugins.checklist.checklistparser
   :prog: checklist
    
   These commands are available from the shell.   

Interactive Prompt Commands
===========================

.. autoclass:: taskshell.plugins.checklist.ChecklistCmd
   :members:
