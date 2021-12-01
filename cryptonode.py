#!/usr/bin/env python3
# coding: UTF-8

import sys
import pycurl
import requests

from itertools import count

# RPC interface for Bitcoin type nodes

from slickrpc import Proxy
from slickrpc import exc

# RPC interface for Monero type nodes

from monero.wallet import Wallet
from monero.daemon import Daemon
from monero.transaction import PaymentFilter

import monero.exceptions

# DNS resolver to boot strap ecc name services

import dns.resolver

################################################################################
## cryptoNodeException class ###################################################
################################################################################

class cryptoNodeException(Exception):

	############################################################################

	def __init__(self, message):

		super().__init__(message)

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

		self.available   = False

		self.blocks      = 0
		self.peers       = 0

		self.zmqAddress  = ''

		self.no_refresh  = False	# Used by owner to suppress refresh() calls during sync/catchup

	############################################################################

	def __getattr__(self, method):

		raise NotImplementedError

	############################################################################

	def initialise(self):

		raise NotImplementedError

	############################################################################

	def refresh(self):

		raise NotImplementedError

	############################################################################

	def get_balance(self):

		raise NotImplementedError

	############################################################################

	def get_unlocked_balance(self):

		raise NotImplementedError

	############################################################################

	def get_unconfirmed_balance(self):

		raise NotImplementedError

	############################################################################

	def get_new_address(self):

		raise NotImplementedError

	############################################################################

	def wallet_locked(self):

		raise NotImplementedError

	############################################################################

	def unlock_wallet(self, passphrase, seconds):

		raise NotImplementedError

	############################################################################

	def send_to_address(self):

		raise NotImplementedError

	############################################################################

	def shutdown(self):

		raise NotImplementedError

################################################################################
## eccoinNode class ############################################################
################################################################################

class eccoinNode(cryptoNode):

	version_min = 30000
	version_max = 99999
	win_zmq_bug = 30300

	version_fPacketSig = 30300

	serviceIdx = count(start=1)
	respondIdx = count(start=1)

	############################################################################

	def __init__(self, symbol, rpc_address, rpc_user, rpc_pass, service_id = 1, respond_id = None):

		super().__init__(symbol, rpc_address, rpc_user, rpc_pass)

		self.proxy = Proxy('http://%s:%s@%s' % (rpc_user, rpc_pass, rpc_address)) # Not thread safe ...
		self.prox2 = Proxy('http://%s:%s@%s' % (rpc_user, rpc_pass, rpc_address)) # ... hence needing 2

		self.serviceId  = service_id
		self.respondId  = respond_id
		self.serviceKey = ''
		self.respondKey = ''

		self.routingTag = ''

		self.ecresolve_tags = []

		# ECC feature flags (based on version number)

		self.fPacketSig = False

	############################################################################

	def __getattr__(self, method):

		return getattr(self.proxy, method)

	############################################################################

	def initialise(self):

		try:

			info = self.proxy.getnetworkinfo()

		except ValueError:

			raise cryptoNodeException('Failed to connect - error in rpcuser or rpcpassword for eccoin')

		except pycurl.error:

			raise cryptoNodeException('Failed to connect - check that eccoin daemon is running')

		except exc.RpcInWarmUp:

			raise cryptoNodeException('Failed to connect -  eccoin daemon is starting but not ready - try again after 60 seconds')

		except exc.RpcMethodNotFound:

			raise cryptoNodeException('RPC getnetworkinfo unavailable for {} daemon'.format(self.symbol))

		# ECC daemon version checking and feature enablement

		if not self.version_min <= info['version'] <= self.version_max:

			raise cryptoNodeException('eccoind version {} not supported - please run a version in the range {}-{}'.format(info['version'], self.version_min, self.version_max))

		if (info['version'] == self.win_zmq_bug) and (sys.platform in ['win32', 'cygwin']):

			raise cryptoNodeException('eccoind version {} not supported on Windows - please upgrade'.format(info['version']))

		self.fPacketSig = info['version'] >= self.version_fPacketSig

		# ECC messaging buffer setup

		try:

			self.routingTag = self.proxy.getroutingpubkey()

			if self.serviceId:

				self.serviceKey = self.proxy.registerbuffer(self.serviceId)

			if self.respondId:

				self.respondKey = self.proxy.registerbuffer(self.respondId)

		except exc.RpcInternalError:

			raise cryptoNodeException('API Buffer was not correctly unregistered or another instance running - try again after 60 seconds')

		# ZMQ detection and configuration loading

		try:

			zmqnotifications = self.proxy.getzmqnotifications()

		except pycurl.error:

			raise cryptoNodeException('Blockchain node for {} not available or incorrectly configured'.format(self.symbol))

		except (exc.RpcMethodNotFound, ValueError):

			zmqnotifications = []

		for zmqnotification in zmqnotifications:

			if zmqnotification['type'] == 'pubhashblock':

				self.zmqAddress = zmqnotification['address']

		# Load ecresolve routing tags and setup routes for subsequent ecc network name resolution

		self.ecresolve_tags = self.get_ecresolve_tags()

		route = []

		for tag in self.ecresolve_tags:

			try:

				self.proxy.findroute(tag)

				route.append(self.proxy.haveroute(tag))

			except exc.RpcInvalidAddressOrKey:

				raise cryptoNodeException('Routing tag for ecresolve has invalid base64 encoding : {}'.format(tag))

		if not any(route):

			raise cryptoNodeException('No route available to ecresolve across all {} configured routing tags'.format(len(self.ecresolve_tags)))

	############################################################################

	def refresh(self):

		self.blocks = self.proxy.getblockcount()
		self.peers  = self.proxy.getconnectioncount()

	############################################################################

	def get_balance(self):

		return self.proxy.getbalance()

	############################################################################

	def get_unlocked_balance(self):

		return self.proxy.getbalance()

	############################################################################

	def get_unconfirmed_balance(self):

		return self.proxy.getunconfirmedbalance()

	############################################################################

	def get_new_address(self):

		return self.proxy.getnewaddress()

	############################################################################

	def wallet_locked(self):

		info = self.proxy.getwalletinfo()

		# TODO : Handle staking_only_unlock
		# TODO : Check that the unlock remains in force for sufficient time

		if 'unlocked_until' in info:

			return info['unlocked_until'] == 0

		return False

	############################################################################

	def unlock_wallet(self, passphrase, seconds, staking = False):

		try:

			self.proxy.walletpassphrase(passphrase, seconds, staking)

		except exc.RpcWalletPassphraseIncorrect:

			return False

		else:

			return True

	############################################################################

	def send_to_address(self, address, amount, comment):

		try:

			txid = self.proxy.sendtoaddress(address, amount, comment)

		except exc.RpcWalletUnlockNeeded:

			raise cryptoNodeException('Wallet locked - please unlock')

		except exc.RpcWalletInsufficientFunds:

			raise cryptoNodeException('Insufficient funds in wallet')

		except exc.RpcTypeError:

			raise cryptoNodeException('Invalid amount')

		except exc.RpcWalletError:

			raise cryptoNodeException('Amount too small')

		else:

			return txid

	############################################################################

	def reset_service_buffer_timeout(self):

		if self.serviceKey:

			try:

				bufferSig = self.prox2.buffersignmessage(self.serviceKey, 'ResetBufferTimeout')

				self.prox2.resetbuffertimeout(self.serviceId, bufferSig)

			except pycurl.error:

				self.serviceKey = ''

				raise cryptoNodeException('Failed to connect - check that eccoin daemon is running')

			return True

		return False

	############################################################################

	def reset_respond_buffer_timeout(self):

		if self.respondKey:

			try:

				bufferSig = self.prox2.buffersignmessage(self.respondKey, 'ResetBufferTimeout')

				self.prox2.resetbuffertimeout(self.respondId, bufferSig)

			except pycurl.error:

				self.serviceKey = ''

				raise cryptoNodeException('Failed to connect - check that eccoin daemon is running')

			return True

		return False

	############################################################################

	def reset_buffer_timeouts(self):

		serviceResult = self.reset_service_buffer_timeout()

		respondResult = self.reset_respond_buffer_timeout()

		return serviceResult or respondResult # OR semantics because the return value is used to gate timer setup

	############################################################################

	def get_ecresolve_tags(self):

		domain = 'ecchat.io'

		# TODO - Make this daemon version dependent ref new RPC

		tags = []

		try:

			resolved = dns.resolver.resolve(domain, 'TXT')

		except:

			raise cryptoNodeException('Error while resolving ecresolve routing tags from {} TXT record'.format(domain))

		for entry in resolved:

			decoded_entry = entry.to_text()[1:-1].split('=', 1)

			if (len(decoded_entry) == 2) and (decoded_entry[0] == 'ecresolve'):

				tags.append(decoded_entry[1])

		return tags

	############################################################################

	def setup_route(self, targetRoute):

		try:

			self.proxy.findroute(targetRoute)

			isRoute = self.proxy.haveroute(targetRoute)

		except exc.RpcInvalidAddressOrKey:

			raise cryptoNodeException('Routing tag has invalid base64 encoding : {}'.format(targetRoute))

		if not isRoute:

			raise cryptoNodeException('No route available to : {}'.format(targetRoute))

	############################################################################

	def send_packet(self, dest_key, protocol_id, data):

		if self.fPacketSig:

			signature = self.proxy.tagsignmessage(data)

			self.proxy.sendpacket(dest_key, protocol_id, data, self.routingTag, signature)

		else:

			self.proxy.sendpacket(dest_key, protocol_id, data)

	############################################################################

	def get_service_buffer(self):

		if self.serviceKey:

			bufferCmd = 'GetBufferRequest:' + str(self.serviceId) + str(next(self.serviceIdx))

			bufferSig = self.proxy.buffersignmessage(self.serviceKey, bufferCmd)

			eccbuffer = self.proxy.getbuffer(self.serviceId, bufferSig)

			return eccbuffer

		else:

			return None

	############################################################################

	def get_respond_buffer(self):

		if self.respondKey:

			bufferCmd = 'GetBufferRequest:' + str(self.respondId) + str(next(self.respondIdx))

			bufferSig = self.proxy.buffersignmessage(self.respondKey, bufferCmd)

			eccbuffer = self.proxy.getbuffer(self.respondId, bufferSig)

			return eccbuffer

		else:

			return None

	############################################################################

	def get_buffer(self, protocol_id = 1):

		if protocol_id == self.serviceId:

			return self.get_service_buffer()

		if protocol_id == self.respondId:

			return self.get_respond_buffer()

		return None

	############################################################################

	def shutdown(self):

		if self.serviceKey:

			bufferSig = self.proxy.buffersignmessage(self.serviceKey, 'ReleaseBufferRequest')

			self.proxy.releasebuffer(self.serviceId, bufferSig)

			self.serviceKey = ''

		if self.respondKey:

			bufferSig = self.proxy.buffersignmessage(self.respondKey, 'ReleaseBufferRequest')

			self.proxy.releasebuffer(self.respondId, bufferSig)

			self.respondKey = ''

################################################################################
## bitcoinNode class ###########################################################
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

		try:

			info = self.proxy.getnetworkinfo()

		except ValueError:

			raise cryptoNodeException('Failed to connect - error in rpcuser or rpcpassword for {} daemon'.format(self.symbol))

		except pycurl.error:

			raise cryptoNodeException('Failed to connect - check that {} daemon is running'.format(self.symbol))

		except exc.RpcInWarmUp:

			raise cryptoNodeException('Failed to connect - {} daemon is starting but not ready - try again after 60 seconds'.format(self.symbol))

		except exc.RpcMethodNotFound:

			raise cryptoNodeException('RPC getnetworkinfo unavailable for {} daemon'.format(self.symbol))

		try:

			zmqnotifications = self.proxy.getzmqnotifications()

		except pycurl.error:

			raise cryptoNodeException('Blockchain node for {} not available or incorrectly configured'.format(self.symbol))

		except (exc.RpcMethodNotFound, ValueError):

			zmqnotifications = []

		for zmqnotification in zmqnotifications:

			if zmqnotification['type'] == 'pubhashblock':

				self.zmqAddress = zmqnotification['address']

	############################################################################

	def refresh(self):
		
		self.blocks = self.proxy.getblockcount()
		self.peers  = self.proxy.getconnectioncount()

	############################################################################

	def get_balance(self):

		try:

			result = self.proxy.getbalance()

		except exc.RpcException as error:

			raise cryptoNodeException('{} daemon returned error: {}'.format(self.symbol, str(error)))

		else:

			return result

	############################################################################

	def get_unlocked_balance(self):

		try:

			result = self.proxy.getbalance()

		except exc.RpcException as error:

			raise cryptoNodeException('{} daemon returned error: {}'.format(self.symbol, str(error)))

		else:

			return result

	############################################################################

	def get_unconfirmed_balance(self):

		try:

			result = self.proxy.getunconfirmedbalance()

		except exc.RpcException as error:

			raise cryptoNodeException('{} daemon returned error: {}'.format(self.symbol, str(error)))

		else:

			return result

	############################################################################

	def get_new_address(self):

		return self.proxy.getnewaddress()

	############################################################################

	def wallet_locked(self):

		info = self.proxy.getwalletinfo()

		if 'unlocked_until' in info:

			return info['unlocked_until'] == 0

		return False

	############################################################################

	def unlock_wallet(self, passphrase, seconds):

		try:

			self.proxy.walletpassphrase(passphrase, seconds)

		except exc.RpcWalletPassphraseIncorrect:

			return False

		else:

			return True

	############################################################################

	def send_to_address(self, address, amount, comment):

		try:

			txid = self.proxy.sendtoaddress(address, amount, comment)

		except exc.RpcWalletUnlockNeeded:

			raise cryptoNodeException('Wallet locked - please unlock')

		except exc.RpcWalletInsufficientFunds:

			raise cryptoNodeException('Insufficient funds in wallet')

		except exc.RpcTypeError:

			raise cryptoNodeException('Invalid amount')

		except exc.RpcWalletError:

			raise cryptoNodeException('Amount too small')

		else:

			return txid

	############################################################################

	def shutdown(self):

		pass

################################################################################
## moneroNode class ############################################################
################################################################################

class moneroNode(cryptoNode):

	############################################################################

	def __init__(self, symbol, rpc_address, rpc_daemon, rpc_user, rpc_pass):

		super().__init__(symbol, rpc_address, rpc_user, rpc_pass)

		(host, port) = tuple(rpc_address.split(':'))

		try:

			self.wallet = Wallet(host=host, port=port, user=rpc_user, password=rpc_pass)

		except monero.backends.jsonrpc.exceptions.Unauthorized:

			raise cryptoNodeException('Failed to connect - error in rpcuser or rpcpassword for {} wallet'.format(self.symbol))

		except requests.exceptions.ConnectTimeout:

			raise cryptoNodeException('Failed to connect - check that {} wallet is running'.format(self.symbol))

		(host, port) = tuple(rpc_daemon.split(':'))

		try:

			self.daemon = Daemon(host=host, port=port)

		except monero.backends.jsonrpc.exceptions.Unauthorized:

			raise cryptoNodeException('Failed to connect - error in rpcuser or rpcpassword for {} daemon'.format(self.symbol))

		except requests.exceptions.ConnectTimeout:

			raise cryptoNodeException('Failed to connect - check that {} daemon is running'.format(self.symbol))

	############################################################################

	def __getattr__(self, method):

		return getattr(self.proxy, method)

		pass

	############################################################################

	def initialise(self):

		pass

	############################################################################

	def refresh(self):

		try:

			self.blocks = self.wallet.height()

		except monero.backends.jsonrpc.exceptions.Unauthorized:

			raise cryptoNodeException('Failed to connect - error in rpcuser or rpcpassword for {} wallet'.format(self.symbol))

		except requests.exceptions.ConnectTimeout:

			raise cryptoNodeException('Failed to connect - check that {} wallet is running'.format(self.symbol))

		try:

			info = self.daemon.info()

		except monero.backends.jsonrpc.exceptions.Unauthorized:

			raise cryptoNodeException('Failed to connect - check that {} daemon is running'.format(self.symbol))

		except requests.exceptions.ConnectTimeout:

			raise cryptoNodeException('Failed to connect - check that {} daemon is running'.format(self.symbol))

		self.peers = info['incoming_connections_count'] + info['outgoing_connections_count']

	############################################################################

	def get_balance(self):

		return self.wallet.balance()

	############################################################################

	def get_unlocked_balance(self):

		return self.wallet.balance(unlocked=True)

	############################################################################

	def get_unconfirmed_balance(self):

		amount = 0.0

		transfers = self.wallet._backend.transfers_in(0, PaymentFilter(unconfirmed=True, confirmed=False))

		for transfer in transfers:

			amount += float(transfer.amount)

		return amount

	############################################################################

	def get_new_address(self):

		return str(self.wallet.address())

	############################################################################

	def wallet_locked(self):

		# Assume that wallet is unlocked when monero-wallet-rpc is started

		return False

	############################################################################

	def unlock_wallet(self, passphrase, seconds):

		return True

	############################################################################

	def send_to_address(self, address, amount, comment):

		return self.wallet.transfer(address, float(amount))[0].hash

	############################################################################

	def shutdown(self):

		pass

################################################################################
