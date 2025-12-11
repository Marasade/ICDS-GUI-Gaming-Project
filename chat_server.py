"""
Created on Tue Jul 22 00:47:05 2014

@author: selina,Yirui
"""

import time
import socket
import select
import sys
import string
import indexer
import json
import pickle as pkl
from chat_utils import *
import chat_group as grp

class Server:
    def __init__(self):
        self.new_clients = [] #list of new sockets of which the user id is not known
        self.logged_name2sock = {} #dictionary mapping username to socket
        self.logged_sock2name = {} # dict mapping socket to user name
        self.all_sockets = []
        self.group = grp.Group()
        #start server
        self.server=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(SERVER)
        self.server.listen(5)
        self.all_sockets.append(self.server)
        #initialize past chat indices
        self.indices={}


        ## Game matchmaking
        self.waiting_players = []  # 等待匹配的玩家列表
        self.active_games = {}     # {player_socket: game_info}
        self.leaderboard = {}      # {player_name: score}
        self.boards = {}         # 记录每个玩家对应的棋盘列表
        self.player_symbols = {} # 记录每个玩家是 X 还是 O


        # sonnet
        # self.sonnet_f = open('AllSonnets.txt.idx', 'rb')
        # self.sonnet = pkl.load(self.sonnet_f)
        # self.sonnet_f.close()
        self.sonnet = indexer.PIndex("AllSonnets.txt")
    def new_client(self, sock):
        #add to all sockets and to new clients
        print('new client...')
        sock.setblocking(0)
        self.new_clients.append(sock)
        self.all_sockets.append(sock)

    def login(self, sock):
        #read the msg that should have login code plus username
        try:
            msg = json.loads(myrecv(sock))
            print("login:", msg)
            if len(msg) > 0:

                if msg["action"] == "login":
                    name = msg["name"]
                    
                    if self.group.is_member(name) != True:
                        #move socket from new clients list to logged clients
                        self.new_clients.remove(sock)
                        #add into the name to sock mapping
                        self.logged_name2sock[name] = sock
                        self.logged_sock2name[sock] = name
                        #load chat history of that user
                        if name not in self.indices.keys():
                            try:
                                self.indices[name]=pkl.load(open(name+'.idx','rb'))
                            except IOError: #chat index does not exist, then create one
                                self.indices[name] = indexer.Index(name)
                        print(name + ' logged in')
                        self.group.join(name)
                        mysend(sock, json.dumps({"action":"login", "status":"ok"}))
                    else: #a client under this name has already logged in
                        mysend(sock, json.dumps({"action":"login", "status":"duplicate"}))
                        print(name + ' duplicate login attempt')
                else:
                    print ('wrong code received')
            else: #client died unexpectedly
                self.logout(sock)
        except:
            self.all_sockets.remove(sock)

    def logout(self, sock):
        #remove sock from all lists
        name = self.logged_sock2name[sock]
        pkl.dump(self.indices[name], open(name + '.idx','wb'))
        del self.indices[name]
        del self.logged_name2sock[name]
        del self.logged_sock2name[sock]
        self.all_sockets.remove(sock)
        self.group.leave(name)
        sock.close()

#==============================================================================
# main command switchboard
#==============================================================================
    def handle_msg(self, from_sock):
        #read msg code
        msg = myrecv(from_sock)
        if len(msg) > 0:
            try:
                msg = json.loads(msg)
                print(f"[SERVER] Received: {msg.get('action')}")  # 调试
            except:
                print("[SERVER] Failed to parse JSON")
                return
#==============================================================================
# handle connect request
#==============================================================================
              # 游戏匹配请求
            if msg["action"] == "find_match":
                self.handle_find_match(from_sock,msg)
                return
            
            # 游戏移动
            elif msg["action"] == "game_move":
                self.handle_game_move(from_sock, msg)
                return
            
            # 提交分数
            elif msg["action"] == "submit_score":
                self.handle_submit_score(from_sock, msg)
                return
            
            elif msg["action"] == "connect":
                to_name = msg["target"]
                from_name = self.logged_sock2name[from_sock]
                if to_name == from_name:
                    msg = json.dumps({"action":"connect", "status":"self"})
                # connect to the peer
                elif self.group.is_member(to_name):
                    to_sock = self.logged_name2sock[to_name]
                    self.group.connect(from_name, to_name)
                    the_guys = self.group.list_me(from_name)
                    msg = json.dumps({"action":"connect", "status":"success"})
                    for g in the_guys[1:]:
                        to_sock = self.logged_name2sock[g]
                        mysend(to_sock, json.dumps({"action":"connect", "status":"request", "from":from_name}))
                else:
                    msg = json.dumps({"action":"connect", "status":"no-user"})
                mysend(from_sock, msg)
#==============================================================================
# handle messeage exchange: one peer for now. will need multicast later
#==============================================================================
            elif msg["action"] == "exchange":
                from_name = self.logged_sock2name[from_sock]
                the_guys = self.group.list_me(from_name)
                #said = msg["from"]+msg["message"]
                said2 = text_proc(msg["message"], from_name)
                self.indices[from_name].add_msg_and_index(said2)
                for g in the_guys[1:]:
                    to_sock = self.logged_name2sock[g]
                    self.indices[g].add_msg_and_index(said2)
                    mysend(to_sock, json.dumps({"action":"exchange", "from":msg["from"], "message":msg["message"]}))
#==============================================================================
#                 listing available peers
#==============================================================================
            elif msg["action"] == "list":
                from_name = self.logged_sock2name[from_sock]
                msg = self.group.list_all()
                mysend(from_sock, json.dumps({"action":"list", "results":msg}))
#==============================================================================
#             retrieve a sonnet
#==============================================================================
            elif msg["action"] == "poem":
                poem_indx = int(msg["target"])
                from_name = self.logged_sock2name[from_sock]
                print(from_name + ' asks for ', poem_indx)
                poem = self.sonnet.get_poem(poem_indx)
                poem = '\n'.join(poem).strip()
                print('here:\n', poem)
                mysend(from_sock, json.dumps({"action":"poem", "results":poem}))
#==============================================================================
#                 time
#==============================================================================
            elif msg["action"] == "time":
                ctime = time.strftime('%d.%m.%y,%H:%M', time.localtime())
                mysend(from_sock, json.dumps({"action":"time", "results":ctime}))
#==============================================================================
#                 search
#==============================================================================
            elif msg["action"] == "search":
                term = msg["target"]
                from_name = self.logged_sock2name[from_sock]
                print('search for ' + from_name + ' for ' + term)
                # search_rslt = (self.indices[from_name].search(term))
                search_rslt = '\n'.join([x[-1] for x in self.indices[from_name].search(term)])
                print('server side search: ' + search_rslt)
                mysend(from_sock, json.dumps({"action":"search", "results":search_rslt}))
#==============================================================================
# the "from" guy has had enough (talking to "to")!
#==============================================================================
            elif msg["action"] == "disconnect":
                from_name = self.logged_sock2name[from_sock]
                the_guys = self.group.list_me(from_name)
                self.group.disconnect(from_name)
                the_guys.remove(from_name)
                if len(the_guys) == 1:  # only one left
                    g = the_guys.pop()
                    to_sock = self.logged_name2sock[g]
                    mysend(to_sock, json.dumps({"action":"disconnect"}))
#==============================================================================
#                 the "from" guy really, really has had enough
#==============================================================================

        else:
            #client died unexpectedly
            self.logout(from_sock)

#==============================================================================
# main loop, loops *forever*
#==============================================================================
    def run(self):
        print ('starting server...')
        while(1):
           read,write,error=select.select(self.all_sockets,[],[])
           print('checking logged clients..')
           for logc in list(self.logged_name2sock.values()):
               if logc in read:
                   self.handle_msg(logc)
           print('checking new clients..')
           for newc in self.new_clients[:]:
               if newc in read:
                   self.login(newc)
           print('checking for new connections..')
           if self.server in read :
               #new client request
               sock, address=self.server.accept()
               self.new_client(sock)

##。
    def handle_find_match(self, client_socket, data):
        """处理匹配请求"""
        player_name = self.logged_sock2name.get(client_socket)
        
        if not player_name:
            return
        
        # 如果已经有人在等待，配对成功
        if self.waiting_players:
            opponent_socket = self.waiting_players.pop(0)
            opponent_name = self.logged_sock2name[opponent_socket]
            shared_board = [""] * 9 
            self.boards[client_socket] = shared_board
            self.boards[opponent_socket] = shared_board
            
            # 记录符号
            self.player_symbols[opponent_socket] = "X" # 先来的是 X
            self.player_symbols[client_socket] = "O"   # 后来的是 O
            
            # 通知两个玩家匹配成功
            # 第一个玩家是 X
            msg1 = json.dumps({
                "game_action": "match_found",
                "opponent": player_name,
                "your_symbol": "X"
            })
            mysend(opponent_socket, msg1)
            
            # 第二个玩家是 O
            msg2 = json.dumps({
                "game_action": "match_found",
                "opponent": opponent_name,
                "your_symbol": "O"
            })
            mysend(client_socket, msg2)
            
            # 记录游戏状态
            self.active_games[opponent_socket] = client_socket
            self.active_games[client_socket] = opponent_socket
        else:
            # 加入等待队列
            self.waiting_players.append(client_socket)

    def handle_game_move(self, client_socket, data):
        if client_socket not in self.active_games:
            return
    
        opponent_socket = self.active_games[client_socket]
        move = data.get("move")
    
        if move is None:
            return
        
        # 1. 更新服务器端的棋盘记录
        if client_socket in self.boards:
            board = self.boards[client_socket]
            symbol = self.player_symbols[client_socket]
            
            # 检查位置是否已被占用
            if board[move] != "":
                return
                
            board[move] = symbol  # 在棋盘上记录这一步
            
            # 2. 检查胜负
            winner = self.check_winner(board)
            if winner:
                # 发送游戏结束消息
                msg = json.dumps({
                    "game_action": "game_over",
                    "result": "win",
                    "winner": winner
                })
                mysend(client_socket, msg)
                mysend(opponent_socket, msg)
                self.cleanup_game(client_socket, opponent_socket)
                return

            # 3. 检查平局 (棋盘满了但没人赢)
            if "" not in board:
                msg = json.dumps({
                    "game_action": "game_over",
                    "result": "tie",
                    "winner": None
                })
                mysend(client_socket, msg)
                mysend(opponent_socket, msg)
                self.cleanup_game(client_socket, opponent_socket)
                return

            # 4. 如果没结束，正常转发给对手
            msg = json.dumps({
                "game_action": "opponent_move",
                "move": move
            })
            mysend(opponent_socket, msg)

    # === 新增：辅助函数 ===
    def check_winner(self, board):
        ##检查是否有赢家"""
        # 所有赢的组合
        winning_combos = [
            (0, 1, 2), (3, 4, 5), (6, 7, 8), # 行
            (0, 3, 6), (1, 4, 7), (2, 5, 8), # 列
            (0, 4, 8), (2, 4, 6)             # 对角线
        ]
        for a, b, c in winning_combos:
            if board[a] and board[a] == board[b] == board[c]:
                return board[a] # 返回 "X" 或 "O"
        return None

    def cleanup_game(self, sock1, sock2):
        ##游戏结束后清理内存"""
        # 删除棋盘记录
        if sock1 in self.boards: del self.boards[sock1]
        if sock2 in self.boards: del self.boards[sock2]
        # 删除符号记录
        if sock1 in self.player_symbols: del self.player_symbols[sock1]
        if sock2 in self.player_symbols: del self.player_symbols[sock2]
        # 删除对战关系
        if sock1 in self.active_games: del self.active_games[sock1]
        if sock2 in self.active_games: del self.active_games[sock2]

    def handle_submit_score(self, client_socket, data):
        ##处理分数提交"""
        player = data.get("player")
        score = data.get("score")
        
        # 更新排行榜
        if player in self.leaderboard:
            self.leaderboard[player] += score
        else:
            self.leaderboard[player] = score
        
        # 广播更新的排行榜
        self.broadcast_leaderboard()

    def broadcast_leaderboard(self):
        ###广播排行榜
        sorted_scores = sorted(
            self.leaderboard.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        leaderboard_data = [
            {"player": name, "score": score}
            for name, score in sorted_scores
        ]
        
        msg = json.dumps({
            "action": "leaderboard_update",
            "data": leaderboard_data
        })
        
        for sock in self.logged_sock2name.keys():
            try:
                mysend(sock, msg)
            except:
                pass




def main():
    server=Server()
    server.run()

if __name__ == "__main__":
    main()
