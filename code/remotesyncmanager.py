#!/usr/bin/env python3

import os
import sys
import time
import datetime
import netifaces
import socket
import queue
import threading
import multiprocessing as mp
import multiprocessing.managers as mpm
import pickle
import contextlib
from contextlib import contextmanager


def get_machine_default_gateway_ip():
    """Return the default gateway IP for the machine."""
    # This function [def get_machine_default_gateway_ip():] was borrowed
    # (unmodified) from:
    # https://www.programcreek.com/python/?code=maas%2Fmaas%2Fmaas-master%2Fsrc%2Fprovisioningserver%2Futils%2Fipaddr.py
    # Under the GNU AFFERO GENERAL PUBLIC LICENSE, Version 3, 19 November 2007:
    # https://www.programcreek.com/python/?code=maas%2Fmaas%2Fmaas-master%2FLICENSE
    # or, http://www.gnu.org/licenses/agpl.html

    gateways = netifaces.gateways()
    defaults = gateways.get("default")
    if not defaults:
        return

    def default_ip(family):
        gw_info = defaults.get(family)
        if not gw_info:
            return
        addresses = netifaces.ifaddresses(gw_info[1]).get(family)
        if addresses:
            return addresses[0]["addr"]

    return default_ip(netifaces.AF_INET) or default_ip(netifaces.AF_INET6)

def get_ip():
    """Return the IP of this machine as seen by the default gateway."""
    with contextlib.closing(socket.socket(socket.AF_INET,
                                          socket.SOCK_DGRAM)) as s:
        s.connect((get_machine_default_gateway_ip(), 80))
        return s.getsockname()[0]

def get_free_port():
    """
        Return the next freely available port number.

        Note: the port is released, so could theoretically be used by another
        process before it is effectively used by the caller of this function,
        this is a potential race condition, however ports are generally
        allocated in a cycling fashion, so unless another process has
        hard-coded this particular port number, then chances are extremely slim
        for it to be used before the caller does.
    """
    with contextlib.closing(socket.socket(socket.AF_INET,
                                          socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


class RemoteSyncManager:
    '''
        `class RemoteSyncManager:` provides an easier interface to work with
        multiprocessing.managers.SyncManagers, particularly for use with remote
        processes (i.e. processes started separately or even on different
        machines).

        At initiation the user must provide a filename to store server
        information to be use by the client to connect. It is up to the user to
        find a way to communicate this file to the client processes.

        The other parameter, `namedobjects` is the list of objects to be shared
        and managed between local and remote processes. It is a list of pairs:
        the first intem in the tuple pair is the shared item name, the second is
        the shared item object. For instance, one could want the following:

        (
            ('mynamespace', multiprocessing.managers.Namespace()),
            ('myqueue', queue.Queue()),
            ('mylock', threading.Lock()),
            ('myevent', threading.Event()),
        )

        It is particularly adapted to recognise the types registered with
        SyncManager in the multiprocessing.managers library.

        It should be noted that managed objects do NOT play well within a
        Namespace.

        To use this class, declare an object, associated with a filename and a
        list of named objects, let's call this object `remotesyncmgr`.
        The named objects are used with dot-notation of the local variable
        `remotesyncmgr`, e.g. `remotesyncmgr.myqueue`.
        This local variable can be passed as an argument and used as is in
        processes (multiprocessing.Process) started within the same program.
        For local use, there is no need to start a client instance.

        For use as a remote client, simply declare an object associated with the
        same file contents (it contains amongst others the IP address - which
        will only work if the client is on the same network - this code will
        need to be adapted if intended for work across networks), and no
        `namedobjects` parameter. Let's call this object `syncclient`.
        `syncclient` can then be used just like `remotesyncmgr` across all
        processes started within the same program.
    '''

    class syncmanager(mpm.SyncManager):
        pass

    def __init__(self, serverdatafilename, namedobjects = None):
        # If namedobjects is defined, we start the server side
        # Otherwise we start the client side

        # Classes register with multiprocessing.managers.SyncManager:
        #
        #   'Queue': (
        #       <class 'queue.Queue'>,
        #       None,
        #       None,
        #       <function AutoProxy at 0x7f48934de620>
        #   ),
        #   'JoinableQueue': (
        #       <class 'queue.Queue'>,
        #       None,
        #       None,
        #       <function AutoProxy at 0x7f48934
        #       de620>
        #   ),
        #   'Event': (
        #       <class 'threading.Event'>,
        #       ('is_set', 'set', 'clear', 'wait'),
        #       None,
        #       <class 'multiprocessing.managers.EventProxy'>
        #   ),
        #   'Lock': (
        #       <built-in function allocate_lock>,
        #       ('acquire', 'release'),
        #       None,
        #       <class 'multiprocessing.managers.AcquirerProxy'>
        #   ),
        #   'RLock': (
        #       <function RLock at 0x7f4893db5268>,
        #       ('acquire', 'release'),
        #       None,
        #       <class 'multiprocessing.managers.AcquirerProxy'>
        #   ),
        #   'Semaphore': (
        #       <class 'threading.Semaphore'>,
        #       ('acquire', 'release'),
        #       None,
        #       <class 'multiprocessing.managers.AcquirerProxy'>
        #   ),
        #   'BoundedSemaphore': (
        #       <class 'threading.BoundedSemaphore'>,
        #       ('acquire', 'release'),
        #       None,
        #       <class 'multiprocessing.managers.AcquirerProxy'>
        #   ),
        #   'Condition': (
        #       <class 'threading.Condition'>,
        #       ('acquire', 'release', 'wait', 'notify', 'notify_all'),
        #       None,
        #       <class 'multiprocessing.managers.ConditionProxy'>
        #   ),
        #   'Barrier': (
        #       <class 'threading.Barrier'>,
        #       ('__getattribute__', 'wait', 'abort', 'reset'),
        #       None,
        #       <class 'multiprocessing.managers.BarrierProxy'>
        #   ),
        #   'Pool': (
        #       <class 'multiprocessing.pool.Pool'>,
        #       ('apply', 'apply_async', 'close', 'imap', 'imap_unordered',
        #        'join', 'map', 'map_async', 'starmap', 'starmap_async',
        #        'terminate'),
        #       {'apply_async': 'AsyncResult', 'map_async': 'AsyncResult',
        #        'starmap_async': 'AsyncResult', 'imap': 'Iterator',
        #        'imap_unordered': 'Iterator'},
        #       <class 'multiprocessing.managers.PoolProxy'>
        #   ),
        #   'list': (
        #       <class 'list'>,
        #       ('__add__', '__contains__', '__delitem__', '__getitem__',
        #        '__len__', '__mul__', '__reversed__', '__rmul__',
        #        '__setitem__', 'append', 'count', 'extend', 'index', 'insert',
        #        'pop', 'remove', 'reverse', 'sort', '__imul__'),
        #       None,
        #       <class 'multiprocessing.managers.ListProxy'>
        #   ),
        #   'dict': (
        #       <class 'dict'>,
        #       ('__contains__', '__delitem__', '__getitem__', '__iter__',
        #        '__len__', '__setitem__', 'clear', 'copy', 'get', 'has_key',
        #        'items', 'keys', 'pop', 'popitem', 'setdefault', 'update',
        #        'values'),
        #       {'__iter__': 'Iterator'},
        #       <class 'multiprocessing.managers.DictProxy'>
        #   ),
        #   'Value': (
        #       <class 'multiprocessing.managers.Value'>,
        #       ('get', 'set'),
        #       None,
        #       <class 'multiprocessing.managers.ValueProxy'>
        #   ),
        #   'Array': (
        #       <function Array at 0x7f48934de6a8>,
        #       ('__len__', '__getitem__', '__setitem__'),
        #       None,
        #       <class 'multiprocessing.managers.ArrayProxy'>
        #   ),
        #   'Namespace': (
        #       <class 'multiprocessing.managers.Namespace'>,
        #       ('__getattribute__', '__setattr__', '__delattr__'),
        #       None,
        #       <class 'multiprocessing.managers.NamespaceProxy'>
        #   ),
        #   'Iterator': (
        #       None,
        #       ('__next__', 'send', 'throw', 'close'),
        #       None,
        #       <class 'multiprocessing.managers.IteratorProxy'>
        #   ),
        #   'AsyncResult': (
        #       None,
        #       None,
        #       None,
        #       <function AutoProxy at 0x7f48934de620>
        #   )

        # Define a callable that returns the value of obj when retobj is called
        # Note: placing the lambda function in the callable parameter of the
        # registry function resolves that oobject when the lambda function gets
        # called, i.e. when the server is started, at that point, obj contains
        # something possibly irrelevant, causing a lot of confusion.
        def retobj(obj):
            return lambda: obj

        # The class `ContextWrap` is used to wrap the LockProxy object because
        # it does not provide the context handling, at least not in python 3.6.
        # I could have patched it, but I preferred a wrapper as a quick fix.
        # This class works hand in hand with the dictionary `contextwrapmap`
        # which matches the object type with the `__entry__` and `__exit__`
        # context functions. Matching objects are stored in the `contextwrap`
        # dictionary.
        class ContextWrap:
            def __init__(self, obj, enter, exit):
                self.__enter = getattr(obj, enter)
                self.__exit = getattr(obj, exit)
            def __enter__(self):
                self.__enter()
            def __exit__(self, typ, val, tb):
                self.__exit()

        # `proxymap` is used to automatically identify the right proxy to each
        # named object.
        proxymap = {}
        for obj, objprops in self.syncmanager._registry.items():
            if objprops[0]:
                proxymap[objprops[0]] = objprops[3]

        # `exposedmap` is presently unused, it was an attempt to publish the
        # missing Lock attributes in the proxy, but clearly based on an
        # incorrect understanding of Lock proxies.
        # I kept this, however in case it may become useful.
        exposedmap = {
            # type(threading.Lock()):
            # ('acquire', 'release', '__enter__', '__exit__'),
            # does not work with the lock, may be useful some day?
        }

        # `attributesmap` was another attempt to make context managers
        # work for Locks, again based on an incorrect understanding of how
        # Locks and context managers were programmed.
        # As it maps an attribute to another, I thought I would keep this
        # since it is such a simple mechanism and it may become useful.
        attributesmap = {
            # type(threading.Lock()):
            # (('__enter__', 'acquire'), ('__exit__', 'release')),
            # does not work with the lock, may be useful some day?
        }

        # See note with `ContextWrap` above.
        contextwrapmap = {
            type(threading.Lock()): ('acquire', 'release'),
        }

        # The `formatmap` is used to identify those namedobjects which
        # require special handling by __str__, to provide detailed
        # information about certain objects.
        formatmap = {
            queue.Queue:      'queue',
            threading.Event:  'event',
        }

        self.attributesmapping = {}
        self.contextwrap = {}
        self.formats = {}

        if namedobjects:
            self.clientobjects = []

            for objdesc in namedobjects:
                if len(objdesc) == 2:
                    (name, obj) = objdesc

                    objtype = type(obj)
                    if objtype in attributesmap:
                        self.attributesmapping[name] = attributesmap[objtype]
                    if objtype in contextwrapmap:
                        self.contextwrap[name] = contextwrapmap[objtype]
                    if objtype in formatmap:
                        self.formats[name] = formatmap[objtype]

                    if objtype in proxymap:
                        proxytype = proxymap[objtype]
                        if objtype in exposedmap:
                            exposed = exposedmap[objtype]
                            self.clientobjects.append(
                                (name, proxytype, exposed)
                            )
                            self.syncmanager.register(
                                'get_' + name, callable=retobj(obj),
                                proxytype=proxytype,
                                exposed=exposed
                            )
                        else:
                            self.clientobjects.append((name, proxytype))
                            self.syncmanager.register('get_' + name, callable=retobj(obj), proxytype=proxytype)
                    else:
                        self.clientobjects.append((name,))
                        self.syncmanager.register('get_' + name, callable=retobj(obj))
                elif len(objdesc) == 3:
                    (name, obj, proxytype) = objdesc
                    objtype = type(obj)
                    if objtype in attributesmap:
                        self.attributesmapping[name] = attributesmap[objtype]
                    if objtype in contextwrapmap:
                        self.contextwrap[name] = contextwrapmap[objtype]

                    self.clientobjects.append((name, proxytype))
                    self.syncmanager.register('get_' + name, callable=retobj(obj), proxytype=proxytype)

            newportnumber = get_free_port()
            self.serverdata = {'address': (get_ip(), newportnumber), 'authkey': b'mptest'}
            with open(serverdatafilename, 'wb') as serverdata_file:
                pickle.dump((self.serverdata, self.clientobjects, self.attributesmapping, self.contextwrap, self.formats), serverdata_file, pickle.HIGHEST_PROTOCOL)

            serverdata = self.serverdata
            serverdata['address'] = ('', newportnumber)
            self.server = self.syncmanager(**serverdata)
            self.server.start()

            for objdesc in self.clientobjects:
                name = objdesc[0]

                if name in self.contextwrap:
                    setattr(self, '__context_wrapped__'+name, getattr(self.server, 'get_' + name)())
                    setattr(self, name, ContextWrap(
                        getattr(self, '__context_wrapped__'+name),
                        self.contextwrap[name][0],
                        self.contextwrap[name][1],
                    ))

                else:
                    setattr(self, name, getattr(self.server, 'get_' + name)())

                    if name in self.attributesmapping:
                        obj = getattr(self, name)
                        for pair in self.attributesmapping[name]:
                            setattr(obj, pair[0], getattr(obj, pair[1]))

        else:
            with open(serverdatafilename, 'rb') as serverdata_file:
                (self.serverdata, self.clientobjects, self.attributesmapping, self.contextwrap, self.formats) = pickle.load(serverdata_file)

            for objdesc in self.clientobjects:
                if len(objdesc) == 1:
                    (name,) = objdesc
                    self.syncmanager.register('get_' + name)
                elif len(objdesc) == 2:
                    (name, proxytype) = objdesc
                    self.syncmanager.register('get_' + name, proxytype=proxytype)
                elif len(objdesc) == 3:
                    (name, proxytype, exposed) = objdesc
                    self.syncmanager.register('get_' + name, proxytype=proxytype, exposed=exposed)

            self.client = self.syncmanager(**self.serverdata)
            self.client.connect()

            for objdesc in self.clientobjects:
                name = objdesc[0]

                if name in self.contextwrap:
                    setattr(self, '__context_wrapped__'+name, getattr(self.client, 'get_' + name)())
                    setattr(self, name, ContextWrap(
                        getattr(self, '__context_wrapped__'+name),
                        self.contextwrap[name][0],
                        self.contextwrap[name][1],
                    ))

                else:
                    setattr(self, name, getattr(self.client, 'get_' + name)())

                    if name in self.attributesmapping:
                        obj = getattr(self, name)
                        for pair in self.attributesmapping[name]:
                            setattr(obj, pair[0], getattr(obj, pair[1]))

    def __str__(self):
        S = []
        for objdesc in self.clientobjects:
            name = objdesc[0]
            obj = getattr(self, name)
            if name in self.formats:
                strformat = self.formats[name]
                if strformat == 'queue':
                    S.append(f'{name}: {obj} ' + ('E' if obj.empty() else (f'{obj.qsize()}' + ('F' if obj.full() else ''))))
                if strformat == 'event':
                    S.append(f'{name}: {obj} is_set={obj.is_set()}')
            else:
                S.append(f'{name}: {obj}')
        return '\n'.join(S)

# vim: se ai ts=2 expandtab sw=2 tw=80 :
