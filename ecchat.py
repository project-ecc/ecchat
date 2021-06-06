#!/usr/bin/env python3
# coding: UTF-8

import datetime
import argparse
import pyqrcode
import pathlib
import logging
import signal
import codecs
import pickle
import urwid
import zmq
import sys
import re

from uuid import uuid4

# ZMQ event loop adapter for urwid

from zmqeventloop import zmqEventLoop

#from slickrpc import Proxy
from slickrpc import exc # RpcWalletUnlockNeeded only TO BE REMOVED !!!!! # TIDY

# Configuration file management : eccoin.conf & ecchat.conf

from configure import loadConfigurationECC, loadConfigurationAlt

# eccPacket, cryptoNode & transaction classes

from eccpacket    import eccPacket
from cryptonode   import cryptoNode, eccoinNode, bitcoinNode, moneroNode, cryptoNodeException
from transactions import txSend, txReceive

# urwid extension classes

from urwidext import GridFlowPlus, YesNoDialog, PassphraseDialog, MessageListBox, FrameFocus, MessageWalker

################################################################################
## ChatApp class ###############################################################
################################################################################

class ChatApp:

	_clock_fmt = '[%H:%M:%S] '

	_palette = [
				('header', 'black'           , 'brown'      , 'standout'),
				('status', 'black'           , 'brown'      , 'standout'),
				('text'  , 'light gray'      , 'black'      , 'default' ),
				('tnak'  , 'dark gray'       , 'black'      , 'default' ),
				('tack'  , 'light gray'      , 'black'      , 'default' ),
				('time'  , 'brown'           , 'black'      , 'default' ),
				('self'  , 'light cyan'      , 'black'      , 'default' ),
				('other' , 'light green'     , 'black'      , 'default' ),
				('ecchat', 'brown'           , 'black'      , 'default' ),
				('scroll', 'text'                                       ),
				('footer', 'text'                                       ),
				('btn_nm', 'black'           , 'brown'      , 'default' ),
				('btn_hl', 'black'           , 'yellow'     , 'standout')]

	def __init__(self, name, other, tag, conf, debug=False):

		urwid.set_encoding('utf-8')

		self.version      = '1.3'

		self.protocol_id  = 1
		self.protocol_ver = 1

		self.party_name = ['ecchat', name, other]

		self.party_separator  = ['|', '>', '<']

		self.party_name_style = ['ecchat', 'self', 'other']

		self.party_text_style = ['ecchat', 'text', 'text']

		self.party_size = max(len(t) for t in self.party_name)

		if tag == 'ececho':

			self.otherTag = 'BImGKLu0cwgmRigdvoWTnJdQ0Q+QgscUzJgsdChUOTi2dkM6wF/KXf84w9VjIydfIwl3EDgNPvjLP3HgNyifZ9w='

		else:

			self.otherTag = tag

		self.conf     = conf
		self.debug    = debug

		self.swap_pending    = False
		self.swap_uuid       = ''
		self.swap_timeout_h  = 0
		self.swap_amountGive = 0.0
		self.swap_amountTake = 0.0
		self.swap_indexGive  = 0
		self.swap_indexTake  = 0

		self.txid = ''

		self.subscribers = []

		self.coins = []

		self.txSend    = {}
		self.txReceive = {}
		self.txSwap    = {}

	############################################################################

	def check_symbol(self, symbol):

		return_valid = False
		return_index = 0

		for index, coin in enumerate(self.coins):

			if symbol.lower() == coin.symbol:

				return_valid = True
				return_index = index

		return return_valid, return_index

	############################################################################

	def build_ui(self):

		self.walker  = MessageWalker ()

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

		ecc_packet = eccPacket(self.protocol_id, self.protocol_ver, self.otherTag, self.coins[0].routingTag, meth, data)

		if self.debug:

			logging.info('TX: {}'.format(ecc_packet.to_json()))

		ecc_packet.send(self.coins[0])

	############################################################################

	def append_message(self, party, text, uuid = '', ack = True):

		tstyle = {True : self.party_text_style[party], False : 'tnak'} [ack]

		markup = [('time', datetime.datetime.now().strftime(self._clock_fmt)), (self.party_name_style[party], u'{0:>{1}s} {2} '.format(self.party_name[party], self.party_size, self.party_separator[party])), (tstyle, text)]

		self.walker.append(party, markup, uuid)

		self.scrollT.set_focus(len(self.scrollT.body) - 1)

	############################################################################

	def replace_message(self, party, text, uuid = '', ack = True):

		tstyle = {True : self.party_text_style[party], False : 'tnak'} [ack]

		markup = [('time', datetime.datetime.now().strftime(self._clock_fmt)), (self.party_name_style[party], u'{0:>{1}s} {2} '.format(self.party_name[party], self.party_size, self.party_separator[party])), (tstyle, text)]

		self.walker.replace(party, markup, uuid)

		self.scrollT.set_focus(len(self.scrollT.body) - 1)

	############################################################################

	def delete_message(self, party, text, uuid = '', ack = True):

		del_text = '\u2588' * len(text)

		tstyle = {True : self.party_text_style[party], False : 'tnak'} [ack]

		markup = [('time', datetime.datetime.now().strftime(self._clock_fmt)), (self.party_name_style[party], u'{0:>{1}s} {2} '.format(self.party_name[party], self.party_size, self.party_separator[party])), (tstyle, del_text)]

		self.walker.replace(party, markup, uuid)

		self.scrollT.set_focus(len(self.scrollT.body) - 1)

	############################################################################

	def ack_message(self, uuid):

		self.walker.set_markup_style(uuid, 2, 'tack')

	############################################################################

	def clock_refresh(self, loop = None, data = None):

		text = datetime.datetime.now().strftime(self._clock_fmt)

		for coin in self.coins:

			text += ' {} # {:d}/{:d} '.format(coin.symbol, coin.blocks, coin.peers)

		self.statusT.set_text(text)

		loop.set_alarm_in(1, self.clock_refresh)

	############################################################################

	def reset_buffer_timeout(self, loop = None, data = None):

		if self.coins[0].reset_buffer_timeout():

			loop.set_alarm_in(10, self.reset_buffer_timeout)

	############################################################################

	def block_refresh_timed(self, loop = None, data = None):

		for coin in self.coins:

			if not coin.zmqAddress:

				coin.refresh()

		loop.set_alarm_in(10, self.block_refresh_timed)

	############################################################################

	def block_refresh(self, index):

		self.coins[index].refresh()

	############################################################################

	def show_passphrase_dialog(self, symbol, retry_no, retry_max, callback):

		dialog = PassphraseDialog(text = u'Enter {} wallet unlock passphrase ({:d}/{:d}):'.format(symbol, retry_no, retry_max), loop = self.loop)

		urwid.connect_signal(dialog, 'commit', callback)

		dialog.show()

	############################################################################

	def start_swap(self, amountGive, indexGive, amountTake, indexTake):

		# Check 1 - Is a swap currently pending ?

		if self.swap_pending:

			self.loop.remove_alarm(self.swap_timeout_h)

			self.swap_pending    = False
			self.swap_uuid       = ''
			self.swap_timeout_h  = 0
			self.swap_amountGive = 0.0
			self.swap_amountTake = 0.0
			self.swap_indexGive  = 0
			self.swap_indexTake  = 0

		# Check 2 - Can the swap amount be converted to a float correctly ?

		try:

			float_amountGive = float(amountGive)
			float_amountTake = float(amountTake)

		except ValueError:

			self.append_message(0, 'Invalid swap amount - number expected')

			return

		# Check 3 - Is the swap amount in a sensible range ?

		if (float_amountGive <= 0) or (float_amountTake <= 0):

			self.append_message(0, 'Invalid swap amount - must be greater than zero')

			return

		# Check 4 - Does the user's wallet hold an adequate balance ?

		balance = self.coins[indexGive].get_unlocked_balance()

		if float_amountGive >= balance:

			self.append_message(0, 'Invalid swap amount - must be less than current balance = {:f}'.format(balance))

			return

		# Check 5 - Ensure the user's wallet is unlocked

		# TODO

		# Send swap information

		data = {'uuid' : str(uuid4()),
				'cogv' : self.coins[indexGive].symbol,
				'amgv' : float_amountGive,
				'cotk' : self.coins[indexTake].symbol,
				'amtk' : float_amountTake}

		self.send_ecc_packet(eccPacket.METH_swapInf, data)

		handle = self.loop.set_alarm_in(60, self.timeout_swap)

		self.swap_pending    = True
		self.swap_uuid       = data['uuid']
		self.swap_timeout_h  = handle
		self.swap_amountGive = float_amountGive
		self.swap_amountTake = float_amountTake
		self.swap_indexGive  = indexGive
		self.swap_indexTake  = indexTake

	############################################################################

	def swap_proposed(self, symbolGive, amountGive, symbolTake, amountTake):

		# Notify user of swap proposal

		self.append_message(0, 'Swap proposed : {} {} for {} {}'.format(amountGive, symbolGive, amountTake, symbolTake))

		# Check 1 - Is a swap currently incomplete ?

		if self.swap_pending:

			self.swap_pending    = False
			self.swap_uuid       = ''
			self.swap_timeout_h  = 0
			self.swap_amountGive = 0.0
			self.swap_amountTake = 0.0
			self.swap_indexGive  = 0
			self.swap_indexTake  = 0

		# Check 2 - Are both the coins in the proposed swap available

		validGive, indexGive = self.check_symbol(symbolGive)
		validTake, indexTake = self.check_symbol(symbolTake)

		if not validGive:

			self.append_message(0, 'Unknown coin symbol: {}'.format(match.group('symbolGive')))

			return

		if not validTake:

			self.append_message(0, 'Unknown coin symbol: {}'.format(match.group('symbolTake')))

			return

		# Check 3 - Can the swap amount be converted to a float correctly ?

		try:

			float_amountGive = float(amountGive)
			float_amountTake = float(amountTake)

		except ValueError:

			self.append_message(0, 'Invalid swap amount - number expected')

			return

		# Check 4 - Is the swap amount in a sensible range ?

		if (float_amountGive <= 0) or (float_amountTake <= 0):

			self.append_message(0, 'Invalid swap amount - must be greater than zero')

			return

		# Check 5 - Does the user's wallet hold an adequate balance ?

		balance = self.coins[indexTake].get_unlocked_balance()

		if float_amountTake >= balance:

			self.append_message(0, 'Invalid swap amount - must be less than current balance = {:f}'.format(balance))

			return

		self.swap_pending    = True
		self.swap_uuid       = ''
		self.swap_timeout_h  = 0
		self.swap_amountGive = float_amountGive
		self.swap_amountTake = float_amountTake
		self.swap_indexGive  = indexGive
		self.swap_indexTake  = indexTake

	############################################################################

	def swap_execute(self):

		# Check 1 - Ensure the user's wallet is unlocked

		# TODO

		if not self.swap_pending:

			self.append_message(0, 'No swap available to execute')

			return

		address = self.coins[self.swap_indexGive].get_new_address()

		data = {'uuid' : self.swap_uuid,
				'cogv' : self.coins[self.swap_indexGive].symbol,
				'adgv' : address}

		self.send_ecc_packet(eccPacket.METH_swapReq, data)

		self.loop.set_alarm_in(10, self.timeout_execute)

	############################################################################

	def swap_request(self, symbolGive, addressGive):

		if self.swap_pending:

			assert symbolGive == self.coins[self.swap_indexGive].symbol

			self.swap_addressGive = addressGive

			address = self.coins[self.swap_indexTake].get_new_address()

			data = {'uuid' : self.swap_uuid,
					'cotk' : self.coins[self.swap_indexTake].symbol,
					'adtk' : address}

			self.send_ecc_packet(eccPacket.METH_swapRes, data)

		else:

			data = {'uuid' : '',
					'cotk' : '',
					'adtk' : '0'}

			self.send_ecc_packet(eccPacket.METH_swapRes, data)

	############################################################################

	def swap_response(self, symbolTake, addressTake):

		if addressTake == '0':

			self.append_message(0, 'Other party is unable or unwilling to receive swaped {}'.format(symbolTake))

			#TODO : Test this !!!

		if self.swap_pending and addressTake != '0':

			assert symbolTake == self.coins[self.swap_indexTake].symbol

			try:

				self.txid = self.coins[self.swap_indexTake].send_to_address(addressTake, str(self.swap_amountTake), "ecchat")

			except exc.RpcWalletUnlockNeeded: # TODO RpcWalletInsufficientFunds

				self.append_message(0, 'Wallet locked - please unlock')

			else:

				self.append_message(0, '{:f} {} sent to {}'.format(self.swap_amountTake, symbolTake, addressTake))

			# Send the METH_txidInf message - (coin, amount, address, txid)

			data = {'coin' : self.coins[self.swap_indexTake].symbol,
					'amnt' : '{:f}'.format(self.swap_amountTake),
					'addr' : addressTake,
					'txid' : self.txid}

			self.send_ecc_packet(eccPacket.METH_txidInf, data)

		# /execute command complete - reset state variables

		self.swap_pending    = False
		self.swap_uuid       = ''
		self.swap_timeout_h  = 0
		self.swap_amountGive = 0.0
		self.swap_amountTake = 0.0
		self.swap_indexGive  = 0
		self.swap_indexTake  = 0

	############################################################################

	def complete_swap(self):

		if self.swap_pending:

			try:

				self.txid = self.coins[self.swap_indexGive].send_to_address(self.swap_addressGive, str(self.swap_amountGive), "ecchat")

			except exc.RpcWalletUnlockNeeded: # TODO RpcWalletInsufficientFunds

				self.append_message(0, 'Wallet locked - please unlock')

			else:

				self.append_message(0, '{:f} {} sent to {}'.format(self.swap_amountGive, self.coins[self.swap_indexGive].symbol, self.swap_addressGive))

			# Send the METH_txidInf message - (coin, amount, address, txid)

			data = {'coin' : self.coins[self.swap_indexGive].symbol,
					'amnt' : '{:f}'.format(self.swap_amountGive),
					'addr' : self.swap_addressGive,
					'txid' : self.txid}

			self.send_ecc_packet(eccPacket.METH_txidInf, data)

		# /swap command complete - reset state variables

		self.swap_pending    = False
		self.swap_uuid       = ''
		self.swap_timeout_h  = 0
		self.swap_amountGive = 0.0
		self.swap_amountTake = 0.0
		self.swap_indexGive  = 0
		self.swap_indexTake  = 0

	############################################################################

	def timeout_swap(self, loop = None, data = None):

		if self.swap_pending:

			self.append_message(0, 'No /execute from other party - swap cancelled')

			# /swap command cancelled - reset state variables

			self.swap_pending    = False
			self.swap_uuid       = ''
			self.swap_timeout_h  = 0
			self.swap_amountGive = 0.0
			self.swap_amountTake = 0.0
			self.swap_indexGive  = 0
			self.swap_indexTake  = 0

	############################################################################

	def timeout_execute(self, loop = None, data = None):

		if self.swap_pending:

			self.append_message(0, 'No response from other party - swap cancelled')

			# /execute command cancelled - reset state variables

			self.swap_pending    = False
			self.swap_uuid       = ''
			self.swap_timeout_h  = 0
			self.swap_amountGive = 0.0
			self.swap_amountTake = 0.0
			self.swap_indexGive  = 0
			self.swap_indexTake  = 0

	############################################################################

	def echo_help(self):

		self.append_message(0, '%-8s - %s' % ('/help          ', 'display help - commands'))
		self.append_message(0, '%-8s - %s' % ('/keys          ', 'display help - keys'))
		self.append_message(0, '%-8s - %s' % ('/exit          ', 'exit - also /quit and ESC'))
		self.append_message(0, '%-8s - %s' % ('/version       ', 'display ecchat version info'))
		self.append_message(0, '%-8s - %s' % ('/blocks  <coin>', 'display block count'))
		self.append_message(0, '%-8s - %s' % ('/peers   <coin>', 'display peer count'))
		self.append_message(0, '%-8s - %s' % ('/tag           ', 'display routing tag public key'))
		self.append_message(0, '%-8s - %s' % ('/qr            ', 'display routing tag as QR code'))
		self.append_message(0, '%-8s - %s' % ('/balance <coin>', 'display wallet balance'))
		self.append_message(0, '%-8s - %s' % ('/address <coin>', 'generate a new address'))
		self.append_message(0, '%-8s - %s' % ('/send x  <coin>', 'send x to other party'))
		self.append_message(0, '%-8s - %s' % ('/txid          ', 'display txid of last transaction'))
		self.append_message(0, '%-8s - %s' % ('/list    <coin>', 'list all transactions this session'))
		self.append_message(0, '%-8s - %s' % ('         <coin>', 'optional coin symbol - defaults to ecc'))
		self.append_message(0, '%-8s - %s' % ('/swap x <coin-1> for y <coin-2>', 'proposes a swap'))
		self.append_message(0, '%-8s - %s' % ('/execute       ', 'executes the proposed swap'))

	############################################################################

	def echo_keys(self):

		self.append_message(0, '------------------------------------')
		self.append_message(0, 'Recall, replace, erase, scroll, exit')
		self.append_message(0, '------------------------------------')
		self.append_message(0, 'CURSOR UP/DOWN     - Recall previous message / command')
		self.append_message(0, 'ENTER              - Send as new message / command')
		self.append_message(0, 'ALT+ENTER          - Replace previous message')
		self.append_message(0, 'ALT+DELETE         - Erase previous message')
		self.append_message(0, 'ALT+CURSOR UP/DOWN - Scroll messages one line')
		self.append_message(0, 'PAGE UP/DOWN       - Scroll messages one page')
		self.append_message(0, 'ESCAPE             - Exit ecchat')

	############################################################################

	def echo_balance(self, coin):

		try:

			balance_con = coin.get_balance()
			balance_unl = coin.get_unlocked_balance()
			balance_unc = coin.get_unconfirmed_balance()

		except cryptoNodeException as error:

			self.append_message(0, str(error))

		else:

			if balance_con != balance_unl:

				if balance_unc > 0:

					self.append_message(0, '{} : {:f} confirmed ({:f} unlocked) + {:f} unconfirmed'.format(coin.symbol, balance_con, balance_unl, balance_unc))

				else:

					self.append_message(0, '{} : {:f} ({:f} unlocked)'.format(coin.symbol, balance_con, balance_unl))

			else:

				if balance_unc > 0:

					self.append_message(0, '{} : {:f} confirmed + {:f} unconfirmed'.format(coin.symbol, balance_con, balance_unc))

				else:

					self.append_message(0, '{} : {:f}'.format(coin.symbol, balance_con))

	############################################################################

	def echo_qrcode(self, text):

		qrdecode = [[' ', '\u2584'], ['\u2580', '\u2588']]

		lines = text.splitlines()

		lines_top = lines[::2]
		lines_bot = lines[1::2]

		if len(lines_bot) < len(lines_top):

			lines_bot.append(lines_bot[0])

		for i in range(0, len(lines_top)):

			qrline = ''

			for j in range(0, len(lines_top[i])):

				qrline += qrdecode[int(lines_top[i][j])][int(lines_bot[i][j])]

			self.append_message(0, qrline)

	############################################################################

	def echo_transactions(self, symbol):

		for tx in self.txSend.values():

			if tx.coin.symbol == symbol:

				self.append_message(0, 'TX: {} {} {:f} {} {}'.format(tx.time_tx.strftime('%x %X'), tx.coin.symbol, tx.f_amount, tx.addr, tx.txid))

		for tx in self.txReceive.values():

			if tx.coin.symbol == symbol:

				self.append_message(0, 'RX: {} {} {:f} {} {}'.format(tx.time_tx.strftime('%x %X'), tx.coin.symbol, tx.f_amount, tx.addr, tx.txid))

	############################################################################

	def process_user_entry(self, text):

		if len(text) > 0:

			uuid = str(uuid4())

			self.footerT.set_edit_text(u'')

			self.append_message(1, text, uuid, text.startswith('/'))

			if text.startswith('/exit'):

				self.check_quit('exit')

			elif text.startswith('/quit'):

				self.check_quit('quit')

			elif text.startswith('/help'):

				self.echo_help()

			elif text.startswith('/keys'):

				self.echo_keys()

			elif text.startswith('/version'):

				self.append_message(0, self.version)

			elif text.startswith('/blocks'):

				match = re.match('/blocks (?P<symbol>\w+)', text)

				if match:

					valid, index = self.check_symbol(match.group('symbol'))

					if valid:

						self.append_message(0, '{:d}'.format(self.coins[index].blocks))

					else:

						self.append_message(0, 'Unknown coin symbol: {}'.format(match.group('symbol')))

				else:

					for coin in self.coins:

						self.append_message(0, '{} : {:d}'.format(coin.symbol, coin.blocks))

			elif text.startswith('/peers'):

				match = re.match('/peers (?P<symbol>\w+)', text)

				if match:

					valid, index = self.check_symbol(match.group('symbol'))

					if valid:

						self.append_message(0, '{:d}'.format(self.coins[index].peers))

					else:

						self.append_message(0, 'Unknown coin symbol: {}'.format(match.group('symbol')))

				else:

					for coin in self.coins:

						self.append_message(0, '{} : {:d}'.format(coin.symbol, coin.peers))

			elif text.startswith('/tag'):

				self.append_message(0, '{}'.format(self.coins[0].routingTag))

			elif text.startswith('/qr'):

				self.echo_qrcode(pyqrcode.create(self.coins[0].routingTag).text(quiet_zone=2))

			elif text.startswith('/balance'):

				match = re.match('/balance (?P<symbol>\w+)', text)

				if match:

					valid, index = self.check_symbol(match.group('symbol'))

					if valid:

						self.echo_balance(self.coins[index])

					else:

						self.append_message(0, 'Unknown coin symbol: {}'.format(match.group('symbol')))

				else:

					for coin in self.coins:

						self.echo_balance(coin)

			elif text.startswith('/address'):

				match = re.match('/address (?P<symbol>\w+)', text)

				if match:

					valid, index = self.check_symbol(match.group('symbol'))

					if valid:

						address = self.coins[index].get_new_address()

						self.append_message(0, '{}'.format(address))

					else:

						self.append_message(0, 'Unknown coin symbol: {}'.format(match.group('symbol')))

				else:

					address = self.coins[0].get_new_address()

					self.append_message(0, '{}'.format(address))

			elif text.startswith('/send'):

				match_default = re.match('/send (?P<amount>([0-9]*\.)?[0-9]+)'                , text)
				match_symbol  = re.match('/send (?P<amount>([0-9]*\.)?[0-9]+) (?P<symbol>\w+)', text)

				if match_symbol:

					valid, index = self.check_symbol(match_symbol.group('symbol'))

					if valid:

						uuid = str(uuid4())

						self.txSend[uuid] = txSend(self, uuid, self.coins[index], match_symbol.group('amount'))

						self.txSend[uuid].do_checks()

					else:

						self.append_message(0, 'Unknown coin symbol: {}'.format(match_symbol.group('symbol')))

				elif match_default:

					uuid = str(uuid4())

					self.txSend[uuid] = txSend(self, uuid, self.coins[0], match_default.group('amount'))

					self.txSend[uuid].do_checks()

				else:

					self.append_message(0, 'Unknown command syntax - try /help for a list of commands')

			elif text.startswith('/swap'):

				match = re.match('/swap (?P<amountGive>([0-9]*\.)?[0-9]+) (?P<symbolGive>\w+) for (?P<amountTake>([0-9]*\.)?[0-9]+) (?P<symbolTake>\w+)', text)

				if match:

					validGive, indexGive = self.check_symbol(match.group('symbolGive'))
					validTake, indexTake = self.check_symbol(match.group('symbolTake'))

					if validGive and validTake:

						self.start_swap(match.group('amountGive'), indexGive,
										match.group('amountTake'), indexTake)

					else:

						if not validGive:

							self.append_message(0, 'Unknown coin symbol: {}'.format(match.group('symbolGive')))

						if not validTake:

							self.append_message(0, 'Unknown coin symbol: {}'.format(match.group('symbolTake')))

				else:

					self.append_message(0, 'Unknown command syntax - try /help for a list of commands')

			elif text.startswith('/execute'):

				self.swap_execute()

			elif text.startswith('/txid'):

				if self.txid:

					self.append_message(0, 'txid = %s' % self.txid)

				else:

					self.append_message(0, 'txid = %s' % 'none')

			elif text.startswith('/list'):

				match = re.match('/list (?P<symbol>\w+)', text)

				if match:

					valid, index = self.check_symbol(match.group('symbol'))

					if valid:

						self.echo_transactions(self.coins[index].symbol)

					else:

						self.append_message(0, 'Unknown coin symbol: {}'.format(match.group('symbol')))

				else:

					for coin in self.coins:

						self.echo_transactions(coin.symbol)


			elif text.startswith('/'):

				self.append_message(0, 'Unknown command syntax - try /help for a list of commands')

			else:

				data = {'uuid' : uuid,
						'cmmd' : 'add',
						'text' : text}

				self.send_ecc_packet(eccPacket.METH_chatMsg, data)

	############################################################################

	def process_user_replace(self, text):

		if len(text) > 0 and not text.startswith('/'):

			if uuid := self.walker.recall_uuid():

				self.footerT.set_edit_text(u'')

				self.replace_message(1, text, uuid, False)

				data = {'uuid' : uuid,
						'cmmd' : 'replace',
						'text' : text}

				self.send_ecc_packet(eccPacket.METH_chatMsg, data)

			else:

				self.process_user_entry(text)

	############################################################################

	def process_user_delete(self, text):

		if len(text) > 0 and not text.startswith('/'):

			if uuid := self.walker.recall_uuid():

				self.footerT.set_edit_text(u'')

				self.delete_message(1, text, uuid, False)

				data = {'uuid' : uuid,
						'cmmd' : 'delete',
						'text' : text}

				self.send_ecc_packet(eccPacket.METH_chatMsg, data)

	############################################################################

	def process_ecc_packet(self, ecc_packet):

		# Spam filter

		if ecc_packet.get_from() != self.otherTag:

			return

		if ecc_packet.get_meth() == eccPacket.METH_chatMsg:

			data = ecc_packet.get_data()

			if data['cmmd'] == 'add':

				self.append_message(2, data['text'], data['uuid'])

			if data['cmmd'] == 'replace':

				self.replace_message(2, data['text'], data['uuid'])

			if data['cmmd'] == 'delete':

				self.delete_message(2, data['text'], data['uuid'])

			rData = {'uuid' : data['uuid'],
					 'cmmd' : data['cmmd'],
					 'able' : True}

			self.send_ecc_packet(eccPacket.METH_chatAck, rData)

		elif ecc_packet.get_meth() == eccPacket.METH_chatAck:

			data = ecc_packet.get_data()

			self.ack_message(data['uuid'])

		elif ecc_packet.get_meth() == eccPacket.METH_addrReq:

			data = ecc_packet.get_data()

			valid, index = self.check_symbol(data['coin'])

			if valid:

				address = self.coins[index].get_new_address()

				rData = {'uuid' : data['uuid'],
						 'coin' : data['coin'],
						 'addr' : address}

				self.send_ecc_packet(eccPacket.METH_addrRes, rData)

		elif ecc_packet.get_meth() == eccPacket.METH_addrRes:

			data = ecc_packet.get_data()

			if 'uuid' in data:

				if data['uuid'] in self.txSend:

					self.txSend[data['uuid']].do_send(data['addr'])

		elif ecc_packet.get_meth() == eccPacket.METH_txidInf:

			data = ecc_packet.get_data()

			self.append_message(0, '{} {} received at {}'.format(data['amnt'], data['coin'], data['addr']))

			self.txid = data['txid']

			valid, index = self.check_symbol(data['coin'])

			if valid:

				self.txReceive[data['uuid']] = txReceive(self, data['uuid'], self.coins[index], data['amnt'], data['addr'], data['txid'])

			if self.swap_pending: #TIDY

				self.complete_swap()

		elif ecc_packet.get_meth() == eccPacket.METH_swapInf:

			data = ecc_packet.get_data()

			self.swap_proposed(data['cogv'], data['amgv'], data['cotk'], data['amtk'])

		elif ecc_packet.get_meth() == eccPacket.METH_swapReq:

			data = ecc_packet.get_data()

			self.swap_request(data['cogv'], data['adgv'])

		elif ecc_packet.get_meth() == eccPacket.METH_swapRes:

			data = ecc_packet.get_data()

			self.swap_response(data['cotk'], data['adtk'])

		else:

			pass

	############################################################################

	def unhandled_keypress(self, key):

		if isinstance(key, str):

			if key in ('up', 'down'): # prev entry recall with scrolling

				text = self.walker.recall(1, 2, {'up' : -1, 'down' : 1} [key])

				self.footerT.set_edit_text(text)

				self.footerT.set_edit_pos(len(text))

			if key in ('page up', 'page down'): # scroll only

				self.scrollT.key(key)

			if key in ('meta up', 'meta down'): # scroll only

				self.scrollT.key(key.split()[-1])

			if key in ('enter', ):

				self.process_user_entry(self.footerT.get_edit_text())

			if key in ('meta enter', 'meta left', 'meta right'):

				self.process_user_replace(self.footerT.get_edit_text())

			if key in ('meta delete', ):

				self.process_user_delete(self.footerT.get_edit_text())
				
			if key in ('esc', ):

				self.check_quit()

	############################################################################

	def check_quit(self, command = 'quit'):

		dialog = YesNoDialog(text = u'Do you want to %s ?' % command, loop = self.loop)

		urwid.connect_signal(dialog, 'commit', self.quit)

		dialog.show()

	############################################################################

	def quit(self, *args, **kwargs):

		# TODO - send exit notification for all connected parties

		raise urwid.ExitMainLoop()

	############################################################################

	def zmqInitialise(self):

		self.context    = zmq.Context()
		self.event_loop = zmqEventLoop()

		for index, coin in enumerate(self.coins):

			self.subscribers.append(self.context.socket(zmq.SUB))

			if coin.zmqAddress:

				self.subscribers[index].connect(coin.zmqAddress)
				self.subscribers[index].setsockopt(zmq.SUBSCRIBE, b'')

				self.event_loop.watch_queue(self.subscribers[index], self.zmqHandler, zmq.POLLIN, index)

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

			eccbuffer = self.coins[0].get_buffer(int(protocolID))

			if eccbuffer:

				for packet in eccbuffer.values():

					message = codecs.decode(packet, 'hex').decode()

					if self.debug:

						logging.info('RX: {}'.format(message))

					ecc_packet = eccPacket.from_json(message)

					self.process_ecc_packet(ecc_packet)

	############################################################################

	def zmqShutdown(self):

		for subscriber in self.subscribers:

			subscriber.close()

		self.context.term()

	############################################################################

	def cryptoInitialise(self):

		if loadConfigurationECC(self.coins, self.protocol_id) and loadConfigurationAlt(self.coins, self.conf):

			# TODO : Check coins[0] is online ???

			for coin in self.coins:

				try:

					coin.initialise()
					coin.refresh()

					if coin == self.coins[0]: # self.coins[0].symbol == 'ecc'

						coin.setup_route(self.otherTag)

				except cryptoNodeException as error:

					print(str(error))

					return False

			return True

		return False

	############################################################################

	def cryptoShutdown(self):

		for coin in self.coins:

			coin.shutdown()

	############################################################################

	def run(self):

		if self.cryptoInitialise():

			self.zmqInitialise()

			self.build_ui()

			self.loop = urwid.MainLoop(widget          = self.window,
			                           palette         = self._palette,
			                           handle_mouse    = True,
			                           unhandled_input = self.unhandled_keypress,
			                           event_loop      = self.event_loop)

			self.loop.set_alarm_in( 1, self.clock_refresh)

			self.loop.set_alarm_in(10, self.reset_buffer_timeout)

			self.loop.set_alarm_in(10, self.block_refresh_timed)

			self.loop.run()

			self.zmqShutdown()

		self.cryptoShutdown()

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

	logging.basicConfig(filename = 'log/ecchat-{:%Y-%m-%d}.log'.format(datetime.datetime.now()),
						filemode = 'a',
						level    = logging.INFO,
						format   = '%(asctime)s - %(levelname)s : %(message)s',
						datefmt  = '%d/%m/%Y %H:%M:%S')

	logging.info('STARTUP')

	signal.signal(signal.SIGINT,  terminate)  # keyboard interrupt ^C
	signal.signal(signal.SIGTERM, terminate)  # kill [default -15]

	argparser = argparse.ArgumentParser(description='Simple command line chat for ECC')

	argparser.add_argument('-n', '--name'  , action='store',      help='nickname    (local)' , type=str, default = ''           , required=True )
	argparser.add_argument('-o', '--other' , action='store',      help='nickname    (remote)', type=str, default = '[other]'    , required=False)
	argparser.add_argument('-t', '--tag'   , action='store',      help='routing tag (remote)', type=str, default = ''           , required=True )
	argparser.add_argument('-c', '--conf'  , action='store',      help='configuration file'  , type=str, default = 'ecchat.conf', required=False)
	argparser.add_argument('-d', '--debug' , action='store_true', help='debug message log'   ,                                    required=False)

	command_line_args = argparser.parse_args()

	logging.info('Arguments %s', vars(command_line_args))

	app = ChatApp(command_line_args.name,
	              command_line_args.other,
	              command_line_args.tag,
	              command_line_args.conf,
	              command_line_args.debug)

	app.run()

	logging.info('SHUTDOWN')

################################################################################

if __name__ == '__main__':

	main()

################################################################################
