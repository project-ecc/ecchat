#!/usr/bin/env python3
# coding: UTF-8

import urwid
import heapq
import time
import zmq
import os

from itertools import count

from urwid.main_loop import EventLoop

zmq_magic = 99999

################################################################################

class zmqEventLoop(EventLoop):

	_alarm_break = count()

	#############################################################################

	def __init__(self):

		self._did_something   = True
		self._alarms          = []
		self._poller          = zmq.Poller()
		self._queue_callbacks = {}				# Callback functions
		self._queue_callbacki = {}				# Index to pass to callback function
		self._idle_handle     = 0
		self._idle_callbacks  = {}

	#############################################################################

	def alarm(self, seconds, callback):

		handle = (time.time() + seconds, next(self._alarm_break), callback)

		heapq.heappush(self._alarms, handle)
		
		return handle

	#############################################################################

	def remove_alarm(self, handle):

		try:

			self._alarms.remove(handle)

			heapq.heapify(self._alarms)

			return True

		except ValueError:

			return False

	#############################################################################

	def watch_queue(self, queue, callback, flags=1, index=zmq_magic):

		if queue in self._queue_callbacks:

			raise ValueError('already watching %r' % queue)

		self._poller.register(queue, flags)

		self._queue_callbacks[queue] = callback
		self._queue_callbacki[queue] = index

		return queue

	#############################################################################

	def remove_watch_queue(self, handle):

		try:

			try:

				self._poller.unregister(handle)

			finally:

				self._queue_callbacks.pop(handle, None)
				self._queue_callbacki.pop(handle, None)

			return True

		except KeyError:

			return False

	#############################################################################

	def watch_file(self, fd, callback, flags=1):

		if isinstance(fd, int):

			fd = os.fdopen(fd)

		self._poller.register(fd, flags)

		self._queue_callbacks[fd.fileno()] = callback
		self._queue_callbacki[fd.fileno()] = zmq_magic

		return fd

	#############################################################################

	def remove_watch_file(self, handle):

		try:

			try:

				self._poller.unregister(handle)

			finally:

				self._queue_callbacks.pop(handle.fileno(), None)
				self._queue_callbacki.pop(handle.fileno(), None)

			return True

		except KeyError:

			return False

	#############################################################################

	def enter_idle(self, callback):

		self._idle_handle += 1

		self._idle_callbacks[self._idle_handle] = callback

		return self._idle_handle

	#############################################################################

	def remove_enter_idle(self, handle):

		try:

			del self._idle_callbacks[handle]

			return True

		except KeyError:

			return False

	#############################################################################

	def _entering_idle(self):

		for callback in list(self._idle_callbacks.values()):

			callback()

	#############################################################################

	def run(self):

		try:

			while True:

				try:

					self._loop()

				except zmq.error.ZMQError as exc:

					if exc.errno != errno.EINTR:

						raise

		except urwid.ExitMainLoop:

			pass

	#############################################################################

	def _loop(self):

		if self._alarms or self._did_something:

			if self._alarms:

				state = 'alarm'

				timeout = max(0, self._alarms[0][0] - time.time())

			if self._did_something and (not self._alarms or (self._alarms and timeout > 0)):

				state = 'idle'

				timeout = 0

			ready = dict(self._poller.poll(timeout * 1000))

		else:

			state = 'wait'

			ready = dict(self._poller.poll())

		if not ready:

			if state == 'idle':

				self._entering_idle()

				self._did_something = False

			elif state == 'alarm':

				due, tie_break, callback = heapq.heappop(self._alarms)

				callback()

				self._did_something = True

		for queue, _ in ready.items():

			if self._queue_callbacki[queue] == zmq_magic:						# Default value used for back compatibility

				self._queue_callbacks[queue]()									# Call for urwid file descriptor

			else:

				self._queue_callbacks[queue](self._queue_callbacki[queue])		# Call for zmq queue

			self._did_something = True

################################################################################
