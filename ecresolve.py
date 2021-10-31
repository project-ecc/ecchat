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

	############################################################################

	def __init__(self, name):

		self.usageFilePath = 'net'
		self.usageFileName = name + '-usage.dat'

		pathlib.Path(self.usageFilePath).mkdir(parents=True, exist_ok=True)

		self.filePath  = pathlib.Path(self.usageFilePath) / self.usageFileName

		self.tagHashes = self.loadListFile(self.filePath)

		self.changed   = False

	############################################################################

	def start(self):

		self.timer = RepeatTimer(60, self.saveIfNecessary)

		self.timer.start()

	############################################################################

	def stop(self):

		self.timer.cancel()

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
## ServiceApp class ############################################################
################################################################################

class ServiceApp:

	def __init__(self, protocol, name, debug=False):

		self.protocol_id	= protocol
		self.protocol_ver	= 1
		self.name			= name
		self.debug			= debug
		self.subscribers	= []
		self.coins			= []
		self.running		= True
		self.timer          = 0

		self.usageTrack		= UsageTrack(name)

	############################################################################

	def send_ecc_packet(self, dest, meth, data):

		ecc_packet = eccPacket(self.protocol_id, self.protocol_ver, dest, self.coins[0].routingTag, meth, data)

		if self.debug:

			logging.info('TX: {}'.format(ecc_packet.to_json()))

		ecc_packet.send(self.coins[0])

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

			self.send_ecc_packet(ecc_packet.get_from(), eccPacket.METH_chatAck, ackData)

			reply = []

			if data['text'].startswith('#BALANCE'):

				reply.append("Balance = {:f}".format(self.coins[0].get_balance()))

			elif data['text'].startswith('#USAGE'):

				reply.append("Unique users (identified by ECC routing tag) = {:d}".format(self.usageTrack.count()))

			elif data['text'].startswith('#STOP!!!'):

				reply.append("ececho stopping ...")

				self.running = False

			else:

				reply.append(self.prefix + data['text'])

			# echo back the reply text as a new chatMsg

			for line in reply:

				echData = {'uuid' : str(uuid4()),
						   'cmmd' : 'add',
						   'text' : line}

				self.send_ecc_packet(ecc_packet.get_from(), eccPacket.METH_chatMsg, echData)

			self.usageTrack.usageByTag(ecc_packet.get_from())

		elif ecc_packet.get_meth() == eccPacket.METH_addrReq:

			data = ecc_packet.get_data()

			if data['coin'] == self.coins[0].symbol:

				address = self.coins[0].get_new_address()

				rData = {'uuid' : data['uuid'],
						 'coin' : data['coin'],
						 'addr' : address}

				self.send_ecc_packet(ecc_packet.get_from(), eccPacket.METH_addrRes, rData)

			else:

				rData = {'uuid' : data['uuid'],
						 'coin' : data['coin'],
						 'addr' : '0'}

				self.send_ecc_packet(ecc_packet.get_from(), eccPacket.METH_addrRes, rData)

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

						logging.info('RX: {}'.format(message))

					ecc_packet = eccPacket.from_json(message)

					self.process_ecc_packet(ecc_packet)

	############################################################################

	def zmqShutdown(self):

		for subscriber in self.subscribers:

			subscriber.close()

		self.context.term()

	############################################################################

	def reset_buffer_timeout(self):

		self.coins[0].reset_buffer_timeout()

	############################################################################

	def cryptoInitialise(self):

		if loadConfigurationECC(self.coins, self.protocol_id):

			for coin in self.coins:

				try:

					coin.initialise()

				except cryptoNodeException as error:

					print(str(error))

					return False

				self.timer = RepeatTimer(10, self.reset_buffer_timeout)

				self.timer.start()

			return True

		return False

	############################################################################

	def cryptoShutdown(self):

		if self.timer:

			self.timer.cancel()

		for coin in self.coins:

			coin.shutdown()

	############################################################################

	def run(self):

		self.usageTrack.start()

		if self.cryptoInitialise():

			self.zmqInitialise()

			while self.running:

				self.zmqHandler(0)

			self.zmqShutdown()

		self.cryptoShutdown()

		self.usageTrack.stop()

################################################################################

def terminate(signalNumber, frame):

	logging.info('%s received - terminating' % signal.Signals(signalNumber).name)

	sys.exit()

################################################################################
### Main program ###############################################################
################################################################################

def main():

	if sys.version_info[0] < 3:

		raise 'Use Python 3'

	signal.signal(signal.SIGINT,  terminate)  # keyboard interrupt ^C
	signal.signal(signal.SIGTERM, terminate)  # kill [default -15]

	argparser = argparse.ArgumentParser(description='Echo service for ecchat')

	argparser.add_argument('-p', '--protocol', action='store'     , help='Protocol ID'      , type=int, default=2          , required=False)
	argparser.add_argument('-n', '--name'    , action='store'     , help='service name'     , type=str, default='ecresolve', required=False)
	argparser.add_argument('-d', '--debug'   , action='store_true', help='debug message log',                                required=False)

	command_line_args = argparser.parse_args()

	pathlib.Path('log').mkdir(parents=True, exist_ok=True)

	logging.basicConfig(filename = 'log/{}-{:%Y-%m-%d}.log'.format(command_line_args.name, datetime.datetime.now()),
						filemode = 'a',
						level    = logging.INFO,
						format   = '%(asctime)s - %(levelname)s : %(message)s',
						datefmt  = '%d/%m/%Y %H:%M:%S')

	logging.info('STARTUP')

	logging.info('Arguments %s', vars(command_line_args))

	app = ServiceApp(command_line_args.protocol,
	                 command_line_args.name,
	                 command_line_args.debug)

	app.run()

	logging.info('SHUTDOWN')

################################################################################

if __name__ == '__main__':

	main()

################################################################################
