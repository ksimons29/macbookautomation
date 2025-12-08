# YouTube Video Transcriber

This project automates downloading and transcribing YouTube videos using `yt-dlp` and OpenAI's Whisper.

## Project Structure

- `transcribe_videos_from_file.sh` - Main script that reads URLs from a file and transcribes each video
- `transcribe_playlist_combined.sh` - Script for processing entire YouTube playlists
- `video_urls.txt` - Input file with YouTube URLs (one per line, supports `#` comments)
- `transcriptions/` - Output folder containing `.txt` transcript files

## Dependencies

- `yt-dlp` - YouTube video/audio downloader
- `ffmpeg` - Audio processing
- `whisper` - OpenAI Whisper CLI for transcription (default path: `~/.local/bin/whisper`)

## Usage

```bash
# Basic usage (uses defaults)
bash transcribe_videos_from_file.sh

# With custom settings
WORKDIR=/path/to/workdir URL_FILE=/path/to/urls.txt OUTDIR=/path/to/out bash transcribe_videos_from_file.sh
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WORKDIR` | Script directory | Working directory |
| `URL_FILE` | `$WORKDIR/video_urls.txt` | File containing YouTube URLs |
| `OUTDIR` | `$WORKDIR/transcriptions` | Output directory for transcripts |
| `MODEL` | `small` | Whisper model size |
| `WHISPER_LANG` | `en` | Transcription language |
| `WHISPER_CMD` | `~/.local/bin/whisper` | Path to whisper executable |

## Notes

- Audio files are automatically deleted after transcription
- Leftover audio files are cleaned at script start
- Transcripts are named after the video title (e.g., `Video Title.txt`)
