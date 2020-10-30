#!/usr/bin/env python3
# coding: UTF-8

import urwid
import zmq

from urwid.main_loop import EventLoop

################################################################################

class zmqEventLoop(EventLoop):

	def __init__(self):

		self._did_something   = True
		self._alarms          = []
		self._poller          = xmq.Poller()
		self._queue_callbacks = {}
		self._idle_handle     = 0
		self._idle_callbacks  = {}

################################################################################
