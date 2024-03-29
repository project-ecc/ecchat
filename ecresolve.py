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
## NamesCache class ############################################################
################################################################################

class NamesCache:

	############################################################################

	def __init__(self, timeout):

		self.timeout = timeout

		self.cache = {}

	############################################################################

	def start(self):

		self.timer = RepeatTimer(10, self.timeoutNames)

		self.timer.start()

	############################################################################

	def stop(self):

		self.timer.cancel()

	############################################################################

	def timeoutNames(self):

		now = datetime.datetime.now()

		for key in [k for k, v in self.cache.items() if v['until'] < now]:

			logging.info('NamesCache : Name timedout : {}/{}'.format(key, self.cache[key]['type']))

			del self.cache[key]

	############################################################################

	def add(self, name, name_type, name_tag):

		until = datetime.datetime.now() + datetime.timedelta(seconds=self.timeout)

		if name in self.cache:

			if self.cache[name]['tag'] == name_tag:

				self.cache[name]['until'] = until

				logging.info('NamesCache : Name extended : {}/{}'.format(name, name_type))

				return True

			else:

				logging.info('NamesCache : Name rejected : {} : {}'.format(name, 'Registration of existing name by another node rejected'))

				return False

		else:

			self.cache[name] = {'type' : name_type, 'tag' : name_tag, 'until' : until}

			logging.info('NamesCache : Name register : {}/{}'.format(name, name_type))

			return True

	############################################################################

	def resolve(self, name, name_type):

		if name in self.cache:

			if self.cache[name]['type'] == name_type:

				logging.info('NamesCache : Name resolved : {}/{}'.format(name, name_type))

				return [self.cache[name]['tag']]

		logging.info('NamesCache : Name unknown  : {}/{}'.format(name, name_type))

		return []

################################################################################
## ServiceApp class ############################################################
################################################################################

class ServiceApp:

	def __init__(self, name, debug=False):

		self.name			= name
		self.debug			= debug
		self.subscribers	= []
		self.coins			= []
		self.running		= True
		self.timer          = 0

		self.usageTrack		= UsageTrack(name)
		self.namesCache     = NamesCache(90)

	############################################################################

	def send_response_packet(self, dest, rid, meth, data):

		ecc_packet = eccPacket(eccPacket._protocol_id_ecresolve, rid, dest, self.coins[0].routingTag, meth, data)

		if self.debug:

			logging.info('TX({}): {}'.format(rid, ecc_packet.to_json()))

		ecc_packet.send_response(self.coins[0])

	############################################################################

	def process_ecc_packet(self, ecc_packet):

		# Ensure we have a route back to whoever sent the ecresolve message for messages needing a response

		if ecc_packet.get_meth() in (eccPacket.METH_nameReq):

			try:

				self.coins[0].setup_route(ecc_packet.get_from())

			except cryptoNodeException as error:

				logging.info(str(error))

				return

		if ecc_packet.get_meth() == eccPacket.METH_nameAdv:

			data = ecc_packet.get_data()

			self.usageTrack.usageByTag(ecc_packet.get_from())

			self.namesCache.add(data['name'], data['type'], ecc_packet.get_from())

		elif ecc_packet.get_meth() == eccPacket.METH_nameReq:

			data = ecc_packet.get_data()

			tags = self.namesCache.resolve(data['name'], data['type'])

			rData = {'uuid' : data['uuid'],
					 'name' : data['name'],
					 'type' : data['type'],
					 'tags' : tags}

			self.send_response_packet(ecc_packet.get_from(), ecc_packet.get_rid(), eccPacket.METH_nameRes, rData)

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

		if loadConfigurationECC(self.coins, eccPacket._protocol_id_ecresolve):

			for coin in self.coins:

				try:

					coin.initialise()

					self.logRoutingTags()

				except cryptoNodeException as error:

					print(str(error))

					return False

				self.timer = RepeatTimer(10, self.reset_buffer_timeouts)

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
		self.namesCache.start()

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
		self.namesCache.stop()

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

	signal.signal(signal.SIGINT,  terminate)  # keyboard interrupt ^C
	signal.signal(signal.SIGTERM, terminate)  # kill [default -15]

	argparser = argparse.ArgumentParser(description='Echo service for ecchat')

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

	app = ServiceApp(command_line_args.name,
	                 command_line_args.debug)

	app.run()

	logging.info('SHUTDOWN')

################################################################################

if __name__ == '__main__':

	main()

################################################################################
