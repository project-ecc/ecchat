#!/usr/bin/env python3
# coding: UTF-8

from datetime   import datetime
from eccpacket  import eccPacket
from cryptonode import cryptoNode, eccoinNode, bitcoinNode, moneroNode, cryptoNodeException

###########################################################################################
# TODO - Consider implementing a txObject base class that has parent/uuid/errorTxt,
# has do_failure and implements a callback registration mechanism back up to the zmqHandler
###########################################################################################

################################################################################
## txChat class ################################################################
################################################################################

class txChat():

	STATE_initial	= 1
	STATE_resolve	= 2
	STATE_request   = 3
	STATE_accept	= 4
	STATE_failure	= 5

	############################################################################

	def __init__(self, parent, uuid, name):

		self.parent   = parent
		self.uuid     = uuid
		self.name     = name
		self.tag      = ''
		self.errorTxt = ''

		self.tx_state = self.STATE_initial

	############################################################################

	def do_failure(self, text):

		self.errorTxt = text

		self.parent.append_message(0, self.errorTxt)

		self.tx_state = self.STATE_failure		

	############################################################################

	def ok_to_chat(self):

		return self.tx_state == self.STATE_accept

	############################################################################

	def is_routing_tag(self, targetRoute):

		return len(targetRoute) == 88 and targetRoute[-1] == '='

	############################################################################

	def resolve_chat(self):

		assert self.tx_state == self.STATE_initial

		self.tx_state = self.STATE_resolve

		if self.is_routing_tag(self.name):

			self.request_chat([self.name])

		else:

			self.parent.append_message(0, 'Attempting to resolve: {}'.format(self.name))

			# Try ecresolve name resolution

			data = {'uuid' : self.uuid,
					'name' : self.name,
					'type' : 'chatname'}

			self.parent.send_ecresolve_packet(eccPacket.METH_nameReq, data)

			self.parent.loop.set_alarm_in(5, self.do_resolve_timeout)

	############################################################################

	def do_resolve_timeout(self, loop = None, data = None):

		if self.tx_state == self.STATE_resolve:

			self.do_failure('Failed to resolve: {}'.format(self.name))

	############################################################################

	def request_chat(self, tags):

		if self.tx_state == self.STATE_resolve:

			if len(tags) > 0:

				self.tag = tags[0]

				if self.tag == self.parent.coins[0].routingTag:

					self.do_failure('Computer says no - you cannot talk to yourself')

					return

				self.parent.append_message(0, 'Resolved: {}'.format(self.name))

				try:

					self.parent.coins[0].setup_route(self.tag)

				except cryptoNodeException as error:

					self.do_failure(str(error))

					return

				# Request chat

				self.tx_state = self.STATE_request

				data = {'uuid' : self.uuid,
						'cmmd' : 'start',
						'name' : self.name}

				self.parent.send_ecchat_packet(eccPacket.METH_chatReq, data)

				self.parent.append_message(0, 'Chat request sent to: {}'.format(self.name))

				self.parent.loop.set_alarm_in(5, self.do_request_timeout)

			else:

				pass # awaiting response from other ecresolve instances, or timeout

	############################################################################

	def do_request_timeout(self, loop = None, data = None):

		if self.tx_state == self.STATE_request:

			self.parent.append_message(0, 'Waiting for chat request to be accepted by: {}'.format(self.name))

			self.parent.loop.set_alarm_in(5, self.do_request_timeout)

	############################################################################

	def start_chat(self, name):

		if self.tx_state == self.STATE_request:

			self.tx_state = self.STATE_accept

			self.name = name # For chats started by routing tag, this is the first time we discover other party name

			self.parent.append_message(0, 'Chat request accepted by: {}'.format(self.name))

			self.parent.set_party_name(2, self.name)
		
	############################################################################

	def stop_chat(self):

		if self.tx_state == self.STATE_accept:

			self.tx_state = self.STATE_initial

			self.parent.append_message(0, 'Chat ended with: {}'.format(self.name))

			self.parent.set_party_name(2, '')
		
################################################################################
## txSend class ################################################################
################################################################################

class txSend():

	STATE_initial	= 1
	STATE_checking	= 2
	STATE_addr_req	= 3
	STATE_complete	= 4
	STATE_failure	= 5

	STATE_SET = [STATE_initial,
				 STATE_checking,
				 STATE_addr_req,
				 STATE_complete,
				 STATE_failure]

	############################################################################

	def __init__(self, parent, uuid, coin, amount):

		self.parent   = parent
		self.uuid     = uuid
		self.coin     = coin
		self.addr     = ''
		self.txid     = ''
		self.time_tx  = 0.0
		self.s_amount = amount
		self.f_amount = 0.0
		self.unlRetry = 0
		self.unlLimit = 3
		self.errorTxt = ''

		self.tx_state = self.STATE_initial

	############################################################################

	def do_failure(self, text):

		self.errorTxt = text

		self.parent.append_message(0, self.errorTxt)

		self.tx_state = self.STATE_failure		

	############################################################################

	def do_checks(self):

		assert self.tx_state == self.STATE_initial

		self.tx_state = self.STATE_checking

		# Check 1 - Can the send amount be converted to a float correctly ?

		try:

			self.f_amount = float(self.s_amount)

		except ValueError:

			self.do_failure('Invalid send amount - number expected')

			return

		# Check 2 - Is the send amount in a sensible range ?

		if self.f_amount <= 0:

			self.do_failure('Invalid send amount - must be greater than zero')

			return

		# Check 3 - Does the user's wallet hold an adequate balance ?

		try:

			balance = self.coin.get_unlocked_balance()

		except cryptoNodeException as error:

			self.do_failure(str(error))

			return

		if self.f_amount >= balance:

			self.do_failure('Invalid send amount - must be less than current balance = {:f}'.format(balance))

			return

		# Check 4 - Ensure the user's wallet is unlocked (separate due to retry mechanism)

		self.do_wallet_unlocked_check()

	############################################################################

	def do_wallet_unlocked_check(self):

		assert self.tx_state == self.STATE_checking

		if self.coin.wallet_locked(cache_prior_state = (self.unlRetry == 0)):

			self.unlRetry += 1

			if self.unlRetry > self.unlLimit:

				self.do_failure('Wallet unlock - {} attempts failed : {}'.format(self.unlLimit,self.coin.symbol))

				return

			self.parent.show_passphrase_dialog(self.coin.symbol, self.unlRetry, self.unlLimit, self.passphrase_callback)

		else:

			self.do_addr_req()

	############################################################################

	def passphrase_callback(self, status, passphrase):

		assert self.tx_state == self.STATE_checking

		if status:

			if passphrase:

				self.coin.unlock_wallet(passphrase, 60)

			self.do_wallet_unlocked_check()

		else:

			self.do_failure('Wallet unlock cancelled: {}'.format(self.coin.symbol))

	############################################################################

	def do_addr_req(self):

		assert self.tx_state == self.STATE_checking

		self.tx_state = self.STATE_addr_req		

		# Request address from peer

		data = {'uuid' : self.uuid,
				'coin' : self.coin.symbol,
				'type' : 'P2PKH'}

		self.parent.send_ecchat_packet(eccPacket.METH_addrReq, data)

		self.parent.loop.set_alarm_in(10, self.do_addr_req_timeout)

	############################################################################

	def do_addr_req_timeout(self, loop = None, data = None):

		if self.tx_state == self.STATE_addr_req:

			self.do_failure('No response from other party - /send cancelled')

			self.coin.revert_wallet_lock()

	############################################################################

	def do_send(self, addr):

		assert self.tx_state == self.STATE_addr_req

		self.addr = addr

		if addr == '0':

			self.do_failure('Other party is unable or unwilling to receive unsolicited sends of {}'.format(self.coin.symbol))

			self.coin.revert_wallet_lock()
			
			return

		if (self.tx_state == self.STATE_addr_req) and addr != '0':

			try:

				self.txid = self.coin.send_to_address(addr, str(self.f_amount), "ecchat")

				self.coin.revert_wallet_lock()

			except cryptoNodeException as error:

				self.do_failure(str(error))

				return

			else:

				self.time_tx  = datetime.now()

				self.parent.append_message(0, '{:f} {} sent to {}'.format(self.f_amount, self.coin.symbol, self.addr))

				# Send the METH_txidInf message - (uuid, coin, amount, address, txid)

				data = {'uuid' : self.uuid,
						'coin' : self.coin.symbol,
						'amnt' : '{:f}'.format(self.f_amount),
						'addr' : self.addr,
						'txid' : self.txid}

				self.parent.send_ecchat_packet(eccPacket.METH_txidInf, data)

				self.parent.txid = self.txid # TIDY

				self.tx_state = self.STATE_complete

################################################################################
## txReceive class #############################################################
################################################################################

class txReceive():

	############################################################################

	def __init__(self, parent, uuid, coin, amount, addr, txid):

		self.parent   = parent
		self.uuid     = uuid
		self.coin     = coin
		self.s_amount = amount
		self.f_amount = float(amount)
		self.addr     = addr
		self.txid     = txid
		self.time_tx  = datetime.now()

################################################################################
