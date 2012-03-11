#!/usr/bin/python
#
# Copyright (c) 2012 Adam Coddington
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import datetime
import logging
from multiprocessing import Process, Queue
import os
from optparse import OptionParser
from subprocess import Popen, PIPE
import time

from gi.repository import GObject, Gio, GLib
import gtk

class FileWatcher(gtk.StatusIcon):
    UI_UPDATE_DURATION = datetime.timedelta(seconds = 2)
    INTERVAL = 100 # Milliseconds!

    def __init__(self, watch):
        self.logger = logging.getLogger('FileWatcher')
        self.logger.debug("Initializing...")

        self.watch = watch

        gtk.StatusIcon.__init__(self)

        self.ui_reset()

        self.notification_active = False
        self.last_update = datetime.datetime(2000, 1, 1)

        self.procs = {}

        self.from_tail = Queue()
        self.to_tail = Queue()

        self.main()

    def configure_unity(self):
        application_name = 'systray_watch'
        schema = 'com.canonical.Unity.Panel'
        key = 'systray-whitelist'
        settings = Gio.Settings(schema)
        value = settings.get_value(key)
        if value:
            if 'all' not in value and application_name not in value:
                unpacked = value.unpack()
                unpacked.append(application_name)
                updated = GLib.Variant('as', unpacked)
                settings.set_value(key, updated)
                raise Exception("You must log-out and log-in again for your system tray icon to appear.")

    def main(self):
        self.watch_file(self.watch)
        GObject.timeout_add(self.INTERVAL, self.check_for_notifications)
        self.ui_reset()
        self.logger.info("Started.")

    def watch_file(self, file_path):
        self.logger.info("Spawing process for watching \"%s\"" % file_path)
        proc_info = {}
        proc_info['process'] = Process(
                        target=FileWatcherProcess,
                        args=(
                                file_path,
                                self.to_tail,
                                self.from_tail,
                            )
                    )
        proc_info['process'].start()
        self.procs[file_path] = proc_info

    def check_for_notifications(self):
        if not self.from_tail.empty():
            self.logger.debug("Found new data.")
            data_object = self.from_tail.get_nowait()
            self.ui_update_new_data(data_object)
        if self.ui_notification_out_of_date() and self.notification_active:
            self.logger.debug("Setting notification as expired.")
            self.ui_reset()
        return True

    # UI bits

    def ui_update_new_data(self, data):
        self.notification_active = True
        self.last_update = datetime.datetime.now()
        self.set_from_file(os.path.join(
                os.path.dirname(__file__),
                'icons/updating.png'
            )) 
        self.set_tooltip("Updates in progress to %s" % self.watch)

    def ui_reset(self):
        self.notification_active = False
        self.set_from_file(os.path.join(
                os.path.dirname(__file__),
                'icons/idle.png'
            ))
        self.set_tooltip("No recent changes to %s" % self.watch)

    def ui_notification_out_of_date(self):
        if datetime.datetime.now() > self.last_update + self.UI_UPDATE_DURATION:
            return True
        return False

class FileWatcherProcess(object):
    POLLING_INTERVAL = 0.1 # Seconds

    def __init__(self, path, pipe_in, pipe_out):
        self.path = path
        self.incoming = pipe_in
        self.outgoing = pipe_out

        self.logger = logging.getLogger('FileWatcherProcess')

        self.main();

    def main(self):
        self.logger.debug("Opening process to watch for file data.")
        self.proc = Popen(
            [
                'tail',
                '-f',
                self.path,
            ], 
            shell=False,
            stdout=PIPE,
            bufsize=1, # Line-buffered
        )
        while True:
            self.proc.stdout.flush()
            data = self.proc.stdout.readline().strip()
            if data:
                self.logger.debug("Found data \"%s\"" % data)
                self.notify_changes(data)
            time.sleep(self.POLLING_INTERVAL)

    def notify_changes(self, data):
        self.logger.debug("Sending notification to parent process that %s has changed." % self.path)
        self.outgoing.put(
                (
                    self.path,
                    data
                )
            )

def run_from_cmdline():
    parser = OptionParser()
    parser.add_option('-v', '--verbose', dest='verbose', action='store_true', default=False)
    (opts, args, ) = parser.parse_args()

    logging.basicConfig(
            level=logging.DEBUG if opts.verbose else logging.WARNING
        )

    if len(args) < 1:
        parser.error("You must specify the path to the filename to watch as the first argument.")

    FileWatcher(args[0])
    gtk.main()