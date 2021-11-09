# ecchat

ecchat is a decentralized messenger application built on the ecc message bus with integrated support for multi-chain cryptocurrency payments and cross-chain trusted swaps, with cross-chain atomic swaps in the pipeline.

![ecchat 1.4 initial screen](https://raw.githubusercontent.com/project-ecc/ecchat/master/ecchat-1.4.png)

## The ecc Network

The ecc network is a virtual network overlaid on the mesh network formed by eccoind nodes, which in turn are interconnected using a mix of IPv4, IPv6 and tor. The eccoind nodes act as gateways into the network for ecc applications, which  may be client applications (such as chat or dex) or services (such as translation or vpn).

The ecc network provides a packet transport with the following characteristics:

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

The ecc network ecosystem consists of a growing range of client applications and services.

| App / Service | Status | Description |
|:--|:--|:--|
|ecchat|Released|Messenger application with integrated cross chain payments & swaps
|ecresolve|In Dev|Network name resolution service for services, chat names & chat groups|
|ectranslate|In Dev|Real time translation service for ecchat|
|ecfaucet|Pending|Everyone loves FREE MONEY !!!|
|ecchatgroup|Pending|Decentralized group chat services - anyone can create their own groups|
|ecnodeproxy|Pending|Infrastructure support for mobile deployment of ecchat|
|ectorrent|Pending|Implementation of BitTorrent over ecc network|
|ecvpn|Pending|Fully decentralized VPN with URL > geolocation mapping|
|ecdex|Pending|Decentralized, non-custodial, non-KYC exchange|


## ecchat - features & capabilities


### Further Information

| Resource | Description |
|:--|:--|
|[quickstart.md](quickstart.md)|ecchat - Quick Start Guide|
|[compatibility.md](compatibility.md)|ecchat - Compatibility with coins & tokens|
|[eccprotocol.md](eccprotocol.md)|Developer documentation for the ecc message protocols|
|[ecchat @ YouTube](https://www.youtube.com/channel/UCRoM0_frNi8Lx9yL-aK8siA)|ecchat YouTube channel with live demonstrations|


