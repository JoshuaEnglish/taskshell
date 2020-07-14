from setuptools import setup

setup(
    name='taskshell',
    version='0.0dev',
    description='Extensible Todo Manager',
    url='https://github.com/JoshuaEnglish/taskshell',
    author='Josh English',
    author_email='josh@joshuarenglish.com',
    license='GNU3',
    packages=["taskshell", ],
    install_requires=['colorama','lxml']
    zip_safe=False,
    entry_points={
        'console_scripts': ['s=taskshell.cli:main'],
        'tasker_commands': ['checklist = taskshell.plugins.checklist:checklistparser'],
        'tasker_library': ['checklist = taskshell.plugins.checklist:ChecklistLib'],
        'tasker_minions': ['checklist = taskshell.plugins.checklist:ChecklistCmd']
    }
    )
