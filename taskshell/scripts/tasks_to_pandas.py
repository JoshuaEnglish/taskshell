from taskshell import TaskLib, config
import pandas as pd

tasklib = TaskLib(config)

data = []
for tasknum, taskobj in tasklib.sort_tasks(
    filters=[
        "newhire",
    ],
    showcomplete=True,
):
    data.append(
        [
            taskobj.complete,
            taskobj.start,
            taskobj.end,
            taskobj.text,
            " ".join(taskobj.contexts),
            " ".join(taskobj.projects),
        ]
    )

df = pd.DataFrame.from_records(
    data, columns=["complete", "start", "end", "text", "contexts", "projects"]
)
print(df)
