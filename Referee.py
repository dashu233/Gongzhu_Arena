#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import time, sys, traceback, math, numpy, signal,json, random,copy,threading

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


from http.server import BaseHTTPRequestHandler

try:
    from http.server import ThreadingHTTPServer
    HTTPServerClass = ThreadingHTTPServer
except ImportError:
    from http.server import HTTPServer
    HTTPServerClass = HTTPServer
    log("import ThreadingHTTPServer failed, use HTTPServer instead")


class MyTimeoutException(Exception):
    pass

class MyHTTPServer(HTTPServerClass):
    '''
        rooms: dict, id:room
        players:dict, name:player
    '''
    players = {}
    rooms = {}
    def serve_forever(self):
        log("server is on %s" % (self.socket.getsockname(),))
        HTTPServerClass.serve_forever(self)

    def _handle_request_noblock(self):
        try:
            request, client_address = self.get_request()
        except OSError as e:
            signal.alarm(0)
            # log("OSError: %s"%(e),l=2)
            return 1
        except MyTimeoutException:
            # log("normal timeout")
            return 2
        except:
            signal.alarm(0)
            log("uncaught exception", l=3)
            return 3

        if self.verify_request(request, client_address):
            try:
                self.process_request(request, client_address)
            except:
                self.handle_error(request, client_address)
                self.shutdown_request(request)
        else:
            self.shutdown_request(request)
        return 0

    def get_request(self):
        def alarm_handle(signum, frame):
            raise MyTimeoutException("timeout!")

        # id=random.randint(0,65535)
        # log("%d: accepting new request"%(id))
        signal.signal(signal.SIGALRM, alarm_handle)
        signal.alarm(1)
        acc = self.socket.accept()
        signal.alarm(0)
        # log("%d: accpeted, cert: %s"%(id,acc[0].getpeercert()))
        return acc

#for sorting cards
ORDER_DICT1={'S':-300,'H':-200,'D':-100,'C':0,'J':-200}
ORDER_DICT2={'2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,'9':9,'1':10,'J':11,'Q':12,'K':13,'A':14,'P':15,'G':16}
def cards_order(card):
    return ORDER_DICT1[card[0]]+ORDER_DICT2[card[1]]

SCORE_DICT={'SQ':-100,'DJ':100,'C10':0,
            'H2':0,'H3':0,'H4':0,'H5':-10,'H6':-10,'H7':-10,'H8':-10,'H9':-10,'H10':-10,
            'HJ':-20,'HQ':-30,'HK':-40,'HA':-50,'JP':-60,'JG':-70}

class Player:
    def __init__(self, name = None, rob = True, client = 0, id = -1,place = 0):
        self.name = name
        self.rob = rob
        self.client = client
        self.id = -1
        self.place = place

class Room:
    '''
    player_num: 3 or 4
    for 4:   0
           3   1
             2
    for 3:   0
           2   1
    id : roomid

    player_address : address of players
    player_state : 0:empty,1:person,2:robot
    player_cards : player's hand cards(剩余)
    player_collect : player's collect cards, hearts.etc
    player_score : player's score(?)
    #player_score可以用一个函数每次现算，因为也不是很常用，存为变量的话，大部分时间都是undef的状态令人不安
    player_name : player's names
    player_ready_trick_end : ready for next trick, clear when ready_new_trick
    player_ready_new_trick : ready for new trick, clear when ready_trick_end

    star : which player need to play a card
    winner : which player win this turn
    huase : huase need to play, '' is any kind of huase
    cards_on_table: cards play in this turn
    turn : which turn
    game_state : waiting(0), start(1)

    trick_step: how many player has played a card in this trick
    trick: i'th trick

    '''
    def __init__(self,roomid,pn):
        self.id = roomid
        self.player_num = pn
        self.player_address = [0 for i in range(pn)]
        self.player_state = [0 for i in range(pn)]
        self.player_cards = [[] for i in range(pn)]
        self.player_collect = [[] for i in range(pn)]
        self.player_score = [0 for i in range(pn)]
        self.player_names = ['' for i in range(pn)]
        self.player_ready_trick_end = [False for i in range(pn)]
        self.player_trick_end_get = [False for i in range(pn)]

        self.star = 0
        self.winner = 0
        self.huase = ''
        self.cards_on_table = []
        self.last_trick_cards = []
        self.turn = 1
        self.game_state = 0

        self.trick_step = 0
        self.trick = 1

    def __str__(self):
        print("room:%d" % self.id)
        print("num of player: %d" % self.player_num)
        print("address of players:")
        print(self.player_address)
        print("state of players:")
        print(self.player_state)
        print("name of players:")
        print(self.player_names)
        print("score of players:")
        print(self.player_score)
        print("cards of players:")
        for i in self.player_cards:
            print(i)
        print("cards on table:")
        print(self.cards_on_table)
        print("next to play: %d winner:%d" % (self.star,self.winner))
        if self.huase:
            print("huase need to play: %s" % self.huase)
        else:
            print("huase need to play: Any")

        print("trick:%d"%self.trick)
        print("game state:%d"%self.game_state)
        print()

    def empty_seats(self):
        a = []
        for i in range(self.player_num):
            if self.player_state[i] == 0:
                a.append(i)
        return a

    def add_player(self, address, state, place, name):
        if state == 0 or place > self.player_num - 1 or place < 0:
            print("not a legal player\n")
            return False
        if self.player_state[place]:
            print("occupied\n")
            return False

        self.player_address[place] = address
        self.player_state[place] = state
        self.player_ready_new_trick = True
        self.player_names[place] = name
        return True

    def shuffle(self, start_place = 0):
        for i in self.player_state:
            if i == 0:
                print("there're empty place\n")
                return False
        self.game_state = 1
        self.star = start_place
        self.trick = 1
        self.trick_step = 0
        if self.player_num == 3:
            cards = ['S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8', 'S9', 'S10', 'SJ', 'SQ', 'SK', 'SA',
                     'H2', 'H3', 'H4', 'H5', 'H6', 'H7', 'H8', 'H9', 'H10', 'HJ', 'HQ', 'HK', 'HA',
                     'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'DJ', 'DQ', 'DK', 'DA',
                     'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9', 'C10', 'CJ', 'CQ', 'CK', 'CA', 'JG', 'JP']
            random.shuffle(cards)
            for i in range(3):
                self.player_cards[i] = cards[18*i:18*(i+1)]
                self.player_cards[i].sort(key = cards_order)
        else:
            cards = ['S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8', 'S9', 'S10', 'SJ', 'SQ', 'SK', 'SA',
                     'H2', 'H3', 'H4', 'H5', 'H6', 'H7', 'H8', 'H9', 'H10', 'HJ', 'HQ', 'HK', 'HA',
                     'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'DJ', 'DQ', 'DK', 'DA',
                     'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9', 'C10', 'CJ', 'CQ', 'CK', 'CA']
            random.shuffle(cards)
            for i in range(4):
                self.player_cards[i] = cards[13 * i:13 * (i + 1)]
                self.player_cards[i].sort(key=cards_order)
        return True

    def legal(self,place,card):
        if self.star != place:
            return False
        if card not in self.player_cards[place]:
            return False
        if self.huase:
            if self.huase != card[0] and not {self.huase,card[0]} == {'J','H'}:
                for i in self.player_cards[place]:
                    if i[0] == self.huase or {self.huase,i[0]} == {'J','H'}:
                        return False
            return True
        return True

    def play_card(self,place,card):
        if self.game_state == 0:
            return False
        if not self.legal(place,card):
            return False
        self.player_cards[place].remove(card)
        self.cards_on_table.append([place,card])
        if self.star == 0:
            self.huase = card[0]
        self.star += 1
        self.star %= self.player_num

        self.trick_step += 1
        return True

    def judge_winner(self):
        soc = -65535
        loc = -1
        for i, card in self.cards_on_table:
            if (card[0] == self.huase or {card[0],self.huase} == {'H','J'}) and ORDER_DICT2[card[1]] > soc:
                loc = i
                soc = ORDER_DICT2[card[1]]
                # log("%s is larger"%(card))
        return loc

    def calc_score_i(self,place):
        score = 0
        has_score_flag = False
        c10_flag = False
        heart_count = 0
        # calc points
        for i in self.player_collect[place]:
            if i == "C10":
                c10_flag = True
            else:
                score += SCORE_DICT[i]
                has_score_flag = True
            if i.startswith('H') or i.startswith('J'):
                heart_count += 1
        # check whole Hearts
        if (self.player_num == 3) and heart_count == 15:
            score += 660
        if (self.player_num == 4) and heart_count == 13:
            score += 400
        # times two
        if c10_flag == True:
            if has_score_flag == False:
                score += 50
            else:
                score *= 2
        return score

    def end_trick(self):
        if self.trick_step != self.player_num:
            return False

        self.winner = self.judge_winner()
        self.star = self.winner
        for _, cd in self.cards_on_table:
            if cd in SCORE_DICT:
                self.player_collect[self.winner].append(cd)

        self.last_trick_cards = copy.copy(self.cards_on_table)
        self.cards_on_table.clear()

        self.trick_step = 0
        self.trick += 1
        return True

    def ready_trick_end(self):
        if False in self.player_ready_trick_end:
            return False
        return True

    def trick_end_get(self):
        if False in self.player_trick_end_get:
            return False
        return True

    def start_place(self):
        return self.star - len(self.cards_on_table)

    def end_game(self):
        if (self.trick == 14 and self.player_num == 4) or (self.trick == 19 and self.player_num == 3):
            self.game_state = 0
            for i in range(self.player_num):
                self.player_score[i] = self.calc_score_i(i)
            return True
        return False

    def leave(self,place):
        self.game_state = 0
        self.player_state[place] = 0
        self.player_names[place] = ''
        self.player_address[place] = 0

MaxRoom = 100

class MyHTTPRequestHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        return

    def _set_headers(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()

    def do_HEAD(self):
        self._set_headers()

    def do_GET(self):
        log("%s from %s requesting %s" % (self.command, self.client_address, self.path))
        # self.headers contains many infos of client
        # self.path is the request path
        # self.rfile is the file to read from client
        # self.wfile is the file to write to response
        self._set_headers()

        recive_text = self.rfile.read(int(self.headers['content-length']))

        js_recive = json.loads(recive_text.decode())
        print(js_recive)

        cmd = js_recive["command"]

        rooms = self.server.rooms
        players = self.server.players

        def login():
            name = js_recive["user"]
            pwd = js_recive["user_pwd"]
            rob = js_recive["rob"]


            if name in players:
                error = "Same Name"
                reply = {"command": "error", "detail": error}
                reply_text = json.dumps(reply)
                reply_byte = reply_text.encode("utf8")
                self.wfile.write(reply_byte)
                return

            players[name] = Player(name,rob,self.client_address)
            reply = {"command": "login_reply", "success": True}
            self.wfile.write(json.dumps(reply).encode("utf8"))
            #print(players)
            return

        def findroom():
            ins = js_recive["instruction"]
            id_ = js_recive["roomid"]
            if ins[0] == 'T':
                # avoid conflict
                if id_ in rooms:
                    error = "room existed"
                    reply = {"command": "error", "detail": error}
                    self.wfile.write(json.dumps(reply).encode("utf8"))
                    return

                #create room and replay
                rooms[id_] = Room(id_,3)
                reply = {"command":"room_reply","roomid":id_,"success":True,"seats":rooms[id_].empty_seats()}
                self.wfile.write(json.dumps(reply).encode("utf8"))
            elif ins[0] == 'Q':
                # same as T
                if id_ in rooms:
                    error = "room existed"
                    reply = {"command": "error","detail": error}
                    self.wfile.write(json.dumps(reply).encode("utf8"))
                    return
                rooms[id_] = Room(id_,4)
                reply = {"command":"room_reply", "roomid":id_,"success":True,"seats":rooms[id_].empty_seats()}
                self.wfile.write(json.dumps(reply).encode("utf8"))
            elif ins[0] == 'A':
                n = ord(ins[1]) - ord('0')
                l = ord(ins[1]) - ord('0')
                if l <= 0 or n not in [3,4]:
                    error = "nonlegal ins"
                    reply = {"command": "error", "detail": error}
                    self.wfile.write(json.dumps(reply).encode("utf8"))
                    return

                if l != 5 or (l == 5 and n == 3):
                    # A45 is specific
                    if len(rooms) > 0:
                        for _,i in rooms.items():
                            # find empty enough room
                            if i.player_num == n:
                                eps = i.empty_seats()
                                if len(eps) >= l:
                                    id = i.id
                                    reply = {"command": "room_reply", "roomid": id, "success": True,
                                             "seats": rooms[id].empty_seats()}
                                    self.wfile.write(json.dumps(reply).encode("utf8"))
                                    return


                    for id in range(MaxRoom):
                        # if not find , retrun a new room
                        if id not in rooms:
                            rooms[id] = Room(id, n)
                            reply = {"command": "room_reply", "roomid": id, "success": True,
                                     "seats": rooms[id].empty_seats()}
                            self.wfile.write(json.dumps(reply).encode("utf8"))
                            return

                    # run  this line means room full
                    error = "room full"
                    reply = {"command": "error", "detail": error}
                    self.wfile.write(json.dumps(reply).encode("utf8"))
                    return

                else:
                    if len(rooms) > 0:
                        for _, i in rooms.items():
                            # find empty enough room
                            if i.player_num == n:
                                eps = i.empty_seats()
                                if (0 in eps and 2 in eps) or (1 in eps or 3 in eps):
                                    id = i.id
                                    reply = {"command": "room_reply", "roomid": id, "success": True,
                                             "seats":rooms[id].empty_seats()}
                                    self.wfile.write(json.dumps(reply).encode("utf8"))
                                    return


                    for id in range(MaxRoom):
                        # if not find , retrun a new room
                        if id not in rooms:
                            rooms[id] = Room(id, n)
                            reply = {"command": "room_reply", "roomid": id, "success": True,
                                     "seats": rooms[id].empty_seats()}
                            self.wfile.write(json.dumps(reply).encode("utf8"))
                            return

                    # run  this line means room full
                    error = "room full"
                    reply = {"command": "error", "detail": error}
                    self.wfile.write(json.dumps(reply).encode("utf8"))
                    return
            elif ins == 'F':
                if id_ in rooms:
                    reply = {"command": "room_reply", "roomid": id_, "success": True,
                             "seats": rooms[id_].empty_seats()}
                    self.wfile.write(json.dumps(reply).encode("utf8"))
                    return
                else:
                    error = "room not exist"
                    reply = {"command": "error", "detail": error}
                    self.wfile.write(json.dumps(reply).encode("utf8"))
            else:
                error = "nonlegal ins"
                reply = {"command": "error", "detail": error}
                self.wfile.write(json.dumps(reply).encode("utf8"))
                return

        def sitdown():
            id = js_recive["roomid"]
            pl = js_recive["place"]
            name = js_recive["user"]
            if name not in players:
                error = "hasn't loggin"
                reply = {"command": "error", "detail": error}
                self.wfile.write(json.dumps(reply).encode("utf8"))
                return

            rm = rooms[id]
            if pl >= rm.player_num or pl < 0:
                error = "wrong place"
                reply = {"command": "error", "detail": error}
                self.wfile.write(json.dumps(reply).encode("utf8"))
                return

            if rm.player_state[pl]:
                error = "already has a person"
                reply = {"command": "error", "detail": error}
                self.wfile.write(json.dumps(reply).encode("utf8"))
                return

            player_ = players[name]
            if player_.id != -1:
                error = "you're already in a room"
                reply = {"command": "error", "detail": error}
                self.wfile.write(json.dumps(reply).encode("utf8"))
                return

            if player_.rob:
                st = 2
            else:
                st = 1

            rm.add_player(player_.client,st,pl,name)
            player_.id = id
            player_.place = pl

            reply = {"command": "sitdown_reply", "room":id,"place":pl,"players":rm.player_names}
            self.wfile.write(json.dumps(reply).encode("utf8"))

        def askstart():
            player_name = js_recive["user"]
            if player_name not in players:
                error = "login first"
                reply = {"command": "error", "detail": error}
                self.wfile.write(json.dumps(reply).encode("utf8"))
                return
            player_instance = players[player_name]
            player_place = player_instance.place
            rm = rooms[player_instance.id]

            if len(rm.empty_seats()) > 0:
                reply = {"command":"start_reply_waiting", "players":rm.player_names}
                self.wfile.write(json.dumps(reply).encode("utf8"))
                return
            else:
                if not rm.game_state:
                    # always starts from 0
                    # TODO: start ramdomly or sequencily
                    start_pl = 0
                    rm.shuffle(start_pl)

                reply={"command":"start_reply_start", \
                       "players":rm.player_names,\
                       "start_place":rm.star,\
                       "cards":rm.player_cards[player_place]}
                self.wfile.write(json.dumps(reply).encode("utf8"))
                return

        def updatecard():
            player_name = js_recive["user"]
            if player_name not in players:
                error = "login first"
                reply = {"command": "error", "detail": error}
                self.wfile.write(json.dumps(reply).encode("utf8"))
                return
            player_instance = players[player_name]
            rm = rooms[player_instance.id]

            rm.__str__()

            if rm.end_game() or not rm.game_state:
                rm.game_state = 0
                reply = {"command": "update_card_reply_game_end", "score": rm.player_score, \
                         "collect": rm.player_collect}
                self.wfile.write(json.dumps(reply).encode("utf8"))
            else:
                reply = {"command": "update_card_reply", "cards_on_table": rm.cards_on_table, \
                         "start_place": rm.start_place(), "now_player": rm.star, "suit": rm.huase}
                self.wfile.write(json.dumps(reply).encode("utf8"))



        def playacard():
            player_name = js_recive["user"]
            if player_name not in players:
                error = "login first"
                reply = {"command": "error", "detail": error}
                self.wfile.write(json.dumps(reply).encode("utf8"))
                return
            player_instance = players[player_name]
            player_place = player_instance.place
            rm = rooms[player_instance.id]
            card = js_recive["card"]

            if not rm.game_state:
                error = "game not start"
                reply = {"command": "error", "detail": error}
                self.wfile.write(json.dumps(reply).encode("utf8"))
                return

            if rm.play_card(player_place,card):
                reply = {"command": "play_a_card_reply"}
                self.wfile.write(json.dumps(reply).encode("utf8"))
            else:
                error = "nonlegal choice"
                reply = {"command": "error", "detail": error}
                self.wfile.write(json.dumps(reply).encode("utf8"))
                return

        def asktrickend():
            player_name = js_recive["user"]
            if player_name not in players:
                error = "login first"
                reply = {"command": "error", "detail": error}
                self.wfile.write(json.dumps(reply).encode("utf8"))
                return
            player_instance = players[player_name]
            player_place = player_instance.place
            rm = rooms[player_instance.id]

            if not rm.game_state:
                error = "game not start"
                reply = {"command": "error", "detail": error}
                self.wfile.write(json.dumps(reply).encode("utf8"))
                return

            if rm.ready_trick_end():
                rm.end_trick()
                rm.player_trick_end_get = [False for i in range(rm.player_num)]
                reply = {"command":"ask_trick_end_reply","cards_on_table":rm.last_trick_cards,\
                         "start_player":rm.start_place(),"winner":rm.judge_winner(),"trick":rm.trick}
                self.wfile.write(json.dumps(reply).encode("utf8"))

            else:
                rm.player_ready_trick_end[player_place] = True
                print(rm.player_ready_trick_end)

                reply = {"command":"ask_trick_end_reply_waiting"}
                self.wfile.write(json.dumps(reply).encode("utf8"))

        def trickendget():
            player_name = js_recive["user"]
            if player_name not in players:
                error = "login first"
                reply = {"command": "error", "detail": error}
                self.wfile.write(json.dumps(reply).encode("utf8"))
                return
            player_instance = players[player_name]
            player_place = player_instance.place
            rm = rooms[player_instance.id]

            if not rm.game_state:
                error = "game not start"
                reply = {"command": "error", "detail": error}
                self.wfile.write(json.dumps(reply).encode("utf8"))
                return

            if rm.trick_end_get():
                rm.player_ready_trick_end = [False for i in range(rm.player_num)]
                reply = {"command":"trick_end_get_reply"}
                self.wfile.write(json.dumps(reply).encode("utf8"))

            else:
                rm.player_trick_end_get[player_place] = True
                reply = {"command":"trick_end_get_reply_waiting"}
                self.wfile.write(json.dumps(reply).encode("utf8"))


        switch_deal = {
            "user_login":login,
            "find_room":findroom,
            "sit_down":sitdown,
            "ask_start":askstart,
            "update_card":updatecard,
            "play_a_card":playacard,
            "ask_trick_end":asktrickend,
            "trick_end_get":trickendget,
        }
        switch_deal[cmd]()


        return 0

    def do_POST(self):
        log("%s from %s requesting %s" % (self.command, self.client_address, self.path))
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        self._set_headers()
        reply_byte = "got your post at %s" % (time.strftime("%y/%m/%d %H:%M:%S", time.localtime()),)
        reply_byte = reply_byte.encode("ascii")
        self.wfile.write(reply_byte)
        return 0


def run_server(port=20000):
    re_code = -1
    try:
        httpd = MyHTTPServer(('', port), MyHTTPRequestHandler)
        httpd.serve_forever()
    except KeyboardInterrupt:
        log("KeyboardInterrupt")
        re_code = 0
    except MyTimeoutException:
        log("normal timeout, but did not be catched", l=3)
        re_code = 1
    except:
        log("server run error!", l=3)
        re_code = 2
    finally:
        if "httpd" in locals().keys():
            httpd.server_close()
    log("quit run_server", l=2)
    return re_code


if __name__ == "__main__":
    run_server()

