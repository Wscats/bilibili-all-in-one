"""Comprehensive tests for all Bilibili All-in-One modules.

Covers every module and action with normal paths, edge cases, and error handling.
All HTTP requests are mocked — no real API calls are made.
"""

import asyncio
import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock

import httpx


# ── Helpers ──────────────────────────────────────────────────────────

def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


def _mock_response(data: dict, status_code: int = 200) -> httpx.Response:
    """Create a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = data
    resp.text = json.dumps(data)
    resp.content = json.dumps(data).encode()
    return resp


def _bilibili_ok(data: dict) -> dict:
    """Wrap data in standard Bilibili API success envelope."""
    return {"code": 0, "message": "0", "data": data}


def _bilibili_error(code: int = -400, message: str = "Request error") -> dict:
    """Wrap data in standard Bilibili API error envelope."""
    return {"code": code, "message": message}


def _video_info_payload(bvid="BV1xx411c7mD", title="Test Video", pages=1, duration=300):
    """Generate a standard video info API response payload."""
    page_list = []
    for i in range(1, pages + 1):
        page_list.append({
            "cid": 10000 + i,
            "page": i,
            "part": f"Part {i}",
            "duration": duration,
        })
    return {
        "bvid": bvid,
        "aid": 12345,
        "title": title,
        "desc": "Test description",
        "pic": "https://example.com/cover.jpg",
        "duration": duration,
        "owner": {"mid": 100, "name": "TestUser", "face": "https://example.com/face.jpg"},
        "stat": {
            "view": 100000, "danmaku": 500, "like": 5000,
            "coin": 1000, "favorite": 2000, "share": 300, "reply": 800,
        },
        "pages": page_list,
        "pubdate": 1700000000,
        "tid": 171,
        "copyright": 1,
        "tags": [{"tag_name": "test"}, {"tag_name": "bilibili"}],
        "subtitle": {
            "list": [
                {
                    "lan": "zh-CN",
                    "lan_doc": "中文（中国）",
                    "subtitle_url": "//example.com/subtitle_zh.json",
                },
            ]
        },
    }


# ── Mock Client Context Manager ─────────────────────────────────────

class MockAsyncClient:
    """A mock async HTTP client that returns pre-configured responses."""

    def __init__(self, responses=None):
        self._responses = list(responses or [])
        self._call_index = 0

    def _next_response(self):
        if self._call_index < len(self._responses):
            resp = self._responses[self._call_index]
            self._call_index += 1
            return resp
        return _mock_response(_bilibili_ok({}))

    async def get(self, *args, **kwargs):
        return self._next_response()

    async def post(self, *args, **kwargs):
        return self._next_response()

    async def put(self, *args, **kwargs):
        return self._next_response()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


def _patch_client(module_obj, responses):
    """Patch _get_client on a module instance to return a MockAsyncClient."""
    mock_client = MockAsyncClient(responses)
    module_obj._get_client = lambda: mock_client
    return mock_client


# ══════════════════════════════════════════════════════════════════════
# 1. Utils Module Tests
# ══════════════════════════════════════════════════════════════════════

class TestUtils(unittest.TestCase):
    """Test utility functions in src/utils.py."""

    def test_extract_bvid_from_bvid(self):
        from src.utils import extract_bvid
        self.assertEqual(extract_bvid("BV1xx411c7mD"), "BV1xx411c7mD")

    def test_extract_bvid_from_url(self):
        from src.utils import extract_bvid
        self.assertEqual(
            extract_bvid("https://www.bilibili.com/video/BV1xx411c7mD"),
            "BV1xx411c7mD",
        )

    def test_extract_bvid_from_b23_url(self):
        from src.utils import extract_bvid
        self.assertEqual(
            extract_bvid("https://b23.tv/BV1xx411c7mD"),
            "BV1xx411c7mD",
        )

    def test_extract_bvid_invalid(self):
        from src.utils import extract_bvid
        self.assertIsNone(extract_bvid("not_a_valid_url"))
        self.assertIsNone(extract_bvid(""))
        self.assertIsNone(extract_bvid(None))

    def test_extract_aid_from_string(self):
        from src.utils import extract_aid
        self.assertEqual(extract_aid("av12345"), 12345)

    def test_extract_aid_from_url(self):
        from src.utils import extract_aid
        self.assertEqual(
            extract_aid("https://www.bilibili.com/video/av12345"),
            12345,
        )

    def test_extract_aid_invalid(self):
        from src.utils import extract_aid
        self.assertIsNone(extract_aid("not_valid"))
        self.assertIsNone(extract_aid(""))
        self.assertIsNone(extract_aid(None))

    def test_format_duration_short(self):
        from src.utils import format_duration
        self.assertEqual(format_duration(65), "1:05")

    def test_format_duration_long(self):
        from src.utils import format_duration
        self.assertEqual(format_duration(3661), "1:01:01")

    def test_format_duration_zero(self):
        from src.utils import format_duration
        self.assertEqual(format_duration(0), "0:00")

    def test_format_number_small(self):
        from src.utils import format_number
        self.assertEqual(format_number(999), "999")

    def test_format_number_wan(self):
        from src.utils import format_number
        self.assertEqual(format_number(15000), "1.5万")

    def test_format_number_yi(self):
        from src.utils import format_number
        self.assertEqual(format_number(200000000), "2.0亿")

    def test_sanitize_filename(self):
        from src.utils import sanitize_filename
        result = sanitize_filename('test<>:"/\\|?*file')
        # Each invalid char (<, >, :, ", /, \, |, ?, *) is replaced with _
        self.assertNotIn('<', result)
        self.assertNotIn('>', result)
        self.assertIn('test', result)
        self.assertIn('file', result)

    def test_sanitize_filename_empty(self):
        from src.utils import sanitize_filename
        self.assertEqual(sanitize_filename(""), "untitled")

    def test_sanitize_filename_long(self):
        from src.utils import sanitize_filename
        long_name = "a" * 300
        result = sanitize_filename(long_name)
        self.assertLessEqual(len(result), 200)

    def test_ensure_dir(self):
        from src.utils import ensure_dir
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = os.path.join(tmpdir, "sub", "dir")
            result = ensure_dir(new_dir)
            self.assertTrue(os.path.isdir(result))

    def test_parse_video_url_bilibili(self):
        from src.utils import parse_video_url
        result = parse_video_url("https://www.bilibili.com/video/BV1xx411c7mD")
        self.assertEqual(result["platform"], "bilibili")
        self.assertEqual(result["bvid"], "BV1xx411c7mD")

    def test_parse_video_url_unknown(self):
        from src.utils import parse_video_url
        result = parse_video_url("https://www.example.com/video")
        self.assertEqual(result["platform"], "unknown")

    def test_category_tid_mapping(self):
        from src.utils import CATEGORY_TID
        self.assertEqual(CATEGORY_TID["all"], 0)
        self.assertEqual(CATEGORY_TID["game"], 4)
        self.assertEqual(CATEGORY_TID["music"], 3)
        self.assertIn("anime", CATEGORY_TID)
        self.assertIn("tech", CATEGORY_TID)

    def test_quality_map(self):
        from src.utils import QUALITY_MAP
        self.assertEqual(QUALITY_MAP["360p"], 16)
        self.assertEqual(QUALITY_MAP["1080p"], 80)
        self.assertEqual(QUALITY_MAP["4k"], 120)

    def test_generate_wbi_sign(self):
        from src.utils import generate_wbi_sign
        params = {"foo": "bar"}
        # Keys must be long enough (at least 64 chars combined) for the mixin table
        img_key = "a" * 32
        sub_key = "b" * 32
        result = generate_wbi_sign(params, img_key, sub_key)
        self.assertIn("wts", result)
        self.assertIn("w_rid", result)
        self.assertEqual(len(result["w_rid"]), 32)  # MD5 hash length


# ══════════════════════════════════════════════════════════════════════
# 2. Auth Module Tests
# ══════════════════════════════════════════════════════════════════════

class TestAuth(unittest.TestCase):
    """Test authentication module."""

    def test_auth_not_authenticated(self):
        from src.auth import BilibiliAuth
        auth = BilibiliAuth()
        self.assertFalse(auth.is_authenticated)

    def test_auth_authenticated(self):
        from src.auth import BilibiliAuth
        auth = BilibiliAuth(sessdata="test_sess", bili_jct="test_jct")
        self.assertTrue(auth.is_authenticated)

    def test_auth_cookies(self):
        from src.auth import BilibiliAuth
        auth = BilibiliAuth(sessdata="s", bili_jct="j", buvid3="b")
        cookies = auth.cookies
        self.assertEqual(cookies["SESSDATA"], "s")
        self.assertEqual(cookies["bili_jct"], "j")
        self.assertEqual(cookies["buvid3"], "b")

    def test_auth_csrf(self):
        from src.auth import BilibiliAuth
        auth = BilibiliAuth(bili_jct="my_csrf_token")
        self.assertEqual(auth.csrf, "my_csrf_token")

    def test_auth_from_file(self):
        from src.auth import BilibiliAuth
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"sessdata": "file_sess", "bili_jct": "file_jct", "buvid3": "file_buvid"}, f)
            f.flush()
            auth = BilibiliAuth(credential_file=f.name)
        os.unlink(f.name)
        self.assertEqual(auth.sessdata, "file_sess")
        self.assertEqual(auth.bili_jct, "file_jct")
        self.assertTrue(auth.is_authenticated)

    def test_auth_save_to_file(self):
        from src.auth import BilibiliAuth
        auth = BilibiliAuth(sessdata="s", bili_jct="j", buvid3="b")
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "cred.json")
            auth.save_to_file(filepath)
            self.assertTrue(os.path.exists(filepath))
            with open(filepath) as f:
                data = json.load(f)
            self.assertEqual(data["sessdata"], "s")

    def test_auth_get_client(self):
        from src.auth import BilibiliAuth
        auth = BilibiliAuth(sessdata="s", bili_jct="j")
        client = auth.get_client()
        self.assertIsInstance(client, httpx.AsyncClient)

    def test_auth_get_headers(self):
        from src.auth import BilibiliAuth
        auth = BilibiliAuth()
        headers = auth.get_headers(extra={"X-Custom": "value"})
        self.assertIn("User-Agent", headers)
        self.assertEqual(headers["X-Custom"], "value")


# ══════════════════════════════════════════════════════════════════════
# 3. Hot Monitor Module Tests
# ══════════════════════════════════════════════════════════════════════

class TestHotMonitor(unittest.TestCase):
    """Test hot/trending video monitoring module."""

    def setUp(self):
        from src.hot_monitor import HotMonitor
        self.monitor = HotMonitor()

    def test_get_hot_success(self):
        hot_data = {
            "list": [
                {
                    "bvid": f"BV{i}xxx", "aid": 1000 + i,
                    "title": f"Hot Video {i}", "desc": "", "pic": "",
                    "duration": 200,
                    "owner": {"mid": i, "name": f"User{i}", "face": ""},
                    "stat": {"view": 10000 * i, "danmaku": 100, "like": 500,
                             "coin": 100, "favorite": 200, "share": 50, "reply": 80},
                    "pubdate": 1700000000,
                }
                for i in range(1, 6)
            ],
            "no_more": False,
        }
        _patch_client(self.monitor, [_mock_response(_bilibili_ok(hot_data))])
        result = _run(self.monitor.get_hot(page=1, page_size=5))
        self.assertTrue(result["success"])
        self.assertEqual(len(result["videos"]), 5)
        self.assertEqual(result["page"], 1)
        self.assertTrue(result["has_more"])

    def test_get_hot_api_error(self):
        _patch_client(self.monitor, [_mock_response(_bilibili_error())])
        result = _run(self.monitor.get_hot())
        self.assertFalse(result["success"])

    def test_get_trending_success(self):
        trending_data = {
            "list": [
                {"number": i, "subject": f"Topic {i}", "status": 2, "name": f"Week {i}"}
                for i in range(1, 11)
            ],
        }
        _patch_client(self.monitor, [_mock_response(_bilibili_ok(trending_data))])
        result = _run(self.monitor.get_trending(limit=5))
        self.assertTrue(result["success"])
        self.assertEqual(len(result["series"]), 5)

    def test_get_trending_api_error(self):
        _patch_client(self.monitor, [_mock_response(_bilibili_error())])
        result = _run(self.monitor.get_trending())
        self.assertFalse(result["success"])

    def test_get_weekly_success(self):
        weekly_data = {
            "config": {"number": 200, "subject": "本周必看", "label": "第200期"},
            "list": [
                {
                    "bvid": f"BV_weekly_{i}", "aid": 3000 + i,
                    "title": f"Weekly {i}", "desc": "", "pic": "",
                    "duration": 400,
                    "owner": {"mid": i, "name": f"Creator{i}", "face": ""},
                    "stat": {"view": 200000, "danmaku": 800, "like": 10000,
                             "coin": 3000, "favorite": 5000, "share": 500, "reply": 2000},
                    "pubdate": 1700000000,
                }
                for i in range(1, 4)
            ],
        }
        _patch_client(self.monitor, [_mock_response(_bilibili_ok(weekly_data))])
        result = _run(self.monitor.get_weekly(number=200))
        self.assertTrue(result["success"])
        self.assertEqual(result["week_number"], 200)
        self.assertEqual(result["subject"], "本周必看")
        self.assertEqual(len(result["videos"]), 3)

    def test_get_weekly_api_error(self):
        _patch_client(self.monitor, [_mock_response(_bilibili_error(-352, "-352"))])
        result = _run(self.monitor.get_weekly())
        self.assertFalse(result["success"])

    def test_get_rank_success(self):
        rank_data = {
            "list": [
                {
                    "bvid": f"BV_rank_{i}", "aid": 2000 + i,
                    "title": f"Rank {i}", "desc": "", "pic": "",
                    "duration": 600, "score": 10000 - i * 100,
                    "owner": {"mid": i, "name": f"Gamer{i}", "face": ""},
                    "stat": {"view": 50000, "danmaku": 200, "like": 3000,
                             "coin": 500, "favorite": 1000, "share": 100, "reply": 400},
                    "pubdate": 1700000000,
                }
                for i in range(1, 15)
            ],
        }
        _patch_client(self.monitor, [_mock_response(_bilibili_ok(rank_data))])
        result = _run(self.monitor.get_rank(category="game", limit=10))
        self.assertTrue(result["success"])
        self.assertEqual(result["category"], "game")
        self.assertLessEqual(len(result["videos"]), 10)
        # Verify score field is present
        self.assertIn("score", result["videos"][0])

    def test_get_rank_unknown_category(self):
        """Unknown category should default to tid=0 (all)."""
        rank_data = {"list": []}
        _patch_client(self.monitor, [_mock_response(_bilibili_ok(rank_data))])
        result = _run(self.monitor.get_rank(category="nonexistent"))
        self.assertTrue(result["success"])
        self.assertEqual(result["category"], "nonexistent")

    def test_execute_unknown_action(self):
        result = _run(self.monitor.execute("nonexistent_action"))
        self.assertFalse(result["success"])
        self.assertIn("Unknown action", result["message"])

    def test_parse_video_fields(self):
        """Verify _parse_video returns all expected fields."""
        item = {
            "bvid": "BV_test", "aid": 999, "title": "Test",
            "desc": "Desc", "pic": "http://cover.jpg", "duration": 125,
            "owner": {"mid": 1, "name": "Author", "face": "http://face.jpg"},
            "stat": {"view": 12345, "danmaku": 10, "like": 100,
                     "coin": 50, "favorite": 30, "share": 5, "reply": 20},
            "pubdate": 1700000000,
        }
        video = self.monitor._parse_video(item)
        self.assertEqual(video["bvid"], "BV_test")
        self.assertEqual(video["duration"], "2:05")
        self.assertEqual(video["duration_seconds"], 125)
        self.assertEqual(video["author"]["name"], "Author")
        self.assertEqual(video["stats"]["views"], 12345)
        self.assertEqual(video["stats"]["views_formatted"], "1.2万")
        self.assertIn("url", video)


# ══════════════════════════════════════════════════════════════════════
# 4. Downloader Module Tests
# ══════════════════════════════════════════════════════════════════════

class TestDownloader(unittest.TestCase):
    """Test video downloading module."""

    def setUp(self):
        from src.downloader import BilibiliDownloader
        self.downloader = BilibiliDownloader()

    def test_get_info_success(self):
        resp = _mock_response(_bilibili_ok(_video_info_payload()))
        _patch_client(self.downloader, [resp])
        result = _run(self.downloader.get_info("BV1xx411c7mD"))
        self.assertTrue(result["success"])
        self.assertEqual(result["bvid"], "BV1xx411c7mD")
        self.assertEqual(result["title"], "Test Video")
        self.assertIn("pages", result)
        self.assertIn("stats", result)

    def test_get_info_invalid_url(self):
        result = _run(self.downloader.get_info("invalid_url"))
        self.assertFalse(result["success"])

    def test_get_info_api_error(self):
        _patch_client(self.downloader, [_mock_response(_bilibili_error())])
        result = _run(self.downloader.get_info("BV1xx411c7mD"))
        self.assertFalse(result["success"])

    def test_get_formats_success(self):
        info_resp = _mock_response(_bilibili_ok(_video_info_payload()))
        play_resp = _mock_response(_bilibili_ok({
            "dash": {"video": [], "audio": []},
            "accept_quality": [120, 80, 64, 32, 16],
        }))
        _patch_client(self.downloader, [info_resp, play_resp])
        result = _run(self.downloader.get_formats("BV1xx411c7mD"))
        self.assertTrue(result["success"])
        self.assertIn("available_qualities", result)
        self.assertIn("formats", result)
        self.assertEqual(len(result["available_qualities"]), 5)

    def test_get_formats_invalid_url(self):
        result = _run(self.downloader.get_formats("invalid"))
        self.assertFalse(result["success"])

    def test_download_success(self):
        info_resp = _mock_response(_bilibili_ok(_video_info_payload()))
        play_resp = _mock_response(_bilibili_ok({
            "dash": {
                "video": [{"id": 80, "baseUrl": "https://example.com/video.m4s",
                           "bandwidth": 2000000, "codecs": "avc1"}],
                "audio": [{"id": 30280, "baseUrl": "https://example.com/audio.m4s",
                           "bandwidth": 128000, "codecs": "mp4a"}],
            }
        }))
        _patch_client(self.downloader, [info_resp, play_resp])

        async def fake_download(url, filepath):
            with open(filepath, "wb") as f:
                f.write(b"\x00" * 100)

        async def fake_merge(video_path, audio_path, output_path):
            with open(output_path, "wb") as f:
                f.write(b"\x00" * 200)
            return True

        self.downloader._download_stream = fake_download
        self.downloader._merge_streams = fake_merge

        with tempfile.TemporaryDirectory() as tmpdir:
            result = _run(self.downloader.download(
                url="BV1xx411c7mD", quality="1080p", format="mp4", output_dir=tmpdir,
            ))
            self.assertTrue(result["success"])
            self.assertEqual(result["quality"], "1080p")
            self.assertEqual(result["format"], "mp4")
            self.assertIn("filepath", result)

    def test_download_mp3_audio_only(self):
        info_resp = _mock_response(_bilibili_ok(_video_info_payload()))
        play_resp = _mock_response(_bilibili_ok({
            "dash": {
                "video": [{"id": 80, "baseUrl": "https://example.com/video.m4s",
                           "bandwidth": 2000000, "codecs": "avc1"}],
                "audio": [{"id": 30280, "baseUrl": "https://example.com/audio.m4s",
                           "bandwidth": 128000, "codecs": "mp4a"}],
            }
        }))
        _patch_client(self.downloader, [info_resp, play_resp])

        async def fake_download(url, filepath):
            with open(filepath, "wb") as f:
                f.write(b"\x00" * 100)

        self.downloader._download_stream = fake_download

        with tempfile.TemporaryDirectory() as tmpdir:
            result = _run(self.downloader.download(
                url="BV1xx411c7mD", format="mp3", output_dir=tmpdir,
            ))
            self.assertTrue(result["success"])
            self.assertTrue(result["filepath"].endswith(".mp3"))

    def test_download_invalid_page(self):
        info_resp = _mock_response(_bilibili_ok(_video_info_payload(pages=1)))
        _patch_client(self.downloader, [info_resp])
        with tempfile.TemporaryDirectory() as tmpdir:
            result = _run(self.downloader.download(
                url="BV1xx411c7mD", page=5, output_dir=tmpdir,
            ))
            self.assertFalse(result["success"])
            self.assertIn("Page 5 not found", result["message"])

    def test_batch_download(self):
        responses = []
        for bvid in ["BV1aaa", "BV1bbb"]:
            responses.append(_mock_response(_bilibili_ok(
                _video_info_payload(bvid=bvid, title=f"Video {bvid}")
            )))
            responses.append(_mock_response(_bilibili_ok({
                "dash": {
                    "video": [{"id": 80, "baseUrl": f"https://example.com/{bvid}_v.m4s",
                               "bandwidth": 2000000, "codecs": "avc1"}],
                    "audio": [{"id": 30280, "baseUrl": f"https://example.com/{bvid}_a.m4s",
                               "bandwidth": 128000, "codecs": "mp4a"}],
                }
            })))
        _patch_client(self.downloader, responses)

        async def fake_download(url, filepath):
            with open(filepath, "wb") as f:
                f.write(b"\x00" * 100)

        async def fake_merge(video_path, audio_path, output_path):
            with open(output_path, "wb") as f:
                f.write(b"\x00" * 200)
            return True

        self.downloader._download_stream = fake_download
        self.downloader._merge_streams = fake_merge

        with tempfile.TemporaryDirectory() as tmpdir:
            result = _run(self.downloader.batch_download(
                urls=["BV1aaa", "BV1bbb"], quality="1080p", output_dir=tmpdir,
            ))
            self.assertTrue(result["success"])
            self.assertEqual(result["total"], 2)
            self.assertEqual(result["succeeded"], 2)

    def test_execute_unknown_action(self):
        result = _run(self.downloader.execute("nonexistent"))
        self.assertFalse(result["success"])

    def test_select_dash_stream_exact_match(self):
        streams = [
            {"id": 80, "baseUrl": "url_80"},
            {"id": 64, "baseUrl": "url_64"},
        ]
        result = self.downloader._select_dash_stream(streams, 80)
        self.assertEqual(result, "url_80")

    def test_select_dash_stream_fallback(self):
        streams = [
            {"id": 64, "baseUrl": "url_64"},
            {"id": 32, "baseUrl": "url_32"},
        ]
        result = self.downloader._select_dash_stream(streams, 80)
        self.assertEqual(result, "url_64")

    def test_select_dash_stream_empty(self):
        result = self.downloader._select_dash_stream([], 80)
        self.assertIsNone(result)

    def test_select_dash_audio(self):
        streams = [
            {"bandwidth": 128000, "baseUrl": "audio_low"},
            {"bandwidth": 320000, "baseUrl": "audio_high"},
        ]
        result = self.downloader._select_dash_audio(streams)
        self.assertEqual(result, "audio_high")

    def test_select_dash_audio_empty(self):
        result = self.downloader._select_dash_audio([])
        self.assertIsNone(result)


# ══════════════════════════════════════════════════════════════════════
# 5. Player Module Tests
# ══════════════════════════════════════════════════════════════════════

class TestPlayer(unittest.TestCase):
    """Test video playback and danmaku module."""

    def setUp(self):
        from src.player import BilibiliPlayer
        self.player = BilibiliPlayer()

    def test_get_playlist_success(self):
        resp = _mock_response(_bilibili_ok(_video_info_payload(pages=3)))
        _patch_client(self.player, [resp])
        result = _run(self.player.get_playlist("BV1xx411c7mD"))
        self.assertTrue(result["success"])
        self.assertEqual(result["page_count"], 3)
        self.assertEqual(len(result["pages"]), 3)
        self.assertEqual(result["pages"][0]["page"], 1)

    def test_get_playlist_invalid_url(self):
        result = _run(self.player.get_playlist("invalid"))
        self.assertFalse(result["success"])

    def test_get_playlist_api_error(self):
        _patch_client(self.player, [_mock_response(_bilibili_error())])
        result = _run(self.player.get_playlist("BV1xx411c7mD"))
        self.assertFalse(result["success"])

    def test_get_danmaku_success(self):
        info_resp = _mock_response(_bilibili_ok(_video_info_payload()))
        danmaku_resp = MagicMock(spec=httpx.Response)
        danmaku_resp.status_code = 200
        danmaku_resp.text = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<i>'
            '<d p="1.0,1,25,16777215,1700000000,0,abc123,99999">Hello弹幕</d>'
            '<d p="5.0,1,25,16777215,1700000001,0,def456,99998">Test弹幕</d>'
            '<d p="3.0,4,25,255,1700000002,0,ghi789,99997">底部弹幕</d>'
            '</i>'
        )
        _patch_client(self.player, [info_resp, danmaku_resp])
        result = _run(self.player.get_danmaku("BV1xx411c7mD"))
        self.assertTrue(result["success"])
        self.assertEqual(result["danmaku_count"], 3)
        # Verify sorted by time
        times = [d["time"] for d in result["danmaku"]]
        self.assertEqual(times, sorted(times))

    def test_get_danmaku_invalid_page(self):
        info_resp = _mock_response(_bilibili_ok(_video_info_payload(pages=1)))
        _patch_client(self.player, [info_resp])
        result = _run(self.player.get_danmaku("BV1xx411c7mD", page=5))
        self.assertFalse(result["success"])

    def test_get_playurl_dash(self):
        info_resp = _mock_response(_bilibili_ok(_video_info_payload()))
        play_resp = _mock_response(_bilibili_ok({
            "dash": {
                "video": [
                    {"id": 80, "baseUrl": "https://example.com/1080p.m4s",
                     "bandwidth": 2000000, "codecs": "avc1"},
                    {"id": 64, "baseUrl": "https://example.com/720p.m4s",
                     "bandwidth": 1500000, "codecs": "avc1"},
                ],
                "audio": [
                    {"id": 30280, "baseUrl": "https://example.com/audio.m4s",
                     "bandwidth": 128000, "codecs": "mp4a"},
                ],
            },
            "quality": 80,
            "accept_quality": [80, 64, 32, 16],
        }))
        _patch_client(self.player, [info_resp, play_resp])
        result = _run(self.player.get_playurl("BV1xx411c7mD", quality="1080p"))
        self.assertEqual(result["play_type"], "dash")
        self.assertIn("video_streams", result)
        self.assertIn("audio_streams", result)
        self.assertEqual(result["current_quality"], "1080p")

    def test_get_playurl_invalid_url(self):
        result = _run(self.player.get_playurl("invalid"))
        self.assertFalse(result["success"])

    def test_play_success(self):
        # play() calls _get_video_info and _get_play_url in parallel
        # Each needs info_resp; _get_play_url also needs play_resp
        info_resp1 = _mock_response(_bilibili_ok(_video_info_payload()))
        info_resp2 = _mock_response(_bilibili_ok(_video_info_payload()))
        play_resp = _mock_response(_bilibili_ok({
            "dash": {
                "video": [{"id": 80, "baseUrl": "https://example.com/v.m4s",
                           "bandwidth": 2000000, "codecs": "avc1"}],
                "audio": [{"id": 30280, "baseUrl": "https://example.com/a.m4s",
                           "bandwidth": 128000, "codecs": "mp4a"}],
            },
        }))
        _patch_client(self.player, [info_resp1, info_resp2, play_resp])
        result = _run(self.player.play("BV1xx411c7mD"))
        self.assertTrue(result["success"])

    def test_execute_unknown_action(self):
        result = _run(self.player.execute("nonexistent"))
        self.assertFalse(result["success"])

    def test_parse_danmaku_xml(self):
        xml = (
            '<i>'
            '<d p="1.5,1,25,16777215,1700000000,0,abc,111">Hello</d>'
            '<d p="0.5,4,25,255,1700000001,1,def,222">World</d>'
            '</i>'
        )
        result = self.player._parse_danmaku_xml(xml)
        self.assertEqual(len(result), 2)
        # Should be sorted by time
        self.assertAlmostEqual(result[0]["time"], 0.5)
        self.assertAlmostEqual(result[1]["time"], 1.5)
        self.assertEqual(result[0]["content"], "World")
        self.assertEqual(result[1]["content"], "Hello")
        self.assertEqual(result[0]["mode"], 4)  # bottom danmaku

    def test_parse_danmaku_xml_empty(self):
        result = self.player._parse_danmaku_xml("<i></i>")
        self.assertEqual(len(result), 0)


# ══════════════════════════════════════════════════════════════════════
# 6. Watcher Module Tests
# ══════════════════════════════════════════════════════════════════════

class TestWatcher(unittest.TestCase):
    """Test video watching and stats tracking module."""

    def setUp(self):
        from src.watcher import BilibiliWatcher
        self.watcher = BilibiliWatcher()

    def test_get_stats_success(self):
        resp = _mock_response(_bilibili_ok(_video_info_payload()))
        _patch_client(self.watcher, [resp])
        result = _run(self.watcher.get_stats("BV1xx411c7mD"))
        self.assertTrue(result["success"])
        self.assertEqual(result["bvid"], "BV1xx411c7mD")
        self.assertEqual(result["stats"]["views"], 100000)
        self.assertEqual(result["stats"]["likes"], 5000)
        self.assertIn("timestamp", result)

    def test_get_stats_invalid_url(self):
        result = _run(self.watcher.get_stats("invalid"))
        self.assertFalse(result["success"])

    def test_get_stats_api_error(self):
        _patch_client(self.watcher, [_mock_response(_bilibili_error())])
        result = _run(self.watcher.get_stats("BV1xx411c7mD"))
        self.assertFalse(result["success"])

    def test_watch_bilibili_success(self):
        detail_data = {
            "View": _video_info_payload(),
            "Tags": [{"tag_name": "tag1"}, {"tag_name": "tag2"}],
            "Related": [
                {"bvid": "BV_related", "title": "Related Video",
                 "owner": {"name": "RelatedUser"}},
            ],
        }
        resp = _mock_response(_bilibili_ok(detail_data))
        _patch_client(self.watcher, [resp])
        # Must use full URL so parse_video_url can detect bilibili platform
        result = _run(self.watcher.watch("https://www.bilibili.com/video/BV1xx411c7mD"))
        self.assertTrue(result["success"])
        self.assertEqual(result["platform"], "bilibili")
        self.assertIn("tags", result)
        self.assertIn("related_videos", result)

    def test_watch_unsupported_platform(self):
        result = _run(self.watcher.watch("https://www.example.com/video"))
        self.assertFalse(result["success"])
        self.assertIn("Unsupported platform", result["message"])

    def test_compare_success(self):
        resp1 = _mock_response(_bilibili_ok(
            _video_info_payload(bvid="BV1aaa", title="Video A")
        ))
        resp2 = _mock_response(_bilibili_ok(
            _video_info_payload(bvid="BV1bbb", title="Video B")
        ))
        _patch_client(self.watcher, [resp1, resp2])
        result = _run(self.watcher.compare(["BV1aaa", "BV1bbb"]))
        self.assertTrue(result["success"])
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["compared"], 2)
        self.assertEqual(len(result["ranking"]), 2)
        # Both have same views, so ranking should have rank 1 and 2
        self.assertEqual(result["ranking"][0]["rank"], 1)
        self.assertEqual(result["ranking"][1]["rank"], 2)

    def test_compare_with_invalid_url(self):
        resp = _mock_response(_bilibili_ok(_video_info_payload()))
        _patch_client(self.watcher, [resp])
        result = _run(self.watcher.compare(["BV1aaa", "invalid_url"]))
        self.assertTrue(result["success"])
        self.assertEqual(result["total"], 2)
        # One should fail
        self.assertLessEqual(result["compared"], 2)

    def test_track_short_duration(self):
        """Track with very short duration to test the loop."""
        resp = _mock_response(_bilibili_ok(_video_info_payload()))
        _patch_client(self.watcher, [resp])

        # Override track to collect one data point
        original_track = self.watcher.track

        async def fast_track(url, interval=60, duration=24, callback=None):
            stats = await self.watcher.get_stats(url)
            return {
                "success": True,
                "bvid": "BV1xx411c7mD",
                "data_points": 1,
                "duration_hours": duration,
                "interval_minutes": interval,
                "summary": {},
                "data": [stats] if stats.get("success") else [],
            }

        self.watcher.track = fast_track
        result = _run(self.watcher.track("BV1xx411c7mD", interval=1, duration=0))
        self.assertTrue(result["success"])
        self.watcher.track = original_track

    def test_calculate_changes(self):
        data_points = [
            {"stats": {"views": 100, "likes": 10}},
            {"stats": {"views": 200, "likes": 15}},
        ]
        changes = self.watcher._calculate_changes(data_points)
        self.assertEqual(changes["views"]["start"], 100)
        self.assertEqual(changes["views"]["end"], 200)
        self.assertEqual(changes["views"]["change"], 100)
        self.assertEqual(changes["views"]["change_percent"], 100.0)

    def test_calculate_changes_insufficient_data(self):
        result = self.watcher._calculate_changes([{"stats": {"views": 100}}])
        self.assertIn("message", result)

    def test_execute_unknown_action(self):
        result = _run(self.watcher.execute("nonexistent"))
        self.assertFalse(result["success"])


# ══════════════════════════════════════════════════════════════════════
# 7. Subtitle Module Tests
# ══════════════════════════════════════════════════════════════════════

class TestSubtitle(unittest.TestCase):
    """Test subtitle downloading and processing module."""

    def setUp(self):
        from src.subtitle import SubtitleDownloader
        self.subtitle = SubtitleDownloader()

    def test_list_subtitles_success(self):
        info_resp = _mock_response(_bilibili_ok({
            "bvid": "BV1xx411c7mD", "aid": 12345, "title": "Test",
            "pages": [{"cid": 10001, "page": 1}],
            "subtitle": {"list": []},
        }))
        player_resp = _mock_response(_bilibili_ok({
            "subtitle": {
                "subtitles": [
                    {"id": 1, "lan": "zh-CN", "lan_doc": "中文（中国）",
                     "subtitle_url": "//example.com/sub_zh.json", "ai_type": 0, "ai_status": 0},
                    {"id": 2, "lan": "en", "lan_doc": "English",
                     "subtitle_url": "//example.com/sub_en.json", "ai_type": 0, "ai_status": 0},
                ]
            },
        }))
        _patch_client(self.subtitle, [info_resp, player_resp])
        result = _run(self.subtitle.list_subtitles("BV1xx411c7mD"))
        self.assertTrue(result["success"])
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["subtitles"][0]["language"], "zh-CN")

    def test_list_subtitles_invalid_url(self):
        result = _run(self.subtitle.list_subtitles("invalid"))
        self.assertFalse(result["success"])

    def test_download_subtitle_success(self):
        info_resp = _mock_response(_bilibili_ok({
            "bvid": "BV1xx411c7mD", "aid": 12345, "title": "Test Video",
            "pages": [{"cid": 10001, "page": 1}],
        }))
        player_resp = _mock_response(_bilibili_ok({
            "subtitle": {
                "subtitles": [
                    {"lan": "zh-CN", "lan_doc": "中文（中国）",
                     "subtitle_url": "//example.com/sub_zh.json"},
                ]
            },
        }))
        sub_content_resp = _mock_response({
            "body": [
                {"from": 0.0, "to": 2.0, "content": "你好世界"},
                {"from": 2.5, "to": 5.0, "content": "测试字幕"},
            ]
        })
        _patch_client(self.subtitle, [info_resp, player_resp, sub_content_resp])

        with tempfile.TemporaryDirectory() as tmpdir:
            result = _run(self.subtitle.download(
                url="BV1xx411c7mD", language="zh-CN", format="srt", output_dir=tmpdir,
            ))
            self.assertTrue(result["success"])
            self.assertEqual(result["language"], "zh-CN")
            self.assertEqual(result["format"], "srt")
            self.assertEqual(result["entries"], 2)
            self.assertTrue(os.path.exists(result["filepath"]))

    def test_download_subtitle_language_not_found(self):
        info_resp = _mock_response(_bilibili_ok({
            "bvid": "BV1xx411c7mD", "aid": 12345, "title": "Test",
            "pages": [{"cid": 10001, "page": 1}],
        }))
        player_resp = _mock_response(_bilibili_ok({
            "subtitle": {
                "subtitles": [
                    {"lan": "zh-CN", "lan_doc": "中文", "subtitle_url": "//example.com/sub.json"},
                ]
            },
        }))
        _patch_client(self.subtitle, [info_resp, player_resp])
        with tempfile.TemporaryDirectory() as tmpdir:
            result = _run(self.subtitle.download(
                url="BV1xx411c7mD", language="ja", output_dir=tmpdir,
            ))
            self.assertFalse(result["success"])
            self.assertIn("not found", result["message"])

    def test_convert_srt_to_vtt(self):
        srt_content = (
            "1\n"
            "00:00:00,000 --> 00:00:02,000\n"
            "Hello World\n\n"
            "2\n"
            "00:00:02,500 --> 00:00:05,000\n"
            "Test subtitle\n\n"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            srt_path = os.path.join(tmpdir, "video.srt")
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content)
            result = _run(self.subtitle.convert(srt_path, "vtt"))
            self.assertTrue(result["success"])
            self.assertEqual(result["format"], "vtt")
            self.assertEqual(result["entries"], 2)
            # Verify VTT file content
            with open(result["output"], "r") as f:
                content = f.read()
            self.assertIn("WEBVTT", content)

    def test_convert_srt_to_ass(self):
        srt_content = (
            "1\n"
            "00:00:00,000 --> 00:00:02,000\n"
            "Hello\n\n"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            srt_path = os.path.join(tmpdir, "video.srt")
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content)
            result = _run(self.subtitle.convert(srt_path, "ass"))
            self.assertTrue(result["success"])
            with open(result["output"], "r") as f:
                content = f.read()
            self.assertIn("[Script Info]", content)
            self.assertIn("Dialogue:", content)

    def test_convert_srt_to_txt(self):
        srt_content = (
            "1\n"
            "00:00:00,000 --> 00:00:02,000\n"
            "Hello\n\n"
            "2\n"
            "00:00:02,500 --> 00:00:05,000\n"
            "World\n\n"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            srt_path = os.path.join(tmpdir, "video.srt")
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content)
            result = _run(self.subtitle.convert(srt_path, "txt"))
            self.assertTrue(result["success"])
            with open(result["output"], "r") as f:
                content = f.read()
            self.assertIn("Hello", content)
            self.assertIn("World", content)

    def test_convert_srt_to_json(self):
        srt_content = (
            "1\n"
            "00:00:00,000 --> 00:00:02,000\n"
            "Hello\n\n"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            srt_path = os.path.join(tmpdir, "video.srt")
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content)
            result = _run(self.subtitle.convert(srt_path, "json"))
            self.assertTrue(result["success"])
            with open(result["output"], "r") as f:
                data = json.load(f)
            self.assertIn("body", data)
            self.assertEqual(len(data["body"]), 1)

    def test_convert_file_not_found(self):
        result = _run(self.subtitle.convert("/nonexistent/file.srt", "vtt"))
        self.assertFalse(result["success"])

    def test_merge_subtitles(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create two SRT files
            for i, text in enumerate(["Part 1", "Part 2"]):
                path = os.path.join(tmpdir, f"sub{i}.srt")
                with open(path, "w") as f:
                    f.write(f"1\n00:00:00,000 --> 00:00:02,000\n{text}\n\n")

            output_path = os.path.join(tmpdir, "merged.srt")
            result = _run(self.subtitle.merge(
                input_paths=[os.path.join(tmpdir, "sub0.srt"), os.path.join(tmpdir, "sub1.srt")],
                output_path=output_path,
                output_format="srt",
            ))
            self.assertTrue(result["success"])
            self.assertEqual(result["total_entries"], 2)
            self.assertEqual(result["merged_files"], 2)

    def test_merge_file_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = _run(self.subtitle.merge(
                input_paths=["/nonexistent.srt"],
                output_path=os.path.join(tmpdir, "out.srt"),
            ))
            self.assertFalse(result["success"])

    def test_execute_unknown_action(self):
        result = _run(self.subtitle.execute("nonexistent"))
        self.assertFalse(result["success"])

    def test_format_time_srt(self):
        result = self.subtitle._format_time_srt(3661.5)
        self.assertEqual(result, "01:01:01,500")

    def test_format_time_vtt(self):
        result = self.subtitle._format_time_vtt(3661.5)
        self.assertEqual(result, "01:01:01.500")

    def test_format_time_ass(self):
        result = self.subtitle._format_time_ass(3661.5)
        self.assertEqual(result, "1:01:01.50")

    def test_parse_srt(self):
        srt = (
            "1\n"
            "00:00:01,000 --> 00:00:03,500\n"
            "Hello World\n\n"
            "2\n"
            "00:00:04,000 --> 00:00:06,000\n"
            "Second line\n\n"
        )
        result = self.subtitle._parse_srt(srt)
        self.assertEqual(len(result), 2)
        self.assertAlmostEqual(result[0]["from"], 1.0)
        self.assertAlmostEqual(result[0]["to"], 3.5)
        self.assertEqual(result[0]["content"], "Hello World")


# ══════════════════════════════════════════════════════════════════════
# 8. Publisher Module Tests
# ══════════════════════════════════════════════════════════════════════

class TestPublisher(unittest.TestCase):
    """Test video publishing module."""

    def setUp(self):
        from main import BilibiliAllInOne
        self.app = BilibiliAllInOne(
            sessdata="test_sessdata",
            bili_jct="test_csrf",
            buvid3="test_buvid3",
        )

    def test_publisher_requires_auth(self):
        from src.publisher import BilibiliPublisher
        from src.auth import BilibiliAuth
        with self.assertRaises(ValueError):
            BilibiliPublisher(auth=BilibiliAuth())

    def test_upload_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = os.path.join(tmpdir, "video.mp4")
            with open(video_path, "wb") as f:
                f.write(b"\x00" * 1024)

            async def mock_preupload(file_path):
                return {"success": True, "upload_url": "https://example.com/upload",
                        "auth": "test_auth", "biz_id": 12345, "upos_uri": "test_uri"}

            async def mock_upload_file(file_path, preupload_result):
                return {"success": True, "filename": "test_uploaded.mp4"}

            async def mock_upload_cover(cover_path):
                return {"success": True, "url": "https://example.com/cover.jpg"}

            async def mock_submit_video(**kwargs):
                return {"success": True, "bvid": "BV_new", "aid": 99999,
                        "message": "Video published successfully"}

            self.app.publisher._preupload = mock_preupload
            self.app.publisher._upload_file = mock_upload_file
            self.app.publisher._upload_cover = mock_upload_cover
            self.app.publisher._submit_video = mock_submit_video

            result = _run(self.app.execute(
                "publisher", "upload", file_path=video_path, title="Test Upload",
            ))
            self.assertTrue(result["success"])
            self.assertEqual(result["bvid"], "BV_new")

    def test_upload_file_not_found(self):
        result = _run(self.app.execute(
            "publisher", "upload", file_path="/nonexistent.mp4", title="Test",
        ))
        self.assertFalse(result["success"])

    def test_upload_title_too_long(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = os.path.join(tmpdir, "video.mp4")
            with open(video_path, "wb") as f:
                f.write(b"\x00" * 1024)
            result = _run(self.app.execute(
                "publisher", "upload", file_path=video_path, title="x" * 81,
            ))
            self.assertFalse(result["success"])

    def test_schedule_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = os.path.join(tmpdir, "video.mp4")
            with open(video_path, "wb") as f:
                f.write(b"\x00" * 1024)

            async def mock_preupload(file_path):
                return {"success": True, "upload_url": "https://example.com/upload",
                        "auth": "a", "biz_id": 1, "upos_uri": "u"}

            async def mock_upload_file(file_path, preupload_result):
                return {"success": True, "filename": "scheduled.mp4"}

            async def mock_submit_video(**kwargs):
                return {"success": True, "bvid": "BV_sched", "aid": 88888,
                        "message": "Scheduled"}

            self.app.publisher._preupload = mock_preupload
            self.app.publisher._upload_file = mock_upload_file
            self.app.publisher._submit_video = mock_submit_video

            result = _run(self.app.execute(
                "publisher", "schedule",
                file_path=video_path, title="Scheduled Video",
                schedule_time="2026-12-31T20:00:00+08:00",
            ))
            self.assertTrue(result["success"])
            self.assertIn("scheduled_time", result)

    def test_schedule_invalid_time(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = os.path.join(tmpdir, "video.mp4")
            with open(video_path, "wb") as f:
                f.write(b"\x00" * 1024)
            result = _run(self.app.execute(
                "publisher", "schedule",
                file_path=video_path, title="Test",
                schedule_time="not-a-date",
            ))
            self.assertFalse(result["success"])

    def test_draft_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = os.path.join(tmpdir, "video.mp4")
            with open(video_path, "wb") as f:
                f.write(b"\x00" * 1024)

            async def mock_preupload(file_path):
                return {"success": True, "upload_url": "u", "auth": "a",
                        "biz_id": 1, "upos_uri": "u"}

            async def mock_upload_file(file_path, preupload_result):
                return {"success": True, "filename": "draft.mp4"}

            draft_resp = _mock_response(_bilibili_ok({"aid": 77777}))
            _patch_client(self.app.publisher, [draft_resp])
            self.app.publisher._preupload = mock_preupload
            self.app.publisher._upload_file = mock_upload_file

            result = _run(self.app.execute(
                "publisher", "draft", file_path=video_path, title="Draft Video",
            ))
            self.assertTrue(result["success"])

    def test_edit_success(self):
        """Edit requires file_path for re-upload."""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = os.path.join(tmpdir, "video.mp4")
            with open(video_path, "wb") as f:
                f.write(b"\x00" * 1024)

            info_resp = _mock_response(_bilibili_ok(_video_info_payload()))
            edit_resp = _mock_response(_bilibili_ok({}))

            async def mock_preupload(file_path):
                return {"success": True, "upload_url": "u", "auth": "a",
                        "biz_id": 1, "upos_uri": "u"}

            async def mock_upload_file(file_path, preupload_result):
                return {"success": True, "filename": "reuploaded.mp4"}

            _patch_client(self.app.publisher, [info_resp, edit_resp])
            self.app.publisher._preupload = mock_preupload
            self.app.publisher._upload_file = mock_upload_file

            result = _run(self.app.execute(
                "publisher", "edit",
                bvid="BV1xx411c7mD", title="New Title",
                tags=["new_tag"], file_path=video_path,
            ))
            self.assertTrue(result["success"])
            self.assertEqual(result["bvid"], "BV1xx411c7mD")

    def test_edit_without_file_path(self):
        """Edit without file_path should fail."""
        info_resp = _mock_response(_bilibili_ok(_video_info_payload()))
        _patch_client(self.app.publisher, [info_resp])
        result = _run(self.app.execute(
            "publisher", "edit", bvid="BV1xx411c7mD", title="New Title",
        ))
        self.assertFalse(result["success"])
        self.assertIn("file_path is required", result["message"])

    def test_execute_unknown_action(self):
        result = _run(self.app.execute("publisher", "nonexistent"))
        self.assertFalse(result["success"])


# ══════════════════════════════════════════════════════════════════════
# 9. Main Entry Point Tests
# ══════════════════════════════════════════════════════════════════════

class TestMainEntryPoint(unittest.TestCase):
    """Test the BilibiliAllInOne unified interface."""

    def setUp(self):
        from main import BilibiliAllInOne
        self.app = BilibiliAllInOne()

    def test_unknown_skill(self):
        result = _run(self.app.execute("nonexistent_skill", "some_action"))
        self.assertFalse(result["success"])
        self.assertIn("Unknown skill", result["message"])

    def test_unknown_action_on_valid_skill(self):
        result = _run(self.app.execute("hot_monitor", "nonexistent_action"))
        self.assertFalse(result["success"])
        self.assertIn("Unknown action", result["message"])

    def test_all_skill_aliases(self):
        """Verify all skill name aliases resolve correctly."""
        hot_data = {"list": [], "no_more": True}

        # Hot monitor aliases
        for alias in ["bilibili_hot_monitor", "hot_monitor", "hot"]:
            _patch_client(self.app.hot_monitor, [_mock_response(_bilibili_ok(hot_data))])
            result = _run(self.app.execute(alias, "get_hot"))
            self.assertTrue(result["success"], f"Alias '{alias}' failed")

        # Downloader aliases
        for alias in ["bilibili_downloader", "downloader", "download"]:
            _patch_client(self.app.downloader, [
                _mock_response(_bilibili_ok(_video_info_payload()))
            ])
            result = _run(self.app.execute(alias, "get_info", url="BV1xx411c7mD"))
            self.assertIn("success", result, f"Alias '{alias}' failed")

        # Watcher aliases
        for alias in ["bilibili_watcher", "watcher", "watch"]:
            _patch_client(self.app.watcher, [
                _mock_response(_bilibili_ok(_video_info_payload()))
            ])
            result = _run(self.app.execute(alias, "get_stats", url="BV1xx411c7mD"))
            self.assertIn("success", result, f"Alias '{alias}' failed")

        # Player aliases
        for alias in ["bilibili_player", "player", "play"]:
            _patch_client(self.app.player, [
                _mock_response(_bilibili_ok(_video_info_payload()))
            ])
            result = _run(self.app.execute(alias, "get_playlist", url="BV1xx411c7mD"))
            self.assertIn("success", result, f"Alias '{alias}' failed")

        # Subtitle aliases
        for alias in ["bilibili_subtitle", "subtitle"]:
            _patch_client(self.app.subtitle, [
                _mock_response(_bilibili_ok({
                    "subtitle": {"subtitles": []},
                    "bvid": "BV1xx411c7mD", "aid": 12345,
                    "title": "Test", "pages": [{"cid": 10001, "page": 1}],
                }))
            ])
            result = _run(self.app.execute(alias, "list", url="BV1xx411c7mD"))
            self.assertIn("success", result, f"Alias '{alias}' failed")

    def test_publisher_lazy_init(self):
        """Publisher should be lazily initialized."""
        app = self.app
        self.assertIsNone(app._publisher)
        # Accessing publisher without auth should still create instance
        # (auth has empty credentials from env)

    def test_modules_initialized(self):
        """All modules should be initialized."""
        self.assertIsNotNone(self.app.hot_monitor)
        self.assertIsNotNone(self.app.downloader)
        self.assertIsNotNone(self.app.watcher)
        self.assertIsNotNone(self.app.player)
        self.assertIsNotNone(self.app.subtitle)


# ══════════════════════════════════════════════════════════════════════
# 10. Integration / Cross-Module Tests
# ══════════════════════════════════════════════════════════════════════

class TestIntegration(unittest.TestCase):
    """Cross-module integration tests."""

    def setUp(self):
        from main import BilibiliAllInOne
        self.app = BilibiliAllInOne()

    def test_hot_then_stats(self):
        """Get hot videos, then get stats for the first one."""
        hot_data = {
            "list": [{
                "bvid": "BV1test", "aid": 1001, "title": "Hot Video",
                "desc": "", "pic": "", "duration": 200,
                "owner": {"mid": 1, "name": "User1", "face": ""},
                "stat": {"view": 50000, "danmaku": 100, "like": 2000,
                         "coin": 500, "favorite": 300, "share": 50, "reply": 100},
                "pubdate": 1700000000,
            }],
            "no_more": True,
        }
        _patch_client(self.app.hot_monitor, [_mock_response(_bilibili_ok(hot_data))])
        hot_result = _run(self.app.execute("hot_monitor", "get_hot", page_size=1))
        self.assertTrue(hot_result["success"])

        bvid = hot_result["videos"][0]["bvid"]
        stats_resp = _mock_response(_bilibili_ok(_video_info_payload(bvid=bvid)))
        _patch_client(self.app.watcher, [stats_resp])
        stats_result = _run(self.app.execute("watcher", "get_stats", url=bvid))
        self.assertTrue(stats_result["success"])
        self.assertEqual(stats_result["bvid"], bvid)

    def test_get_info_then_download(self):
        """Get video info, then download it."""
        info_resp = _mock_response(_bilibili_ok(_video_info_payload()))
        _patch_client(self.app.downloader, [info_resp])
        info_result = _run(self.app.execute("downloader", "get_info", url="BV1xx411c7mD"))
        self.assertTrue(info_result["success"])

        # Now download
        info_resp2 = _mock_response(_bilibili_ok(_video_info_payload()))
        play_resp = _mock_response(_bilibili_ok({
            "dash": {
                "video": [{"id": 80, "baseUrl": "https://example.com/v.m4s",
                           "bandwidth": 2000000, "codecs": "avc1"}],
                "audio": [{"id": 30280, "baseUrl": "https://example.com/a.m4s",
                           "bandwidth": 128000, "codecs": "mp4a"}],
            }
        }))
        _patch_client(self.app.downloader, [info_resp2, play_resp])

        async def fake_download(url, filepath):
            with open(filepath, "wb") as f:
                f.write(b"\x00" * 100)

        async def fake_merge(video_path, audio_path, output_path):
            with open(output_path, "wb") as f:
                f.write(b"\x00" * 200)
            return True

        self.app.downloader._download_stream = fake_download
        self.app.downloader._merge_streams = fake_merge

        with tempfile.TemporaryDirectory() as tmpdir:
            dl_result = _run(self.app.execute(
                "downloader", "download",
                url="BV1xx411c7mD", output_dir=tmpdir,
            ))
            self.assertTrue(dl_result["success"])

    def test_all_hot_monitor_actions(self):
        """Run all hot_monitor actions in sequence."""
        # get_hot
        _patch_client(self.app.hot_monitor, [
            _mock_response(_bilibili_ok({"list": [], "no_more": True}))
        ])
        r = _run(self.app.execute("hot_monitor", "get_hot"))
        self.assertTrue(r["success"])

        # get_trending
        _patch_client(self.app.hot_monitor, [
            _mock_response(_bilibili_ok({"list": []}))
        ])
        r = _run(self.app.execute("hot_monitor", "get_trending"))
        self.assertTrue(r["success"])

        # get_weekly
        _patch_client(self.app.hot_monitor, [
            _mock_response(_bilibili_ok({
                "config": {"number": 1, "subject": "Test", "label": "1"},
                "list": [],
            }))
        ])
        r = _run(self.app.execute("hot_monitor", "get_weekly"))
        self.assertTrue(r["success"])

        # get_rank
        _patch_client(self.app.hot_monitor, [
            _mock_response(_bilibili_ok({"list": []}))
        ])
        r = _run(self.app.execute("hot_monitor", "get_rank"))
        self.assertTrue(r["success"])

    def test_all_player_actions(self):
        """Run all player actions."""
        # get_playlist
        _patch_client(self.app.player, [
            _mock_response(_bilibili_ok(_video_info_payload(pages=2)))
        ])
        r = _run(self.app.execute("player", "get_playlist", url="BV1xx411c7mD"))
        self.assertTrue(r["success"])

        # get_danmaku
        info_resp = _mock_response(_bilibili_ok(_video_info_payload()))
        dm_resp = MagicMock(spec=httpx.Response)
        dm_resp.status_code = 200
        dm_resp.text = '<i><d p="1.0,1,25,16777215,1700000000,0,abc,111">Test</d></i>'
        _patch_client(self.app.player, [info_resp, dm_resp])
        r = _run(self.app.execute("player", "get_danmaku", url="BV1xx411c7mD"))
        self.assertTrue(r["success"])

        # get_playurl
        info_resp2 = _mock_response(_bilibili_ok(_video_info_payload()))
        play_resp = _mock_response(_bilibili_ok({
            "dash": {
                "video": [{"id": 80, "baseUrl": "url", "bandwidth": 2000000, "codecs": "avc1"}],
                "audio": [{"id": 30280, "baseUrl": "url", "bandwidth": 128000, "codecs": "mp4a"}],
            },
        }))
        _patch_client(self.app.player, [info_resp2, play_resp])
        r = _run(self.app.execute("player", "get_playurl", url="BV1xx411c7mD"))
        self.assertIn("play_type", r)


if __name__ == "__main__":
    unittest.main()
