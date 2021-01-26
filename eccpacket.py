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

	METH_SET = [METH_chatMsg,
				METH_chatAck,
				METH_addrReq,
				METH_addrRes,
				METH_txidInf]

	KEY_LIST = {METH_chatMsg : ('uuid', 'cmmd', 'text'),
				METH_chatAck : ('uuid', 'cmmd'),
				METH_addrReq : ('coin', 'type'),
				METH_addrRes : ('coin', 'addr'),
				METH_txidInf : ('coin', 'amnt', 'addr', 'txid')}

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

		proxy.sendpacket(self.packet['to'], self.packet['id'], json.dumps(self.packet))

################################################################################
