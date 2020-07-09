import time, sys, traceback, math, numpy, signal,json, random,copy
import threading
import urllib.request
import os
import socketio
import requests
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


ORDER_DICT1={'S':-300,'H':-200,'D':-100,'C':0,'J':-200}
ORDER_DICT2={'2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,'9':9,'1':10,'J':11,'Q':12,'K':13,'A':14,'P':15,'G':16}
def cards_order(card):
    return ORDER_DICT1[card[0]]+ORDER_DICT2[card[1]]


class Robot:
    def __init__(self,room,place,name):
        self.place = place
        self.room = room
        self.name = name
        self.players_information = [None, None, None, None]
        self.cards_list = []
        self.initial_cards = []
        self.history = []
        self.cards_on_table = []
        self.game_mode = 4
        self.scores = [[],[],[],[]]
        self.scores_num = [0,0,0,0]

    def pick_a_card(self,suit):
        self.mycards = {"S": [], "H": [], "D": [], "C": [], "J": []}
        for i in self.cards:
            self.mycards[i[0]].append(i[1:])

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

        print("{} plays {}".format(self.name,suit + self.mycards[suit][i]))

        return suit + self.mycards[suit][i]


    @staticmethod
    def family_name():
        return 'Coucou'



class RobotFamily:
    def __init__(self,url,robot_type):
        self.members = []
        self.sio = socketio.Client()
        self.robot = robot_type
        self.url = url

        pt = self

        @self.sio.event
        def connect():
            log("connect to server %s" % (pt.url))

        @self.sio.event
        def disconnect():
            log("disconnect from server %s" % (pt.url))

        @self.sio.on('loginsuc')
        def loginsuc(data):
            pt.loginsuc(data)

        @self.sio.on('new_player')
        def newplayer(data):
            pt.newplayer(data)

        @self.sio.on('shuffle')
        def shuffle(data):
            pt.shuffle(data)

        @self.sio.on('tableupdate')
        def tableupdate(data):
            pt.tableupdate(data)

        @self.sio.on('yourturn')
        def yourturn(data):
            pt.yourturn(data)

        @self.sio.on('got_yourchoice')
        def gotyourchoice(data):
            pt.gotyourchoice(data)

        @self.sio.on('got_leave_room')
        def gotleaveroom(data):
            pt.gotleaveroom(data)

        @self.sio.on('trick_end')
        def trickend(data):
            pt.trickend(data)

        @self.sio.on('game_end')
        def gameend(data):
            pt.gameend(data)

        @self.sio.on('interrupt_game_end')
        def interrupt_game_end(data):
            pt.interruptgameend(data)

        @self.sio.on('error')
        def error(data):
            pt.error(data)


    def connect(self):
        self.sio.connect(self.url)
        time.sleep(1)

    def sendmsg(self, cmd, dict):
        """name 是发给用户, sid 是发给sid, room 是房间广播"""
        log("sending %s: %s to server" % (cmd, dict))
        for retry_num in range(2):  # default not retry
            try:
                self.sio.emit(cmd, json.dumps(dict))
                break
            except:
                log("unknown error, retry_num: %d" % (retry_num), l=3)
        else:
            log("send failed", l=2)
            return 2
        return 0

    def strip_data(self,data):
        try:
            data = json.loads(data)
        except:
            log("parse data error: %s" % (data), l=2)
            self.sendmsg('error', {'detail': 'json.load(data) error'})
            return 1
        try:
            assert 'name' in data
        except:
            log('data lack element: %s' % (data), l=2)
            self.sendmsg('error', {'detail': 'data lack element'})
            return 2
        return data

    def add_member(self, room, place):
        ap = 0
        Flag = True
        while (Flag):
            Flag = False
            name = self.robot.family_name() + str(ap)
            for rb in self.members:
                if name == rb.name:
                    ap += 1
                    Flag = True
                    break

        name = self.robot.family_name() + str(ap)
        self.members.append(self.robot(room, place, name))
        #'login': {"user": "name", "user_pwd": "pwd", "room": roomid}
        #TODO:place, robot password
        self.sendmsg('login',{"user":name,"user_pwd":-1,"room":room,"place":place})

    def create_room(self):
        ap = 0
        Flag = True
        while (Flag):
            Flag = False
            name = self.robot.family_name() + str(ap)
            for rb in self.members:
                if name == rb.name:
                    ap += 1
                    Flag = True
                    break

        name = self.robot.family_name() + str(ap)
        self.members.append(self.robot(0, -1, name))
        self.sendmsg('login', {"user": name, "user_pwd": -1, "room": 'Q', "place": 0})

    def find_player(self,name):
        for rb in self.members:
            if rb.name == name:
                return rb
        return None

    def loginsuc(self,data):
        data = self.strip_data(data)
        if isinstance(data,int):
            return
        #TODO: response name from server
        #'loginsuc':{"name":name,"room":roomid,"your_loc":0,"players":["player1_name","player2_name",...]}
        player = self.find_player(data["name"])
        if not player:
            self.sendmsg('error',{'detail':"no such player"})
            return
        player.room = data["room"]
        player.place = data["your_loc"]

        player.players_information = copy.deepcopy(data["players"])

    def newplayer(self,data):
        data = self.strip_data(data)
        if isinstance(data,int):
            return

        player = self.find_player(data['name'])
        if not player:
            self.sendmsg('error', {'detail': "no such player"})
            return
        player.players_information = copy.deepcopy(data["players"])

    def shuffle(self,data):
        data = self.strip_data(data)
        if isinstance(data, int):
            return
        player = self.find_player(data['name'])
        if not player:
            self.sendmsg('error', {'detail': "no such player"})
            return

        player.initial_cards = copy.deepcopy(data["cards"])
        player.cards_list = copy.deepcopy(data["cards"])

    def update(self,data):
        data = self.strip_data(data)
        if isinstance(data, int):
            return

        player = self.find_player(data['name'])
        if not player:
            self.sendmsg('error', {'detail': "no such player"})
            return

        cards_on_table = copy.deepcopy(data['this_trick'])
        start = data['trick_start']

        player.cards_on_table = []
        player.cards_on_table.append(start)
        player.cards_on_table.extend(cards_on_table)

    def yourturn(self,data):
        data = self.strip_data(data)
        if isinstance(data, int):
            return

        player = self.find_player(data['name'])
        if not player:
            self.sendmsg('error', {'detail': "no such player"})
            return

        if not player.state == 'trick_before_play':
            return

        card = player.pick_a_card(data['color'])

        self.sendmsg('mychoice', {'user': player.name, 'card':card, 'room':player.room})

    def gotyourchoice(self,data):
        data = self.strip_data(data)
        if isinstance(data, int):
            return

        player = self.find_player(data['name'])
        if not player:
            self.sendmsg('error', {'detail': "no such player"})
            return

        player.cards_list = copy.deepcopy(data['your_remain'])

    def gotleaveroom(self,data):
        data = self.strip_data(data)
        if isinstance(data, int):
            return

        player = self.find_player(data['name'])
        if not player:
            self.sendmsg('error', {'detail': "no such player"})
            return

        index = 0
        for i,mem in enumerate(self.members):
            if mem.name == data['name']:
                index = i
                break

        self.members.pop(index)
        if len(self.members) == 0:
            self.close_family()

    def trickend(self,data):
        data = self.strip_data(data)
        if isinstance(data, int):
            return

        player = self.find_player(data['name'])
        if not player:
            self.sendmsg('error', {'detail': "no such player"})
            return

        player.scores = copy.deepcopy(data['scores'])
        player.history.append(player.cards_on_table)
        player.cards_on_table = []

    def gameend(self,data):
        data = self.strip_data(data)
        if isinstance(data, int):
            return

        player = self.find_player(data['name'])
        if not player:
            self.sendmsg('error', {'detail': "no such player"})
            return

        player.scores_num = copy.deepcopy(data['scores_num'])
        player.scores = copy.deepcopy(data['scores'])

        #time.sleep(1)
        self.cancel_player(player.name)

    def interruptgameend(self,data):
        data = self.strip_data(data)
        if isinstance(data, int):
            return

        player = self.find_player(data['name'])
        if not player:
            self.sendmsg('error', {'detail': "no such player"})
            return

        self.cancel_player(player.name)


    def error(self,data):
        data = self.strip_data(data)
        if isinstance(data, int):
            return

        if 'name' in data:
            player = self.find_player(data['name'])
            if not player:
                self.sendmsg('error', {'detail': "no such player"})
                return

            log('%s:%s'%(data['name'],data['detail']),l = 1)

        else:
            log(data['detail'],l = 1)

    def cancel_player(self,name):
        player = self.find_player(name)
        if not player:
            self.sendmsg('error', {'detail': "no such player"})
            return

        self.sendmsg('leave_room',{'user':name,'room':player.room})

    def close_family(self):
        if len(self.members) == 0:
            self.sio.disconnect()
        print("disconnect from server")


robot_list = [Robot]

if __name__ == '__main__':
    fm = RobotFamily('http://0.0.0.0:5000',Robot)
    fm.connect()
    print('a')
    fm.create_room()
    print('b')
    while fm.members[0].place == -1:
        time.sleep(1)
        print('gg')
    print('c')
    id = fm.members[0].room
    print('d')
    fm.add_member(id,1)
    fm.add_member(id,2)
    fm.add_member(id,3)
    print('f')




