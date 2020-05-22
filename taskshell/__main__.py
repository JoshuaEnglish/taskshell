import minioncmd

from taskshell import TaskLib


class TaskCmd(minioncmd.BossCmd):
    prompt = "tasker> "
    doc_leader = "Tasker Help"
    doc_header = "Top-level commands (type help <command>)"
    minion_header = "Subcommands (type <command> help)"

    def __init__(self, completekey='tab', stdin=None, stdout=None,
                 config=None, lib=None):
        super().__init__(completekey, stdin, stdout)

        self.config = config
        self.lib = lib

    def do_list(self, text):
        """Lists tasks [-nayx] [-o DATE] [-c DATE] [FILTERS]
        Can use ~word to filter out tasks containing that word
        """
        print('Listing Tasks:', text)

    def do_add(self, text):
        """Add a task"""
        print('Adding a task:', text)


def main():
    tasklib = TaskLib()
    print(tasklib)


if __name__ == '__main__':
    main()
