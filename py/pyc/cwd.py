#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4 -*-
#
# Simple Clone of Clamd using pyc extension
#
# Copyright (C) 2008-2009 Gianluigi Tiesi <sherpya@netfarm.it>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
# ======================================================================

from asynchat import async_chat
from asyncore import dispatcher, loop
from socket import socket, AF_INET, SOCK_STREAM
from select import select
from sys import stdout, exc_info, exit as sys_exit
from tempfile import mkstemp
from time import time
from os import walk, unlink, write as os_write, close as os_close
from os.path import isfile, isdir, join as path_join
import pyc

class CwdHandler(async_chat):
    def __init__(self, conn, addr, server):
        async_chat.__init__(self, conn)
        self.client_address = addr
        self.connection = conn
        self.server = server
        self.set_terminator ('\n')
        self.found_terminator = self.handle_request_line

    def handle_data(self):
        pass

    def handle_request_line(self):
        pass

    def scanfile(self, filename):
        try:
            infected, virus = pyc.scanFile(filename)
        except:
            t, val, tb = exc_info()
            return None, 'ERROR', val.message
        return True, infected, virus

    def sendreply(self, res, name, infected, virusname):
        try:
            if res is None:
                print '%s: ERROR %s' % (name, virusname)
                self.connection.send('%s: ERROR %s\n' % (name, virusname))
                return False
            if infected:
                print '%s: %s FOUND' % (name, virusname)
                self.connection.send('%s: %s FOUND\n' % (name, virusname))
            else:
                self.connection.send('%s: OK\n' % name)
            return True
        except Exception, error:
            t, val, tb = exc_info()
            print 'Error sending reply', error
            return False

    def scan(self, path, name=None, cont=False):
        if (name is not None):
            res, infected, virusname = self.scanfile(path)
            return self.sendreply(res, name, infected, virusname)
        elif isfile(path):
            res, infected, virusname = self.scanfile(path)
            return self.sendreply(res, path, infected, virusname)
        elif isdir(path):
            for f in walk(path):
                for child in f[2]:
                    filename = path_join(f[0], child)
                    res, infected, virusname = self.scanfile(filename)
                    if not self.sendreply(res, filename, infected, virusname): return
                    if not cont: return
        else:
            self.connection.send('%s: ERROR not a regular file or directory\n' % path)

    def collect_incoming_data(self, cmd):
        client = self.connection.getpeername()
        print 'Connection from:', client[0]
        cmd = cmd.strip()
        if cmd.startswith('SCAN '):
            self.do_SCAN(cmd.split('SCAN ', 1).pop())
        elif cmd == 'QUIT' or cmd == 'SHUTDOWN':
            self.do_QUIT()
        elif cmd == 'RELOAD':
            self.do_RELOAD()
        elif cmd == 'PING':
            self.do_PING()
        elif cmd.startswith('CONTSCAN '):
            self.do_CONTSCAN(cmd.split('CONTSCAN ', 1).pop())
        elif cmd == 'VERSION':
            self.do_VERSION()
        elif cmd == 'SESSION':
            self.do_SESSION(client)
        elif cmd == 'END':
            self.do_END(client)
        elif cmd == 'STREAM':
            self.do_STREAM()
        elif cmd.startswith('MULTISCAN '):
            self.do_MULTISCAN(cmd.split('MULTISCAN ', 1).pop())
        else:
            print 'Unknown command', cmd
            self.connection.send('UNKNOWN COMMAND\n')
        if not client in self.server.sessions: self.close()

    def do_SCAN(self, path):
        self.scan(path)

    def do_QUIT(self):
        print 'Shutdown Requested'
        self.server.close()

    def do_RELOAD(self):
        self.connection.send('RELOADING\n')
        pyc.checkAndLoadDB()

    def do_PING(self):
        self.connection.send('PONG\n')

    def do_CONTSCAN(self, path):
        self.scan(path, cont=True)

    def do_VERSION(self):
        version = pyc.getVersions()[0]
        self.connection.send(version + '\n')

    def do_STREAM(self):
        stream = socket(AF_INET, SOCK_STREAM)
        stream.settimeout(self.server.config['ReadTimeout'])
        stream.bind((self.server.ip, 0))
        stream.listen(1)
        self.connection.send('PORT %d\n' % stream.getsockname()[1])

        try:
            conn, addr = stream.accept()
        except Exception, error:
            print 'Connection aborted', error
            self.connection.send('stream: ERROR %s\n' % error)
            stream.close()
            return

        f, filename = mkstemp()
        start = time()
        ok = True
        bytes = 0
        while True:
            r, w, e = select([conn], [], [], 1)
            now = time()
            if (now - start) > self.server.config['ReadTimeout']:
                print 'Connection Timeout'
                self.connection.send('stream: ERROR timeout\n')
                ok = False
                break
            if r:
                try:
                    d = conn.recv(4096)
                    if not d: break
                    bytes = bytes + len(d)
                    if bytes > self.server.config['StreamMaxLength']:
                        print 'ScanStream: StreamMaxLength reached (max: %s)' % self.server.config['StreamMaxLength']
                        self.connection.send('stream: ERROR StreamMaxLength reached\n')
                        ok = False
                        break
                    os_write(f, d)
                    start = now
                except Exception, error:
                    print 'Error Recv', error
                    self.connection.send('stream: ERROR %s\n' % error)
                    ok = False
                    break
            if e:
                print 'Error select()'
                self.connection.send('stream: Socket ERROR\n')
                ok = False
                break

        conn.close()
        os_close(f)
        stream.close()

        if ok: self.scan(filename, 'stream')

        if not self.server.config['LeaveTemporaryFiles']:
            try:
                unlink(filename)
            except:
                print 'Error unlinking tempfile'

    def do_SESSION(self, client):
        if client in self.server.sessions:
            self.connection.send('ERROR Session already started\n')
        else:
            self.server.sessions.append(client)

    def do_END(self, client):
        if not client in self.server.sessions:
            self.connection.send('ERROR Session not started\n')
        else:
            self.server.sessions.remove(client)

    def do_MULTISCAN(self, filename):
        self.connection.send('ERROR Not implemented\n')

class CwConfig:
    def __init__(self):
        self.config = {}

    def __setitem__(self, name, value):
        self.options[name][self.VALUE] = value

    def __getitem__(self, name):
        return self.options[name][self.VALUE]

    def qstr(value):
        if value[0] == '"' and value[-1] == '"':
            return value[1:-1]
        else:
            return value

    def nqstr(value):
        if value.find(' ') != -1:
            raise Exception, 'Invalid space in value'
        return value

    def boolean(value):
        value = value.lower()
        if value in [ 'true', '1', 'yes' ]:
            return True
        if value in [ 'false', '0', 'no' ]:
            return False
        raise Exception, 'Bad value for boolean'

    def size_t(value):
        try:
            return int(value) # no modifier: bytes
        except:
            pass
        size = value[:-1]
        mod = value[-1].lower()
        if mod == 'k':
            return int(size) * 1024
        elif mod == 'm':
            return int(size) * 1024 * 1024
        else:
            raise Exception, 'Bad Modifier'

    OWNER, NAME, VALIDATOR, VALUE = range(4)
    options = {
        'MaxScanSize'               : [ 'engine', 'max-scansize', size_t, 150 * 1024 * 1024 ], # MB
        'MaxFileSize'               : [ 'engine', 'max-filesize', size_t, 100 * 1024 * 1024 ], # MB
        'MaxRecursion'              : [ 'engine', 'max-recursion', int, 16 ],
        'MaxFiles'                  : [ 'engine', 'max-files', int, 15000 ],
        #'TemporaryDirectory'        : [ 'engine', 'tempdir', qstr, None ],
        'LeaveTemporaryFiles'       : [ 'engine', 'leave-temps', boolean, False ],

        'ScanPE'                    : [ 'scan', 'pe', boolean, True ],
        'ScanELF'                   : [ 'scan', 'elf', boolean, True ],
        'DetectBrokenExecutables'   : [ 'scan', 'blockbroken', boolean, False ],
        'ScanOLE2'                  : [ 'scan', 'ole2', boolean, True ],
        'ScanPDF'                   : [ 'scan', 'pdf', boolean, False ],
        'ScanMail'                  : [ 'scan', 'mail', boolean, True ],
        'ScanHTML'                  : [ 'scan', 'html', boolean, True ],
        'ScanArchive'               : [ 'scan', 'archive', boolean, True ],

        'SelfCheck'                 : [ 'cwd', None, int, 3600 ], # seconds
        'Debug'                     : [ 'cwd', None, boolean, False ],
        'DatabaseDirectory'         : [ 'cwd', None, qstr, None ],
        'TCPSocket'                 : [ 'cwd', None, int, 3310 ],
        'TCPAddr'                   : [ 'cwd', None, nqstr, 'localhost' ],
        'MaxConnectionQueueLength'  : [ 'cwd', None, int, 5 ],
        'StreamMaxLength'           : [ 'cwd', None, size_t, 100 * 1024 * 1024 ], # MB
        'ReadTimeout'               : [ 'cwd', None, int, 300 ] # seconds
    }

    def engage(self):
        if self['DatabaseDirectory'] is not None:
            pyc.setDBPath(self['DatabaseDirectory'])
        if self['Debug']:
            pyc.setDebug()
        pyc.setDBTimer(self['SelfCheck'])

        for option in self.options.keys():
            (owner, name, _, value) = self.options[option]
            if owner == 'engine':
                print 'Setting engine', name, value
                pyc.setEngineOption(name, value)
            elif owner == 'scan':
                print 'Setting scan', name, value
                pyc.setScanOption(name, value)

    def load(self, filename):
        f = open(filename)
        for line in f:
            line = line.strip()
            if (len(line) == 0) or line.startswith('#'):
                continue
            if line.startswith('Example'):
                f.close()
                raise Exception, 'You should edit the default config and remove Example keyword'
            option, value = line.split(' ', 1)

            if option in self.options:
                try:
                    value = self.options[option][self.VALIDATOR](value)
                    self.options[option][self.VALUE] = value
                except Exception, e:
                    print e.message, 'for option', option
                    f.close()
                    raise Exception, 'Invalid configuration'
        f.close()

class CwServer(dispatcher):
    def __init__(self, configfile=None):
        self.handler = CwdHandler
        self.sessions = []
        self.ip = 'localhost'
        self.port = 0
        dispatcher.__init__(self)

        self.config = CwConfig()
        if configfile:
            self.config.load(configfile)
        self.config.engage()

        pyc.loadDB()
        self.startup()

    def startup(self):
        self.create_socket(AF_INET, SOCK_STREAM)
        self.set_reuse_addr()
        self.ip, self.port = self.config['TCPAddr'], self.config['TCPSocket']
        self.bind((self.ip, self.port))
        self.listen(self.config['MaxConnectionQueueLength'])

    def handle_accept(self):
        conn, addr = self.accept()
        self.handler(conn, addr, self)

if __name__ == '__main__':
    s = CwServer('clamd.conf')
    print "Cwd Server running on port %s" % s.port
    try:
        loop(timeout=1)
    except KeyboardInterrupt:
        print "Crtl+C pressed. Shutting down."
