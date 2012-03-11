from setuptools import setup

from systray_file_watcher_app import get_version

setup(
    name='systray_file_watcher',
    version=get_version(),
    url='http://bitbucket.org/latestrevision/systray-file-watcher/',
    description='File modification notifier in your system tray',
    author='Adam Coddington',
    author_email='me@adamcoddington.net',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Utilities',
    ],
    packages=['systray_file_watcher_app', ],
    entry_points={
            'console_scripts': [
                'systray_watch = systray_file_watcher_app.application:run_from_cmdline',
                ],
        },
    install_requires = [
            #'pygtk',
        ],
    include_package_data=True
)
