#!/usr/bin/env python3

from http import client
import socket
import codecs
import re
import platform

# ty regexy potom rozsir o ruzne znaky mezer atd.

hostname = re.compile("^GET \/hostname")
cpuname = re.compile("^GET \/cpu-name")
load = re.compile("^GET \/load ")
loadr = re.compile("^GET \/load\?refresh=[0-9]+ ")

tp = re.compile("^Accept: text\/plain$")
aj = re.compile("^Accept: application\/json$")

s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
s.bind(("merlin.fit.vutbr.cz",12345))
s.listen(1)
conn,address = s.accept() # conn = novy socket na ktery posilam, address = tuple ve formatu addr + port druhe strany

while 1:
    data = conn.recv(2048)
    if not data:
        break

    conn.sendall(data)

    text = data.decode().split('\r\n')

    # validace requestu
    if re.match(text[0],hostname):
        print(socket.gethostname())
    elif re.match(text[0],cpuname):
        print(platform.processor())
    elif re.match(text[0],load):

    elif re.match(text[0],loadr):

    else:
        # raise, except, spatny request

    # zpracovani typu accept

    if re.match(text[2],aj):

    else: # byl zadan text/plain jiny typ accept, poslat defaultne text/plain # bacha accept tam vubec byt nemusi.
        # json format: { "type" : "OK", "value":"25%" }



