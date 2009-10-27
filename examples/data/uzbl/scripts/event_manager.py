#!/usr/bin/env python

# Event Manager for Uzbl
# Copyright (c) 2009, Mason Larobina <mason.larobina@gmail.com>
# Copyright (c) 2009, Dieter Plaetinck <dieter@plaetinck.be>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''

E V E N T _ M A N A G E R . P Y
===============================

Event manager for uzbl written in python.

'''

import imp
import os
import sys
import re
import types
import socket
import pprint
import time
import atexit
from select import select
from signal import signal, SIGTERM
from optparse import OptionParser
from traceback import print_exc


# ============================================================================
# ::: Default configuration section ::::::::::::::::::::::::::::::::::::::::::
# ============================================================================

# Automagically set during `make install`
PREFIX = None

# Check if PREFIX not set and set to default /usr/local/
if not PREFIX:
    PREFIX = '/usr/local/'

def xdghome(key, default):
    '''Attempts to use the environ XDG_*_HOME paths if they exist otherwise
    use $HOME and the default path.'''

    xdgkey = "XDG_%s_HOME" % key
    if xdgkey in os.environ.keys() and os.environ[xdgkey]:
        return os.environ[xdgkey]

    return os.path.join(os.environ['HOME'], default)

# Setup xdg paths.
DATA_DIR = os.path.join(xdghome('DATA', '.local/share/'), 'uzbl/')
CACHE_DIR = os.path.join(xdghome('CACHE', '.cache/'), 'uzbl/')


# Config dict (NOT the same as the uzbl.config).
config = {
    'verbose':         False,
    'daemon_mode':     True,
    'auto_close':      False,

    'plugins_load':    [],
    'plugins_ignore':  [],

    'plugin_dirs':     [os.path.join(DATA_DIR, 'plugins/'),
        os.path.join(PREFIX, 'share/uzbl/examples/data/uzbl/plugins/')],

    'server_socket':   os.path.join(CACHE_DIR, 'event_daemon'),
    'pid_file':        os.path.join(CACHE_DIR, 'event_daemon.pid'),
}


# ============================================================================
# ::: End of configuration section :::::::::::::::::::::::::::::::::::::::::::
# ============================================================================


# Define some globals.
_SCRIPTNAME = os.path.basename(sys.argv[0])
_RE_FINDSPACES = re.compile("\s+")

def echo(msg):
    '''Prints only if the verbose flag has been set.'''

    if config['verbose']:
        sys.stdout.write("%s: %s\n" % (_SCRIPTNAME, msg))


def error(msg):
    '''Prints error messages to stderr.'''

    sys.stderr.write("%s: error: %s\n" % (_SCRIPTNAME, msg))


def counter():
    '''Generate unique object id's.'''

    i = 0
    while True:
        i += 1
        yield i


def iscallable(obj):
    '''Return true if the object is callable.'''

    return hasattr(obj, "__call__")


def isiterable(obj):
    '''Return true if you can iterate over the item.'''

    return hasattr(obj, "__iter__")


def find_plugins(plugin_dirs):
    '''Find all event manager plugins in the plugin dirs and return a
    dictionary of {'plugin-name.py': '/full/path/to/plugin-name.py', ...}'''

    plugins = {}

    for plugin_dir in plugin_dirs:
        plugin_dir = os.path.realpath(os.path.expandvars(plugin_dir))
        if not os.path.isdir(plugin_dir):
            continue

        for file in os.listdir(plugin_dir):
            if not file.lower().endswith('.py'):
                continue

            path = os.path.join(plugin_dir, file)
            if not os.path.isfile(path):
                continue

            if file not in plugins:
                plugins[file] = plugin_dir

    return plugins


def load_plugins(plugin_dirs, load=[], ignore=[]):
    '''Load event manager plugins found in the plugin_dirs.'''

    # Find the plugins in the plugin_dirs.
    found = find_plugins(plugin_dirs)

    if load:
        # Ignore anything not in the load list.
        for plugin in found.keys():
            if plugin not in load:
                del found[plugin]

    if ignore:
        # Ignore anything in the ignore list.
        for plugin in found.keys():
            if plugin in ignore:
                del found[plugin]

    # Print plugin list to be loaded.
    pprint.pprint(found)

    loaded = {}
    # Load all found plugins into the loaded dict.
    for (filename, dir) in found.items():
        name = filename[:-3]
        info = imp.find_module(name, [dir,])
        plugin = imp.load_module(name, *info)
        loaded[(dir, filename)] = plugin

    return loaded


def daemonize():
    '''Daemonize the process using the Stevens' double-fork magic.'''

    try:
        if os.fork():
            os._exit(0)

    except OSError:
        print_exc()
        sys.stderr.write("fork #1 failed")
        sys.exit(1)

    os.chdir('/')
    os.setsid()
    os.umask(0)

    try:
        if os.fork():
            os._exit(0)

    except OSError:
        print_exc()
        sys.stderr.write("fork #2 failed")
        sys.exit(1)

    sys.stdout.flush()
    sys.stderr.flush()

    devnull = '/dev/null'
    stdin = file(devnull, 'r')
    stdout = file(devnull, 'a+')
    stderr = file(devnull, 'a+', 0)

    os.dup2(stdin.fileno(), sys.stdin.fileno())
    os.dup2(stdout.fileno(), sys.stdout.fileno())
    os.dup2(stderr.fileno(), sys.stderr.fileno())


def make_dirs(path):
    '''Make all basedirs recursively as required.'''

    dirname = os.path.dirname(path)
    if not os.path.isdir(dirname):
        os.makedirs(dirname)


def make_pid_file(pid_file):
    '''Make pid file at given pid_file location.'''

    make_dirs(pid_file)
    file = open(pid_file, 'w')
    file.write('%d' % os.getpid())
    file.close()


def del_pid_file(pid_file):
    '''Delete pid file at given pid_file location.'''

    if os.path.isfile(pid_file):
        os.remove(pid_file)


def get_pid(pid_file):
    '''Read pid from pid_file.'''

    try:
        file = open(pid_file, 'r')
        strpid = file.read()
        file.close()
        pid = int(strpid.strip())
        return pid

    except:
        print_exc()
        return None


def pid_running(pid):
    '''Returns True if a process with the given pid is running.'''

    try:
        os.kill(pid, 0)

    except OSError:
        return False

    else:
        return True


def term_process(pid):
    '''Send a SIGTERM signal to the process with the given pid.'''

    if not pid_running(pid):
        return False

    os.kill(pid, SIGTERM)

    start = time.time()
    while True:
        if not pid_running(pid):
            return True

        if time.time() - start > 5:
            raise OSError('failed to stop process with pid: %d' % pid)

        time.sleep(0.25)


def prepender(function, *pre_args):
    '''Creates a wrapper around a callable object injecting a list of
    arguments before the called arguments.'''

    locals = (function, pre_args)
    def _prepender(*args, **kargs):
        (function, pre_args) = locals
        return function(*(pre_args + args), **kargs)

    return _prepender


class EventHandler(object):

    nexthid = counter().next

    def __init__(self, event, handler, *args, **kargs):
        if not iscallable(handler):
            raise ArgumentError("EventHandler object requires a callable "
                "object function for the handler argument not: %r" % handler)

        self.function = handler
        self.args = args
        self.kargs = kargs
        self.event = event
        self.hid = self.nexthid()


    def __repr__(self):
        args = ["event=%s" % self.event, "hid=%d" % self.hid,
            "function=%r" % self.function]

        if self.args:
            args.append("args=%r" % self.args)

        if self.kargs:
            args.append("kargs=%r" % self.kargs)

        return "<EventHandler(%s)>" % ', '.join(args)


class UzblInstance(object):
    def __init__(self, parent, client_socket):

        # Internal variables.
        self._exports = {}
        self._handlers = {}
        self._parent = parent
        self._client_socket = client_socket

        self.buffer = ''

        # Call the init() function in every plugin. Inside the init function
        # is where the plugins insert the hooks into the event system.
        self._init_plugins()


    def __getattribute__(self, attr):
        '''Expose any exported functions before class functions.'''

        if not attr.startswith('_'):
            exports = object.__getattribute__(self, '_exports')
            if attr in exports:
                return exports[attr]

        return object.__getattribute__(self, attr)


    def _init_plugins(self):
        '''Call the init() function in every plugin and expose all exposable
        functions in the plugins root namespace.'''

        plugins = self._parent['plugins']

        # Map all plugin exports
        for (name, plugin) in plugins.items():
            if not hasattr(plugin, '__export__'):
                continue

            for export in plugin.__export__:
                if export in self._exports:
                    raise KeyError("conflicting export: %r" % export)

                obj = getattr(plugin, export)
                if iscallable(obj):
                    obj = prepender(obj, self)

                self._exports[export] = obj

        echo("exposed attribute(s): %s" % ', '.join(self._exports.keys()))

        # Now call the init function in all plugins.
        for (name, plugin) in plugins.items():
            try:
                plugin.init(self)

            except:
                #print_exc()
                raise


    def send(self, msg):
        '''Send a command to the uzbl instance via the socket file.'''

        if self._client_socket:
            print '<-- %s' % msg
            self._client_socket.send(("%s\n" % msg).encode('utf-8'))

        else:
            print '!-- %s' % msg


    def connect(self, event, handler, *args, **kargs):
        '''Connect event with handler and return the newly created handler.
        Handlers can either be a function or a uzbl command string.'''

        if event not in self._handlers.keys():
            self._handlers[event] = []

        handlerobj = EventHandler(event, handler, *args, **kargs)
        self._handlers[event].append(handlerobj)
        print handlerobj


    def connect_dict(self, connect_dict):
        '''Connect a dictionary comprising of {"EVENT_NAME": handler, ..} to
        the event handler stack.

        If you need to supply args or kargs to an event use the normal connect
        function.'''

        for (event, handler) in connect_dict.items():
            self.connect(event, handler)


    def remove_by_id(self, hid):
        '''Remove connected event handler by unique handler id.'''

        for (event, handlers) in self._handlers.items():
            for handler in list(handlers):
                if hid != handler.hid:
                    continue

                echo("removed %r" % handler)
                handlers.remove(handler)
                return

        echo('unable to find & remove handler with id: %d' % handler.hid)


    def remove(self, handler):
        '''Remove connected event handler.'''

        for (event, handlers) in self._handlers.items():
            if handler in handlers:
                echo("removed %r" % handler)
                handlers.remove(handler)
                return

        echo('unable to find & remove handler: %r' % handler)


    def exec_handler(self, handler, *args, **kargs):
        '''Execute event handler function.'''

        args += handler.args
        kargs = dict(handler.kargs.items()+kargs.items())
        handler.function(self, *args, **kargs)


    def event(self, event, *args, **kargs):
        '''Raise a custom event.'''

        # Silence _printing_ of geo events while debugging.
        if event != "GEOMETRY_CHANGED":
            print "--> %s %s %s" % (event, args, '' if not kargs else kargs)

        if event not in self._handlers:
            return

        for handler in self._handlers[event]:
            try:
                self.exec_handler(handler, *args, **kargs)

            except:
                print_exc()


    def close(self):
        '''Close the client socket and clean up.'''

        try:
            self._client_socket.close()

        except:
            pass

        for (name, plugin) in self._parent['plugins'].items():
            if hasattr(plugin, 'cleanup'):
                plugin.cleanup(self)

        del self._exports
        del self._handlers
        del self._client_socket


class UzblEventDaemon(dict):
    def __init__(self):

        # Init variables and dict keys.
        dict.__init__(self, {'uzbls': {}})
        self.running = None
        self.server_socket = None
        self.socket_location = None

        # Register that the event daemon server has started by creating the
        # pid file.
        make_pid_file(config['pid_file'])

        # Register a function to clean up the socket and pid file on exit.
        atexit.register(self.quit)

        # Make SIGTERM act orderly.
        signal(SIGTERM, lambda signum, stack_frame: sys.exit(1))

        # Load plugins, first-build of the plugins may be a costly operation.
        self['plugins'] = load_plugins(config['plugin_dirs'],
            config['plugins_load'], config['plugins_ignore'])


    def _create_server_socket(self):
        '''Create the event manager daemon socket for uzbl instance duplex
        communication.'''

        server_socket = config['server_socket']
        server_socket = os.path.realpath(os.path.expandvars(server_socket))
        self.socket_location = server_socket

        # Delete socket if it exists.
        if os.path.exists(server_socket):
            os.remove(server_socket)

        self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server_socket.bind(server_socket)
        self.server_socket.listen(5)


    def _close_server_socket(self):
        '''Close and delete the server socket.'''

        try:
            self.server_socket.close()
            self.server_socket = None

            if os.path.exists(self.socket_location):
                os.remove(self.socket_location)

        except:
            pass


    def run(self):
        '''Main event daemon loop.'''

        if config['daemon_mode']:
            echo('entering daemon mode.')
            daemonize()
            # The pid has changed so update the pid file.
            make_pid_file(config['pid_file'])

        # Create event daemon socket.
        self._create_server_socket()
        echo('listening on: %s' % self.socket_location)

        # Now listen for incoming connections and or data.
        self.listen()

        # Clean up.
        self.quit()


    def listen(self):
        '''Accept incoming connections and constantly poll instance sockets
        for incoming data.'''

        self.running = True
        while self.running:

            sockets = [self.server_socket,] + self['uzbls'].keys()

            read, _, error = select(sockets, [], sockets, 1)

            if self.server_socket in read:
                self.accept_connection()
                read.remove(self.server_socket)

            for client in read:
                self.read_socket(client)

            for client in error:
                error('Unknown error on socket: %r' % client)
                self.close_connection(client)


    def read_socket(self, client):
        '''Read data from an instance socket and pass to the uzbl objects
        event handler function.'''

        try:
            uzbl = self['uzbls'][client]
            try:
                raw = unicode(client.recv(8192), 'utf-8', 'ignore')

            except:
                print_exc()
                raw = None

            if not raw:
                # Read null byte, close socket.
                return self.close_connection(client)

            uzbl.buffer += raw
            msgs = uzbl.buffer.split('\n')
            uzbl.buffer = msgs.pop()

            for msg in msgs:
                self.parse_msg(uzbl, msg)

        except:
            raise


    def parse_msg(self, uzbl, msg):
        '''Parse an incoming msg from a uzbl instance. All non-event messages
        will be printed here and not be passed to the uzbl instance event
        handler function.'''

        msg = msg.strip()
        if not msg:
            return

        cmd = _RE_FINDSPACES.split(msg, 3)
        if not cmd or cmd[0] != 'EVENT':
            # Not an event message.
            print '---', msg
            return

        if len(cmd) < 4:
            cmd.append('')

        event, args = cmd[2], cmd[3]

        try:
            uzbl.event(event, args)

        except:
            print_exc()


    def accept_connection(self):
        '''Accept incoming connection to the server socket.'''

        client_socket = self.server_socket.accept()[0]

        uzbl = UzblInstance(self, client_socket)
        self['uzbls'][client_socket] = uzbl


    def close_connection(self, client):
        '''Clean up after instance close.'''

        try:
            if client in self['uzbls']:
                uzbl = self['uzbls'][client]
                uzbl.close()
                del self['uzbls'][client]

        except:
            print_exc()

        if not len(self['uzbls']) and config['auto_close']:
            echo('auto closing event manager.')
            self.running = False


    def quit(self):
        '''Close all instance socket objects, server socket and delete the
        pid file.'''

        echo('shutting down event manager.')

        for client in self['uzbls'].keys():
            self.close_connection(client)

        echo('unlinking: %r' % self.socket_location)
        self._close_server_socket()

        echo('deleting pid file: %r' % config['pid_file'])
        del_pid_file(config['pid_file'])


def stop():
    '''Stop the event manager daemon.'''

    pid_file = config['pid_file']
    if not os.path.isfile(pid_file):
        return echo('no running daemon found.')

    echo('found pid file: %r' % pid_file)
    pid = get_pid(pid_file)
    if not pid_running(pid):
        echo('no process with pid: %d' % pid)
        return os.remove(pid_file)

    echo("terminating process with pid: %d" % pid)
    term_process(pid)
    if os.path.isfile(pid_file):
        os.remove(pid_file)

    echo('stopped event daemon.')


def start():
    '''Start the event manager daemon.'''

    pid_file = config['pid_file']
    if os.path.isfile(pid_file):
        echo('found pid file: %r' % pid_file)
        pid = get_pid(pid_file)
        if pid_running(pid):
            return echo('event daemon already started with pid: %d' % pid)

        echo('no process with pid: %d' % pid)
        os.remove(pid_file)

    echo('starting event manager.')
    UzblEventDaemon().run()


def restart():
    '''Restart the event manager daemon.'''

    echo('restarting event manager daemon.')
    stop()
    start()


def list_plugins():
    '''List all the plugins being loaded by the event daemon.'''

    plugins = find_plugins(config['plugin_dirs'])
    dirs = {}

    for (plugin, dir) in plugins.items():
        if dir not in dirs:
            dirs[dir] = []

        dirs[dir].append(plugin)

    for (index, (dir, plugin_list)) in enumerate(sorted(dirs.items())):
        if index:
            print

        print "%s:" % dir
        for plugin in sorted(plugin_list):
            print "    %s" % plugin


if __name__ == "__main__":
    usage = "usage: %prog [options] {start|stop|restart|list}"
    parser = OptionParser(usage=usage)
    parser.add_option('-v', '--verbose', dest='verbose', action="store_true",
      help="print verbose output.")

    parser.add_option('-d', '--plugin-dirs', dest='plugin_dirs', action="store",
      metavar="DIRS", help="Specify plugin directories in the form of "\
      "'dir1:dir2:dir3'.")

    parser.add_option('-l', '--load-plugins', dest="load", action="store",
      metavar="PLUGINS", help="comma separated list of plugins to load")

    parser.add_option('-i', '--ignore-plugins', dest="ignore", action="store",
      metavar="PLUGINS", help="comma separated list of plugins to ignore")

    parser.add_option('-p', '--pid-file', dest='pid', action='store',
      metavar='FILE', help="specify pid file location")

    parser.add_option('-s', '--server-socket', dest='socket', action='store',
      metavar='SOCKET', help="specify the daemon socket location")

    parser.add_option('-n', '--no-daemon', dest="daemon",
      action="store_true", help="don't enter daemon mode.")

    parser.add_option('-a', '--auto-close', dest='autoclose',
      action='store_true', help='auto close after all instances disconnect.')

    (options, args) = parser.parse_args()

    # init like {start|stop|..} daemon control section.
    daemon_controls = {'start': start, 'stop': stop, 'restart': restart,
        'list': list_plugins}

    if len(args) == 1:
        action = args[0]
        if action not in daemon_controls:
            error('unknown action: %r' % action)
            sys.exit(1)

    elif len(args) > 1:
        error("too many arguments: %r" % args)
        sys.exit(1)

    else:
        action = 'start'

    # parse other flags & options.
    if options.verbose:
        config['verbose'] = True

    if options.plugin_dirs:
        plugin_dirs = map(str.strip, options.plugin_dirs.split(':'))
        config['plugin_dirs'] = plugin_dirs
        echo("plugin search dirs: %r" % plugin_dirs)

    if options.load and options.ignore:
        error("you can't load and ignore at the same time.")
        sys.exit(1)

    elif options.load:
        plugins_load = config['plugins_load']
        for plugin in options.load.split(','):
            if plugin.strip():
                plugins_load.append(plugin.strip())

        echo('only loading plugin(s): %s' % ', '.join(plugins_load))

    elif options.ignore:
        plugins_ignore = config['plugins_ignore']
        for plugin in options.ignore.split(','):
            if plugin.strip():
                plugins_ignore.append(plugin.strip())

        echo('ignoring plugin(s): %s' % ', '.join(plugins_ignore))

    if options.autoclose:
        config['auto_close'] = True
        echo('will auto close.')

    if options.pid:
        config['pid_file'] = options.pid
        echo("pid file location: %r" % config['pid_file'])

    if options.socket:
        config['server_socket'] = options.socket
        echo("daemon socket location: %s" % config['server_socket'])

    if options.daemon:
        config['daemon_mode'] = False

    # Now {start|stop|...}
    daemon_controls[action]()
