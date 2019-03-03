#!/usr/bin/env python3

import socket # je tu kvuli socketum
import re # je tu kvuli regexum pri zpracovani lscpu
import platform # je tu kvuli nazvu procesoru
import subprocess # je tu kvuli spusteni lscpu
import sys # je tu kvuli argv[1]
import json # prevod data na json objekt
import _thread # kvuli vlaknum
from email.utils import formatdate # kvuli casu a datu v http response

max_requests = 50 # maximalni pocet requestu pres jeden socket

if len(sys.argv) is not 2: # test na pocet argumentu
    print("Spatne argumenty.")
    sys.exit(1)
port = int(sys.argv[1])
if not isinstance(port,int) or port < 1024 or port > 65535: # test na port
    print("Spatne cislo portu nebo spatny format cisla portu")
    sys.exit(1)

def keep(s): # nastaveni TCP keepalive
    s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1) # nastav keepalive ON
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 5) # jak dlouho musi byt v necinnosti aby se aktivoval ping
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 2) # interval mezi pingy
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5) # pocet neuspesnych pingu nez se spojeni uzavre

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
        return '' # neco se rozbilo, 500

def cut_body(text): # dostan ven z requestu telo a prazdny radek
    text2 = []
    for line in text:
        if line == '':
            return text2
        text2.append(line)
    return text2
        
# zpracovani klienta - START ##
def processing(client,s,arg_port,arg_address, max_requests): # vlakno s klientem
            
    for i in range(max_requests):
        data = client.recv(1024) # buffer = 1024 default
        if not data:  # neprisla zadna data, socket je zavreny
            break    
           
        if data:
            text = data.decode().split('\r\n')  # obsah requestu v listu
            text = cut_body(text) # vyhod ven telo requestu

            # validacni promenne
            IsRequest = False  # jestli je to vubec request, jestli ne odesli 400
            IsGetRequest = False  # jedna se o GET request, otazka je s jakou adresou
            RefreshRequest = False  # soucasti response bude refresh
            ToJson = False  # budeme prevadet na JSON
            FoundType = False  # zatim nenalezl na zadnem radku typ requestu
            SomeAccept = False  # je tam nejaky jiny typ Accept nez vsechny validni typy. Defaultne predpokladejme ze tam zadny Accept typ neni
            FoundAccept = False  # zatim nenalezl na zadnem radku Accept type
            CpuError = False  # odeslat 500, vnitrni chyba serveru pri zpracovani cpuinfo
            CpuNameError = False  # odeslat 500, vnitrni chyba serveru pri zpracovani cpu name
            Browser = False  # browser request: favicon etc.
            Connection = True # jedna se o validni radek s connection
            Keepalive = False # defaultne je Connection: closed

            for line in text:  # validace requestu
                if re.match(isrequest, line):  # validace jestli se jedna o request
                    IsRequest = True # jedna se o request
                    if re.match(ver_10, line):
                        version = "HTTP/1.0"
                        Keepalive = False # defaultni connection: close u verze http 1.0
                    elif re.match(ver_11, line):
                        version = "HTTP/1.1"
                        Keepalive = True # defualtni conenction: keep alive u verze http 1.1
                    if re.match(isgetrequest, line):
                        IsGetRequest = True  # jedna se o request GET
                if not FoundAccept:  # validace header requestu, konkretne Accept: */*
                    if re.match(aj_accept, line):
                        FoundAccept = True
                        ToJson = True
                    elif re.match(tp_accept, line):
                        FoundAccept = True
                    elif re.match(all_accept, line):
                        FoundAccept = True
            if not FoundAccept:  # pokus o nalezeni vubec nejakeho Accept typu
                for line in text:
                    if "Accept:" in line or "accept:" in line:  # naslo to radek ve kterem je "Accept"
                        if re.match(some_accept, line):  # ten radek odpovida obecnemu typu accept
                            SomeAccept = True
                            break
                        else:  # accept ma nevalidni format, tzn spatny request. Odesli 400
                            IsRequest = False
            if IsRequest and IsGetRequest:  # jedna se o GET request. aby se netestovalo zbytecne na neco co neni request
                for line in text:
                    if "Connection:" in line or "connection:" in line: # Pokud se vyskytuje radek s connection
                        if re.match(connection, line): # naslo to radek s connection
                            if re.match(keepalive, line): # Keep alive connection, pokud je explicitne napsano ze ma byt keep-alive
                                Keepalive = True
                            elif re.match(keepclose, line):
                                Keepalive = False
                        else: # nevalidni radek s connection
                            Connection = False

                    if re.match(icon, line):
                        Browser = True
                    if not FoundType:  # validace typu requestu GET /.....
                        if re.match(hostname, line):  # vrat hostname (= hostname.domainname)
                            FoundType = True
                            typ = "hostname"
                            data = socket.gethostname()
                        elif re.match(cpuname, line):  # vrat nazev cpu
                            FoundType = True
                            typ = "cpu"
                            cpuinfo = subprocess.Popen(["cat", "/proc/cpuinfo"], stdout=subprocess.PIPE, bufsize=1,
                                                       universal_newlines=True)
                            output = cpuinfo.communicate()[0]
                            text = output.split('\n')
                            model = re.compile("^model name.*$")
                            model_name = re.compile("(?<=: ).*$")
                            for t in text:
                                if re.match(model, t):
                                    FoundCpuLine = True  # naslo to radek s modelem
                                    data = re.findall(model_name, t)
                                    if data[0]:
                                        data = data[0]
                                    else:
                                        CpuNameError = True  # chybi nazev modelu
                                    break
                            if not FoundCpuLine:  # nebyl nalezen radek s modelem cpu
                                CpuNameError = True
                        elif re.match(loadr, line):  # vrat zatez a do Accept pridej refresh
                            FoundType = True
                            typ = "zatizeni"
                            data = getcpu()
                            if len(data) == 0:  # budes vracet 500
                                CpuError = True
                            else:
                                refresh = re.findall(dec, line)
                                if not refresh[0]:  # request ma spatnou strukturu, 404
                                    FoundType = False
                                else:
                                    refresh = refresh[0]  # vyber refresh rate
                                    RefreshRequest = True  # budes vytvaret vlastni textovy request k odeslani
                        elif re.match(load, line):  # vrat zatez
                            FoundType = True
                            typ = "zatizeni"
                            data = getcpu()
                            if len(data) == 0:  # budes vracet 500
                                CpuError = True

            ## zpracovani keep-alive na strane serveru. Funguje pouze pro linux, pro W a osx ne
            if Keepalive: # pokud je pozadavek na keep-alive nebo HTTP 1.1 automaticky
                if i == max_requests-1: # posledni mozny zpracovavany request pres tento port, max = 50
                    conn = "Connection: close\n Date: " + formatdate(timeval=None, localtime=False, usegmt=True) + "\n"
                else:
                    keep(s) # nastav parametry keep alive v linuxu
                    conn = "Keep-Alive: timeout=15, max=50\nDate: "  + formatdate(timeval=None, localtime=False, usegmt=True) + "\n" # timeout = 5s + 10s max = max pocet spojeni pres socket
                    # Connection keep alive je pro http 1.1 defaultni, nemusi tu tedy byt
            else:
                conn = "Connection: close\n Date: " + formatdate(timeval=None, localtime=False, usegmt=True) + "\n"
                
            ##### processing vypisu: START #####
            # odchyceni chyb
            if IsRequest:
                if IsGetRequest:
                    if not FoundType:  # nebyl nalezen typ, ale budes posilat 404 (text nebo JSON)
                        data = "Obsah nenalezen"
                        typ = "Chyba"
                    elif not Connection: # spatny typ connection, odesilas 400
                        data = "Spatny typ Connection"
                        typ = "Chyba"
                    elif SomeAccept:  # spatny typ Accept, odesilas 406
                        typ = "Chyba"
                        data = "spatny Accept typ obsahu"
                    elif CpuError or CpuNameError:  # Cpu error || Cpu Name Error, nahrad typ chyby, odesilas 500
                        typ = "Chyba"
                        data = "Vnitrni chyba serveru"
                else:  # je to request ale neni to GET, odesilas 405
                    typ = "Chyba"
                    data = "Nespravna metoda"
            else:  # neni to request, posli 400
                typ = "Chyba"
                data = "Spatna syntaxe requestu"

            # prevod dat na json tam, kde ma byt json
            if ToJson:  # nalezen typ json
                data = "{ \"typ : " + typ + "\" , \"hodnota : " + data + "\" }"
                data = json.dumps(data)
                content_type = "application/json"
                str_length = "\nContent-Length: " + str(len(data.encode("utf-8")))
            else:  # nalezen typ text nebo nebyl nalezen, takze posilam text. Nebo pripad kdy byl nalezen jiny typ nez Json
                content_type = "text/plain"
                str_length = "\nContent-Length: " + str(len(data))  # delka dat u text/plain

            ##### processing vypisu: FAKTICKE ODESLANI DAT #####

            if not Browser:  # nebylo to browserem (favicon..)
                if FoundType:  # typ byl nalezen
                    if SomeAccept:  # odesilas 406, spatny typ Accept
                        outcoming = version + " 406 Not Acceptable\n" + conn + "Content-type:" + content_type + str_length + "\r\n\r\n" + data + '\n'
                    elif CpuError or CpuNameError:  # Cpu error load nebo name, odesilas 500
                        outcoming = version + " 500 Internal Server Error\n" + conn + "Content-type:" + content_type + str_length + "\r\n\r\n" + data + '\n'
                    else:  # validni request, odesli 200
                        if RefreshRequest:  # vytvor odpoved s refresh
                            refr_string = "Refresh: " + refresh + ";url=http://" + arg_address + ":" + str(
                                arg_port) + "/load?refresh=" + refresh + "\n"
                        else:  # vytvor obyc-ejnou odpoved
                            refr_string = ''
                        outcoming = version + " 200 OK\n" + refr_string + conn + "Content-type:" + content_type + str_length + "\r\n\r\n" + data + '\n'
                else:  # typ nenalezen, jedna se o nevalidni request a resi se chyby
                    if IsRequest:
                        if IsGetRequest:
                            if not FoundType:  # nebyl nalezen typ, ale budes posilat 404 (text nebo JSON)
                                outcoming = version + " 404 Not Found\n" + conn + "Content-type:" + content_type + str_length + "\r\n\r\n" + data + '\n'
                            if not Connection: # spatny radek s Connection, budes posilat 400
                                outcoming = version + " 400 Bad Request\n" + conn + "Content-type:" + content_type + str_length + "\r\n\r\n" + data + '\n'
                        else:  # je to request ale neni to GET, odesilas 405
                            outcoming = version + " 405 Method Not Allowed\n" + conn + "Content-type:" + content_type + str_length + "\r\n\r\n" + data + '\n'
                    else:  # neni to request, posli 400
                        outcoming = version + " 400 Bad Request\n" + conn + "Content-type:" + content_type + str_length + "\r\n\r\n" + data + '\n'
                client.sendall(outcoming.encode())  # odeslani requestu
    client.close() # uzavreni socketu na strane klienta
## zpracovani klienta - END ##

## REGEX ##
# keep alive connection
connection = re.compile("^[Cc]onnection:\s*([Kk]eep-alive|[Cc]lose)$") # jestli se jedna o validni radek s conenction
keepalive = re.compile("^[Cc]onnection:\s*[Kk]eep-[Aa]live$")
keepclose = re.compile("^[Cc]onnection:\s*[Cc]lose$")
# re typ pozadavku
isrequest = re.compile("^(GET|POST|HEAD|PUT|DELETE|CONNECT|OPTION|TRACE) \/\S* HTTP\/(1\.0|1\.1)$") # pokud nesedi sablone zadneho requestu, odeslat 400
isgetrequest = re.compile("^GET \/\S* HTTP\/(1\.0|1\.1)$") # musi sedet sablone get requestu, pokud ne odeslat 405
# jednotlive typy vyhovujici get requestu
hostname = re.compile("^GET \/hostname HTTP\/(1\.0|1\.1)$")
cpuname = re.compile("^GET \/cpu-name HTTP\/(1\.0|1\.1)$")
load = re.compile("^GET \/load HTTP\/(1\.0|1\.1)$")
loadr = re.compile("^GET \/load\?refresh=[123456789][0-9]* HTTP\/(1\.0|1\.1)$")
# re typ ignore (browser)
icon = re.compile("^GET \/favicon.ico HTTP\/(1\.0|1\.1)$")
# re typ accept
all_accept = re.compile("^[Aa]ccept:\s*\S*\*\/\*\S*$") # ..*/*..
tp_accept = re.compile("^[Aa]ccept:\s*\S*[Tt]ext\/([Pp]lain|\*)\S*$") # text/* || text/plain
aj_accept = re.compile("^[Aa]ccept:\s*\S*[Aa]pplication\/([Jj]son|\*)\S*$") # ..application/json || application/*..
some_accept = re.compile("^[Aa]ccept:\s*\S+\/\S+$") # jakykoliv dalsi Accept, pokud nebyly nalezeny ty predchozi
# dec cislo, vyhledani refresh rate v radku
dec = re.compile("\d+")
# ruzne podporovane verze HTTP
ver_10 = re.compile("^GET \/\S* HTTP\/1\.0$")
ver_11 = re.compile("^GET \/\S* HTTP\/1\.1$")

try:
    s = socket.socket(socket.AF_INET,socket.SOCK_STREAM) # vytvor socket
    s.settimeout(15.0) # nastav timeout server socketu
    #arg_address = ''.join(socket.gethostbyname_ex(socket.gethostname())[2]) # host
    arg_address = socket.gethostname()     
    arg_port = sys.argv[1] # port
    s.bind(("127.0.0.1", int(arg_port)))
except socket.error:
    print("Chyba pri vytvareni socketu.")
else:
    s.listen(25) # kolik klientu muze maximalne cekat ve fronte na pripojeni, nez je zacne server odmitat
    while True:
        try:
            client,address = s.accept() # client = socket na druhe strane, address = tuple ve formatu addr + port druhe strany
            try:
                _thread.start_new_thread(processing,(client,s,arg_port,arg_address,max_requests,)) # zaloz nove vlakno s aktualnim klientem
            except socket.timeout as e: # timeout error
                print(e)
            except socket.herror as e: # chyba host
                print(e)
            except socket.gaierror as e: # jina chyba
                print(e)
            except:
                print("Nelze vytvorit vlakno.")
        # osetri vyjimky
        except socket.timeout as e: # timeout error
            continue
        except:
            break
    try:
        s.close() # uzavri socket na strane serveru
    except:
        pass
