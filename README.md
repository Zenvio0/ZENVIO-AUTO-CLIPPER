# ZENVIO AUTO CLIPPER

A free, local-first video clipping studio for footage you own or are authorized to edit.

## Included
- Scene-change based clip candidate suggestions (visual heuristic, not semantic/viral AI).
- Batch MP4 rendering and ZIP download.
- 9:16, 1:1 and 16:9 canvas options.
- 720p, 1080p and 4K export.
- SRT import and subtitle burn-in.
- Six subtitle presets: Viral Yellow, Bold Creator, Cinematic, Neon Glow, Karaoke and Minimal White.
- Optional local speech transcription with faster-whisper. No paid API is used.

## Requirements
- Python 3.11 or 3.12 recommended on Windows.
- FFmpeg and FFprobe installed and available in PATH.
- Free disk space for source and rendered videos.

## Windows setup
1. Install Python and FFmpeg.
2. Open PowerShell in this folder.
3. Run: `python -m pip install -r requirements.txt`
4. Run: `python -m streamlit run app.py`
5. Open the local URL shown in the terminal.

Optional transcription: install faster-whisper with `python -m pip install faster-whisper`. It may need a compatible Python/CTranslate2 environment; Python 3.11/3.12 is recommended. SRT upload works without transcription.

## Notes
- 4K exports can be slow and use substantial disk space, especially on CPU.
- Clip suggestions are based on scene changes and duration heuristics; they are not guaranteed viral moments.
- The project does not download online videos or bypass copyright systems. Process only material you own or are licensed to use.
