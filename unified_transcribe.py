#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import sys
import json
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Iterable

from openai import OpenAI
import yt_dlp

KEYCHAIN_SERVICE_API_KEY = "anki-tools-openai"

AUDIO_EXTS = {
    ".mp3",
    ".mp4",
    ".mpeg",
    ".mpga",
    ".m4a",
    ".wav",
    ".webm",
    ".ogg",
    ".oga",
    ".flac",
}

MAX_UPLOAD_BYTES_DEFAULT = 25 * 1024 * 1024


def configure_utf8_io() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def sanitize_api_key(key: str) -> str:
    key = (key or "").strip()
    key = key.replace("“", "").replace("”", "").replace("‘", "").replace("’", "")
    key = key.strip().strip('"').strip("'")
    key = key.encode("ascii", "ignore").decode("ascii")
    return key.strip()


def read_api_key() -> str:
    env_key = sanitize_api_key(os.environ.get("OPENAI_API_KEY", ""))
    if env_key:
        return env_key

    try:
        key = subprocess.check_output(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE_API_KEY, "-w"],
            text=True,
        )
        key = sanitize_api_key(key)
        if not key:
            raise RuntimeError("Empty or invalid key returned from Keychain after sanitization")
        return key
    except Exception as e:
        raise RuntimeError(
            "OpenAI API key not found. Set OPENAI_API_KEY or store it in Keychain.\n"
            'Keychain example:\n'
            'security add-generic-password -a "$USER" -s "anki-tools-openai" -w "YOUR_KEY" -U'
        ) from e


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def load_urls(url_file: Path) -> list[str]:
    if not url_file.exists():
        return []

    lines = url_file.read_text(encoding="utf-8").splitlines()
    urls: list[str] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        urls.append(line)
    return urls


def download_youtube_audio(urls: list[str], inbox: Path) -> None:
    if not urls:
        return

    ensure_dir(inbox)

    archive_file = inbox / "youtube_downloaded_archive.txt"

    ydl_opts = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "download_archive": str(archive_file),
        "outtmpl": str(inbox / "%(title).200s [%(id)s].%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
                "preferredquality": "0",
            }
        ],
        "quiet": False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download(urls)


def iter_audio_files(inbox: Path) -> Iterable[Path]:
    for p in sorted(inbox.iterdir()):
        if p.is_file() and p.suffix.lower() in AUDIO_EXTS:
            yield p


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def load_done_hashes(index_file: Path) -> set[str]:
    if not index_file.exists():
        return set()

    done: set[str] = set()
    for line in index_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            h = obj.get("sha256", "")
            if h:
                done.add(h)
        except Exception:
            continue
    return done


def append_index_record(index_file: Path, record: dict) -> None:
    with index_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def date_stamp_for_filename(audio_path: Path) -> str:
    ts = audio_path.stat().st_mtime
    return datetime.fromtimestamp(ts).strftime("%Y%m%d %H%M%S")


def safe_stem(s: str) -> str:
    bad = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', "“", "”", "‘", "’"]
    out = s
    for ch in bad:
        out = out.replace(ch, " ")
    out = " ".join(out.split())
    return out


def make_unique_txt_path(folder: Path, base_name: str) -> Path:
    candidate = folder / f"{base_name}.txt"
    if not candidate.exists():
        return candidate

    i = 2
    while True:
        candidate = folder / f"{base_name} {i}.txt"
        if not candidate.exists():
            return candidate
        i += 1


def maybe_compress_if_too_large(audio_path: Path, max_bytes: int) -> Path:
    if audio_path.stat().st_size <= max_bytes:
        return audio_path

    compressed = audio_path.with_suffix(".compressed.m4a")
    if compressed.exists():
        compressed.unlink()

    subprocess.check_call(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(audio_path),
            "-vn",
            "-c:a",
            "aac",
            "-b:a",
            "64k",
            str(compressed),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    return compressed


def preferred_language() -> str:
    # OpenAI expects ISO-639-1 codes for language, so Portuguese must be "pt"
    raw = os.environ.get("TRANSCRIBE_PT_VARIANT", "pt").strip()
    raw_lower = raw.lower()

    # Normalize common variants
    if raw_lower in {"pt-pt", "pt_pt", "ptpt", "portuguese", "português"}:
        return "pt"
    if raw_lower in {"pt-br", "pt_br", "ptbr"}:
        return "pt"

    # If user set something longer like "pt-PT", keep only the ISO-639-1 part
    if "-" in raw_lower:
        raw_lower = raw_lower.split("-", 1)[0]

    # Final fallback
    return raw_lower or "pt"

def transcribe_with_openai(client: OpenAI, audio_path: Path, model: str, language: str | None) -> str:
    with audio_path.open("rb") as f:
        kwargs = {
            "model": model,
            "file": f,
        }
        # If language is provided, it biases strongly toward that language
        if language:
            kwargs["language"] = language

        result = client.audio.transcriptions.create(**kwargs)

    text = getattr(result, "text", None)
    if not text:
        raise RuntimeError("No transcript text returned by API")

    return str(text).strip()


def main() -> int:
    configure_utf8_io()

    inbox_str = os.environ.get("INBOX_DIR", "").strip()
    if not inbox_str:
        raise RuntimeError("Set INBOX_DIR to your iCloud Transcrições folder path")

    inbox = Path(inbox_str).expanduser()
    ensure_dir(inbox)

    transcripts_dir = inbox / "Transcripts"
    ensure_dir(transcripts_dir)

    archive_dir = inbox / "Archive"
    ensure_dir(archive_dir)

    url_file = inbox / "video_urls.txt"
    urls = load_urls(url_file)
    if urls:
        download_youtube_audio(urls, inbox)

    api_key = read_api_key()
    client = OpenAI(api_key=api_key)

    model = os.environ.get("TRANSCRIBE_MODEL", "whisper-1").strip()

    # Default is Portuguese. If you want to allow auto detection, set TRANSCRIBE_AUTO_DETECT=1
    auto_detect = os.environ.get("TRANSCRIBE_AUTO_DETECT", "0").strip() == "1"
    language = None if auto_detect else preferred_language()

    move_audio = os.environ.get("MOVE_AUDIO_TO_ARCHIVE", "1").strip() == "1"
    move_skipped = os.environ.get("MOVE_SKIPPED_TO_ARCHIVE", "1").strip() == "1"

    max_bytes = int(os.environ.get("MAX_UPLOAD_BYTES", str(MAX_UPLOAD_BYTES_DEFAULT)).strip())

    errors_log = transcripts_dir / "transcribe_errors.log"

    index_file = inbox / "transcribed_index.jsonl"
    done_hashes = load_done_hashes(index_file)

    ok = 0
    skipped = 0
    failed = 0

    for audio in iter_audio_files(inbox):
        try:
            file_hash = sha256_file(audio)
        except Exception as e:
            failed += 1
            with errors_log.open("a", encoding="utf-8") as f:
                f.write(f"{datetime.now().isoformat()}  {audio.name}  hash_error  {e}\n")
            continue

        if file_hash in done_hashes:
            skipped += 1
            if move_skipped:
                try:
                    audio.replace(archive_dir / audio.name)
                except Exception:
                    pass
            continue

        stamp = date_stamp_for_filename(audio)
        cleaned_stem = safe_stem(audio.stem)
        base_name = f"{stamp} {cleaned_stem}"
        txt_path = make_unique_txt_path(transcripts_dir, base_name)

        working_audio = audio
        created_temp = False

        try:
            if audio.stat().st_size > max_bytes:
                working_audio = maybe_compress_if_too_large(audio, max_bytes)
                created_temp = working_audio != audio

            print(f"Transcribing {audio.name}")
            text = transcribe_with_openai(client, working_audio, model=model, language=language)

            header_lines = [
                f"DateStamp {stamp}",
                f"AudioFile {audio.name}",
                f"Sha256 {file_hash}",
                f"Model {model}",
                f"LanguageHint {language or 'auto'}",
                "",
            ]

            txt_path.write_text("\n".join(header_lines) + text + "\n", encoding="utf-8")

            append_index_record(
                index_file,
                {
                    "sha256": file_hash,
                    "audio_file": audio.name,
                    "transcript_file": str(txt_path.relative_to(inbox)),
                    "date_stamp": stamp,
                    "model": model,
                    "language_hint": language or "auto",
                    "created_at": datetime.now().isoformat(),
                },
            )
            done_hashes.add(file_hash)

            ok += 1

            if move_audio:
                audio.replace(archive_dir / audio.name)

        except Exception as e:
            failed += 1
            with errors_log.open("a", encoding="utf-8") as f:
                f.write(f"{datetime.now().isoformat()}  {audio.name}  transcribe_error  {e}\n")
            print(f"Failed {audio.name}  {e}")

        finally:
            if created_temp:
                try:
                    working_audio.unlink()
                except Exception:
                    pass

    print(f"Done  success {ok}  skipped {skipped}  failed {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())