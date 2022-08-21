#!/usr/bin/python3

# E.g.
# python3 wine.py
# python3 wine.py r[ows]=16 c[ols]=16 w[ines]=24

import tkinter as tk
import tkinter.font as font
from enum import Enum
from random import randint
from sys import argv



# Represents the current phase of the game - used with GameController->set_state
class GameState(Enum):
    PLAYING = 1
    WIN = 2
    LOSS = 3



# Value storage mule
class Constants:
    rows: 8
    cols: 8
    wines: 8
    colors = {
        -1: '#000000', # wine
        0: '#bbbbbb',  # empty
        1: '#0000FA',
        2: '#4B802D',
        3: '#DB1300',
        4: '#202081',
        5: '#690400',
        6: '#457A7A',
        7: '#1B1B1B',
        8: '#7A7A7A',
    }
    glyphs = {
        'WATER': '🚰',
        'WINE': '🍷',
        'FLAG': '🚩',
        'BLOCK': '█',
        'FACE_PLAYING': '🤔',
        'FACE_WIN': '😊',
        'FACE_LOSS': '🥴', # see doctor
    }
    _prefix_map = {
        'r': 'rows',
        'c': 'cols',
        'w': 'wines',
    }

    @classmethod
    def evaluate_post_root(cls):
        cls._initialize_tk_root_dependents()
        cls._parse_script_parameters()

    @classmethod
    def _initialize_tk_root_dependents(cls):
        cls.empty_pixels = tk.PhotoImage(width = 0, height = 0)
        cls.button_font = font.Font(size = 18, weight = 'bold')
        cls.start_button_font = font.Font(size = 36, weight = 'bold')

    @classmethod
    def _parse_script_parameters(cls):
        params = {
            'rows': 8,
            'cols': 8,
            'wines': 8,
        }
        pdict = dict(s.split('=') for s in argv[1:])
        for k in pdict:
            first = k[:1].lower()
            if first in cls._prefix_map:
                key = cls._prefix_map[first]
                try:
                    params[key] = int(pdict[k])
                except ValueError:
                    pass
        # Normalize the number of wines to the rows * cols before copying vals to class
        params['wines'] = max(1, min(params['wines'], params['rows'] * params['cols']))
        cls.rows = params['rows']
        cls.cols = params['cols']
        cls.wines = params['wines']



# Extention of tk.Button for winesweeper functions
# This represents a cell on the board
class FieldButton(tk.Button):
    def __init__(self, controller, tk_parent, x, y):
        self._controller = controller
        self.x = x
        self.y = y
        super().__init__(tk_parent,
                text = '',
                font = Constants.button_font,
                image = Constants.empty_pixels, # allow for pixel sizing
                compound = 'c',
                border = 0,
                width = 24,
                height = 24)
        super().grid(row = y, column = x)
        self.bind('<Button-1>', self._leftclick)
        self.bind('<Button-2>', self._rightclick)
        self.bind('<Button-3>', self._rightclick)

    def flag(self, flagged=True):
        self.configure(text = flagged and Constants.glyphs['FLAG'] or '')

    def reveal(self, value):
        text = '%d' % value
        if value == -1:
            text = Constants.glyphs['WINE']
        elif value == 0:
            text = Constants.glyphs['BLOCK']
        self.configure(fg = Constants.colors[value], text = text)

    def _leftclick(self, event):
        self._controller.do_left_click(self.x, self.y)

    def _rightclick(self, event):
        self._controller.do_right_click(self.x, self.y)



# Used for organizing logic within the search for open empty spaces (GameController->_crawl_blank_field)
class CrawlInfo:
    def __init__(self):
        self._empties = []

    @property
    def empties(self) -> list:
        return self._empties

    def add_empty(self, x, y):
        self._empties.append((x, y))

    def is_visited(self, x, y) -> bool:
        return (x, y) in self._empties



# Primary game logic
class GameController:

    def __init__(self, tk_root):
        self._create_ui(tk_root)
        self.generate_game()

    # Invoked from a cell's FieldButton
    def do_left_click(self, x, y):
        boardscore = self._winefield[y][x]
        if boardscore == -1:
            self.set_state(GameState.LOSS)
        elif boardscore > 0:
            self._reveal(x, y)
        else:
            self._reveal_empty_field(x, y)

    # Invoked from a cell's FieldButton
    def do_right_click(self, x, y):
        xy = (x, y)
        if not xy in self._revealed:
            btn = self._buttons[y][x]
            if xy in self._flagged:
                btn.flag(False)
                self._flagged.remove(xy)
            else:
                btn.flag(True)
                self._flagged.append(xy)
            self._check_win()

    # Clears out all the game data and starts fresh with a new board
    def generate_game(self, event=None):
        self.set_state(GameState.PLAYING)
        self._revealed = []  # [(x, y)]
        self._flagged = []   # [(x, y)]
        self._winefield = [] # [y][x] - weights

        # Zero out board
        for y in range(Constants.rows):
            self._winefield.append([])
            for x in range(Constants.cols):
                self._winefield[y].append(0)

        # Fill in wines (don't overlap)
        filled = 0
        while filled < Constants.wines:
            x = randint(0, Constants.cols - 1)
            y = randint(0, Constants.rows - 1)
            # we want to avoid if we already have a wine here (val = -1)
            if self._winefield[y][x] != -1:
                self._winefield[y][x] = -1
                filled = filled + 1
                # crawl squares surrounding the wine and append 1 to their weight in winefield[]
                neighbors = self._find_neighbors(x, y)
                for (xr, yr) in neighbors:
                    val = self._winefield[yr][xr]
                    if val != -1:
                        self._winefield[yr][xr] = val + 1
    
    # Pass in STATE_ class constants
    def set_state(self, state):
        if state == GameState.PLAYING:
            # Reset cell appearances
            for y in range(Constants.rows):
                for x in range(Constants.cols):
                    self._buttons[y][x].configure(text = '', fg = '#000000')
            self._btn_start.configure(text = Constants.glyphs['FACE_PLAYING'])
        elif state == GameState.WIN:
            self._btn_start.configure(text = Constants.glyphs['FACE_WIN'])
            self._reveal_all_cells(wine_glyph = 'WATER')
        elif state == GameState.LOSS:
            self._btn_start.configure(text = Constants.glyphs['FACE_LOSS'])
            self._reveal_all_cells()

    # Sees which cells are flagged and tries to sum their board value to (-1 * Constants.wines)
    def _check_win(self):
        total = 0
        for (x, y) in self._flagged:
            total = total + self._winefield[y][x]
        if total == -1 * Constants.wines:
            self.set_state(GameState.WIN)

    # Return bordering cells to (x, y)
    def _find_neighbors(self, x, y) -> list:
        neighbors = []
        xa, xb = max(0, x - 1), min(x + 1, Constants.cols - 1)
        ya, yb = max(0, y - 1), min(y + 1, Constants.rows - 1)
        for yr in range(ya, yb + 1):
            for xr in range(xa, xb + 1):
                neighbors.append((xr, yr))
        neighbors.remove((x, y))
        return neighbors

    # Reveals a single cell
    def _reveal(self, x, y):
        if not (x, y) in self._revealed:
            self._buttons[y][x].reveal(self._winefield[y][x])
            self._revealed.append((x, y))
    
    # Finds and reveals any mass of empty cells bordering x,y
    # Crawls up to a weighted cell and stops on it (inclusive)
    def _reveal_empty_field(self, x, y):
        info = CrawlInfo()
        self._crawl_blank_field(info, x, y)
        for (x, y) in info.empties:
            self._reveal(x, y)

    # Reveals all cells on the board
    def _reveal_all_cells(self, wine_glyph='WINE'):
        for y in range(Constants.rows):
            for x in range(Constants.cols):
                self._reveal(x, y)
                if self._winefield[y][x] == -1:
                    self._buttons[y][x].configure(text = Constants.glyphs[wine_glyph])

    # Used recursively within _reveal_empty_field
    def _crawl_blank_field(self, info, x, y):
        if info.is_visited(x, y):
            return
        info.add_empty(x, y)
        if self._winefield[y][x] != 0:
            return
        neighbors = self._find_neighbors(x, y)
        for (nx, ny) in neighbors:
            self._crawl_blank_field(info, nx, ny)

    # Abstraction from __init__ - to reset the game, call .generate_game()
    def _create_ui(self, tk_root):
        topframe = tk.Frame(tk_root, height = 48)
        topframe.grid(row = 0, column = 0)
        bottomframe = tk.Frame(tk_root)
        bottomframe.grid(row = 1, column = 0)

        # Top UI
        self._btn_start = tk.Button(topframe,
            text = Constants.glyphs['FACE_PLAYING'],
            font = Constants.start_button_font,
            image = Constants.empty_pixels, # allow for pixel sizing
            compound = 'c',
            width = 48,
            height = 48)
        self._btn_start.bind('<Button-1>', self.generate_game)
        self._btn_start.grid(row = 0, column = 0)

        # Cells (FieldButton)
        self._buttons = []
        for y in range(Constants.rows):
            self._buttons.append([])
            for x in range(Constants.cols):
                btn = FieldButton(self, bottomframe, x, y)
                self._buttons[y].append(btn)



root = tk.Tk()
Constants.evaluate_post_root()

# Configure the window
root.title('Winesweeper - %d wines' % Constants.wines)
rw, rh = 28 * Constants.cols, (28 * Constants.rows) + 64
sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
root.geometry('%dx%d+%d+%d' % (rw, rh, int(sw/2 - rw/2), int(sh/2 - rh/2)))

app = GameController(root)
root.mainloop()
