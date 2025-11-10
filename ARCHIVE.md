# Archive log

These files were moved into `archive/` to declutter the repository root. They are preserved with full contents so nothing is lost. Move performed on user request.

Moved files:

- `generate_youtube_music_links.py` — Experimental generator script for YouTube Music playlist links. Moved to `archive/` because the functionality overlaps with the core `discord_bot` utilities and it's used infrequently.
- `youtube_search_enhanced.py` — Enhanced/experimental YouTube search implementation. Moved to `archive/` for later review before integrating into `discord_bot.py`.
- `implement_youtube_fix.py` — One-off patch script that writes fallback links for problematic artists. Archived for record and re-use if needed.
- `YOUTUBE_SEARCH_FIX.md` — Documentation and instructions related to the YouTube search fix. Moved to `archive/` to keep docs consolidated.
- `generate_env_data.py` — Helper to encode `artists_data.json` into a Render env var. Archived since it's a one-time helper.

If you want any of these restored to the repo root, run:

    git mv archive/<filename> .

Notes:
- Archived files may contain code that references project internals; review and test before re-integrating.
- No permanent deletions were performed; git history still contains original commits.
