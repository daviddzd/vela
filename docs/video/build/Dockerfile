# Image for the explainer videos: the bible image (Playwright 1.65.1 + Chromium + Node + Python) plus a full ffmpeg
# (libx264, libass for burnt-in subtitles). Built by scripts/build_video.sh after the bible image.
FROM vela-biblia
USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg \
 && rm -rf /var/lib/apt/lists/*
