server需要完成的工作包括模拟打牌，记录历史和计分，client是人或者机器人，注意一个client里面可能有多个机器人
协议主体一律采用json格式
client将把内容放在HTTPConnection.request(method, url, body)中的body发送，method为"Get"
client将通过HTTPConnection.getresponse()接受服务器发回来的内容
之后再根据不同的命令有不同的key和格式
目前定下的命令有

### 用户发给服务器

* {"command": "user_login", "user":"name","user_pwd":"pwd","robot":true}


* {"command": "find_room","room":roomid,"instruction":'T'}
    roomid 是一个数字，instruction或者为'T'或'Q'（创建房间）,
'A'(Any) 'Ani',n代表几人游戏，i代表要求至少i个空位,'A45'代表剩余空位为[0,2] or [1,3]
'F' 代表询问房间是否存在

*{"command":"sit_down","user":name,"roomid":id,"place":0}
    server 返回可用位置，玩家选择位置place坐下。玩家需自己保存place。

*{"command":"ask_start","user":name}
    询问server游戏是否开始

*{"command":"update_card","user":name}
    打牌时询问更新

* {"command": "play_a_card", "user": name, "card":"SQ"}
    place 代表几号位置

*{"command":"ask_trick_end","user":name}

*{"command":"trick_end_get","user":name}

* {"command": "leave_room", "user": name, 'room':roomid}
    代表name离开啦

* {"command": "ready_for_next", "user":name, 'room':roomid}
   name希望再打一轮

*{"command":"give_up","user":name,'room':roomid}
    name希望认输

### 服务器发给单独用户
* {"command":"login_reply","success":true}

* {"command":"room_reply","roomid":id,"success":true,"seats":[avalible_seat1,...]}
 用户申请加入某一房间，服务器返回是否成功加入，如果成功，seats代表当前房间可用位置


* {"command": 'sitdown_reply', "room":roomid,"place":lst,"players":["player1_name","player2_name",...]}
  "your_loc"是坐的位置, 按加入顺序按0123分配, 列表的长度等于发过去的robot_name_list的长度，顺序也是一样，如果是玩家则长度为1
  "players"也按0123顺序排好
  登陆失败交给"error"命令处理

#* {"command":"new_player", "players":["player1_name","player2_name",...]}
#  "players"格式与login_suc中一样
* {"command":"start_reply_waiting", "players":["player1_name","player2_name",...]}
未开始比赛，其他位置上的人

* {"command":"start_reply_start", "players":["player1_name","player2_name",...],"start_place":place,"cards":["SA","H2","D3","C4",...]}
  如果开始了，返回cards以及由谁开始打
  S(Spade), H(Heart), D(Diamond), C(Club)表示黑红方梅
  A23456789JQK表示不同的牌

*{"command":"update_card_reply","cards_on_table":[card1,card2,...],"start_place":place, "now_player":pl,"suit":st}
*{"command":"update_card_reply_game_end","scores":[sc1,sc2,...],"collect":[card1,card2...]}
*{"command":"play_a_card_reply"}

*{"command":"ask_trick_end_reply","cards_on_table":[card1,card2,...],"start_player":st_pl,"winner":wr,"trick":trick}
*{"command":"ask_trick_end_reply_waiting"}

*{"command":"trick_end_get_reply"}
*{"command":"trick_end_get_reply_waiting"}


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

#* {"command":'got_yourchoice','your_remain':[[]]}
#  告诉用户获得了 mychoice

#* {"command":'got_leave_room','room':roomid}

* {"command":'error', "detail":"blabla"}
