# Systray File Watcher (for Linux)

This application will watch for updates occurring to a file, and display
a notification in your system tray when updates are taking place.

This is particularly helpful for error or synchronization logs.

## Dependencies

 - pygtk

On Ubuntu, you can install pygtk by running ``sudo apt-get install python-gtk2``.

## Installation

 1. Run ``sudo python setup.py install``.
 2. Run ``systray_watch /path/to/some/file``.

If the application immediately closes with the message "You must log-out and log-in again for your system tray icon to appear.", log-out and log-back in again; a system settings change was required.
