import json
from pathlib import Path
from tkinter import BooleanVar, ttk, Tk, StringVar, Menu, messagebox, filedialog
from sys import argv as sys_argv, platform
import webbrowser
import toml

from widgets import Keyboard, KeyButton
from autokeys import Backend, Key, KeyCode

DEBUG = False

def donothing(): pass

def get_datadir() -> Path:
    home = Path.home()
    if platform == "win32": return home / "AppData/Roaming"
    elif platform == "linux": return home / ".local/share"
    elif platform == "darwin": return home / "Library/Application Support"

DOCUMENT_DIR = Path.home() / "documents"
if not DEBUG: DATA_DIR = get_datadir() / 'autokeys'
else: DATA_DIR = Path('data') / 'autokeys'
USER_LANG_DIR = DATA_DIR / 'lang'
SYSTEM_LANG_DIR = Path.cwd() / 'lang'
USER_LAYOUT_DIR = DATA_DIR / 'layouts'
SYSTEM_LAYOUT_DIR = Path.cwd() / 'layouts'
LANG_DIRS = (USER_LANG_DIR, SYSTEM_LANG_DIR,)
LAYOUTS_DIRS = (USER_LAYOUT_DIR, SYSTEM_LAYOUT_DIR)
CONFIG_FILE = DATA_DIR / 'config.toml'

DATA_DIR.mkdir(exist_ok=True)
USER_LANG_DIR.mkdir(exist_ok=True)
USER_LAYOUT_DIR.mkdir(exist_ok=True)

Key.DEBUG = DEBUG

class Config:
    DEFAULT = {
        'lang' : 'en-US',
        'layout': 'qwerty',
        'loop' : True
    }
    def __init__(self):
        if not CONFIG_FILE.exists(): self.write_config()
        self.data = self._read_config()

    def write_config(self):
        if not hasattr(self, 'data'): self.data = self.DEFAULT
        data = toml.dumps(self.data)
        CONFIG_FILE.write_text(data)
    
    def _read_config(self):
        data = CONFIG_FILE.read_text()
        return toml.loads(data)
    
    @property
    def lang(self) -> str: return self['lang']

    @lang.setter
    def lang(self, value): self['lang'] = value

    @property
    def layout(self) -> str: return self['layout']

    @layout.setter
    def layout(self, value): self['layout'] = value

    @property
    def loop(self) -> bool: return self['loop']

    @loop.setter
    def loop(self, value): self['loop'] = value
    
    def __getitem__(self, key): return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value
        self.write_config()

class Lang:
    def __init__(self, code: str):
        self.code = code
        self.data = {}
        self.set(code)
    
    def set(self, code: str): 
        self.code = code
        for path in LANG_DIRS:
            file = path / f"{code}.lang"
            if file.exists():
                data = file.read_text('utf-8')
                self.data = json.loads(data)
    
    def _get_path(self, path: list | tuple):
        current = self.data
        for part in path:current = current[part]
        if isinstance(current, dict): return current['.']
        return current
    
    def get(self, key: str):
        parts = key.split(".")
        return self._get_path(parts)

    def __getitem__(self, key): return self.get(key)

class App:
    TITLE_FMT = "AutoKeys - {}"
    FILE_TYPES = [['autokeys data', ['.akd']], ['json', ['.json']]]
    def __init__(self, argv: list[str] = sys_argv):
        self.argv = argv
        self.backend = Backend(self._macro_run_feedback, self._macro_end_cmd)

        self.file = None
        self.saved = True
        self.config = Config()
        self.lang = Lang(self.config.lang)

        self.backend.loop = self.config.loop

        self.root = Tk()
        self.root.geometry("1280x720")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        self.update_title(self.lang["actions.idle"])
        self._bind_shortcuts()

        self.menubar = self._create_menu()
        self.root.config(menu=self.menubar)

        self.keyboard = Keyboard(self.root, command=self._key_select_command)
        self.load_layout(self.config.layout)
        self.keyboard.pack(expand=True)

        self.h_separator = ttk.Separator(self.root, orient='horizontal')
        self.h_separator.pack(fill='x', padx=20, pady=10)

        self.bottom_frame = ttk.Frame(self.root)
        self.key_option_frame = ttk.Frame(self.bottom_frame)

        self.key_option_frame.pack(side='left', expand=True, fill='both')

        self.v_separator = ttk.Separator(self.bottom_frame, orient='vertical')
        self.v_separator.pack(side='left', fill='y', padx=10, pady=20)

        self.action_list_option = ttk.Frame(self.bottom_frame)
        
        self.action_list = self._create_action_list()
        self.action_list.pack(expand=True, fill='both', padx=(0, 10), pady=(0, 10))
        
        self.action_button_var = StringVar(self.action_list_option, self.lang['macro.button.run'])
        self.action_button = ttk.Button(self.action_list_option, textvariable=self.action_button_var, command=self._action_button_command)
        self.action_button.pack(fill='x', padx=(0, 10),pady=(0,10))

        self.action_list_option.pack(side='right', expand=True, fill='both')

        self.bottom_frame.pack(expand=True, fill='both')

        self.show_option(self._create_empty_option)

        self.action_list.bind("<<TreeviewSelect>>", self._selection_handle)
    
    def _bind_shortcuts(self):
        self.root.bind('<Control-Shift-S>', lambda _: self.save_as())
        self.root.bind('<Control-s>', lambda _: self.save())
        self.root.bind('<Control-q>', lambda _: self.quit())
        self.root.bind('<Control-o>', lambda _: self.open())
        self.root.bind('<Control-n>', lambda _: self.reset())
        self.root.bind('<Control-r>', lambda _: self._action_button_command())
        self.root.bind('<Control-l>', lambda _: self.toggle_loop())
        self.root.bind('<Control-a>', lambda _: self.action_list.selection_set(self.action_list.get_children()))

    def toggle_loop(self): self.backend.loop = not self.backend.loop

    def quit(self):
        if not self.saved: 
            result = messagebox.askyesnocancel(self.lang['ask.quit.title'], self.lang['ask.quit.message'], icon='question', parent=self.root)
            if result is None: return
            if result: self.save()
        self.root.quit()
        
    def show_option(self, callback, *args, **kwargs):
        if hasattr(self, 'option'): self.option.destroy()
        self.update_title(self.lang["actions.editing"])
        self.option = callback(*args, **kwargs)
        self.option.pack(expand=True, fill='both', padx=(10,0), pady=(0, 10))

    def run_macro(self):
        if self.action_list.get_children() == (): return
        self._first_feedback = None
        self._setup_bakend()
        if sum([key.delay for key in self.backend.keys]) / len(self.backend.keys) <= 10:
            if not messagebox.askyesno(self.lang["ask.dangerous_macro.title"], self.lang["ask.dangerous_macro.message"], icon='warning', parent=self.root): return
        
        self.show_option(self._create_running_option)
        self.action_button_var.set(self.lang['macro.button.stop'])
        self.action_list.configure(selectmode='none')
        self._disable_file_op()
        self.keyboard.set_state('disabled')
        self.runmenu.entryconfigure(self.MENU_RUN_BUTTON_INDEX, state='disabled')
        self.runmenu.entryconfigure(self.MENU_STOP_BUTTON_INDEX, state='normal')
        self.backend.start()
        self.update_title(self.lang["actions.running"])
    
    def stop_macro(self):
        self.update_title(self.lang["actions.idle"])
        self.action_button_var.set(self.lang['macro.button.run'])
        self.action_list.configure(selectmode='extended')
        self._activate_file_op()
        self.keyboard.set_state('normal')
        self.runmenu.entryconfigure(self.MENU_RUN_BUTTON_INDEX, state='normal')
        self.runmenu.entryconfigure(self.MENU_STOP_BUTTON_INDEX, state='disabled')
        self.backend.stop()
        if self.action_list.selection() == (): self.show_option(self._create_empty_option)
        else: self._selection_handle()

    def _disable_file_op(self):
        self.filemenu.entryconfigure(self.MENU_NEW_FILE_BUTTON_INDEX, state="disabled")
        self.filemenu.entryconfigure(self.MENU_OPEN_FILE_BUTTON_INDEX, state="disabled")
        self.filemenu.entryconfigure(self.MENU_SAVE_FILE_BUTTON_INDEX, state="disabled")
        self.filemenu.entryconfigure(self.MENU_SAVEAS_FILE_BUTTON_INDEX, state="disabled")
    
    def _activate_file_op(self):
        self.filemenu.entryconfigure(self.MENU_NEW_FILE_BUTTON_INDEX, state="normal")
        self.filemenu.entryconfigure(self.MENU_OPEN_FILE_BUTTON_INDEX, state="normal")
        self.filemenu.entryconfigure(self.MENU_SAVE_FILE_BUTTON_INDEX, state="normal")
        self.filemenu.entryconfigure(self.MENU_SAVEAS_FILE_BUTTON_INDEX, state="normal")

    def _setup_bakend(self):
        self.backend.clear_keys()
        for _id in self.action_list.get_children():
            name, delay, key = self.action_list.item(_id)['values']
            key_value = key.removeprefix('Key.')
            try: key_value = KeyCode[key_value]
            except KeyError: key_value = key
            self.backend.add_key(key_value, _id, delay, name)

    def _action_button_command(self):
        if self.backend.running: self.stop_macro()
        else: self.run_macro()
    
    def _macro_run_feedback(self, key: Key):
        if self._first_feedback is None: self._first_feedback = True
        if key.delay > 10 or self._first_feedback:self.action_list.selection_set(key.id)
        self._first_feedback = False

    def _key_select_command(self, key: KeyCode | str):
        self.action_list.selection_remove(*self.action_list.selection())
        self.show_option(self._create_option_for_key, key)

    def _selection_handle(self, event=None):
        if self.backend.running: return
        selection = self.action_list.selection()
        if len(selection) == 0: return
        if len(selection) > 1: self.show_option(self._create_edit_multiple_option_key, *selection)
        else: self.show_option(self._create_edit_option_key, selection[0])
        self.keyboard.deselect()

    def import_layout(self, keyboardmenu: Menu, keyboardmenu_var: StringVar):
        paths = filedialog.askopenfilenames(defaultextension='json', filetypes=[['json', '.json']], initialdir=DOCUMENT_DIR, parent=self.root)
        errors = []
        for path in paths:
            path = Path(path)
            raw_data = path.read_text('utf-8')
            data = json.loads(raw_data)
            if self._check_layout(data): 
                keyboardmenu.insert_radiobutton(0, label=path.stem.title(), value=path.stem, variable=keyboardmenu_var, command=lambda: self.load_layout(keyboardmenu_var.get()))
                copy_path = USER_LAYOUT_DIR / path.name
                copy_path.write_text(raw_data, encoding='utf-8')
            else: errors.append(path)

        if len(errors) > 0: messagebox.showwarning(self.lang['messages.warn.layout_not_found.title'], self.lang['messages.warn.layout_not_found.message'].format(files='\n'.join([str(err) for err in errors])), icon='warning')
        else: messagebox.showinfo(self.lang['messages.info.layout_imported.title'], self.lang['messages.info.layout_imported.message'], icon='info')


    def load_layout(self, layout_name: str):
        path = self._get_layout_path(layout_name)
        if path is None: return messagebox.showerror(self.lang['messages.error.layout_not_found.title'], self.lang['messages.error.layout_not_found.title'].format(layout_name=layout_name))
        data = path.read_text('utf-8')
        data = json.loads(data)
        if not self._check_layout(data): return messagebox.showerror(self.lang['messages.error.invalid_layout.title'], self.lang['messages.error.invalid_layout.title'].format(path=path))
        self.keyboard.set_layout(data)
        self.config.layout = layout_name

    def _check_sep(self, seps: dict[str, dict[str, float]]):
        if 'x' not in seps: return False
        if 'y' not in seps: return False
        for axis in seps:
            out = {}
            for sep in seps[axis]:
                if not sep.isdigit(): return False
                out[int(sep)] = seps[axis][sep]
            seps[axis] = out
        return True

    def _check_key_syntax(self, key: str):
        key_len = len(key)
        if len(key) >= 3 and ':' in key: 
            if key.index(':') == key_len - 1: return False
        if len(key) >= 3 and '!' in key:
            key = key.split('!')[0]
            if not key.isdigit(): return False
        return True

    def _check_layout(self, layout: dict):
        if 'grid' not in layout: return False
        for key, value in layout.items():
            if key == 'grid': 
                layout[key] = tuple(value)
                continue
            if key == 'sep':
                if not self._check_sep(value): return False
                continue
            if not isinstance(value, list): return False
            len_value = len(value)
            if len_value < 2 or len_value > 4: return False
            if not self._check_key_syntax(key): return False
            layout[key] = tuple(value)
        return True

    def _get_layout_path(self, layout_name: str):
        for path in LAYOUTS_DIRS:
            for file in path.iterdir():
                if file.name == f'{layout_name}.json': return file


    MENU_RUN_BUTTON_INDEX = 0
    MENU_STOP_BUTTON_INDEX = 1
    MENU_NEW_FILE_BUTTON_INDEX = 0
    MENU_OPEN_FILE_BUTTON_INDEX = 1
    MENU_SAVE_FILE_BUTTON_INDEX = 2
    MENU_SAVEAS_FILE_BUTTON_INDEX = 3
    def _create_menu(self):
        menubar = Menu(self.root)
        self.filemenu = Menu(menubar, tearoff=0)
        self.filemenu.add_command(label=self.lang['menu.file.new'], command=self.reset)
        self.filemenu.add_command(label=self.lang['menu.file.open'], command=self.open)
        self.filemenu.add_command(label=self.lang['menu.file.save'], command=self.save)
        self.filemenu.add_command(label=self.lang['menu.file.saveas'], command=self.save_as)
        self.filemenu.add_separator()
        self.filemenu.add_command(label=self.lang['menu.file.exit'], command=self.quit)
        menubar.add_cascade(label=self.lang['menu.file'], menu=self.filemenu)

        self.runmenu = Menu(menubar, tearoff=0)
        self.runmenu.add_command(label=self.lang['menu.run.run'], command=self.run_macro)
        self.runmenu.add_command(label=self.lang['menu.run.stop'], command=self.stop_macro)

        loop_var = BooleanVar(self.runmenu, self.backend.loop)
        self.runmenu.add_checkbutton(label=self.lang['menu.run.loop'], command=lambda: self.set_loop(loop_var), onvalue=True, offvalue=False, variable=loop_var)

        self.runmenu.entryconfigure(self.MENU_STOP_BUTTON_INDEX, state='disabled')
        menubar.add_cascade(label=self.lang['menu.run'], menu=self.runmenu)

        langmenu = Menu(menubar, tearoff=0)
        langmenu_var = StringVar(langmenu, self.config.lang)
        self._add_adviable_lang(langmenu, langmenu_var)
        menubar.add_cascade(label=self.lang['menu.lang'], menu=langmenu)


        keyboardmenu = Menu(menubar, tearoff=0)
        keyboardmenu_var = StringVar(keyboardmenu, self.config.layout)
        self._add_adviable_layout(keyboardmenu, keyboardmenu_var)

        keyboardmenu.add_separator()
        keyboardmenu.add_command(label=self.lang['menu.keyboard.import'], command=lambda: self.import_layout(keyboardmenu, keyboardmenu_var))
        menubar.add_cascade(label=self.lang['menu.keyboard'], menu=keyboardmenu)

        helpmenu = Menu(menubar, tearoff=0)
        helpmenu.add_command(label=self.lang['menu.help.docs'], command=lambda : webbrowser.open("https://github.com/BlankoDev/autokeys"))
        helpmenu.add_command(label=self.lang['menu.help.about'], command=lambda : webbrowser.open("https://github.com/BlankoDev"))
        menubar.add_cascade(label=self.lang['menu.help'], menu=helpmenu)
        return menubar

    def _add_adviable_lang(self, langmenu: Menu, langmenu_var: StringVar):
        for path in LANG_DIRS:
            for file in path.iterdir():
                langmenu.add_radiobutton(label=file.stem, value=file.stem, variable=langmenu_var, command=lambda: self.set_lang(langmenu_var.get()))

    def _add_adviable_layout(self, keyboardmenu: Menu, keyboardmenu_var: StringVar):
        for path in LAYOUTS_DIRS:
            for file in path.iterdir():
                keyboardmenu.add_radiobutton(label=file.stem.title(), value=file.stem, variable=keyboardmenu_var, command=lambda: self.load_layout(keyboardmenu_var.get()))

    def _update_actionlist(self):
        self.action_list.heading("name", text=self.lang["table.name"])
        self.action_list.heading("key", text=self.lang["table.key"])
        self.action_list.heading("delay", text=self.lang["table.delay"])
    
    def _update_action_button_lang(self):
        if not self.backend.running: self.action_button_var.set(self.lang['macro.button.run'])
        else: self.action_button_var.set(self.lang['macro.button.stop'])

    def set_lang(self, lang_code: str):
        self.lang.set(lang_code)
        self.config.lang = lang_code
        selection = self.action_list.selection()
        self.menubar.destroy()
        self.menubar = self._create_menu()
        self.root.config(menu=self.menubar)
        self._update_actionlist()
        self._update_action_button_lang()
        if self.backend.running: self.show_option(self._create_running_option)
        elif selection == ():
            if self.keyboard._current_key is None: self.show_option(self._create_empty_option)
            else: self.show_option(self._create_option_for_key)
        else: self._selection_handle()

    def save_as(self):
        if self.file is not None: initialfile = self.file.name
        else: initialfile = 'no-name'
        path = filedialog.asksaveasfilename(defaultextension='akd', filetypes=self.FILE_TYPES, initialdir=DOCUMENT_DIR, initialfile=initialfile)
        if path == '': return
        self._setup_bakend()
        self.backend.save(path)
        self.file = Path(path)
        self.saved = True
        self.update_title()

    def save(self):
        if self.file is None: return self.save_as()
        self._setup_bakend()
        self.backend.save(self.file)
        self.saved = True
        self.update_title()

    def open(self, confirm=True, path=None):
        if confirm and self.file is not None: 
            if not messagebox.askyesno(self.lang['ask.replace.title'], self.lang['ask.replace.message'], icon='question', parent=self.root): return
        if path is None:path = filedialog.askopenfilename(defaultextension='akd',filetypes=self.FILE_TYPES, initialdir=DOCUMENT_DIR)
        if path == '': return
        try: data = self.backend.load(path)
        except UnicodeDecodeError: return messagebox.showerror(self.lang['messages.error.unicode.title'], self.lang['messages.error.unicode.message'], parent=self.root)
        except AssertionError: return messagebox.showerror(self.lang['messages.error.invalid_file.title'], self.lang['messages.error.invalid_file.message'].format(path=path), parent=self.root)
        self.reset(False)
        for key_data in data: self.action_list.insert('', 'end', values=(key_data['action_name'], key_data['delay'], key_data['key']))
        self.file = Path(path)
        self.update_title()

    def reset(self, confirm=True):
        if confirm and self.file is not None: 
            if not messagebox.askyesno(self.lang['ask.delete.title'], self.lang['ask.delete.message'], icon='question', parent=self.root): return
        self.file = None
        self.saved = True
        self.backend.clear_keys()
        self.keyboard.deselect()
        all = self.action_list.get_children()
        self.action_list.delete(*all)
        self.show_option(self._create_empty_option)

    def set_loop(self, var: BooleanVar): 
        self.backend.loop = var.get()

    def _macro_end_cmd(self): self.stop_macro()

    def update_title(self, action: str = None): 
        if action is not None: self.action = action
        if self.file is not None: title = f"{self.action} - [{self.file.absolute()}]"
        else: title = f"{self.action}"
        if not self.saved:title = title + '*'
        self.root.title(self.TITLE_FMT.format(title))

    def _create_action_list(self):
        action_list = ttk.Treeview(self.action_list_option, columns=('name', 'delay', 'key'))
        
        action_list.heading("#0", text="#")
        action_list.heading("name", text=self.lang["table.name"])
        action_list.heading("key", text=self.lang["table.key"])
        action_list.heading("delay", text=self.lang["table.delay"])

        action_list.column("#0", width=10)
        action_list.column("name", width=250)
        action_list.column("key", width=20)
        action_list.column("delay", width=50)
        return action_list

    def _create_empty_option(self):
        self.update_title(self.lang["actions.idle"])
        frame = ttk.Labelframe(self.key_option_frame, text=self.lang["option.empty.title"])
        sub_frame = ttk.Frame(frame)
        label = ttk.Label(sub_frame, text=self.lang["option.empty.message.title"], font=('', 20))
        label.pack()
        label2 = ttk.Label(sub_frame, text=self.lang["option.empty.message.subtitle"])
        sub_frame.pack(expand=True)
        label2.pack()

        return frame
    
    def _create_running_option(self):
        frame = ttk.Labelframe(self.key_option_frame, text=self.lang["option.running.title"])
        sub_frame = ttk.Frame(frame)
        label = ttk.Label(sub_frame, text=self.lang["option.running.message.title"], font=('', 20))
        label.pack()
        label2 = ttk.Label(sub_frame, text=self.lang["option.running.message.subtitle"])
        sub_frame.pack(expand=True)
        label2.pack()

        return frame

    def _create_edit_multiple_option_key(self, *items):

        frame = ttk.Labelframe(self.key_option_frame, text=self.lang["option.edit.multiple.title"])
        sub_frame = ttk.Frame(frame)

        delay_frame = ttk.Frame(sub_frame)
        delay_label = ttk.Label(delay_frame, text=self.lang["option.labels.delay"])
        delay_label.pack(side='left', padx=(0, 10))

        delay_spinbox = ttk.Spinbox(delay_frame, to=100000, validate='all')
        delay_spinbox.set(0)
        delay_spinbox.pack(side='left')
        delay_frame.pack()

        sub_frame.pack(expand=True)

        bottom_frame = ttk.Frame(frame)
        add_button = ttk.Button(bottom_frame, text=self.lang["option.buttons.apply"], command=lambda: self._edit_multiple_action_command(delay_spinbox, items))
        add_button.pack(side='left', padx=5)

        delete_button = ttk.Button(bottom_frame, text=self.lang["option.buttons.delete"], command=lambda: self._delete_multiples_action_command(*items))
        delete_button.pack(side='left', padx=5)
        bottom_frame.pack(side='bottom', pady=5)

        return frame

    def _create_edit_option_key(self, item):
        name, delay, key = self.action_list.item(item)['values']
        index = self.action_list.index(item)
        frame = ttk.Labelframe(self.key_option_frame, text=self.lang["option.edit.single.title"].format(name=name, key=key))
        sub_frame = ttk.Frame(frame)

        delay_frame = ttk.Frame(sub_frame)
        delay_label = ttk.Label(delay_frame, text=self.lang["option.labels.delay"])
        delay_label.pack(side='left', padx=(0, 10))

        delay_spinbox = ttk.Spinbox(delay_frame, to=100000, validate='all')
        delay_spinbox.set(delay)
        delay_spinbox.pack(side='left')
        delay_frame.pack()

        index_frame = ttk.Frame(sub_frame)
        index_label = ttk.Label(index_frame, text=self.lang["option.labels.index"])
        index_label.pack(side='left', padx=(0, 10), pady=5)

        index_spinbox = ttk.Spinbox(index_frame, to=10000, validate='all')
        index_spinbox.set(index)
        index_spinbox.pack(side='left')
        index_frame.pack()

        name_frame = ttk.Frame(sub_frame)
        name_label = ttk.Label(name_frame, text=self.lang["option.labels.name"])
        name_label.pack(side='left', padx=(0, 10))

        name_entry = ttk.Entry(name_frame, validate='all')
        name_entry.insert(0, name)
        name_entry.pack(side='left')
        name_frame.pack()
        sub_frame.pack(expand=True)

        bottom_frame = ttk.Frame(frame)
        add_button = ttk.Button(bottom_frame, text=self.lang["option.buttons.apply"], command=lambda: self._edit_action_command(key, delay_spinbox, name_entry, index_spinbox, item))
        add_button.pack(side='left', padx=5)

        delete_button = ttk.Button(bottom_frame, text=self.lang["option.buttons.delete"], command=lambda: self._delete_action_command(item))
        delete_button.pack(side='left', padx=5)
        bottom_frame.pack(side='bottom', pady=5)

        return frame

    def _create_option_for_key(self, key: KeyCode | str):
        size = len(self.action_list.get_children())
        frame = ttk.Labelframe(self.key_option_frame, text=self.lang["option.add.title"].format(key=key))
        sub_frame = ttk.Frame(frame)

        delay_frame = ttk.Frame(sub_frame)
        delay_label = ttk.Label(delay_frame, text=self.lang["option.labels.delay"])
        delay_label.pack(side='left', padx=(0, 10))

        delay_spinbox = ttk.Spinbox(delay_frame, to=100000, validate='all')
        delay_spinbox.set(0)
        delay_spinbox.pack(side='left')
        delay_frame.pack()

        index_frame = ttk.Frame(sub_frame)
        index_label = ttk.Label(index_frame, text=self.lang["option.labels.index"])
        index_label.pack(side='left', padx=(0, 10), pady=5)

        index_spinbox = ttk.Spinbox(index_frame, to=10000, validate='all')
        index_spinbox.set(size)
        index_spinbox.pack(side='left')
        index_frame.pack()

        name_frame = ttk.Frame(sub_frame)
        name_label = ttk.Label(name_frame, text=self.lang["option.labels.name"])
        name_label.pack(side='left', padx=(0, 10))

        name_entry = ttk.Entry(name_frame, validate='all')
        name_entry.insert(0, self.lang["option.add.default"])
        name_entry.pack(side='left')
        name_frame.pack()
        sub_frame.pack(expand=True)

        add_button = ttk.Button(frame, text=self.lang["option.buttons.add"], command=lambda: self._add_action_command(key, delay_spinbox, name_entry, index_spinbox))
        add_button.pack(side='bottom', pady=5)

        return frame
    
    def _add_action_command(self, key: KeyCode | str, delay: ttk.Spinbox, name: ttk.Entry, index: ttk.Spinbox):
        if not delay.get().isdigit(): return messagebox.showwarning(self.lang["messages.warn.int_number.title"], self.lang["messages.warn.int_number.message"].format(entry=self.lang["table.delay"]))
        if not index.get().isdigit(): return messagebox.showwarning(self.lang["messages.warn.int_number.title"], self.lang["messages.warn.int_number.message"].format(entry=self.lang["table.index"]))
        self.saved = False
        item = self.action_list.insert('', index.get(), values=(name.get(), delay.get(), key))
        self.action_list.selection_set(item)

    def _edit_multiple_action_command(self, delay: ttk.Spinbox, items):
        if not delay.get().isdigit(): return messagebox.showwarning(self.lang["messages.warn.int_number.title"], self.lang["messages.warn.int_number.message"].format(entry=self.lang["table.delay"]))
        self.saved = False
        for item in items:
            values = self.action_list.item(item, 'values')
            self.action_list.item(item, values=(values[0], delay.get(), values[2]))

    def _edit_action_command(self, key: KeyCode | str, delay: ttk.Spinbox, name: ttk.Entry, index: ttk.Spinbox, item):
        if not delay.get().isdigit(): return messagebox.showwarning(self.lang["messages.warn.int_number.title"], self.lang["messages.warn.int_number.message"].format(entry=self.lang["table.delay"]))
        if not index.get().isdigit(): return messagebox.showwarning(self.lang["messages.warn.int_number.title"], self.lang["messages.warn.int_number.message"].format(entry=self.lang["table.index"]))
        self.saved = False
        self.action_list.item(item, values=(name.get(), delay.get(), key))
        if self.action_list.index(item) != index.get(): self.action_list.move(item, '', index.get())

    def _delete_multiples_action_command(self, *items):
        self.saved = False
        self.action_list.delete(*items)
        self.show_option(self._create_empty_option)

    def _delete_action_command(self, item):
        self.saved = False
        next_item = self.action_list.prev(item)
        self.action_list.delete(item)
        if self.action_list.get_children() == (): return self.show_option(self._create_empty_option)
        self.action_list.selection_set(next_item)

    def mainloop(self): self.root.mainloop()

if __name__ == "__main__": 
    KeyButton.SIZE = 50
    app = App()
    app.mainloop()

