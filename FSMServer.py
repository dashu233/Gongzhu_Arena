

import time, sys, traceback, math, copy
import FSMClient

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

SCORE_DICT = {'SQ': -100, 'DJ': 100, 'C10': 0,
              'H2': 0, 'H3': 0, 'H4': 0, 'H5': -10, 'H6': -10, 'H7': -10, 'H8': -10, 'H9': -10, 'H10': -10,
              'HJ': -20, 'HQ': -30, 'HK': -40, 'HA': -50, 'JP': -60, 'JG': -70}

ORDER_DICT1 = {'S': -300, 'H': -200, 'D': -100, 'C': 0, 'J': -200}
ORDER_DICT2 = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '1': 10, 'J': 11, 'Q': 12, 'K': 13,
               'A': 14, 'P': 15, 'G': 16}


def cards_order(card):
    #print(card)
    return ORDER_DICT1[card[0]] + ORDER_DICT2[card[1]]

import random, eventlet, socketio, copy, json, threading

class PlayerInfo():
    def __init__(self):
        self.cards_list = []
        self.initial_cards = []
        self.scores = []
        self.scores_num = []
        self.ready = False
    def clear(self):
        self.cards_list = []
        self.initial_cards = []
        self.scores = []
        self.scores_num = []
        self.ready = False

class RoomHoster:
    def __init__(self,gamemode=4):
        self.gamemode = gamemode
        self.players = ['' for i in range(self.gamemode)]
        self.players_info = {'EXAMPLE':PlayerInfo()}
        # key is player's name
        # include 'cards_list', 'initial_cards', 'scores', 'scores_num', 'state','ready'
        self.cards_on_table = []
        # [1,cards1,cards2,cards3..]

        self.history = []
        # joined cards_on_table
        self.trick_start = 0
        self.now_player = 0
        self.trick_end = False
        self.trick_count = 0
        self.game_end = False

        self.room_state = 'available'
        #'available', 'full', 'started'

    def get_loc(self,name):
        if not name:
            log("empty name is illegal")
            return -1
        try:
            return self.players.index(name)
        except:
            log('no such player')
            return -1

    def update_scores(self,winner):
        for card in self.cards_on_table[1:]:
            if card in SCORE_DICT:
                self.players_info[self.players[winner]].scores.append(card)

    def calc_score(self,name):
        s = 0
        has_score_flag = False
        c10_flag = False
        for i in self.players_info[name].scores:
            if i == "C10":
                c10_flag = True
            else:
                s += SCORE_DICT[i]
                has_score_flag = True
        if c10_flag:
            if not has_score_flag:
                s += 50
            else:
                s *= 2
        self.players_info[name].scores_num = s
        return s

    def judge_winner(self):
        soc = -65535
        loc = 0
        for i, card in enumerate(self.cards_on_table[1:]):
            if card[0] == self.cards_on_table[1][0] and ORDER_DICT2[card[1]] > soc:
                loc = i
                soc = ORDER_DICT2[card[1]]
                # log("%s is larger"%(card))
        return (loc + self.cards_on_table[0]) % self.gamemode

    def shuffle(self):
        """will init cards_remain,cards_played,cards_initial,trick_start"""
        if self.gamemode == 3:
            cards = ['S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8', 'S9', 'S10', 'SJ', 'SQ', 'SK', 'SA',
                     'H2', 'H3', 'H4', 'H5', 'H6', 'H7', 'H8', 'H9', 'H10', 'HJ', 'HQ', 'HK', 'HA',
                     'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'DJ', 'DQ', 'DK', 'DA',
                     'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9', 'C10', 'CJ', 'CQ', 'CK', 'CA', 'JG', 'JP']
        else:
            cards = ['S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8', 'S9', 'S10', 'SJ', 'SQ', 'SK', 'SA',
                     'H2', 'H3', 'H4', 'H5', 'H6', 'H7', 'H8', 'H9', 'H10', 'HJ', 'HQ', 'HK', 'HA',
                     'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'DJ', 'DQ', 'DK', 'DA',
                     'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9', 'C10', 'CJ', 'CQ', 'CK', 'CA']
        # 初始化room信息
        random.shuffle(cards)
        if self.gamemode == 3:
            for i,player in enumerate(self.players):
                self.players_info[player].initial_cards = cards[i*18:(i+1)*18]
                self.players_info[player].scores = []
        else:
            for i,player in enumerate(self.players):
                self.players_info[player].initial_cards = cards[i*13:(i+1)*13]
                self.players_info[player].scores = []

        for player in self.players:
            tmp = self.players_info[player].initial_cards
            tmp.sort(key = cards_order)
            self.players_info[player].cards_list = copy.copy(tmp)

        self.history = []
        self.cards_on_table = []
        self.trick_start = 0
        self.now_player = self.trick_start
        self.room_state = 'started'

    def get_players(self):
        tmp = []
        for player in self.players:
            if not player:
                tmp.append(['',False])
            else:
                tmp.append([player,self.players_info[player].ready])
        return tmp

    def add_player(self,name,place = 0):
        if not self.room_state == 'available':
            log('room not available')
            return False
        if self.players[place]:
            log('already exist player')
            return False
        else:
            self.players[place] = name

        self.players_info[name] = PlayerInfo()
        if all(self.players):
            self.room_state = 'full'

        return True

    def make_ready(self,name):
        if name in self.players_info:
            self.players_info[name].ready = True
            return True
        else:
            return False

    def check_ready(self):
        for player in self.players:
            if not player:
                return False
            if not self.players_info[player].ready:
                return False
        return True

    def play_a_card(self,name,card):
        #return 0 is success
        #check legel
        try:
            usr_loc = self.players.index(name)
        except:
            log('no such player')
            return 1
        if usr_loc != self.now_player:
            return 'error', {'detail': 'not your turn'}
        if card not in self.players_info[name].cards_list:
            return 'error', {'detail': 'not your card'}

        if usr_loc == self.trick_start:
            # the first player
            pass
        elif card[0] == self.cards_on_table[1][0]:
            # the same color
            pass
        elif all([not i[0] == self.cards_on_table[1][0] for i in self.players_info[name].cards_list]):
            # do not have this color
            pass
        else:
            return 'my_choice_reply',{'legal':False,'your_remain':self.players_info[name].cards_list}

        #play a card
        cardid = self.players_info[name].cards_list.index(card)
        self.players_info[name].cards_list.pop(cardid)
        self.cards_on_table.append(card)
        self.now_player += 1
        self.now_player %= self.gamemode

        if self.now_player == self.trick_start:
            self.trick_end = True

        return 'my_choice_reply',{'legal':True,'your_remain':self.players_info[name].cards_list}

    def step(self):
        if self.trick_end:
            self.trick_count += 1
            self.trick_end = False
            winner = self.judge_winner()
            self.update_scores(winner)
            self.trick_start = winner
            self.now_player = winner
            self.history.append(self.cards_on_table)
            self.cards_on_table = []
            if self.trick_count == 13 if self.gamemode == 4 else 18:
                self.game_end = True
            return 'all','trick_end',{"winner":winner, 'scores':[self.players_info[pl].scores for pl in self.players]}
        if self.game_end:
            self.room_state = 'full'
            self.game_end = False
            for pl in self.players:
                self.calc_score(pl)
            return 'all','game_end',{'scores':[self.players_info[pl].scores for pl in self.players],
                                     'scores_num':[self.players_info[pl].scores_num for pl in self.players]}
        print(self.cards_on_table)

        if len(self.cards_on_table) == 0:
            self.cards_on_table.append(self.trick_start)

        return self.players[self.now_player],'your_turn',\
            {'suit': 'A' if self.trick_start == self.now_player else self.cards_on_table[1][0]}

    def update(self):
        return 'update', {'this_trick':self.cards_on_table[1:],'trick_start':self.trick_start}
    def clear(self):
        self.cards_on_table = []
        self.history = []
        # joined cards_on_table
        self.trick_start = 0
        self.now_player = 0
        self.trick_end = False
        self.trick_count = 0
        self.game_end = False

        self.room_state = 'full'
        # 'available', 'full', 'started'

    def leave_room(self,name):
        if self.room_state == 'started':
            log('game started')
            return False
        if name not in self.players:
            log('no such player')
            return False

        id = self.players.index(name)
        self.players[id] = ''
        self.players_info.pop(name)

    def isempty(self):
        if all([not pl for pl in self.players]):
            return True

class UserInfo():
    def __init__(self):
        self.state = 'logout'
        self.room = -1
        self.pwd = ''
        self.sid = 1000
        self.is_robot = False
        self.robot_type = ''


class FSMServer:
    def __init__(self,port):
        self.sio = socketio.Server()
        self.app = socketio.WSGIApp(self.sio,
                       static_files={'/': 'index.html', '/favicon.ico': 'logo.png', '/asset': 'asset', '/src': 'src'})

        self.user_state_dict = {0:UserInfo()}
        # 'state':FSMstate,'room':room or -1, 'pwd':password, 'sid':1000
        self.rooms = {0:RoomHoster()}

        self.port = port

        #rooms[id] = RoomHoster()
        self.robot_dict = {}
        self.robot_family = {'0':FSMClient.RobotFamily('http://127.0.0.1:5000',FSMClient.Robot)}
        self.load_robot_dict()

        pt = self

        self.load_pwd()

        @self.sio.on('login')
        def login(sid,data):
            pt.login(sid,data)

        @self.sio.on('request_room_list')
        def request_room_list(sid,data):
            pt.requestroomlist(sid,data)

        @self.sio.on('create_room')
        def create_room(sid,data):
            pt.createroom(sid,data)

        @self.sio.on('enter_room')
        def enter_room(sid,data):
            pt.enterroom(sid,data)

        @self.sio.on('choose_place')
        def choose_place(sid,data):
            pt.chooseplace(sid,data)

        @self.sio.on('ready_for_start')
        def ready_for_start(sid,data):
            pt.readyforstart(sid,data)

        @self.sio.on('my_choice')
        def my_choice(sid,data):
            pt.mychoice(sid,data)

        @self.sio.on('leave_room')
        def leave_room(sid,data):
            pt.leaveroom(sid,data)

        @self.sio.on('logout')
        def logout(sid,data):
            pt.logout(sid,data)

        @self.sio.on('new_game')
        def new_game(sid,data):
            pt.newgame(sid,data)

        @self.sio.on('ask_change_place')
        def ask_change_place(sid,data):
            pt.askchangeplace(sid,data)

        @self.sio.on('change_place_request_reply')
        def change_place_request_reply(sid,data):
            pt.changeplacerequestreply(sid,data)

        @self.sio.on('request_robot_list')
        def request_robot_list(sid,data):
            pt.requestrobotlist(sid,data)

        @self.sio.on('add_robot')
        def add_robot(sid,data):
            pt.addrobot(sid,data)

        @self.sio.on('cancel_robot')
        def cancel_robot(sid,data):
            pt.cancelrobot(sid,data)

        @self.sio.on('error')
        def error(sid,data):
            data = json.loads(data)
            log("error:%s" % (data['detail']))

        @self.sio.on('request_info')
        def request_info(sid,data):
            self.requestinfo(sid,data)

        @self.sio.event
        def connect(sid, environ):
            # environ 基本就是 headers 加上一些杂七杂八的东西
            # log("environ: %s"%(environ))
            log("sid %s connect" % (sid))

        @self.sio.event
        def disconnect(sid):
            log("sid %s disconnect" % (sid))



    def load_robot_dict(self):
        for i,rb in enumerate(FSMClient.robot_list):
            self.robot_dict[rb.family_name()] = rb
            self.robot_family[rb.family_name()] = \
                FSMClient.RobotFamily('http://127.0.0.1:{}'.format(self.port),rb)


    def load_pwd(self):
        pass

    def login(self,sid,data):
        data = self.strip_data(sid, data)
        name = data['user']
        '''
        TODO: add pwd check
        '''
        try:
            assert self.user_state_dict[name].state == 'logout'
        except:
            self.sendmsg('error', {'detail': 'state error'}, name=name)
            return

        self.user_state_dict[name].state = 'login'
        if 'is_robot' in data:
            self.user_state_dict[name].is_robot = True
            self.user_state_dict[name].robot_type = data['robot_type']

        self.sendmsg('login_reply',{},name=name)

    def requestroomlist(self,sid,data):
        data = self.strip_data(sid, data)
        name = data['user']
        # check data form
        try:
            assert 'range' in data
            rg = range(data['range'])
        except:
            self.sendmsg('error', {'detail': 'form error'}, name=name)
            return

        # check state
        try:
            assert self.user_state_dict[name].state == 'login'
        except:
            self.sendmsg('error', {'detail': 'state error'}, name=name)
            return

        state_list = []
        for i in rg:
            if i in self.rooms:
                if self.rooms[i].room_state == 'available':
                    state_list.append(1)
                if self.rooms[i].room_state == 'full':
                    state_list.append(2)
                if self.rooms[i].room_state == 'started':
                    state_list.append(3)
            else:
                state_list.append(0)
        self.sendmsg('request_room_list_reply',{'list':state_list})

    def createroom(self,sid,data):
        data = self.strip_data(sid,data)
        name = data['user']

        # check data form
        try:
            assert 'room' in data
            way = data['room']
            assert way in ['Q','T']
        except:
            self.sendmsg('error', {'detail': 'form error'}, name=name)
            return

        #check state
        try:
            assert self.user_state_dict[name].state == 'login'
        except:
            self.sendmsg('error', {'detail': 'state error'}, name=name)
            return

        roomid_plus_lock = threading.Lock()
        roomid_plus_lock.acquire()
        try:
            roomid = max([i for i in self.rooms.keys()]) + 1
            self.rooms[roomid] = RoomHoster(gamemode=4 if way == 'Q' else 3)

            name = data['user']
            self.user_state_dict[name].room = roomid
            self.rooms[roomid].add_player(name)
            #change state
            self.user_state_dict[name].state = 'wait'
            self.sendmsg("create_room_reply", {
                                 "room_id": roomid, "players": self.rooms[roomid].get_players()}, name=name)
        except:
            log("", l=3)
            return 2
        finally:
            roomid_plus_lock.release()

    def enterroom(self,sid,data):
        data = self.strip_data(sid, data)
        name = data['user']

        try:
            assert 'room' in data
            roomid = data['room']
        except:
            self.sendmsg('error', {'detail': 'form error'}, name=name)
            return

        try:
            assert self.user_state_dict[name].state == 'login'
        except:
            self.sendmsg('error', {'detail': 'state error'}, name=name)
            return

        thisroom = self.rooms[roomid]
        self.user_state_dict[name].state = 'room'
        self.sendmsg("enter_room_reply", {
            "game_state":thisroom.room_state, "players": thisroom.get_players()}, name=name)

    def chooseplace(self,sid,data):
        data = self.strip_data(sid, data)
        name = data['user']

        #check form
        try:
            assert 'room' in data
            roomid = data['room']
            assert 'place' in data
            place = data['place']
        except:
            self.sendmsg('error', {'detail': 'form error'}, name=name)
            return

        #check state
        try:
            assert self.user_state_dict[name].state == 'room'
        except:
            self.sendmsg('error', {'detail': 'state error'}, name=name)
            return

        thisroom = self.rooms[roomid]
        suc = thisroom.add_player(name,place)

        self.sendmsg('choose_place_reply', {'success': suc},name=name)
        # change state
        if suc:
            self.user_state_dict[name].state = 'wait'
            self.user_state_dict[name].room = roomid
            self.send_player_info(roomid)

    def send_player_info(self,roomid):
        self.sendmsg('player_info',{'players':self.rooms[roomid].get_players()},roomid=roomid)

    def readyforstart(self,sid,data):
        data = self.strip_data(sid, data)
        name = data['user']

        # check form
        try:
            pass
        except:
            self.sendmsg('error', {'detail': 'form error'}, name=name)
            return

        # check state
        try:
            assert self.user_state_dict[name].state == 'wait'
        except:
            self.sendmsg('error', {'detail': 'state error'}, name=name)
            return

        roomid = self.user_state_dict[name].room
        thisroom = self.rooms[roomid]

        if not thisroom.make_ready(name):
            self.sendmsg('error',{'detail':'no such player'},name=name)
        self.sendmsg('ready_for_start_reply',{},name=name)

        self.user_state_dict[name].state = 'before_start'

        if thisroom.check_ready():
            for pl in thisroom.players:
                self.user_state_dict[pl].state = 'trick_before_play'
            self.shuffle(roomid)

            cmd, dict = thisroom.update()
            self.sendmsg(cmd,dict,roomid=roomid)
            tar,cmd,dict = thisroom.step()
            self.user_state_dict[tar].state = 'play_a_card'
            self.sendmsg(cmd,dict,name=tar)

    def mychoice(self,sid,data):
        data = self.strip_data(sid, data)
        name = data['user']

        # check form
        try:
            assert 'card' in data
        except:
            self.sendmsg('error', {'detail': 'form error'}, name=name)
            return

        # check state
        try:
            assert self.user_state_dict[name].state == 'play_a_card'
        except:
            self.sendmsg('error', {'detail': 'state error'}, name=name)
            return

        roomid = self.user_state_dict[name].room
        cd = data['card']
        thisroom = self.rooms[roomid]
        #time.sleep(0.1)
        cmd,dict = thisroom.play_a_card(name,cd)
        self.sendmsg(cmd,dict,name=name)
        #time.sleep(0.1)
        if cmd == 'my_choice_reply' and dict['legal']:
            self.user_state_dict[name].state = 'trick_after_play'
            cmd,dict = thisroom.update()
            self.sendmsg(cmd,dict,roomid=roomid)
            tar,cmd,dict = thisroom.step()
            if tar == 'all':
                if cmd == 'trick_end':
                    self.sendmsg(cmd,dict,roomid=roomid)
                    for pl in thisroom.players:
                        self.user_state_dict[pl].state = 'trick_before_play'
                    cmd, dict = thisroom.update()
                    self.sendmsg(cmd, dict, roomid=roomid)
                    tar,cmd,dict = thisroom.step()
                    if tar == 'all':
                        if not cmd == 'game_end':
                            log('game end error')
                        for pl in thisroom.players:
                            self.user_state_dict[pl].state = 'end'
                        #time.sleep(0.1)
                        self.sendmsg(cmd, dict, roomid=roomid)
                        thisroom.clear()
                    else:
                        self.user_state_dict[tar].state = 'play_a_card'
                        self.sendmsg(cmd,dict,name=tar)
                else:
                    log('trick end error')
            else:
                self.user_state_dict[tar].state = 'play_a_card'
                self.sendmsg(cmd, dict, name=tar)

    def leaveroom(self,sid,data):
        data = self.strip_data(sid, data)
        name = data['user']

        # check form
        try:
            pass
        except:
            self.sendmsg('error', {'detail': 'form error'}, name=name)
            return

        # check state
        try:
            assert self.user_state_dict[name].state == 'end' or \
                    self.user_state_dict[name].state == 'room' or \
                    self.user_state_dict[name].state == 'wait'
        except:
            self.sendmsg('error', {'detail': 'state error'}, name=name)
            return

        roomid = self.user_state_dict[name].room
        thisroom = self.rooms[roomid]

        if thisroom.leave_room(name):
            self.user_state_dict[name].state = 'login'
            self.user_state_dict[name].room = -1
            self.sendmsg('leave_room_reply',{},name=name)
            if thisroom.isempty():
                self.rooms.pop(roomid)

    def load_robot_list(self):
        self.robot_dict['MrRandom'] = Robot()

    def logout(self,sid,data):
        data = self.strip_data(sid, data)
        name = data['user']

        # check form
        try:
            pass
        except:
            self.sendmsg('error', {'detail': 'form error'}, name=name)
            return

        # check state
        try:
            assert self.user_state_dict[name].state == 'end' or \
                   self.user_state_dict[name].state == 'login' or \
                   self.user_state_dict[name].state == 'room' or \
                   self.user_state_dict[name].state == 'wait' or \
                   self.user_state_dict[name].state == 'ready'
        except:
            self.sendmsg('error', {'detail': 'state error'}, name=name)
            return

        roomid = self.user_state_dict[name].room
        if not roomid == -1:
            thisroom = self.rooms[roomid]
            if thisroom.leave_room(name):
                self.user_state_dict[name].room = -1
            if thisroom.isempty():
                self.rooms.pop(roomid)

        self.user_state_dict[name].state = 'logout'
        self.sendmsg('logout_reply',{},name=name)

    def newgame(self,sid,data):
        data = self.strip_data(sid, data)
        name = data['user']

        # check form
        try:
            pass
        except:
            self.sendmsg('error', {'detail': 'form error'}, name=name)
            return

        # check state
        try:
            assert self.user_state_dict[name].state == 'end'
        except:
            self.sendmsg('error', {'detail': 'state error'}, name=name)
            return

        roomid = self.user_state_dict[name].room
        thisroom = self.rooms[roomid]

        thisroom.players_info[name].clear()
        self.user_state_dict[name].state = 'wait'
        self.sendmsg('new_game_reply',{},name=name)

    def askchangeplace(self,sid,data):
        data = self.strip_data(sid, data)
        name = data['user']

        # check form
        try:
            assert 'target_place' in data
            target_place = data['target_place']
        except:
            self.sendmsg('error', {'detail': 'form error'}, name=name)
            return

        # check state
        try:
            assert self.user_state_dict[name].state == 'wait'
        except:
            self.sendmsg('error', {'detail': 'state error'}, name=name)
            return

        roomid = self.user_state_dict[name].room
        thisroom = self.rooms[roomid]

        if thisroom.players_info[name].ready:
            self.sendmsg('error', {'detail': 'you can\'t change place in ready mode' }, name=name)
            return
        tar_player = thisroom.players[target_place]
        if not tar_player:
            thisroom.players[target_place] = name
            self.sendmsg('ask_change_place_reply', {'success':True,'now_place':target_place}, name=name)
            self.sendmsg('player_info',{'players':thisroom.get_players()},roomid = roomid)
        else:
            self.sendmsg('change_place_request',{'request':[name,thisroom.players.index(name)]})

    def changeplacerequestreply(self,sid,data):
        data = self.strip_data(sid, data)
        name = data['user']

        # check form
        try:
            assert 'success' in data
            assert 'target_place' in data
            suc = data['success']
            tar_place = data['target_place']
        except:
            self.sendmsg('error', {'detail': 'form error'}, name=name)
            return

        # check state
        try:
            assert self.user_state_dict[name].state == 'wait'
        except:
            self.sendmsg('error', {'detail': 'state error'}, name=name)
            return

        roomid = self.user_state_dict[name].room
        thisroom = self.rooms[roomid]

        if suc:
            prt_place = thisroom.players.index(name)
            tmp = thisroom.players[tar_place]
            thisroom.players[tar_place] = name
            thisroom.players[prt_place] = tmp

            self.sendmsg('change_place_request_confirm',{'now_place':tar_place},name=name)
            self.sendmsg('ask_change_place_reply',{'success':suc, 'now_place':prt_place},name=tmp)

        else:
            prt_place = thisroom.players.index(name)
            tmp = thisroom.players[tar_place]
            self.sendmsg('change_place_request_confirm', {'now_place': prt_place}, name=name)
            self.sendmsg('ask_change_place_reply', {'success': suc, 'now_place': tar_place}, name=tmp)

    def requestrobotlist(self,sid,data):
        data = self.strip_data(sid, data)
        name = data['user']

        # check form
        try:
            pass
        except:
            self.sendmsg('error', {'detail': 'form error'}, name=name)
            return

        # check state
        try:
            assert self.user_state_dict[name].state == 'wait'
        except:
            self.sendmsg('error', {'detail': 'state error'}, name=name)
            return

        roomid = self.user_state_dict[name].room
        thisroom = self.rooms[roomid]

        self.sendmsg('request_robot_list_reply',{'robot_list':self.robot_dict})

    def addrobot(self,sid,data):
        data = self.strip_data(sid, data)
        name = data['user']

        # check form
        try:
            assert 'place' in data
            assert 'robot' in data
            place = data['place']
            rb_type = data['robot']
        except:
            self.sendmsg('error', {'detail': 'form error'}, name=name)
            return

        # check state
        try:
            assert self.user_state_dict[name].state == 'wait'
        except:
            self.sendmsg('error', {'detail': 'state error'}, name=name)
            return

        roomid = self.user_state_dict[name].room
        thisroom = self.rooms[roomid]

        if thisroom.players[place] or rb_type not in self.robot_dict:
            self.sendmsg('add_robot_reply', {'success': False}, name=name)

        rbn = self.robot_family[rb_type].add_member(roomid,place)
        self.sendmsg('add_robot_reply', {'success': True}, name=name)
        self.sendmsg('robot_come_in',{'robot_name':rbn,'place':place,'master':name},roomid=roomid)
        self.send_player_info(roomid)

    def robotswitch(self,sid,data):
        data = self.strip_data(sid, data)
        name = data['user']

        # check form
        try:
            assert 'robot_place' in data
            place1,place2 = tuple(data['place'])
        except:
            self.sendmsg('error', {'detail': 'form error'}, name=name)
            return

        # check state
        try:
            assert self.user_state_dict[name].state == 'wait'
        except:
            self.sendmsg('error', {'detail': 'state error'}, name=name)
            return

        roomid = self.user_state_dict[name].room
        thisroom = self.rooms[roomid]

        rb1 = thisroom.players[place1]
        rb2 = thisroom.players[place2]
        if not (rb1 and rb2 and not self.user_state_dict[rb1].is_robot
            and self.user_state_dict[rb2].is_robot):
            self.sendmsg('robot_switch_reply', {'success': False}, name=name)

        else:
            thisroom.players[place1] = rb2
            thisroom.players[place2] = rb1
            self.sendmsg('robot_switch_reply', {'success': True}, name=name)
            self.send_player_info(roomid)

    def cancelrobot(self,sid,data):
        data = self.strip_data(sid, data)
        name = data['user']

        # check form
        try:
            assert 'place' in data
            place = data['place']
        except:
            self.sendmsg('error', {'detail': 'form error'}, name=name)
            return

        # check state
        try:
            assert self.user_state_dict[name].state == 'wait'
        except:
            self.sendmsg('error', {'detail': 'state error'}, name=name)
            return

        roomid = self.user_state_dict[name].room
        thisroom = self.rooms[roomid]
        rbn = thisroom.players[place]

        if not rbn or not self.user_state_dict[rbn].is_robot:
            self.sendmsg('cancel_robot',{'success':False})
            return

        else:
            rb_type = self.user_state_dict[rbn].robot_type
            rb_family = self.robot_family[rb_type]
            rb_family.cancel_player(rbn)
            self.send_player_info(roomid)

    def requestinfo(self,sid,data):
        data = self.strip_data(sid, data)
        name = data['user']

        # check form
        try:
            pass
        except:
            self.sendmsg('error', {'detail': 'form error'}, name=name)
            return

        cmd = 'request_info_reply'
        dict = {}
        if name in self.user_state_dict:
            usrinfo = self.user_state_dict[name]
        else:
            dict['state'] = 'logout'
            self.sendmsg(cmd, dict, name=name)
            return

        roomid = usrinfo.room
        if roomid == -1:
            dict['state'] = usrinfo.state
            self.sendmsg(cmd, dict, name=name)
            return

        thisroom = self.rooms[roomid]
        plinfo = thisroom.players_info[name]
        dict = {'room':roomid,'state':usrinfo.state,'place':thisroom.players.index(name),
                'cards_remain':plinfo.cards_list,'this_trick':thisroom.cards_on_table[1:],
                'trick_start':thisroom.trick_start,'players':thisroom.get_players(),
                'history':thisroom.history,'initial_cards':plinfo.initial_cards,
                'scores':[thisroom.players_info[pl].scores for pl in thisroom.players],
                'scores_num':[thisroom.players_info[pl].scores_num for pl in thisroom.players]}
        self.sendmsg(cmd,dict,name=name)

    def shuffle(self,roomid):
        try:
            assert roomid in self.rooms, "roomid: %s not in rooms" % (roomid)
            thisroom = self.rooms[roomid]
            assert thisroom.gamemode == len(thisroom.players)
        except:
            log("", l=3)
            return 1

        thisroom.shuffle()

        for player in thisroom.players:
            self.sendmsg('shuffle',{'cards':thisroom.players_info[player].cards_list},name=player)

    def sendmsg(self,cmd, dict, name=None, sid=None, roomid=None,need_reply = False):
        """name 是发给用户, sid 是发给sid, room 是房间广播"""
        if cmd == 'disconnect':
            print('unkown disconnect')
            print(dict)
        for retry_num in range(2):  # default not retry
            try:
                # 以一定的概率触发异常以模拟网络不好，前端程序员会感谢我的
                #if random.random() > 100:
                #    raise Exception("Simulate Network error")
                # TODO: 文档上说默认是群发，需要加这个room关键字才是单发，但我觉得不管用？需要测试一下这个函数是否正常
                if name != None:
                    dict['user'] = name
                    log("sending %s: %s to (name)%s,(sid)%s,(roomid)%s" % (cmd, dict, name, sid, roomid))
                    self.sio.emit(cmd, json.dumps(dict), room=self.user_state_dict[name].sid)
                    #self.sio.emit(cmd, json.dumps(dict), room=self.user_state_dict[name].sid)
                elif sid != None:
                    log("sending %s: %s to (name)%s,(sid)%s,(roomid)%s" % (cmd, dict, name, sid, roomid))
                    self.sio.emit(cmd, json.dumps(dict), room=sid)
                elif roomid != None:
                    for user in self.rooms[roomid].players:
                        if user:
                            #log("sending %s: %s to (name)%s,(sid)%s,(roomid)%s" % (cmd, dict, name, sid, roomid))
                            self.sendmsg(cmd, dict, name=user)
                break
            except:
                log("unknown error, retry_num: %d" % (retry_num), l=3)
        else:
            log("send failed", l=2)
            return 2
        #time.sleep(0.1)
        return 0

    def strip_data(self,sid,data):
        try:
            data = json.loads(data)
        except:
            log("parse data error: %s" % (data), l=2)
            self.sendmsg('error', {'detail': 'json.load(data) error'}, sid=sid)
            return 1
        try:
            assert 'user' in data
            #assert 'room' in data
        except:
            log('data lack element: %s' % (data), l=2)
            self.sendmsg('error', {'detail': 'data lack element'}, sid=sid)
            return 2
        if data['user'] in self.user_state_dict:
            self.user_state_dict[data['user']].sid = sid
        else:
            self.user_state_dict[data['user']] = UserInfo()
            self.user_state_dict[data['user']].sid = sid
        return data

    def run_forever(self):
        try:
            eventlet.wsgi.server(eventlet.listen(('', self.port)), self.app)
        except:
            log("unknown error", l=3)


if __name__ == "__main__":
    server = FSMServer(5000)
    server.run_forever()

