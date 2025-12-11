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
        self.leaderboard_window = None
        self.leaderboard_data = []
        self.my_score = 0

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
        # 1. 还没轮到自己，不能点
        if not self.is_my_turn:
            return
        
        # 2. 【防止重复落子】直接检查按钮上有没有字
        # 假设你的按钮列表叫 self.board_buttons (请核对你的变量名)
        if self.board_buttons[position]['text'] != "":
            return 
        
        # 3. 【关键修复】本地立刻显示自己的棋子，并锁住按钮
        self.board_buttons[position].config(text=self.my_symbol, state=DISABLED)
        
        # 4. 发送移动到服务器
        # 注意：这里要用 "game_move" 和 "move" 才能匹配我们之前改的 Server 代码
        msg = json.dumps({
            "action": "game_move", 
            "move": position
        })
        self.send(msg)
        
        # 5. 切换状态
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


    def request_leaderboard(self):
        """请求服务器发送排行榜"""
        msg = json.dumps({"action": "request_leaderboard"})
        self.send(msg)
    
    def update_leaderboard_display(self, leaderboard_data):
        """更新排行榜显示"""
        if not self.game_window or not hasattr(self, 'leaderboard_text'):
            return
        
        self.leaderboard_text.config(state=NORMAL)
        self.leaderboard_text.delete(1.0, END)
        
        if not leaderboard_data:
            self.leaderboard_text.insert(END, "No scores yet!\n")
        else:
            for i, entry in enumerate(leaderboard_data, 1):
                player = entry["player"]
                score = entry["score"]
                
                # 高亮当前玩家
                if player == self.sm.get_myname():
                    line = f"{i}. {player}: {score} ⭐\n"
                else:
                    line = f"{i}. {player}: {score}\n"
                
                self.leaderboard_text.insert(END, line)
        
        self.leaderboard_text.config(state=DISABLED)
    
    def update_my_score(self, new_score):
        """更新我的分数显示"""
        self.my_score = new_score
        if hasattr(self, 'score_label'):
            self.score_label.config(text=f"Your Score: {self.my_score}")
    
    def show_leaderboard(self):
        """显示独立的排行榜窗口"""
        if self.leaderboard_window:
            self.leaderboard_window.lift()
            return
        
        self.leaderboard_window = Toplevel(self.Window)
        self.leaderboard_window.title("Leaderboard")
        self.leaderboard_window.geometry("300x400")
        self.leaderboard_window.resizable(False, False)
        
        # 标题
        title = Label(self.leaderboard_window,
                     text="🏆 Top Players",
                     font="Helvetica 16 bold",
                     bg="#2c3e50",
                     fg="#ecf0f1")
        title.pack(fill=X, pady=10)
        
        # 排行榜显示
        lb_text = Text(self.leaderboard_window,
                       font="Helvetica 12",
                       bg="#ecf0f1",
                       state=DISABLED)
        lb_text.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        # 请求并显示排行榜
        self.request_leaderboard()
        
        # 更新显示
        if self.leaderboard_data:
            lb_text.config(state=NORMAL)
            for i, entry in enumerate(self.leaderboard_data, 1):
                player = entry["player"]
                score = entry["score"]
                
                if player == self.sm.get_myname():
                    line = f"{i}. {player}: {score} ⭐\n"
                else:
                    line = f"{i}. {player}: {score}\n"
                
                lb_text.insert(END, line)
            lb_text.config(state=DISABLED)
        
        # 关闭窗口
        def on_close():
            self.leaderboard_window.destroy()
            self.leaderboard_window = None
        
        self.leaderboard_window.protocol("WM_DELETE_WINDOW", on_close)
    
    def submit_score(self, score_change):
        """提交分数到服务器"""
        msg = json.dumps({
            "action": "submit_score",
            "player": self.sm.get_myname(),
            "score": score_change
        })
        self.send(msg)
    
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
        self.entryMsg.place(relwidth = 0.50,
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
          
        self.buttonMsg.place(relx = 0.52,
                             rely = 0.008,
                             relheight = 0.06, 
                             relwidth = 0.22)
        

        self.buttonGame = Button(self.labelBottom,
                             text = "Start Game",
                             font = "Helvetica 10 bold",
                             width = 20,
                             bg = "#2ECC71",  # 绿色
                             command = self.startGameButton)
    
        self.buttonGame.place(relx = 0.75,
                            rely = 0.008,  # 放在 Send 按钮右边
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
        while True:
            try: # <--- 新增：最外层的 try，防止线程直接挂掉
                read, write, error = select.select([self.socket], [], [], 0)
                peer_msg = []
                if self.socket in read:
                    peer_msg = self.recv()
                
                if len(self.my_msg) > 0 or len(peer_msg) > 0:
                    # 1. 尝试拦截游戏/排行榜消息
                    if len(peer_msg) > 0:
                        try:
                            msg_data = json.loads(peer_msg)
                            
                            # 检查是否有 game_action
                            if "game_action" in msg_data:
                                self.handle_game_message(msg_data)
                                continue # 处理完直接跳过，不给聊天系统
                                
                        except json.JSONDecodeError:
                            pass # 不是 JSON，可能是普通聊天，放行
                        except Exception as e:
                            print(f"⚠️ 游戏逻辑出错: {e}") # 打印错误但不要崩潰

                    # 2. 正常的聊天/菜单消息处理
                    # 如果上面 continue 了，这里就不会执行
                    self.system_msg += self.sm.proc(self.my_msg, peer_msg)
                    self.my_msg = ""
                    
                    # 更新 GUI 聊天框
                    self.textCons.config(state = NORMAL)
                    self.textCons.insert(END, self.system_msg + "\n\n")      
                    self.textCons.config(state = DISABLED)
                    self.textCons.see(END)
                    self.system_msg = ""

            except Exception as e:
                # <--- 这里會告訴你為什麼黑屏
                print(f"❌ proc 线程崩溃: {e}") 
                import traceback
                traceback.print_exc() # 打印详细报错位置
                break # 避免死循环刷屏

    def submit_score(self, score_change):
    ###提交分数到服务器"""
        msg = json.dumps({
            "action": "submit_score",
            "player": self.sm.get_myname(),
            "score": score_change
        })
        self.send(msg)
    def handle_game_message(self, msg_data):
        """处理服务器发来的游戏消息"""
        action = msg_data.get("game_action")
        
        if not action:
            return

        if action == "match_found":
            opponent = msg_data["opponent"]
            self.my_symbol = msg_data["your_symbol"]
            self.is_my_turn = (self.my_symbol == "X")
            self.game_active = True
            
            # 创建游戏窗口
            self.create_game_window()
            self.update_turn_display()
            
            # 在聊天框提示
            self.textCons.config(state=NORMAL)
            self.textCons.insert(END, f"Match found! Playing against {opponent}\n\n")
            self.textCons.config(state=DISABLED)

        elif action == "opponent_move":
            move_index = msg_data["move"]
            opponent_symbol = "O" if self.my_symbol == "X" else "X"
            
            # 更新棋盘按钮
            if self.game_window:
                self.board_buttons[move_index].config(text=opponent_symbol, state=DISABLED)
            
            self.is_my_turn = True
            self.update_turn_display()

        elif action == "game_over":
            result = msg_data["result"]
            winner = msg_data.get("winner")

            message = ""
            score_change = 0
            
            if result == "tie":
                message = "It's a tie! 🤝"
                score_change = 1
            elif winner == self.my_symbol:
                message = "You win! 🎉"
                score_change = 3
            else:
                message = "You lose! 😢"
                score_change = 0

            if self.game_window:
                self.turn_info.config(text=message, font="Helvetica 14 bold", fg="blue")
                for btn in self.board_buttons:
                    btn.config(state=DISABLED)

            self.game_active = False
            self.textCons.config(state=NORMAL)
            self.textCons.insert(END, f"Game Over: {message}\nYou earned {score_change} points!\n\n")
            self.textCons.config(state=DISABLED)

            # 提交分数
            self.submit_score(score_change)
            
        elif action == "leaderboard_update":
            data = msg_data.get("data", [])

            self.show_leaderboard_window(data)
            
            self.textCons.config(state=NORMAL)
            self.textCons.insert(END, "📊 Leaderboard updated!\n\n")
            self.textCons.config(state=DISABLED)
            
           
            
    def show_leaderboard_window(self, data):
        """显示或更新排行榜窗口"""
        
        # 如果窗口已存在且打开，先关闭
        if hasattr(self, 'lb_window') and self.lb_window and self.lb_window.winfo_exists():
            self.lb_window.destroy()
        
        # 创建新窗口
        self.lb_window = Toplevel(self.Window)
        self.lb_window.title("🏆 Leaderboard")
        self.lb_window.geometry("350x450")
        self.lb_window.resizable(False, False)
        self.lb_window.configure(bg="#2c3e50")
        
        # 标题
        title_label = Label(
            self.lb_window,
            text="🏆 TOP PLAYERS 🏆",
            font=("Helvetica", 16, "bold"),
            bg="#2c3e50",
            fg="#ecf0f1",
            pady=15
        )
        title_label.pack(fill=X)
        
        # 使用 Text 显示排行榜（更简单）
        lb_text = Text(
            self.lb_window,
            font=("Courier", 12),  # 等宽字体对齐更好
            bg="#ecf0f1",
            fg="#2c3e50",
            state=NORMAL,
            width=40,
            height=20
        )
        lb_text.pack(pady=10, padx=10, fill=BOTH, expand=True)
        
        # 填入数据
        if not data:
            lb_text.insert(END, "\n  No scores yet!\n  Be the first to play!\n")
        else:
            # 表头
            lb_text.insert(END, "  Rank  Player              Score\n")
            lb_text.insert(END, "  " + "="*38 + "\n\n")
            
            # 显示排行榜
            my_name = self.sm.get_myname()
            for i, entry in enumerate(data, 1):
                player = entry["player"]
                score = entry["score"]
                
                # 高亮当前玩家
                if player == my_name:
                    line = f"  {i:>2}.  {player:<18} {score:>5} ⭐\n"
                else:
                    line = f"  {i:>2}.  {player:<18} {score:>5}\n"
                
                lb_text.insert(END, line)
        
        lb_text.config(state=DISABLED)
        
        # 关闭按钮
        close_btn = Button(
            self.lb_window,
            text="Close",
            font=("Helvetica", 11, "bold"),
            bg="#e74c3c",
            fg="white",
            command=self.lb_window.destroy
        )
        close_btn.pack(pady=10)
        
        # 设置关闭事件
        def on_close():
            self.lb_window.destroy()
            self.lb_window = None
        
        self.lb_window.protocol("WM_DELETE_WINDOW", on_close)
    def request_and_show_leaderboard(self):
        """请求服务器发送排行榜"""
        msg = json.dumps({"action": "request_leaderboard"})
        self.send(msg)
        
        # 在聊天框提示
        self.textCons.config(state=NORMAL)
        self.textCons.insert(END, "📊 Requesting leaderboard...\n\n")
        self.textCons.config(state=DISABLED)

    def run(self):
        self.login()
# create a GUI class object
#if __name__ == "__main__": 
    #g = GUI()