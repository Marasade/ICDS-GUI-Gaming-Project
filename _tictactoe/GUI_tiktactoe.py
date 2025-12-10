#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI with TicTacToe Game Integration
"""

import threading
import select
from tkinter import *
from tkinter import messagebox
from chat_utils import *
import json
from tictactoe_game import TicTacToeGame

class GUI:
    def __init__(self, send, recv, sm, s):
        self.Window = Tk()
        self.Window.withdraw()
        self.send = send
        self.recv = recv
        self.sm = sm
        self.socket = s
        self.my_msg = ""
        self.system_msg = ""
        self.game_window = None
        self.current_game = None
        self.waiting_for_match = False

    def login(self):
        self.login = Toplevel()
        self.login.title("Login")
        self.login.resizable(width=False, height=False)
        self.login.configure(width=400, height=300)
        
        self.pls = Label(
            self.login,
            text="Please login to continue",
            justify=CENTER,
            font="Helvetica 14 bold"
        )
        self.pls.place(relheight=0.15, relx=0.2, rely=0.07)
        
        self.labelName = Label(
            self.login,
            text="Name: ",
            font="Helvetica 12"
        )
        self.labelName.place(relheight=0.2, relx=0.1, rely=0.2)
        
        self.entryName = Entry(self.login, font="Helvetica 14")
        self.entryName.place(relwidth=0.4, relheight=0.12, relx=0.35, rely=0.2)
        self.entryName.focus()
        
        self.go = Button(
            self.login,
            text="CONTINUE",
            font="Helvetica 14 bold",
            command=lambda: self.goAhead(self.entryName.get())
        )
        self.go.place(relx=0.4, rely=0.55)
        self.Window.mainloop()

    def goAhead(self, name):
        if len(name) > 0:
            msg = json.dumps({"action": "login", "name": name})
            self.send(msg)
            response = json.loads(self.recv())
            if response["status"] == 'ok':
                self.login.destroy()
                self.sm.set_state(S_LOGGEDIN)
                self.sm.set_myname(name)
                self.layout(name)
                self.textCons.config(state=NORMAL)
                self.textCons.insert(END, tictactoe_menu + "\n\n")
                self.textCons.config(state=DISABLED)
                self.textCons.see(END)
                
                process = threading.Thread(target=self.proc)
                process.daemon = True
                process.start()

    def layout(self, name):
        self.name = name
        self.Window.deiconify()
        self.Window.title("TicTacToe GAME LOBBY")
        self.Window.resizable(width=False, height=False)
        self.Window.configure(width=470, height=550, bg="#17202A")
        
        self.labelHead = Label(
            self.Window,
            bg="#17202A",
            fg="#EAECEE",
            text=self.name,
            font="Helvetica 13 bold",
            pady=5
        )
        self.labelHead.place(relwidth=1)
        
        self.line = Label(self.Window, width=450, bg="#ABB2B9")
        self.line.place(relwidth=1, rely=0.07, relheight=0.012)
        
        self.textCons = Text(
            self.Window,
            width=20,
            height=2,
            bg="#17202A",
            fg="#EAECEE",
            font="Helvetica 14",
            padx=5,
            pady=5
        )
        self.textCons.place(relheight=0.745, relwidth=1, rely=0.08)
        
        self.labelBottom = Label(self.Window, bg="#ABB2B9", height=80)
        self.labelBottom.place(relwidth=1, rely=0.825)
        
        self.entryMsg = Entry(
            self.labelBottom,
            bg="#2C3E50",
            fg="#EAECEE",
            font="Helvetica 13"
        )
        self.entryMsg.place(relwidth=0.74, relheight=0.06, rely=0.008, relx=0.011)
        self.entryMsg.focus()
        
        self.buttonMsg = Button(
            self.labelBottom,
            text="Send",
            font="Helvetica 10 bold",
            width=20,
            bg="#ABB2B9",
            command=lambda: self.sendButton(self.entryMsg.get())
        )
        self.buttonMsg.place(relx=0.77, rely=0.008, relheight=0.06, relwidth=0.22)
        
        self.textCons.config(cursor="arrow")
        
        scrollbar = Scrollbar(self.textCons)
        scrollbar.place(relheight=1, relx=0.974)
        scrollbar.config(command=self.textCons.yview)
        
        self.textCons.config(state=DISABLED)

    def sendButton(self, msg):
        self.textCons.config(state=DISABLED)
        self.my_msg = msg
        self.entryMsg.delete(0, END)

    def find_match(self):
        """Request to find a match"""
        if self.waiting_for_match:
            self.display_message("⏳ Already waiting for a match...")
            return
        
        if self.current_game is not None:
            try:
                if self.game_window and self.game_window.winfo_exists():
                    self.display_message("❌ You're already in a game!")
                    return
            except:
                pass
        
        self.waiting_for_match = True
        msg = json.dumps({"action": "find_match", "game": "tictactoe"})
        self.send(msg)
        self.display_message("🔍 Looking for opponent...\n⏳ Please wait...")

    def on_match_found(self, opponent_name, my_symbol):
        """Called when a match is found"""
        self.waiting_for_match = False
        self.display_message(f"✅ Match found!\n👤 Opponent: {opponent_name}\n🎮 You are: {my_symbol}\n")
        
        # Create game window
        self.game_window = Toplevel(self.Window)
        self.current_game = TicTacToeGame(
            self.game_window,
            my_symbol=my_symbol,
            opponent_name=opponent_name,
            on_move_callback=self.send_move,
            on_game_over_callback=self.on_game_over
        )

    def send_move(self, row, col):
        """Send move to server"""
        msg = json.dumps({
            "action": "game_move",
            "game": "tictactoe",
            "move": {"row": row, "col": col}
        })
        self.send(msg)

    def receive_opponent_move(self, row, col):
        """Receive opponent's move from server"""
        if self.current_game:
            self.current_game.receive_opponent_move(row, col)

    def on_game_over(self, result):
        """Called when game ends"""
        if result == 'win':
            self.display_message("🎉 You won the game!\n")
            # Submit score
            msg = json.dumps({
                "action": "submit_score",
                "player": self.name,
                "score": 3  # 3 points for win
            })
            self.send(msg)
        elif result == 'lose':
            self.display_message("😢 You lost the game.\n")
        else:  # draw
            self.display_message("🤝 Game ended in a draw.\n")
            # 1 point for draw
            msg = json.dumps({
                "action": "submit_score",
                "player": self.name,
                "score": 1
            })
            self.send(msg)
        
        self.current_game = None

    def display_message(self, msg):
        """Display message in chat window"""
        self.textCons.config(state=NORMAL)
        self.textCons.insert(END, msg + "\n")
        self.textCons.config(state=DISABLED)
        self.textCons.see(END)

    def display_leaderboard(self, leaderboard_data):
        """Display leaderboard in chat window"""
        self.textCons.config(state=NORMAL)
        self.textCons.insert(END, "\n" + "="*40 + "\n")
        self.textCons.insert(END, "🏆 LEADERBOARD 🏆\n")
        self.textCons.insert(END, "="*40 + "\n")
        
        if not leaderboard_data:
            self.textCons.insert(END, "No scores yet. Be the first to play!\n")
        else:
            for i, entry in enumerate(leaderboard_data[:10], 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                line = f"{medal} {entry['player']:.<20} {entry['score']:>5} pts\n"
                self.textCons.insert(END, line)
        
        self.textCons.insert(END, "="*40 + "\n\n")
        self.textCons.config(state=DISABLED)
        self.textCons.see(END)

    def proc(self):
        while True:
            read, write, error = select.select([self.socket], [], [], 0)
            peer_msg = []
            
            if self.socket in read:
                peer_msg = self.recv()
            
            if len(self.my_msg) > 0 or len(peer_msg) > 0:
                # Check for game commands
                if self.my_msg == 'play':
                    self.find_match()
                    self.my_msg = ""
                    continue
                elif self.my_msg == 'l':
                    self.send(json.dumps({"action": "get_leaderboard"}))
                    self.my_msg = ""
                    continue
                
                # Handle messages from server
                if len(peer_msg) > 0:
                    try:
                        peer_data = json.loads(peer_msg)
                        
                        if peer_data.get("action") == "match_found":
                            # Match found!
                            opponent = peer_data.get("opponent")
                            my_symbol = peer_data.get("your_symbol")
                            self.on_match_found(opponent, my_symbol)
                            peer_msg = ""
                        
                        elif peer_data.get("action") == "opponent_move":
                            # Opponent made a move
                            move = peer_data.get("move")
                            self.receive_opponent_move(move["row"], move["col"])
                            peer_msg = ""
                        
                        elif peer_data.get("action") == "opponent_disconnected":
                            # Opponent left
                            self.display_message("⚠️ Opponent disconnected. You win by default!")
                            if self.current_game:
                                self.current_game.end_game(self.current_game.my_symbol)
                            peer_msg = ""
                        
                        elif peer_data.get("action") == "leaderboard_update":
                            self.display_leaderboard(peer_data.get("data", []))
                            peer_msg = ""
                        
                        elif peer_data.get("action") == "match_cancelled":
                            self.waiting_for_match = False
                            self.display_message("❌ Match cancelled.\n")
                            peer_msg = ""
                    
                    except Exception as e:
                        print(f"Error processing peer message: {e}")
                
                # Process regular chat messages
                if len(peer_msg) > 0 or len(self.my_msg) > 0:
                    self.system_msg += self.sm.proc(self.my_msg, peer_msg)
                    self.my_msg = ""
                
                if self.system_msg:
                    self.textCons.config(state=NORMAL)
                    self.textCons.insert(END, self.system_msg + "\n\n")
                    self.textCons.config(state=DISABLED)
                    self.textCons.see(END)
                    self.system_msg = ""

    def run(self):
        self.login()

if __name__ == "__main__":
    g = GUI()