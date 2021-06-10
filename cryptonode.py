#!/usr/bin/env python3
# coding: UTF-8

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
	version_max = 30300

	version_fPacketSig = 30300

	bufferIdx = count(start=1)

	############################################################################

	def __init__(self, symbol, rpc_address, rpc_user, rpc_pass, protocol_id):

		super().__init__(symbol, rpc_address, rpc_user, rpc_pass)

		self.proxy = Proxy('http://%s:%s@%s' % (rpc_user, rpc_pass, rpc_address))

		self.protocolId = protocol_id
		self.routingTag = ''
		self.bufferKey  = ''

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

		self.fPacketSig = info['version'] >= self.version_fPacketSig

		# ECC messaging buffer setup

		try:

			self.routingTag = self.proxy.getroutingpubkey()
			self.bufferKey  = self.proxy.registerbuffer(self.protocolId)

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

	def reset_buffer_timeout(self):

		if self.bufferKey:

			bufferSig = self.proxy.buffersignmessage(self.bufferKey, 'ResetBufferTimeout')

			self.proxy.resetbuffertimeout(self.protocolId, bufferSig)

			return True

		return False

	############################################################################

	def resolve_route(self, targetRoute):

		if targetRoute == 'ececho':

			if self.fPacketSig:

				return 'BAU3rdcs0BnDtOhXX/PjoR/99Toft8tyYWYxdTFlfiTAPQb43akF/waOo23REBVVRrSdsMX8iPHKDYgqhEGetSY=' # eccserver2.ddns.net

			else

				return 'BImGKLu0cwgmRigdvoWTnJdQ0Q+QgscUzJgsdChUOTi2dkM6wF/KXf84w9VjIydfIwl3EDgNPvjLP3HgNyifZ9w=' # eccserver1.ddns.net

		return targetRoute

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

	def send_packet(self, dest_key, protocol_id, data)

		self.proxy.sendpacket(dest_key, protocol_id, data)

	############################################################################

	def get_buffer(self, protocol_id = 1):

		assert protocol_id == self.protocolId

		if self.bufferKey:

			bufferCmd = 'GetBufferRequest:' + str(protocol_id) + str(next(self.bufferIdx))

			bufferSig = self.proxy.buffersignmessage(self.bufferKey, bufferCmd)

			eccbuffer = self.proxy.getbuffer(protocol_id, bufferSig)

			return eccbuffer

		else:

			return None

	############################################################################

	def shutdown(self):

		if self.bufferKey:

			bufferSig = self.proxy.buffersignmessage(self.bufferKey, 'ReleaseBufferRequest')

			self.proxy.releasebuffer(self.protocolId, bufferSig)

			self.bufferKey = ''

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
