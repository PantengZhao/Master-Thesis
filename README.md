# YouTube AIGC Sampling & Transcripts

Two lightweight scripts to collect YouTube videos about AI content creation and fetch transcripts for manually curated “core” videos.

## Files
- `youtube_aigc_sampler.py`: Runs a few generic queries in a fixed date window, dedupes, fetches stats (views/likes/comments), and exports `youtube_candidates_basic.csv` for manual screening.
- `fetch_core_transcripts.py`: Reads your curated CSV (with `Core_video` flag), fetches transcripts for `Core_video=1` videos, and writes `youtube_core_transcripts.csv`.
- `youtube_candidates_basic.csv`: Sample output from the sampler (kept here as reference).
- `youtube_core_transcripts.csv`: Sample output after fetching transcripts (kept here as reference).
  - Columns include `transcript` for the videos you marked as `Core_video=1`.
- `youtube_candidates_basic.csv`: Output of the sampler with search results + stats + month bucket (for manual screening).

## Requirements
- Python 3.8+
- Packages: `google-api-python-client`, `pandas`, `tqdm`, `youtube-transcript-api`
- YouTube API key: set env `YOUTUBE_API_KEY` (or edit the script to inject your key)

Install deps (in your virtualenv):
```bash
pip install google-api-python-client pandas tqdm youtube-transcript-api
```

## 1) Collect candidates
The sampler searches 2025-08-01 to 2025-11-22 with three queries:
- `AI tools for content creation`
- `AI tools for content creators`
- `AI workflow for content creation`

Run (ensure `YOUTUBE_API_KEY` is set):
```bash
export YOUTUBE_API_KEY=YOUR_API_KEY
python youtube_aigc_sampler.py
```
Output: `youtube_candidates_basic.csv` with video id, channel, title/description, stats, and `month_bucket`.

## 2) Fetch transcripts for curated videos
1) Export your Numbers sheet as CSV (e.g., `youtube_core.csv`) with columns:
   - `video_id`
   - `Core_video` (set to `1` for rows needing transcripts)
   - other columns are passed through.
2) Run:
```bash
python fetch_core_transcripts.py --input youtube_core.csv --output youtube_core_transcripts.csv
```
Behavior:
- Tries English transcripts (manual or auto). Falls back to generated English if available.
- If subtitles are disabled or no English track exists, transcript stays empty (e.g., a video with only Hindi auto-subtitles).

## Notes
- API key: update `API_KEY` in `youtube_aigc_sampler.py` to your own.
- Search quota: each `search().list` costs 100 quota units; the sampler uses ~300 units per run.
- Transcript access can be blocked by YouTube (IP/region/rate limits). If you see “IP blocked” errors, retry later or from a different network.
