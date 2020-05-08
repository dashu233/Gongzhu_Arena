import requests
import time, sys, traceback, math, numpy, signal,json, random,copy
import threading
import urllib.request
import os

from http.client import HTTPConnection

sleep_time = 0.2

LOGLEVEL = {0: "DEBUG", 1: "INFO", 2: "WARN", 3: "ERR", 4: "FATAL"}
LOGFILE = sys.argv[0].split(".")
LOGFILE[-1] = "log"
LOGFILE = ".".join(LOGFILE)


def log(msg, l=1, end="\n", logfile=None, fileonly=False):
    st = traceback.extract_stack()[-2]
    lstr = LOGLEVEL[l]
    now_str = "%s %03d" % (time.strftime("%y/%m/%d %H:%M:%S", time.localtime()), math.modf(time.time())[0] * 1000)
    if l < 3:
        tempstr = "%s [%s,%s:%d] %s%s" % (now_str, lstr, st.name, st.lineno, str(msg), end)
    else:
        tempstr = "%s [%s,%s:%d] %s:\n%s%s" % (
        now_str, lstr, st.name, st.lineno, str(msg), traceback.format_exc(limit=5), end)
    if not fileonly:
        print(tempstr, end="")
    if l >= 1 or fileonly:
        if logfile == None:
            logfile = LOGFILE
        with open(logfile, "a") as f:
            f.write(tempstr)


class Client:
    def login(self,name,pwd,url,rob):
        '''
        *{"command": "user_login", "user": "name", "user_pwd": "pwd", "robot": true}
        '''
        self.name = name
        self.pwd = pwd
        self.url = url
        self.rob = rob
        conn = HTTPConnection(url)
        postdata = {"command": "user_login", "user":name,\
                        "user_pwd":pwd, "rob":rob}
        data = json.dumps(postdata).encode()
        headers = {'Content-type': "text/plain"}
        conn.request("GET", '/index.html', data, headers)
        rep = conn.getresponse().read().decode()
        rep = json.loads(rep)
        #print(rep)
        return rep

    def create_room(self,roomid,ins):
        conn = HTTPConnection(self.url)
        postdata = {"command": "find_room", "roomid": roomid, \
                        "instruction": ins}
        data = json.dumps(postdata).encode()
        headers = {'Content-type': "text/plain"}
        conn.request("GET", '/index.html', data, headers)
        rep = conn.getresponse().read().decode()
        rep = json.loads(rep)
        #print(rep)
        return rep

    def sit_down(self,id,pl):
        conn = HTTPConnection(self.url)
        postdata = {"command": "sit_down", "user":self.name,"roomid": id, \
                    "place": pl}
        data = json.dumps(postdata).encode()
        headers = {'Content-type': "text/plain"}
        conn.request("GET", '/index.html', data, headers)
        rep = conn.getresponse().read().decode()
        rep = json.loads(rep)

        #print(rep)
        return rep

    def ask_start(self):
        conn = HTTPConnection(self.url)
        postdata = {"command": "ask_start", "user": self.name}
        data = json.dumps(postdata).encode()
        headers = {'Content-type': "text/plain"}
        conn.request("GET", '/index.html', data, headers)
        rep = conn.getresponse().read().decode()
        rep = json.loads(rep)

        #print(rep)
        return rep

    def update_card(self):
        conn = HTTPConnection(self.url)
        postdata = {"command": "update_card", "user": self.name}
        data = json.dumps(postdata).encode()
        headers = {'Content-type': "text/plain"}
        conn.request("GET", '/index.html', data, headers)
        rep = conn.getresponse().read().decode()
        rep = json.loads(rep)

        #print(rep)
        return rep

    def ask_trick_end(self):
        conn = HTTPConnection(self.url)
        postdata = {"command": "ask_trick_end", "user": self.name}
        data = json.dumps(postdata).encode()
        headers = {'Content-type': "text/plain"}
        conn.request("GET", '/index.html', data, headers)
        rep = conn.getresponse().read().decode()
        rep = json.loads(rep)

        #print(rep)
        return rep

    def play_a_card(self,card):

        conn = HTTPConnection(self.url)
        postdata = {"command": "play_a_card", "user":self.name, "card":card}
        data = json.dumps(postdata).encode()
        headers = {'Content-type': "text/plain"}
        conn.request("GET", '/index.html', data, headers)
        rep = conn.getresponse().read().decode()
        rep = json.loads(rep)

        #print(rep)
        return rep

    def trick_end_get(self):
        conn = HTTPConnection(self.url)
        postdata = {"command": "trick_end_get", "user": self.name}
        data = json.dumps(postdata).encode()
        headers = {'Content-type': "text/plain"}
        conn.request("GET", '/index.html', data, headers)
        rep = conn.getresponse().read().decode()
        rep = json.loads(rep)

        #print(rep)
        return rep


    def leave(self):
        conn = HTTPConnection(self.url)
        postdata = {"command": "leave", "user": self.name}
        data = json.dumps(postdata).encode()
        headers = {'Content-type': "text/plain"}
        conn.request("GET", '/index.html', data, headers)
        rep = conn.getresponse().read().decode()
        rep = json.loads(rep)

        #print(rep)
        return rep

    def recive_information(self):
        pass
    def other_player_card(self):
        pass
    def join(self):
        pass


class Agent:
    def __init__(self,name,pwd,rob = False):
        self.client = Client()
        self.name = name
        self.pwd = pwd
        self.rob = rob

        self.place = 0
        self.cards = []  # cards in hand
        self.history = [[]]
        self.final_score = 0
        # trick,[first_one_place, first_card,second_card,...]
        # 13*5 or 18*4
        self.cards_on_table = []  # [first_one_place, first_card,second_card,...]
        self.suit = ''

        pass

    def login(self,url):
        rep = self.client.login(self.name, self.pwd, url, self.rob)
        cmd = rep["command"]
        if cmd == "login_reply":
            return
        if cmd == "error":
            log("login error:" + rep["details"])
            return False

    def create_room(self,roomid,ins):
        rep = self.client.create_room(roomid, ins)
        cmd = rep["command"]

        if cmd == "error":
            log("create_room error:" + rep["detail"])
            return False

        return True

    def sit_down(self,id,pl):
        rep = self.client.sit_down(id, pl)
        cmd = rep["command"]

        if cmd == "error":
            log("sit_down error:" + rep["detail"])
            return False
        else:
            self.place = pl
            self.final_score = 0
            return True

    def waiting_for_start(self):
        while True:
            rep = self.client.ask_start()

            if rep["command"] == "error":
                log("waiting_for_start error:" + rep["detail"])
                return False
            if rep["command"] == "start_reply_start":
                self.cards = rep["cards"]
                self.initial_cards = rep["cards"]
                self.room_mate = copy.copy(rep["players"])
                self.suit = ''
                self.now_player = rep["start_place"]
                return
            self.room_mate = copy.copy(rep["players"])
            time.sleep(sleep_time)


    def updating(self):
        while True:
            rep = self.client.update_card()
            if rep["command"] == "error":
                log("updating error:" + rep["detail"])
            if rep["command"] == "update_card_reply":
                self.cards_on_table = [rep["start_place"]]
                self.cards_on_table = self.cards_on_table.append(rep["cards_on_table"])
                self.suit = rep["suit"]
                self.now_player = rep["now_player"]
                if self.now_player == self.place:
                    return True
            if rep["command"] == "update_card_reply_game_end":
                self.final_score = rep["score"][self.place]
                self.final_collect = rep["collect"][self.place]
                return "game_end"
            time.sleep(sleep_time)

    def keep_on(self):
        return False

    def pick_a_card(self):
        #self.cards
        return self.cards[0]

    def play_a_card(self):
        card = self.pick_a_card()
        print(self.name + " play a card:" + card)
        rep = self.client.play_a_card(card)
        if rep["command"] == "play_a_card_reply":
            self.cards.remove(card)
            return True
        else:
            log("ask_trick_end error:" + rep["detail"])
            return False

    def ask_trick_end(self):
        #print(self.name + "ask trick end")
        while True:
            rep = self.client.ask_trick_end()
            if rep["command"] == "ask_trick_end_reply":
                self.cards_on_table = rep["cards_on_table"]
                #self.cards_on_table = self.cards_on_table.append(rep["cards_on_table"])
                self.history.append(self.cards_on_table)

                self.winner = rep["winner"]
                self.get_reward()

                return

            if rep["command"] == "trick_end_reply_waiting":
                time.sleep(sleep_time)
                continue

            if rep["command"] == "error":
                log("ask_trick_end error:" + rep["detail"])

    def trick_end_get(self):
        while True:
            time.sleep(sleep_time)
            rep = self.client.trick_end_get()

            if rep["command"] == "trick_end_get_reply":
                break

            if rep["command"] == "trick_end_get_reply_waiting":
                continue

            if rep["command"] == "error":
                log("ask_trick_end error:" + rep["detail"])


    def get_reward(self):
        pass


import socket, re
from Referee import *


class MrRandom(Agent):

    def pick_a_card(self):
        self.mycards = {"S": [], "H": [], "D": [], "C": [],"J":[]}
        for i in self.cards:
            self.mycards[i[0]].append(i[1:])
        suit = self.suit

        while True:
            if suit == 'H':
                if suit not in self.mycards:
                    if 'J' not in self.mycards:
                        suit = random.choice(list(self.mycards.keys()))
                    else:
                        suit = 'J'
            elif suit == 'J':
                if suit not in self.mycards:
                    if 'H' not in self.mycards:
                        suit = random.choice(list(self.mycards.keys()))
                    else:
                        suit = 'H'

            else:
                if suit not in self.mycards:
                    suit = random.choice(list(self.mycards.keys()))

            if len(self.mycards[suit]) == 0:
                self.mycards.pop(suit)
                continue
            else:
                break

        i = random.randint(0, len(self.mycards[suit]) - 1)

        return suit + self.mycards[suit][i]


class Agent_Thread(threading.Thread):
    def __init__(self,ag,name, pwd, url, rob = True):
        threading.Thread.__init__(self)
        self.url = url
        self.agent = ag(name,pwd,rob)


    def run(self):

        self.agent.login(self.url)
        if self.agent.name == "shiju1":
            self.agent.create_room(11, 'T')
            print("created")
        else:
            while not self.agent.create_room(11, 'F'):
                pass

        while True:
            if self.agent.sit_down(11, ord(self.agent.name[5]) - ord('1')):
                break
            else:
                time.sleep(sleep_time)

        while True:
            self.agent.waiting_for_start()
            trick = 0
            while True:
                trick += 1
                print(self.name + "trick: %d"%trick)
                end = self.agent.updating()
                if end == "game_end":
                    break
                elif end:
                    self.agent.play_a_card()
                    self.agent.ask_trick_end()
                    self.agent.trick_end_get()

            print(self.agent.name + " final score = %d"% self.agent.final_score)
            if self.agent.keep_on():
                continue
            else:
                break

        if self.agent.name == "shiju1":
            for i in self.agent.history:
                print(i)

        print("over:"+self.agent.name)


def test_post():
    shiju1 = Agent_Thread(MrRandom,"shiju1","23333","0.0.0.0:20000",False)
    shiju2 = Agent_Thread(MrRandom,"shiju2", "23333", "0.0.0.0:20000", False)
    shiju3 = Agent_Thread(MrRandom,"shiju3", "23333", "0.0.0.0:20000", False)
    shiju1.start()
    shiju2.start()
    shiju3.start()
    shiju1.join()
    shiju2.join()
    shiju3.join()


if __name__ == "__main__":
    # post_info()
    # psot_info_3()
    test_post()

