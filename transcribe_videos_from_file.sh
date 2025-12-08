#!/usr/bin/env bash
set -euo pipefail

# Config defaults (override with env vars if needed)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKDIR="${WORKDIR:-$SCRIPT_DIR}"
URL_FILE="${URL_FILE:-$WORKDIR/video_urls.txt}"
OUTDIR="${OUTDIR:-$WORKDIR/transcriptions}"
MODEL="${MODEL:-small}"
# Use a dedicated var so locale LANG does not override Whisper language
WHISPER_LANG="${WHISPER_LANG:-en}"

cd "$WORKDIR"
mkdir -p "$OUTDIR"

if [ ! -f "$URL_FILE" ]; then
  echo "URL list file not found: $URL_FILE" >&2
  exit 1
fi

# Clean leftover audio so we only keep text outputs
rm -f "$WORKDIR"/*.webm "$WORKDIR"/*.mp3 "$WORKDIR"/*.m4a "$WORKDIR"/*.wav "$WORKDIR"/*.flac || true

while IFS= read -r url; do
  # Skip blank lines and comments
  [[ -z "${url// }" ]] && continue
  [[ "$url" =~ ^# ]] && continue

  echo "=== Processing: $url ==="

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
    continue
  fi

  # Transcribe with Whisper to txt
  WHISPER_CMD="${WHISPER_CMD:-$HOME/.local/bin/whisper}"
  whisper_args=( "$audio_file" --model "$MODEL" --output_dir "$OUTDIR" --output_format txt )
  if [ -n "$WHISPER_LANG" ]; then
    whisper_args+=( --language "$WHISPER_LANG" )
  fi
  "$WHISPER_CMD" "${whisper_args[@]}"

  # Normalize transcript filename to Title.txt
  base="$(basename "$audio_file")"
  stem="${base%.*}"
  candidate1="$OUTDIR/$base.txt"
  candidate2="$OUTDIR/$stem.txt"
  final_txt="$candidate2"

  if [ -f "$candidate1" ] && [ "$candidate1" != "$candidate2" ]; then
    mv "$candidate1" "$candidate2"
  elif [ -f "$candidate1" ]; then
    final_txt="$candidate1"
  elif [ -f "$candidate2" ]; then
    final_txt="$candidate2"
  else
    echo "Transcript file not found for: $audio_file" >&2
  fi

  echo "Transcript saved as: $final_txt"

  # Remove downloaded audio to leave only text
  rm -f "$audio_file"
  echo
done < "$URL_FILE"

echo "All done. Check $OUTDIR for the .txt transcript files."
