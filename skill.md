# Bilibili All-in-One Skill

A comprehensive Bilibili toolkit that integrates hot trending monitoring, video downloading, video watching/playback, subtitle downloading, and video publishing capabilities into a single unified skill.

## Features

| Module | Description |
|---|---|
| 🔥 **Hot Monitor** | Monitor Bilibili hot/trending videos and topics in real-time |
| ⬇️ **Downloader** | Download Bilibili videos with multiple quality and format options |
| 👀 **Watcher** | Watch and track video engagement metrics (supports Bilibili & YouTube) |
| 📝 **Subtitle** | Download and process subtitles in multiple formats and languages |
| ▶️ **Player** | Get playback URLs, danmaku (bullet comments), and playlist info |
| 📤 **Publisher** | Upload, schedule, edit, and manage videos on Bilibili |

## Installation

### Requirements

- Python >= 3.8
- ffmpeg (optional, for merging video/audio streams)

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Dependencies

- `httpx >= 0.24.0`
- `bilibili-api-python >= 16.0.0`
- `aiohttp >= 3.8.0`
- `beautifulsoup4 >= 4.12.0`
- `lxml >= 4.9.0`
- `requests >= 2.31.0`

## Configuration

Some features (downloading high-quality videos, publishing, etc.) require Bilibili authentication. You can provide credentials in three ways:

### 1. Environment Variables

```bash
export BILIBILI_SESSDATA="your_sessdata"
export BILIBILI_BILI_JCT="your_bili_jct"
export BILIBILI_BUVID3="your_buvid3"
```

### 2. Credential File

Create a JSON file (e.g., `credentials.json`):

```json
{
  "sessdata": "your_sessdata",
  "bili_jct": "your_bili_jct",
  "buvid3": "your_buvid3"
}
```

### 3. Direct Parameters

Pass credentials directly when initializing:

```python
from main import BilibiliAllInOne

app = BilibiliAllInOne(
    sessdata="your_sessdata",
    bili_jct="your_bili_jct",
    buvid3="your_buvid3",
)
```

> **How to get cookies:** Log in to [bilibili.com](https://www.bilibili.com), open browser DevTools (F12) → Application → Cookies, and copy the values of `SESSDATA`, `bili_jct`, and `buvid3`.

## Usage

### CLI

```bash
python main.py <skill_name> <action> [params_json]
```

### Python API

```python
import asyncio
from main import BilibiliAllInOne

app = BilibiliAllInOne()

async def demo():
    result = await app.execute("hot_monitor", "get_hot", limit=5)
    print(result)

asyncio.run(demo())
```

---

## Skills Reference

### 1. 🔥 Hot Monitor (`bilibili_hot_monitor`)

Monitor Bilibili hot/trending videos and topics in real-time. Supports filtering by category, tracking rank changes.

#### Actions

| Action | Description | Parameters |
|---|---|---|
| `get_hot` | Get popular/hot videos | `page`, `page_size` |
| `get_trending` | Get trending series/topics | `limit` |
| `get_weekly` | Get weekly must-watch list | `number` (week number, optional) |
| `get_rank` | Get category ranking videos | `category`, `limit` |

#### Supported Categories

`all`, `anime`, `music`, `dance`, `game`, `tech`, `life`, `food`, `car`, `fashion`, `entertainment`, `movie`, `tv`

#### Examples

```bash
# Get top 10 hot videos
python main.py hot_monitor get_hot '{"page_size": 10}'

# Get trending topics
python main.py hot_monitor get_trending '{"limit": 5}'

# Get this week's must-watch
python main.py hot_monitor get_weekly

# Get game category rankings
python main.py hot_monitor get_rank '{"category": "game", "limit": 10}'
```

```python
# Python API
result = await app.execute("hot_monitor", "get_hot", page_size=10)
result = await app.execute("hot_monitor", "get_rank", category="game", limit=10)
```

---

### 2. ⬇️ Downloader (`bilibili_downloader`)

Download Bilibili videos with support for multiple quality options, batch downloading, and format selection.

#### Actions

| Action | Description | Parameters |
|---|---|---|
| `get_info` | Get video information | `url` |
| `get_formats` | List available qualities/formats | `url` |
| `download` | Download a single video | `url`, `quality`, `output_dir`, `format`, `page` |
| `batch_download` | Download multiple videos | `urls`, `quality`, `output_dir`, `format` |

#### Quality Options

`360p`, `480p`, `720p`, `1080p` (default), `1080p+`, `4k`

#### Format Options

`mp4` (default), `flv`, `mp3` (audio only)

#### Examples

```bash
# Get video info
python main.py downloader get_info '{"url": "BV1xx411c7mD"}'

# List available formats
python main.py downloader get_formats '{"url": "BV1xx411c7mD"}'

# Download in 1080p MP4
python main.py downloader download '{"url": "BV1xx411c7mD", "quality": "1080p", "format": "mp4"}'

# Extract audio only
python main.py downloader download '{"url": "BV1xx411c7mD", "format": "mp3"}'

# Batch download
python main.py downloader batch_download '{"urls": ["BV1xx411c7mD", "BV1yy411c8nE"], "quality": "720p"}'
```

```python
# Python API
info = await app.execute("downloader", "get_info", url="BV1xx411c7mD")
result = await app.execute("downloader", "download", url="BV1xx411c7mD", quality="1080p")
```

---

### 3. 👀 Watcher (`bilibili_watcher`)

Watch and monitor Bilibili (and YouTube) videos. Track view counts, comments, likes, and other engagement metrics over time.

#### Actions

| Action | Description | Parameters |
|---|---|---|
| `watch` | Get detailed video information | `url` |
| `get_stats` | Get current engagement statistics | `url` |
| `track` | Track metrics over time | `url`, `interval` (minutes), `duration` (hours) |
| `compare` | Compare multiple videos | `urls` |

#### Supported Platforms

- **Bilibili**: `https://www.bilibili.com/video/BVxxxxxx` or `BVxxxxxx`
- **YouTube**: `https://www.youtube.com/watch?v=xxxxx` or `https://youtu.be/xxxxx`

#### Examples

```bash
# Get video details
python main.py watcher watch '{"url": "BV1xx411c7mD"}'

# Get current stats
python main.py watcher get_stats '{"url": "BV1xx411c7mD"}'

# Track views every 30 minutes for 12 hours
python main.py watcher track '{"url": "BV1xx411c7mD", "interval": 30, "duration": 12}'

# Compare multiple videos
python main.py watcher compare '{"urls": ["BV1xx411c7mD", "BV1yy411c8nE"]}'
```

```python
# Python API
details = await app.execute("watcher", "watch", url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
comparison = await app.execute("watcher", "compare", urls=["BV1xx411c7mD", "BV1yy411c8nE"])
```

---

### 4. 📝 Subtitle (`bilibili_subtitle`)

Download and process subtitles/CC from Bilibili videos. Supports multiple subtitle formats and languages.

#### Actions

| Action | Description | Parameters |
|---|---|---|
| `list` | List available subtitles | `url` |
| `download` | Download subtitles | `url`, `language`, `format`, `output_dir` |
| `convert` | Convert subtitle format | `input_path`, `output_format`, `output_dir` |
| `merge` | Merge multiple subtitle files | `input_paths`, `output_path`, `output_format` |

#### Supported Formats

`srt` (default), `ass`, `vtt`, `txt`, `json`

#### Supported Languages

`zh-CN` (default), `en`, `ja`, and other language codes available on the video.

#### Examples

```bash
# List available subtitles
python main.py subtitle list '{"url": "BV1xx411c7mD"}'

# Download Chinese subtitles in SRT format
python main.py subtitle download '{"url": "BV1xx411c7mD", "language": "zh-CN", "format": "srt"}'

# Download English subtitles in ASS format
python main.py subtitle download '{"url": "BV1xx411c7mD", "language": "en", "format": "ass"}'

# Convert SRT to VTT
python main.py subtitle convert '{"input_path": "./subtitles/video.srt", "output_format": "vtt"}'

# Merge subtitle files
python main.py subtitle merge '{"input_paths": ["part1.srt", "part2.srt"], "output_path": "merged.srt"}'
```

```python
# Python API
subs = await app.execute("subtitle", "list", url="BV1xx411c7mD")
result = await app.execute("subtitle", "download", url="BV1xx411c7mD", language="zh-CN", format="srt")
```

---

### 5. ▶️ Player (`bilibili_player`)

Play Bilibili videos with support for playback control, playlist management, and danmaku (bullet comments) display.

#### Actions

| Action | Description | Parameters |
|---|---|---|
| `play` | Get complete playback info | `url`, `quality`, `page` |
| `get_playurl` | Get direct play URLs | `url`, `quality`, `page` |
| `get_danmaku` | Get danmaku/bullet comments | `url`, `page`, `segment` |
| `get_playlist` | Get playlist/multi-part info | `url` |

#### Danmaku Modes

| Mode | Description |
|---|---|
| 1 | Scroll (right to left) |
| 4 | Bottom fixed |
| 5 | Top fixed |

#### Examples

```bash
# Get playback info
python main.py player play '{"url": "BV1xx411c7mD", "quality": "1080p"}'

# Get direct play URLs
python main.py player get_playurl '{"url": "BV1xx411c7mD", "quality": "720p"}'

# Get danmaku
python main.py player get_danmaku '{"url": "BV1xx411c7mD"}'

# Get playlist for multi-part video
python main.py player get_playlist '{"url": "BV1xx411c7mD"}'

# Get page 3 of a multi-part video
python main.py player play '{"url": "BV1xx411c7mD", "quality": "1080p", "page": 3}'
```

```python
# Python API
play_info = await app.execute("player", "play", url="BV1xx411c7mD", quality="1080p")
danmaku = await app.execute("player", "get_danmaku", url="BV1xx411c7mD")
playlist = await app.execute("player", "get_playlist", url="BV1xx411c7mD")
```

---

### 6. 📤 Publisher (`bilibili_publisher`)

Publish videos to Bilibili. Supports uploading videos, setting metadata, scheduling publications, and managing drafts.

> ⚠️ **Authentication Required**: All publisher actions require valid Bilibili credentials.

#### Actions

| Action | Description | Parameters |
|---|---|---|
| `upload` | Upload and publish a video | `file_path`, `title`, `description`, `tags`, `category`, `cover_path`, `dynamic`, `no_reprint`, `open_elec` |
| `draft` | Save as draft | `file_path`, `title`, `description`, `tags`, `category`, `cover_path` |
| `schedule` | Schedule future publication | `file_path`, `title`, `schedule_time`, `description`, `tags`, `category`, `cover_path` |
| `edit` | Edit existing video metadata | `bvid`, `title`, `description`, `tags`, `cover_path` |
| `delete` | Delete a video | `bvid` |

#### Upload Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `file_path` | string | *required* | Path to the video file |
| `title` | string | *required* | Video title (max 80 chars) |
| `description` | string | `""` | Video description (max 2000 chars) |
| `tags` | string[] | `["bilibili"]` | Tags (max 12, each max 20 chars) |
| `category` | string | `"171"` | Category TID |
| `cover_path` | string | `null` | Path to cover image (JPG/PNG) |
| `no_reprint` | int | `1` | 1 = original content, 0 = repost |
| `open_elec` | int | `0` | 1 = enable charging, 0 = disable |

#### Examples

```bash
# Upload and publish
python main.py publisher upload '{"file_path": "./video.mp4", "title": "My Video", "description": "Hello World", "tags": ["test", "demo"], "category": "171"}'

# Save as draft
python main.py publisher draft '{"file_path": "./video.mp4", "title": "Draft Video"}'

# Schedule publication
python main.py publisher schedule '{"file_path": "./video.mp4", "title": "Scheduled Video", "schedule_time": "2025-12-31T20:00:00+08:00"}'

# Edit video metadata
python main.py publisher edit '{"bvid": "BV1xx411c7mD", "title": "New Title", "tags": ["updated"]}'

# Delete a video
python main.py publisher delete '{"bvid": "BV1xx411c7mD"}'
```

```python
# Python API (authentication required)
app = BilibiliAllInOne(sessdata="xxx", bili_jct="xxx", buvid3="xxx")

result = await app.execute("publisher", "upload",
    file_path="./video.mp4",
    title="My Video",
    description="Published via bilibili-all-in-one",
    tags=["python", "bilibili"],
)
```

---

## Project Structure

```
bilibili-all-in-one/
├── skill.json              # Skill configuration & parameter schema
├── skill.md                # This documentation file
├── requirements.txt        # Python dependencies
├── main.py                 # Entry point & unified BilibiliAllInOne class
├── src/
│   ├── __init__.py         # Package exports
│   ├── auth.py             # Authentication & credential management
│   ├── utils.py            # Shared utilities, API constants, helpers
│   ├── hot_monitor.py      # Hot/trending video monitoring
│   ├── downloader.py       # Video downloading
│   ├── watcher.py          # Video watching & stats tracking
│   ├── subtitle.py         # Subtitle downloading & processing
│   ├── player.py           # Video playback & danmaku
│   └── publisher.py        # Video uploading & publishing
└── tests/
    └── __init__.py
```

## Skill Origin

This skill integrates the functionality of the following individual skills into one unified toolkit:

| Original Skill | Source | Integrated Module |
|---|---|---|
| bilibili-hot-monitor | [Jacobzwj/bilibili-hot-monitor](https://clawhub.ai/Jacobzwj/bilibili-hot-monitor) | `hot_monitor` |
| bililidownloader | [caiyundc880518/bililidownloader](https://clawhub.ai/caiyundc880518/bililidownloader) | `downloader` |
| bilibili-youtube-watcher | [donnycui/bilibili-youtube-watcher](https://clawhub.ai/donnycui/bilibili-youtube-watcher) | `watcher` |
| bilibili-subtitle-download-skill | [DavinciEvans/bilibili-subtitle-download-skill](https://clawhub.ai/DavinciEvans/bilibili-subtitle-download-skill) | `subtitle` |
| bilibili-player | [e421083458/bilibili-player](https://clawhub.ai/e421083458/bilibili-player) | `player` |
| bilibili-video-publish | [Johnnyxu820/bilibili-video-publish](https://clawhub.ai/Johnnyxu820/bilibili-video-publish) | `publisher` |

## Response Format

All skill actions return a JSON object with a unified structure:

```json
{
  "success": true,
  "...": "action-specific fields"
}
```

On error:

```json
{
  "success": false,
  "message": "Error description"
}
```

## License

MIT
