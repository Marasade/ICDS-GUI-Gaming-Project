#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TicTacToe Game Module for Multiplayer
"""

from tkinter import *
from tkinter import messagebox

class TicTacToeGame:
    def __init__(self, master, my_symbol, opponent_name, on_move_callback, on_game_over_callback):
        """
        Args:
            master: Tkinter窗口
            my_symbol: 'X' 或 'O'
            opponent_name: 对手名字
            on_move_callback: 下棋时的回调函数 callback(row, col)
            on_game_over_callback: 游戏结束回调 callback(winner)
        """
        self.master = master
        self.my_symbol = my_symbol
        self.opponent_symbol = 'O' if my_symbol == 'X' else 'X'
        self.opponent_name = opponent_name
        self.on_move_callback = on_move_callback
        self.on_game_over_callback = on_game_over_callback
        
        # Game state
        self.board = [['' for _ in range(3)] for _ in range(3)]
        self.current_turn = 'X'  # X always goes first
        self.game_over = False
        self.my_turn = (self.my_symbol == 'X')
        
        # UI settings
        self.cell_size = 120
        self.board_size = self.cell_size * 3
        
        self.setup_ui()
        self.draw_board()
        self.update_status()
    
    def setup_ui(self):
        """Setup the game UI"""
        self.master.title("Tic Tac Toe - Multiplayer")
        self.master.resizable(False, False)
        self.master.configure(bg="#2C3E50")
        
        # Info frame
        info_frame = Frame(self.master, bg="#34495E", pady=10)
        info_frame.pack(fill=X)
        
        # Player info
        self.player_label = Label(
            info_frame,
            text=f"You: {self.my_symbol}",
            font=("Helvetica", 14, "bold"),
            bg="#34495E",
            fg="#ECF0F1"
        )
        self.player_label.pack(side=LEFT, padx=20)
        
        self.opponent_label = Label(
            info_frame,
            text=f"Opponent: {self.opponent_name} ({self.opponent_symbol})",
            font=("Helvetica", 14, "bold"),
            bg="#34495E",
            fg="#ECF0F1"
        )
        self.opponent_label.pack(side=RIGHT, padx=20)
        
        # Status label
        self.status_label = Label(
            self.master,
            text="",
            font=("Helvetica", 16, "bold"),
            bg="#2C3E50",
            fg="#F39C12",
            pady=10
        )
        self.status_label.pack()
        
        # Canvas for game board
        self.canvas = Canvas(
            self.master,
            width=self.board_size,
            height=self.board_size,
            bg="#ECF0F1",
            highlightthickness=0
        )
        self.canvas.pack(pady=10)
        
        # Bind click event
        self.canvas.bind('<Button-1>', self.on_click)
        
        # Buttons frame
        btn_frame = Frame(self.master, bg="#2C3E50", pady=10)
        btn_frame.pack()
        
        self.restart_btn = Button(
            btn_frame,
            text="Request Rematch",
            font=("Helvetica", 12),
            command=self.request_rematch,
            state=DISABLED,
            bg="#3498DB",
            fg="white",
            padx=20,
            pady=5
        )
        self.restart_btn.pack(side=LEFT, padx=5)
        
        self.quit_btn = Button(
            btn_frame,
            text="Quit Game",
            font=("Helvetica", 12),
            command=self.quit_game,
            bg="#E74C3C",
            fg="white",
            padx=20,
            pady=5
        )
        self.quit_btn.pack(side=LEFT, padx=5)
    
    def draw_board(self):
        """Draw the tic tac toe board"""
        # Draw grid lines
        for i in range(1, 3):
            # Vertical lines
            x = i * self.cell_size
            self.canvas.create_line(
                x, 0, x, self.board_size,
                width=3,
                fill="#34495E"
            )
            # Horizontal lines
            y = i * self.cell_size
            self.canvas.create_line(
                0, y, self.board_size, y,
                width=3,
                fill="#34495E"
            )
    
    def update_status(self):
        """Update status label"""
        if self.game_over:
            return
        
        if self.my_turn:
            self.status_label.config(
                text="Your Turn!",
                fg="#2ECC71"
            )
        else:
            self.status_label.config(
                text=f"Waiting for {self.opponent_name}...",
                fg="#E67E22"
            )
    
    def on_click(self, event):
        """Handle click on canvas"""
        if self.game_over or not self.my_turn:
            return
        
        # Calculate which cell was clicked
        col = event.x // self.cell_size
        row = event.y // self.cell_size
        
        # Check if cell is valid and empty
        if 0 <= row < 3 and 0 <= col < 3 and self.board[row][col] == '':
            self.make_move(row, col, self.my_symbol)
            # Notify server
            self.on_move_callback(row, col)
    
    def make_move(self, row, col, symbol):
        """Place a symbol on the board"""
        if self.board[row][col] != '':
            return False
        
        self.board[row][col] = symbol
        self.draw_symbol(row, col, symbol)
        
        # Check for winner
        winner = self.check_winner()
        if winner:
            self.end_game(winner)
            return True
        
        # Check for draw
        if self.is_board_full():
            self.end_game('Draw')
            return True
        
        # Switch turn
        self.current_turn = self.opponent_symbol if self.current_turn == self.my_symbol else self.my_symbol
        self.my_turn = not self.my_turn
        self.update_status()
        
        return True
    
    def draw_symbol(self, row, col, symbol):
        """Draw X or O on the board"""
        x1 = col * self.cell_size + 20
        y1 = row * self.cell_size + 20
        x2 = (col + 1) * self.cell_size - 20
        y2 = (row + 1) * self.cell_size - 20
        
        if symbol == 'X':
            # Draw X
            self.canvas.create_line(
                x1, y1, x2, y2,
                width=8,
                fill="#E74C3C",
                capstyle=ROUND
            )
            self.canvas.create_line(
                x2, y1, x1, y2,
                width=8,
                fill="#E74C3C",
                capstyle=ROUND
            )
        else:  # O
            # Draw O
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            radius = (x2 - x1) / 2
            self.canvas.create_oval(
                cx - radius, cy - radius,
                cx + radius, cy + radius,
                width=8,
                outline="#3498DB"
            )
    
    def check_winner(self):
        """Check if there's a winner"""
        # Check rows
        for row in self.board:
            if row[0] == row[1] == row[2] != '':
                return row[0]
        
        # Check columns
        for col in range(3):
            if self.board[0][col] == self.board[1][col] == self.board[2][col] != '':
                return self.board[0][col]
        
        # Check diagonals
        if self.board[0][0] == self.board[1][1] == self.board[2][2] != '':
            return self.board[0][0]
        if self.board[0][2] == self.board[1][1] == self.board[2][0] != '':
            return self.board[0][2]
        
        return None
    
    def is_board_full(self):
        """Check if board is full"""
        for row in self.board:
            if '' in row:
                return False
        return True
    
    def end_game(self, winner):
        """Handle game over"""
        self.game_over = True
        self.restart_btn.config(state=NORMAL)
        
        if winner == 'Draw':
            self.status_label.config(
                text="Game Draw!",
                fg="#95A5A6"
            )
            result = 'draw'
        elif winner == self.my_symbol:
            self.status_label.config(
                text="You Win! 🎉",
                fg="#2ECC71"
            )
            result = 'win'
        else:
            self.status_label.config(
                text="You Lose! 😢",
                fg="#E74C3C"
            )
            result = 'lose'
        
        # Notify callback
        self.on_game_over_callback(result)
    
    def receive_opponent_move(self, row, col):
        """Receive and process opponent's move"""
        if not self.game_over and not self.my_turn:
            self.make_move(row, col, self.opponent_symbol)
    
    def request_rematch(self):
        """Request a rematch"""
        self.status_label.config(
            text="Rematch requested...",
            fg="#F39C12"
        )
        # In a full implementation, this would send a rematch request to the server
        messagebox.showinfo("Rematch", "Rematch feature coming soon! Please start a new game.")
    
    def quit_game(self):
        """Quit the game"""
        if messagebox.askyesno("Quit", "Are you sure you want to quit?"):
            self.master.destroy()


# Test the game independently (for development)
if __name__ == "__main__":
    def test_move(row, col):
        print(f"Move made at: ({row}, {col})")
    
    def test_game_over(result):
        print(f"Game over! Result: {result}")
    
    root = Tk()
    game = TicTacToeGame(
        root,
        my_symbol='X',
        opponent_name='TestBot',
        on_move_callback=test_move,
        on_game_over_callback=test_game_over
    )
    
    # Simulate opponent moves for testing
    def simulate_opponent():
        import random
        if not game.game_over and not game.my_turn:
            empty_cells = [(i, j) for i in range(3) for j in range(3) if game.board[i][j] == '']
            if empty_cells:
                row, col = random.choice(empty_cells)
                root.after(1000, lambda: game.receive_opponent_move(row, col))
                root.after(1500, simulate_opponent)
    
    root.after(2000, simulate_opponent)
    root.mainloop()