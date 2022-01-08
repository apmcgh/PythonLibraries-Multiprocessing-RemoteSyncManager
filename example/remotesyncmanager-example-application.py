#!/usr/bin/env python3

import sys
import time
import datetime
import code
import queue
import threading
import multiprocessing as mp
import multiprocessing.managers as mpm
import remotesyncmanager as rsm


def ProcA(name, RS):
    with RS.lo:
        print('=======================')
        print(name)
        print(RS)
        RS.vi.value += 1234
        RS.vf.value += 3.1415926535
        RS.di[name] = 'start'
        RS.vb.value = False
        print(name)
        print(RS)
        sys.stdout.flush()

    RS.ev.wait()
    RS.ev.clear()
    RS.q1.put(f'message from {name}.')

    RS.ev.wait()
    with RS.lo:
        RS.ev.clear()
        print('=======================')
        print(name)
        print(RS)
        sys.stdout.flush()

    print(RS.q3.get())
    time.sleep(0.7)
    while not RS.q3.empty():
        print(RS.q3.get())
        time.sleep(0.7)

def ProcB(name, RS):
    with RS.lo:
        print('=======================')
        print(name)
        print(RS)
        RS.vi.value += 4321
        RS.vf.value = RS.vf.value * RS.vi.value
        RS.di[name] = 'start'
        RS.vb.value = False
        print(name)
        print(RS)
        sys.stdout.flush()

    RS.ev.set()
    print(RS.q1.get())

    RS.ev.set()
    with RS.lo:
        print('=======================')
        print(name)
        print(RS)
        sys.stdout.flush()

    for n in range(10):
        print('Enqueuing message', n, '...', end='')
        RS.q3.put(f'message {n} from {name}.')
        print('Enqueued')


if __name__ == '__main__':
    if sys.argv[1] == 'server' and len(sys.argv) == 2:
        RemoteSync = rsm.RemoteSyncManager('mpSERVERDATA.pkl', b'testpw123$%^', (
            ('ns', mpm.Namespace()),
            ('q1', queue.Queue(1)),
            ('q2', queue.Queue(1)),
            ('q3', queue.Queue(4)),
            ('lo', threading.Lock()),
            ('ev', threading.Event()),
            ('di', dict()),
            ('vi', mpm.Value(int, 88)),
            ('vf', mpm.Value(float, 5.67)),
            ('vb', mpm.Value(bool, True)),
        ))
        '''
        {
            'Queue': (<class 'queue.Queue'>, None, None, <function AutoProxy at 0x7f48934de620>),
            'JoinableQueue': (<class 'queue.Queue'>, None, None, <function AutoProxy at 0x7f48934de620>),
            'Event': (<class 'threading.Event'>, ('is_set', 'set', 'clear', 'wait'), None, <class 'multiprocessing.managers.EventProxy'>),
            'Lock': (<built-in function allocate_lock>, ('acquire', 'release'), None, <class 'multiprocessing.managers.AcquirerProxy'>),
            'RLock': (<function RLock at 0x7f4893db5268>, ('acquire', 'release'), None, <class 'multiprocessing.managers.AcquirerProxy'>),
            'Semaphore': (<class 'threading.Semaphore'>, ('acquire', 'release'), None, <class 'multiprocessing.managers.AcquirerProxy'>),
            'BoundedSemaphore': (<class 'threading.BoundedSemaphore'>, ('acquire', 'release'), None, <class 'multiprocessing.managers.AcquirerProxy'>),
            'Condition': (<class 'threading.Condition'>, ('acquire', 'release', 'wait', 'notify', 'notify_all'), None, <class 'multiprocessing.managers.ConditionProxy'>),
            'Barrier': (<class 'threading.Barrier'>, ('__getattribute__', 'wait', 'abort', 'reset'), None, <class 'multiprocessing.managers.BarrierProxy'>),
            'Pool': (<class 'multiprocessing.pool.Pool'>, ('apply', 'apply_async', 'close', 'imap', 'imap_unordered', 'join', 'map', 'map_async', 'starmap', 'starmap_async', 'terminate'), {'apply_async': 'AsyncResult', 'map_async': 'AsyncResult', 'starmap_async': 'AsyncResult', 'imap': 'Iterator', 'imap_unordered': 'Iterator'}, <class 'multiprocessing.managers.PoolProxy'>),
            'list': (<class 'list'>, ('__add__', '__contains__', '__delitem__', '__getitem__', '__len__', '__mul__', '__reversed__', '__rmul__', '__setitem__', 'append', 'count', 'extend', 'index', 'insert', 'pop', 'remove', 'reverse', 'sort', '__imul__'), None, <class 'multiprocessing.managers.ListProxy'>),
            'dict': (<class 'dict'>, ('__contains__', '__delitem__', '__getitem__', '__iter__', '__len__', '__setitem__', 'clear', 'copy', 'get', 'has_key', 'items', 'keys', 'pop', 'popitem', 'setdefault', 'update', 'values'), {'__iter__': 'Iterator'}, <class 'multiprocessing.managers.DictProxy'>),
            'Value': (<class 'multiprocessing.managers.Value'>, ('get', 'set'), None, <class 'multiprocessing.managers.ValueProxy'>),
            'Array': (<function Array at 0x7f48934de6a8>, ('__len__', '__getitem__', '__setitem__'), None, <class 'multiprocessing.managers.ArrayProxy'>),
            'Namespace': (<class 'multiprocessing.managers.Namespace'>, ('__getattribute__', '__setattr__', '__delattr__'), None, <class 'multiprocessing.managers.NamespaceProxy'>),
            'Iterator': (None, ('__next__', 'send', 'throw', 'close'), None, <class 'multiprocessing.managers.IteratorProxy'>),
            'AsyncResult': (None, None, None, <function AutoProxy at 0x7f48934de620>)
        }
        '''
        with RemoteSync.server:
            print(RemoteSync)

            RemoteSync.ns.yv1 = RemoteSync.server.Value(int, 6789)
            RemoteSync.ns.yv2 = 987654321
            RemoteSync.ns.yv3 = 123
            print(f'Server ns = {RemoteSync.ns}')

            print('waiting for q2.get()')
            print(RemoteSync.q2.get())
            print(f'\n     Server ns = {RemoteSync.ns}')
            RemoteSync.q1.put(f'Server ns = {RemoteSync.ns}\nServer di = {RemoteSync.di}')

            with RemoteSync.lo:
                RemoteSync.ns.yd1 = RemoteSync.server.dict({'a': 123, 'b': 345})
                RemoteSync.ns.yd2 = []
                RemoteSync.ns.yd3 = [123, 456, 789]
                RemoteSync.di[54] = 'af'

            print('waiting for q2.get()')
            print(RemoteSync.q2.get())
            print(f'\n     Server ns = {RemoteSync.ns}')
            RemoteSync.q1.put(f'Server ns = {RemoteSync.ns}\nServer di = {RemoteSync.di}')

            RemoteSync.di[45] = '#af#'

            print('waiting for q2.get()')
            print(RemoteSync.q2.get())
            print(f'\n     Server ns = {RemoteSync.ns}')
            RemoteSync.q1.put(f'Server ns = {RemoteSync.ns}\nServer di = {RemoteSync.di}')

            RemoteSync.di[345] = '---#asdf#---'
            RemoteSync.di['POC'][3] = 7777777777777777
            poc=RemoteSync.di['POC']
            poc[4]=888888888
            RemoteSync.di['POC']=poc

            print('waiting for q2.get()')
            print(RemoteSync.q2.get())
            print(f'\n     Server ns = {RemoteSync.ns}')
            RemoteSync.q1.put(f'Server ns = {RemoteSync.ns}\nServer di = {RemoteSync.di}')

            print('waiting for q2.get()')
            print(RemoteSync.q2.get())

            #Proc = mp.Process(target=ProcA, args=('proca, server process', RemoteSync.objects()))
            Proc = mp.Process(target=ProcA, args=('proca, server process', RemoteSync))
            Proc.start()

            code.interact(local=globals())

    elif sys.argv[1] == 'client' and len(sys.argv) == 2:
        RemoteSync = rsm.RemoteSyncManager('mpSERVERDATA.pkl', b'testpw123$%^')
        print(RemoteSync)

        print(f'Client ns = {RemoteSync.ns}')
        RemoteSync.ns.yv3 += 44
        print(f'Client ns = {RemoteSync.ns}')

        RemoteSync.q2.put('ready')

        RemoteSync.ns.yv3 += 44
        RemoteSync.di[345] = '#asdf#'

        print('waiting for q1.get()')
        msg = RemoteSync.q1.get()
        print(f'ACK\n{msg}\nclient ns = {RemoteSync.ns}\nclient di = {RemoteSync.di}')
        RemoteSync.q2.put(f'ACK\n{msg}\nclient ns = {RemoteSync.ns}\nclient di = {RemoteSync.di}')

        RemoteSync.di['POC'] = [2,5,8,11,33,66,99]

        print('waiting for q1.get()')
        msg = RemoteSync.q1.get()
        print(f'ACK\n{msg}\nclient ns = {RemoteSync.ns}\nclient di = {RemoteSync.di}')
        RemoteSync.q2.put(f'ACK\n{msg}\nclient ns = {RemoteSync.ns}\nclient di = {RemoteSync.di}')

        RemoteSync.ns.yd3[1] = 99999
        RemoteSync.ns.yd3.append(11)

        print('waiting for q1.get()')
        msg = RemoteSync.q1.get()
        print(f'ACK\n{msg}\nclient ns = {RemoteSync.ns}\nclient di = {RemoteSync.di}')
        RemoteSync.q2.put(f'ACK\n{msg}\nclient ns = {RemoteSync.ns}\nclient di = {RemoteSync.di}')

        print('waiting for q1.get()')
        msg = RemoteSync.q1.get()
        print(f'ACK\n{msg}\nclient ns = {RemoteSync.ns}\nclient di = {RemoteSync.di}')
        RemoteSync.q2.put(f'ACK\n{msg}\nclient ns = {RemoteSync.ns}\nclient di = {RemoteSync.di}')

        #Proc = mp.Process(target=ProcB, args=('procb, client process', RemoteSync.objects()))
        Proc = mp.Process(target=ProcB, args=('procb, client process', RemoteSync))
        Proc.start()

        code.interact(local=globals())

# vim: se ai ts=2 expandtab sw=2 :
