#!/usr/bin/env python3
# coding: UTF-8

import threading
import datetime
import argparse
import pathlib
import logging
import hashlib
import signal
import codecs
import pickle
import zmq
import sys

from uuid import uuid4

# Configuration file management : eccoin.conf

from configure import loadConfigurationECC

# eccPacket & cryptoNode  classes

from eccpacket    import eccPacket
from cryptonode   import cryptoNode, eccoinNode, cryptoNodeException

################################################################################
## RepeatTimer class ###########################################################
################################################################################

class RepeatTimer(threading.Timer):

    def run(self):

        while not self.finished.wait(self.interval):

            self.function(*self.args, **self.kwargs)

################################################################################
## UsageTrack class ############################################################
################################################################################

class UsageTrack:

	usageFilePath = 'net'
	usageFileName = 'taghashes.dat'

	############################################################################

	def __init__(self):

		pathlib.Path(self.usageFilePath).mkdir(parents=True, exist_ok=True)

		self.filePath  = pathlib.Path(self.usageFilePath) / self.usageFileName

		self.tagHashes = self.loadListFile(self.filePath)

		self.changed   = False

	############################################################################

	def start(self):

		self.buffer_timer = RepeatTimer(10, self.saveIfNecessary)

		self.buffer_timer.start()

	############################################################################

	def stop(self):

		self.buffer_timer.cancel()

	############################################################################

	def usageByTag(self, tag):

		tagHash = hashlib.sha256(tag.encode()).hexdigest()

		if tagHash not in self.tagHashes:

			self.tagHashes.append(tagHash)

			self.changed = True

	############################################################################

	def count(self):

		return len(self.tagHashes)

	############################################################################

	def saveIfNecessary(self):

		if self.changed:

			self.saveListFile(self.tagHashes, self.filePath)

			self.changed = False

	############################################################################

	def loadListFile(self, filePath = ''):

		nullList = []

		if not pathlib.Path(filePath).is_file():

			with open(filePath, 'wb') as f:

				pickle.dump(nullList, f)

				f.close()

				return nullList

		else:

			with open(filePath, 'rb') as f:

				return pickle.load(f)

	############################################################################

	def saveListFile(self, list = [], filePath = ''):

		with open(filePath, 'wb') as f:

			pickle.dump(list, f)

			f.close()

################################################################################
## EchoApp class ###############################################################
################################################################################

class EchoApp:

	def __init__(self, protocol, name, prefix, debug=False):

		self.name			= name
		self.prefix			= prefix
		self.debug			= debug
		self.subscribers	= []
		self.coins			= []
		self.running		= True
		self.buffer_timer   = 0
		self.chatname_timer = 0

		self.usageTrack		= UsageTrack()

	############################################################################

	def send_ecchat_packet(self, dest, meth, data):

		ecc_packet = eccPacket(eccPacket._protocol_id_ecchat, 0, dest, self.coins[0].routingTag, meth, data)

		if self.debug:

			logging.info('TX({}): {}'.format(eccPacket._protocol_id_ecchat, ecc_packet.to_json()))

		ecc_packet.send(self.coins[0])

	############################################################################

	def send_ecresolve_packet(self, meth, data):

		for tag in self.coins[0].ecresolve_tags:

			ecc_packet = eccPacket(eccPacket._protocol_id_ecresolve, 0, tag, self.coins[0].routingTag, meth, data)

			if self.debug:

				logging.info('TX({}): {}'.format(eccPacket._protocol_id_ecresolve, ecc_packet.to_json()))

			ecc_packet.send(self.coins[0])

	############################################################################

	def advertise_chat_name(self, loop = None, data = None):

		uuid = str(uuid4())

		data = {'uuid' : str(uuid4()),
				'name' : self.name,
				'type' : 'chatname'}

		self.send_ecresolve_packet(eccPacket.METH_nameAdv, data)

	############################################################################

	def process_ecc_packet(self, ecc_packet):

		# Ensure we have a route back to whoever is sending an ecchat message

		try:

			self.coins[0].setup_route(ecc_packet.get_from())

		except cryptoNodeException as error:

			logging.info(str(error))

			return

		if ecc_packet.get_meth() == eccPacket.METH_chatMsg:

			data = ecc_packet.get_data()

			# send the chatAck message

			ackData = {'uuid' : data['uuid'],
					   'cmmd' : data['cmmd'],
					   'able' : True}

			self.send_ecchat_packet(ecc_packet.get_from(), eccPacket.METH_chatAck, ackData)

			reply = []

			if data['text'].startswith('#BALANCE'):

				reply.append("Balance = {:f}".format(self.coins[0].get_balance()))

			elif data['text'].startswith('#USAGE'):

				reply.append("Unique users (identified by ECC routing tag) = {:d}".format(self.usageTrack.count()))

			else:

				reply.append(self.prefix + data['text'])

			# echo back the reply text as a new chatMsg

			for line in reply:

				echData = {'uuid' : str(uuid4()),
						   'cmmd' : 'add',
						   'text' : line}

				self.send_ecchat_packet(ecc_packet.get_from(), eccPacket.METH_chatMsg, echData)

			self.usageTrack.usageByTag(ecc_packet.get_from())

		elif ecc_packet.get_meth() == eccPacket.METH_addrReq:

			data = ecc_packet.get_data()

			if data['coin'] == self.coins[0].symbol:

				address = self.coins[0].get_new_address()

				rData = {'uuid' : data['uuid'],
						 'coin' : data['coin'],
						 'addr' : address}

				self.send_ecchat_packet(ecc_packet.get_from(), eccPacket.METH_addrRes, rData)

			else:

				rData = {'uuid' : data['uuid'],
						 'coin' : data['coin'],
						 'addr' : '0'}

				self.send_ecchat_packet(ecc_packet.get_from(), eccPacket.METH_addrRes, rData)

		else:

			pass

	############################################################################

	def zmqInitialise(self):

		self.context = zmq.Context()

		for index, coin in enumerate(self.coins):

			self.subscribers.append(self.context.socket(zmq.SUB))

			if coin.zmqAddress:

				self.subscribers[index].connect(coin.zmqAddress)
				self.subscribers[index].setsockopt(zmq.SUBSCRIBE, b'')

	############################################################################

	def zmqHandler(self, index):

		[address, contents] = self.subscribers[index].recv_multipart()
		
		if address.decode() == 'packet':

			protocolID = contents.decode()[1:]

			eccbuffer = self.coins[0].get_buffer(int(protocolID))

			if eccbuffer:

				for packet in eccbuffer.values():

					message = codecs.decode(packet, 'hex').decode()

					if self.debug:

						logging.info('RX({}): {}'.format(protocolID, message))

					ecc_packet = eccPacket.from_json(message)

					self.process_ecc_packet(ecc_packet)

	############################################################################

	def zmqShutdown(self):

		for subscriber in self.subscribers:

			subscriber.close()

		self.context.term()

	############################################################################

	def reset_buffer_timeouts(self):

		self.coins[0].reset_buffer_timeouts()

	############################################################################

	def logRoutingTags(self):

		logging.info('Resolved local routing tag : {}'.format(self.coins[0].routingTag))

		for index, tag in enumerate(self.coins[0].ecresolve_tags):

			if tag == self.coins[0].routingTag:

				logging.info('Resolved ecresolve tag #{}  * {}'.format(index, tag))

			else:

				logging.info('Resolved ecresolve tag #{}  : {}'.format(index, tag))

	############################################################################

	def cryptoInitialise(self):

		if loadConfigurationECC(self.coins, eccPacket._protocol_id_ecchat):

			for coin in self.coins:

				try:

					coin.initialise()

					self.logRoutingTags()

				except cryptoNodeException as error:

					print(str(error))

					return False

				self.buffer_timer   = RepeatTimer(10, self.reset_buffer_timeouts)

				self.buffer_timer.start()

				self.chatname_timer = RepeatTimer(60, self.advertise_chat_name)

				self.chatname_timer.start()

			return True

		return False

	############################################################################

	def cryptoShutdown(self):

		if self.buffer_timer:

			self.buffer_timer.cancel()

		if self.chatname_timer:

			self.chatname_timer.cancel()

		for coin in self.coins:

			coin.shutdown()

	############################################################################

	def run(self):

		self.usageTrack.start()

		if self.cryptoInitialise():

			self.zmqInitialise()

			while self.running:

				try:

					self.zmqHandler(0)

				except ServiceExit:

					self.running = False

			self.zmqShutdown()

		self.cryptoShutdown()

		self.usageTrack.stop()

################################################################################

class ServiceExit(Exception):

	pass

################################################################################

def terminate(signalNumber, frame):

	logging.info('%s received - terminating' % signal.Signals(signalNumber).name)

	raise ServiceExit

################################################################################
### Main program ###############################################################
################################################################################

def main():

	if sys.version_info[0] < 3:

		raise 'Use Python 3'

	pathlib.Path('log').mkdir(parents=True, exist_ok=True)

	logging.basicConfig(filename = 'log/ececho-{:%Y-%m-%d}.log'.format(datetime.datetime.now()),
						filemode = 'a',
						level    = logging.INFO,
						format   = '%(asctime)s - %(levelname)s : %(message)s',
						datefmt  = '%d/%m/%Y %H:%M:%S')

	logging.info('STARTUP')

	signal.signal(signal.SIGINT,  terminate)  # keyboard interrupt ^C
	signal.signal(signal.SIGTERM, terminate)  # kill [default -15]

	argparser = argparse.ArgumentParser(description='Echo service for ecchat')

	argparser.add_argument('-p', '--protocol', action='store'     , help='Protocol ID'      , type=int, default=1       , required=False)
	argparser.add_argument('-n', '--name'    , action='store'     , help='nickname'         , type=str, default='ececho', required=False)
	argparser.add_argument('-x', '--prefix'  , action='store'     , help='reply prefix'     , type=str, default='> '    , required=False)
	argparser.add_argument('-d', '--debug'   , action='store_true', help='debug message log',                             required=False)

	command_line_args = argparser.parse_args()

	logging.info('Arguments %s', vars(command_line_args))

	app = EchoApp(command_line_args.protocol,
	              command_line_args.name,
	              command_line_args.prefix,
	              command_line_args.debug)

	app.run()

	logging.info('SHUTDOWN')

################################################################################

if __name__ == '__main__':

	main()

################################################################################
