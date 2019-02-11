#!/usr/bin/env python3

import socket
import re
import platform
import sys
import subprocess

def getcpu():
    curr = re.compile("^CPU MHz:\s*[0-9]+\.[0-9]+$")
    max = re.compile("^CPU max MHz:\s*[0-9]+\.[0-9]+$")
    fl = re.compile("\d+.?\d+")
    foundcurr = False
    foundmax = False
    test = subprocess.Popen(["lscpu"], stdout=subprocess.PIPE, bufsize=1, universal_newlines=True)
    output = test.communicate()[0]    
    text = output.split('\n')
    for t in text:
        if re.match(max,t):
            maxlist = [float(i) for i in re.findall(fl,t)]
            foundmax = True
        elif re.match(curr,t):
            currlist = [float(i) for i in re.findall(fl,t)]
            foundcurr = True
    if foundmax and foundcurr:
        return str(int(currlist[0]/maxlist[0]*100)) + '%'
    else:
        print("Chyba pri lscpu.")
        sys.exit(1)

# re typ pozadavku
hostname = re.compile("^GET\s+\/hostname.*$")
cpuname = re.compile("^GET\s+\/cpu-name.*$")
load = re.compile("^GET\s+\/load\s+.*$")
loadr = re.compile("^GET\s+\/load\?refresh=[0-9]+\s+.*$")
# re typ accept
tp = re.compile("^Accept:\s+text\/plain$.*$")
aj = re.compile("^Accept:\s+application\/json$.*$")

s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
s.bind(("merlin.fit.vutbr.cz",12225))
s.listen(1)
conn,address = s.accept() # conn = socket na druhe strane, address = tuple ve formatu addr + port druhe strany

while 1:
    data = conn.recv(1024)
    if not data:
        break
    text = data.decode().split('\r\n')
    
    ToJson = False # budeme prevadet na JSON
    FoundType = False # zatim nenalezl na zadnem radku typ requestu
    FoundAccept = False # zatim nenalezl na zadnem radku Accept type    
    for line in text:
        # validace typu requestu GET /.....
        if not FoundType:
            if re.match(line,hostname):
                FoundType = True
                typ = "hostname"
                data = socket.gethostname()
            elif re.match(line,cpuname):
                FoundType = True
                typ = "cpu"
                data = platform.processor()
            elif re.match(line,load):
                FoundType = True
                typ = "zatizeni"
                data = getcpu()
            elif re.match(line,loadr):
                FoundType = True
                typ = "zatizeni"
                data = getcpu()
        if not FoundAccept:
            if re.match(line,aj):
                FoundAccept = True
                ToJson = True
            elif re.match(line,tp):
                FoundAccept = True
      
    if (FoundType and FoundAccept) or (FoundType and not FoundAccept): # nalezeny oba, rid se podle typu Accept || nalezen jen typ, Accept automaticky na text/plain
        if ToJson: # preved na JSON, typ se nastavoval uz v analyze
            data = "{ \"typ : " + typ + "\" , \"hodnota : " + data + "\" }"
        conn.sendall(data)             
    else: # nebyl nalezen typ, exception
        print("Spatny typ requestu.")
        sys.exit(1)

