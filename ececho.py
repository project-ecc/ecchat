#!/usr/bin/env python3
# coding: UTF-8

import threading
import datetime
import argparse
import pathlib
import logging
import signal
import codecs
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
## EchoApp class ###############################################################
################################################################################

class EchoApp:

	def __init__(self, protocol, name, prefix, debug=False):


		self.protocol_id	= protocol
		self.protocol_ver	= 1
		self.name			= name
		self.prefix			= prefix
		self.debug			= debug
		self.subscribers	= []
		self.coins			= []
		self.running		= True
		self.timer          = 0

	############################################################################

	def send_ecc_packet(self, dest, meth, data):

		ecc_packet = eccPacket(self.protocol_id, self.protocol_ver, dest, self.coins[0].routingTag, meth, data)

		if self.debug:

			logging.info('TX: {}'.format(ecc_packet.to_json()))

		ecc_packet.send(self.coins[0])

	############################################################################

	def process_ecc_packet(self, ecc_packet):

		# Ensure we have a route back to whoever is sending an ecchat message

		self.coins[0].setup_route(ecc_packet.get_from())

		if ecc_packet.get_meth() == eccPacket.METH_chatMsg:

			data = ecc_packet.get_data()

			# send the chatAck message

			ackData = {'uuid' : data['uuid'],
					   'cmmd' : data['cmmd'],
					   'able' : True}

			self.send_ecc_packet(ecc_packet.get_from(), eccPacket.METH_chatAck, ackData)

			if data['text'].startswith('#BALANCE'):

				reply = "Balance = {:f}".format(self.coins[0].get_balance())

			elif data['text'].startswith('#STOP!!!'):

				reply = "ececho stopping ..."

				self.running = False

			else:

				reply = self.prefix + data['text']

			# echo back the reply text as a new chatMsg

			echData = {'uuid' : str(uuid4()),
					   'cmmd' : 'add',
					   'text' : reply}

			self.send_ecc_packet(ecc_packet.get_from(), eccPacket.METH_chatMsg, echData)

		elif ecc_packet.get_meth() == eccPacket.METH_addrReq:

			data = ecc_packet.get_data()

			if data['coin'] == self.coins[0].symbol:

				address = self.coins[0].get_new_address()

				rData = {'uuid' : data['uuid'],
						 'coin' : data['coin'],
						 'addr' : address}

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

		if self.cryptoInitialise():

			self.zmqInitialise()

			while self.running:

				self.zmqHandler(0)

			self.zmqShutdown()

		self.cryptoShutdown()

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
	argparser.add_argument('-x', '--prefix'  , action='store'     , help='reply prefix'     , type=str, default='>>> '  , required=False)
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
