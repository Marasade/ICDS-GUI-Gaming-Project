"""
Game Server with TicTacToe Matchmaking
"""

import time
import socket
import select
import sys
import json
import pickle as pkl
from chat_utils import *
import chat_group as grp
import indexer

class Server:
    def __init__(self):
        self.new_clients = []
        self.logged_name2sock = {}
        self.logged_sock2name = {}
        self.all_sockets = []
        self.group = grp.Group()
        
        # Game-related data structures
        self.scoreboard = {}  # {player_name: total_score}
        self.game_queue = []  # Players waiting for match
        self.game_rooms = {}  # {room_id: {"X": player1, "O": player2, "board": [...], "turn": "X"}}
        self.player_to_room = {}  # {player_name: room_id}
        self.room_counter = 0
        
        # Start server
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(SERVER)
        self.server.listen(5)
        self.all_sockets.append(self.server)
        
        # Initialize chat indices
        self.indices = {}
        self.sonnet = indexer.PIndex("AllSonnets.txt")
        
        print("🎮 TicTacToe Game Server initialized")
        print("📊 Matchmaking system ready")

    def new_client(self, sock):
        print('new client...')
        sock.setblocking(0)
        self.new_clients.append(sock)
        self.all_sockets.append(sock)

    def login(self, sock):
        try:
            msg = json.loads(myrecv(sock))
            print("login:", msg)
            if len(msg) > 0:
                if msg["action"] == "login":
                    name = msg["name"]
                    
                    if self.group.is_member(name) != True:
                        self.new_clients.remove(sock)
                        self.logged_name2sock[name] = sock
                        self.logged_sock2name[sock] = name
                        
                        # Load chat history
                        if name not in self.indices.keys():
                            try:
                                self.indices[name] = pkl.load(open(name + '.idx', 'rb'))
                            except IOError:
                                self.indices[name] = indexer.Index(name)
                        
                        # Initialize scoreboard entry
                        if name not in self.scoreboard:
                            self.scoreboard[name] = 0
                        
                        print(f'✅ {name} logged in')
                        self.group.join(name)
                        mysend(sock, json.dumps({"action": "login", "status": "ok"}))
                    else:
                        mysend(sock, json.dumps({"action": "login", "status": "duplicate"}))
                        print(name + ' duplicate login attempt')
                else:
                    print('wrong code received')
            else:
                self.logout(sock)
        except Exception as e:
            print(f"Login error: {e}")
            if sock in self.all_sockets:
                self.all_sockets.remove(sock)

    def logout(self, sock):
        name = self.logged_sock2name[sock]
        
        # Remove from game queue if waiting
        if name in self.game_queue:
            self.game_queue.remove(name)
            print(f"🚪 {name} removed from game queue")
        
        # Handle active game
        if name in self.player_to_room:
            room_id = self.player_to_room[name]
            if room_id in self.game_rooms:
                room = self.game_rooms[room_id]
                # Notify opponent
                opponent = room['O'] if room['X'] == name else room['X']
                if opponent in self.logged_name2sock:
                    mysend(self.logged_name2sock[opponent], json.dumps({
                        "action": "opponent_disconnected"
                    }))
                # Clean up room
                del self.game_rooms[room_id]
                if opponent in self.player_to_room:
                    del self.player_to_room[opponent]
            del self.player_to_room[name]
        
        # Clean up user data
        pkl.dump(self.indices[name], open(name + '.idx', 'wb'))
        del self.indices[name]
        del self.logged_name2sock[name]
        del self.logged_sock2name[sock]
        self.all_sockets.remove(sock)
        self.group.leave(name)
        sock.close()
        print(f"👋 {name} logged out")

    def create_game_room(self, player1, player2):
        """Create a new game room"""
        self.room_counter += 1
        room_id = self.room_counter
        
        self.game_rooms[room_id] = {
            "X": player1,
            "O": player2,
            "board": [['' for _ in range(3)] for _ in range(3)],
            "turn": "X"
        }
        
        self.player_to_room[player1] = room_id
        self.player_to_room[player2] = room_id
        
        print(f"🎮 Game room {room_id} created: {player1} (X) vs {player2} (O)")
        return room_id

    def broadcast_leaderboard(self):
        """Broadcast updated leaderboard to all connected clients"""
        sorted_scores = sorted(
            self.scoreboard.items(),
            key=lambda x: x[1],
            reverse=True
        )
        leaderboard = [
            {"player": p, "score": s}
            for p, s in sorted_scores if s > 0
        ]
        
        msg = json.dumps({
            "action": "leaderboard_update",
            "data": leaderboard
        })
        
        for sock in self.logged_sock2name.keys():
            try:
                mysend(sock, msg)
            except:
                print("Failed to send leaderboard to a client")

    def handle_msg(self, from_sock):
        msg = myrecv(from_sock)
        if len(msg) > 0:
            try:
                msg = json.loads(msg)
            except:
                return
            
            # ========== GAME ACTIONS ==========
            if msg["action"] == "find_match":
                from_name = self.logged_sock2name[from_sock]
                
                # Check if already in queue
                if from_name in self.game_queue:
                    print(f"⚠️ {from_name} already in queue")
                    return
                
                # Check if already in a game
                if from_name in self.player_to_room:
                    print(f"⚠️ {from_name} already in a game")
                    return
                
                # Add to queue
                self.game_queue.append(from_name)
                print(f"🔍 {from_name} joined match queue (Queue: {len(self.game_queue)})")
                
                # Try to match
                if len(self.game_queue) >= 2:
                    player1 = self.game_queue.pop(0)
                    player2 = self.game_queue.pop(0)
                    
                    # Create game room
                    room_id = self.create_game_room(player1, player2)
                    
                    # Notify both players
                    mysend(self.logged_name2sock[player1], json.dumps({
                        "action": "match_found",
                        "opponent": player2,
                        "your_symbol": "X"
                    }))
                    
                    mysend(self.logged_name2sock[player2], json.dumps({
                        "action": "match_found",
                        "opponent": player1,
                        "your_symbol": "O"
                    }))
                    
                    print(f"✅ Match created: {player1} vs {player2}")
            
            elif msg["action"] == "game_move":
                from_name = self.logged_sock2name[from_sock]
                move = msg["move"]
                
                # Find player's game room
                if from_name not in self.player_to_room:
                    print(f"⚠️ {from_name} not in any game room")
                    return
                
                room_id = self.player_to_room[from_name]
                room = self.game_rooms[room_id]
                
                # Find opponent
                opponent = room['O'] if room['X'] == from_name else room['X']
                
                # Forward move to opponent
                if opponent in self.logged_name2sock:
                    mysend(self.logged_name2sock[opponent], json.dumps({
                        "action": "opponent_move",
                        "move": move
                    }))
                    print(f"📤 Move forwarded: {from_name} -> {opponent} at ({move['row']},{move['col']})")
            
            elif msg["action"] == "submit_score":
                player = msg["player"]
                score = msg["score"]
                
                print(f"📊 Score received: {player} earned {score} points")
                
                # Update scoreboard
                self.scoreboard[player] = self.scoreboard.get(player, 0) + score
                
                # Broadcast updated leaderboard
                self.broadcast_leaderboard()
            
            elif msg["action"] == "get_leaderboard":
                sorted_scores = sorted(
                    self.scoreboard.items(),
                    key=lambda x: x[1],
                    reverse=True
                )
                leaderboard = [
                    {"player": p, "score": s}
                    for p, s in sorted_scores if s > 0
                ]
                
                response = json.dumps({
                    "action": "leaderboard_update",
                    "data": leaderboard
                })
                mysend(from_sock, response)
            
            # ========== CHAT ACTIONS (original) ==========
            elif msg["action"] == "connect":
                to_name = msg["target"]
                from_name = self.logged_sock2name[from_sock]
                if to_name == from_name:
                    msg = json.dumps({"action": "connect", "status": "self"})
                elif self.group.is_member(to_name):
                    to_sock = self.logged_name2sock[to_name]
                    self.group.connect(from_name, to_name)
                    the_guys = self.group.list_me(from_name)
                    msg = json.dumps({"action": "connect", "status": "success"})
                    for g in the_guys[1:]:
                        to_sock = self.logged_name2sock[g]
                        mysend(to_sock, json.dumps({
                            "action": "connect",
                            "status": "request",
                            "from": from_name
                        }))
                else:
                    msg = json.dumps({"action": "connect", "status": "no-user"})
                mysend(from_sock, msg)
            
            elif msg["action"] == "exchange":
                from_name = self.logged_sock2name[from_sock]
                the_guys = self.group.list_me(from_name)
                said2 = text_proc(msg["message"], from_name)
                self.indices[from_name].add_msg_and_index(said2)
                for g in the_guys[1:]:
                    to_sock = self.logged_name2sock[g]
                    self.indices[g].add_msg_and_index(said2)
                    mysend(to_sock, json.dumps({
                        "action": "exchange",
                        "from": msg["from"],
                        "message": msg["message"]
                    }))
            
            elif msg["action"] == "list":
                from_name = self.logged_sock2name[from_sock]
                msg = self.group.list_all()
                mysend(from_sock, json.dumps({"action": "list", "results": msg}))
            
            elif msg["action"] == "poem":
                poem_indx = int(msg["target"])
                from_name = self.logged_sock2name[from_sock]
                print(from_name + ' asks for ', poem_indx)
                poem = self.sonnet.get_poem(poem_indx)
                poem = '\n'.join(poem).strip()
                mysend(from_sock, json.dumps({"action": "poem", "results": poem}))
            
            elif msg["action"] == "time":
                ctime = time.strftime('%d.%m.%y,%H:%M', time.localtime())
                mysend(from_sock, json.dumps({"action": "time", "results": ctime}))
            
            elif msg["action"] == "search":
                term = msg["target"]
                from_name = self.logged_sock2name[from_sock]
                print('search for ' + from_name + ' for ' + term)
                search_rslt = '\n'.join([
                    x[-1] for x in self.indices[from_name].search(term)
                ])
                mysend(from_sock, json.dumps({
                    "action": "search",
                    "results": search_rslt
                }))
            
            elif msg["action"] == "disconnect":
                from_name = self.logged_sock2name[from_sock]
                the_guys = self.group.list_me(from_name)
                self.group.disconnect(from_name)
                the_guys.remove(from_name)
                if len(the_guys) == 1:
                    g = the_guys.pop()
                    to_sock = self.logged_name2sock[g]
                    mysend(to_sock, json.dumps({"action": "disconnect"}))
        else:
            self.logout(from_sock)

    def run(self):
        print('🚀 Starting TicTacToe game server...')
        print('=' * 50)
        while(1):
            read, write, error = select.select(self.all_sockets, [], [])
            
            for logc in list(self.logged_name2sock.values()):
                if logc in read:
                    self.handle_msg(logc)
            
            for newc in self.new_clients[:]:
                if newc in read:
                    self.login(newc)
            
            if self.server in read:
                sock, address = self.server.accept()
                self.new_client(sock)

def main():
    server = Server()
    server.run()

if __name__ == "__main__":
    main()