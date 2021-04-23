#!/usr/bin/env python3
# coding: UTF-8

from eccpacket  import eccPacket
from cryptonode import cryptoNode, cryptoNodeException

################################################################################
## txSend class ################################################################
################################################################################

class txSend():

	STATE_SET = [STATE_initial,
				 STATE_checking,
				 STATE_addr_req,
				 STATE_complete]

	############################################################################

	def __init__(self, parent, uuid, coin, amount):

		self.parent   = parent
		self.uuid     = uuid
		self.coin     = coin
		self.s_amount = amount
		self.f_amount = 0.0

		self.tx_state = STATE_initial

	############################################################################

	def do_checks():

		assert self.tx_state == STATE_initial

		# TODO

		self.tx_state = STATE_checking
		
	############################################################################

	def do_addr_req():

		assert self.tx_state == STATE_checking

		# TODO

		self.tx_state = STATE_addr_req		

	############################################################################

	def do_send():

		assert self.tx_state == STATE_addr_req

		#TODO

		self.tx_state = STATE_complete		
		
################################################################################
