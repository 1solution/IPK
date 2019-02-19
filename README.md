# IPK

xplsek03<br>
Psano v Python3.<br>
Spusteni skriptu pomoci Makefile, make run port =[cislo_portu]. Port je treba vybrat z intervalu <1024;65535>.<br>
Kod obsahuje dostatek komentaru tam, kde tahle dokumentace nestaci!

## Jak to funguje
Pote co je uspesne vybran port, na serveru kde skript bezi probehne pokus o vytvoreni socketu na uvedenem portu. 
Skript bezi ve smycce, pokud dojde ke spojeni s klientem tak se automaticky generuji prislusne http responses s kody 
a dalsimi informacemi v hlavicce a vzdy s obsahem (at uz datovym nebo popisem chyby) v tele response.
<br>
Skript zpet odesila responses:
- 200 s Refresh / bez Refresh (kvuli automaticke obnove stranky v prohlizeci)
- 400 pokud se nejednalo o validni request
- 404 nenalezeno, pokud uzivatel posila GET ovsem s nevalidni operaci
- 405 pokud by zjisten jiny typ requestu nez GET
- 406 spatny typ Accept 
- 500 pokud by doslo k nejake chybe pri sberu informaci, napr. o zatizeni serveru pri volani subprocesu lscpu

Skript data odesila bud ve formatu JSON nebo text. Presneji, textove v pripade pokud neni uveden typ Accept, Accept */*, Accept text/* a Accept text/plain. Pomoci JSON objektu v pripade Accept application/json a application/* . V pripade ze je uveden jiny typ nez jeden z techto, server odesila response 406. Validace typu Accept probiha nasledovne: napred se postupne hleda radek s uvedenym typem Accept: text/* || text/plain a Accept: application/* || application/json a Accept: */*, pokud neni nalezen ani jeden z techto typu tak se zjistuje, jestli je typ Accept vubec uvedeny. Pokud je, odesila se response 406, pokud neni, odesila se jako content-type automaticky text/plain. Pokud je uvedeny spatne, tzn. ma spatny format (napr. Accept: stone_//table), je odeslana chyba 400: nevalidni request. K pripadnemu uvedeni content-type: application/json a odeslani JSON objektu dochazi vzdy, kdyz je jasne ze je prevod vyzadovan, a to i v pripade ze napr. odesilame response 404, v takovem pripade je response body v tomto formatu. 
<br>
Struktura requestu a hlavicek requestu je validovana pomoci regexu, neni to sice tak prehledne jako pouzit validaci 
```
if "string" is in "line":
```
ale je to spolehlivejsi zpusob kvuli slozitosti struktury requestu.

## prace s vlakny
Pokud je spojeni s klientem validni, jeho zpracovani je umisteno do nove vytvoreneho vlakna, pomoci knihovny \_thread (pro nase ucely bohate staci). socket.listen() je nastaven na 25, tj pocet moznych klientu kteri mohou cekat ve fronte na spojeni se serverem.

## Funkce pro ziskani cpu load
Funkce spusti podproces s prikazem lscpu a zkouma jeho textovy vystup pomoci regexu. Zajimaji nas radky "max MHz" a "cpu MHz", hodnoty nasledujici za nimi prevede na float a podeli, vysledek prevede na int a posle zpet jako procentualni hodnotu. Pokud dojde k chybe (neco se pokazi na urovni ziskavani dat), server odesle response 500. Podobnym zpusobem probiha ziskavani nazvu cpu.

## Refresh v prohlizeci a favicon
Obnova probiha jednoduse pridanim Refresh:X;url=url_to_refresh do hlavicky repsonse. Poznamka: prohlizec rovnez odesilal (Chrome) GET request na ziskani favicon. Tento request je ve skriptu odchycen a zamerne ignorovan, neni to mozna nejlepsi zpusob ale je nejjednodussi. Teoreticky by bylo spravnejsi odeslat prazdny soubor. 

## Odchytavani chyb a vyjimky
Odesilane responses s chybami jsou serazeny podle priority,  nejprve se testuje zda se jedna o request, pote zda se jedna o GET request, pote jestli obsahuje spravnou URI, pote jestli se je pozadovany typ Accept v poradku a pote jestli nedoslo k vnitrni chybe serveru pri sberu informaci. Vice informaci viz. kod. Vyjimky jsou: neznamy hostitel, chyba adresy a timeout, osetrene na konci kodu.
