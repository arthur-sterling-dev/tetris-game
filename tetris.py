"""
Tetris — a classic falling-blocks game built with Pygame.

Controls:
    Left / Right arrows : move the piece horizontally
    Down arrow          : soft drop (move down faster)
    Up arrow / X        : rotate clockwise
    Z                   : rotate counter-clockwise
    Space               : hard drop (instantly drop the piece)
    P                   : pause / resume
    Esc                 : quit
"""

import random
import sys

import pygame

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CELL_SIZE = 30          # pixel size of a single cell
COLUMNS = 10            # board width in cells
ROWS = 20               # board height in cells

PLAY_WIDTH = COLUMNS * CELL_SIZE
PLAY_HEIGHT = ROWS * CELL_SIZE

SIDEBAR_WIDTH = 6 * CELL_SIZE
SCREEN_WIDTH = PLAY_WIDTH + SIDEBAR_WIDTH
SCREEN_HEIGHT = PLAY_HEIGHT

FPS = 60

# Colours
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREY = (40, 40, 40)
LIGHT_GREY = (90, 90, 90)

# The seven tetromino shapes, defined on a 4x4 grid using rotation states.
# Each shape is a list of rotation states; each state is a list of (x, y) offsets.
SHAPES = {
    "I": [[(0, 1), (1, 1), (2, 1), (3, 1)],
          [(2, 0), (2, 1), (2, 2), (2, 3)],
          [(0, 2), (1, 2), (2, 2), (3, 2)],
          [(1, 0), (1, 1), (1, 2), (1, 3)]],
    "O": [[(1, 0), (2, 0), (1, 1), (2, 1)]],
    "T": [[(1, 0), (0, 1), (1, 1), (2, 1)],
          [(1, 0), (1, 1), (2, 1), (1, 2)],
          [(0, 1), (1, 1), (2, 1), (1, 2)],
          [(1, 0), (0, 1), (1, 1), (1, 2)]],
    "S": [[(1, 0), (2, 0), (0, 1), (1, 1)],
          [(1, 0), (1, 1), (2, 1), (2, 2)],
          [(1, 1), (2, 1), (0, 2), (1, 2)],
          [(0, 0), (0, 1), (1, 1), (1, 2)]],
    "Z": [[(0, 0), (1, 0), (1, 1), (2, 1)],
          [(2, 0), (1, 1), (2, 1), (1, 2)],
          [(0, 1), (1, 1), (1, 2), (2, 2)],
          [(1, 0), (0, 1), (1, 1), (0, 2)]],
    "J": [[(0, 0), (0, 1), (1, 1), (2, 1)],
          [(1, 0), (2, 0), (1, 1), (1, 2)],
          [(0, 1), (1, 1), (2, 1), (2, 2)],
          [(1, 0), (1, 1), (0, 2), (1, 2)]],
    "L": [[(2, 0), (0, 1), (1, 1), (2, 1)],
          [(1, 0), (1, 1), (1, 2), (2, 2)],
          [(0, 1), (1, 1), (2, 1), (0, 2)],
          [(0, 0), (1, 0), (1, 1), (1, 2)]],
}

SHAPE_COLORS = {
    "I": (0, 240, 240),
    "O": (240, 240, 0),
    "T": (160, 0, 240),
    "S": (0, 240, 0),
    "Z": (240, 0, 0),
    "J": (0, 0, 240),
    "L": (240, 160, 0),
}


class Piece:
    """A falling tetromino piece."""

    def __init__(self, shape_name):
        self.name = shape_name
        self.rotations = SHAPES[shape_name]
        self.color = SHAPE_COLORS[shape_name]
        self.rotation = 0
        # Spawn near the top-centre of the board.
        self.x = COLUMNS // 2 - 2
        self.y = -1

    def cells(self, rotation=None, x=None, y=None):
        """Return the absolute board coordinates occupied by the piece."""
        rotation = self.rotation if rotation is None else rotation
        x = self.x if x is None else x
        y = self.y if y is None else y
        state = self.rotations[rotation % len(self.rotations)]
        return [(x + cx, y + cy) for cx, cy in state]


def new_board():
    """Create an empty board grid filled with None."""
    return [[None for _ in range(COLUMNS)] for _ in range(ROWS)]


def valid_position(piece, board, rotation=None, x=None, y=None):
    """Check whether the piece fits at the given position without collisions."""
    for cx, cy in piece.cells(rotation, x, y):
        if cx < 0 or cx >= COLUMNS or cy >= ROWS:
            return False
        if cy >= 0 and board[cy][cx] is not None:
            return False
    return True


def lock_piece(piece, board):
    """Freeze the piece into the board grid."""
    for cx, cy in piece.cells():
        if 0 <= cy < ROWS and 0 <= cx < COLUMNS:
            board[cy][cx] = piece.color


def clear_lines(board):
    """Remove completed lines and return the number cleared."""
    remaining = [row for row in board if any(cell is None for cell in row)]
    cleared = ROWS - len(remaining)
    for _ in range(cleared):
        remaining.insert(0, [None for _ in range(COLUMNS)])
    board[:] = remaining
    return cleared


def random_bag():
    """Return a shuffled bag of all seven shapes (7-bag randomiser)."""
    bag = list(SHAPES.keys())
    random.shuffle(bag)
    return bag


def draw_cell(surface, x, y, color, offset_x=0):
    """Draw a single filled cell with a subtle border."""
    rect = pygame.Rect(offset_x + x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
    pygame.draw.rect(surface, color, rect)
    pygame.draw.rect(surface, BLACK, rect, 1)


def draw_board(surface, board):
    """Draw the locked cells and the grid lines."""
    for y in range(ROWS):
        for x in range(COLUMNS):
            if board[y][x] is not None:
                draw_cell(surface, x, y, board[y][x])
    # Grid lines
    for x in range(COLUMNS + 1):
        pygame.draw.line(surface, GREY, (x * CELL_SIZE, 0), (x * CELL_SIZE, PLAY_HEIGHT))
    for y in range(ROWS + 1):
        pygame.draw.line(surface, GREY, (0, y * CELL_SIZE), (PLAY_WIDTH, y * CELL_SIZE))


def draw_piece(surface, piece):
    """Draw the active falling piece."""
    for cx, cy in piece.cells():
        if cy >= 0:
            draw_cell(surface, cx, cy, piece.color)


def draw_ghost(surface, piece, board):
    """Draw a translucent preview of where the piece will land."""
    ghost_y = piece.y
    while valid_position(piece, board, y=ghost_y + 1):
        ghost_y += 1
    for cx, cy in piece.cells(y=ghost_y):
        if cy >= 0:
            rect = pygame.Rect(cx * CELL_SIZE, cy * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(surface, LIGHT_GREY, rect, 2)


def draw_sidebar(surface, font, score, level, lines, next_piece):
    """Draw the score panel and the preview of the next piece."""
    base_x = PLAY_WIDTH + 20

    def label(text, y, color=WHITE):
        surface.blit(font.render(text, True, color), (base_x, y))

    label("TETRIS", 20)
    label(f"Score: {score}", 70)
    label(f"Level: {level}", 110)
    label(f"Lines: {lines}", 150)
    label("Next:", 210)

    # Draw the next piece preview.
    preview_origin_x = PLAY_WIDTH + 20
    preview_origin_y = 250
    state = next_piece.rotations[0]
    for cx, cy in state:
        rect = pygame.Rect(
            preview_origin_x + cx * CELL_SIZE,
            preview_origin_y + cy * CELL_SIZE,
            CELL_SIZE,
            CELL_SIZE,
        )
        pygame.draw.rect(surface, next_piece.color, rect)
        pygame.draw.rect(surface, BLACK, rect, 1)


def draw_text_center(surface, font, text, color=WHITE):
    """Draw a line of text centred over the play field."""
    render = font.render(text, True, color)
    rect = render.get_rect(center=(PLAY_WIDTH // 2, PLAY_HEIGHT // 2))
    surface.blit(render, rect)


def main():
    pygame.init()
    pygame.display.set_caption("Tetris")
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 24)
    big_font = pygame.font.SysFont("consolas", 36)

    board = new_board()
    bag = random_bag()
    current = Piece(bag.pop())
    next_piece = Piece(bag.pop())

    score = 0
    lines_cleared_total = 0
    level = 1

    fall_time = 0
    # Milliseconds between automatic drops; decreases as the level rises.
    fall_speed = 500

    game_over = False
    paused = False

    def spawn_next():
        """Pull the next piece and refill the bag when empty."""
        nonlocal current, next_piece, bag
        current = next_piece
        if not bag:
            bag = random_bag()
        next_piece = Piece(bag.pop())

    running = True
    while running:
        dt = clock.tick(FPS)
        if not game_over and not paused:
            fall_time += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                elif event.key == pygame.K_p and not game_over:
                    paused = not paused

                elif game_over and event.key == pygame.K_r:
                    # Restart the game.
                    board = new_board()
                    bag = random_bag()
                    current = Piece(bag.pop())
                    next_piece = Piece(bag.pop())
                    score = 0
                    lines_cleared_total = 0
                    level = 1
                    fall_time = 0
                    fall_speed = 500
                    game_over = False

                elif not game_over and not paused:
                    if event.key == pygame.K_LEFT:
                        if valid_position(current, board, x=current.x - 1):
                            current.x -= 1
                    elif event.key == pygame.K_RIGHT:
                        if valid_position(current, board, x=current.x + 1):
                            current.x += 1
                    elif event.key == pygame.K_DOWN:
                        if valid_position(current, board, y=current.y + 1):
                            current.y += 1
                            score += 1
                    elif event.key in (pygame.K_UP, pygame.K_x):
                        new_rotation = current.rotation + 1
                        if valid_position(current, board, rotation=new_rotation):
                            current.rotation = new_rotation % len(current.rotations)
                    elif event.key == pygame.K_z:
                        new_rotation = current.rotation - 1
                        if valid_position(current, board, rotation=new_rotation):
                            current.rotation = new_rotation % len(current.rotations)
                    elif event.key == pygame.K_SPACE:
                        while valid_position(current, board, y=current.y + 1):
                            current.y += 1
                            score += 2
                        lock_piece(current, board)
                        cleared = clear_lines(board)
                        lines_cleared_total += cleared
                        score += {0: 0, 1: 100, 2: 300, 3: 500, 4: 800}[cleared] * level
                        spawn_next()
                        if not valid_position(current, board):
                            game_over = True
                        fall_time = 0

        # Automatic falling.
        if not game_over and not paused and fall_time >= fall_speed:
            fall_time = 0
            if valid_position(current, board, y=current.y + 1):
                current.y += 1
            else:
                lock_piece(current, board)
                cleared = clear_lines(board)
                lines_cleared_total += cleared
                score += {0: 0, 1: 100, 2: 300, 3: 500, 4: 800}[cleared] * level
                spawn_next()
                if not valid_position(current, board):
                    game_over = True

        # Level progression: every 10 cleared lines speeds up the fall.
        level = 1 + lines_cleared_total // 10
        fall_speed = max(80, 500 - (level - 1) * 40)

        # Rendering.
        screen.fill(BLACK)
        draw_board(screen, board)
        if not game_over:
            draw_ghost(screen, current, board)
            draw_piece(screen, current)
        draw_sidebar(screen, font, score, level, lines_cleared_total, next_piece)

        if paused:
            draw_text_center(screen, big_font, "PAUSED")
        if game_over:
            draw_text_center(screen, big_font, "GAME OVER - press R")

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
