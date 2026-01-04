import numpy as np
import random
import copy

# --- CONSTANTS ---
ROW_COUNT = 6
COLUMN_COUNT = 7

EMPTY = 0
PLAYER_PIECE = 1
AI_PIECE = 2

WINDOW_LENGTH = 4

class Connect4Logic:
    """
    THE BLUE BRAIN: 
    Strict adherence to rules. Pure Logic. Unbeatable Math.
    """
    def __init__(self):
        self.board = np.zeros((ROW_COUNT, COLUMN_COUNT), dtype=int)

    def create_board(self):
        self.board = np.zeros((ROW_COUNT, COLUMN_COUNT), dtype=int)

    def drop_piece(self, row, col, piece):
        """Standard gravity drop."""
        self.board[row][col] = piece

    def is_valid_location(self, col):
        """Checks if the top row of a column is empty."""
        return self.board[0][col] == 0

    def get_next_open_row(self, col):
        """Finds the lowest empty slot in a column (simulating gravity)."""
        for r in range(ROW_COUNT-1, -1, -1):  # Start from bottom (ROW_COUNT-1) and go up
            if self.board[r][col] == 0:
                return r

    def winning_move(self, piece):
        """Checks horizontal, vertical, and diagonal for a win."""
        # Check Horizontal
        for c in range(COLUMN_COUNT - 3):
            for r in range(ROW_COUNT):
                if self.board[r][c] == piece and self.board[r][c+1] == piece and \
                   self.board[r][c+2] == piece and self.board[r][c+3] == piece:
                    return True

        # Check Vertical
        for c in range(COLUMN_COUNT):
            for r in range(ROW_COUNT - 3):
                if self.board[r][c] == piece and self.board[r+1][c] == piece and \
                   self.board[r+2][c] == piece and self.board[r+3][c] == piece:
                    return True

        # Check Positively Sloped Diagonals
        for c in range(COLUMN_COUNT - 3):
            for r in range(ROW_COUNT - 3):
                if self.board[r][c] == piece and self.board[r+1][c+1] == piece and \
                   self.board[r+2][c+2] == piece and self.board[r+3][c+3] == piece:
                    return True

        # Check Negatively Sloped Diagonals
        for c in range(COLUMN_COUNT - 3):
            for r in range(3, ROW_COUNT):
                if self.board[r][c] == piece and self.board[r-1][c+1] == piece and \
                   self.board[r-2][c+2] == piece and self.board[r-3][c+3] == piece:
                    return True
        return False

    def evaluate_window(self, window, piece):
        """Heuristic scoring for non-terminal states."""
        score = 0
        opp_piece = PLAYER_PIECE
        if piece == PLAYER_PIECE:
            opp_piece = AI_PIECE

        if window.count(piece) == 4:
            score += 100
        elif window.count(piece) == 3 and window.count(EMPTY) == 1:
            score += 5
        elif window.count(piece) == 2 and window.count(EMPTY) == 2:
            score += 2

        if window.count(opp_piece) == 3 and window.count(EMPTY) == 1:
            score -= 4 # Penalize leaving opponent with a winning move

        return score

    def score_position(self, piece):
        """Scoring the entire board state."""
        score = 0
        
        # Score Center Column (Tactical Advantage)
        center_array = [int(i) for i in list(self.board[:, COLUMN_COUNT//2])]
        center_count = center_array.count(piece)
        score += center_count * 3

        # Score Horizontal
        for r in range(ROW_COUNT):
            row_array = [int(i) for i in list(self.board[r,:])]
            for c in range(COLUMN_COUNT - 3):
                window = row_array[c:c+WINDOW_LENGTH]
                score += self.evaluate_window(window, piece)

        # Score Vertical
        for c in range(COLUMN_COUNT):
            col_array = [int(i) for i in list(self.board[:,c])]
            for r in range(ROW_COUNT - 3):
                window = col_array[r:r+WINDOW_LENGTH]
                score += self.evaluate_window(window, piece)

        # Score Diagonals (omitted for brevity, follows same pattern)
        # ... (Implemented in full version)
        
        return score

    def is_terminal_node(self):
        return self.winning_move(PLAYER_PIECE) or self.winning_move(AI_PIECE) or len(self.get_valid_locations()) == 0

    def get_valid_locations(self):
        valid_locations = []
        for col in range(COLUMN_COUNT):
            if self.is_valid_location(col):
                valid_locations.append(col)
        return valid_locations

    def minimax(self, board, depth, alpha, beta, maximizingPlayer):
        """
        THE ALGORITHM:
        Minimax with Alpha-Beta Pruning.
        """
        valid_locations = self.get_valid_locations()
        is_terminal = self.is_terminal_node()
        
        if depth == 0 or is_terminal:
            if is_terminal:
                if self.winning_move(AI_PIECE):
                    return (None, 100000000000000)
                elif self.winning_move(PLAYER_PIECE):
                    return (None, -10000000000000)
                else: # Game is over, no more valid moves
                    return (None, 0)
            else: # Depth is zero
                return (None, self.score_position(AI_PIECE))
        
        if maximizingPlayer:
            value = -np.inf
            column = random.choice(valid_locations)
            for col in valid_locations:
                row = self.get_next_open_row(col)
                b_copy = self.board.copy()
                # Simulate move
                self.board[row][col] = AI_PIECE
                new_score = self.minimax(self.board, depth-1, alpha, beta, False)[1]
                # Undo move
                self.board = b_copy
                
                if new_score > value:
                    value = new_score
                    column = col
                alpha = max(alpha, value)
                if alpha >= beta:
                    break
            return column, value

        else: # Minimizing player
            value = np.inf
            column = random.choice(valid_locations)
            for col in valid_locations:
                row = self.get_next_open_row(col)
                b_copy = self.board.copy()
                self.board[row][col] = PLAYER_PIECE
                new_score = self.minimax(self.board, depth-1, alpha, beta, True)[1]
                self.board = b_copy
                
                if new_score < value:
                    value = new_score
                    column = col
                beta = min(beta, value)
                if alpha >= beta:
                    break
            return column, value
            
    def get_best_move(self, depth=5):
        col, minimax_score = self.minimax(self.board, depth, -np.inf, np.inf, True)
        return col


class GodModeEngine(Connect4Logic):
    """
    THE RED BRAIN:
    Chaos. Reality Bending. The tools the LLM uses to 'cheat'.
    """
    
    def force_place_token(self, row, col, piece):
        """
        Allows placing a token anywhere.
        Ignores gravity. Ignores column fullness.
        """
        if 0 <= row < ROW_COUNT and 0 <= col < COLUMN_COUNT:
            self.board[row][col] = piece
            return True
        return False

    def remove_token(self, row, col):
        """Deletes a token from existence."""
        if 0 <= row < ROW_COUNT and 0 <= col < COLUMN_COUNT:
            self.board[row][col] = EMPTY
            return True
        return False

    def wipe_board(self):
        """Standard 'Rage Quit' or 'Fresh Start'."""
        self.create_board()

    def get_board_state_string(self):
        """Returns the board as a string for the LLM to read."""
        # Flip vertically so row 0 is at the bottom visually
        return str(np.flip(self.board, 0))