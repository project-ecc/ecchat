#!/usr/bin/env python3
# coding: UTF-8

import json

################################################################################
## eccPacket class #############################################################
################################################################################

class eccPacket():

	METH_chatMsg = 'chatMsg'
	METH_chatAck = 'chatAck'
	METH_addrReq = 'addrReq'
	METH_addrRes = 'addrRes'
	METH_txidInf = 'txidInf'
	METH_swapInf = 'swapInf'
	METH_swapReq = 'swapReq'
	METH_swapRes = 'swapRes'
	METH_nameAdv = 'nameAdv'

	METH_SET = [METH_chatMsg,
				METH_chatAck,
				METH_addrReq,
				METH_addrRes,
				METH_txidInf,
				METH_swapInf,
				METH_swapReq,
				METH_swapRes,
				METH_nameAdv]

	KEY_LIST = {METH_chatMsg : ('uuid', 'cmmd', 'text'),
				METH_chatAck : ('uuid', 'cmmd', 'able'),
				METH_addrReq : ('uuid', 'coin', 'type'),
				METH_addrRes : ('uuid', 'coin', 'addr'),
				METH_txidInf : ('uuid', 'coin', 'amnt', 'addr', 'txid'),
				METH_swapInf : ('uuid', 'cogv', 'amgv', 'cotk', 'amtk'),
				METH_swapReq : ('uuid', 'cogv', 'adgv'),
				METH_swapRes : ('uuid', 'cotk', 'adtk'),
				METH_nameAdv : ('uuid', 'name', 'type')}

	############################################################################

	def __init__(self, _id = '', _ver = '', _to = '', _from = '', _meth = '', _data = ''):

		assert isinstance(_data, dict)

		assert _meth in self.METH_SET

		assert all(key in _data for key in self.KEY_LIST[_meth])

		self.packet = {	'id'	: _id,
						'ver'	: _ver,
						'to'	: _to,
						'from'	: _from,
						'meth'	: _meth,
						'data'	: _data}

	############################################################################

	@classmethod

	def from_json(cls, json_string = ''):

		d = json.loads(json_string)

		return cls(d['id'], d['ver'], d['to'], d['from'], d['meth'], d['data'])

	############################################################################

	def to_json(self):

		return json.dumps(self.packet)

	############################################################################

	def get_id(self):

		return self.packet['id']

	############################################################################

	def get_ver(self):

		return self.packet['ver']

	############################################################################

	def get_to(self):

		return self.packet['to']

	############################################################################

	def get_from(self):

		return self.packet['from']

	############################################################################

	def get_meth(self):

		return self.packet['meth']

	############################################################################

	def get_data(self):

		data = self.packet['data']

		assert isinstance(data, dict)

		assert self.packet['meth'] in self.METH_SET

		assert all(key in data for key in self.KEY_LIST[self.packet['meth']])

		return data

	############################################################################

	def send(self, proxy):

		proxy.send_packet(self.packet['to'], self.packet['id'], json.dumps(self.packet))

################################################################################
