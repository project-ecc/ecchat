# ECC Message Protocols

The ECC Message Protocols are a set of protocols, each identified by an integer Protocol ID. The following have been reserved:

| Protocol ID | Protocol Name |
|:-:|:--|
|1|ecchat|
|2|
|3|ecfaucet|
|4|ectranslate|
|5|ecchatgroup|
|6|ecnodeproxy
|7|ectorrent|
|8|ecvpn|

----------

## 1 : ecchat

This protocol uses a top level JSON structure as follows:

   	{
		"id"   : 1
		"ver"  : 1
		"to"   : "<routing tag of destination>"
		"from" : "<routing tag of source>"
		"meth" : "<method called>"
		"data" : "<nested JSON depending on type>"
	}

The following values for `meth` are defined:

|meth|Purpose|
|:--|:--|
|chatMsg|Chat message content|
|chatAck|Chat message acknowledge|
|addrReq|Request new receive address|
|addrRes|Respond with receive address|
|txidInf|Send transaction information|
|swapInf|Swap proposal information|
|swapReq|Swap execution request|
|swapRes|Swap execution response|

The `data` value for each `meth` are as follows:

### chatMsg

The `chatMsg` method is used to add, replace and delete chat messages.

	{
		"uuid" : "<uuid value>"
		"cmmd" : "add|replace|delete"
		"text" : "<message text>"
		"lang" : "<language code>"
	}

The `lang` field encodes message language using lower case two character ISO 639-1 encoding.

### chatAck

The `chatAck` method is used to acknowledge a `chatMsg` message.

	{
		"uuid" : "<uuid value>"
		"cmmd" : "add|replace|delete"
		"able" : "true|false"
	}

If the value `false` is returned in the `able` field it indicates that the application does not support the command defined in a prior `chatMsg` message.

### addrReq

The `addrReq` method is used to request a new receive address from the other party.

	{
		"uuid" : "<uuid value>"
		"coin" : "<coin symbol>"
		"type" : "P2PKH|P2SH|bech32"
	}

### addrRes

The `addrRes` method is used to reply to a `addrReq` message.

	{
		"uuid" : "<uuid value>"
		"coin" : "<coin symbol>"
		"addr" : "0|<address>"
	}

If the value `0` is returned in the `addr` field it indicates that the other party is unable or unwilling to receive unsolicited sends at this time.

### txidInf

The `txidInf` method is used to send transaction information from the sending party to the other party.

	{
		"uuid" : "<uuid value>"
		"coin" : "<coin symbol>"
		"amnt" : "<coin amount>"
		"addr" : "<receive address>"
		"txid" : "<transaction ID>"
	}

### swapInf

The `swapInf` method is used to send swap proposal information.

	{
		"uuid" : "<uuid value>"
		"cogv" : "<coin symbol - give>"
		"amgv" : "<coin amount - give>"
		"cotk" : "<coin symbol - take>"
		"amtk" : "<coin amount - take>"
	}

### swapReq

The `swapReq` method is used to initiate execution of the prior swap proposal, including the executing party's address information.

	{
		"uuid" : "<uuid value>"
		"cogv" : "<coin symbol - give>"
		"adgv" : "<address     - give>"
	}

### swapRes

The `swapRe`s method is used to confirm execution of the swap, including proposing party's address information.

	{
		"uuid" : "<uuid value>"
		"cotk" : "<coin symbol - take>"
		"adtk" : "0|<address   - take>"
	} 

If the value `0` is returned in the `addr` field it indicates that the other party is unable or unwilling to proceed with swap execution.

### ecchat `/send` command

The `addrReq`, `addrRes` and `txidInf` methods are used together to support the ecchat /send command.

![alt text](https://www.websequencediagrams.com/cgi-bin/cdraw?lz=dGl0bGUgZWNjaGF0IC9zZW5kIGNvbW1hbmQKcGFydGljaXBhbnQgQm9iJ3MgZWNjb2kAAhhoYXQAJg1BbGljZQABGgAUBwBLBW5vdGUgb3ZlcgBBDToAgQkHMTAwMCBlY2MKAF8MLT4AUg46AC0IYWRkclJlcQAfDi0-AEsOdGltZW91dCAxMHMKAIEaDgBLDW9pbmQ6UlBDOmdldG5ld2FkZHJlcwAlDW9pbmQAehFlY2MgABkTAIExBQCBUw4AgScNcwCBUg8AgmcNAIECBXNlbmR0bwCAfwgAgwcNAIFTD2VjYyB0eGlkAIIOJnR4aWRJbmYAgn0LAIJODwCCewggcmVjZWl2ZWQgLi4uCg&s=default)

The UML sequence specification for the above diagram follows:

	title ecchat /send command
	participant Bob's eccoind
	participant Bob's ecchat
	participant Alice's ecchat
	participant Alice's eccoind
	note over Bob's ecchat: /send 1000 ecc
	Bob's ecchat->Alice's ecchat: ecchat:addrReq
	Bob's ecchat-->Bob's ecchat: timeout 10s
	Alice's ecchat->Alice's eccoind:RPC:getnewaddress
	Alice's eccoind->Alice's ecchat:ecc address
	Alice's ecchat->Bob's ecchat: ecchat:addrRes
	Bob's ecchat->Bob's eccoind:RPC:sendtoaddress
	Bob's eccoind->Bob's ecchat:ecc txid
	Bob's ecchat->Alice's ecchat: ecchat:txidInf
	note over Alice's ecchat:1000 ecc received ...

### ecchat `/swap` command

The `swapInf`, `swapReq`, `swapRes` and `txidInf` methods are used together to support the ecchat /swap command.

![alt text](https://www.websequencediagrams.com/cgi-bin/cdraw?lz=dGl0bGUgZWNjaGF0IC9zd2FwIGNvbW1hbmQKcGFydGljaXBhbnQgQm9iJ3MgeHl6Y29pAAYVZWMAARkAVwUAQQ1BbGljZQABGgAUBwBZEQAvCAB-CW5vdGUgb3ZlcgBeDToAgUEHMTAwMCBlY2MgZm9yIDEgeHl6CgCBBgwtPgB5DjoANwhzd2FwSW5mAB8OLT4AVQ50aW1lb3V0IDYwcwBnIDEAFnEAgUkQL2V4ZWN1dGUKAIJrDgCBdQ1vaW5kOlJQQzpnZXRuZXdhZGRyZXNzACYMb2luZACCJBFlY2MgABkTAIJbBQCDBw4AglMLUmVxAHsQAIJ8EgCCWggxMHMAgykPAIR_DjogAIEkEgCFIQ4AgywQeHl6AIErCQCDaSlSZQCBTxIAhQEQAII7BXNlbmR0bwCCMBAAgQIKAIRnD3h5eiB0eGlkAIIYJnR4aWRJbmYAhWIYAIVhBSByZWNlaXZlZCAuLi4AgiYVAINjDACBIQ4Ah0ANAIVlD2VjYwCBJAYAhiElAIEYEgCGYA8Ahg8JAIEiDQo&s=default)

The UML sequence specification for the above diagram follows:

	title ecchat /swap command
	participant Bob's xyzcoind
	participant Bob's eccoind
	participant Bob's ecchat
	participant Alice's ecchat
	participant Alice's eccoind
	participant Alice's xyzcoind
	note over Bob's ecchat: /swap 1000 ecc for 1 xyz
	Bob's ecchat->Alice's ecchat: ecchat:swapInf
	Bob's ecchat-->Bob's ecchat: timeout 60s
	note over Bob's ecchat: /swap 1100 ecc for 1 xyz
	Bob's ecchat->Alice's ecchat: ecchat:swapInf
	Bob's ecchat-->Bob's ecchat: timeout 60s
	note over Alice's ecchat: /execute
	Alice's ecchat->Alice's eccoind:RPC:getnewaddress
	Alice's eccoind->Alice's ecchat:ecc address
	Alice's ecchat->Bob's ecchat: ecchat:swapReq
	Alice's ecchat-->Alice's ecchat: timeout 10s
	Bob's ecchat->Bob's xyzcoind: RPC:getnewaddress
	Bob's xyzcoind->Bob's ecchat: xyz address
	Bob's ecchat->Alice's ecchat: ecchat:swapRes
	Alice's ecchat->Alice's xyzcoind:RPC:sendtoaddress
	Alice's xyzcoind->Alice's ecchat:xyz txid
	Alice's ecchat->Bob's ecchat: ecchat:txidInf
	note over Bob's ecchat:1 xyz received ...
	Bob's ecchat->Bob's eccoind:RPC:sendtoaddress
	Bob's eccoind->Bob's ecchat:ecc txid
	Bob's ecchat->Alice's ecchat: ecchat:txidInf
	note over Alice's ecchat:1100 ecc received ...

----------

## 2 : ec....

This protocol uses a top level JSON structure as follows:

   	{
		"id"   : 2
		"ver"  : 1
		"to"   : "<routing tag of destination>"
		"from" : "<routing tag of source>"
		"meth" : "<method called>"
		"data" : "<nested JSON depending on type>"
	}

The following values for `meth` are defined:

|meth|Purpose|
|:--|:--|

----------

## 3 : ecfaucet

This protocol uses a top level JSON structure as follows:

   	{
		"id"   : 3
		"ver"  : 1
		"to"   : "<routing tag of destination>"
		"from" : "<routing tag of source>"
		"meth" : "<method called>"
		"data" : "<nested JSON depending on type>"
	}

The following values for `meth` are defined:

|meth|Purpose|
|:--|:--|
|faucetReq|Faucet request|
|faucetRes|Faucet response|

The `data` value for each `meth` are as follows:

### faucetReq

The `faucetReq` method is used to request a payout from the faucet for coin `coin` to be sent to the address `addr`.

	{
		"coin" : "<coin symbol>"
		"addr" : "<address>"
	}

### faucetRes

The `faucetRes` method is used to reply to a `faucetReq` message. It is used to send transaction information from the faucet to the requesting party.


	{
		"coin" : "<coin symbol>"
		"amnt" : "<coin amount>"
		"addr" : "<receive address>"
		"txid" : "<transaction ID>"
		"erno" : "<error number>"
		"errr" : "<error text>"
	}

In the event of an error preventing a faucet from making a payout, the `amnt`, `addr` and `txid` fields will all be set to `0` with the `erno` field nonzero and the `errr` field containing an error message.

The following `erno` values are defined:

|erno|Meaning|
|:--|:--|
|0|Request completed normally|
|1|Coin identified in request unavailable at this faucet|
|2|Invalid address|
|3|Faucet previously visited by address <address>|
|4|Faucet previously visited by node <tag>|
|5|Faucet balance too low - payouts blocked|
|6|Faucet wallet is currently locked|

----------

## 4 : ectranslate

This protocol uses a top level JSON structure as follows:

   	{
		"id"   : 4
		"ver"  : 1
		"to"   : "<routing tag of destination>"
		"from" : "<routing tag of source>"
		"meth" : "<method called>"
		"data" : "<nested JSON depending on type>"
	}

----------

## 5 : ecchatgroup

This protocol uses a top level JSON structure as follows:

   	{
		"id"   : 5
		"ver"  : 1
		"to"   : "<routing tag of destination>"
		"from" : "<routing tag of source>"
		"meth" : "<method called>"
		"data" : "<nested JSON depending on type>"
	}

----------

## 6 : ecnodeproxy

This protocol uses a top level JSON structure as follows:

   	{
		"id"   : 6
		"ver"  : 1
		"to"   : "<routing tag of destination>"
		"from" : "<routing tag of source>"
		"meth" : "<method called>"
		"data" : "<nested JSON depending on type>"
	}

----------

## 7 : ectorrent

This protocol uses a top level JSON structure as follows:

   	{
		"id"   : 7
		"ver"  : 1
		"to"   : "<routing tag of destination>"
		"from" : "<routing tag of source>"
		"meth" : "<method called>"
		"data" : "<nested JSON depending on type>"
	}

----------

## 8 : ecvpn

This protocol uses a top level JSON structure as follows:

   	{
		"id"   : 8
		"ver"  : 1
		"to"   : "<routing tag of destination>"
		"from" : "<routing tag of source>"
		"meth" : "<method called>"
		"data" : "<nested JSON depending on type>"
	}

