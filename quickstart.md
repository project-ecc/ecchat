# ecchat - Quick Start Guide

**ecchat** is a decentralized messaging application with integrated support for cross-chain transactions

This Quick Start Guide helps you get started with ecchat version 1.3, the MVP beta release.

## Installing and Configuring ecchat on Linux

1 - Ensure that eccoin.conf contains the following settings using your preferred text file editor:

	$ vi ~/.eccoin/eccoin.conf

	rpcuser=any_user_name
	rpcpassword=any_password
	rpcport=19119
	rpcconnect=127.0.0.1
	rpcallowip=127.0.0.1
	server=1
	daemon=1
	beta=1
	zmqpubpacket=tcp://127.0.0.1:28001
	zmqpubhashblock=tcp://127.0.0.1:28001

2 - Start eccoind in your preferred manner - command line or Lynx - to make the conf file changes current:

	$ ~/eccoin/eccoind

3 - Ensure eccoind is running and responding to RPC commands:

	$ ~/eccoin/eccoind getinfo

4 - Ensure eccoind is a compatible version by checking that `version` returned by the previous command is in the range 30000 - 30201.

5 - Create a directory for ecchat:

	$ mkdir ~/ecchat
	$ cd ~/ecchat

6 - Download the ecchat executable:

	$ wget https://github.com/project-ecc/ecchat/releases/download/1.3/ecchat-1.3-linux-x86_64.tar.gz

7 - Extract the ecchat executable:

	$ tar xvf ecchat-1.3-linux-x86_64.tar.gz

8 - Check that ecchat's md5 and sha256 file checksums are correct:

	$ md5sum ecchat
	0679f35c710a46ec66a538a17eee3ad6  ecchat
	$ sha256sum ecchat
	367616c016c18f3a199a17e73c11fd11e07094bb7dbd683670283c27ff9ec5a0  ecchat

If either of these checksums do not match up, your copy of ecchat may have been tampered with and you should NOT run it.

9 - Run ecchat with the --help option to familiarise yourself with the available command line options:

	$ ./ecchat --help

10 - Run ecchat with your first conversation with the ececho service:

	$ ./ecchat -n my_name -o ececho -t ececho

You should see something resembling the following:

![ecchat 1.3 initial screen](https://raw.githubusercontent.com/project-ecc/ecchat/master/ecchat-1.3.png)

11 - Enter a short message which ececho will repeat back to you.

12 - Text with a / prefix is a command to ecchat:

	/help - lists all / commands
	/keys - info on recall, replace, erase, scroll and exit

13 - While you are chatting with ececho, take a note of your routing tag which you'll need to give to someone else wishing to chat with you via ecchat:

	/tag

depending on your terminal emulation app, you should be able to copy this to the clipboard. With Putty on Windows this is done with SHIFT and a left click mouse drag.

Alternatively you can take a screen shot of your routing tag as a QR code:

	/qr

14 - The first time ecchat is run it creates a file `ecchat.conf`. You may use this file to add RPC connections to additional crypto nodes running either locally or on remote servers. ecchat 1.3 supports most Bitcoin and Monero derived nodes. The following have been tested and are known to work. You are welcome to try others, numbering in the hundreds, that should also work. 

	ltc  : Litecoin
	doge : Dogecoin
	xmr  : Monero
	rdd  : Reddcoin
	