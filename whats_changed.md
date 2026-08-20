# 7th Heaven to FFVIISE Mod Loader Converter - Changelog

## [2.0.0] - 2026-08-20
- Fixed `.iro` archive unpacking for `Remastered Backgrounds.iro` and similar mods by implementing proper bitmask checking (`flags & 1` for LZMA, `flags & 2` for Deflate/zlib).
- Added multi-stage fallback decompression for zlib streams lacking standard headers (raw DEFLATE `-MAX_WBITS` & gzip headers).
- Deep backward path matching: Scans full directory paths to locate target asset folders (`char`, `flevel`, `battle`, etc.) even when nested under arbitrary IroNite or 7th Heaven subfolders.
- Diagnostic troubleshooting output: If 0 files match, prints clear guidance on expected subfolder names instead of falsely reporting success.
- Expanded folder mapping: Added support for `wm`, `textures`, `override`, and `direct`.


## [1.0.0] - 2026-08-05
### Added
- Initial standalone release of `ConvertForModLoader.exe`.
- Automatic 7th Heaven subfolder mapping (`char`, `chocobo`, `field`, `battle`, `magic`, `stage`, `menu`, `world`, `high`, `sub`, `snowboard`, `condor`, `coaster`).
- Portable directory auto-detection.
- Merges multi-folder modpacks into `1ModLoaderPack`.
