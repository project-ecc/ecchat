import settings
import argparse
import pathlib
import logging
import socket
import signal
import zmq
import sys

from datetime import datetime

################################################################################

class eccMessage:

	def __init__(self):

		pass

	############################################################################

	def method(self):

		pass

################################################################################

def terminate(signalNumber, frame):

	logging.info('%s received - terminating' % signal.Signals(signalNumber).name)

	sys.exit()

################################################################################
### Main program ###############################################################
################################################################################

def main():

	pathlib.Path('log').mkdir(parents=True, exist_ok=True)

	logging.basicConfig(filename = 'log/{:%Y-%m-%d}.log'.format(datetime.now()),
						filemode = 'a',
						level    = logging.INFO,
						format   = '%(asctime)s - %(levelname)s : %(message)s',
						datefmt  = '%d/%m/%Y %H:%M:%S')

	logging.info('STARTUP')

	signal.signal(signal.SIGINT,  terminate)  # keyboard interrupt ^C
	signal.signal(signal.SIGTERM, terminate)  # kill [default -15]

	argparser = argparse.ArgumentParser(description='Simple command line chat for ECC')

	#argparser.add_argument('-a', '--addr', action='store', help='address to accept connections', type=str, default = '127.0.0.1')
	#argparser.add_argument('-p', '--port', action='store', help='port for client connections'  , type=int, default = 5222)

	command_line_args = argparser.parse_args()

	logging.info('Arguments %s', vars(command_line_args))

	#====================================================
	context    = zmq.Context()
	subscriber = context.socket(zmq.SUB)
	subscriber.connect('tcp://%s'%settings.zmq_address)
	subscriber.setsockopt(zmq.SUBSCRIBE, b'')

#    while True:

#        [address, contents] = subscriber.recv_multipart()

#        if address.decode() == 'packet':

#            protocolID = contents.decode()[1:]

#            logging.info('Notification for Protocol ID %s' % protocolID)

#            eccbuffer = eccoin.getbuffer(int(protocolID))

#            for packet in eccbuffer.values():

#                message = codecs.decode(packet, 'hex').decode()

#                logging.info('Received message - %s' % message)

#               handle(protocolID, message)

	subscriber.close()
	context.term()
	#====================================================

	logging.info('SHUTDOWN')

################################################################################

if __name__ == "__main__":

	main()

################################################################################
