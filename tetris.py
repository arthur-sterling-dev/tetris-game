"""
Tetris — a modern, restyled falling-blocks game built with Pygame.

Modern features:
    * Sleek dark UI with gradient-shaded, glossy blocks and rounded panels
    * Hold Piece mechanic   (swap the active piece into a hold slot)
    * Combo scoring system  (chained line clears award escalating bonuses)
    * Screen shake feedback  (a satisfying jolt on every hard drop)

Controls:
    Left / Right arrows : move the piece horizontally
    Down arrow          : soft drop (move down faster)
    Up arrow / X        : rotate clockwise
    Z                   : rotate counter-clockwise
    Space               : hard drop (instantly drop the piece)
    C / Shift           : hold piece (swap with the hold slot)
    P                   : pause / resume
    R                   : restart (after Game Over)
    Esc                 : quit
"""

import math
import random
import sys

import pygame

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CELL_SIZE = 32          # pixel size of a single cell
COLUMNS = 10            # board width in cells
ROWS = 20               # board height in cells

PLAY_WIDTH = COLUMNS * CELL_SIZE
PLAY_HEIGHT = ROWS * CELL_SIZE

BOARD_MARGIN = 24       # gap around the playfield
SIDEBAR_WIDTH = 200
HOLD_WIDTH = 160

SCREEN_WIDTH = HOLD_WIDTH + PLAY_WIDTH + SIDEBAR_WIDTH + BOARD_MARGIN * 2
SCREEN_HEIGHT = PLAY_HEIGHT + BOARD_MARGIN * 2

# Where the playfield is drawn on screen.
BOARD_X = HOLD_WIDTH + BOARD_MARGIN
BOARD_Y = BOARD_MARGIN

FPS = 60

# ---------------------------------------------------------------------------
# Modern colour palette (deep slate background, neon-leaning accents)
# ---------------------------------------------------------------------------
BG_TOP = (18, 18, 28)
BG_BOTTOM = (30, 30, 46)
PANEL = (26, 27, 42)
PANEL_BORDER = (58, 60, 90)
GRID_LINE = (44, 46, 70)
WELL_BG = (14, 14, 22)
TEXT = (228, 230, 245)
TEXT_DIM = (140, 144, 175)
ACCENT = (122, 162, 255)
GHOST = (120, 124, 160)

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

# Vibrant, slightly desaturated modern colours for each piece.
SHAPE_COLORS = {
    "I": (38, 198, 218),
    "O": (255, 202, 40),
    "T": (171, 71, 188),
    "S": (102, 187, 106),
    "Z": (239, 83, 80),
    "J": (66, 133, 244),
    "L": (255, 138, 60),
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


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------
def _shade(color, factor):
    """Lighten (factor > 1) or darken (factor < 1) a colour, clamped to 0-255."""
    return tuple(max(0, min(255, int(c * factor))) for c in color)


def vertical_gradient(surface, top_color, bottom_color):
    """Fill a surface with a smooth vertical gradient."""
    height = surface.get_height()
    width = surface.get_width()
    for y in range(height):
        t = y / max(1, height - 1)
        color = (
            int(top_color[0] + (bottom_color[0] - top_color[0]) * t),
            int(top_color[1] + (bottom_color[1] - top_color[1]) * t),
            int(top_color[2] + (bottom_color[2] - top_color[2]) * t),
        )
        pygame.draw.line(surface, color, (0, y), (width, y))


def draw_block(surface, px, py, color, size=CELL_SIZE):
    """Draw a single glossy block with a gradient body, highlight and shadow."""
    rect = pygame.Rect(px, py, size, size)

    # Gradient body (top lighter, bottom darker) for a rounded, 3D look.
    body = pygame.Surface((size, size))
    vertical_gradient(body, _shade(color, 1.18), _shade(color, 0.72))
    surface.blit(body, (px, py))

    # Inner glossy highlight near the top-left.
    highlight = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.rect(highlight, (255, 255, 255, 55),
                     pygame.Rect(3, 3, size - 6, max(2, size // 4)), border_radius=4)
    surface.blit(highlight, (px, py))

    # Bottom shadow strip for depth.
    shadow = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.rect(shadow, (0, 0, 0, 70),
                     pygame.Rect(2, size - max(3, size // 5), size - 4, max(2, size // 6)),
                     border_radius=4)
    surface.blit(shadow, (px, py))

    # Crisp rounded border.
    pygame.draw.rect(surface, _shade(color, 1.35), rect, 1, border_radius=4)


def draw_well(surface):
    """Draw the playfield background well with grid lines."""
    well = pygame.Rect(BOARD_X, BOARD_Y, PLAY_WIDTH, PLAY_HEIGHT)
    pygame.draw.rect(surface, WELL_BG, well, border_radius=6)

    for x in range(COLUMNS + 1):
        gx = BOARD_X + x * CELL_SIZE
        pygame.draw.line(surface, GRID_LINE, (gx, BOARD_Y), (gx, BOARD_Y + PLAY_HEIGHT))
    for y in range(ROWS + 1):
        gy = BOARD_Y + y * CELL_SIZE
        pygame.draw.line(surface, GRID_LINE, (BOARD_X, gy), (BOARD_X + PLAY_WIDTH, gy))

    pygame.draw.rect(surface, PANEL_BORDER, well, 2, border_radius=6)


def draw_board(surface, board):
    """Draw the locked cells inside the well."""
    for y in range(ROWS):
        for x in range(COLUMNS):
            if board[y][x] is not None:
                draw_block(surface, BOARD_X + x * CELL_SIZE, BOARD_Y + y * CELL_SIZE, board[y][x])


def draw_piece(surface, piece):
    """Draw the active falling piece."""
    for cx, cy in piece.cells():
        if cy >= 0:
            draw_block(surface, BOARD_X + cx * CELL_SIZE, BOARD_Y + cy * CELL_SIZE, piece.color)


def draw_ghost(surface, piece, board):
    """Draw a translucent preview of where the piece will land."""
    ghost_y = piece.y
    while valid_position(piece, board, y=ghost_y + 1):
        ghost_y += 1
    for cx, cy in piece.cells(y=ghost_y):
        if cy >= 0:
            rect = pygame.Rect(BOARD_X + cx * CELL_SIZE, BOARD_Y + cy * CELL_SIZE,
                               CELL_SIZE, CELL_SIZE)
            overlay = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
            pygame.draw.rect(overlay, (*piece.color, 45),
                             overlay.get_rect(), border_radius=4)
            surface.blit(overlay, rect.topleft)
            pygame.draw.rect(surface, GHOST, rect, 2, border_radius=4)


def draw_panel(surface, rect, title, font):
    """Draw a rounded panel with a title; return the content y-offset."""
    pygame.draw.rect(surface, PANEL, rect, border_radius=10)
    pygame.draw.rect(surface, PANEL_BORDER, rect, 2, border_radius=10)
    if title:
        label = font.render(title, True, TEXT_DIM)
        surface.blit(label, (rect.x + 14, rect.y + 10))


def draw_mini_piece(surface, piece, area):
    """Draw a piece centred inside a small preview area (a pygame.Rect)."""
    if piece is None:
        return
    mini = max(16, CELL_SIZE - 8)
    state = piece.rotations[0]
    xs = [cx for cx, _ in state]
    ys = [cy for _, cy in state]
    w = (max(xs) - min(xs) + 1) * mini
    h = (max(ys) - min(ys) + 1) * mini
    start_x = area.x + (area.width - w) // 2 - min(xs) * mini
    start_y = area.y + (area.height - h) // 2 - min(ys) * mini
    for cx, cy in state:
        draw_block(surface, start_x + cx * mini, start_y + cy * mini, piece.color, mini)


def draw_hold(surface, font, hold_piece, can_hold):
    """Draw the Hold panel on the left side."""
    rect = pygame.Rect(BOARD_MARGIN // 2, BOARD_Y, HOLD_WIDTH - BOARD_MARGIN, 150)
    draw_panel(surface, rect, "HOLD", font)
    area = pygame.Rect(rect.x, rect.y + 36, rect.width, rect.height - 46)
    # Dim the held piece when it can't be swapped again this turn.
    if hold_piece is not None and not can_hold:
        faded = Piece(hold_piece.name)
        faded.color = _shade(hold_piece.color, 0.55)
        draw_mini_piece(surface, faded, area)
    else:
        draw_mini_piece(surface, hold_piece, area)


def draw_sidebar(surface, font, big_font, small_font, stats, next_piece):
    """Draw the score panel, combo readout, and next-piece preview."""
    sx = BOARD_X + PLAY_WIDTH + BOARD_MARGIN

    # Score / level / lines panel.
    stats_rect = pygame.Rect(sx, BOARD_Y, SIDEBAR_WIDTH - BOARD_MARGIN, 200)
    draw_panel(surface, stats_rect, "STATS", font)

    def stat(label_text, value, y, value_color=TEXT):
        surface.blit(small_font.render(label_text, True, TEXT_DIM), (stats_rect.x + 14, y))
        val = big_font.render(str(value), True, value_color)
        surface.blit(val, (stats_rect.x + 14, y + 18))

    stat("SCORE", f"{stats['score']:,}", stats_rect.y + 40)
    stat("LEVEL", stats["level"], stats_rect.y + 100, ACCENT)
    surface.blit(small_font.render("LINES", True, TEXT_DIM), (stats_rect.x + 110, stats_rect.y + 100))
    surface.blit(big_font.render(str(stats["lines"]), True, TEXT),
                 (stats_rect.x + 110, stats_rect.y + 118))

    # Combo panel — highlighted when a combo chain is active.
    combo_rect = pygame.Rect(sx, stats_rect.bottom + 16, SIDEBAR_WIDTH - BOARD_MARGIN, 90)
    draw_panel(surface, combo_rect, "COMBO", font)
    combo = stats["combo"]
    if combo > 0:
        # Pulsing accent colour while the combo runs.
        pulse = 0.6 + 0.4 * abs(math.sin(stats["time"] / 180.0))
        color = _shade((255, 170, 60), pulse)
        text = big_font.render(f"x{combo}", True, color)
        surface.blit(text, (combo_rect.x + 14, combo_rect.y + 36))
        surface.blit(small_font.render(f"BEST x{stats['max_combo']}", True, TEXT_DIM),
                     (combo_rect.x + 90, combo_rect.y + 50))
    else:
        surface.blit(small_font.render("—", True, TEXT_DIM),
                     (combo_rect.x + 14, combo_rect.y + 42))
        surface.blit(small_font.render(f"BEST x{stats['max_combo']}", True, TEXT_DIM),
                     (combo_rect.x + 90, combo_rect.y + 50))

    # Next-piece panel.
    next_rect = pygame.Rect(sx, combo_rect.bottom + 16, SIDEBAR_WIDTH - BOARD_MARGIN, 150)
    draw_panel(surface, next_rect, "NEXT", font)
    area = pygame.Rect(next_rect.x, next_rect.y + 36, next_rect.width, next_rect.height - 46)
    draw_mini_piece(surface, next_piece, area)


def draw_overlay(surface, big_font, small_font, title, subtitle):
    """Dim the playfield and show a centred message."""
    overlay = pygame.Surface((PLAY_WIDTH, PLAY_HEIGHT), pygame.SRCALPHA)
    overlay.fill((10, 10, 16, 200))
    surface.blit(overlay, (BOARD_X, BOARD_Y))

    cx = BOARD_X + PLAY_WIDTH // 2
    cy = BOARD_Y + PLAY_HEIGHT // 2
    title_render = big_font.render(title, True, TEXT)
    surface.blit(title_render, title_render.get_rect(center=(cx, cy - 16)))
    if subtitle:
        sub_render = small_font.render(subtitle, True, TEXT_DIM)
        surface.blit(sub_render, sub_render.get_rect(center=(cx, cy + 24)))


def main():
    pygame.init()
    pygame.display.set_caption("Tetris — Modern Edition")
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 18, bold=True)
    small_font = pygame.font.SysFont("consolas", 15)
    big_font = pygame.font.SysFont("consolas", 30, bold=True)
    huge_font = pygame.font.SysFont("consolas", 40, bold=True)

    # Pre-render the static background gradient once.
    background = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    vertical_gradient(background, BG_TOP, BG_BOTTOM)

    board = new_board()
    bag = random_bag()
    current = Piece(bag.pop())
    next_piece = Piece(bag.pop())

    hold_piece = None
    can_hold = True

    score = 0
    lines_cleared_total = 0
    level = 1
    combo = 0          # current combo chain length
    max_combo = 0      # best combo achieved this game
    total_time = 0     # ms elapsed, used for animation pulses

    fall_time = 0
    fall_speed = 500   # ms between automatic drops; decreases as level rises

    # Screen-shake state (Innovation #3).
    shake_time = 0
    shake_intensity = 0

    game_over = False
    paused = False

    def trigger_shake(intensity, duration):
        """Start a screen-shake effect."""
        nonlocal shake_time, shake_intensity
        shake_time = duration
        shake_intensity = intensity

    def spawn_next():
        """Pull the next piece and refill the bag when empty."""
        nonlocal current, next_piece, bag, can_hold
        current = next_piece
        if not bag:
            bag = random_bag()
        next_piece = Piece(bag.pop())
        can_hold = True

    def resolve_lock(hard_drop_cells=0):
        """Lock the current piece, clear lines, update score/combo, and spawn."""
        nonlocal score, lines_cleared_total, combo, max_combo, game_over
        lock_piece(current, board)
        cleared = clear_lines(board)
        lines_cleared_total += cleared
        if cleared > 0:
            score += {1: 100, 2: 300, 3: 500, 4: 800}[cleared] * level
            # Combo scoring system (Innovation #2): each consecutive clear
            # extends the chain and awards an escalating bonus.
            score += 50 * combo * level
            combo += 1
            max_combo = max(max_combo, combo)
            # Bigger shake for bigger clears.
            trigger_shake(4 + cleared * 3, 220)
        else:
            combo = 0
        spawn_next()
        if not valid_position(current, board):
            game_over = True

    def reset_game():
        """Reset all state for a fresh game."""
        nonlocal board, bag, current, next_piece, hold_piece, can_hold
        nonlocal score, lines_cleared_total, level, combo, max_combo
        nonlocal fall_time, fall_speed, game_over, paused
        board = new_board()
        bag = random_bag()
        current = Piece(bag.pop())
        next_piece = Piece(bag.pop())
        hold_piece = None
        can_hold = True
        score = 0
        lines_cleared_total = 0
        level = 1
        combo = 0
        max_combo = 0
        fall_time = 0
        fall_speed = 500
        game_over = False
        paused = False

    running = True
    while running:
        dt = clock.tick(FPS)
        total_time += dt
        if not game_over and not paused:
            fall_time += dt
        if shake_time > 0:
            shake_time = max(0, shake_time - dt)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                elif event.key == pygame.K_p and not game_over:
                    paused = not paused

                elif game_over and event.key == pygame.K_r:
                    reset_game()

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
                    elif event.key in (pygame.K_c, pygame.K_LSHIFT, pygame.K_RSHIFT):
                        # Hold Piece mechanic (Innovation #1): swap the active
                        # piece with the held one — but only once per drop.
                        if can_hold:
                            if hold_piece is None:
                                hold_piece = Piece(current.name)
                                spawn_next()
                            else:
                                swapped = hold_piece.name
                                hold_piece = Piece(current.name)
                                current = Piece(swapped)
                            can_hold = False
                            fall_time = 0
                    elif event.key == pygame.K_SPACE:
                        drop_distance = 0
                        while valid_position(current, board, y=current.y + 1):
                            current.y += 1
                            score += 2
                            drop_distance += 1
                        # Screen shake scales with how far the piece fell.
                        trigger_shake(3 + min(drop_distance, 12), 180)
                        resolve_lock()
                        fall_time = 0

        # Automatic falling.
        if not game_over and not paused and fall_time >= fall_speed:
            fall_time = 0
            if valid_position(current, board, y=current.y + 1):
                current.y += 1
            else:
                resolve_lock()

        # Level progression: every 10 cleared lines speeds up the fall.
        level = 1 + lines_cleared_total // 10
        fall_speed = max(80, 500 - (level - 1) * 40)

        # ------------------------------------------------------------------
        # Rendering
        # ------------------------------------------------------------------
        # Compute the screen-shake offset for this frame.
        offset_x = offset_y = 0
        if shake_time > 0 and shake_intensity > 0:
            mag = shake_intensity * (shake_time / 220.0)
            offset_x = int(math.sin(total_time / 13.0) * mag)
            offset_y = int(math.cos(total_time / 11.0) * mag)

        frame = screen
        frame.blit(background, (0, 0))

        # We shift the playfield by the shake offset by drawing the well and its
        # contents into a temp surface, then blitting it with the offset.
        field = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        draw_well(field)
        draw_board(field, board)
        if not game_over:
            draw_ghost(field, current, board)
            draw_piece(field, current)
        frame.blit(field, (offset_x, offset_y))

        # Static UI panels (not shaken) drawn on top.
        draw_hold(frame, font, hold_piece, can_hold)
        stats = {
            "score": score,
            "level": level,
            "lines": lines_cleared_total,
            "combo": combo,
            "max_combo": max_combo,
            "time": total_time,
        }
        draw_sidebar(frame, font, big_font, small_font, stats, next_piece)

        if paused:
            draw_overlay(frame, huge_font, small_font, "PAUSED", "Press P to resume")
        if game_over:
            draw_overlay(frame, huge_font, small_font, "GAME OVER", "Press R to play again")

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
