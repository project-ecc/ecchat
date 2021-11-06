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
|Bitcoin|btc|[bitcoin.org](http://bitcoin.org)|
|BitGreen|bitg|[bitg.org](http://bitg.org)|
|Eccoin|ecc|[ecc.network](http://ecc.network)|
|Dash|dash|[dash.org](http://dash.org)|
|Dogecoin|doge|[dogecoin.com](http://dogecoin.com)|
|Litecoin|ltc|[litecoin.org](http://litecoin.org)|
|Millennium Club Coin|mclb|[millenniumclub.ca](http://millenniumclub.ca)|
|NEXT|next|[next.exchange](http://next.exchange)|
|Pirate Chain|arrr|[pirate.black](http://pirate.black)|
|Qtum|qtum|[qtum.org](http://qtum.org)|
|Reddcoin|rdd|[reddcoin.com](http://reddcoin.com)|
|Syscoin|sys|[syscoin.org](http://syscoin.org)|
|Xuez|xuez|[xuezcoin.com](http://xuezcoin.com)|


## Monero Based Coins

**ecchat** supports any Monero based coin that is supported by the `monero` Python library.

The following Monero based coins have been tested with **ecchat**:

|Name|Symbol|URL|
|:--|:--|:--|
|Monero|xmr|[getmonero.org](http://getmonero.org)|

## ERC-20 Tokens

At the current time **ecchat** does not support any ERC-20 tokens.

