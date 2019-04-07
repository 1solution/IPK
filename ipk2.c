#include <stdio.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <unistd.h> // sleep()
#include <pthread.h>
#include <getopt.h>
#include <string.h>
#include <netinet/ip.h>
#include <netinet/tcp.h>
#define PCKT_LEN 8192

#define PORT_RANGE_START 50000
#define PORT_RANGE_END 60000

int checkArg(char *argument) {
    int range = 0; // -
    int col = 0; // ,
    for(int i = 0; i < strlen(argument); i++) {
        if(isdigit(argument[i]))
            continue;
        else if(argument[i] == '-')
            range++;
        else if(argument[i] == ',')
            col++;
        else
            return 0;       
    } 
    if(range > 1 || !isdigit(argument[strlen(argument)]) || (range > 0 && col > 0))
        return 0;
    
    if(range > 1) {
		return 1; // je tam jedna pomlcka		
	}
	else if(col > 1)
		return 2; // jsou tam carky
	else
		return 3; // jsou tam jen cisla
}

int getCharCount(char *str, char z) {
    int c = 0;
    for(int i = 0; i < strlen(str); i++) {
        if(!strcmp(str[i],z))
            c++;
    }
    return c;
}

int processArgument(int ret, int *xu_arr) { // BUG zkontrolu jaby tam nebyly nahodou dva stejne porty
    if(ret == 1) { // hledas -
        xu_arr = malloc(sizeof(int)*2);
        if(xu_arr == NULL)
            return 2; // malloc error
        int i = 0;
        char *p = strtok(pu, "-");
        while (p != NULL) {
            xu_arr[i++] = (int)strtol(p);
            p = strtok(NULL, "-");
        }
    }
    else if(ret == 2) { // hledas ,
        int l = getCharCount(pu,',');
        xu_arr = malloc(sizeof(int) * (l+1));
        if(xu_arr == NULL)
            return 2; // malloc error
        int i = 0;
        char *p = strtok(pu, ",");
        while (p != NULL) {
            xu_arr[i++] = (int)strtol(p);
            p = strtok(NULL, ",");
        }
    }
    else { // vkladas cely cislo do pole
        xu_arr = malloc(sizeof(int));
        if(xu_arr == NULL)
            return 2; // malloc error
        xu_arr[0] = (int)strtol(pu);
    }

    int size = sizeof(xu_arr)/sizeof(int);
    for(int i = 0; i < size; i++) {
        if(xu_arr[i] > 65535 || xu_arr[i] < 0)
            return 1; // chyba rozsahu int
    }
    return 0;
}

int main(char **argv, int argc) {

	// promenne pro vlaidaci argumentu
    char *pu = "";
    char *pt = "";
    char *host = "";
    bool foundPu = false;
    bool foundPt = false;
    bool foundHost = false;
    int puc = 0;
    int ptc = 0;
    int hc = 0;
    
    // pole pro seznam 
    int *pu_arr;
    int *pt_arr;
    
    // kontrola poctu argumentu
    if(argc != 6)
        goto wrong_arguments;

    // nalezeni argumentu
    for(int i = 1; i < argc; i++) {
        if(foundPu) {
            pu = argv[i];
            puc++;
            continue;
        }
        if(foundPt) {
            pt = argv[i];
            ptc++;
            continue;
        }
        if(argv[i] == "-pu") {
            if(i == argc-1)
                goto wrong_arguments;
            else {
                foundPu = true;
            }
        }
        if(argv[i] == "-pt") {
            if(i == argc-1)
                goto wrong_arguments;
            else
                foundPt = true;
        }
        else {
            host = argv[i];
            foundHost = true;
            hc++;
        }
    }

    // validace nalezenych argumentu
    if(puc != 1 || ptc != 1 || hc != 1)
        goto wrong_arguments;

    // co jsou oba argumenty zac, jestli range, vycet..
    int ret_pu = checkArg(puc);
    int ret_pt = checkArg(ptc);
    if(!ret_pu || !ret_pt)
        goto wrong_arguments;

    // obsah ret_pu || ret_pt:
	// 0 = chyba
    // 1 = jedna pomlcka
    // 2 = nejake carky
    // 3 = jen cisla

    int ret_pu2 = processArgument(ret_pu,pu_arr);
    int ret_pt2 = processArgument(ret_pt,pt_arr);   
    if(ret_pu2 == 2 || ret_pt2 == 2)
        goto malloc_error;
    if(ret_pu2 == 1 || ret_pt2 == 1)
        goto range_error;

	int pu_arr_size = sizeof(pu_arr) / sizeof(int);
	int pt_arr_size = sizeof(pt_arr) / sizeof(int);
	
    // ted jsou v pu_arr a pt_arr jednotlive porty, a v ret_pu a ret_pt je typ pole (1'-' 2',' 3'int'), pu_arr_size, pt_arr_size jsou velikosti
    
    char *addresses[10] = {"192.168.1.5","192.168.1.6",
                        "192.168.1.50","192.168.1.53",
                        "192.168.1.67","192.168.1.46",
                        "192.168.1.23","192.168.1.105",
                        "192.168.1.25","192.168.1.77"
    }; // napln pole ip adresama, zjisti ktere se daji pouzit uz na zacatku + vytvor ARP zaznam na tomhle hostovi
    address_count = 10; // pocet ip adres

    int client = socket(PF_INET, SOCK_RAW, IPPROTO_TCP); // jeden socket pro praci vice vlaken
    if (client < 0) 
        fprintf(STDERR,"Chyba pri vytvareni socketu.\n"); 

    // tady spust sniffer vlakno

    // target_address
    // target_port

    for(int spoofed_port = PORT_RANGE_START; spoofed_port < PORT_RANGE_END; spoofed_port++) {

        send_syn(target_port, target_address, addresses, address_count);

    }
    
    label wrong_arguments:
        fprintf(STDERR,"Spatne zadane argumenty programu.\n");
        return 1;

    label malloc_error:
        fprintf(STDERR,"Chyba pri alokaci.\n");
        return 1;

    label range_error:
        fprintf(STDERR,"Spatny rozsah cisla portu (0 - 65535).\n");
        return 1;

}
