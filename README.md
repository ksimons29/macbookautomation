# YouTube Video Transcriber

Shell script to download YouTube videos as audio, transcribe them with Whisper, and keep only a clean `.txt` transcript per video.

## Files
- `transcribe_videos_from_file.sh`: main runner. Reads URLs from `video_urls.txt`, downloads audio with `yt-dlp`, transcribes with Whisper, renames to `Title.txt`, and deletes the audio files.
- `video_urls.txt`: one YouTube URL per line (blank lines and `#` comments are ignored). Pre-filled with the provided Claude-related links.
- `transcriptions/`: output folder for transcripts.

## Requirements
- `yt-dlp`, `ffmpeg`, and `whisper` (OpenAI Whisper CLI).

## Usage
```bash
cd /Users/koossimons/macbookautomation
# optional overrides:
# WORKDIR=/path/to/workdir URL_FILE=/path/to/urls.txt OUTDIR=/path/to/out WHISPER_LANG=en MODEL=small
bash transcribe_videos_from_file.sh
```

## Notes
- Defaults to working in the repo directory; override via env vars if you prefer another workspace.
- Cleans leftover audio files before starting and deletes each downloaded audio after its transcript is saved.
- Whisper language defaults to `en` via `WHISPER_LANG` so locale variables (e.g., `LANG=C.UTF-8`) don’t interfere.
