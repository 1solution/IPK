# IPK

xplsek03<br>
Psano v Python3.<br>
Spusteni skriptu pomoci Makefile, make run port =[cislo_portu]. Port je treba vybrat z intervalu <1024;65535>.<br>
Kod obsahuje dostatek komentaru tam, kde tahle dokumentace nestaci.

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

Skript data odesila bud ve formatu JSON nebo text. Presneji, textove v pripade pokud neni uveden typ Accept, Accept */* ,Accept text/* a Accept text/plain.
JSONem v pripade Accept application/json a application/*. V pripade ze je uveden jiny typ nez jeden z techto, server odesila response 406.
