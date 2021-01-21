# ECC Service Advertisment Mechanism
ECC/Roam needs a means of advertising services to apps. Examples include faucets, chat translation services, group message brokers, etc.

Service types, with corresponding messaging protocols, are identified by Protocol IDs and may also require names, for example in the case of group message brokers where different brokers serve different subsets of messaging groups, all using the same Protocol ID.

It is proposed that the AODV mechanism be enhanced to enable a broadcast messaging capability that is used to advertise services to the entire network in an efficient manner.

From an application perspective, the following enhancemenmts would be made available:

## getroutingpubkey
The `getroutingpubkey` RPC should either be overloaded with optional arguments, or a new RPC call provided with the following syntax:

	getroutingpubkey - returns local routing tag
	getroutingpubkey <protocol ID> - returns any instance of a routing tag hosting a servivce identified by <protocol ID>
	getroutingpubkey <protocol ID> <name> - returns any instance of a routing tag hosting a service identified by <protocolID> and <name>

Applications would use the first form to obtain their own local routing tag.

Applications would use the second form to obtain for example the routing tag of a node hosting a faucet.

Applications would use the third form to obtain the routing tag of a group message broker that is handling the named group.

## advertiseservice

The `advertiseservice` RPC call will be used to advertise a service to the network. The syntax is as follows:

	advertiseservice <protocol ID> - advertises a service identified by <protocol ID>
	advertiseservice <protocol ID> <name> - advertises a service identified by <protocol ID> and <name>

## Implementation
It is suggested that the AODV mechanism for locating routes, which in so doing must span the entire network, be enhanced with special handling of the all zeros routing tag to communicate service advertisments. Such service advertisments should be repeated at fixed intervals to (a) support late network joining instances of eccoind and (b) support a timeout mechanism for service table entry deletion.

eccoind would maintain a cache table of service advertisments, with a timeout mechanism to handle service table entry deletion.

In cases where multiple hosts provide the same service advertisment, this will facilitate both load balancing and fault tolerance, with the service resolution mechanism in eccoind randomly selecting one of the available  service instances.

With the service resolution mechanism embedded in eccoind, this leaves the door open to future enhancements that might support service redirection, performance based prioritization, enhanced security where some services may require the provision of a key for service resolution, etc.