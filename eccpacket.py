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
	METH_nameReq = 'nameReq'
	METH_nameRes = 'nameRes'

	METH_SET = [METH_chatMsg,
				METH_chatAck,
				METH_addrReq,
				METH_addrRes,
				METH_txidInf,
				METH_swapInf,
				METH_swapReq,
				METH_swapRes,
				METH_nameAdv,
				METH_nameReq,
				METH_nameRes]

	KEY_LIST = {METH_chatMsg : ('uuid', 'cmmd', 'text'),
				METH_chatAck : ('uuid', 'cmmd', 'able'),
				METH_addrReq : ('uuid', 'coin', 'type'),
				METH_addrRes : ('uuid', 'coin', 'addr'),
				METH_txidInf : ('uuid', 'coin', 'amnt', 'addr', 'txid'),
				METH_swapInf : ('uuid', 'cogv', 'amgv', 'cotk', 'amtk'),
				METH_swapReq : ('uuid', 'cogv', 'adgv'),
				METH_swapRes : ('uuid', 'cotk', 'adtk'),
				METH_nameAdv : ('uuid', 'name', 'type'),
				METH_nameReq : ('uuid', 'name', 'type'),
				METH_nameRes : ('uuid', 'name', 'type', 'tags')}

	############################################################################

	def __init__(self, _ver = '', _sid = 0, _rid = 0, _to = '', _from = '', _meth = '', _data = ''):

		assert isinstance(_data, dict)

		assert _meth in self.METH_SET

		assert all(key in _data for key in self.KEY_LIST[_meth])

		if _rid == 0:

			self.packet = {	'ver'	: _ver,
							'sid'	: _sid,
							'to'	: _to,
							'from'	: _from,
							'meth'	: _meth,
							'data'	: _data}

		else:

			self.packet = {	'ver'	: _ver,
							'sid'	: _sid,
							'rid'	: _rid,
							'to'	: _to,
							'from'	: _from,
							'meth'	: _meth,
							'data'	: _data}

	############################################################################

	@classmethod

	def from_json(cls, json_string = ''):

		d = json.loads(json_string)

		if 'rid' in d:

			return cls(d['ver'], d['sid'], d['rid'], d['to'], d['from'], d['meth'], d['data'])

		else:

			return cls(d['ver'], d['sid'], d['sid'], d['to'], d['from'], d['meth'], d['data'])

	############################################################################

	def to_json(self):

		return json.dumps(self.packet)

	############################################################################

	def get_ver(self):

		return self.packet['ver']

	############################################################################

	def get_sid(self):

		return self.packet['sid']

	############################################################################

	def get_rid(self):

		if 'rid' in self.packet:

			return self.packet['rid']

		else:

			return None

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

		proxy.send_packet(self.packet['to'], self.packet['sid'], json.dumps(self.packet))

	############################################################################

	def send_response(self, proxy):

		if 'rid' in self.packet:

			proxy.send_packet(self.packet['to'], self.packet['rid'], json.dumps(self.packet))

		else:

			proxy.send_packet(self.packet['to'], self.packet['sid'], json.dumps(self.packet))

################################################################################
