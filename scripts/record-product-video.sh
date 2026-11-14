#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TASK_TMP="/tmp/restockos-video"
mkdir -p "$TASK_TMP" "$ROOT/videos"

for tool in screencapture say ffmpeg ffprobe node; do
  command -v "$tool" >/dev/null || { echo "Missing required recording tool: $tool" >&2; exit 1; }
done

echo "Show the RestockOS hosted demo full-screen in Chrome before starting."
echo "The next capture lasts 103 seconds and includes the cursor/clicks."
echo "Do not show wallet prompts, credentials, unrelated tabs, or private data."
read -r -p "Press Return when the app is ready to record: " _

screencapture -v -C -k -m -V 103 "$TASK_TMP/screen.mov"
say -v Daniel -r 145 -f "$ROOT/videos/voiceover.txt" -o "$TASK_TMP/voiceover.aiff"
node "$ROOT/scripts/render-demo-video.mjs"
ffprobe -v error -show_entries format=duration,size -of default=noprint_wrappers=1 \
  "$ROOT/videos/RestockOS-Product-Demo.mp4"
