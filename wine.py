#!/usr/bin/python3

# E.g.
# python3 wine.py
# python3 wine.py r[ows]=16 c[ols]=16 w[ines]=24

import tkinter as tk
import tkinter.font as font
from random import randint
from sys import argv


# Reusable values
class Constants(object):
    def __init__(self):
        self._script_params = { # Default script params
            'rows': 8,
            'cols': 8,
            'wines': 8,
        }
        self.__prefix_map = {
            'r': 'rows',
            'c': 'cols',
            'w': 'wines',
        }
        self._pixels = tk.PhotoImage(width = 0, height = 0)
        self._colors = {
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
        self._button_font = font.Font(size = 18, weight = 'bold')
        self._start_button_font = font.Font(size = 36, weight = 'bold')
        self._glyphs = {
            'WATER': '🚰',
            'WINE': '🍷',
            'FLAG': '🚩',
            'BLOCK': '█',
            'FACE_PLAYING': '🤔',
            'FACE_WIN': '😊',
            'FACE_LOSS': '🥴', # see doctor
        }

    def parse_script_parameters(self, plist):
        pdict = dict(s.split('=') for s in plist)
        for k in pdict:
            first = k[:1]
            if first in self.__prefix_map:
                key = self.__prefix_map[first]
                try:
                    value = int(pdict[k])
                    self._script_params[self.__prefix_map[first]] = value
                except ValueError:
                    pass
        self.__normalize_wine_count()

    def __normalize_wine_count(self):
        self._script_params['wines'] = max(1, min(self._script_params['wines'], self.get_row_count() * self.get_col_count()))

    def get_row_count(self):
        return self._script_params['rows']

    def get_col_count(self):
        return self._script_params['cols']

    def get_wine_count(self):
        return self._script_params['wines']

    # Others
    def get_button_font(self):
        return self._button_font
    
    def get_color(self, value):
        return self._colors[value]

    def get_empty_pixels(self):
        return self._pixels

    def get_glyph(self, name):
        return self._glyphs[name] or '?'

    def get_start_button_font(self):
        return self._start_button_font



# Extend the tkinter button for winesweeper type functions
class FieldButton(tk.Button):
    def __init__(self, controller, parent, x, y):
        self.__controller = controller
        self.x = x
        self.y = y
        super().__init__(
                parent,
                text = '',
                image = controller.get_constants().get_empty_pixels(),
                compound = 'c',
                border = 0,
                width = 24,
                height = 24)
        self.bind('<Button-1>', self._leftclick)
        self.bind('<Button-2>', self._rightclick)
        self.bind('<Button-3>', self._rightclick)
        super().grid(row = y, column = x)

    def flag(self, flagged=True):
        text = (flagged and self.__get_glyph('FLAG')) or ''
        self.configure(text = text)

    def reveal(self, value):
        fg = self.__controller.get_constants().get_color(value)
        text = '%d' % value
        if value == -1:
            text = self.__get_glyph('WINE')
        elif value == 0:
            text = self.__get_glyph('BLOCK')
        self.configure(fg = fg, text = text)

    def _leftclick(self, event):
        self.__controller.do_left_click(self.x, self.y)

    def _rightclick(self, event):
        self.__controller.do_right_click(self.x, self.y)
    
    def __get_glyph(self, name):
        return self.__controller.get_constants().get_glyph(name)



# Used for organizing logic within the search for open empty spaces
class CrawlInfo(object):
    def __init__(self, rows, cols):
        self._visited = []
        self._empties = []
        for y in range(rows):
            self._visited.append([])
            for x in range(cols):
                self._visited[y].append(False)

    def add_empty(self, x, y):
        self._empties.append((x, y))

    def is_visited(self, x, y):
        return (x, y) in self._empties

    def get_empties(self):
        return self._empties



# Primary game logic
class GameController(object):
    def __init__(self, window, constants):
        self.window = window
        self.constants = constants
        self.rows = constants.get_row_count()
        self.cols = constants.get_col_count()
        self.wines = constants.get_wine_count()

        # Simple game states, don't really need these anywhere else.
        self.STATE_PLAYING = 0
        self.STATE_WIN = 1
        self.STATE_LOSS = 2

        self.winefield = []
        self.revealed = []
        self.flagged = []
        self.buttons = []

        self.__create_ui()
        self.generate_game()

    # Sees which cells are flagged and tries to sum their board value to (-1 * self.wines)
    def check_win(self):
        target = -1 * self.wines
        total = 0
        for (x, y) in self.flagged:
            total = total + self.winefield[y][x]
        if total == target:
            self.set_state(self.STATE_WIN)

    def do_left_click(self, x, y):
        boardscore = self.winefield[y][x]
        # Hit a wine - game over
        if boardscore == -1:
            self.set_state(self.STATE_LOSS)
        elif boardscore > 0:
            self._reveal(x, y)
        else:
            self._reveal_empty_field(x, y)

    def do_right_click(self, x, y):
        xy = (x, y)
        if not xy in self.revealed:
            btn = self.buttons[y][x]
            if xy in self.flagged:
                btn.flag(flagged = False)
                self.flagged.remove(xy)
            else:
                btn.flag(flagged = True)
                self.flagged.append(xy)
                self.check_win()

    def generate_game(self, event=None):
        self.set_state(self.STATE_PLAYING)
        self.winefield = [] # [y][x]
        self.revealed = []  # [(x, y)]
        self.flagged = []   # [(x, y)]

        # Reset button appearance
        self.__clear_buttons()

        # Empty board of zeroes
        for y in range(self.rows):
            self.winefield.append([])
            self.revealed.append([])
            for x in range(self.cols):
                self.winefield[y].append(0)
                self.revealed[y].append(False)

        # Fill in wines (don't overlap)
        filled = 0
        while filled < self.wines:
            x = randint(0, self.cols - 1)
            y = randint(0, self.rows - 1)
            # we want to avoid if we already have a wine here (val = -1)
            if self.winefield[y][x] != -1:
                self.winefield[y][x] = -1
                filled = filled + 1
                # crawl squares around the wine to append to their weight
                neighbors = self._get_neighbors(x, y)
                for (xr, yr) in neighbors:
                    val = self.winefield[yr][xr]
                    if val != -1:
                        self.winefield[yr][xr] = val + 1

    def get_constants(self):
        return self.constants

    def set_state(self, state):
        if state == self.STATE_PLAYING:
            self.__btn_start.configure(text = self.constants.get_glyph('FACE_PLAYING'))
        elif state == self.STATE_WIN:
            self.__btn_start.configure(text = self.constants.get_glyph('FACE_WIN'))
            self._reveal_all_cells(wine_glyph = 'WATER')
        elif state == self.STATE_LOSS:
            self.__btn_start.configure(text = self.constants.get_glyph('FACE_LOSS'))
            self._reveal_all_cells()

    # Return bordering cells to (x, y)
    def _get_neighbors(self, x, y):
        neighbors = []
        xa, xb = max(0, x - 1), min(x + 1, self.cols - 1)
        ya, yb = max(0, y - 1), min(y + 1, self.rows - 1)
        for yr in range(ya, yb + 1):
            for xr in range(xa, xb + 1):
                neighbors.append((xr, yr))
        neighbors.remove((x, y))
        return neighbors

    # reveal single
    def _reveal(self, x, y):
        if not (x, y) in self.revealed:
            self.buttons[y][x].reveal(self.winefield[y][x])
            self.revealed.append((x, y))
    
    # Find and reveal surrounding empty cells
    def _reveal_empty_field(self, x, y):
        info = CrawlInfo(self.rows, self.cols)
        self.__crawl_blank_field(info, x, y)
        for (x, y) in info.get_empties():
            self._reveal(x, y)

    # All on board
    def _reveal_all_cells(self, wine_glyph='WINE'):
        for y in range(self.rows):
            for x in range(self.cols):
                self._reveal(x, y)
                if self.winefield[y][x] == -1:
                    self.buttons[y][x].configure(text = self.constants.get_glyph(wine_glyph))

    # Call to reset all winefield buttons to their default look
    def __clear_buttons(self):
        for y in range(self.rows):
            for x in range(self.cols):
                btn = self.buttons[y][x]
                btn.configure(text = '', fg = '#000000')

    # Used recursively within _reveal_empty_field
    def __crawl_blank_field(self, info, x, y):
        # Breaking conditions: already visited, or value != 0
        currentValue = self.winefield[y][x]
        if info.is_visited(x, y):
            return
        info.add_empty(x, y)
        if currentValue != 0:
            return
        # Get neighboring cells
        neighbors = self._get_neighbors(x, y)
        for (nx, ny) in neighbors:
            self.__crawl_blank_field(info, nx, ny)

    # Abstraction from __init__ - to reset the game, call .generate_game()
    def __create_ui(self):
        topframe = tk.Frame(self.window, height = 48)
        topframe.grid(row = 0, column = 0)
        bottomframe = tk.Frame(self.window)
        bottomframe.grid(row = 1, column = 0)

        # Top UI
        self.__btn_start = tk.Button(topframe,
            text = self.constants.get_glyph('FACE_PLAYING'),
            image = self.constants.get_empty_pixels(),
            font = self.constants.get_start_button_font(),
            compound = 'c',
            width = 48,
            height = 48
        )
        self.__btn_start.bind('<Button-1>', self.generate_game)
        self.__btn_start.grid(row = 0, column = 0)

        # Cells (FieldButton)
        for y in range(self.rows):
            self.buttons.append([])
            for x in range(self.cols):
                btn = FieldButton(self, bottomframe, x, y)
                btn.configure(font = self.constants.get_button_font())
                self.buttons[y].append(btn)




root = tk.Tk()
constants = Constants()
constants.parse_script_parameters(argv[1:])

# Configure the window
root.title('Winesweeper - %d wines' % constants.get_wine_count())
rw, rh = 28 * constants.get_col_count(), (28 * constants.get_row_count()) + 64
sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
root.geometry('%dx%d+%d+%d' % (rw, rh, int(sw/2 - rw/2), int(sh/2 - rh/2)))

app = GameController(root, constants)
root.mainloop()
