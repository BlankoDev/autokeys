from tkinter import Button, Frame
from typing import Literal
from autokeys import Key
from pynput.keyboard import Key as KeyCode


def fill_tuple(_tuple: tuple, size: int, value): return _tuple + (*[value for _ in range(size - len(_tuple))],)

class KeyButton(Button):
    SIZE = 80
    def __init__(self, master: 'Keyboard', key: KeyCode | str, width=1, height=1, label=None, command = None):
        if label is not None: text = label
        else: text = key if isinstance(key, str) else key.name
        super().__init__(master, text=text, borderwidth=5, command=self._on_click)
        self.bind("<Enter>", self._on_hover_in)
        self.bind("<Leave>", self._on_hover_out)
        self.selected = False
        self.key = key
        self._hovered = False
        self._command = command

        self.width = width
        self.height = height

    def select(self):
        self.selected = True
        self.configure(relief='solid')

    def deselect(self):
        self.selected = False
        if self._hovered: self.configure(relief='groove')
        else: self.configure(relief='raised')

    def _on_hover_in(self, _): 
        if self.master.state == 'disabled': return
        self._hovered = True
        if not self.selected:self.configure(relief='groove')

    def _on_hover_out(self, _): 
        if self.master.state == 'disabled': return
        self._hovered = False
        if not self.selected:self.configure(relief='raised')
    
    def _on_click(self):
        if self._command is not None: self._command(self)
        self.select()

    def place(self, x: int = 0, y: int = 0): super().place(x=x, y=y, width=self.SIZE*self.width, height=self.SIZE*self.height)

class Keyboard(Frame):
    def __init__(self, master, layout: dict = {'grid':(0, 0,)}, command = None):
        grid = layout.get('grid')
        super().__init__(master, relief='ridge', borderwidth=3, width=(grid[0]*KeyButton.SIZE)+6, height=(grid[1]*KeyButton.SIZE)+6)
        self.layout = layout
        self.state = 'normal'
        self._current_key: KeyButton = None
        self._command = command
        self._keys: list[KeyButton] = []
        self._setup_layout()

    def set_layout(self, layout: dict):
        for key in self._keys: key.destroy()
        self._keys.clear()
        self.layout = layout
        grid = layout.get('grid')
        self.configure(width=(grid[0]*KeyButton.SIZE)+6, height=(grid[1]*KeyButton.SIZE)+6)
        self._setup_layout()

    def set_state(self, state: Literal['normal', 'active', 'disabled']):
        self.state = state
        if state == 'disabled': self.deselect()
        for key in self._keys: key.configure(state=state)

    def deselect(self): 
        if self._current_key is None: return
        self._current_key.deselect()
        self._current_key = None

    def _on_key_select(self, key: KeyButton):
        if self._command is not None: self._command(key.key)
        if self._current_key is not None: self._current_key.deselect()
        self._current_key = key
    
    def _setup_layout(self):
        if 'sep' in self.layout: sep = self.layout.get('sep')
        else: sep = tuple()
        for key, position in self.layout.items():
            if key in ('grid', 'sep',): continue
            x, y, width, height = fill_tuple(position, 4, 1)
            x_offset, y_offset = self._get_offset(sep, x, y)
            label = None
            if len(key) >= 3 and '!' in key:key = key.split('!')[-1]
            if len(key) >= 3 and ':' in key: 
                split = key.split(':')
                key = split[0]
                label = split[1]
            key_button = KeyButton(self, key, width, height, label=label, command=self._on_key_select)
            key_button.place((x + x_offset) * KeyButton.SIZE, (y + y_offset) * KeyButton.SIZE)
            self._keys.append(key_button)
    
    def _get_offset(self, sep: dict[str, dict[int, float | int]], x, y):
        x_seps = sep['x']
        y_seps = sep['y']
        x_result = 0
        y_result = 0
        for x_sep, value in x_seps.items():
            if x > x_sep: x_result += value
        for y_sep, value in y_seps.items():
            if y > y_sep: y_result += value
        return x_result, y_result


if __name__ == "__main__": pass