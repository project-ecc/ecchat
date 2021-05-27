# Compatibility : ecchat : coins & tokens

This document is a guide to compatibility of **ecchat** with cryptocurrency coins and tokens.

## Bitcoin Based Coins

**ecchat** supports any Bitcoin based coin that in turn supports the following RPC calls:

	getnetworkinfo
	getblockcount
	getconnectioncount	
	getbalance
	getunconfirmedbalance
	walletpassphrase
	getnewaddress
	sendtoaddress

The following coins have been tested with **ecchat**:

|Name|Symbol|URL|
|:--|:--|:--|
|Bitcoin|btc|bitcoin.org|
|Eccoin|ecc|ecc.network|
|Dashcoin|dash|dash.org|
|Dogecoin|doge|dogecoin.com|
|Litecoin|ltc|litecoin.org|
|Millennium Club Coin|mclb|millenniumclub.ca|
|NEXT|next|next.exchange|
|Pirate Chain|arrr|pirate.black|
|Reddcoin|rdd|reddcoin.com|
|Xuez|xuez|xuezcoin.com|


## Monero Based Coins

**ecchat** supports any Monero based coin that is supported by the `monero` Python library.

The following Monero based coins have been tested with **ecchat**:

|Name|Symbol|URL|
|:--|:--|:--|
|Monero|xmr|getmonero.org|

## ERC-20 Tokens

At the current time **ecchat** does not support any ERC-20 tokens.

