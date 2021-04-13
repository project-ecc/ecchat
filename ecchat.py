#!/usr/bin/env python3
# coding: UTF-8

import datetime
import settings
import argparse
import pyqrcode
import pathlib
import logging
import signal
import codecs
import urwid
import time
import zmq
import sys
import re

from uuid import uuid4

# ZMQ event loop adapter for urwid

from zmqeventloop import zmqEventLoop

#from slickrpc import Proxy
from slickrpc import exc # RpcWalletUnlockNeeded only TO BE REMOVED !!!!!

# eccPacket & cryptoNode classes

from eccpacket  import eccPacket
from cryptonode import cryptoNode, eccoinNode, bitcoinNode, litecoinNode, moneroNode, cryptoNodeException

# urwid extension classes

from urwidext import GridFlowPlus, YesNoDialog, PasswordDialog, MessageListBox, FrameFocus, MessageWalker

coins = []

for index, chain in enumerate(settings.chains):

	if index == 0:

		if chain['coin_symbol'] != 'ecc':

			print('ecc must be the first configured chain')

			sys.exit()

	if chain['coin_symbol'] == 'ecc':

		coins.append(eccoinNode(chain['coin_symbol'], chain['rpc_address'], chain['rpc_user'], chain['rpc_pass'], settings.protocol_id))

	elif chain['coin_symbol'] == 'ltc':

		coins.append(litecoinNode(chain['coin_symbol'], chain['rpc_address'], chain['rpc_user'], chain['rpc_pass']))

	elif chain['coin_symbol'] == 'xmr':

		coins.append(moneroNode(chain['coin_symbol'], chain['rpc_address'],chain['rpc_daemon'], chain['rpc_user'], chain['rpc_pass']))

	else:

		coins.append(bitcoinNode(chain['coin_symbol'], chain['rpc_address'], chain['rpc_user'], chain['rpc_pass']))

################################################################################

def check_symbol(symbol):

	return_valid = False
	return_index = 0

	for index, coin in enumerate(coins):

		if symbol.lower() == coin.symbol:

			return_valid = True
			return_index = index

	return return_valid, return_index

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
		self.send_amount  = 0.0
		self.send_index   = 0

		self.swap_pending    = False
		self.swap_uuid       = ''
		self.swap_timeout_h  = 0
		self.swap_amountGive = 0.0
		self.swap_amountTake = 0.0
		self.swap_indexGive  = 0
		self.swap_indexTake  = 0

		self.txid = ''

		self.subscribers = []

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

		ecc_packet = eccPacket(settings.protocol_id, settings.protocol_ver, self.otherTag, coins[0].routingTag, meth, data)

		logging.info(ecc_packet.to_json())

		ecc_packet.send(coins[0])

	############################################################################

	def append_message(self, party, text, uuid = '', ack = True):

		tstyle = {True : self.party_text_style[party], False : 'tnak'} [ack]

		markup = [('time', time.strftime(self._clock_fmt)), (self.party_name_style[party], u'{0:>{1}s} {2} '.format(self.party_name[party], self.party_size, self.party_separator[party])), (tstyle, text)]

		self.walker.append(party, markup, uuid)

		self.scrollT.set_focus(len(self.scrollT.body) - 1)

	############################################################################

	def ack_message(self, uuid):

		self.walker.set_markup_style(uuid, 2, 'tack')

	############################################################################

	def clock_refresh(self, loop = None, data = None):

		text = time.strftime(self._clock_fmt)

		for coin in coins:

			text += ' {} # {:d}/{:d} '.format(coin.symbol, coin.blocks, coin.peers)

		self.statusT.set_text(text)

		loop.set_alarm_in(1, self.clock_refresh)

	############################################################################

	def reset_buffer_timeout(self, loop = None, data = None):

		if coins[0].reset_buffer_timeout():

			loop.set_alarm_in(10, self.reset_buffer_timeout)

	############################################################################

	def block_refresh_timed(self, loop = None, data = None):

		for coin in coins:

			if not coin.zmqAddress:

				coin.refresh()

		loop.set_alarm_in(10, self.block_refresh_timed)

	############################################################################

	def block_refresh(self, index):

		coins[index].refresh()

	############################################################################

	def start_send(self, amount, index):

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

		balance = coins[index].get_unlocked_balance()

		if float_amount >= balance:

			self.append_message(0, 'Invalid send amount - must be less than current balance = {:f}'.format(balance))

			return

		# Check 5 - Ensure the user's wallet is unlocked

		while coins[index].wallet_locked():

			passphrase = 'TODO'

			coins[index].unlock_wallet(passphrase, 60)

		# Request address from peer

		data = {'coin' : coins[index].symbol,
				'type' : 'P2PKH'}

		self.send_ecc_packet(eccPacket.METH_addrReq, data)

		self.loop.set_alarm_in(10, self.timeout_send)

		self.send_pending = True
		self.send_amount  = float_amount
		self.send_index   = index

	############################################################################

	def complete_send(self, address):

		if address == '0':

			self.append_message(0, 'Other party is unable or unwilling to receive unsolicited sends of {}'.format(coins[self.send_index].symbol))

			#TODO : Test this !!!

		if self.send_pending and address != '0':

			try:

				self.txid = coins[self.send_index].send_to_address(address, str(self.send_amount), "ecchat")

			except exc.RpcWalletUnlockNeeded: # TODO RpcWalletInsufficientFunds

				self.append_message(0, 'Wallet locked - please unlock')

			else:

				self.append_message(0, '{:f} {} sent to {} [/txid available]'.format(self.send_amount, coins[self.send_index].symbol,address))

			# Send the METH_txidInf message - (coin, amount, address, txid)

			data = {'coin' : coins[self.send_index].symbol,
					'amnt' : '{:f}'.format(self.send_amount),
					'addr' : address,
					'txid' : self.txid}

			self.send_ecc_packet(eccPacket.METH_txidInf, data)

		# /send command complete - reset state variables

		self.send_pending = False
		self.send_amount  = 0.0
		self.send_index   = 0

	############################################################################

	def timeout_send(self, loop = None, data = None):

		if self.send_pending:

			self.append_message(0, 'No response from other party - /send cancelled')

			# /send command cancelled - reset state variables

			self.send_pending = False
			self.send_amount  = 0.0
			self.send_index   = 0

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

		balance = coins[indexGive].get_unlocked_balance()

		if float_amountGive >= balance:

			self.append_message(0, 'Invalid swap amount - must be less than current balance = {:f}'.format(balance))

			return

		# Check 5 - Ensure the user's wallet is unlocked

		# TODO

		# Send swap information

		data = {'uuid' : str(uuid4()),
				'cogv' : coins[indexGive].symbol,
				'amgv' : float_amountGive,
				'cotk' : coins[indexTake].symbol,
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

		validGive, indexGive = check_symbol(symbolGive)
		validTake, indexTake = check_symbol(symbolTake)

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

		balance = coins[indexTake].get_unlocked_balance()

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

		address = coins[self.swap_indexGive].get_new_address()

		data = {'uuid' : self.swap_uuid,
				'cogv' : coins[self.swap_indexGive].symbol,
				'adgv' : address}

		self.send_ecc_packet(eccPacket.METH_swapReq, data)

		self.loop.set_alarm_in(10, self.timeout_execute)

	############################################################################

	def swap_request(self, symbolGive, addressGive):

		if self.swap_pending:

			assert symbolGive == coins[self.swap_indexGive].symbol

			self.swap_addressGive = addressGive

			address = coins[self.swap_indexTake].get_new_address()

			data = {'uuid' : self.swap_uuid,
					'cotk' : coins[self.swap_indexTake].symbol,
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

			assert symbolTake == coins[self.swap_indexTake].symbol

			try:

				self.txid = coins[self.swap_indexTake].send_to_address(addressTake, str(self.swap_amountTake), "ecchat")

			except exc.RpcWalletUnlockNeeded: # TODO RpcWalletInsufficientFunds

				self.append_message(0, 'Wallet locked - please unlock')

			else:

				self.append_message(0, '{:f} {} sent to {} [/txid available]'.format(self.swap_amountTake, symbolTake, addressTake))

			# Send the METH_txidInf message - (coin, amount, address, txid)

			data = {'coin' : coins[self.swap_indexTake].symbol,
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

				self.txid = coins[self.swap_indexGive].send_to_address(self.swap_addressGive, str(self.swap_amountGive), "ecchat")

			except exc.RpcWalletUnlockNeeded: # TODO RpcWalletInsufficientFunds

				self.append_message(0, 'Wallet locked - please unlock')

			else:

				self.append_message(0, '{:f} {} sent to {} [/txid available]'.format(self.swap_amountGive, coins[self.swap_indexGive].symbol, self.swap_addressGive))

			# Send the METH_txidInf message - (coin, amount, address, txid)

			data = {'coin' : coins[self.swap_indexGive].symbol,
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

	def echo_balance(self, coin):

		balance_con = coin.get_balance()
		balance_unl = coin.get_unlocked_balance()
		balance_unc = coin.get_unconfirmed_balance()

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

				self.append_message(0, '%-8s - %s' % ('/help          ', 'display help information'))
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
				self.append_message(0, '%-8s - %s' % ('         <coin>', 'coin symbol - defaults to ecc'))
				self.append_message(0, '%-8s - %s' % ('/swap x <coin-1> for y <coin-2>', 'proposes a swap'))
				self.append_message(0, '%-8s - %s' % ('/execute       ', 'executes the proposed swap'))

			elif text.startswith('/version'):

				self.append_message(0, self.version)

			elif text.startswith('/blocks'):

				match = re.match('/blocks (?P<symbol>\w+)', text)

				if match:

					valid, index = check_symbol(match.group('symbol'))

					if valid:

						self.append_message(0, '{:d}'.format(coins[index].blocks))

					else:

						self.append_message(0, 'Unknown coin symbol: {}'.format(match.group('symbol')))

				else:

					for coin in coins:

						self.append_message(0, '{} : {:d}'.format(coin.symbol, coin.blocks))

			elif text.startswith('/peers'):

				match = re.match('/peers (?P<symbol>\w+)', text)

				if match:

					valid, index = check_symbol(match.group('symbol'))

					if valid:

						self.append_message(0, '{:d}'.format(coins[index].peers))

					else:

						self.append_message(0, 'Unknown coin symbol: {}'.format(match.group('symbol')))

				else:

					for coin in coins:

						self.append_message(0, '{} : {:d}'.format(coin.symbol, coin.peers))

			elif text.startswith('/tag'):

				self.append_message(0, '{}'.format(coins[0].routingTag))

			elif text.startswith('/qr'):

				self.echo_qrcode(pyqrcode.create(coins[0].routingTag).text(quiet_zone=2))

			elif text.startswith('/balance'):

				match = re.match('/balance (?P<symbol>\w+)', text)

				if match:

					valid, index = check_symbol(match.group('symbol'))

					if valid:

						self.echo_balance(coins[index])

					else:

						self.append_message(0, 'Unknown coin symbol: {}'.format(match.group('symbol')))

				else:

					for coin in coins:

						self.echo_balance(coin)

			elif text.startswith('/address'):

				match = re.match('/address (?P<symbol>\w+)', text)

				if match:

					valid, index = check_symbol(match.group('symbol'))

					if valid:

						address = coins[index].get_new_address()

						self.append_message(0, '{}'.format(address))

					else:

						self.append_message(0, 'Unknown coin symbol: {}'.format(match.group('symbol')))

				else:

					address = coins[0].get_new_address()

					self.append_message(0, '{}'.format(address))

			elif text.startswith('/send'):

				match_default = re.match('/send (?P<amount>([0-9]*\.)?[0-9]+)'                , text)
				match_symbol  = re.match('/send (?P<amount>([0-9]*\.)?[0-9]+) (?P<symbol>\w+)', text)

				if match_symbol:

					valid, index = check_symbol(match_symbol.group('symbol'))

					if valid:

						self.start_send(match_symbol.group('amount'), index)

					else:

						self.append_message(0, 'Unknown coin symbol: {}'.format(match_symbol.group('symbol')))

				elif match_default:

					self.start_send(match_default.group('amount'), 0)

				else:

					self.append_message(0, 'Unknown command syntax - try /help for a list of commands')

			elif text.startswith('/swap'):

				match = re.match('/swap (?P<amountGive>([0-9]*\.)?[0-9]+) (?P<symbolGive>\w+) for (?P<amountTake>([0-9]*\.)?[0-9]+) (?P<symbolTake>\w+)', text)

				if match:

					validGive, indexGive = check_symbol(match.group('symbolGive'))
					validTake, indexTake = check_symbol(match.group('symbolTake'))

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

			elif text.startswith('/'):

				self.append_message(0, 'Unknown command syntax - try /help for a list of commands')

			else:

				data = {'uuid' : uuid,
						'cmmd' : 'add',
						'text' : text}

				self.send_ecc_packet(eccPacket.METH_chatMsg, data)

	############################################################################

	def unhandled_keypress(self, key):

		if isinstance(key, str):

			if key in ('up', 'down'):

				#self.scrollT.key(key)

				######################################################
				self.scrollT.set_focus(max(0, self.walker.focus - 1))
				######################################################

				markup = self.walker.text[self.walker.focus]

				(style, text) = markup[2]

				self.footerT.set_edit_text(text)

				######################################################

			if key in ('page up', 'page down'):

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

		for index, coin in enumerate(coins):

			self.subscribers.append(self.context.socket(zmq.SUB))

			if coin.zmqAddress:

				self.subscribers[index].connect(coin.zmqAddress)
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

			eccbuffer = coins[0].get_buffer(int(protocolID))

			if eccbuffer:

				for packet in eccbuffer.values():

					message = codecs.decode(packet, 'hex').decode()

					ecc_packet = eccPacket.from_json(message)

					if ecc_packet.get_meth() == eccPacket.METH_chatMsg:

						data = ecc_packet.get_data()

						if data['cmmd'] == 'add':

							self.append_message(2, data['text'], data['uuid'])

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

						if data['cmmd'] == 'add':

							self.ack_message(data['uuid'])

					elif ecc_packet.get_meth() == eccPacket.METH_addrReq:

						data = ecc_packet.get_data()

						valid, index = check_symbol(data['coin'])

						if valid:

							address = coins[index].get_new_address()

							rData = {'coin' : data['coin'],
									 'addr' : address}

							self.send_ecc_packet(eccPacket.METH_addrRes, rData)

					elif ecc_packet.get_meth() == eccPacket.METH_addrRes:

						data = ecc_packet.get_data()

						self.complete_send(data['addr'])

					elif ecc_packet.get_meth() == eccPacket.METH_txidInf:

						data = ecc_packet.get_data()

						self.append_message(0, '{} {} received at {} [/txid available]'.format(data['amnt'], data['coin'], data['addr']))

						self.txid = data['txid']

						if self.swap_pending:

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

	def cryptoInitialise(self):

		for coin in coins:

			try:

				coin.initialise()
				coin.refresh()

				if coin == coins[0]: # coins[0].symbol == 'ecc'

					coin.setup_route(self.otherTag)

			except cryptoNodeException as error:

				print(error)

				return False

		return True

	############################################################################

	def cryptoShutdown(self):

		for coin in coins:

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
