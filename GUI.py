#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Apr 30 13:36:58 2021

@author: bing
"""

# import all the required  modules
import threading
import select
from tkinter import *
from tkinter import font
from tkinter import ttk
from chat_utils import *
import json

# GUI class for the chat
class GUI:
    # constructor method
    def __init__(self, send, recv, sm, s):
        # chat window which is currently hidden
        self.Window = Tk()
        self.Window.withdraw()
        self.send = send
        self.recv = recv
        self.sm = sm
        self.socket = s
        self.my_msg = ""
        self.system_msg = ""

        self.game_window = None  # 游戏窗口
        self.game_active = False  # 游戏是否激活
        self.game_board = None    # 游戏棋盘
        self.my_symbol = None     # 我的符号 (X 或 O)
        self.is_my_turn = False   # 是否轮到我

    def login(self):
        # login window
        self.login = Toplevel()
        # set the title
        self.login.title("Login")
        self.login.resizable(width = False, 
                             height = False)
        self.login.configure(width = 400,
                             height = 300)
        # create a Label
        self.pls = Label(self.login, 
                       text = "Please login to continue",
                       justify = CENTER, 
                       font = "Helvetica 14 bold")
          
        self.pls.place(relheight = 0.15,
                       relx = 0.2, 
                       rely = 0.07)
        # create a Label
        self.labelName = Label(self.login,
                               text = "Name: ",
                               font = "Helvetica 12")
          
        self.labelName.place(relheight = 0.2,
                             relx = 0.1, 
                             rely = 0.2)
          
        # create a entry box for 
        # tyoing the message
        self.entryName = Entry(self.login, 
                             font = "Helvetica 14")
          
        self.entryName.place(relwidth = 0.4, 
                             relheight = 0.12,
                             relx = 0.35,
                             rely = 0.2)
          
        # set the focus of the curser
        self.entryName.focus()
          
        # create a Continue Button 
        # along with action
        self.go = Button(self.login,
                         text = "CONTINUE", 
                         font = "Helvetica 14 bold", 
                         command = lambda: self.goAhead(self.entryName.get()))
          
        self.go.place(relx = 0.4,
                      rely = 0.55)
        self.Window.mainloop()
  
    def goAhead(self, name):
        if len(name) > 0:
            msg = json.dumps({"action":"login", "name": name})
            self.send(msg)
            response = json.loads(self.recv())
            if response["status"] == 'ok':
                self.login.destroy()
                self.sm.set_state(S_LOGGEDIN)
                self.sm.set_myname(name)
                self.layout(name)
                self.textCons.config(state = NORMAL)
                # self.textCons.insert(END, "hello" +"\n\n")   
                self.textCons.insert(END, menu +"\n\n")      
                self.textCons.config(state = DISABLED)
                self.textCons.see(END)
                # while True:
                #     self.proc()
        # the thread to receive messages
            process = threading.Thread(target=self.proc)
            process.daemon = True
            process.start()



    def startGameButton(self):
        #处理Start Game按钮点击 
        if self.game_active:
            self.textCons.config(state = NORMAL)
            self.textCons.insert(END, "Game already in progress!\n\n")
            self.textCons.config(state = DISABLED)
            self.textCons.see(END)
            return
        msg = json.dumps({"action": "find_match"})
        self.send(msg)
        self.textCons.config(state = NORMAL)
        self.textCons.insert(END, "Looking for opponent...\n\n")
        self.textCons.config(state = DISABLED)
        self.textCons.see(END)
    
    def create_game_window(self):
        """创建游戏窗口"""
        self.game_window = Toplevel(self.Window)
        self.game_window.title("Tic-Tac-Toe")
        self.game_window.geometry("400x450")
        self.game_window.resizable(False, False)
        
        # 游戏信息标签
        self.game_info = Label(self.game_window,
                              text = f"You are: {self.my_symbol}",
                              font = "Helvetica 14 bold",
                              bg = "#ecf0f1")
        self.game_info.pack(pady=10)
        
        # 回合信息
        self.turn_info = Label(self.game_window,
                              text = "Waiting for game to start...",
                              font = "Helvetica 12")
        self.turn_info.pack(pady=5)
        
        # 游戏棋盘框架
        game_frame = Frame(self.game_window, bg="#34495e")
        game_frame.pack(padx=20, pady=20)
        
        # 创建 3x3 棋盘按钮
        self.board_buttons = []
        self.game_board = ['' for _ in range(9)]  # 空棋盘
        
        for i in range(9):
            btn = Button(game_frame,
                        text = '',
                        font = "Helvetica 24 bold",
                        width = 5,
                        height = 2,
                        bg = "#ecf0f1",
                        command = lambda idx=i: self.make_move(idx))
            btn.grid(row=i//3, column=i%3, padx=5, pady=5)
            self.board_buttons.append(btn)
        
        # 关闭窗口时的处理
        self.game_window.protocol("WM_DELETE_WINDOW", self.close_game)
    
    def make_move(self, position):
        """玩家点击棋盘格子"""
        if not self.is_my_turn:
            return
        
        if self.game_board[position] != '':
            return  # 格子已被占用
        
        # 发送移动到服务器
        msg = json.dumps({
            "action": "game_move",
            "position": position
        })
        self.send(msg)
        
        # 本地更新（等服务器确认）
        self.is_my_turn = False
        self.update_turn_display()
    
    def update_board(self, board_state):
        """更新棋盘显示"""
        self.game_board = board_state
        for i, btn in enumerate(self.board_buttons):
            btn.config(text=board_state[i])
            if board_state[i] != '':
                btn.config(state=DISABLED)
            else:
                btn.config(state=NORMAL)
    
    def update_turn_display(self):
        """更新回合显示"""
        if self.is_my_turn:
            self.turn_info.config(text="Your turn!", fg="#27ae60")
        else:
            self.turn_info.config(text="Opponent's turn...", fg="#e74c3c")
    
    def close_game(self):
        """关闭游戏窗口"""
        if self.game_active:
            # 通知服务器退出游戏
            msg = json.dumps({"action": "quit_game"})
            self.send(msg)
        
        self.game_window.destroy()
        self.game_window = None
        self.game_active = False
        self.game_board = None
        
    # The main layout of the chat
    def layout(self,name):
        
        self.name = name
        # to show chat window
        self.Window.deiconify()
        self.Window.title("CHATROOM")
        self.Window.resizable(width = False,
                              height = False)
        self.Window.configure(width = 470,
                              height = 550,
                              bg = "#17202A")
        self.labelHead = Label(self.Window,
                             bg = "#17202A", 
                              fg = "#EAECEE",
                              text = self.name ,
                               font = "Helvetica 13 bold",
                               pady = 5)
          
        self.labelHead.place(relwidth = 1)
        self.line = Label(self.Window,
                          width = 450,
                          bg = "#ABB2B9")
          
        self.line.place(relwidth = 1,
                        rely = 0.07,
                        relheight = 0.012)
          
        self.textCons = Text(self.Window,
                             width = 20, 
                             height = 2,
                             bg = "#17202A",
                             fg = "#EAECEE",
                             font = "Helvetica 14", 
                             padx = 5,
                             pady = 5)
          
        self.textCons.place(relheight = 0.745,
                            relwidth = 1, 
                            rely = 0.08)
          
        self.labelBottom = Label(self.Window,
                                 bg = "#ABB2B9",
                                 height = 80)
          
        self.labelBottom.place(relwidth = 1,
                               rely = 0.825)
          
        self.entryMsg = Entry(self.labelBottom,
                              bg = "#2C3E50",
                              fg = "#EAECEE",
                              font = "Helvetica 13")
          
        # place the given widget
        # into the gui window
        self.entryMsg.place(relwidth = 0.74,
                            relheight = 0.06,
                            rely = 0.008,
                            relx = 0.011)
          
        self.entryMsg.focus()
          
        # create a Send Button
        self.buttonMsg = Button(self.labelBottom,
                                text = "Send",
                                font = "Helvetica 10 bold", 
                                width = 20,
                                bg = "#ABB2B9",
                                command = lambda : self.sendButton(self.entryMsg.get()))
          
        self.buttonMsg.place(relx = 0.77,
                             rely = 0.008,
                             relheight = 0.06, 
                             relwidth = 0.22)
        

        self.buttonGame = Button(self.labelBottom,
                             text = "Start Game",
                             font = "Helvetica 10 bold",
                             width = 20,
                             bg = "#2ECC71",  # 绿色
                             command = self.startGameButton)
    
        self.buttonGame.place(relx = 0.77,
                            rely = 0.5,  # 放在 Send 按钮下方
                            relheight = 0.06,
                            relwidth = 0.22)
          
        self.textCons.config(cursor = "arrow")
          
        # create a scroll bar
        scrollbar = Scrollbar(self.textCons)
          
        # place the scroll bar 
        # into the gui window
        scrollbar.place(relheight = 1,
                        relx = 0.974)
          
        scrollbar.config(command = self.textCons.yview)
          
        self.textCons.config(state = DISABLED)
  
    # function to basically start the thread for sending messages
    def sendButton(self, msg):
        self.textCons.config(state = DISABLED)
        self.my_msg = msg
        # print(msg)
        self.entryMsg.delete(0, END)

    def proc(self):
        # print(self.msg)
        while True:
            read, write, error = select.select([self.socket], [], [], 0)
            peer_msg = []
            # print(self.msg)
            if self.socket in read:
                peer_msg = self.recv()
            if len(self.my_msg) > 0 or len(peer_msg) > 0:
                if len(peer_msg) > 0:
                    try:
                        msg_data = json.loads(peer_msg)
                        
                        # 处理游戏相关消息
                        if "game_action" in msg_data:
                            self.handle_game_message(msg_data)
                            peer_msg = ""  # 已处理，清空
                    except:
                        pass 

                # print(self.system_msg)
                self.system_msg += self.sm.proc(self.my_msg, peer_msg)
                self.my_msg = ""
                self.textCons.config(state = NORMAL)
                self.textCons.insert(END, self.system_msg +"\n\n")      
                self.textCons.config(state = DISABLED)
                self.textCons.see(END)
                self.system_msg = ""
    def handle_game_message(self, msg_data):
    ##处理游戏消息
        game_action = msg_data["game_action"]
    
        if game_action == "match_found":
        # 找到对手
            opponent = msg_data["opponent"]
            self.my_symbol = msg_data["your_symbol"]
            self.is_my_turn = (self.my_symbol == "X")  # X 先走
            
            self.game_active = True
            self.create_game_window()
            self.update_turn_display()
            
            self.textCons.config(state = NORMAL)
            self.textCons.insert(END, f"Match found! Playing against {opponent}\n\n")
            self.textCons.config(state = DISABLED)
            
        elif game_action == "board_update":
            board_state = msg_data["board"]
            current_turn = msg_data["current_turn"]
            self.is_my_turn = (current_turn == self.my_symbol)
                
        if self.game_window:
            self.update_board(board_state)
            self.update_turn_display()
        
        elif game_action == "game_over":
            # 游戏结束
            result = msg_data["result"]
            winner = msg_data.get("winner", None)
            
            if self.game_window:
                if winner == self.my_symbol:
                    message = "You win! 🎉"
                elif winner:
                    message = "You lose! 😢"
                else:
                    message = "It's a tie! 🤝"
                
                self.turn_info.config(text=message, font="Helvetica 14 bold")
            
            self.game_active = False
            self.textCons.config(state = NORMAL)
            self.textCons.insert(END, f"Game Over: {message}\n\n")
            self.textCons.config(state = DISABLED)

    def run(self):
        self.login()
# create a GUI class object
#if __name__ == "__main__": 
    #g = GUI()