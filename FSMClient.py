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
    def __init__(self,room,place,name,create_room = False):
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
        self.state = 'logout'
        self.creator = create_room

    def pick_a_card(self):
        self.mycards = {"S": [], "H": [], "D": [], "C": [], "J": []}
        for i in self.cards_list:
            self.mycards[i[0]].append(i[1:])

        suit = 'A' if len(self.cards_on_table) == 1 else self.cards_on_table[1][0]

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

    def __str__(self):
        return 'name:{} state:{}'.format(self.name,self.state)

    def shuffle(self):
        pass

    def update(self):
        pass

    def trickend(self):
        pass

    def gameend(self):
        print('result:{} my score:{}'.format(self.scores_num,self.scores_num[self.place]))
        time.sleep(1)

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
        self.a = 0

        @self.sio.event
        def connect():
            log("connect to server %s" % (pt.url))
            for rb in self.members:
                print(rb)
                self.sendmsg('request_info',{'user':rb.name})
            pt.a = time.time()

        @self.sio.event
        def disconnect():

            log("disconnect from server %s" % (pt.url))

        @self.sio.on('login_reply')
        def login_reply(data):
            pt.loginreply(data)

        @self.sio.on('create_room_reply')
        def create_room_reply(data):
            pt.createroomreply(data)

        @self.sio.on('enter_room_reply')
        def enter_room_reply(data):
            pt.enterroomreply(data)

        @self.sio.on('ready_for_start_reply')
        def ready_for_start_reply(data):
            pt.readyforstartreply(data)

        @self.sio.on('player_info')
        def player_info(data):
            pt.playerinfo(data)

        @self.sio.on('shuffle')
        def shuffle(data):
            pt.shuffle(data)

        @self.sio.on('update')
        def update(data):
            pt.update(data)

        @self.sio.on('your_turn')
        def your_turn(data):
            pt.yourturn(data)

        @self.sio.on('my_choice_reply')
        def my_choice_reply(data):
            pt.mychoicereply(data)

        @self.sio.on('logout_reply')
        def logout_reply(data):
            pt.logoutreply(data)

        @self.sio.on('trick_end')
        def trickend(data):
            pt.trickend(data)

        @self.sio.on('game_end')
        def game_end(data):
            pt.gameend(data)

        @self.sio.on('new_game_reply')
        def newgamereply(data):
            pt.newgamereply(data)

        @self.sio.on('choose_place_reply')
        def choose_place_reply(data):
            pt.chooseplacereply(data)

        @self.sio.on('request_info_reply')
        def request_info_reply(data):
            pt.recovery(data)

        @self.sio.on('error')
        def error(data):
            pt.error(data)

    def recovery(self,data):
        data = self.strip_data(data)
        if isinstance(data, int):
            return
        player = self.find_player(data['user'])
        if not player:
            self.sendmsg('error', {'detail': "no such player"})
            return

        player.state = data['state']
        if player.state == 'logout':
            self.cancel_player(player.name)
            return
        if player.state == 'login':
            if player.room > 0:
                self.sendmsg('enter_room',{'user':player.name,'room':player.room})
            else:
                self.cancel_player(player.name)
            return
        if player.state == 'room':
            if player.room > 0:
                self.sendmsg('choose_place', {'user': player.name, 'room': player.room, 'place': player.place})
            else:
                self.cancel_player(player.name)
            return

        player.room = data['room']
        player.place = data['place']
        player.players_information = copy.deepcopy(data['players'])
        if player.state == 'wait':
            self.sendmsg('ready_for_start', {'user': player.name})
            return

        player.cards_list = copy.deepcopy(data['cards_remain'])
        player.cards_on_table = []
        player.cards_on_table.append(data['trick_start'])
        player.cards_on_table = copy.deepcopy(data['this_trick'])
        player.history = copy.deepcopy(data['history'])
        player.initial_cards = copy.deepcopy(data['initial_cards'])

        if player.state == 'end':
            player.scores = copy.deepcopy(data['scores'])
            player.scores_num = copy.copy(data['scores_num'])
            #print('data:{}'.format(data['scores_num']))
            player.gameend()
            self.sendmsg('new_game',{'user':player.name})
            return
        if player.state == 'play_a_card':
            card = player.pick_a_card()
            print('sending choice')
            self.sendmsg('my_choice', {'user': player.name, 'card': card})
            return

    def connect(self):
        self.sio.connect(self.url)
        #time.sleep(1)

    def sendmsg(self, cmd, dict):
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
            assert 'user' in data
        except:
            log('data lack element: %s' % (data), l=2)
            self.sendmsg('error', {'detail': 'data lack element'})
            return 2
        return data

    def make_a_name(self):
        ap = 0
        Flag = True
        name = ''
        while (Flag):
            Flag = False
            name = self.robot.family_name() + str(ap)
            for rb in self.members:
                if name == rb.name:
                    ap += 1
                    Flag = True
                    break
        return name

    def add_member(self, room, place):
        name = self.make_a_name()
        self.members.append(self.robot(room, place, name))
        #'login': {"user": "name", "user_pwd": "pwd", "room": roomid}
        #TODO:place, robot password
        self.sendmsg('login',{"user":name,"user_pwd":-1,"is_robot":True,"robot_type":self.robot.family_name()})
        return name

    def find_player(self,name):
        for rb in self.members:
            if rb.name == name:
                return rb
        return None

    def loginreply(self,data):
        data = self.strip_data(data)
        if isinstance(data,int):
            print('data error')
            return
        player = self.find_player(data['user'])
        if not player:
            self.sendmsg('error',{'detail':"no such player"})
            return
        if not player.state == 'logout':

            return
        player.state = 'login'
        if not player.creator:
            self.sendmsg('enter_room',{'user':player.name,'room':player.room})
        else:
            self.sendmsg('create_room', {'user': player.name, 'room':'Q'})
        #player.players_information = copy.deepcopy(data["players"])

    def createroomreply(self,data):
        data = self.strip_data(data)
        if isinstance(data, int):
            return
        player = self.find_player(data['user'])
        if not player:
            self.sendmsg('error', {'detail': "no such player"})
            return
        if not player.state == 'login':
            return

        player.state = 'wait'
        player.room = data['room_id']
        player.place = 0
        player.players_information = copy.deepcopy(data["players"])
        self.sendmsg('ready_for_start', {'user': player.name})

    def enterroomreply(self,data):
        data = self.strip_data(data)
        if isinstance(data, int):
            return
        player = self.find_player(data['user'])
        if not player:
            self.sendmsg('error', {'detail': "no such player"})
            return
        if not player.state == 'login':
            return

        player.state = 'room'
        self.sendmsg('choose_place', {'user':player.name,'room':player.room,'place':player.place})

    def chooseplacereply(self,data):
        data = self.strip_data(data)
        if isinstance(data, int):
            return
        player = self.find_player(data['user'])
        if not player:
            self.sendmsg('error', {'user':player.name,'detail': "no such player"})
            return
        if not player.state == 'room':
            return

        if not data['success']:
            self.sendmsg('error',{'user':player.name,'detail':'robot can\'t sit down'})
            return

        player.state = 'wait'
        self.sendmsg('ready_for_start',{'user':player.name})

    def readyforstartreply(self,data):
        data = self.strip_data(data)
        if isinstance(data, int):
            return
        player = self.find_player(data['user'])
        if not player:
            self.sendmsg('error', {'user': player.name, 'detail': "no such player"})
            return
        if not player.state == 'wait':
            return

        player.state = 'before_start'

    def playerinfo(self,data):
        data = self.strip_data(data)
        if isinstance(data,int):
            return

        player = self.find_player(data['user'])
        if not player:
            self.sendmsg('error', {'detail': "no such player"})
            return
        player.players_information = copy.deepcopy(data["players"])

    def shuffle(self,data):
        #print('processin shuffle')
        data = self.strip_data(data)
        if isinstance(data, int):
            return
        player = self.find_player(data['user'])

        if not player:
            self.sendmsg('error', {'detail': "no such player"})
            return

        if not player.state == 'before_start':
            return

        player.initial_cards = copy.deepcopy(data["cards"])
        player.cards_list = copy.deepcopy(data["cards"])
        player.state = 'trick_before_play'
        player.shuffle()

    def update(self,data):
        #print('processing update')
        data = self.strip_data(data)
        if isinstance(data, int):
            return

        player = self.find_player(data['user'])
        if not player:
            self.sendmsg('error', {'detail': "no such player"})
            return

        cards_on_table = copy.deepcopy(data['this_trick'])
        start = data['trick_start']

        player.cards_on_table = []
        player.cards_on_table.append(start)
        player.cards_on_table.extend(cards_on_table)
        player.update()

    def yourturn(self,data):
        #print('processing youturn')
        data = self.strip_data(data)
        if isinstance(data, int):
            return

        player = self.find_player(data['user'])
        if not player:
            self.sendmsg('error', {'detail': "no such player"})
            return

        if not player.state == 'trick_before_play':
            print(player.state)
            return
        player.state = 'play_a_card'

        card = player.pick_a_card()
        print('sending choice')
        self.sendmsg('my_choice', {'user': player.name, 'card':card})

    def mychoicereply(self,data):
        print('enter reply')
        data = self.strip_data(data)
        if isinstance(data, int):
            return

        player = self.find_player(data['user'])
        if not player:
            self.sendmsg('error', {'detail': "no such player"})
            return

        if not player.state == 'play_a_card':
            return

        tmp = len(player.cards_list)
        player.cards_list= copy.deepcopy(data['your_remain'])
        if not tmp == len(player.cards_list):
            player.state = 'trick_after_play'
            #self.sendmsg('error', {'user': player.name, 'detail': 'just test'})
            print('recevive choice reply')
        else:
            card = player.pick_a_card()
            self.sendmsg('my_choice', {'user': player.name, 'card': card})


    def logoutreply(self,data):
        data = self.strip_data(data)
        if isinstance(data, int):
            return

        player = self.find_player(data['user'])
        if not player:
            self.sendmsg('error', {'detail': "no such player"})
            return

        index = 0
        for i,mem in enumerate(self.members):
            if mem.name == data['user']:
                index = i
                break

        self.members.pop(index)

    def trickend(self,data):
        print('receive trick end')
        data = self.strip_data(data)
        if isinstance(data, int):
            return

        player = self.find_player(data['user'])
        if not player:
            self.sendmsg('error', {'detail': "no such player"})
            return

        if not player.state == 'trick_after_play':
            return

        player.scores = copy.deepcopy(data['scores'])
        player.history.append(player.cards_on_table)
        player.cards_on_table = []
        player.state = 'trick_before_play'
        player.trickend()

    def gameend(self,data):
        print('receive game end')
        data = self.strip_data(data)
        if isinstance(data, int):
            return

        player = self.find_player(data['user'])
        if not player:
            self.sendmsg('error', {'detail': "no such player"})
            return

        if not player.state == 'trick_before_play':
            return

        player.scores = copy.deepcopy(data['scores'])
        player.scores_num = data['scores_num']
        player.gameend()

        player.state = 'end'

        print('send new game')
        self.sendmsg('new_game',{'user':data['user']})

        #time.sleep(1)
        #self.cancel_player(player.name)

    def newgamereply(self,data):
        data = self.strip_data(data)
        if isinstance(data, int):
            return

        player = self.find_player(data['user'])
        if not player:
            self.sendmsg('error', {'detail': "no such player"})
            return

        if not player.state == 'end':
            return

        player.state = 'wait'
        self.sendmsg('ready_for_start',{'user':player.name})

    def error(self,data):
        data = self.strip_data(data)
        if isinstance(data, int):
            return

        if 'user' in data:
            player = self.find_player(data['user'])
            if not player:
                self.sendmsg('error', {'detail': "no such player"})
                return

            log('%s:%s'%(data['user'],data['detail']),l = 1)

        else:
            log(data['detail'],l = 1)

    def cancel_player(self,name):
        player = self.find_player(name)
        if not player:
            self.sendmsg('error', {'detail': "no such player"})
            return

        if not player.state == 'ready':
            return

        self.sendmsg('logout',{'user':name})

    def close_family(self):
        if len(self.members) == 0:
            self.sio.disconnect()
        print("disconnect from server")

    def create_room(self):
        name = self.make_a_name()
        self.members.append(self.robot(0, 0, name,True))
        # 'login': {"user": "name", "user_pwd": "pwd", "room": roomid}
        # TODO:place, robot password
        self.sendmsg('login', {"user": name, "user_pwd": -1})


robot_list = [Robot]

if __name__ == '__main__':
    fm = RobotFamily('http://127.0.0.1:5000',Robot)
    fm.connect()
    print('a')
    fm.create_room()
    print('b')
    while fm.members[0].room == 0:
        time.sleep(0.1)
        print('gg')
    print('c')
    id = fm.members[0].room
    print('d')
    fm.add_member(id,1)
    fm.add_member(id,2)
    fm.add_member(id,3)
    print('f')




