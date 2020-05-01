server需要完成的工作包括模拟打牌，记录历史和计分，client是人或者机器人，注意一个client里面可能有多个机器人
协议主体一律采用json格式
client将把内容放在HTTPConnection.request(method, url, body)中的body发送，method为"Get"
client将通过HTTPConnection.getresponse()接受服务器发回来的内容
之后再根据不同的命令有不同的key和格式
目前定下的命令有

### 用户发给服务器
* {"command": "robot_login", "user":"CouCou", "password":"abcdefg", "number_of_robots": "4", "robot_name_list": alist, "room": roomid}
    代表有4个机器人想打牌，登陆时需要输入主人的用户名和密码，如果是两个机器人，要安排它们坐在对家
    alist是机器人的名字，是一个str列表
    roomid如果是'A'，则表明机器人愿意加入任何一个现存的房间

#* {"command": "user_login", "user":"name","user_pwd":"pwd","room":roomid}
#    roomid 是一个数字，或者为'T'或'Q'

* {"command": "mychoice", "robot_name": robotname, "card":"SQ","room":roomid}
    roomid 是数字哦
    如果是玩家自己在打牌robotname是"moi"("ich")

* {"command": "leave_room", "robot_name_list": alist, 'room':roomid}

* {"command": "ready_for_next", "robot_name_list": alist, 'room':roomid}
    所有机器人在这一轮训练完毕，已经准备好重新发牌再打一局

### 服务器发给单独用户
* {"command": 'loginsuc', "room":roomid,"your_loc":lst,"players":["player1_name","player2_name",...]}
  "your_loc"是坐的位置, 按加入顺序按0123分配, 列表的长度等于发过去的robot_name_list的长度，顺序也是一样，如果是玩家则长度为1
  "players"也按0123顺序排好
  登陆失败交给"error"命令处理

#* {"command":"new_player", "players":["player1_name","player2_name",...]}
#  "players"格式与login_suc中一样

* {"command":"shuffle", "cards":[["SA","H2","D3","C4",...],[...]]}
  S(Spade), H(Heart), D(Diamond), C(Club)表示黑红方梅
  A23456789JQK表示不同的牌
  "cards"中的每个元素是：["SA","H2","D3","C4",...]，排列的顺序与robot_name_list一致

* {"command":"tableupdate", 'this_trick':[...], 'trick_start':a number, 'which_round': a number}
  别人打牌出去以后需要告诉client牌桌更新了
  'which_round'代表这是打的第几轮了，从0到12（或从0到18）

#* {"command":"relative_history", "robot_name":robotname, "data":str, 'which_round': a number}
#  将所有历史发送给机器人robotname，格式如下：
#  相对历史是指将robotname作为0号玩家所看到的历史，其原本的格式是一个4*13*(4+52)维的01向量，robotname右边的玩家为1号玩家，依此类推
#  其第(i,j,k)号元素代表(若k>3)第i号玩家在第j轮是否打出了第k张牌。打出了为1，否则为0
#  52张牌的编码顺序为从0到51分别为's2','H3',...'HA','C2','C3',...'CA','D2','D3',...'DA','S2','S3',...'SA'
#  若k<=3,第(i,j,k)号元素代表第i号玩家在第j轮是不是第k(k=0,1,2)个打牌的，是为1，不是为0
#  将这个4*13*(4+52)的向量压平成2912维的01向量，在最前面再加上一个1(防止首位是0带来的丢失)，然后转化为十进制数，附在data后面发送

* {"command":"super_power","initial_cards":[[],[],...]}
  把所有隐藏的信息发给用户，用于训练机器人
  把所有玩家的手牌发过来，用绝对位置0123排序

* {"command":'yourturn', "robot_name":robotname, 'color':'S'}
  告诉client该你打牌了,并且返回应该打牌的用户的绝对位置 (用于区分不同的机器人)
  color是这一轮的花色，用'S','H','C','D', 或者是'A'

#* {"command":'got_yourchoice','your_remain':[[]]}
#  告诉用户获得了 mychoice

#* {"command":'got_leave_room','room':roomid}

* {"command":'trickend', "winner":0,"reward":["SQ","DJ",..]}

* {"command": 'game_end','final_reward':[0,0,0,50]}
  "scores"也按0123顺序排好

* {"command":'error', "detail":"blabla"}