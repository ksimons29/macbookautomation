# YouTube Video Transcriber

Shell script to download YouTube videos as audio, transcribe them with Whisper, and keep only a clean `.txt` transcript per video.

## Files
- `transcribe_videos_from_file.sh`: main runner. Reads URLs from `video_urls.txt`, downloads audio with `yt-dlp`, transcribes with Whisper, renames to `Title.txt`, and deletes the audio files.
- `video_urls.txt`: one YouTube URL per line (blank lines and `#` comments are ignored).
- `transcriptions/`: output folder for transcripts.

## Requirements
- `yt-dlp`, `ffmpeg`, and `whisper` (OpenAI Whisper CLI).

## Usage
```bash
cd "$HOME/yt-transcript-env"
# optional overrides:
# WORKDIR=/path/to/workdir URL_FILE=/path/to/urls.txt OUTDIR=/path/to/out WHISPER_LANG=en MODEL=small
bash transcribe_videos_from_file.sh
```

## Notes
- The script cleans leftover audio files before starting and deletes each downloaded audio after its transcript is saved.
- Whisper language defaults to `en` via `WHISPER_LANG`. This avoids locale variables overriding the language flag.
