#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
import socket,re
from Referee import *

class MrRandom():
    def __init__(self):
        #log("please input server's \"ip:port\":",end=" ")
        log("please input server's port:",end=" ")
        while True:
            iport=input()
            #m=re.fullmatch("([0-9\.]+?):([0-9]{1,5})",iport)
            m=re.fullmatch("([0-9]{1,5})",iport)
            if m:
                break
            else:
                #log("format incorrect, please input like \"127.0.0.1:12345\":",end=" ")
                log("format incorrect, please input like \"12345\":",end=" ")
        
        log("connecting to remote server...")
        self.s=socket.socket()
        #self.s.connect((m.group(1),int(m.group(2))))
        self.s.connect(("127.0.0.1",int(m.group(1))))
        log("connected to %s:%d"%self.s.getpeername())
    def recv_msg(self):
        while True:
            msg=self.s.recv(128)
            msg=msg.decode("ascii")
            if msg.startswith(SHUFFLE):
                self.recv_shuffle(msg)
            elif msg.startswith(YOURTURN):
                self.recv_turn(msg)
            elif msg.startswith(OVER):
                self.recv_over(msg)
            elif msg.startswith(FINALRESULT):
                log(msg)
                break
            else:
                log('unparsable msg "%s"'%(msg))
    def recv_shuffle(self,msg):
        cards=msg.split(",")[1:]
        self.mycards={"S":[],"H":[],"D":[],"C":[]}
        for i in cards:
            self.mycards[i[0]].append(i[1:])
        for i in self.mycards:
            if len(self.mycards[i])==0:
                self.mycards.pop(i)
        log("get cards %s"%(self.mycards))
    def recv_turn(self,msg):
        log(msg)
        msg=msg.split(",")
        if len(msg)==2:
            suit="you are the first player"
        else:
            suit=msg[2][0]

        if suit not in self.mycards:
            suit=random.choice(list(self.mycards.keys()))
        i=random.randint(0,len(self.mycards[suit])-1)
        to_send="%s,%s%s"%(CHOICE,suit,self.mycards[suit].pop(i))
        log('going to send "%s"'%(to_send))
        if len(self.mycards[suit])==0:
            self.mycards.pop(suit)
            log("suit %s is empty"%(suit))
        log("still have %s"%(self.mycards))
        self.s.send(to_send.encode("ascii"))

    def recv_over(self,msg):
        log(msg)

if __name__=="__main__":
    h=MrRandom()
    h.recv_msg()