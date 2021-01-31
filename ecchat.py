#!/usr/bin/env python3
# coding: UTF-8

import datetime
import settings
import argparse
import pathlib
import logging
import socket
import pycurl
import signal
import codecs
import urwid
import time
import uuid
import zmq
import sys
import re

from itertools import count

# ZMQ event loop adapter for urwid

from zmqeventloop import zmqEventLoop

# Full node RPC interface

from slickrpc import Proxy
from slickrpc import exc

# eccPacket class

from eccpacket import eccPacket

coins = []

for index, chain in enumerate(settings.chains):

	if index == 0:

		if chain['coin_symbol'] != 'ecc':

			print('ecc must be the first configured chain')

			sys.exit()

	coins.append(Proxy('http://%s:%s@%s' % (chain['rpc_user'], chain['rpc_pass'], chain['rpc_address'])))

################################################################################

def check_symbol(symbol):

	return_valid = False
	return_index = 0

	for index, chain in enumerate(settings.chains):

		if symbol.lower() == chain['coin_symbol']:

			return_valid = True
			return_index = index

	return return_valid, return_index

################################################################################
## urwid related ###############################################################
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

	############################################################################

	def on_yes(self, *args, **kwargs):

		self.loop.widget = self.parent

		urwid.emit_signal(self, 'commit')

	############################################################################

	def on_no(self, *args, **kwargs):

		self.loop.widget = self.parent

	############################################################################

	def show(self):

		self.loop.widget = self.view

################################################################################

class PasswordDialog(urwid.WidgetWrap):

	signals = ['commit']

	def __init__(self, text, loop):

		self.loop = loop

		self.parent = self.loop.widget

		#self.body = urwid.Filler(urwid.Text(text))

		#self.frame = urwid.Frame(self.body, focus_part = 'body')

		#self.view = urwid.Padding(self.frame, ('fixed left', 2), ('fixed right' , 2))
		#self.view = urwid.Filler (self.view,  ('fixed top' , 1), ('fixed bottom', 1))
		#self.view = urwid.LineBox(self.view)
		#self.view = urwid.Overlay(self.view, self.parent, 'center', len(text) + 6, 'middle', 7)

		#self.frame.footer = GridFlowPlus([urwid.AttrMap(urwid.Button('OK', self.on_ok), 'btn_nm', 'btn_hl'),
		#	                              urwid.AttrMap(urwid.Button('Cancel' , self.on_cancel) , 'btn_nm', 'btn_hl')],
		#	                             7, 3, 1, 'center')

		#self.frame.focus_position = 'footer'

		super().__init__(self.view)

	############################################################################

	def on_ok(self, *args, **kwargs):

		self.loop.widget = self.parent

		urwid.emit_signal(self, 'commit')

	############################################################################

	def on_cancel(self, *args, **kwargs):

		self.loop.widget = self.parent

	############################################################################

	def show(self):

		self.loop.widget = self.view

################################################################################

class MessageListBox(urwid.ListBox):

	def __init__(self, body):

		super().__init__(body)

	############################################################################

	def render(self, size, *args, **kwargs):

		self.last_render_size = size

		return super().render(size, *args, **kwargs)

	############################################################################

	def key(self, key):

		#TODO - check scrolling keypresses and pass back to footer edit control

		super().keypress(self.last_render_size, key)

################################################################################

class FrameFocus(urwid.Frame):

	def __init__(self, body, header=None, footer=None, focus_part='body'):

		self.focus_part = focus_part

		super().__init__(body, header, footer, focus_part)

	############################################################################

	def mouse_event(self, size, event, button, col, row, focus):

		self.set_focus(self.focus_part)

################################################################################
## chain class #################################################################
################################################################################

class blockChain():

	############################################################################

	def __init__(self, symbol, rpc_address, rpc_user, rpc_pass):

		self.symbol			= symbol
		self.rpc_address	= rpc_address
		self.rpc_user		= rpc_user
		self.rpc_pass		= rpc_pass

################################################################################
## ChatApp class ###############################################################
################################################################################

class ChatApp:

	_bufferIdx = count(start=1)

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

	def __init__(self, name, other, tag):

		urwid.set_encoding('utf-8')

		self.version = '1.1'

		self.party_name = ['ecchat', name, other]

		self.party_separator  = ['|', '>', '<']

		self.party_name_style = ['ecchat', 'self', 'other']

		self.party_text_style = ['ecchat', 'text', 'text']

		self.party_size = max(len(t) for t in self.party_name)

		self.otherTag = tag

		self.send_pending = False

		self.send_amount = 0.0

		self.send_index = 0

		self.txid = ''

		self.blocks = []
		self.peers  = []

		self.zmq_address = []

		self.subscribers = []

	############################################################################

	def build_ui(self):

		self.walker  = urwid.SimpleListWalker([])

		self.headerT = urwid.Text    (u'ecchat {} : {} > {}'.format(self.version, self.party_name[1], self.party_name[2]))
		self.headerA = urwid.AttrMap (self.headerT, 'header')

		self.scrollT = MessageListBox(self.walker)
		self.scrollA = urwid.AttrMap (self.scrollT, 'scroll')

		self.statusT = urwid.Text    (u'Initializing ...')
		self.statusA = urwid.AttrMap (self.statusT, 'status')

		self.footerT = urwid.Edit    ('> ')
		self.footerA = urwid.AttrMap (self.footerT, 'footer')

		self.frame   = urwid.Frame   (body = self.scrollA, header = self.headerA, footer = self.statusA)

		self.window  = FrameFocus    (body = self.frame, footer = self.footerA, focus_part = 'footer')

	############################################################################

	def send_ecc_packet(self, meth, data):

		ecc_packet = eccPacket(settings.protocol_id, settings.protocol_ver, self.otherTag, self.selfTag, meth, data)

		logging.info(ecc_packet.to_json())

		ecc_packet.send(coins[0])

	############################################################################

	def append_message(self, party, text):

		self.walker.append(urwid.Text([('time', time.strftime(self._clock_fmt)), (self.party_name_style[party], u'{0:>{1}s} {2} '.format(self.party_name[party], self.party_size, self.party_separator[party])), (self.party_text_style[party], text)]))

		self.scrollT.set_focus(len(self.scrollT.body) - 1)

	############################################################################

	def clock_refresh(self, loop = None, data = None):

		text = time.strftime(self._clock_fmt)

		for i, coin in enumerate(coins):

			text += ' {} # {:d}/{:d} '.format(settings.chains[i]['coin_symbol'], self.blocks[i], self.peers[i])

		self.statusT.set_text(text)

		#self.statusT.set_text('{} ecc # {:d}/{:d}'.format(time.strftime(self._clock_fmt), self.blocks[0], self.peers[0]))

		loop.set_alarm_in(1, self.clock_refresh)

	############################################################################

	def block_refresh(self, index):

		self.blocks[index] = coins[index].getblockcount()
		self.peers [index] = coins[index].getconnectioncount()

	############################################################################

	def block_refresh_timed(self, loop = None, data = None):

		for index, address in enumerate(self.zmq_address):

			if not address:

				self.blocks[index] = coins[index].getblockcount()
				self.peers [index] = coins[index].getconnectioncount()

		loop.set_alarm_in(10, self.block_refresh_timed)

	############################################################################

	def start_send_ecc(self, amount, index):

		# Check 1 - Is a send currently incomplete ?

		if self.send_pending:

			self.append_message(0, 'Prior send incomplete - try again later')

			return

		# Check 2 - Can the send amount be converted to a float correctly ?

		try:

			float_amount = float(amount)

		except ValueError:

			self.append_message(0, 'Invalid send amount - number expected')

			return

		# Check 3 - Is the send amount in a sensible range ?

		if float_amount <= 0:

			self.append_message(0, 'Invalid send amount - must be greater than zero')

			return

		# Check 4 - Does the user's wallet hold an adequate balance ?

		balance = coins[index].getbalance()

		if float_amount >= balance:

			self.append_message(0, 'Invalid send amount - must be less than current balance = {:f}'.format(balance))

			return

		# Request address from peer

		data = {'coin' : settings.chains[index]['coin_symbol'],
				'type' : 'P2PKH'}

		self.send_ecc_packet(eccPacket.METH_addrReq, data)

		self.loop.set_alarm_in(10, self.timeout_send_ecc)

		self.send_pending = True

		self.send_amount = float_amount

		self.send_index = index

	############################################################################

	def complete_send_ecc(self, address):

		if address == '0':

			self.append_message(0, 'Other party is unable or unwilling to receive unsolicited sends of {}'.format(settings.chains[self.send_index]['coin_symbol']))

			#TODO : Test this !!!

		if self.send_pending:

			try:

				self.txid = coins[self.send_index].sendtoaddress(address, str(self.send_amount), "ecchat")

			except exc.RpcWalletUnlockNeeded:

				self.append_message(0, 'Wallet locked - please unlock')

			else:

				self.append_message(0, '{:f} {} sent to {} [/txid available]'.format(self.send_amount, settings.chains[self.send_index]['coin_symbol'],address))

			# Send the METH_txidInf message - (coin, amount, address, txid)

			data = {'coin' : settings.chains[self.send_index]['coin_symbol'],
					'amnt' : '{:f}'.format(self.send_amount),
					'addr' : address,
					'txid' : self.txid}

			self.send_ecc_packet(eccPacket.METH_txidInf, data)

		# /send command complete - reset state variables

		self.send_pending = False

		self.send_amount = 0.0

		self.send_index = 0

	############################################################################

	def timeout_send_ecc(self, loop = None, data = None):

		if self.send_pending:

			self.append_message(0, 'No response from other party - /send cancelled')

			# /send command cancelled - reset state variables

			self.send_pending = False

			self.send_amount = 0.0

			self.send_index = 0

	############################################################################

	def process_user_entry(self, text):

		if len(text) > 0:

			self.footerT.set_edit_text(u'')

			self.append_message(1, text)

			if text.startswith('/exit'):

				self.check_quit('exit')

			elif text.startswith('/quit'):

				self.check_quit('quit')

			elif text.startswith('/help'):

				self.append_message(0, '%-8s - %s' % ('/help          ', 'display help information'))
				self.append_message(0, '%-8s - %s' % ('/exit          ', 'exit - also /quit and ESC'))
				self.append_message(0, '%-8s - %s' % ('/version       ', 'display ecchat version info'))
				self.append_message(0, '%-8s - %s' % ('/blocks  <coin>', 'display block count'))
				self.append_message(0, '%-8s - %s' % ('/peers   <coin>', 'display peer count'))
				self.append_message(0, '%-8s - %s' % ('/tag           ', 'display routing tag public key'))
				self.append_message(0, '%-8s - %s' % ('/balance <coin>', 'display wallet balance'))
				self.append_message(0, '%-8s - %s' % ('/address <coin>', 'generate a new address'))
				self.append_message(0, '%-8s - %s' % ('/send x  <coin>', 'send x to other party'))
				self.append_message(0, '%-8s - %s' % ('/txid          ', 'display txid of last transaction'))
				self.append_message(0, '%-8s - %s' % ('         <coin>', 'coin symbol - defaults to ecc'))

			elif text.startswith('/version'):

				self.append_message(0, self.version)

			elif text.startswith('/blocks'):

				match = re.match('/blocks (?P<symbol>\w+)', text)

				if match:

					valid, index = check_symbol(match.group('symbol'))

					if valid:

						self.append_message(0, '{:d}'.format(coins[index].getblockcount()))

					else:

						self.append_message(0, 'Unknown coin symbol: {}'.format(match.group('symbol')))

				else:

					for index, coin in enumerate(coins):

						self.append_message(0, '{} : {:d}'.format(settings.chains[index]['coin_symbol'], coin.getblockcount()))

			elif text.startswith('/peers'):

				match = re.match('/peers (?P<symbol>\w+)', text)

				if match:

					valid, index = check_symbol(match.group('symbol'))

					if valid:

						self.peers[index] = coins[index].getconnectioncount()

						self.append_message(0, '{:d}'.format(self.peers[index]))

					else:

						self.append_message(0, 'Unknown coin symbol: {}'.format(match.group('symbol')))

				else:

					for index, coin in enumerate(coins):

						self.peers[index] = coin.getconnectioncount()

						self.append_message(0, '{} : {:d}'.format(settings.chains[index]['coin_symbol'], self.peers[index]))

			elif text.startswith('/tag'):

				self.append_message(0, '{}'.format(self.selfTag))

			elif text.startswith('/balance'):

				match = re.match('/balance (?P<symbol>\w+)', text)

				if match:

					valid, index = check_symbol(match.group('symbol'))

					if valid:

						balance_con = coins[index].getbalance()
						balance_unc = coins[index].getunconfirmedbalance()

						if balance_unc > 0:

							self.append_message(0, '{:f} confirmed + {:f} unconfirmed'.format(balance_con, balance_unc))

						else:

							self.append_message(0, '{:f}'.format(balance_con))

					else:

						self.append_message(0, 'Unknown coin symbol: {}'.format(match.group('symbol')))

				else:

					for index, coin in enumerate(coins):

						balance_con = coin.getbalance()
						balance_unc = coin.getunconfirmedbalance()

						if balance_unc > 0:

							self.append_message(0, '{} : {:f} confirmed + {:f} unconfirmed'.format(settings.chains[index]['coin_symbol'], balance_con, balance_unc))

						else:

							self.append_message(0, '{} : {:f}'.format(settings.chains[index]['coin_symbol'], balance_con))

			elif text.startswith('/address'):

				match = re.match('/address (?P<symbol>\w+)', text)

				if match:

					valid, index = check_symbol(match.group('symbol'))

					if valid:

						address = coins[index].getnewaddress()

						self.append_message(0, '{}'.format(address))

					else:

						self.append_message(0, 'Unknown coin symbol: {}'.format(match.group('symbol')))

				else:

					address = coins[0].getnewaddress()

					self.append_message(0, '{}'.format(address))

			elif text.startswith('/send'):

				match_default = re.match('/send (?P<amount>([0-9]*\.)?[0-9]+)'                , text)
				match_symbol  = re.match('/send (?P<amount>([0-9]*\.)?[0-9]+) (?P<symbol>\w+)', text)

				if match_symbol:

					valid, index = check_symbol(match_symbol.group('symbol'))

					if valid:

						self.start_send_ecc(match_symbol.group('amount'), index)

					else:

						self.append_message(0, 'Unknown coin symbol: {}'.format(match_symbol.group('symbol')))

				elif match_default:

					self.start_send_ecc(match_default.group('amount'), 0)

				else:

					self.append_message(0, 'Unknown command syntax - try /help for a list of commands')

			elif text.startswith('/txid'):

				if self.txid:

					self.append_message(0, 'txid = %s' % self.txid)

				else:

					self.append_message(0, 'txid = %s' % 'none')

			elif text.startswith('/'):

				self.append_message(0, 'Unknown command syntax - try /help for a list of commands')

			else:

				data = {'uuid' : str(uuid.uuid4()),
						'cmmd' : 'add',
						'text' : text}

				self.send_ecc_packet(eccPacket.METH_chatMsg, data)

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

		dialog = YesNoDialog(text = u'Do you want to %s ?' % command, loop = self.loop)

		urwid.connect_signal(dialog, 'commit', self.quit)

		dialog.show()

	############################################################################

	def quit(self, *args, **kwargs):

		raise urwid.ExitMainLoop()

	############################################################################

	def zmqInitialise(self):

		self.context    = zmq.Context()

		self.event_loop = zmqEventLoop()

		for index, address in enumerate(self.zmq_address):

			self.subscribers.append(self.context.socket(zmq.SUB))

			if address:

				self.subscribers[index].connect(address)

				self.subscribers[index].setsockopt(zmq.SUBSCRIBE, b'')

				self.event_loop.watch_queue(self.subscribers[index], self.zmqHandler, zmq.POLLIN, index)

	############################################################################

	def zmqShutdown(self):

		for subscriber in self.subscribers:

			subscriber.close()

		self.context.term()

	############################################################################

	def zmqHandler(self, index):

		if index > 0: # various chains return differing numbers of list values (ltc = 3)

			slashdevslashnull = self.subscribers[index].recv_multipart(zmq.DONTWAIT)

			self.block_refresh(index)

			return

		[address, contents] = self.subscribers[index].recv_multipart(zmq.DONTWAIT)
		
		if address.decode() == 'hashblock':

			self.block_refresh(0)

		if address.decode() == 'packet':

			protocolID = contents.decode()[1:]

			bufferCmd = 'GetBufferRequest:' + protocolID + str(next(self._bufferIdx))

			bufferSig = coins[0].buffersignmessage(self.bufferKey, bufferCmd)

			eccbuffer = coins[0].getbuffer(int(protocolID), bufferSig)

			for packet in eccbuffer.values():

				message = codecs.decode(packet, 'hex').decode()

				ecc_packet = eccPacket.from_json(message)

				if ecc_packet.get_meth() == eccPacket.METH_chatMsg:

					data = ecc_packet.get_data()

					if data['cmmd'] == 'add':

						self.append_message(2, data['text'])

						rData = {'uuid' : data['uuid'],
								 'cmmd' : data['cmmd'],
								 'able' : True}

					else:

						rData = {'uuid' : data['uuid'],
								 'cmmd' : data['cmmd'],
								 'able' : False}

					self.send_ecc_packet(eccPacket.METH_chatAck, rData)

				elif ecc_packet.get_meth() == eccPacket.METH_chatAck:

					data = ecc_packet.get_data()

					# TODO : UI indication of ack

				elif ecc_packet.get_meth() == eccPacket.METH_addrReq:

					data = ecc_packet.get_data()

					valid, index = check_symbol(data['coin'])

					if valid:

						address = coins[index].getnewaddress()

						rData = {'coin' : data['coin'],
								 'addr' : address}

						self.send_ecc_packet(eccPacket.METH_addrRes, rData)

				elif ecc_packet.get_meth() == eccPacket.METH_addrRes:

					data = ecc_packet.get_data()

					self.complete_send_ecc(data['addr'])

				elif ecc_packet.get_meth() == eccPacket.METH_txidInf:

					data = ecc_packet.get_data()

					self.append_message(0, '{} {} received at {} [/txid available]'.format(data['amnt'], data['coin'], data['addr']))

					self.txid = data['txid']

				else:

					pass

	############################################################################

	def eccoinInitialise(self):

		self.bufferKey = ""

		try:

			self.selfTag = coins[0].getroutingpubkey()

		except pycurl.error:

			print('Failed to connect - check that local eccoin daemon is running')

			return False

		except exc.RpcInWarmUp:

			print('Failed to connect - local eccoin daemon is starting but not ready - try again after 60 seconds')

			return False

		try:

			self.bufferKey = coins[0].registerbuffer(settings.protocol_id)

		except exc.RpcInternalError:

			print('API Buffer was not correctly unregistered - try again after 60 seconds')

			return False

		for index, coin in enumerate(coins):

			try:

				zmqnotifications = coins[index].getzmqnotifications()

			except pycurl.error:

				print('Blockchain node for {} not available or incorrectly configured'.format(settings.chains[index]['coin_symbol']))

				return False

			except (exc.RpcMethodNotFound, ValueError):

				zmqnotifications = []

			self.zmq_address.append('')

			for zmqnotification in zmqnotifications:

				if zmqnotification['type'] == 'pubhashblock':

					self.zmq_address[index] = zmqnotification['address']

		try:

			coins[0].findroute(self.otherTag)

			isRoute = coins[0].haveroute(self.otherTag)

		except exc.RpcInvalidAddressOrKey:

			print('Routing tag has invalid base64 encoding : %s' % self.otherTag)

			return False

		if not isRoute:

			print('No route available to : %s' % self.otherTag)

		for coin in coins:

			self.blocks.append(coin.getblockcount())
			self.peers.append (coin.getconnectioncount())

		return isRoute

	############################################################################

	def reset_buffer_timeout(self, loop = None, data = None):

		if self.bufferKey:

			bufferSig = coins[0].buffersignmessage(self.bufferKey, 'ResetBufferTimeout')

			coins[0].resetbuffertimeout(settings.protocol_id, bufferSig)

			loop.set_alarm_in(10, self.reset_buffer_timeout)

	############################################################################

	def eccoinShutdown(self):

		if self.bufferKey:

			bufferSig = coins[0].buffersignmessage(self.bufferKey, 'ReleaseBufferRequest')

			coins[0].releasebuffer(settings.protocol_id, bufferSig)

			self.bufferKey = ""

	############################################################################

	def run(self):

		if self.eccoinInitialise():

			self.zmqInitialise()

			self.build_ui()

			self.loop = urwid.MainLoop(widget          = self.window,
			                           palette         = self._palette,
			                           handle_mouse    = True,
			                           unhandled_input = self.unhandled_keypress,
			                           event_loop      = self.event_loop)

			self.loop.set_alarm_in(1, self.clock_refresh)

			self.loop.set_alarm_in(10, self.reset_buffer_timeout)

			for address in self.zmq_address:

				if not address:

					self.loop.set_alarm_in(10, self.block_refresh_timed)

					break

			self.loop.run()

			self.zmqShutdown()

		self.eccoinShutdown()

################################################################################

def terminate(signalNumber, frame):

	logging.info('%s received - terminating' % signal.Signals(signalNumber).name)

	raise urwid.ExitMainLoop()

################################################################################
### Main program ###############################################################
################################################################################

def main():

	if sys.version_info[0] < 3:

		raise 'Use Python 3'

	pathlib.Path('log').mkdir(parents=True, exist_ok=True)

	logging.basicConfig(filename = 'log/{:%Y-%m-%d}.log'.format(datetime.datetime.now()),
						filemode = 'a',
						level    = logging.INFO,
						format   = '%(asctime)s - %(levelname)s : %(message)s',
						datefmt  = '%d/%m/%Y %H:%M:%S')

	logging.info('STARTUP')

	signal.signal(signal.SIGINT,  terminate)  # keyboard interrupt ^C
	signal.signal(signal.SIGTERM, terminate)  # kill [default -15]

	argparser = argparse.ArgumentParser(description='Simple command line chat for ECC')

	argparser.add_argument('-n', '--name'  , action='store', help='nickname    (local)' , type=str, default = ''       , required=True)
	argparser.add_argument('-o', '--other' , action='store', help='nickname    (remote)', type=str, default = '[other]', required=False)
	argparser.add_argument('-t', '--tag'   , action='store', help='routing tag (remote)', type=str, default = ''       , required=True)

	command_line_args = argparser.parse_args()

	logging.info('Arguments %s', vars(command_line_args))

	app = ChatApp(command_line_args.name, command_line_args.other, command_line_args.tag)

	app.run()

	logging.info('SHUTDOWN')

################################################################################

if __name__ == '__main__':

	main()

################################################################################
