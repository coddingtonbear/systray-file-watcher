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
from subprocess import Popen, PIPE
import time

import gtk
import gnomeapplet
import gobject
import pygtk

class FileWatcher(gnomeapplet.Applet):
    UI_UPDATE_DURATION = datetime.timedelta(seconds = 2)
    INTERVAL = 100 # Milliseconds!

    def __init__(self, applet, iid):
        self.logger = logging.getLogger('FileWatcher')
        self.logger.debug("Initializing...")

        self.applet = applet
        self.iid = iid

        self.label = gtk.Label("...")
        self.applet.add(self.label)
        self.applet.show_all()
    
        self.notification_active = False
        self.last_update = datetime.datetime(2000, 1, 1)

        self.procs = {}

        self.from_tail = Queue()
        self.to_tail = Queue()

        self.main()

    def main(self):
        for path in self.get_files_to_watch():
            self.watch_file(path)
        gobject.timeout_add(self.INTERVAL, self.check_for_notifications)
        self.ui_reset()
        self.logger.info("Started.")

    def get_files_to_watch(self):
        return [
                "/tmp/lsyncd.log"
            ]

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
        self.label.set_markup("<span foreground='#FF5500'>RW</span>")
        self.applet.show_all()

    def ui_reset(self):
        self.notification_active = False
        self.label.set_markup("<span foreground='#FF0000'></span>")
        self.applet.show_all()

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

def file_watcher_factory(applet, iid):
    try:
        FileWatcher(applet, iid)
    except Exception as e:
        logging.exception(e)
    return gtk.TRUE

pygtk.require('2.0')

gobject.type_register(FileWatcher)

logging.basicConfig(
        filename=os.path.expanduser("~/.file_watcher.log"),
        level=logging.DEBUG
    )

if __name__ == "__main__":
    logging.info("Starting via BonoboFactory.")
    gnomeapplet.bonobo_factory(
            "OAFIID:FileWatcher_Factory",
            FileWatcher.__gtype__,
            "hello",
            "0",
           file_watcher_factory 
        )
