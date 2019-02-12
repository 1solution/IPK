#!/usr/bin/env python3

import socket # je tu kvuli socketum
import re # je tu kvuli regexum pri zpracovani lscpu
import platform # je tu kvuli nazvu procesoru
import subprocess # je tu kvuli spusteni lscpu

# vsechno to dej do jednoho velkyho try a osetruj exceptions

class CpuError(Exception): # vlastni vyjimka, chyba pri volani lscpu
    pass
class RequestError(Exception): # vlastni vyjimka, request ma blbou strukturu
    pass

def getcpu(): # vraci % zatizeni cpu
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
        return str(int(currlist[0]/maxlist[0]*100)) + '%\n'
    else:
        return ''

# re typ pozadavku
hostname = re.compile("^GET\s+\/hostname.*$")
cpuname = re.compile("^GET\s+\/cpu-name.*$")
load = re.compile("^GET\s+\/load\s+.*$")
loadr = re.compile("^GET\s+\/load\?refresh=[0-9]+\s+.*$")
# re typ accept
tp = re.compile("^Accept:\s+text\/plain$.*$")
aj = re.compile("^Accept:\s+application\/json$.*$")
# dec cislo, vyhledani refresh rate v radku
dec = re.compile("\d+")

arg_address = "merlin.fit.vutbr.cz" # argument z make
arg_port = 12225 # argument z make

try:
    s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    s.bind((arg_address,arg_port))
    s.listen(1)
    client,address = s.accept() # conn = socket na druhe strane, address = tuple ve formatu addr + port druhe strany
    
    while 1:
        data = client.recv(1024)
        if not data:
            break
        text = data.decode().split('\r\n')

        CustomRequest = False
        ToJson = False # budeme prevadet na JSON
        FoundType = False # zatim nenalezl na zadnem radku typ requestu
        FoundAccept = False # zatim nenalezl na zadnem radku Accept type    
        for line in text:
            # validace typu requestu GET /.....
            if not FoundType:
                
                if re.match(hostname,line): # vrat hostname
                    FoundType = True
                    typ = "hostname"
                    data = socket.gethostname()
                    
                elif re.match(cpuname,line): # vrat nazev cpu
                    FoundType = True
                    typ = "cpu"
                    cpuinfo = subprocess.Popen(["cat /proc/cpuinfo"], stdout=subprocess.PIPE, bufsize=1, universal_newlines=True)
                    output = cpuinfo.communicate()[0]
                    text = output.split('\n')
                    model = re.compile("^model name.*$")
                    model_name = re.compile("(?<=: ).*$")
                    for t in text:
                        print(t)
                        if re.match(model,t):
                            print('NALEZENO.')
                            data = re.findall(model_name,t)
                            data = data[0]
                            break

                elif re.match(loadr,line): # vrat zatez a do Accept pridej refresh
                    FoundType = True
                    typ = "zatizeni"
                    data = getcpu()
                    if len(data) == 0:
                        raise CpuError
                    refresh = [int(i) for i in re.findall(dec,line)]
                    if len(refresh) > 1:
                        raise RequestError
                    refresh = refresh[0] # vyber refresh rate
                    CustomRequest = True # budes vytvaret vlastni textovy request k odeslani
                    
                elif re.match(load,line): # vrat zatez
                    FoundType = True
                    typ = "zatizeni"
                    data = getcpu()
                    if len(data) == 0:
                        raise CpuError
                        
            if not FoundAccept:
                if re.match(aj,line):
                    FoundAccept = True
                    ToJson = True
                elif re.match(tp,line):
                    FoundAccept = True
          
        if (FoundType and FoundAccept) or (FoundType and not FoundAccept): # nalezeny oba, rid se podle typu Accept || nalezen jen typ, Accept automaticky na text/plain          
            if ToJson: # preved na JSON, typ se nastavoval uz v analyze
                data = "{ \"typ : " + typ + "\" , \"hodnota : " + data + "\" }"
                content_type = "application/json"
            else:
                content_type = "text/plain"

            if CustomRequest: # vytvor POST request s refresh
                refr_string = "Refresh: " + refresh + "; " + arg_address + ":" + str(arg_port) + "/load?refresh=" + refresh + "\n"
            else: # vytvor obycejny POST request
                refr_string = ''
            #outcoming = "POST / HTTP/1.1\n" + refr_string + "Host: " + arg_address + ":" + str(arg_port) + " \nContent-Type: " + content_type + "\nContent-Length: " + str(len(data)) + "\n\n" + data
            outcoming = data
            client.sendall(outcoming.encode()) # odeslani requestu
        else: # nebyl nalezen typ, exception
            print("Nebyl nalezen typ requestu GET.")
        client.close()
    s.close()

except socket.error:
    print("Starsi obecna chyba.")
except socket.herror:
    print("Chybna adresa.")
except socket.gaierror:
    print("Chybna adresa.")
except socket.timeout:
    print("Vyprsel cas.")
except InterruptedError:
    print("Doslo k preruseni.")
except CpuError:
    print("Chyba pri volani lscpu.")
except RequestError:
    print("Request ma spatnou strukturu.")