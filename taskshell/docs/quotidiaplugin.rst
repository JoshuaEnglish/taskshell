The Quotidia Plugin
===================

This is a standard plugin for Tasker. 

The Quotidia plugin generates tasks automatically according to a set schedule.
During startup, the plugin searches through the the quotidia it has, and if
the quotidia is active, adds the appropriate task. If the quotidium has been
added recently enough, it is not added again, so running Tasker more than 
once during the day does not cause problems.

Quotidia can be scheduled to run by the day of the week or the day of the 
month. Day codes are "MTWRFYS" for Monday through Sunday, and the day of the
month is a list of days separated by semicolons (i.e. `1` or `5;20`).

Outline of a Quotidium
----------------------

A Quotidium has the following proporties:

=========  ===================================
Attribute  Description
=========  ===================================
qid        Unique identifier for the quotidium
text       The text of the task to be added
days       DOW or DOM codes
active     Boolean value to turn them off
history    List of dates run
=========  ===================================

Using Quotidia on the Command Line
----------------------------------

To use Quotidia on the cmmand line interface

.. argparse::
  :ref: taskshell.plugins.quotidia.quotidiaparser
  :prog: quotidia
  :passparser:
