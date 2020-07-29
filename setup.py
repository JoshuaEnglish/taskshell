from setuptools import setup
import taskshell

setup(
    name='taskshell',
    version=taskshell.__version__,
    description='Extensible Todo Manager',
    url='https://github.com/JoshuaEnglish/taskshell',
    author='Josh English',
    author_email='josh@joshuarenglish.com',
    license='GNU3',
    packages=["taskshell", ],
    install_requires=['colorama','lxml'],
    zip_safe=False,
    entry_points={
        'console_scripts': ['s=taskshell.cli:main'],
        'tasker_commands': 
            ['checklist = taskshell.plugins.checklist:checklistparser',
             'quotidia = taskshell.plugins.quotidia:quotidiaparser'   ],
        'tasker_library': 
            ['checklist = taskshell.plugins.checklist:ChecklistLib',
             'quotidia = taskshell.plugins.quotidia:QuotidiaLib'],
        'tasker_minions': 
            ['checklist = taskshell.plugins.checklist:ChecklistCmd',
             'quotidia = taskshell.plugins.quotidia:QuotidiaCmd']
    }
    )
