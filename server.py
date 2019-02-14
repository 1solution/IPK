#!/usr/bin/env python3

import socket # je tu kvuli socketum
import re # je tu kvuli regexum pri zpracovani lscpu
import platform # je tu kvuli nazvu procesoru
import subprocess # je tu kvuli spusteni lscpu
import sys # je tu kvuli argv[1]
import json # prevod data na json objekt

if len(sys.argv) is not 2: # test na pocet argumentu
    print("Spatne argumenty.")
    sys.exit(1)
port = int(sys.argv[1])
if not isinstance(port,int) or port < 1024 or port > 65535: # test na port
    print("Spatne cislo portu nebo spatny format cisla portu")
    sys.exit(1)

def getcpu(): # vraci % zatizeni cpu
    curr = re.compile("^CPU MHz:\s*[0-9]+[\,,\.][0-9]+$") # dostan maximum
    max = re.compile("^CPU max MHz:\s*[0-9]+[\,,\.][0-9]+$") # dostan current stav
    fl = re.compile("\d+.?\d+") # k hledani vsech pouzitelnych cisel
    foundcurr = False
    foundmax = False
    test = subprocess.Popen(["lscpu"], stdout=subprocess.PIPE, bufsize=1, universal_newlines=True) # spust podproces
    output = test.communicate()[0]    
    text = output.split('\n')
    for t in text:
        if re.match(max,t):
            maxlist = [w.replace(',','.') for w in re.findall(fl,t)] # defaultne je tam v tom cisle carka, tak proto
            maxlist = [float(i) for i in maxlist]
            foundmax = True
        elif re.match(curr,t):
            currlist = [float(i) for i in re.findall(fl,t)]
            foundcurr = True
    if foundmax and foundcurr:
        return str(int(currlist[0]/maxlist[0]*100)) + '%'
    else:
        return '' # neco se rozbilo

## REGEX ##
# vim ze je jich hodne, ale je to jedinej rozumnej a zaroven spolehlivej zpusob jak zjistit obsah toho http header
# re typ pozadavku
isrequest = re.compile("^(GET|POST|HEAD|PUT|DELETE|CONNECT|OPTION|TRACE)\s+\/\S*\s+HTTP\/[0-9]\.[0-9]\s*$") # pokud nesedi sablone zadneho requestu, odeslat 400
isgetrequest = re.compile("^GET\s+\/\S*\s+HTTP\/[0-9]\.[0-9]\s*$") # musi sedet sablone get requestu, pokud ne odeslat 405
# jednotlive typy vyhovujici get requestu
hostname = re.compile("^GET\s+\/hostname\s+HTTP\/[0-9]\.[0-9]\s*$")
cpuname = re.compile("^GET\s+\/cpu-name\s+HTTP\/[0-9]\.[0-9]\s*$")
load = re.compile("^GET\s+\/load\s+HTTP\/[0-9]\.[0-9]\s*$")
loadr = re.compile("^GET\s+\/load\?refresh=[0-9]+\s+HTTP\/[0-9]\.[0-9]\s*$")
# re typ ignore (browser)
icon = re.compile("^GET\s+\/favicon.ico(\s+\w+.*)*")
# re typ accept
all_accept = re.compile("^Accept:\s*\*\/\*\s*$") # */*
tp_accept = re.compile("^Accept:\s*text\/(plain|\*)\s*$") # text/* || text/plain
aj_accept = re.compile("^Accept:\s*application\/(json|\*)\s*$") # application/json || application/*
some_accept = re.compile("^Accept:\s*\S+\/\S+\s*$") # jakykoliv dalsi Accept, pokud nebyly nalezeny ty predchozi
# dec cislo, vyhledani refresh rate v radku
dec = re.compile("\d+")

try:
    s = socket.socket(socket.AF_INET,socket.SOCK_STREAM) # vytvor socket
    arg_address = ''.join(socket.gethostbyname_ex(socket.gethostname())[2]) # host
    arg_port = sys.argv[1] # port
    s.bind((arg_address, int(arg_port)))
except socket.error:
    print("Chyba pri vytvareni socketu.")
else:
    s.listen(0)
    while True:
        try:
            client,address = s.accept() # client = socket na druhe strane, address = tuple ve formatu addr + port druhe strany
            data = client.recv(1024) # buffer = 1024 default
            if not data:
                client.close()
                break
            text = data.decode().split('\r\n') # obsah requestu v listu

            # validacni promenne
            IsRequest = False # jestli je to vubec request, jestli ne odesli 400
            IsGetRequest = False # jedna se o GET request, otazka je s jakou adresou
            RefreshRequest = False # soucasti response bude refresh
            ToJson = False # budeme prevadet na JSON
            FoundType = False # zatim nenalezl na zadnem radku typ requestu
            AllAccept = False # request obsahuje Accept type */*
            SomeAccept = False # je tam nejaky jiny typ Accept nez vsechny validni typy. Defaultne predpokladejme ze tam zadny Accept typ neni
            FoundAccept = False # zatim nenalezl na zadnem radku Accept type
            CpuError = False # odeslat 500, vnitrni chyba serveru pri zpracovani cpuinfo
            Browser = False # browser request: favicon etc.

            for line in text: #validace requestu
                if re.match(isrequest,line): # validace jestli sae jedna o request
                    IsRequest = True # jedna se o request
                    if re.match(isgetrequest,line):
                        IsGetRequest = True # jedna se o request GET
                if not FoundAccept:  # validace header requestu, konkretne Accept: */*
                    if re.match(aj_accept, line):
                        FoundAccept = True
                        ToJson = True
                    elif re.match(tp_accept, line):
                        FoundAccept = True
                    elif re.match(all_accept, line):
                        FoundAccept = True
                        AllAccept = True
            if not FoundAccept: # pokus o nalezeni vubec nejakeho Accept typu
                for line in text:
                    if re.match(some_accept, line):
                        SomeAccept = True
                        break
            if IsRequest and IsGetRequest: # jedna se o GET request. aby se netestovalo zbytecne na neco co neni request
                for line in text:
                    if re.match(icon, line):
                        Browser = True
                    if not FoundType: # validace typu requestu GET /.....
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
                            if len(data) == 0: # budes vracet 500
                                FoundType = False
                                CpuError = True
                            else:
                                refresh = re.findall(dec,line)
                                if not refresh[0]: # request ma spatnou strukturu, 400
                                    FoundType = False
                                else:
                                    refresh = refresh[0] # vyber refresh rate
                                    RefreshRequest = True # budes vytvaret vlastni textovy request k odeslani
                        elif re.match(load,line): # vrat zatez
                            FoundType = True
                            typ = "zatizeni"
                            data = getcpu()
                            if len(data) == 0: # budes vracet 500
                                FoundType = False
                                CpuError = True

            ##### processing vypisu: START #####

            # odchyceni chyb
            if IsRequest:
                if IsGetRequest:
                    if not FoundType: # nebyl nalezen typ, ale budes posilat 404 (text nebo JSON)
                        data = "Obsah nenalezen"
                        typ = "Chyba"
                    elif SomeAccept: # spatny typ Accept, odesilas 406
                        typ = "Chyba"
                        data = "spatny Accept typ obsahu"
                    elif CpuError: # Cpu error, nahrad typ chyby, odesilas 500
                        typ = "Chyba"
                        data = "Vnitrni chyba serveru"
                else: # je to request ale neni to GET, odesilas 405
                    typ = "Chyba"
                    data = "Nespravna metoda"
            else: # neni to request, posli 400
                typ = "Chyba"
                data = "Spatna syntaxe requestu"

            # prevod dat na json tam, kde ma byt json
            if ToJson: # nalezen typ json
                data = "{ \"typ : " + typ + "\" , \"hodnota : " + data + "\" }"
                data = json.dumps(data)
                content_type = "application/json"
                str_length = '' # delku u JSONu neudavat
            else: # nalezen typ text nebo nebyl nalezen, takze posilam text. Nebo pripad kdy byl nalezen jiny typ nez Json
                content_type = "text/plain"
                data = data + '\n' # pridej novy radek kvuli terminalu
                str_length = "\nContent-Length: " + str(len(data)) # delka dat u text/plain

            ##### processing vypisu: FAKTICKE ODESLANI DAT #####

            if not Browser: # nebylo to browserem (favicon..)
                if FoundType: # typ byl nalezen
                    if SomeAccept:  # odesilas 406, spatny typ Accept
                        outcoming = "HTTP/1.1 406 Not Acceptable\nContent-type:" + content_type + str_length + "\r\n\r\n" + data + '\n'
                    elif CpuError:  # Cpu error, odesilas 500
                        outcoming = "HTTP/1.1 500 Internal Server Error\nContent-type:" + content_type + str_length + "\r\n\r\n" + data + '\n'
                    else: # validni request, odesli 200
                        if RefreshRequest: # vytvor odpoved s refresh
                            refr_string = "Refresh: " + refresh + ";url=http://" + arg_address + ":" + str(arg_port) + "/load?refresh=" + refresh + "\n"
                        else: # vytvor obyc-ejnou odpoved
                            refr_string = ''
                        outcoming = "HTTP/1.1 200 OK\n" + refr_string + "Content-type:" + content_type + str_length + "\r\n\r\n" + data + '\n'
                else: # typ nenalezen, jedna se o nevalidni request a resi se chyby
                    if IsRequest:
                        if IsGetRequest:
                            if not FoundType:  # nebyl nalezen typ, ale budes posilat 404 (text nebo JSON)
                                outcoming = "HTTP/1.1 404 Not Found\nContent-type:" + content_type + str_length + "\r\n\r\n" + data + '\n'
                        else:  # je to request ale neni to GET, odesilas 405
                            outcoming = "HTTP/1.1 405 Method Not Allowed\nContent-type:" + content_type + str_length + "\r\n\r\n" + data + '\n'
                    else:  # neni to request, posli 400
                        outcoming = "HTTP/1.1 400 Bad Request\nContent-type:" + content_type + str_length + "\r\n\r\n" + data + '\n'

                client.sendall(outcoming.encode()) # odeslani requestu
            client.close()

        # osetri vyjimky, chyba host, chyba adresy a timeout pri vytvareni
        except socket.herror as e:
            print(e)
        except socket.gaierror as e:
            print(e)
        except socket.timeout as e:
            print(e)
    s.close() # uzavri spojeni, porad jsme ale ve smycce