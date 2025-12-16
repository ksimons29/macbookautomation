# Unified Transcribe

A simple one stop workflow that downloads audio from YouTube or accepts audio files you drop from iPhone, then transcribes via the OpenAI API and saves one transcript text file per audio file.

This project is built around one script:

`unified_transcribe.py`

## What it does

1. Reads YouTube links from `video_urls.txt` in your inbox folder
2. Downloads audio for those links into the inbox folder
3. Looks for audio files in the inbox folder root
4. Transcribes each new audio file using the OpenAI API
5. Saves a separate transcript text file per audio into `Transcripts`
6. Moves the processed audio into `Archive`
7. Never transcribes the same audio content twice, even if the file returns later

## Folder layout

Your inbox folder is:

`iCloud Drive/Portuguese/Transcrições`

Inside it you will have:

1. `video_urls.txt`  
   One YouTube URL per line

2. `Transcripts/`  
   Output transcript files, one txt per audio file

3. `Archive/`  
   Audio files that were successfully processed

4. `transcribed_index.jsonl`  
   The no re transcribe index, keyed by file SHA256

5. `youtube_downloaded_archive.txt`  
   The no re download index for YouTube video ids

## Transcript filenames

Every transcript is saved as a separate txt file. The filename always starts with date and time, taken from the audio file modified time.

Example:

`20251215 231455 Cinco hipermecados assaltados em Lisboa [vwzQwxzXus8].txt`

If a filename already exists, the script adds a counter suffix.

## Requirements

You already have these working if the script ran successfully once:

1. Python 3
2. OpenAI Python package `openai`
3. `yt-dlp` for YouTube downloads
4. `ffmpeg` for audio extraction and optional compression
5. A valid OpenAI API key stored in Keychain or set as an environment variable

## OpenAI API key

The script looks for the key in this order:

1. `OPENAI_API_KEY` environment variable
2. macOS Keychain service name: `anki-tools-openai`

If both exist, the environment variable wins.

Recommended setup is Keychain plus unsetting `OPENAI_API_KEY` if you have multiple projects.

## Portuguese transcription preference

The script biases toward Portuguese using the language hint `pt`.

Use:

`TRANSCRIBE_PT_VARIANT="pt"`

Do not use `pt-PT` because the API expects ISO 639 1 format and will reject it.

## How to run from VS Code terminal

In VS Code, open the folder that contains `unified_transcribe.py`, then open the integrated terminal and run:

```bash
export INBOX_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/Portuguese/Transcrições"
unset OPENAI_API_KEY
export TRANSCRIBE_MODEL="whisper-1"
export TRANSCRIBE_PT_VARIANT="pt"
python unified_transcribe.py