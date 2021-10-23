import dns.resolver
result = dns.resolver.resolve('ecchat.io', 'TXT')
for txt in result:
    print('TXT Record : ', txt.to_text())
