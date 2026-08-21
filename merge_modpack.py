import os
import shutil
import sys
import subprocess
import threading
import struct
import zlib
import lzma
import xml.etree.ElementTree as ET
import queue
import tempfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Complete universal 7th Heaven -> FFVIISE Mod Loader mapping rules
FOLDER_MAPPING = {
    # Field & Overworld
    "char": os.path.join("field", "char"),
    "char.lgp": os.path.join("field", "char"),
    "chocobo": os.path.join("field", "char"),
    "field": os.path.join("field", "flevel"),
    "flevel": os.path.join("field", "flevel"),
    "flevel.lgp": os.path.join("field", "flevel"),
    "world": os.path.join("wm", "world_us"),
    "world_us": os.path.join("wm", "world_us"),
    "world.lgp": os.path.join("wm", "world_us"),
    "world_us.lgp": os.path.join("wm", "world_us"),
    "wm": os.path.join("wm", "world_us"),
    
    # Battle & Effects
    "battle": os.path.join("battle", "battle"),
    "battle.lgp": os.path.join("battle", "battle"),
    "magic": os.path.join("battle", "magic"),
    "magic.lgp": os.path.join("battle", "magic"),
    "stage": os.path.join("battle", "stage"),
    
    # UI & Sound
    "menu": os.path.join("menu", "menu_us"),
    "menu_us": os.path.join("menu", "menu_us"),
    "menu.lgp": os.path.join("menu", "menu_us"),
    "music": "music_ogg",
    "music_ogg": "music_ogg",
    "sound": "sound",
    "movies": "movies",
    
    # Minigames
    "minigame": os.path.join("minigame", "high-us"),
    "minigames": os.path.join("minigame", "high-us"),
    "high": os.path.join("minigame", "high-us"),
    "high-us": os.path.join("minigame", "high-us"),
    "high-us.lgp": os.path.join("minigame", "high-us"),
    "high.lgp": os.path.join("minigame", "high-us"),
    "chocobo_race": os.path.join("minigame", "chocobo"),
    "chocoborace": os.path.join("minigame", "chocobo"),
    "chocobo_racing": os.path.join("minigame", "chocobo"),
    "chocobo.lgp": os.path.join("minigame", "chocobo"),
    "sub": os.path.join("minigame", "sub"),
    "sub.lgp": os.path.join("minigame", "sub"),
    "snowboard": os.path.join("minigame", "snowboard-us"),
    "snowboard-us": os.path.join("minigame", "snowboard-us"),
    "snowboard-us.lgp": os.path.join("minigame", "snowboard-us"),
    "snowboard.lgp": os.path.join("minigame", "snowboard-us"),
    "condor": os.path.join("minigame", "condor"),
    "condor.lgp": os.path.join("minigame", "condor"),
    "coaster": os.path.join("minigame", "coaster"),
    "coaster.lgp": os.path.join("minigame", "coaster"),

    # Common loose / raw textures & override folders
    "textures": os.path.join("field", "char"),
    "override": os.path.join("field", "char"),
    "direct": os.path.join("field", "char")
}

def get_default_source_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def detect_ffvii_mods_dir():
    try:
        import winreg
        steam_path = None
        for subkey in [r'SOFTWARE\WOW6432Node\Valve\Steam', r'SOFTWARE\Valve\Steam']:
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, subkey)
                steam_path, _ = winreg.QueryValueEx(key, 'InstallPath')
                winreg.CloseKey(key)
                if steam_path:
                    break
            except Exception:
                continue

        if steam_path:
            possible_paths = [
                os.path.join(steam_path, "steamapps", "common", "FINAL FANTASY VII Steam Edition", "mods"),
                os.path.join(steam_path, "steamapps", "common", "FINAL FANTASY VII", "mods"),
            ]
            for p in possible_paths:
                if os.path.exists(os.path.dirname(p)): # If game dir exists
                    return p
    except Exception:
        pass
    return None

def lzma_filters(props):
    d = props[0]
    lc = d % 9
    d //= 9
    return [{
        'id': lzma.FILTER_LZMA1,
        'lc': lc,
        'lp': d % 5,
        'pb': d // 5,
        'dict_size': struct.unpack('<I', props[1:5])[0],
    }]

def decompress_lzma(block):
    if len(block) < 8:
        raise lzma.LZMAError('Block too short for LZMA header')
    usize, plen = struct.unpack('<II', block[:8])
    if len(block) < 8 + plen:
        raise lzma.LZMAError('Truncated LZMA header properties')
    props = block[8:8 + plen]
    payload = block[8 + plen:]
    dec = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=lzma_filters(props))
    out = dec.decompress(payload, max_length=usize)
    return out

class IroArchive:
    def __init__(self, filepath):
        self.filepath = filepath
        self.entries = []
        self._handle = None
        self._read_header()

    def __enter__(self):
        self._handle = open(self.filepath, 'rb')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._handle:
            self._handle.close()
            self._handle = None

    def _read_header(self):
        with open(self.filepath, 'rb') as f:
            sig = f.read(4)
            if sig != b'IROS':
                raise ValueError("Not a valid 7th Heaven .iro archive (Missing IROS header signature).")
            ver, flags, hdr_len, num_files = struct.unpack('<iiii', f.read(16))
            
            for _ in range(num_files):
                rec_len, path_len = struct.unpack('<HH', f.read(4))
                raw_path = f.read(path_len)
                path_str = raw_path.decode('utf-16le', errors='ignore').rstrip('\x00').replace('/', os.sep).replace('\\', os.sep)
                file_flags, offset, data_len = struct.unpack('<IqI', f.read(16))
                self.entries.append({
                    'path': path_str,
                    'flags': file_flags,
                    'offset': offset,
                    'length': data_len
                })

    def extract_entry(self, entry, handle=None):
        close_handle = False
        if handle is None:
            if self._handle is not None:
                f = self._handle
            else:
                f = open(self.filepath, 'rb')
                close_handle = True
        else:
            f = handle

        try:
            f.seek(entry['offset'])
            data = f.read(entry['length'])
            flags = entry['flags']
            
            # Flags bitmask handling:
            # 0: Uncompressed
            # 1 (0x01): LZMA compressed
            # 2 (0x02): Zlib / Deflate compressed
            if flags == 0:
                return data
            
            if flags & 1:
                return decompress_lzma(data)
            
            if flags & 2:
                # Try standard zlib, raw DEFLATE (-wbits), or zlib/gzip auto-header
                try:
                    return zlib.decompress(data)
                except zlib.error:
                    pass
                try:
                    return zlib.decompress(data, -zlib.MAX_WBITS)
                except zlib.error:
                    pass
                try:
                    return zlib.decompress(data, zlib.MAX_WBITS | 32)
                except zlib.error:
                    pass
            
            # Fallback attempts if flag is non-standard or bitmask differs
            try:
                return decompress_lzma(data)
            except Exception:
                pass
            try:
                return zlib.decompress(data)
            except Exception:
                pass
            try:
                return zlib.decompress(data, -zlib.MAX_WBITS)
            except Exception:
                return data
        finally:
            if close_handle:
                f.close()

    def extract_all(self, target_dir, log_func=None):
        target_dir_abs = os.path.abspath(target_dir)
        
        with self:
            for entry in self.entries:
                out_path = os.path.abspath(os.path.normpath(os.path.join(target_dir_abs, entry['path'])))
                
                # Zip-Slip Security Guard: Ensure target path doesn't escape target_dir_abs
                if not out_path.startswith(target_dir_abs):
                    if log_func:
                        log_func(f"SECURITY WARNING: Skipped unsafe path traversal entry: {entry['path']}")
                    continue

                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                try:
                    content = self.extract_entry(entry, handle=self._handle)
                    with open(out_path, 'wb') as out_f:
                        out_f.write(content)
                    if log_func:
                        log_func(f"Unpacked: {entry['path']}")
                except Exception as e:
                    if log_func:
                        log_func(f"Error unpacking {entry['path']}: {e}")

def parse_mod_xml_info(xml_path_or_content):
    groups = []
    mod_name = None
    try:
        if os.path.exists(xml_path_or_content):
            tree = ET.parse(xml_path_or_content)
            root = tree.getroot()
        else:
            root = ET.fromstring(xml_path_or_content)

        # Extract name tag (only from top-level ModInfo/Name, not ConfigOption/Name)
        name_node = root.find('Name')
        if name_node is not None and name_node.text:
            raw_name = name_node.text.strip()
            cleaned_name = "".join(c for c in raw_name if c not in r'\/:*?"<>|').strip()
            if cleaned_name:
                mod_name = cleaned_name

        # 1. Check <Group> / <Option> schema
        for elem in root.iter():
            if elem.tag.lower() == 'group':
                group_name = elem.get('Name') or elem.get('name') or 'Options Group'
                options = []
                for child in elem:
                    if child.tag.lower() == 'option':
                        opt_name = child.get('Name') or child.get('name') or 'Option'
                        opt_folder = child.get('Folder') or child.get('folder') or ''
                        options.append({'name': opt_name, 'folder': opt_folder})
                if options:
                    groups.append({'name': group_name, 'options': options})

        # 2. If no <Group> found, check 7th Heaven <ConfigOption> & <ModFolder> schema
        if not groups:
            # Collect all declared ModFolders
            # Example: <ModFolder Folder="Cloud - Chibi" ActiveWhen="cloud_world = 2" />
            mod_folders = []
            for mf in root.findall('.//ModFolder'):
                folder = mf.get('Folder', '')
                active_when = mf.get('ActiveWhen', '')
                if folder:
                    mod_folders.append({'folder': folder, 'condition': active_when})

            for cfg in root.findall('.//ConfigOption'):
                cfg_name_node = cfg.find('Name')
                cfg_id_node = cfg.find('ID')
                cfg_name = cfg_name_node.text.strip() if cfg_name_node is not None and cfg_name_node.text else 'Option'
                cfg_id = cfg_id_node.text.strip() if cfg_id_node is not None and cfg_id_node.text else ''

                options = []
                # First check explicit <Option> elements in <ConfigOption>
                xml_options = cfg.findall('Option')
                for opt in xml_options:
                    opt_name = opt.get('Name', 'Option')
                    opt_val = opt.get('Value', '')

                    matched_folder = ""
                    if cfg_id and opt_val:
                        target_cond = f"{cfg_id} = {opt_val}"
                        for mf in mod_folders:
                            cond_norm = " ".join(mf['condition'].split())
                            if cond_norm.lower() == target_cond.lower():
                                matched_folder = mf['folder']
                                break
                    
                    if not matched_folder and opt_name != "No Change":
                        matched_folder = opt_name

                    options.append({'name': opt_name, 'folder': matched_folder})

                # Check if there are ModFolders linked to this cfg_id that were missing in <Option> tags
                if cfg_id:
                    prefix = cfg_id.split('_')[0].lower() # e.g. 'cloud' from 'cloud_world'
                    for mf in mod_folders:
                        f_lower = mf['folder'].lower()
                        if prefix in f_lower:
                            # Check if folder is already covered in options
                            if not any(o['folder'].lower() == f_lower for o in options if o['folder']):
                                options.append({'name': mf['folder'], 'folder': mf['folder']})

                if options:
                    groups.append({'name': cfg_name, 'options': options})

    except Exception as e:
        print(f"XML parse error: {e}")
    return mod_name, groups

class OptionSelectionDialog(tk.Toplevel):
    def __init__(self, parent, groups):
        super().__init__(parent)
        self.title("7th Heaven Mod Options")
        self.geometry("540x420")
        self.minsize(450, 320)
        self.configure(bg="#1e1e24")

        self.groups = groups
        self.selections = {}
        self.string_vars = {}

        lbl = ttk.Label(self, text="Customize Mod Options", font=("Segoe UI", 12, "bold"))
        lbl.pack(anchor="w", padx=15, pady=(15, 5))

        sub = ttk.Label(self, text="This mod includes optional packages. Select your preferred options:", font=("Segoe UI", 9), foreground="#a0a0b0")
        sub.pack(anchor="w", padx=15, pady=(0, 10))

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=15, pady=5)

        canvas = tk.Canvas(container, bg="#2b2b36", highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas, style="Card.TFrame")

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for idx, group in enumerate(groups):
            grp_lbl = ttk.Label(scroll_frame, text=group['name'], font=("Segoe UI", 10, "bold"), foreground="#ffffff")
            grp_lbl.pack(anchor="w", padx=10, pady=(10, 2))

            var = tk.StringVar(value=group['options'][0]['folder'] if group['options'] else "")
            self.string_vars[group['name']] = var

            for opt in group['options']:
                # Handle options without an explicit folder
                folder_val = opt['folder'] if opt['folder'] else "__none__"
                display_text = opt['name']
                if opt['folder'] and opt['folder'].lower() != opt['name'].lower():
                    display_text = f"{opt['name']}  ({opt['folder']})"
                elif not opt['folder']:
                    display_text = f"{opt['name']}  (No assets replaced)"

                rb = ttk.Radiobutton(scroll_frame, text=display_text, value=folder_val, variable=var)
                rb.pack(anchor="w", padx=25, pady=2)

        btn_box = ttk.Frame(self)
        btn_box.pack(fill="x", padx=15, pady=15)

        btn_confirm = ttk.Button(btn_box, text="Confirm & Convert", style="Primary.TButton", command=self._confirm)
        btn_confirm.pack(side="right", ipadx=10, ipady=4)

        self.grab_set()
        self.wait_window()

    def _confirm(self):
        for grp_name, var in self.string_vars.items():
            val = var.get()
            self.selections[grp_name] = "" if val == "__none__" else val
        self.destroy()

class ConverterGUI(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("7th Heaven -> FFVIISE Mod Loader Converter")
        self.geometry("720x580")
        self.minsize(640, 480)

        # Style configuration
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        
        # Colors & Fonts
        bg_color = "#1e1e24"
        fg_color = "#e1e1e6"
        accent_color = "#007acc"
        card_bg = "#2b2b36"

        self.configure(bg=bg_color)
        self.style.configure(".", background=bg_color, foreground=fg_color, font=("Segoe UI", 10))
        self.style.configure("TFrame", background=bg_color)
        self.style.configure("Card.TFrame", background=card_bg, relief="flat", borderwidth=1)
        self.style.configure("TLabel", background=bg_color, foreground=fg_color)
        self.style.configure("Card.TLabel", background=card_bg, foreground=fg_color)
        self.style.configure("Title.TLabel", background=bg_color, foreground="#ffffff", font=("Segoe UI", 14, "bold"))
        self.style.configure("Header.TLabel", background=bg_color, foreground="#a0a0b0", font=("Segoe UI", 9))
        self.style.configure("TEntry", fieldbackground="#ffffff", foreground="#000000", insertcolor="#000000")
        self.style.map("TEntry", fieldbackground=[("readonly", "#e4e4e8"), ("disabled", "#d0d0d5")], foreground=[("readonly", "#000000"), ("disabled", "#666666")])
        self.style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), background=accent_color, foreground="#ffffff", borderwidth=0)
        self.style.map("Primary.TButton", background=[("active", "#005999"), ("disabled", "#444450")])
        self.style.configure("Secondary.TButton", font=("Segoe UI", 9), background="#3a3a4c", foreground="#ffffff", borderwidth=0)
        self.style.map("Secondary.TButton", background=[("active", "#4a4a60")])

        self.source_path_var = tk.StringVar(value=get_default_source_dir())
        self.output_name_var = tk.StringVar(value="1ModLoaderPack")
        self.last_output_dir = None
        self.log_queue = queue.Queue()

        self._build_ui()
        self._poll_log_queue()

    def _build_ui(self):
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", padx=20, pady=(15, 10))
        
        title_label = ttk.Label(header_frame, text="7th Heaven Mod Pack Converter", style="Title.TLabel")
        title_label.pack(anchor="w")
        subtitle_label = ttk.Label(header_frame, text="Convert 7th Heaven .iro archives or loose folders into FFVII Steam Edition Mod Loader structure", style="Header.TLabel")
        subtitle_label.pack(anchor="w", pady=(2, 0))

        # Main Card / Input Settings
        card = ttk.Frame(self, style="Card.TFrame")
        card.pack(fill="x", padx=20, pady=10)
        card.columnconfigure(1, weight=1)

        # Source Path Selector (Folder or .iro)
        lbl_source = ttk.Label(card, text="Source (.iro or Folder):", style="Card.TLabel", font=("Segoe UI", 9, "bold"))
        lbl_source.grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))
        
        ent_source = ttk.Entry(card, textvariable=self.source_path_var, font=("Segoe UI", 9))
        ent_source.grid(row=0, column=1, sticky="ew", padx=(0, 5), pady=(15, 5))

        btn_browse_folder = ttk.Button(card, text="Folder...", style="Secondary.TButton", command=self._browse_folder)
        btn_browse_folder.grid(row=0, column=2, padx=2, pady=(15, 5))

        btn_browse_iro = ttk.Button(card, text=".iro File...", style="Secondary.TButton", command=self._browse_iro)
        btn_browse_iro.grid(row=0, column=3, padx=(2, 15), pady=(15, 5))

        # Custom Output Folder Name
        lbl_output = ttk.Label(card, text="Output Folder Name:", style="Card.TLabel", font=("Segoe UI", 9, "bold"))
        lbl_output.grid(row=1, column=0, sticky="w", padx=15, pady=(5, 15))
        
        ent_output = ttk.Entry(card, textvariable=self.output_name_var, font=("Segoe UI", 9))
        ent_output.grid(row=1, column=1, sticky="ew", padx=(0, 5), pady=(5, 15))

        lbl_hint = ttk.Label(card, text="(Default: 1ModLoaderPack)", style="Card.TLabel", font=("Segoe UI", 8), foreground="#8a8a9e")
        lbl_hint.grid(row=1, column=2, columnspan=2, sticky="w", padx=(2, 15), pady=(5, 15))

        # Progress & Action Section
        action_frame = ttk.Frame(self)
        action_frame.pack(fill="x", padx=20, pady=5)

        self.btn_convert = ttk.Button(action_frame, text="🚀 Convert Modpack", style="Primary.TButton", command=self._start_conversion)
        self.btn_convert.pack(side="left", pady=5, ipadx=10, ipady=4)

        self.btn_open_folder = ttk.Button(action_frame, text="📁 Open Output Folder", style="Secondary.TButton", command=self._open_output_folder, state="disabled")
        self.btn_open_folder.pack(side="right", pady=5, ipadx=5, ipady=4)

        self.btn_copy_steam = ttk.Button(action_frame, text="🎮 Copy to Steam mods/", style="Secondary.TButton", command=self._copy_to_steam_mods, state="disabled")
        self.btn_copy_steam.pack(side="right", padx=5, pady=5, ipadx=5, ipady=4)

        # Progress bar
        progress_frame = ttk.Frame(self)
        progress_frame.pack(fill="x", padx=20, pady=(2, 5))

        self.progress_bar = ttk.Progressbar(progress_frame, mode="determinate", value=0)
        self.progress_bar.pack(fill="x", side="left", expand=True)

        self.lbl_progress = ttk.Label(progress_frame, text="Ready", style="Header.TLabel", font=("Segoe UI", 8))
        self.lbl_progress.pack(side="right", padx=(10, 0))

        # Log Window
        log_frame = ttk.Frame(self)
        log_frame.pack(fill="both", expand=True, padx=20, pady=(5, 15))

        self.log_text = tk.Text(log_frame, bg="#141418", fg="#d4d4dc", font=("Consolas", 9), relief="flat", wrap="word", highlightthickness=0)
        self.log_text.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=scrollbar.set)

        # Check if Steam Mods folder auto-detected
        steam_mods = detect_ffvii_mods_dir()
        if steam_mods:
            self._log(f"Auto-detected Steam FFVII Mods Folder:\n  {steam_mods}\n")

        self._log("Ready to convert. Select an .iro file or extracted mod folder and click 'Convert Modpack'.\n")

    def _poll_log_queue(self):
        while not self.log_queue.empty():
            try:
                item = self.log_queue.get_nowait()
                if isinstance(item, tuple) and item[0] == "PROGRESS":
                    val, total, text = item[1], item[2], item[3]
                    if total > 0:
                        pct = int((val / total) * 100)
                        self.progress_bar['maximum'] = total
                        self.progress_bar['value'] = val
                        self.lbl_progress.config(text=f"{pct}% ({val}/{total}) - {text}")
                    else:
                        self.lbl_progress.config(text=text)
                else:
                    self.log_text.insert("end", str(item) + "\n")
                    self.log_text.see("end")
            except queue.Empty:
                break
        self.after(100, self._poll_log_queue)

    def _update_progress(self, current, total, status_text="Processing..."):
        self.log_queue.put(("PROGRESS", current, total, status_text))

    def _log(self, text):
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")

    def _browse_folder(self):
        chosen = filedialog.askdirectory(initialdir=os.path.dirname(self.source_path_var.get()), title="Select Mod Folder")
        if chosen:
            norm_path = os.path.normpath(chosen)
            self.source_path_var.set(norm_path)
            self._auto_detect_mod_name(norm_path)

    def _browse_iro(self):
        chosen = filedialog.askopenfilename(initialdir=os.path.dirname(self.source_path_var.get()), title="Select 7th Heaven .iro Archive", filetypes=[("7th Heaven Archive", "*.iro"), ("All Files", "*.*")])
        if chosen:
            norm_path = os.path.normpath(chosen)
            self.source_path_var.set(norm_path)
            self._auto_detect_mod_name(norm_path)

    def _auto_detect_mod_name(self, source_path):
        detected_name = None
        if os.path.isfile(source_path) and source_path.lower().endswith(".iro"):
            try:
                archive = IroArchive(source_path)
                for entry in archive.entries:
                    if os.path.basename(entry['path']).lower() == "mod.xml":
                        content = archive.extract_entry(entry)
                        detected_name, _ = parse_mod_xml_info(content)
                        break
            except Exception:
                pass
            if not detected_name:
                detected_name = os.path.splitext(os.path.basename(source_path))[0]
        elif os.path.isdir(source_path):
            mod_xml_path = os.path.join(source_path, "mod.xml")
            if os.path.exists(mod_xml_path):
                detected_name, _ = parse_mod_xml_info(mod_xml_path)
            if not detected_name:
                base = os.path.basename(source_path)
                if base and base.lower() not in ["dist", "build", "1modloaderpack"]:
                    detected_name = f"{base}_ModLoader"

        if detected_name:
            self.output_name_var.set(detected_name)
            self._log(f"Auto-detected output folder name: '{detected_name}'")
        else:
            self.output_name_var.set("1ModLoaderPack")

    def _start_conversion(self):
        source_path = self.source_path_var.get().strip()
        output_name = self.output_name_var.get().strip()

        if not source_path or not os.path.exists(source_path):
            messagebox.showerror("Error", "Selected source path does not exist!")
            return

        if not output_name:
            # Fall back to 1ModLoaderPack if user cleared or left empty
            output_name = "1ModLoaderPack"
            self.output_name_var.set(output_name)

        self.btn_convert.config(state="disabled")
        self.btn_open_folder.config(state="disabled")
        self.log_text.delete("1.0", "end")

        threading.Thread(target=self._run_conversion, args=(source_path, output_name), daemon=True).start()

    def _run_conversion(self, source_path, output_name):
        self.active_selections = {}
        self.all_option_folders = set()
        temp_dir = None
        try:
            if os.path.isfile(source_path) and source_path.lower().endswith(".iro"):
                self._log(f"Opening .iro archive:\n  {source_path}\n")
                archive = IroArchive(source_path)
                
                temp_dir = tempfile.mkdtemp(prefix="7th_iro_")
                self._log(f"Unpacking archive into temporary directory...")
                archive.extract_all(temp_dir, log_func=self._log)
                
                scan_dir = temp_dir
                base_out_dir = os.path.dirname(source_path)
            else:
                scan_dir = source_path
                base_out_dir = source_path

            # Check for mod.xml details & options (case-insensitive search)
            mod_xml_path = None
            for item in os.listdir(scan_dir):
                if item.lower() == "mod.xml":
                    mod_xml_path = os.path.join(scan_dir, item)
                    break

            if mod_xml_path and os.path.exists(mod_xml_path):
                detected_name, groups = parse_mod_xml_info(mod_xml_path)
                # If mod.xml specifies a name and user is using default name, update output_name
                if detected_name and output_name == "1ModLoaderPack":
                    output_name = detected_name
                    self._log(f"Using mod name from mod.xml: '{output_name}'")

                if groups:
                    self._log(f"\nFound mod.xml with {len(groups)} options group(s). Prompting configuration dialog...")
                    dlg_holder = {}
                    def show_dlg():
                        dlg = OptionSelectionDialog(self, groups)
                        dlg_holder['selections'] = dlg.selections

                    self.after(0, show_dlg)
                    while 'selections' not in dlg_holder:
                        self.update()

                    self.active_selections = dlg_holder['selections']
                    self.all_option_folders = set()
                    for grp in groups:
                        for opt in grp['options']:
                            if opt['folder']:
                                self.all_option_folders.add(os.path.normpath(opt['folder']).lower())

            dest_dir = os.path.join(base_out_dir, output_name)
            self.last_output_dir = dest_dir

            # Conflict / overwrite notice
            if os.path.exists(dest_dir) and os.listdir(dest_dir):
                self._log(f"NOTICE: Target directory '{output_name}' already exists. Merging/updating assets into existing folder.\n")

            self._log("\n" + "=" * 60)
            self._log(f"Converting assets into Mod Loader structure:\n  {dest_dir}\n")

            files_copied = 0
            folders_processed = 0
            processed_mod_folders = set()

            # Count total files for progress bar
            all_files_list = []
            for root, dirs, files in os.walk(scan_dir):
                for f in files:
                    if not f.startswith("."):
                        all_files_list.append(os.path.join(root, f))
            total_files_count = len(all_files_list)

            # If option selections were made in mod.xml dialog, filter scan_dir items
            selected_option_folders = set()
            if hasattr(self, 'active_selections') and self.active_selections:
                for grp, opt_folder in self.active_selections.items():
                    if opt_folder:
                        selected_option_folders.add(os.path.normpath(opt_folder).lower())

            processed_file_index = 0
            for root, dirs, files in os.walk(scan_dir):
                if not files:
                    continue

                rel_path = os.path.relpath(root, scan_dir)
                parts = rel_path.split(os.sep)

                # Ensure we don't copy from build/dist or from inside an existing output directory
                if any(p in ["build", "dist"] for p in parts):
                    continue
                if root.startswith(dest_dir):
                    continue

                # If option folders exist in this mod, check if top_level_folder is a configured option choice
                top_folder_lower = parts[0].lower()
                if selected_option_folders:
                    all_option_folders = getattr(self, 'all_option_folders', set())
                    if top_folder_lower in all_option_folders and top_folder_lower not in selected_option_folders:
                        continue

                matching_index = -1
                matching_key = None
                for idx in range(len(parts) - 1, -1, -1):
                    part_lower = parts[idx].lower()
                    if part_lower in FOLDER_MAPPING:
                        matching_index = idx
                        matching_key = part_lower
                        break

                if matching_key:
                    top_level_mod_name = parts[0]
                    if top_level_mod_name not in processed_mod_folders:
                        processed_mod_folders.add(top_level_mod_name)
                        folders_processed += 1
                        self._log(f"Processing [{folders_processed}]: {top_level_mod_name}")

                    target_base = FOLDER_MAPPING[matching_key]
                    if matching_key == "chocobo":
                        parent_parts_lower = [p.lower() for p in parts[:matching_index]]
                        if any(p in ["minigame", "minigames"] for p in parent_parts_lower):
                            target_base = os.path.join("minigame", "chocobo")
                    remaining_parts = parts[matching_index + 1:] if matching_index + 1 < len(parts) else []
                    
                    if remaining_parts and remaining_parts[0].lower() == os.path.basename(target_base).lower():
                        remaining_parts = remaining_parts[1:]
                        
                    sub_structure = os.path.join(*remaining_parts) if remaining_parts else ""
                    target_folder = os.path.join(dest_dir, target_base, sub_structure)

                    for file in files:
                        processed_file_index += 1
                        if file.startswith("."):
                            continue
                        os.makedirs(target_folder, exist_ok=True)
                        src_file = os.path.join(root, file)
                        dst_file = os.path.join(target_folder, file)
                        shutil.copy2(src_file, dst_file)
                        files_copied += 1
                        self._update_progress(processed_file_index, total_files_count, f"Copying {file}")

            self._log("\n" + "=" * 60)
            if files_copied > 0:
                self._update_progress(total_files_count, total_files_count, "Conversion Complete!")
                self._log(f"SUCCESS! Processed {folders_processed} folder(s) and merged {files_copied} asset file(s).")
                self._log(f"Output folder created at:\n  {dest_dir}\n")
                self._log("Next Step:")
                self._log(f"Copy the '{output_name}' folder directly into your FFVII Steam 'mods/' folder!")
                self.btn_open_folder.config(state="normal")
                if detect_ffvii_mods_dir():
                    self.btn_copy_steam.config(state="normal")
            else:
                self._update_progress(0, 0, "No assets matched")
                self._log("WARNING: No valid 7th Heaven mod files or recognized subfolders were found!")
                self._log("Make sure the source contains subfolders like:")
                self._log("  char, field, battle, magic, menu, world, music, sound, movies, stage, etc.")

        except Exception as e:
            self._log(f"\nERROR during conversion: {e}")

        finally:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            self.btn_convert.config(state="normal")

    def _open_output_folder(self):
        if self.last_output_dir and os.path.exists(self.last_output_dir):
            try:
                if sys.platform == "win32":
                    os.startfile(self.last_output_dir)
                elif sys.platform == "darwin":
                    subprocess.run(["open", self.last_output_dir])
                else:
                    subprocess.run(["xdg-open", self.last_output_dir])
            except Exception as e:
                messagebox.showerror("Error", f"Could not open output folder: {e}")

    def _copy_to_steam_mods(self):
        steam_mods = detect_ffvii_mods_dir()
        if not steam_mods:
            steam_mods = filedialog.askdirectory(title="Select FFVII Steam 'mods' Directory")

        if steam_mods and self.last_output_dir and os.path.exists(self.last_output_dir):
            target_dest = os.path.join(steam_mods, os.path.basename(self.last_output_dir))
            try:
                os.makedirs(steam_mods, exist_ok=True)
                self._log(f"\nCopying mod folder directly to Steam mods directory:\n  {target_dest}")
                shutil.copytree(self.last_output_dir, target_dest, dirs_exist_ok=True)
                self._log(f"✅ Successfully installed mod to:\n  {target_dest}\n")
                messagebox.showinfo("Success", f"Mod installed to Steam FFVII mods directory!\n\nLocation:\n{target_dest}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to copy mod to Steam mods folder: {e}")

if __name__ == "__main__":
    app = ConverterGUI()
    app.mainloop()



