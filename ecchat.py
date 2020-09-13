import datetime
import settings
import argparse
import pathlib
import logging
import socket
import signal
import codecs
import json
import zmq
import sys

from slickrpc import Proxy
from slickrpc import exc

eccoin = Proxy('http://%s:%s@%s'%(settings.rpc_user, settings.rpc_pass, settings.rpc_address))

################################################################################

def checkRoute(routingTag):

	try:

		eccoin.findroute(routingTag)

		isRoute = eccoin.haveroute(routingTag)

	except exc.RpcInvalidAddressOrKey:

		print('Routing tag has invalid base64 encoding : %s' % routingTag)

		return False

	if not isRoute:

		print('No route available to : %s' % routingTag)

	return isRoute

################################################################################

class eccPacket():

	TYPE_chatMsg = 'chatMsg'
	TYPE_addrReq = 'addrReq'
	TYPE_addrRes = 'addrRes'

	def __init__(self, _id = '', _ver = '', _to = '', _from = '', _type = '', _data = ''):

		# TOTO: Add some validation checks here

		self.packet = {	'_id'	: _id,
						'_ver'	: _ver,
						'_to'	: _to,
						'_from'	: _from,
						'_type'	: _type,
						'_data'	: _data}

	############################################################################

	@classmethod

	def from_json(cls, json_string = ''):

		d = json.loads(json_string)

		# TOTO: Add some validation checks here

		return cls(d['_id'], d['_ver'], d['_to'], d['_from'], d['_type'], d['_data'])

	############################################################################

	def get_from(self):

		return self.packet['_from']

	############################################################################

	def get_type(self):

		return self.packet['_type']

	############################################################################

	def get_data(self):

		return self.packet['_data']

	############################################################################

	def send(self):

		eccoin.sendpacket(self.packet['_to'], self.packet['_id'], json.dumps(self.packet))

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

	logging.basicConfig(filename = 'log/{:%Y-%m-%d}.log'.format(datetime.datetime.now()),
						filemode = 'a',
						level    = logging.INFO,
						format   = '%(asctime)s - %(levelname)s : %(message)s',
						datefmt  = '%d/%m/%Y %H:%M:%S')

	logging.info('STARTUP')

	signal.signal(signal.SIGINT,  terminate)  # keyboard interrupt ^C
	signal.signal(signal.SIGTERM, terminate)  # kill [default -15]

	argparser = argparse.ArgumentParser(description='Simple command line chat for ECC')

	argparser.add_argument('-n', '--name', action='store', help='nickname    (local)' , type=str, default = '')
	argparser.add_argument('-t', '--tag' , action='store', help='routing tag (remote)', type=str, default = '')

	command_line_args = argparser.parse_args()

	logging.info('Arguments %s', vars(command_line_args))

	# Initialise eccoind

	routingTag = eccoin.getroutingpubkey()
	bufferKey  = eccoin.registerbuffer(settings.protocol_id)
	bufferIdx  = 0

	# Initialise zmq

	context    = zmq.Context()
	subscriber = context.socket(zmq.SUB)

	subscriber.connect('tcp://%s'%settings.zmq_address)
	subscriber.setsockopt(zmq.SUBSCRIBE, b'')

	poller = zmq.Poller()

	poller.register(sys.stdin,  zmq.POLLIN)
	poller.register(subscriber, zmq.POLLIN)

	# Setup route to remote tag

	if checkRoute(command_line_args.tag):

		print('')
		print('*******************************************')
		print('*** Welcome to ECC Messaging via ecchat ***')
		print('*** The route to your other party is ok ***')
		print('*** Enjoy your p2p e2ee private chat :) ***')
		print('*******************************************')
		print('')

		bExit = False

		while not bExit:

			socks = dict(poller.poll())

			if sys.stdin.fileno() in socks:

				line = sys.stdin.readline().strip('\n')

				if line == "exit":

					bExit = True

					continue

				data = command_line_args.name + '> ' + line

				ecc_packet = eccPacket(settings.protocol_id, settings.protocol_ver, command_line_args.tag, routingTag, eccPacket.TYPE_chatMsg, data)

				ecc_packet.send()

			if subscriber in socks:

				[address, contents] = subscriber.recv_multipart(zmq.DONTWAIT)

				if address.decode() == 'packet':

					protocolID = contents.decode()[1:]

					bufferCmd = 'GetBufferRequest:' + protocolID + str(bufferIdx := bufferIdx + 1)

					bufferSig = eccoin.buffersignmessage(bufferKey, bufferCmd)

					eccbuffer = eccoin.getbuffer(int(protocolID), bufferSig)

					for packet in eccbuffer.values():

						message = codecs.decode(packet, 'hex').decode()

						ecc_packet = eccPacket.from_json(message)

						if   ecc_packet.get_type() == eccPacket.TYPE_chatMsg:

							print(ecc_packet.get_data())

						elif ecc_packet.get_type() == eccPacket.TYPE_addrReq:

							pass

						elif ecc_packet.get_type() == eccPacket.TYPE_addrReq:

							pass

						else:

							pass

	bufferCmd = 'ReleaseBufferRequest'

	bufferSig = eccoin.buffersignmessage(bufferKey, bufferCmd)

	eccoin.releasebuffer(settings.protocol_id, bufferSig)

	subscriber.close()
	context.term()

	logging.info('SHUTDOWN')

################################################################################

if __name__ == '__main__':

	main()

################################################################################
