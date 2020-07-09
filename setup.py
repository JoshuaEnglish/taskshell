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
    zip_safe=False,
    entry_points={
        'console_scripts': ['s=taskshell.cli:main'],
    }
    )
