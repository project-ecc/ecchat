# ECC Message Protocols

The ECC Message Protocols are a set of protocols, each identified by an integer Protocol ID. The following have been reserved:

| Protocol ID | Protocol Name |
|:-:|:--|
|1|ecchat|
|2|eccvpn|

----------

## 1 : ecchat

This protocol uses a top level JSON structure as follows:

   	{
		"id"   : "1"
		"ver"  : "1"
		"to"   : "<routing tag of destination>"
		"from" : "<routing tag of source>"
		"type" : "<message type>"
		"data" : "<string or nested JSON depending on type>"

The following values for `type` are defined:

|type|Purpose|
|:--|:--|
|chatMsg|Chat message content|
|addrReq|Request new receive address|
|addrRes|Respond with receive address|
|txidInf|Send transaction information|
