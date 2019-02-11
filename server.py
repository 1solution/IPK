#!/usr/bin/env python3

from http import client
import socket
import codecs
import re
import platform

# ty regexy potom rozsir o ruzne znaky mezer atd.

# re typ pozadavku
hostname = re.compile("^GET \/hostname")
cpuname = re.compile("^GET \/cpu-name")
load = re.compile("^GET \/load ")
loadr = re.compile("^GET \/load\?refresh=[0-9]+ ")
# re typ accept
tp = re.compile("^Accept: text\/plain$")
aj = re.compile("^Accept: application\/json$")

s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
s.bind(("merlin.fit.vutbr.cz",12345))
s.listen(1)
conn,address = s.accept() # conn = novy socket na ktery posilam, address = tuple ve formatu addr + port druhe strany

while 1:
    data = conn.recv(1024)
    if not data:
        break
    text = data.decode().split('\r\n')

    # bacha na poradi prvku nezalezi, testovat tedy postupne a potom pomoci t/f podminek overit ze vse proslo jak melo
    
    FoundType = False # zatim nenalezl na zadnem radku typ requestu
    FoundAccept = False # zatim nenalezl na zadnem radku Accept type
    
    for line in text:
        # validace typu requestu GET /.....
        if not FoundType:
            if re.match(line,hostname):
                FoundType = True
                print(socket.gethostname())
            elif re.match(line,cpuname):
                FoundType = True
                print(platform.processor())
            elif re.match(line,load):
                FoundType = True
                print("Vypocitej load")
            elif re.match(line,loadr):
                FoundType = True
                print("Vypocitej load s refresh")
        if not FoundAccept:
            if re.match(line,aj):
                FoundAccept = True
                print("Vygeneruj Accept format A/J") # ciste jako string, do json to zpracuje TCP
            elif re.match(line,tp):
                FoundAccept = True
                print("Vygeneruj Accept format T/P")
                
    if FoundType and not FoundAccept: # typ nalezen, ale nebyl zadan Accept typ, poslat defaultne text/plain a odeslat
        print("Vygeneruj Accept t/p")        
    elif not FoundType: # nebyl nalezen typ, exception
        print("Exception")
    else: # nalezeny oba, odeslat
        
    # odesilani    
    conn.sendall(data)

