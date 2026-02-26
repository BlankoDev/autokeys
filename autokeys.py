import json
from pathlib import Path
from threading import Thread
from typing import Literal
from pynput.keyboard import Key as KeyCode, Controller
from time import sleep

class Key:
    DEBUG = False
    def __init__(self, name : str | KeyCode, _id: str, delay: int = 0, action_name=''):
        self.action_name = action_name
        self.name = name
        self.delay = delay
        self.id = _id
    
    def run(self, keyboard: Controller):
        sleep(self.delay / 1000)
        if self.DEBUG: print(self.name)
        else: self.tap(keyboard)
    
    def tap(self, keyboard: Controller):
        keyboard.press(self.name)
        keyboard.release(self.name)

    def to_dict(self):
        if isinstance(self.name, str): name = self.name
        else: name = self.name.name
        return {'key': name, 'delay': self.delay, 'action_name': self.action_name}

    def __hash__(self): return self.name.__hash__()

    def __eq__(self, value): 
        if isinstance(value, Key): return self.name == value.name and self.delay == value.delay
        else:return value == self.name

class Backend:
    VERSION = 1
    def __init__(self, tick_cmd=None, end_cmd=None):
        self.keyboard = Controller()
        self.keys: list[Key] = []
        self._last_index = 0

        self.running = False
        self.loop_thread = self._create_loop_thread()
        self.loop = True
        self._tick_cmd = tick_cmd
        self._end_cmd = end_cmd

    def add_key(self, key : str | KeyCode | Key, _id: str, delay: int = 0, action_name = ''):
        if not isinstance(key, Key): key = Key(key, _id, delay, action_name)
        self.keys.append(key)
        self._last_index += 1
        return self._last_index
    
    def remove_key(self, index: int):
        del self.keys[index]
        self._last_index -= 1

    def peek_key(self, index: int): return self.keys[index]

    def clear_keys(self): 
        self.keys.clear()
        self._last_index = 0

    def run(self):
        for key in self.keys: 
            if not self.running: return
            if self._tick_cmd is not None: self._tick_cmd(key)
            key.run(self.keyboard)
        if not self.loop: 
            self.running = False
            if self._end_cmd is not None: self._end_cmd()

    def start(self):
        if self.loop_thread.is_alive(): raise RuntimeError("loop was already running")
        if self.loop_thread.ident is not None: self.loop_thread = self._create_loop_thread()
        self.running = True
        self.loop_thread.start()

    def stop(self): self.running = False

    def save(self, path: str | Path):
        path = Path(path)
        data = {'version':self.VERSION, 'data': [key.to_dict() for key in self.keys]}
        data = json.dumps(data)
        path.write_text(data)
    
    def load(self, path: str | Path) -> tuple[dict[Literal['key', 'delay', 'action_name'], str | int]]:
        path =Path(path)
        data = path.read_text()
        data = json.loads(data)
        assert 'version' in data
        assert data['version'] == self.VERSION
        assert 'data' in data
        assert isinstance(data['data'], list)
        self.keys.clear()
        for key_data in data['data']: self._check_item(key_data)
        return (*data['data'],)
    
    def _check_item(self, item):
        assert isinstance(item, dict)
        assert 'key' in item
        assert 'delay' in item
        assert 'action_name' in item

    def _loop(self): 
        while self.running: self.run()

    def _create_loop_thread(self): return Thread(target=self._loop, daemon=True)

 