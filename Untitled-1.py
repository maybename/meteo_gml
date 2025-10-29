text:bytes = b'GET / HTTP/1.1\r\nHost: 192.168.68.129\r\nUser-Agent: python-requests/2.32.3\r\nAccept-Encoding: gzip, deflate\r\nAccept: */*\r\nConnection: keep-alive\r\n\r\n'
data = text.decode().split("\r\n")
for d in data:
    d.strip()
print(data)