#!/usr/bin/env python3
# coding: UTF-8

import configparser
import pathlib
import sys

import settings

from cryptonode import cryptoNode, eccoinNode, bitcoinNode, litecoinNode, moneroNode, cryptoNodeException

################################################################################

def getEccoinDataDir():

	if sys.platform == "win32":

		return pathlib.Path.home() / 'AppData/Roaming/eccoin'

	if sys.platform == "darwin":

		return pathlib.Path.home() / 'Library/Application Support/eccoin'

	if sys.platform.startswith('linux'): 

		return pathlib.Path.home() / '.eccoin'

################################################################################

def loadConfigurationECC(coins):

	rpcCheckKeys = {'rpcconnect', 'rpcport', 'rpcuser', 'rpcpassword'}

	eccConfigFile = getEccoinDataDir() / 'eccoin.conf'

	parser = configparser.ConfigParser()

	try:

		with open(eccConfigFile) as stream:

			parser.read_string("[default]\n" + stream.read()) # ConfigParser expects Windows style .INI format

	except FileNotFoundError:

		print('{} file is missing'.format(eccConfigFile))

		return False

	if all (key in parser['default'] for key in rpcCheckKeys):

		rpc_address = '{}:{}'.format(parser['default']['rpcconnect'], parser['default']['rpcport'])

		coins.append(eccoinNode('ecc', rpc_address, parser['default']['rpcuser'], parser['default']['rpcpassword'], settings.protocol_id))

		return True

	else:

		print('eccoin.conf missing one or more of rpcconnect, rpcport, rpcuser, rpcpassword')

		return False

################################################################################

def loadConfigurationAlt(coins, conf):

	rpcCheckKeys = {'rpcconnect', 'rpcport', 'rpcuser', 'rpcpassword'}

	parser = configparser.ConfigParser()

	try:

		with open(conf) as stream:

			parser.read_string(stream.read())

	except FileNotFoundError:

		createTemplateAltConf(conf)

		return True

	for symbol in parser.sections():

		if all (key in parser[symbol] for key in rpcCheckKeys):

			rpc_address = '{}:{}'.format(parser[symbol]['rpcconnect'], parser[symbol]['rpcport'])

			if symbol == 'ltc':

				coins.append(litecoinNode(symbol, rpc_address, parser[symbol]['rpcuser'], parser[symbol]['rpcpassword']))

			elif symbol == 'xmr':

				rpc_daemon  = '{}:{}'.format(parser[symbol]['daemonconnect'], parser[symbol]['daemonport'])

				try:

					coins.append(moneroNode(symbol, rpc_address, rpc_daemon, parser[symbol]['rpcuser'], parser[symbol]['rpcpassword']))

				except cryptoNodeException as error:

					print(str(error))

					return False

			else:

				coins.append(bitcoinNode(symbol, rpc_address, parser[symbol]['rpcuser'], parser[symbol]['rpcpassword']))

	return True

################################################################################

def createTemplateAltConf(conf):

	output = [	'# Example ecchat.conf for adding extra altcoin full node wallets\n', 
				'# \n',
				'# Note - Do not add your ecc config here. It is read directly from eccoin.conf\n',
				'# \n',
				'# [ltc]\n',
				'# rpcuser=username\n',
				'# rpcpassword=password\n',
				'# rpcport=9332\n',
				'# rpcconnect=127.0.0.1\n',
				'# \n',
				'# [xmr]\n',
				'# rpcuser=username\n',
				'# rpcpassword=password\n',
				'# rpcport=18082\n',
				'# rpcconnect=127.0.0.1\n',
				'# daemonport=18081\n',
				'# daemonconnect=127.0.0.1\n',
				'# \n',
				'# [doge]\n',
				'# rpcuser=username\n',
				'# rpcpassword=password\n',
				'# rpcport=22555\n',
				'# rpcconnect=127.0.0.1\n',
				'# \n',
				]

	try:

		with open(conf, "a") as stream:

			stream.writelines(output)

	except:

		pass

################################################################################