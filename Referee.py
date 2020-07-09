#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# --------------------------------------------------------
# 一个拱猪游戏的服务器
# --------------------------------------------------------

# 先定义一个 log 函数
# time sys traceback math 都在 python 标准库中, 不需要特地安装
import time, sys, traceback, math, copy
import Client

robots_family = []
robot_list = copy.deepcopy(Client.robot_list)

hosturl = 'http://127.0.0.1'
hostport = 5000

robots_family = [Client.RobotFamily(hosturl + ':%d'%hostport,rb) for rb in robot_list]

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


import random, eventlet, socketio, copy, json, threading

sio = socketio.Server(logger=False)
app = socketio.WSGIApp(sio,
                       static_files={'/': 'index.html', '/favicon.ico': 'logo.png', '/asset': 'asset', '/src': 'src'})

users = {}  # a dict that map username to sid
player_in_room = {}  # a dict that map username to room
rooms = {0: {"players": [], "game_mode": 3}}  # a dict contains all msg of a game, looks like
# {
#    roomid(int):{
#        "players":["a","b",..],
#        "game_mode":3(or 4),
#        "cards_remain":[set,set,set,set],
#        "cards_initial":[set,set,set,set],
#        "cards_played":[['S2','S3','S4','S5'],...],
#        "trick_start":[0,0,2...],
#        "scores":[[...],[...],[...],[...]]
#        "state":unstart, playing, end
#    }
# }
roomid_plus_lock = threading.Lock()


def print_room(room):
    s = ["trick_start: %s" % (room["trick_start"],),
         "cards_remain: %s" % (room["cards_remain"]),
         "cards_played: %s" % (room['cards_played'],),
         "scores: %s" % (room['scores'],),
         # "cards_initial: %s"%(room['cards_initial'])
         ]
    log("\n".join(s))


def get_loc(user, thisroom):
    for loc, name in enumerate(thisroom["players"]):
        if name == user:
            break
    return loc


SCORE_DICT = {'SQ': -100, 'DJ': 100, 'C10': 0,
              'H2': 0, 'H3': 0, 'H4': 0, 'H5': -10, 'H6': -10, 'H7': -10, 'H8': -10, 'H9': -10, 'H10': -10,
              'HJ': -20, 'HQ': -30, 'HK': -40, 'HA': -50, 'JP': -60, 'JG': -70}


def update_scores(winner, thisroom):
    for card in thisroom['cards_played'][-1]:
        if card in SCORE_DICT:
            thisroom['scores'][winner].append(card)


def calc_score(l):
    s = 0
    has_score_flag = False
    c10_flag = False
    for i in l:
        if i == "C10":
            c10_flag = True
        else:
            s += SCORE_DICT[i]
            has_score_flag = True
    if c10_flag == True:
        if has_score_flag == False:
            s += 50
        else:
            s *= 2
    return s


def sendmsg(cmd, dict, name=None, sid=None, roomid=None):
    """name 是发给用户, sid 是发给sid, room 是房间广播"""
    log("sending %s: %s to (name)%s,(sid)%s,(roomid)%s" % (cmd, dict, name, sid, roomid))
    for retry_num in range(2):  # default not retry
        try:
            # 以一定的概率触发异常以模拟网络不好，前端程序员会感谢我的
            if random.random() > 0.98:
                raise Exception("Simulate Network error")
            # TODO: 文档上说默认是群发，需要加这个room关键字才是单发，但我觉得不管用？需要测试一下这个函数是否正常
            if name != None:
                sio.emit(cmd, json.dumps(dict), room=users[name])
            elif sid != None:
                sio.emit(cmd, json.dumps(dict), room=sid)
            elif roomid != None:
                for user in rooms[roomid]["players"]:
                    dict['name'] = user
                    sendmsg(cmd, dict, name=user)
            break
        except:
            log("unknown error, retry_num: %d" % (retry_num), l=3)
    else:
        log("send failed", l=2)
        return 2
    return 0


ORDER_DICT1 = {'S': -300, 'H': -200, 'D': -100, 'C': 0, 'J': -200}
ORDER_DICT2 = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '1': 10, 'J': 11, 'Q': 12, 'K': 13,
               'A': 14, 'P': 15, 'G': 16}


def cards_order(card):
    return ORDER_DICT1[card[0]] + ORDER_DICT2[card[1]]


def judge_winner(cards):
    soc = -65535
    for i, card in enumerate(cards):
        if card[0] == cards[0][0] and ORDER_DICT2[card[1]] > soc:
            loc = i
            soc = ORDER_DICT2[card[1]]
            # log("%s is larger"%(card))
    return loc


def shuffle(roomid):
    """will init cards_remain,cards_played,cards_initial,trick_start"""
    try:
        assert roomid in rooms, "roomid: %s not in rooms" % (roomid)
        thisroom = rooms[roomid]
        assert "players" in thisroom
        assert "game_mode" in thisroom
        assert thisroom["game_mode"] == len(thisroom["players"])
    except:
        log("", l=3)
        return 1
    if thisroom["game_mode"] == 3:
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
    if thisroom["game_mode"] == 3:
        thisroom["cards_initial"] = [cards[0:18], cards[18:36], cards[36:54]]
        thisroom["scores"] = [[], [], []]
    else:
        thisroom["cards_initial"] = [cards[0:13], cards[13:26], cards[26:39], cards[39:52]]
        thisroom["scores"] = [[], [], [], []]
    for i in thisroom['cards_initial']:
        i.sort(key=cards_order)
    thisroom["cards_remain"] = copy.deepcopy(thisroom["cards_initial"])
    thisroom["cards_played"] = []
    thisroom["trick_start"] = []
    # 客户端返回
    fail_times = 0
    for i in range(thisroom["game_mode"]):
        temp = sendmsg("shuffle", {"name": thisroom["players"][i], \
                                   "cards": thisroom["cards_initial"][i]}, name=thisroom["players"][i])
        if temp != 0:
            fail_times += 1
    if fail_times != 0:
        log("fail_times: %d" % (fail_times,), l=2)
        # return 2
    else:
        pass
        # return 0
    # thisroom["trick_start"].append(1)
    thisroom["trick_start"].append(random.randint(0, thisroom["game_mode"] - 1))
    thisroom["cards_played"].append([])
    sendmsg('yourturn', {'name': thisroom['players'][thisroom["trick_start"][-1]], \
                         'color': 'A'}, name=thisroom['players'][thisroom["trick_start"][-1]])


def checkpwd(username, user_pwd):
    d_user_pwd = {'Sun': '123456', 'CouCou': '123456', 'DaShu': '123456',
                  'BazingA': '123456', 'YaoYao': '123456', 'LuRenJia': '123456', 'LuRenYi': '123456'}
    if (username in d_user_pwd):  # and (d_user_pwd[username]==user_pwd):
        return 0
    else:
        return 1


@sio.event
def connect(sid, environ):
    # environ 基本就是 headers 加上一些杂七杂八的东西
    # log("environ: %s"%(environ))
    log("sid %s connect" % (sid))


@sio.event
def disconnect(sid):
    log("sid %s disconnect" % (sid))


def strip_data(sid, data):
    """
    输入字符串的json, 
    验证密码和加密, 验证有必要元素
    之后解析成字典
    顺便更新 users 字典"""
    try:
        data = json.loads(data)
    except:
        log("parse data error: %s" % (data), l=2)
        sendmsg('error', {'detail': 'json.load(data) error'}, sid=sid)
        return 1
    try:
        assert 'user' in data
        assert 'room' in data
    except:
        log('data lack element: %s' % (data), l=2)
        sendmsg('error', {'detail': 'data lack element'}, sid=sid)
        return 2
    users[data['user']] = sid
    return data


GAME_MODE_DICT = {'T': 3, 'Q': 4}


@sio.on('login')
def login(sid, data):
    data = strip_data(sid, data)
    if isinstance(data, int):
        return
    log("get login: %s" % (data))
    if data['user'] in player_in_room and player_in_room[data['user']] > 0:
        sendmsg('error', {'name': data['user'], 'detail': 'you already in room'}, sid=sid)
        return 1

    if data["room"] in ('T', 'Q'):
        roomid_plus_lock.acquire()
        try:
            roomid = max([i for i in rooms.keys()]) + 1
            thisroom = {"players": [data['user'], ], 'game_mode': GAME_MODE_DICT[data["room"]]}
            rooms[roomid]["players"]
            player_in_room[data['user']] = roomid
            sendmsg("loginsuc", {"name": data['user'],
                                 "room_id": roomid, "your_loc": 0, "players": thisroom["players"]}, sid=sid)
        except:
            log("", l=3)
            return 2
        finally:
            roomid_plus_lock.release()
    elif data["room"] in rooms:
        roomid = data["room"]
        thisroom = rooms[roomid]
        if data['user'] not in thisroom["players"]:
            your_loc = len(thisroom["players"])
            thisroom["players"].append(data['user'])
        else:
            your_loc = get_loc(data['user'], thisroom)
        player_in_room[data['user']] = roomid
        sendmsg("loginsuc", {"name": data['user'], \
                             "room": roomid, "your_loc": your_loc, "players": thisroom["players"]}, sid=sid)
        sendmsg('new_player', {"players": thisroom["players"]}, roomid=roomid)

        thisroom['state'] = 'playing'
        # roomid's name is added in sendmsg

        if len(thisroom['players']) == thisroom['game_mode'] and "cards_initial" not in thisroom:
            log("all members are ready, shuffling...")
            shuffle(data['room'])
    else:
        sendmsg('error', {'name': data['user'], 'detail': 'room %d not exist' % (data['room'])}, sid=sid)
        return 3
    return 0


@sio.on('leave_room')
def leave_room(sid, data):
    data = strip_data(sid, data)
    if isinstance(data, int):
        return
    user = data['user']
    roomid = data['room']
    thisroom = rooms[roomid]
    players = thisroom['players']
    try:
        loc = players.index(user)
        players.pop(loc)
        sendmsg('got_leave_room', {'name': user, 'room': roomid}, sid=sid)

        if rooms[roomid]['state'] == 'playing':
            sendmsg('interrupt_game_end', {'detail': '%s leave the room' % (user)}, sid=sid)
        sendmsg('new_player', {"players": thisroom["players"]}, roomid=roomid)

    except:
        sendmsg('error', {'name': user, 'detail': 'you are not in room %s' % (roomid)}, sid=sid)

    if len(rooms[roomid]['players']) == 0:
        rooms.pop(roomid)


@sio.on('mychoice')
def userchoice(sid, data):
    data = strip_data(sid, data)
    if isinstance(data, int):
        return
    log("get choice: %s" % (data))
    roomid = data['room']
    user = data['user']
    try:
        card = data['card']
        thisroom = rooms[roomid]
        user_loc = get_loc(user, thisroom)
        game_mode = thisroom["game_mode"]
    except:
        log("", l=3)
        sendmsg('error', {'detail': 'error'}, sid=sid)
        return 5
    # 判断出牌是否合法
    if user_loc != (thisroom['trick_start'][-1] + len(thisroom['cards_played'][-1])) % (game_mode):
        sendmsg('error', {'name': user, 'detail': 'not your turn'}, sid=sid)
        return 3
    if card not in thisroom["cards_remain"][user_loc]:
        sendmsg('error', {'name': user, 'detail': 'not your card'}, sid=sid)
        return 1
    if len(thisroom["cards_played"][-1]) == 0:
        # the first player
        pass
    elif card[0] == thisroom["cards_played"][-1][0][0]:
        # the same color
        pass
    elif all([i[0] != thisroom["cards_played"][-1][0][0] for i in thisroom["cards_remain"][user_loc]]):
        # do not have this color
        pass
    else:
        sendmsg('error', {'name': user, 'detail': 'illegal choice'}, sid=sid)
        if len(thisroom['cards_played'][-1]) == 0:
            sendmsg('yourturn', {'name': user, 'color': 'A'}, sid=sid)
        else:
            sendmsg('yourturn', {'name': user, 'color': thisroom['cards_played'][-1][0][0]}, sid=sid)
        return 2
    # 更新数据结构
    for i, c in enumerate(thisroom["cards_remain"][user_loc]):
        if c == card:
            thisroom["cards_remain"][user_loc].pop(i)
    thisroom["cards_played"][-1].append(card)
    sendmsg('got_yourchoice', {'name': user, 'your_remain': thisroom["cards_remain"][user_loc]}, sid=sid)
    sendmsg('tableupdate', {'this_trick': thisroom["cards_played"][-1], 'trick_start': thisroom['trick_start'][-1]},
            roomid=roomid)
    # 下一张牌
    if len(thisroom["cards_played"][-1]) < game_mode:
        next_loc = (user_loc + 1) % (game_mode)
        sendmsg('yourturn', {'name': thisroom['players'][next_loc], \
                             'color': thisroom['cards_played'][-1][0][0]}, name=thisroom['players'][next_loc])
    elif len(thisroom["cards_played"][-1]) == game_mode:
        winner = (judge_winner(thisroom["cards_played"][-1]) + thisroom["trick_start"][-1]) % (game_mode)
        update_scores(winner, thisroom)
        sendmsg('trickend', {'winner': winner, 'scores': thisroom['scores']}, roomid=roomid)
        # 下一墩
        if len(thisroom["cards_remain"][0]) > 0:
            thisroom['trick_start'].append(winner)
            thisroom['cards_played'].append([])
            sendmsg('yourturn', {'name': thisroom["players"][winner], \
                                 'color': 'A'}, name=thisroom["players"][winner])
        else:
            thisroom['scores_num'] = [calc_score(i) for i in thisroom['scores']]
            log("game end: %s" % (thisroom))
            time.sleep(1)
            sendmsg('game_end', {'scores': thisroom['scores'], 'scores_num': thisroom['scores_num']}, roomid=roomid)

            #clear all info in this room

    else:
        log("error", l=2)

    return 0

@sio.on('stay_in_this_room')
def stay_in_this_room(sid,data):
    data = strip_data(sid,data)

@sio.on('add_new_robot')
def add_new_robot(sid,data):
    data = strip_data(sid,data)
    log("get add robot requests: %s" % (data))






def test_login_and_shuffle():
    login(1, json.dumps({'user': 'Sun', 'user_pwd': '123456', 'room': 'T'}))
    login(2, json.dumps({'user': 'CouCou', 'user_pwd': '123456', 'room': 1}))
    login(3, json.dumps({'user': 'DaShu', 'user_pwd': '123456', 'room': 1}))
    log("users: %s" % (users))
    log("rooms: %s" % (rooms))


def test_userchoice():
    import itertools
    login(1, json.dumps({'user': 'Sun', 'user_pwd': '123456', 'room': 'T'}))
    login(2, json.dumps({'user': 'CouCou', 'user_pwd': '123456', 'room': 1}))
    login(3, json.dumps({'user': 'DaShu', 'user_pwd': '123456', 'room': 1}))
    log("users: %s" % (users))
    print_room(rooms[1])
    for i, user in itertools.product(range(30), ("Sun", "CouCou", "DaShu")):
        card = input("input card choice for %s: " % (user))
        userchoice("%s's id" % (user), json.dumps({"user": user, "card": card, "room": 1}))
        try:
            print_room(rooms[1])
        except KeyError:
            break


def test_get_loc():
    login(1, json.dumps({'user': 'Sun', 'user_pwd': '123456', 'room': 'T'}))
    login(2, json.dumps({'user': 'CouCou', 'user_pwd': '123456', 'room': 1}))
    log("users: %s" % (users))
    log("rooms: %s" % (rooms))
    thisroom = rooms[1]
    log(get_loc('Sun', thisroom))
    log(get_loc('CouCou', thisroom))


def test_judge_winner():
    log(judge_winner(['S2', 'S3', 'S4', 'CA', 'S5']))


def test_calc_score():
    log(calc_score(['JG', 'SQ']))
    log(calc_score(['C10']))
    log(calc_score(['C10', 'H2']))
    log(calc_score(['DJ', 'C10']))


def run_forever():
    try:
        eventlet.wsgi.server(eventlet.listen(('', 5000)), app)
    except:
        log("unknown error", l=3)


if __name__ == "__main__":
    # test_judge_winner() #pass
    # test_get_loc() #pass
    # test_calc_score() #pass
    # test_login_and_shuffle() #pass
    # test_userchoice()
    run_forever()

