# ecchat

**ecchat** is a decentralized messenger application built on the **ecc network** (aka Roam) with integrated support for multi-chain cryptocurrency payments and cross-chain trusted swaps, with cross-chain atomic swaps in the pipeline. The transactional protocol underpinning ecchat will become the basis for a fully decentralized, non-custodial, non-KYC exchange.

![ecchat 1.4 initial screen](https://raw.githubusercontent.com/project-ecc/ecchat/master/ecchat-1.4.png)

## The ecc Network

The **ecc network** is a virtual network overlaid on the mesh network formed by eccoind nodes, which in turn are interconnected using a mix of IPv4, IPv6 and tor. The eccoind nodes act as gateways into the network for ecc applications, which  may be client applications (such as chat or dex) or services (such as translation or vpn).

The **ecc network** provides a packet transport with the following characteristics:

- Uniplex (send and receive paths are diversely routed)
- Low latency, non-blocking transport (blockchain NOT used)
- AODV routed via a variable number of hops
- Crypto key addressed with intermediate nodes unaware of the final destination
- Encrypted (per packet) using the receiver's public key
- Signed (per packet) using the sender's private key

Together these mechanisms result in strong privacy characteristics:

- Resistant to content surveillance
- Resistant to "man in the middle" attacks
- Resistant to impersonation attacks
- Resistant to meta data collection

## The ecc Network Ecosystem

The **ecc network ecosystem** consists of a growing range of client applications and services.

| App / Service | Status | Description |
|:--|:--|:--|
|ecchat|Released|Messenger application with integrated cross chain payments & swaps
|ececho|Released|Chat bot which echos back any messages sent to it|
|ecresolve|In Dev|Name resolution service for services, chat names & chat groups|
|ectranslate|In Dev|Real time translation service for messaging|
|ecfaucet|Pending|Everyone loves FREE MONEY !!!|
|ecchatgroup|Pending|Decentralized group chat services - anyone can create their own groups|
|ecnodeproxy|Pending|Infrastructure support for mobile deployment of ecchat|
|ectorrent|Pending|Implementation of BitTorrent over ecc network|
|ecvpn|Pending|Fully decentralized VPN with URL > geolocation mapping|
|ecdex|Pending|Decentralized, non-custodial, non-KYC exchange|


## ecc chat names

To start an ecchat conversation with someone (or something) you must know their **ecc chat name**. There are three types of chat name available on the ecc network:

| Name Type | Example |
|:--|:--|
|Routing Tag|BAU3rdcs0BnDtOhXX/PjoR/99Toft8tyYWYxdTFlfiTAPQb43akF/waOo23REBVVRrSdsMX8iPHKDYgqhEGetSY=|
|Name|bob|
|Reserved Name|satoshi|

Names and reserved names are automatically resolved to routing tags on behalf of users by the ecresolve service.

Names and reserved names differ only in their reservation status. The ecc network keeps track of names currently is use by active ecchat sessions and permits users to choose unique chat names on a first come first served basis. When a user exits their ecchat session, the chat name they used becomes available for anyone else to use (after a 90s timeout period). Users who wish to retain their preferred chat name across multiple ecchat sessions may chose to reserve any chat name for a period of their choosing measured in days, weeks, months or years. Name reservation is free, but requires a pay-to-self transaction of 10,000 ECC locked for the corresponding period. This is automated by ecchat using the /reserve command:

	/reserve satoshi 365 days

A chat name reservation request will fail if the name is in use by any other ecchat session, is the subject of an unexpired reservation, of if the user has less than 10,000 ECC available (unlocked) in their wallet. There is no limit on the number of names that may be reserved, subject to available wallet balance. 

Chat names are _not_ tied to ecc network routing tags and may therefore be reused across different nodes and devices - desktop or mobile.

## Further Information

| Resource | Description |
|:--|:--|
|[quickstart.md](quickstart.md)|ecchat - Quick Start Guide|
|[compatibility.md](compatibility.md)|ecchat - Compatibility with coins & tokens|
|[eccprotocol.md](eccprotocol.md)|Developer documentation for the ecc message protocols|
|[ecchat @ YouTube](https://www.youtube.com/channel/UCRoM0_frNi8Lx9yL-aK8siA)|ecchat YouTube channel with live demonstrations|


