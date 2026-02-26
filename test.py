from autokeys import Key, KeyCode
from pynput.keyboard import Controller
keyboard = Controller()


test = Key(KeyCode['alt_gr'], 'gfreg', 10)
test.run(keyboard)