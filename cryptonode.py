#!/usr/bin/env python3
# coding: UTF-8

import settings
import pycurl

from slickrpc import Proxy
from slickrpc import exc

################################################################################
## cryptoNode class ############################################################
################################################################################

class cryptoNode():

	############################################################################

	def __init__(self, symbol, rpc_address, rpc_user, rpc_pass):

		self.symbol      = symbol.lower()
		self.rpc_address = rpc_address
		self.rpc_user    = rpc_user
		self.rpc_pass    = rpc_pass

	############################################################################

	def __getattr__(self, method):

		raise NotImplementedError

	############################################################################

	def symbol(self):

		return self.symbol

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

	version_min = 30000
	version_max = 30000

	############################################################################

	def __init__(self, symbol, rpc_address, rpc_user, rpc_pass):

		super().__init__(symbol, rpc_address, rpc_user, rpc_pass)

		self.proxy = Proxy('http://%s:%s@%s' % (rpc_user, rpc_pass, rpc_address))

		self.routingTag = ''
		self.bufferKey  = ''

	############################################################################

	def __getattr__(self, method):

		return getattr(self.proxy, method)

	############################################################################

	def initialise(self):

		try:

			info = self.proxy.getinfo()

		except pycurl.error:

			print('Failed to connect - check that local eccoin daemon is running')

			return False

		except exc.RpcInWarmUp:

			print('Failed to connect - local eccoin daemon is starting but not ready - try again after 60 seconds')

			return False

		if not self.version_min <= info['version'] <= self.version_max:

			print('eccoind version {} not supported - please run a version in the range {}-{}'.format(info['version'], self.version_min, self.version_max))

			return False

		try:

			self.routingTag = self.proxy.getroutingpubkey()
			self.bufferKey  = self.proxy.registerbuffer(settings.protocol_id)

		except exc.RpcInternalError:

			print('API Buffer was not correctly unregistered - try again after 60 seconds')

			return False

		return True

	############################################################################

	def shutdown(self):

		if self.bufferKey:

			bufferSig = self.proxy.buffersignmessage(self.bufferKey, 'ReleaseBufferRequest')

			self.proxy.releasebuffer(settings.protocol_id, bufferSig)

			self.bufferKey = ''

	############################################################################

	def reset_buffer_timeout(self):

		if self.bufferKey:

			bufferSig = self.proxy.buffersignmessage(self.bufferKey, 'ResetBufferTimeout')

			self.proxy.resetbuffertimeout(settings.protocol_id, bufferSig)

			return True

		return False

	#TEMPORARY#TEMPORARY#TEMPORARY#TEMPORARY#TEMPORARY#TEMPORARY#TEMPORARY#TEMPORARY

	def routingTag(self):

		return self.routingTag

	#TEMPORARY#TEMPORARY#TEMPORARY#TEMPORARY#TEMPORARY#TEMPORARY#TEMPORARY#TEMPORARY

	def bufferKey(self):

		return self.bufferKey

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
