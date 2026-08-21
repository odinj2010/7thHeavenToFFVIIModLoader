# 7th Heaven to FFVIISE Mod Loader Converter - Changelog

## [2.0.1] - Unreleased
- Context-aware Chocobo routing: Resolved dictionary mapping collision; routes `chocobo.lgp`, `chocobo_race`, and minigame-nested folders to `minigame/chocobo/` while field chocobos map to `field/char/`.
- Security: Implemented Zip-Slip path traversal protection in `IroArchive.extract_all` to validate destination target bounds.
- Performance: Added context management (`__enter__` / `__exit__`) to `IroArchive` to reuse open file handles during batch extraction.
- Stability: Added thread-safe `queue.Queue` log buffering and polling loop to eliminate UI thread race conditions.
- Steam Auto-Detection: Automatically queries Windows Registry to locate Steam FFVII installation directory.
- Direct Game Installation: Added `🎮 Copy to Steam mods/` GUI button to copy converted mod folders directly into the game's `mods/` directory with 1 click.
- Real-Time Progress Bar: Integrated `ttk.Progressbar` and file count status indicator during conversion.
- Conflict & Overwrite Warnings: Displays notice when converting into an existing output folder.

## [2.0.0] - 2026-08-20
- Fixed `.iro` archive unpacking for `Remastered Backgrounds.iro` and similar mods by implementing proper bitmask checking (`flags & 1` for LZMA, `flags & 2` for Deflate/zlib).
- Added multi-stage fallback decompression for zlib streams lacking standard headers (raw DEFLATE `-MAX_WBITS` & gzip headers).
- Deep backward path matching: Scans full directory paths to locate target asset folders (`char`, `flevel`, `battle`, etc.) even when nested under arbitrary IroNite or 7th Heaven subfolders.
- Duplicate archive nesting normalization: Prevents duplicate nested paths (e.g. `field/flevel/flevel/ancnt1` -> `field/flevel/ancnt1`).
- Interactive `mod.xml` Option Parser (WIP / Experimental): Parses `<Group>`/`<Option>` and `<ConfigOption>` XML schemas to present option selection dialogs during conversion.
- Diagnostic troubleshooting output: If 0 files match, prints clear guidance on expected subfolder names instead of falsely reporting success.
- Expanded folder mapping: Added support for `wm`, `textures`, `override`, and `direct`.


## [1.0.0] - 2026-08-05
### Added
- Initial standalone release of `ConvertForModLoader.exe`.
- Automatic 7th Heaven subfolder mapping (`char`, `chocobo`, `field`, `battle`, `magic`, `stage`, `menu`, `world`, `high`, `sub`, `snowboard`, `condor`, `coaster`).
- Portable directory auto-detection.
- Merges multi-folder modpacks into `1ModLoaderPack`.
