# PythonLibraries-Multiprocessing-RemoteSyncManager

A python library to simplify the use of multiprocessing.managers.SyncManager()
for remote and local use.


## A problem to solve

When trying to use the `multiprocessing` python (3.6) module, I became
frustrated very quickly because the documentation, although extensive and
detailed, is not very clear on intent, possible use cases or relevant working
examples comprehensive enough to be any use to help understanding for someone
who is learning to use this tool and not yet an expert.

Many websites, including stackoverflow, offered solutions that were either not
relevant or that I could not understand. Little by little, by cross reading many
sources, including the code of the `multiprocessing` module itself, things
became clearer.

Of this search emerged a library that, in my mind, greatly simplifies the use of
the `SyncManager` for data sharing between local and remote processes.


## The library

Browse over to the `code` directory where you will find the `remotesyncmanager`
module.

It is work in progress, but essentially self-documented.

To fully understand how it works, I suggest reading the example application.


## A working example

In the `example` folder, you will find a single python file that can be run with
`python3 remotesyncmanager-example-application.py server` to start the server
portion in a terminal window, and `python3
remotesyncmanager-example-application.py client` to start the client version,
either in a different terminal window on the same computer, or even on a
different computer after having copied the `mpSERVERDATA.pkl` file from server
to the client computer (this file must be copied after the server has started).
Note that this will only work in the same LAN. The library would require changes
for it to work beyond a LAN.
