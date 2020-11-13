#!/usr/bin/env python3
# coding: UTF-8

import settings
import signal
import urwid
import time
import sys
import zmq
import re

# ZMQ event loop adapter for urwid

from zmqeventloop import zmqEventLoop

################################################################################

class GridFlowPlus(urwid.GridFlow):

	def keypress(self, size, key):

		if isinstance(key, str):

			if key in ('tab', ):

				if self.focus_position == len(self.contents) - 1:

					self.focus_position = 0

				else:

					self.focus_position += 1

				return

			if key in ('esc', 'N', 'n'):

				self.focus_position = 1

				return super().keypress(size, 'enter')

			if key in ('Y', 'y'):

				self.focus_position = 0

				return super().keypress(size, 'enter')

		return super().keypress(size, key)

################################################################################

class YesNoDialog(urwid.WidgetWrap):

	signals = ['commit']

	def __init__(self, text, loop):

		self.loop = loop

		self.parent = self.loop.widget

		self.body = urwid.Filler(urwid.Text(text))

		self.frame = urwid.Frame(self.body, focus_part = 'body')

		self.view = urwid.Padding(self.frame, ('fixed left', 2), ('fixed right' , 2))
		self.view = urwid.Filler (self.view,  ('fixed top' , 1), ('fixed bottom', 1))
		self.view = urwid.LineBox(self.view)
		self.view = urwid.Overlay(self.view, self.parent, 'center', len(text) + 6, 'middle', 7)

		self.frame.footer = GridFlowPlus([urwid.AttrMap(urwid.Button('Yes', self.on_yes), 'btn_nm', 'btn_hl'),
			                              urwid.AttrMap(urwid.Button('No' , self.on_no) , 'btn_nm', 'btn_hl')],
			                             7, 3, 1, 'center')

		self.frame.focus_position = 'footer'

		super().__init__(self.view)

	def on_yes(self, *args, **kwargs):

		self.loop.widget = self.parent

		urwid.emit_signal(self, 'commit')

	def on_no(self, *args, **kwargs):

		self.loop.widget = self.parent

	def show(self):

		self.loop.widget = self.view

################################################################################

class MessageListBox(urwid.ListBox):

	def __init__(self, body):

		super().__init__(body)

	def render(self, size, *args, **kwargs):

		self.last_render_size = size

		return super().render(size, *args, **kwargs)

	def key(self, key):

		#TODO - check scrolling keypresses and pass back to footer edit control

		super().keypress(self.last_render_size, key)

################################################################################

class ChatApp:

	_clock_fmt = '[%H:%M:%S] '

	_palette = [
				('header', 'black'           , 'brown'      , 'standout'),
				('status', 'black'           , 'brown'      , 'standout'),
				('text'  , 'light gray'      , 'black'      , 'default' ),
				('time'  , 'brown'           , 'black'      , 'default' ),
				('self'  , 'light cyan'      , 'black'      , 'default' ),
				('other' , 'light green'     , 'black'      , 'default' ),
				('ecchat', 'brown'           , 'black'      , 'default' ),
				('scroll', 'text'                                       ),
				('footer', 'text'                                       ),
				('btn_nm', 'black'           , 'brown'      , 'default' ),
				('btn_hl', 'black'           , 'yellow'     , 'standout')]

	def __init__(self):

		urwid.set_encoding('utf-8')

		self.TxID = ''

		self.balance = 10000000

	############################################################################

	def build_ui(self):

		self.walker = urwid.SimpleListWalker([])

		self.headerT = urwid.Text    (u'ecchat 1.0 : henry > borg')
		self.headerA = urwid.AttrMap (self.headerT, 'header')

		self.scrollT = MessageListBox(self.walker)
		self.scrollA = urwid.AttrMap (self.scrollT, 'scroll')

		self.statusT = urwid.Text    (u'Initializing ...')
		self.statusA = urwid.AttrMap (self.statusT, 'status')

		self.footerT = urwid.Edit    ('> ')
		self.footerA = urwid.AttrMap (self.footerT, 'footer')

		self.frame  = urwid.Frame(body = self.scrollA, header = self.headerA, footer = self.statusA)

		self.window = urwid.Frame(body = self.frame, footer = self.footerA, focus_part = 'footer')

	############################################################################

	def append_message_self(self, text):

		self.walker.append(urwid.Text([('time', time.strftime(self._clock_fmt)), ('self', u' henry > '), ('text', text)]))

		self.scrollT.set_focus(len(self.scrollT.body) - 1)

	############################################################################

	def append_message_other(self, text):

		self.walker.append(urwid.Text([('time', time.strftime(self._clock_fmt)), ('other', u'  borg < '), ('text', text)]))

		self.scrollT.set_focus(len(self.scrollT.body) - 1)

	############################################################################

	def append_message_ecchat(self, text):

		self.walker.append(urwid.Text([('time', time.strftime(self._clock_fmt)), ('ecchat', u'ecchat $ '), ('ecchat', text)]))

		self.scrollT.set_focus(len(self.scrollT.body) - 1)

	############################################################################

	def clock_refresh(self, loop = None, data = None):

		self.statusT.set_text(time.strftime(self._clock_fmt))

		loop.set_alarm_in(1, self.clock_refresh)

	############################################################################

	def process_user_entry(self, text):

		if len(text) > 0:

			if text.startswith('/exit'):

				self.check_quit('exit')

			elif text.startswith('/quit'):

				self.check_quit('quit')

			elif text.startswith('/help'):

				self.footerT.set_edit_text(u'')

				self.append_message_self(text)

				self.append_message_ecchat('%-8s - %s' % ('/help', 'display help information'))
				self.append_message_ecchat('%-8s - %s' % ('/exit', 'exit - also /quit and ESC'))
				self.append_message_ecchat('%-8s - %s' % ('/version', 'display ecchat version info'))
				self.append_message_ecchat('%-8s - %s' % ('/balance', 'display $ECC wallet balance'))
				self.append_message_ecchat('%-8s - %s' % ('/send x', 'send $ECC x to other party'))
				self.append_message_ecchat('%-8s - %s' % ('/txid', 'display TxID of last send'))

			elif text.startswith('/balance'):

				self.footerT.set_edit_text(u'')

				self.append_message_self(text)

				self.append_message_ecchat('%d' % self.balance)

			elif text.startswith('/version'):

				self.footerT.set_edit_text(u'')

				self.append_message_self(text)

				self.append_message_ecchat('1.0')

			elif text.startswith('/send'):

				match = re.match('/send ', text)

				amount = text[match.end():]

				self.TxID = 'b6046cf6223ad5f5d9f5656ed428b7cc14d007f334105e693a0e2d1699d2dc92'

				self.footerT.set_edit_text(u'')

				self.append_message_self(text)

				self.append_message_ecchat('$ECC %s sent ' % amount)

				self.balance -= int(amount)

			elif text.startswith('/txid'):

				self.footerT.set_edit_text(u'')

				self.append_message_self(text)

				if self.TxID:

					self.append_message_ecchat('TxID = %s' % self.TxID)

				else:

					self.append_message_ecchat('TxID = %s' % 'none')

			else:

				self.footerT.set_edit_text(u'')

				self.append_message_self(text)

				self.append_message_other('Thanks - good stuff !!!')

	############################################################################

	def unhandled_keypress(self, key):

		if isinstance(key, str):

			if key in ('up', 'down', 'page up', 'page down'):

				self.scrollT.key(key)

			if key in ('enter', ):

				self.process_user_entry(self.footerT.get_edit_text())

			if key in ('esc', ):

				self.check_quit()

	############################################################################

	def check_quit(self, command = 'quit'):

		self.footerT.set_edit_text(u'')

		dialog = YesNoDialog(text = u'Do you want to %s ?' % command, loop = self.loop)

		urwid.connect_signal(dialog, 'commit', self.quit)

		dialog.show()

	############################################################################

	def quit(self, *args, **kwargs):

		raise urwid.ExitMainLoop()

	############################################################################

	def zmqHandler(self):

		[address, contents] = self.subscriber.recv_multipart(zmq.DONTWAIT)
		
		self.append_message_ecchat('ZMQ event')

	############################################################################

	def run(self):

		self.event_loop = zmqEventLoop()

		# Initialise zmq

		self.context    = zmq.Context()
		self.subscriber = self.context.socket(zmq.SUB)

		self.subscriber.connect('tcp://%s'%settings.zmq_address)
		self.subscriber.setsockopt(zmq.SUBSCRIBE, b'')

		self.event_loop.watch_queue(self.subscriber, self.zmqHandler, zmq.POLLIN)

		# Initialize & run urwid

		self.build_ui()

		self.loop = urwid.MainLoop(widget = self.window, palette = self._palette, handle_mouse = True, unhandled_input = self.unhandled_keypress, event_loop = self.event_loop)

		self.loop.set_alarm_in(1, self.clock_refresh)

		self.loop.run()

################################################################################

def terminate(signalNumber, frame):

	raise urwid.ExitMainLoop()

################################################################################
### Main program ###############################################################
################################################################################

def main():

	if sys.version_info[0] < 3:

		raise 'Use Python 3'

	signal.signal(signal.SIGINT,  terminate)  # keyboard interrupt ^C
	signal.signal(signal.SIGTERM, terminate)  # kill [default -15]

	app = ChatApp()

	app.run()

################################################################################

if __name__ == '__main__':

	main()

################################################################################
