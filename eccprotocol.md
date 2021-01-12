# ECC Message Protocols

The ECC Message Protocols are a set of protocols, each identified by an integer Protocol ID. The following have been reserved:

| Protocol ID | Protocol Name |
|:-:|:--|
|1|ecchat|
|2|ecvpn|
|3|ectorrent|

----------

## 1 : ecchat

This protocol uses a top level JSON structure as follows:

   	{
		"id"   : 1
		"ver"  : 1
		"to"   : "<routing tag of destination>"
		"from" : "<routing tag of source>"
		"type" : "<message type>"
		"data" : "<nested JSON depending on type>"
	}

The following values for `type` are defined:

|type|Purpose|
|:--|:--|
|chatMsg|Chat message content|
|chatAck|Chat message acknowledge|
|addrReq|Request new receive address|
|addrRes|Respond with receive address|
|txidInf|Send transaction information|

The `data` value for each `type` are as follows:

### chatMsg

The `chatMsg` message type is used to add, replace and delete chat messages.

	{
		"uuid" : "<uuid value>"
		"cmmd" : "add|replace|delete"
		"text" : "<message text>"
	}

### chatAck

The `chatAck` message type is used to acknowledge a `chatMsg` type message.

	{
		"uuid" : "<uuid value>"
		"cmmd" : "add|replace|delete"
	}

### addrReq

The `addrReq` message type is used to request a new receive address from the other party.

	{
		"coin" : "<ticker symbol>"
		"type" : "P2PKH|P2SH|bech32"
	}

### addrRes

The `addrRes` message type is used to reply to a `addrReq` type message.

	{
		"coin" : "<ticker symbol>"
		"addr" : "0|<address>"
	}

If the value `0` is returned in the `addr` field it indicates that the other party is unable or unwilling to receive unsolicited sends at this time.

### txidInf

The `txidInf` message type is used to send transaction information from the sending party to the other party.

	{
		"coin" : "<ticker symbol>"
		"amnt" : "<coin amount>"
		"addr" : "<receive address>"
		"txid" : "<transaction ID>"
	}
		