"""PowerCmd

Undocumented godmode for tasker
"""

import os
import logging
import code

import minioncmd


class PowerCmd(minioncmd.MinionCmd):
    prompt = "power>"
    doc_leader = "Power User Help"
    log = logging.getLogger("poweruser")

    def do_opencodebase(self, line):
        """Opens the folder contining tasker's code"""
        os.startfile(".")

    def do_queue(self, line):
        """Lists all items in the cmdqueue"""
        if not self.master.cmdqueue:
            self.stdout.write("No queued commands\n")
        for item in self.master.cmdqueue:
            self.stdout.write("Queued command: {}=n".format(item))

    def do_sections(self, line):
        """Lists the configuration sections
        Usage: sections"""
        config = self.master.config
        for section in config.sections():
            print(section)

    def do_items(self, line):
        """Lists items in a given section
        Usage: items [section]"""
        config = self.config
        if line.strip() not in config.sections():
            self.stdout.write("Section not found")
        for key, val in config.items(line.strip(), True):
            self.stdout.write(f"{key} = {val}\n")

    def do_set(self, line):
        """Sets a configuration option
        Usage: set SECTION OPTION VALUE"""
        config = self.config
        try:
            section, option, value = line.split(maxsplit=2)
            config.set(section, option, value)
            if self.master:
                self.log.info("Setting option. Saving configuration file")
                self.master.save_config()
            else:
                self.log.info("No master command.Cannot save options.")
        except KeyError as error:
            self.stdout.write(error)

    def do_openfolder(self, line):
        """Opens the tasker file directory
        Usage: openfolder"""
        os.startfile(self.config["Files"]["tasker-dir"])

    def do_python(self, line):
        """Start a python interactive shell"""
        namespace = {
            "boss": self.master,
            "config": self.master.config,
            "lib": self.master.lib,
            "log": logging.getLogger("main"),
            "args": self.master.args,
        }
        code.interact("Tasker Python Session", local=namespace)
        return None
