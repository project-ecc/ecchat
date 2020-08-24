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

"""
  Reference:
  https://github.com/bitcoin/bitcoin/blob/master/src/rpc/protocol.h#L32-L85
"""
ERROR_CODES = {
    # Standard JSON-RPC 2.0 errors
    -32600: 'RpcInvalidRequest',
    -32601: 'RpcMethodNotFound',
    -32602: 'RpcInvalidParams',
    -32603: 'RpcInternalError',
    -32700: 'RpcParseError',
    # General application defined errors
    -1: 'RpcMiscError',
    -2: 'RpcForbiddenBySafeMode',
    -3: 'RpcTypeError',
    -5: 'RpcInvalidAddressOrKey',
    -7: 'RpcOutOfMemory',
    -8: 'RpcInvalidParameter',
    -20: 'RpcDatabaseError',
    -22: 'RpcDeserialisationError',
    -25: 'RpcVerifyError',
    -26: 'RpcVerifyRejected',
    -27: 'RpcVerifyAlreadyInChain',
    -28: 'RpcInWarmUp',
    # P2P client errors
    -9: 'RpcClientNotConnected',
    -10: 'RpcClientInInitialDownload',
    -23: 'RpcClientNodeAlreadyAdded',
    -24: 'RpcClientNodeNotAdded',
    -29: 'RpcClientNotConnected',
    -30: 'RpcClientInvalidIpOrsubnet',
    -31: 'RpcClientP2pDisabled',
    # Wallet Errors
    -4: 'RpcWalletError',
    -6: 'RpcWalletInsufficientFunds',
    -11: 'RpcWalletInvalidAccountName',
    -12: 'RpcWalletKeypoolRanOut',
    -13: 'RpcWalletUnlockNeeded',
    -14: 'RpcWalletPassphraseIncorrect',
    -15: 'RpcWalletWrongEncState',
    -16: 'RpcWalletEncryptionFailed',
    -17: 'RpcWalletAlreadyUnlocked'
}

class RpcException(Exception):
    def __init__(ex, error, method, params):
        Exception.__init__(ex)
        ex.code = error['code']
        ex.message = error['message']
        ex.data = error.get('data')
        ex.method = method
        ex.params = params

    def __new__(cls, error, method, params):
        assert cls is RpcException
        cls = globals().get(ERROR_CODES.get(error['code']), cls)
        self = Exception.__new__(cls)
        cls.__init__(self, error, method, params)
        return self

    def __str__(self):
        return ("%s: %s (code %s)" % (self.method, self.message, self.code))

for one in ERROR_CODES.values():
    locals()[one] = type(one, (RpcException,), {})
