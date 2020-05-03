import requests
import json
import urllib.request
import os

from http.client import HTTPConnection


class Agent:
    name = ""
    pwd = ""
    url = ""
    rob = False

    id = 0
    place = 0



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
        return json.loads(rep)
    def create_room(self,roomid,ins):
        conn = HTTPConnection(self.url)
        postdata = {"command": "find_room", "roomid": roomid, \
                        "instruction": ins}
        data = json.dumps(postdata).encode()
        headers = {'Content-type': "text/plain"}
        conn.request("GET", '/index.html', data, headers)
        rep = conn.getresponse().read().decode()
        return json.loads(rep)

    def sit_down(self,id,pl):
        conn = HTTPConnection(self.url)
        postdata = {"command": "sit_down", "user":self.name,"roomid": id, \
                    "place": pl}
        data = json.dumps(postdata).encode()
        headers = {'Content-type': "text/plain"}
        conn.request("GET", '/index.html', data, headers)
        rep = conn.getresponse().read().decode()
        if rep["command"] == "sitdown_reply":
            self.id = id
            self.place = pl
        return json.loads(rep)

    def play_a_card(self):

        pass
    def recive_information(self):
        pass
    def other_player_card(self):
        pass
    def leave(self):
        pass
    def join(self):
        pass


def test_post():
    shiju1 = Agent()
    rep = shiju1.login("shuju1","23333","0.0.0.0:20000",False)
    print(rep)

    shiju2 = Agent()
    rep = shiju2.login("shuju2", "23333", "0.0.0.0:20000", False)
    print(rep)

    shiju3 = Agent()
    rep = shiju3.login("shuju3", "23333", "0.0.0.0:20000", False)
    print(rep)

    rmid =12
    rep = shiju1.create_room(rmid,'T')
    print(rep)

    rep = shiju1.sit_down(rmid,0)
    print(rep)

    rep = shiju2.sit_down(rmid,2)
    print(rep)

    rep = shiju3.sit_down(rmid,1)
    print(rep)






if __name__ == "__main__":
    # post_info()
    # psot_info_3()
    test_post()

