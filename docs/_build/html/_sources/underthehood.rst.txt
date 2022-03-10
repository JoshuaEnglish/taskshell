Under the Hood
==============

The CLI first creates the logging utility, reads the configuration data,
creates the argument parser, and loads all subparsers in the
`tasker_commands` entry point. 

Then the program parses the arguments, updates the configuration object,
and creates the main TaskLib object, 
which attaches all the libraries in the `tasker_library` entry point.

Finally, the BossCmd object is created, which gets minions in the
`tasker_minion` entry point. Depending on the command line arguments,
the program goes into the command loop REPL, lists tasks according to the 
default parameters, or performs a single command.

