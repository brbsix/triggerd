# -*- coding: utf-8 -*-

from setuptools import setup
from triggerd import __program__
from triggerd import __version__


def read(filename):
    with open(filename) as f:
        return f.read()


setup(
    name=__program__,
    version=__version__,
    author='Brian Beffa',
    author_email='brbsix@gmail.com',
    description='Trigger an event or notification upon the output of a command',
    long_description=read('README.rst'),
    url='https://github.com/brbsix/triggerd',
    license='GPLv3',
    keywords=['automation', 'cron', 'monitoring', 'trigger', 'triggering'],
    py_modules=['triggerd'],
    scripts=['scripts/bash-config', 'scripts/triggerd.sh'],
    data_files=[('share/triggerd/examples', ['examples/event.txt', 'examples/triggers.conf'])],
    install_requires=['batchpath', 'configobj'],
    entry_points={
        'console_scripts': ['triggerd=triggerd:main'],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.0',
        'Programming Language :: Python :: 3.1',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Unix Shell',
        'Topic :: Home Automation',
        'Topic :: System',
        'Topic :: System :: Monitoring',
        'Topic :: System :: Systems Administration',
        'Topic :: Utilities',
    ],
)
