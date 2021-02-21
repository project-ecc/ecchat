#!/usr/bin/env python3
# coding: UTF-8

from slickrpc import Proxy
from slickrpc import exc

################################################################################
## cryptoNode class ############################################################
################################################################################

class cryptoNode():

	############################################################################

	def __init__(self, symbol, rpc_address, rpc_user, rpc_pass):

		self.symbol			= symbol
		self.rpc_address	= rpc_address
		self.rpc_user		= rpc_user
		self.rpc_pass		= rpc_pass

	############################################################################

	def __getattr__(self, method):

		raise NotImplementedError

	############################################################################

	def initialise(self):

		raise NotImplementedError

	############################################################################

	def shutdown(self):

		raise NotImplementedError

################################################################################
## eccoinNode class ############################################################
################################################################################

class eccoinNode(cryptoNode):

	############################################################################

	def __init__(self, symbol, rpc_address, rpc_user, rpc_pass):

		super().__init__(symbol, rpc_address, rpc_user, rpc_pass)

		self.proxy = Proxy('http://%s:%s@%s' % (rpc_user, rpc_pass, rpc_address))

	############################################################################

	def __getattr__(self, method):

		return getattr(self.proxy, method)

	############################################################################

	def initialise(self):

		pass

	############################################################################

	def shutdown(self):

		pass

################################################################################
## bitcoinNode class ############################################################
################################################################################

class bitcoinNode(cryptoNode):

	############################################################################

	def __init__(self, symbol, rpc_address, rpc_user, rpc_pass):

		super().__init__(symbol, rpc_address, rpc_user, rpc_pass)

		self.proxy = Proxy('http://%s:%s@%s' % (rpc_user, rpc_pass, rpc_address))

	############################################################################

	def __getattr__(self, method):

		return getattr(self.proxy, method)

	############################################################################

	def initialise(self):

		pass

	############################################################################

	def shutdown(self):

		pass

################################################################################
## moneroNode class ############################################################
################################################################################

class moneroNode(cryptoNode):

	############################################################################

	def __init__(self, symbol, rpc_address, rpc_user, rpc_pass):

		super().__init__(symbol, rpc_address, rpc_user, rpc_pass)

#		self.proxy = Proxy('http://%s:%s@%s' % (rpc_user, rpc_pass, rpc_address))

	############################################################################

	def __getattr__(self, method):

#		return getattr(self.proxy, method)

		pass

	############################################################################

	def initialise(self):

		pass

	############################################################################

	def shutdown(self):

		pass

################################################################################
