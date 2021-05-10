#!/usr/bin/env python3
# coding: UTF-8

from datetime   import datetime
from eccpacket  import eccPacket
from cryptonode import cryptoNode, eccoinNode, bitcoinNode, moneroNode, cryptoNodeException

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

		if self.coin.wallet_locked():

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

		self.parent.send_ecc_packet(eccPacket.METH_addrReq, data)

		self.parent.loop.set_alarm_in(10, self.do_addr_req_timeout)

	############################################################################

	def do_addr_req_timeout(self, loop = None, data = None):

		if self.tx_state == self.STATE_addr_req:

			self.do_failure('No response from other party - /send cancelled')

	############################################################################

	def do_send(self, addr):

		assert self.tx_state == self.STATE_addr_req

		self.addr = addr

		if addr == '0':

			self.do_failure('Other party is unable or unwilling to receive unsolicited sends of {}'.format(self.coin.symbol))

			#TODO : Test this !!!

			return

		if (self.tx_state == self.STATE_addr_req) and addr != '0':

			try:

				self.txid = self.coin.send_to_address(addr, str(self.f_amount), "ecchat")

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

				self.parent.send_ecc_packet(eccPacket.METH_txidInf, data)

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
