#!/usr/bin/env python3

import socket # je tu kvuli socketum
import re # je tu kvuli regexum pri zpracovani lscpu
import platform # je tu kvuli nazvu procesoru
import subprocess # je tu kvuli spusteni lscpu
import sys # je tu kvuli argv[1]

# odladit blbosti jako spatny argument, cas refresh mimo vteriny, fakeregexy apod.
# napsat manual MD
# 400, 408, nahrad celkove chyby odeslanim respond na clienta misto print()

if len(sys.argv) is not 2: # test na argumenty
    print("Spatne argumenty.")
    sys.exit(1)

class CpuError(Exception): # vlastni vyjimka, chyba pri volani lscpu
    pass
class RequestError(Exception): # vlastni vyjimka, request ma blbou strukturu
    pass

def getcpu(): # vraci % zatizeni cpu
    curr = re.compile("^CPU MHz:\s*[0-9]+[\,,\.][0-9]+$")
    max = re.compile("^CPU max MHz:\s*[0-9]+[\,,\.][0-9]+$")
    fl = re.compile("\d+.?\d+")
    foundcurr = False
    foundmax = False
    test = subprocess.Popen(["lscpu"], stdout=subprocess.PIPE, bufsize=1, universal_newlines=True)
    output = test.communicate()[0]    
    text = output.split('\n')
    for t in text:
        if re.match(max,t):
            maxlist = [w.replace(',','.') for w in re.findall(fl,t)]
            maxlist = [float(i) for i in maxlist]
            foundmax = True
        elif re.match(curr,t):
            currlist = [float(i) for i in re.findall(fl,t)]
            foundcurr = True
    if foundmax and foundcurr:
        return str(int(currlist[0]/maxlist[0]*100)) + '%'
    else:
        return ''

# re typ pozadavku
hostname = re.compile("^GET\s+\/hostname(\s+\w+.*)*") # bacha, u tech regexu to nejspis muze byt soucasti dalsiho radku..
cpuname = re.compile("^GET\s+\/cpu-name(\s+\w+.*)*")
load = re.compile("^GET\s+\/load(\s+\w+.*)*")
loadr = re.compile("^GET\s+\/load\?refresh=[0-9]+(\s+\w+.*)")

# re typ ignore
icon = re.compile("^GET\s+\/favicon.ico(\s+\w+.*)*")

# re typ accept
tp = re.compile("^Accept:\s+text\/plain(\s+\w+.*)*")
aj = re.compile("^Accept:\s+application\/json(\s+\w+.*)*")
# dec cislo, vyhledani refresh rate v radku
dec = re.compile("\d+")

try:
    s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    arg_address = ''.join(socket.gethostbyname_ex(socket.gethostname())[2]) # lokalni server
    print(arg_address)    
    arg_port = sys.argv[1] # argument z make
    s.bind((arg_address, int(arg_port)))
except socket.error:
    print("Chyba pri vytvareni socketu.")
else:
    s.listen(0)

    while True:
        try:
            client,address = s.accept() # conn = socket na druhe strane, address = tuple ve formatu addr + port druhe strany

            data = client.recv(1024)
            if not data:
                client.close()
                break
            text = data.decode().split('\r\n')

            CustomRequest = False
            ToJson = False # budeme prevadet na JSON
            FoundType = False # zatim nenalezl na zadnem radku typ requestu
            FoundAccept = False # zatim nenalezl na zadnem radku Accept type

            for line in text:
                # validace typu requestu GET /.....
                if not FoundType:

                    if re.match(hostname,line): # vrat hostname (= hostname.domainname)
                        FoundType = True
                        typ = "hostname"
                        data = socket.gethostname()

                    elif re.match(cpuname,line): # vrat nazev cpu
                        FoundType = True
                        typ = "cpu"
                        cpuinfo = subprocess.Popen(["cat","/proc/cpuinfo"], stdout=subprocess.PIPE, bufsize=1, universal_newlines=True)
                        output = cpuinfo.communicate()[0]
                        text = output.split('\n')
                        model = re.compile("^model name.*$")
                        model_name = re.compile("(?<=: ).*$")
                        for t in text:
                            if re.match(model,t):
                                data = re.findall(model_name,t)
                                data = data[0]
                                break

                    elif re.match(loadr,line): # vrat zatez a do Accept pridej refresh
                        FoundType = True
                        typ = "zatizeni"
                        data = getcpu()
                        if len(data) == 0:
                            raise CpuError
                        refresh = re.findall(dec,line)
                        if not refresh[0]:
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

            if FoundType: # nalezeny oba, rid se podle typu Accept || nalezen jen typ, Accept automaticky na text/plain
                if ToJson: # preved na JSON, typ se nastavoval uz v analyze
                    data = "{ \"typ : " + typ + "\" , \"hodnota : " + data + "\" }\n"
                    content_type = "application/json"
                else:
                    content_type = "text/plain"

                if CustomRequest: # vytvor odpoved s refresh
                    refr_string = "Refresh: " + refresh + ";url=http://" + arg_address + ":" + str(arg_port) + "/load?refresh=" + refresh + "\n"
                else: # vytvor obycejnou odpoved request
                    refr_string = ''
                outcoming = "HTTP/1.1 200 OK\n" + refr_string + "Content-type:" + content_type + "\nContent-Length: " + str(len(data)) + "\r\n\r\n" + data + '\n'
                client.sendall(outcoming.encode()) # odeslani requestu
            else: # nebyl nalezen typ. Predpokladejme ze validnich requestu je vic nez nevalidnich
                for line in text: # zkus jestli to neni nahodou browserem, co posila dalsi specificke GET
                    if re.match(icon,line):
                        Browser = True
                if not Browser: # jednalo se opravdu o spatny typ
                    print("Nebyl nalezen typ requestu GET.")
                    break
            client.close()
        except socket.herror:
            print("Chybna adresa.")
            break
        except socket.gaierror:
            print("Chybna adresa.")
            break
        except socket.timeout:
            print("Vyprsel cas.")
            break
        except CpuError:
            print("Chyba pri volani lscpu.")
            break
        except RequestError:
            print("Request ma spatnou strukturu.")
            break
    s.close()
