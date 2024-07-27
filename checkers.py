import pygame
import sys
import random
import json
import time

# Initialize Pygame
pygame.init()

# Constants
WIDTH, HEIGHT = 1150, 800
BOARD_WIDTH = 800
MENU_WIDTH = WIDTH - BOARD_WIDTH
ROWS, COLS = 8, 8
SQUARE_SIZE = BOARD_WIDTH // COLS

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
GRAY = (128, 128, 128)

# Set up the display
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Checkers")

class Piece:
    def __init__(self, row, col, color):
        self.row = row
        self.col = col
        self.color = color
        self.king = False
        self.x = 0
        self.y = 0
        self.calc_pos()

    def calc_pos(self):
        self.x = SQUARE_SIZE * self.col + SQUARE_SIZE // 2
        self.y = SQUARE_SIZE * self.row + SQUARE_SIZE // 2

    def make_king(self):
        self.king = True

    def draw(self, screen):
        radius = SQUARE_SIZE // 2 - 10
        pygame.draw.circle(screen, self.color, (self.x, self.y), radius)
        if self.king:
            pygame.draw.circle(screen, GRAY, (self.x, self.y), radius // 2)

    def move(self, row, col):
        self.row = row
        self.col = col
        self.calc_pos()

    def serialize(self):
        return {
            'row': self.row,
            'col': self.col,
            'color': self.color,
            'king': self.king
        }

    @classmethod
    def deserialize(cls, data):
        piece = cls(data['row'], data['col'], data['color'])
        piece.king = data['king']
        return piece

class Board:
    def __init__(self):
        self.board = []
        self.create_board()

    def create_board(self):
        for row in range(ROWS):
            self.board.append([])
            for col in range(COLS):
                if col % 2 == ((row + 1) % 2):
                    if row < 3:
                        self.board[row].append(Piece(row, col, WHITE))
                    elif row > 4:
                        self.board[row].append(Piece(row, col, RED))
                    else:
                        self.board[row].append(0)
                else:
                    self.board[row].append(0)

    def draw(self, screen):
        screen.fill(BLACK)
        for row in range(ROWS):
            for col in range(row % 2, COLS, 2):
                pygame.draw.rect(screen, GRAY, (col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))

        for row in range(ROWS):
            for col in range(COLS):
                piece = self.board[row][col]
                if piece != 0:
                    piece.draw(screen)

    def move(self, piece, row, col):
        self.board[piece.row][piece.col], self.board[row][col] = self.board[row][col], self.board[piece.row][piece.col]
        piece.move(row, col)

        if row == ROWS - 1 or row == 0:
            piece.make_king()

    def get_piece(self, row, col):
        return self.board[row][col]

    def get_valid_moves(self, piece):
        moves = {}
        left = piece.col - 1
        right = piece.col + 1
        row = piece.row

        if piece.color == RED or piece.king:
            moves.update(self._traverse_left(row - 1, max(row - 3, -1), -1, piece.color, left))
            moves.update(self._traverse_right(row - 1, max(row - 3, -1), -1, piece.color, right))
        if piece.color == WHITE or piece.king:
            moves.update(self._traverse_left(row + 1, min(row + 3, ROWS), 1, piece.color, left))
            moves.update(self._traverse_right(row + 1, min(row + 3, ROWS), 1, piece.color, right))

        return moves

    def _traverse_left(self, start, stop, step, color, left, skipped=[]):
        moves = {}
        last = []
        for r in range(start, stop, step):
            if left < 0:
                break

            current = self.board[r][left]
            if current == 0:
                if skipped and not last:
                    break
                elif skipped:
                    moves[(r, left)] = last + skipped
                else:
                    moves[(r, left)] = last

                if last:
                    if step == -1:
                        row = max(r - 3, 0)
                    else:
                        row = min(r + 3, ROWS)
                    moves.update(self._traverse_left(r + step, row, step, color, left - 1, skipped=last))
                    moves.update(self._traverse_right(r + step, row, step, color, left + 1, skipped=last))
                break
            elif current.color == color:
                break
            else:
                last = [current]

            left -= 1

        return moves

    def _traverse_right(self, start, stop, step, color, right, skipped=[]):
        moves = {}
        last = []
        for r in range(start, stop, step):
            if right >= COLS:
                break

            current = self.board[r][right]
            if current == 0:
                if skipped and not last:
                    break
                elif skipped:
                    moves[(r, right)] = last + skipped
                else:
                    moves[(r, right)] = last

                if last:
                    if step == -1:
                        row = max(r - 3, 0)
                    else:
                        row = min(r + 3, ROWS)
                    moves.update(self._traverse_left(r + step, row, step, color, right - 1, skipped=last))
                    moves.update(self._traverse_right(r + step, row, step, color, right + 1, skipped=last))
                break
            elif current.color == color:
                break
            else:
                last = [current]

            right += 1

        return moves

    def remove(self, pieces):
        for piece in pieces:
            self.board[piece.row][piece.col] = 0

    def serialize(self):
        return [[piece.serialize() if piece != 0 else 0 for piece in row] for row in self.board]

    @classmethod
    def deserialize(cls, data):
        board = cls()
        board.board = [[Piece.deserialize(piece) if piece != 0 else 0 for piece in row] for row in data]
        return board

class Game:
    def __init__(self, screen, single_player=False):
        self.screen = screen
        self.board = Board()
        self.turn = RED
        self.valid_moves = {}
        self.selected = None
        self.single_player = single_player
        self.hint_mode = False
        self.red_time = 0
        self.white_time = 0
        self.turn_start_time = time.time()
        self.game_over = False
        self.game_end_time = None

    def update(self):
        self.board.draw(self.screen)
        self.draw_valid_moves(self.valid_moves)
        self.update_timer()
        draw_in_game_menu(self.screen, self)
        pygame.display.update()

    def change_turn(self):
        self.valid_moves = {}
        current_time = time.time()
        if self.turn == RED:
            self.red_time += current_time - self.turn_start_time
            self.turn = WHITE
        else:
            self.white_time += current_time - self.turn_start_time
            self.turn = RED
        self.turn_start_time = current_time

        # Check for a win condition after changing turns
        self.check_for_win()

    def update_timer(self):
        if self.game_over:
            return
        current_time = time.time()
        if self.turn == RED:
            self.red_time += current_time - self.turn_start_time
        else:
            self.white_time += current_time - self.turn_start_time
        self.turn_start_time = current_time

    def select(self, row, col):
        if self.selected:
            result = self._move(row, col)
            if not result:
                self.selected = None
                self.select(row, col)

        piece = self.board.get_piece(row, col)
        if piece != 0 and piece.color == self.turn:
            self.selected = piece
            self.valid_moves = self.board.get_valid_moves(piece)
            return True

        return False

    def _move(self, row, col):
        piece = self.board.get_piece(row, col)
        if self.selected and piece == 0 and (row, col) in self.valid_moves:
            self.board.move(self.selected, row, col)
            skipped = self.valid_moves[(row, col)]
            if skipped:
                self.board.remove(skipped)
            self.change_turn()
        else:
            return False

        return True

    def draw_valid_moves(self, moves):
        for move in moves:
            row, col = move
            pygame.draw.circle(self.screen, GREEN,
                               (col * SQUARE_SIZE + SQUARE_SIZE // 2, row * SQUARE_SIZE + SQUARE_SIZE // 2), 15)

    def get_board(self):
        return self.board

    def ai_move(self):
        piece = random.choice([p for row in self.board.board for p in row if p != 0 and p.color == self.turn])
        valid_moves = self.board.get_valid_moves(piece)
        if valid_moves:
            move = random.choice(list(valid_moves.keys()))
            self.select(piece.row, piece.col)
            self._move(move[0], move[1])

    def get_hint(self):
        for row in self.board.board:
            for piece in row:
                if piece != 0 and piece.color == self.turn:
                    valid_moves = self.board.get_valid_moves(piece)
                    if valid_moves:
                        return piece, random.choice(list(valid_moves.keys()))
        return None

    def draw_hint(self, hint):
        if hint:
            piece, move = hint
            pygame.draw.circle(self.screen, BLUE,
                               (piece.col * SQUARE_SIZE + SQUARE_SIZE // 2, piece.row * SQUARE_SIZE + SQUARE_SIZE // 2),
                               15)
            pygame.draw.circle(self.screen, BLUE,
                               (move[1] * SQUARE_SIZE + SQUARE_SIZE // 2, move[0] * SQUARE_SIZE + SQUARE_SIZE // 2), 15)

    def serialize(self):
        return {
            'board': self.board.serialize(),
            'turn': self.turn,
            'single_player': self.single_player,
            'hint_mode': self.hint_mode
        }

    @classmethod
    def deserialize(cls, screen, data):
        game = cls(screen, single_player=data['single_player'])
        game.board = Board.deserialize(data['board'])
        game.turn = data['turn']
        game.hint_mode = data['hint_mode']
        return game

    def check_for_win(self):
        red_pieces = [p for row in self.board.board for p in row if p != 0 and p.color == RED]
        white_pieces = [p for row in self.board.board for p in row if p != 0 and p.color == WHITE]
        
        if not red_pieces:
            self.display_winner("White")
            return True
        elif not white_pieces:
            self.display_winner("Red")
            return True
        
        red_moves = any(self.board.get_valid_moves(p) for p in red_pieces)
        white_moves = any(self.board.get_valid_moves(p) for p in white_pieces)
        
        if not red_moves:
            self.display_winner("White")
            return True
        elif not white_moves:
            self.display_winner("Red")
            return True
        
        return False

    def display_winner(self, winner):
        font = pygame.font.Font(None, 74)
        text = font.render(f"Congratulations {winner}, you win!", True, BLUE)
        text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        self.screen.blit(text, text_rect)
        
        pygame.display.update()
        pygame.time.wait(3000)  # Wait for 3 seconds
        
        self.game_over = True
        self.game_end_time = time.time()

def format_time(seconds):
    minutes, seconds = divmod(int(seconds), 60)
    return f"{minutes:02d}:{seconds:02d}"

def draw_in_game_menu(screen, game):
    menu_rect = pygame.Rect(BOARD_WIDTH, 0, MENU_WIDTH, HEIGHT)
    pygame.draw.rect(screen, WHITE, menu_rect)
    
    font = pygame.font.Font(None, 36)
    
    buttons = [
        ("New Game", HEIGHT // 2 - 200),
        ("Single Player", HEIGHT // 2 - 100),
        ("Multiplayer", HEIGHT // 2),
        ("Save Game", HEIGHT // 2 + 100),
        ("Load Game", HEIGHT // 2 + 200),
        ("Quit", HEIGHT // 2 + 300)
    ]
    
    for text, y in buttons:
        button_text = font.render(text, True, BLACK)
        text_rect = button_text.get_rect(center=(BOARD_WIDTH + MENU_WIDTH // 2, y))
        screen.blit(button_text, text_rect)

    if game.game_over:
        game_over_text = font.render("Game Over", True, RED)
        screen.blit(game_over_text, (BOARD_WIDTH + 10, 150))

    # Display current player's turn
    if not game.game_over:
        turn_text = font.render(f"Current Turn: {'Red' if game.turn == RED else 'White'}", True, BLACK)
    else:
        turn_text = font.render("Game Finished", True, BLACK)
    screen.blit(turn_text, (BOARD_WIDTH + 10, 50))

    # Display overall timer
    overall_time = game.red_time + game.white_time
    if game.game_over:
        overall_time = game.game_end_time - game.turn_start_time + overall_time
    overall_timer = font.render(f"Overall Time: {format_time(overall_time)}", True, BLACK)
    screen.blit(overall_timer, (BOARD_WIDTH + 10, 100))

def save_game(game):
    with open("checkers_save.json", "w") as f:
        json.dump(game.serialize(), f)
    print("Game saved.")

def load_game(screen):
    try:
        with open("checkers_save.json", "r") as f:
            data = json.load(f)
        return Game.deserialize(screen, data)
    except FileNotFoundError:
        print("No saved game found.")
        return None

def main():
    clock = pygame.time.Clock()
    game = Game(screen)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                x, y = pygame.mouse.get_pos()
                if x < BOARD_WIDTH and not game.game_over:
                    row, col = y // SQUARE_SIZE, x // SQUARE_SIZE
                    game.select(row, col)
                elif x > BOARD_WIDTH:
                    # Menu button clicks
                    if BOARD_WIDTH + 50 < x < WIDTH - 50:
                        if HEIGHT // 2 - 225 < y < HEIGHT // 2 - 175:
                            game = Game(screen)
                        elif HEIGHT // 2 - 125 < y < HEIGHT // 2 - 75:
                            game = Game(screen, single_player=True)
                        elif HEIGHT // 2 - 25 < y < HEIGHT // 2 + 25:
                            game = Game(screen, single_player=False)
                        elif HEIGHT // 2 + 75 < y < HEIGHT // 2 + 125:
                            save_game(game)
                        elif HEIGHT // 2 + 175 < y < HEIGHT // 2 + 225:
                            loaded_game = load_game(screen)
                            if loaded_game:
                                game = loaded_game
                        elif HEIGHT // 2 + 275 < y < HEIGHT // 2 + 325:
                            pygame.quit()
                            sys.exit()

        if game.single_player and game.turn == WHITE and not game.game_over:
            game.ai_move()

        game.update()

        if game.hint_mode and not game.game_over:
            hint = game.get_hint()
            game.draw_hint(hint)

        clock.tick(60)
if __name__ == "__main__":
    main()
