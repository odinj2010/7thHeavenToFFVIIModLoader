# 7th Heaven to FFVII SE Mod Loader Converter (ConvertForModLoader.exe)

A lightweight, portable utility designed to convert unpacked or raw .iro 7th Heaven mod archives into loose, compatible folder structures for the **Final Fantasy VII Steam Edition Mod Loader (d3d11.dll)**.

---

## ?? Features

- **Direct .iro Support**: Unpack and convert standard .iro archives on the fly without needing 7th Heaven installed.
- **Deep Path Matching**: Traverses directory structures of any depth to map assets correctly, making it fully compatible with custom extraction tools like **IroNite** or custom folder layouts.
- **Interactive Mod Options (mod.xml)**: Parses 7th Heaven <Group> / <Option> and <ConfigOption> XML schemas to present clean option selection dialogs for variant choices (e.g. Character skins, battle models, menu styles).
- **Zlib & LZMA Decompression**: Built-in support for standard zlib, raw DEFLATE streams (-MAX_WBITS), LZMA, and Gzip-compressed .iro entries.
- **Automated Directory Mapping**: Maps 7th Heaven asset subfolders (char, ield, attle, magic, menu, world, music, sound, movies, minigames) directly into standard Mod Loader paths (mods/1ModLoaderPack/...).
- **Diagnostic Logging**: Clear log feedback and warnings if 0 files are copied or if folder structure mismatches occur.

---

## ?? Quick Start

1. **Download**: Download ConvertForModLoader.exe from the [dist/](./dist/) folder or the latest GitHub Release.
2. **Launch**: Run ConvertForModLoader.exe.
3. **Select Source**: Choose your .iro archive file OR an unpacked mod folder.
4. **Choose Options**: If the mod contains optional configurations (mod.xml), select your desired settings in the pop-up dialog.
5. **Convert**: Click **Convert & Merge**. The tool will output a clean mod folder named 1ModLoaderPack (or your custom mod folder name).
6. **Install**: Copy the generated output folder into your **FFVII Steam Edition mods/** directory:
   `	ext
   FINAL FANTASY VII Steam Edition/mods/1ModLoaderPack/
   `

---

## ?? Supported Asset Mappings

| 7th Heaven Subfolder | Target Mod Loader Path | Description |
| :--- | :--- | :--- |
| char, chocobo | ield/char/ | Field Character Models & Textures |
| ield, level | ield/flevel/ | Field Backgrounds & Map Scripts |
| world, wm | wm/world_us/ | World Map Models & Textures |
| attle | attle/battle/ | Battle Models, Monsters & FX |
| magic | attle/magic/ | Spell & Ability Effects |
| stage | attle/stage/ | Battle Arena Environments |
| menu, menu_us | menu/menu_us/ | UI, Avatars & Font Textures |
| music | music_ogg/ | High Quality OGG Audio Tracks |
| sound | sound/ | Game Sound Effects |
| movies | movies/ | Cutscene BIK Videos |
| minigame, high | minigame/high-us/ | Highwind Minigame Assets |
| sub | minigame/sub/ | Submarine Minigame Assets |
| snowboard | minigame/snowboard-us/ | Snowboard Minigame Assets |

---

## ??? Building From Source

Requirements:
- Python 3.10+
- PyInstaller (pip install pyinstaller)

Build command:
`cmd
python -m PyInstaller ConvertForModLoader.spec --clean
`
The compiled standalone executable will be generated inside the dist/ directory.

---

## ?? License & Credits

Developed by **NfgOdin** for the Final Fantasy VII modding community.
- Compatible with the **FFVIISE Direct File Mod Loader (d3d11.dll)**.

