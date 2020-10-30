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

	def alarm(self, seconds, callback):

		pass

	def remove_alarm(self, handle):

		pass

	def watch_queue(self, queue, callback, flags=1):

		pass

	def watch_file(self, fd, callback, flags=1):

		pass

	def remove_watch_queue(self, handle):

		pass

	def remove_watch_file(self, handle):

		pass

	def enter_idle(self, callback):

		pass

	def remove_enter_idle(self, handle):

		pass

	def _entering_idle(self):

		pass

	def run(self):

		pass

	def _loop(self):

		pass

		



################################################################################
