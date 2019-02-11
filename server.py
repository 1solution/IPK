#!/usr/bin/env python3

import socket
import codecs
import re
import platform

# re typ pozadavku
hostname = re.compile("^GET\s+\/hostname")
cpuname = re.compile("^GET\s+\/cpu-name")
load = re.compile("^GET\s+\/load\s+")
loadr = re.compile("^GET\s+\/load\?refresh=[0-9]+\s+")
# re typ accept
tp = re.compile("^Accept:\s+text\/plain$")
aj = re.compile("^Accept:\s+application\/json$")

s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
s.bind(("merlin.fit.vutbr.cz",12345))
s.listen(1)
conn,address = s.accept() # conn = socket na druhe strane, address = tuple ve formatu addr + port druhe strany

while 1:
    data = conn.recv(1024)
    if not data:
        break
    text = data.decode().split('\r\n')
    
    FoundType = False # zatim nenalezl na zadnem radku typ requestu
    FoundAccept = False # zatim nenalezl na zadnem radku Accept type    
    for line in text:
        # validace typu requestu GET /.....
        if not FoundType:
            if re.match(line,hostname):
                FoundType = True
                data = socket.gethostname()
            elif re.match(line,cpuname):
                FoundType = True
                data = platform.processor()
            elif re.match(line,load):
                FoundType = True
                data = "25%"
            elif re.match(line,loadr):
                FoundType = True
                data="25%r"
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
    
    @author: plagtag
'''
from time import sleep
import sys

class GetCpuLoad(object):
    '''
    classdocs
    '''


    def __init__(self, percentage=True, sleeptime = 1):
        '''
        @parent class: GetCpuLoad
        @date: 04.12.2014
        @author: plagtag
        @info: 
        @param:
        @return: CPU load in percentage
        '''
        self.percentage = percentage
        self.cpustat = '/proc/stat'
        self.sep = ' ' 
        self.sleeptime = sleeptime

    def getcputime(self):
        '''
        http://stackoverflow.com/questions/23367857/accurate-calculation-of-cpu-usage-given-in-percentage-in-linux
        read in cpu information from file
        The meanings of the columns are as follows, from left to right:
            0cpuid: number of cpu
            1user: normal processes executing in user mode
            2nice: niced processes executing in user mode
            3system: processes executing in kernel mode
            4idle: twiddling thumbs
            5iowait: waiting for I/O to complete
            6irq: servicing interrupts
            7softirq: servicing softirqs

        #the formulas from htop 
             user    nice   system  idle      iowait irq   softirq  steal  guest  guest_nice
        cpu  74608   2520   24433   1117073   6176   4054  0        0      0      0


        Idle=idle+iowait
        NonIdle=user+nice+system+irq+softirq+steal
        Total=Idle+NonIdle # first line of file for all cpus

        CPU_Percentage=((Total-PrevTotal)-(Idle-PrevIdle))/(Total-PrevTotal)
        '''
        cpu_infos = {} #collect here the information
        with open(self.cpustat,'r') as f_stat:
            lines = [line.split(self.sep) for content in f_stat.readlines() for line in content.split('\n') if line.startswith('cpu')]

            #compute for every cpu
            for cpu_line in lines:
                if '' in cpu_line: cpu_line.remove('')#remove empty elements
                cpu_line = [cpu_line[0]]+[float(i) for i in cpu_line[1:]]#type casting
                cpu_id,user,nice,system,idle,iowait,irq,softrig,steal,guest,guest_nice = cpu_line

                Idle=idle+iowait
                NonIdle=user+nice+system+irq+softrig+steal

                Total=Idle+NonIdle
                #update dictionionary
                cpu_infos.update({cpu_id:{'total':Total,'idle':Idle}})
            return cpu_infos

    def getcpuload(self):
        '''
        CPU_Percentage=((Total-PrevTotal)-(Idle-PrevIdle))/(Total-PrevTotal)

        '''
        start = self.getcputime()
        #wait a second
        sleep(self.sleeptime)
        stop = self.getcputime()

        cpu_load = {}

        for cpu in start:
            Total = stop[cpu]['total']
            PrevTotal = start[cpu]['total']

            Idle = stop[cpu]['idle']
            PrevIdle = start[cpu]['idle']
            CPU_Percentage=((Total-PrevTotal)-(Idle-PrevIdle))/(Total-PrevTotal)*100
            cpu_load.update({cpu: CPU_Percentage})
        return cpu_load


if __name__=='__main__':
    x = GetCpuLoad()
    while True:
        try:
            data = x.getcpuload()
            print data
        except KeyboardInterrupt:

            sys.exit("Finished")                

