# -*- coding: utf-8 -*-

"""
  Copyright (C) 2017 Oleksii Ivanchuk

  This file is part of slick-bitcoinrpc.
  It is subject to the license terms in the LICENSE file found in the
  top-level
  directory of this distribution.

  No part of slick-bitcoinrpc, including this file, may be copied, modified,
  propagated, or distributed except according to the terms contained in the
  LICENSE file
"""

from itertools import count
import ujson

import base64
from configobj import ConfigObj
from pycurl import Curl

try:
    import urlparse
except:
    from urllib import parse as urlparse

try:
    from cStringIO import StringIO
except:
    try:
        from StringIO import StringIO
    except ImportError:
        from io import BytesIO as StringIO

from .exc import RpcException

DEFAULT_HTTP_TIMEOUT = 30
DEFAULT_RPC_PORT = 19119 # Default RPC port for eccoin


class Proxy(object):
    _ids = count(0)

    def __init__(self,
                 service_url=None,
                 service_port=None,
                 conf_file=None,
                 timeout=DEFAULT_HTTP_TIMEOUT):
        config = dict()
        if conf_file:
            config = ConfigObj(conf_file)
        if service_url:
            config.update(self.url_to_conf(service_url))
        if service_port:
            config.update(rpcport=service_port)
        elif not config.get('rpcport'):
            config['rpcport'] = DEFAULT_RPC_PORT
        self.conn = self.prepare_connection(config, timeout=timeout)

    def __getattr__(self, method):
        conn = self.conn
        id = next(self._ids)
        def call(*params):
            postdata = ujson.dumps({"jsonrpc": "2.0",
                                    "method": method,
                                    "params": params,
                                    "id": id})
            body = StringIO()
            conn.setopt(conn.WRITEFUNCTION, body.write)
            conn.setopt(conn.POSTFIELDS, postdata)
            conn.perform()
            resp = ujson.loads(body.getvalue())
            if resp.get('error') is not None:
                raise RpcException(resp['error'], method, params)
            return resp['result']
        return call

    @classmethod
    def prepare_connection(cls, conf, timeout=DEFAULT_HTTP_TIMEOUT):
        url = 'http://%s:%s' % (conf['rpchost'], conf['rpcport'])
        auth_header = b"Basic " + base64.b64encode(
                                    ('%s:%s' %
                                     (conf['rpcuser'],
                                      conf['rpcpassword'])).encode('utf8'))
        conn = Curl()
        conn.setopt(conn.HTTPHEADER, ["Authorization: %s"
                                      % auth_header.decode('utf8')])
        conn.setopt(conn.CONNECTTIMEOUT, timeout)
        conn.setopt(conn.TIMEOUT, timeout)
        conn.setopt(conn.URL, url)
        conn.setopt(conn.POST, 1)
        return conn

    @classmethod
    def url_to_conf(cls, service_url):
        url = urlparse.urlparse(service_url)
        return dict(rpchost=url.hostname, rpcport=url.port,
                    rpcuser=url.username, rpcpassword=url.password)
