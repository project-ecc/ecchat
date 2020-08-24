import settings
import argparse
import pathlib
import logging
import socket
import signal
import sys

from datetime import datetime

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

	# TODO : Chat program

	logging.info('SHUTDOWN')

################################################################################

if __name__ == "__main__":

	main()

################################################################################
