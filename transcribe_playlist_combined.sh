#!/usr/bin/env bash
set -euo pipefail

# Config defaults (override with env vars if needed)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKDIR="${WORKDIR:-$SCRIPT_DIR}"
PLAYLIST_URL="${PLAYLIST_URL:-}"
OUTDIR="${OUTDIR:-$WORKDIR/transcriptions}"
OUTPUT_FILE="${OUTPUT_FILE:-$OUTDIR/playlist_combined.txt}"
MODEL="${MODEL:-small}"
# Use a dedicated var so locale LANG does not override Whisper language
WHISPER_LANG="${WHISPER_LANG:-en}"
WHISPER_CMD="${WHISPER_CMD:-$HOME/.local/bin/whisper}"

cd "$WORKDIR"
mkdir -p "$OUTDIR"

if [ -z "$PLAYLIST_URL" ]; then
  echo "Usage: PLAYLIST_URL=<url> bash $0" >&2
  echo "Example: PLAYLIST_URL='https://www.youtube.com/playlist?list=...' bash $0" >&2
  exit 1
fi

# Clean leftover audio so we only keep text outputs
rm -f "$WORKDIR"/*.webm "$WORKDIR"/*.mp3 "$WORKDIR"/*.m4a "$WORKDIR"/*.wav "$WORKDIR"/*.flac || true

# Clear/create the combined output file
> "$OUTPUT_FILE"

echo "=== Downloading playlist metadata ===" >&2
# Get playlist title
playlist_title="$(yt-dlp --flat-playlist --print playlist_title "$PLAYLIST_URL" 2>/dev/null | head -1 || echo "YouTube Playlist")"
echo "Playlist: $playlist_title" | tee -a "$OUTPUT_FILE"
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

# Get all video URLs from the playlist
video_urls=()
while IFS= read -r url; do
  video_urls+=("$url")
done < <(yt-dlp --flat-playlist --print url "$PLAYLIST_URL" 2>/dev/null)

total_videos="${#video_urls[@]}"
echo "Found $total_videos videos in playlist" >&2
echo ""

current=1
for url in "${video_urls[@]}"; do
  echo "=== Processing video $current/$total_videos: $url ===" >&2

  # Get video title before downloading
  video_title="$(yt-dlp --print title --no-warnings --quiet "$url" 2>/dev/null | head -1 || echo "Video $current")"
  echo "Title: $video_title" >&2

  # Download audio
  audio_file="$(
    yt-dlp \
      -x --audio-format mp3 --audio-quality 0 \
      --no-progress --quiet --no-warnings \
      -o '%(title)s.%(ext)s' \
      --print after_move:filepath \
      "$url" | tail -n 1
  )"

  if [ -z "$audio_file" ] || [ ! -f "$audio_file" ]; then
    echo "Download failed for: $url" >&2
    echo "=== TRANSCRIPTION FAILED FOR: $video_title ===" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    ((current++))
    continue
  fi

  echo "Downloaded: $audio_file" >&2

  # Transcribe with Whisper to txt
  temp_outdir="$OUTDIR/temp_$$"
  mkdir -p "$temp_outdir"

  whisper_args=( "$audio_file" --model "$MODEL" --output_dir "$temp_outdir" --output_format txt )
  if [ -n "$WHISPER_LANG" ]; then
    whisper_args+=( --language "$WHISPER_LANG" )
  fi

  echo "Transcribing..." >&2
  "$WHISPER_CMD" "${whisper_args[@]}"

  # Find the transcript file
  base="$(basename "$audio_file")"
  stem="${base%.*}"
  candidate1="$temp_outdir/$base.txt"
  candidate2="$temp_outdir/$stem.txt"

  transcript_file=""
  if [ -f "$candidate1" ]; then
    transcript_file="$candidate1"
  elif [ -f "$candidate2" ]; then
    transcript_file="$candidate2"
  fi

  if [ -z "$transcript_file" ] || [ ! -f "$transcript_file" ]; then
    echo "Transcript file not found for: $audio_file" >&2
    echo "=== TRANSCRIPTION FAILED FOR: $video_title ===" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
  else
    # Append to combined file with header
    echo "=== VIDEO $current/$total_videos: $video_title ===" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    cat "$transcript_file" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    echo "========================================" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    echo "Transcript appended to combined file" >&2
  fi

  # Clean up temp files
  rm -rf "$temp_outdir"
  rm -f "$audio_file"

  echo "Video $current/$total_videos complete" >&2
  echo "" >&2
  ((current++))
done

echo "=== All done! ===" >&2
echo "Combined transcript saved to: $OUTPUT_FILE" >&2
echo "" >&2
echo "Total videos processed: $total_videos" >&2
