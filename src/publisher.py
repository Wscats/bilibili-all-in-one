"""Bilibili video uploading and publishing module."""

import os
import json
import hashlib
import asyncio
import http.server
import threading
import webbrowser
from typing import Optional, Dict, Any, List

import httpx

from .auth import BilibiliAuth
from .utils import DEFAULT_HEADERS, API_BASE, ensure_dir


# Publishing API endpoints
PREUPLOAD_URL = "https://member.bilibili.com/preupload"
UPLOAD_URL = "https://upos-sz-upcdnbda2.bilivideo.com"
MEMBER_API_BASE = "https://member.bilibili.com"
ADD_VIDEO_URL = f"{MEMBER_API_BASE}/x/vu/web/add"
EDIT_VIDEO_URL = f"{MEMBER_API_BASE}/x/vu/web/edit"
DELETE_VIDEO_URL = f"{MEMBER_API_BASE}/x/web/archive/delete"
DRAFT_ADD_URL = f"{MEMBER_API_BASE}/x/vu/web/draft/add"
COVER_UPLOAD_URL = f"{MEMBER_API_BASE}/x/vu/web/cover/up"
CAPTCHA_URL = "https://passport.bilibili.com/x/passport-login/captcha"


def _build_captcha_html(bvid: str, title: str) -> str:
    """Build HTML page with geetest captcha widget for delete confirmation.

    Args:
        bvid: Video BV ID to display.
        title: Video title to display.

    Returns:
        Complete HTML page string.
    """
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>B站视频删除验证</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background: #f4f5f7; }}
        .container {{ background: white; padding: 40px; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.1); text-align: center; max-width: 420px; width: 90%; }}
        h2 {{ color: #333; margin-bottom: 8px; }}
        p {{ color: #666; margin-bottom: 16px; }}
        .bvid {{ color: #00a1d6; font-weight: bold; }}
        .title {{ color: #333; font-size: 14px; }}
        #captcha-box {{ margin: 20px auto; min-height: 50px; }}
        #status {{ margin-top: 16px; padding: 12px; border-radius: 8px; display: none; word-break: break-all; }}
        .success {{ background: #f0fff0; color: #2e8b57; display: block !important; }}
        .error {{ background: #fff0f0; color: #dc3545; display: block !important; }}
        .loading {{ background: #f0f8ff; color: #0066cc; display: block !important; }}
        .info {{ background: #fff8e1; color: #f57c00; display: block !important; }}
        #retry-btn {{ display: none; margin-top: 12px; padding: 10px 24px; background: #00a1d6; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; }}
        #retry-btn:hover {{ background: #00b5e5; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>🗑️ 删除B站视频</h2>
        <p>BVID: <span class="bvid">{bvid}</span></p>
        <p class="title">{title}</p>
        <p>请完成下方验证码以确认删除操作</p>
        <div id="captcha-box"></div>
        <div id="status"></div>
        <button id="retry-btn" onclick="initCaptcha()">🔄 重新加载</button>
    </div>

    <script src="https://static.geetest.com/static/js/gt.0.4.9.js"></script>
    <script>
        var statusEl = document.getElementById('status');
        var retryBtn = document.getElementById('retry-btn');

        function setStatus(msg, cls) {{
            statusEl.textContent = msg;
            statusEl.className = cls;
        }}

        function showRetry() {{
            retryBtn.style.display = 'inline-block';
        }}

        function hideRetry() {{
            retryBtn.style.display = 'none';
        }}

        function initCaptcha() {{
            hideRetry();
            document.getElementById('captcha-box').innerHTML = '';
            setStatus('正在获取验证码...', 'loading');

            fetch('/captcha-info')
                .then(function(r) {{ return r.json(); }})
                .then(function(captchaInfo) {{
                    if (captchaInfo.error) {{
                        setStatus('获取验证码失败: ' + captchaInfo.error, 'error');
                        showRetry();
                        return;
                    }}

                    var gt = captchaInfo.geetest.gt;
                    var challenge = captchaInfo.geetest.challenge;

                    if (typeof initGeetest === 'undefined') {{
                        setStatus('极验 SDK 加载失败，请检查网络连接后重试', 'error');
                        showRetry();
                        return;
                    }}

                    setStatus('正在加载验证码...', 'loading');

                    initGeetest({{
                        gt: gt,
                        challenge: challenge,
                        offline: false,
                        new_captcha: true,
                        product: "popup",
                        width: "300px"
                    }}, function(captchaObj) {{
                        captchaObj.appendTo("#captcha-box");

                        captchaObj.onReady(function() {{
                            setStatus('验证码已加载，请点击按钮完成验证', 'info');
                        }});

                        captchaObj.onSuccess(function() {{
                            var result = captchaObj.getValidate();
                            if (!result) {{
                                setStatus('验证结果为空，请重试', 'error');
                                showRetry();
                                return;
                            }}
                            setStatus('验证通过，正在删除视频...', 'loading');

                            fetch("/delete", {{
                                method: "POST",
                                headers: {{ "Content-Type": "application/json" }},
                                body: JSON.stringify({{ confirmed: true }})
                            }})
                            .then(function(r) {{ return r.json(); }})
                            .then(function(data) {{
                                if (data.success) {{
                                    setStatus("✅ " + data.message, "success");
                                }} else {{
                                    setStatus("❌ " + data.message, "error");
                                    showRetry();
                                }}
                            }})
                            .catch(function(err) {{
                                setStatus("❌ 请求失败: " + err.message, "error");
                                showRetry();
                            }});
                        }});

                        captchaObj.onError(function(e) {{
                            var msg = '验证码加载出错';
                            if (e && e.msg) msg += ': ' + e.msg;
                            if (e && e.desc) msg += ' (' + JSON.stringify(e.desc) + ')';
                            setStatus(msg, 'error');
                            showRetry();
                        }});
                    }});
                }})
                .catch(function(err) {{
                    setStatus('获取验证码信息失败: ' + err.message, 'error');
                    showRetry();
                }});
        }}

        initCaptcha();
    </script>
</body>
</html>"""


class BilibiliPublisher:
    """Publish videos to Bilibili.

    Supports uploading videos, setting metadata, scheduling publications,
    and managing drafts.
    """

    def __init__(self, auth: BilibiliAuth):
        """Initialize BilibiliPublisher.

        Args:
            auth: BilibiliAuth instance (required for publishing).

        Raises:
            ValueError: If auth is not provided or not authenticated.
        """
        if not auth or not auth.is_authenticated:
            raise ValueError("Valid authentication is required for publishing")
        self.auth = auth

    def _get_client(self) -> httpx.AsyncClient:
        """Get an authenticated HTTP client."""
        return self.auth.get_client()

    async def upload(
        self,
        file_path: str,
        title: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        category: str = "171",
        cover_path: Optional[str] = None,
        dynamic: str = "",
        no_reprint: int = 1,
        open_elec: int = 0,
    ) -> Dict[str, Any]:
        """Upload and publish a video to Bilibili.

        Args:
            file_path: Path to the video file.
            title: Video title (max 80 chars).
            description: Video description (max 2000 chars).
            tags: List of tags (max 12 tags, each max 20 chars).
            category: Category TID (default '171' for electronic gaming).
            cover_path: Path to cover image (optional).
            dynamic: Dynamic/feed text.
            no_reprint: 1 = original, 0 = repost.
            open_elec: 1 = enable charging, 0 = disable.

        Returns:
            Upload result with video info.
        """
        if not os.path.exists(file_path):
            return {"success": False, "message": f"File not found: {file_path}"}

        # Validate inputs
        if len(title) > 80:
            return {"success": False, "message": "Title must be 80 characters or less"}

        tags = tags or ["bilibili"]
        if len(tags) > 12:
            tags = tags[:12]

        # Step 1: Pre-upload to get upload params
        preupload_result = await self._preupload(file_path)
        if not preupload_result.get("success"):
            return preupload_result

        # Step 2: Upload video file
        upload_result = await self._upload_file(
            file_path,
            preupload_result,
        )
        if not upload_result.get("success"):
            return upload_result

        # Step 3: Upload cover if provided
        cover_url = ""
        if cover_path and os.path.exists(cover_path):
            cover_result = await self._upload_cover(cover_path)
            if cover_result.get("success"):
                cover_url = cover_result.get("url", "")

        # Step 4: Submit video
        submit_result = await self._submit_video(
            filename=upload_result["filename"],
            title=title,
            desc=description,
            tags=tags,
            tid=int(category),
            cover=cover_url,
            dynamic=dynamic,
            no_reprint=no_reprint,
            open_elec=open_elec,
        )

        return submit_result

    async def draft(
        self,
        file_path: str,
        title: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        category: str = "171",
        cover_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Save a video as draft.

        Args:
            file_path: Path to the video file.
            title: Video title.
            description: Video description.
            tags: List of tags.
            category: Category TID.
            cover_path: Path to cover image.

        Returns:
            Draft save result.
        """
        if not os.path.exists(file_path):
            return {"success": False, "message": f"File not found: {file_path}"}

        tags = tags or ["bilibili"]

        # Upload video file
        preupload_result = await self._preupload(file_path)
        if not preupload_result.get("success"):
            return preupload_result

        upload_result = await self._upload_file(file_path, preupload_result)
        if not upload_result.get("success"):
            return upload_result

        # Upload cover if provided
        cover_url = ""
        if cover_path and os.path.exists(cover_path):
            cover_result = await self._upload_cover(cover_path)
            if cover_result.get("success"):
                cover_url = cover_result.get("url", "")

        # Save as draft (use the same add API with draft=1)
        async with self._get_client() as client:
            resp = await client.post(
                ADD_VIDEO_URL,
                params={"csrf": self.auth.csrf},
                json={
                    "videos": [{
                        "filename": upload_result["filename"],
                        "title": title,
                        "desc": "",
                    }],
                    "title": title,
                    "desc": description,
                    "tag": ",".join(tags),
                    "tid": int(category),
                    "cover": cover_url,
                    "copyright": 1,
                    "no_reprint": 1,
                    "open_elec": 0,
                    "draft": 1,
                    "csrf": self.auth.csrf,
                },
            )
            if resp.status_code != 200:
                return {"success": False, "message": f"HTTP {resp.status_code}: {resp.text[:500]}"}
            try:
                data = resp.json()
            except Exception:
                return {"success": False, "message": f"Invalid JSON response: {resp.text[:500]}"}

        if data.get("code") != 0:
            return {"success": False, "message": data.get("message", "Draft save failed")}

        return {
            "success": True,
            "draft_id": data.get("data", {}).get("aid"),
            "message": "Draft saved successfully",
        }

    async def schedule(
        self,
        file_path: str,
        title: str,
        schedule_time: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        category: str = "171",
        cover_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Schedule a video for future publication.

        Args:
            file_path: Path to the video file.
            title: Video title.
            schedule_time: Scheduled publish time (ISO 8601 format).
            description: Video description.
            tags: List of tags.
            category: Category TID.
            cover_path: Path to cover image.

        Returns:
            Schedule result.
        """
        import datetime

        if not os.path.exists(file_path):
            return {"success": False, "message": f"File not found: {file_path}"}

        # Parse schedule time
        try:
            dt = datetime.datetime.fromisoformat(schedule_time.replace("Z", "+00:00"))
            timestamp = int(dt.timestamp())
        except ValueError:
            return {"success": False, "message": f"Invalid schedule time format: {schedule_time}"}

        tags = tags or ["bilibili"]

        # Upload video file
        preupload_result = await self._preupload(file_path)
        if not preupload_result.get("success"):
            return preupload_result

        upload_result = await self._upload_file(file_path, preupload_result)
        if not upload_result.get("success"):
            return upload_result

        # Upload cover if provided
        cover_url = ""
        if cover_path and os.path.exists(cover_path):
            cover_result = await self._upload_cover(cover_path)
            if cover_result.get("success"):
                cover_url = cover_result.get("url", "")

        # Submit with schedule
        submit_result = await self._submit_video(
            filename=upload_result["filename"],
            title=title,
            desc=description,
            tags=tags,
            tid=int(category),
            cover=cover_url,
            dtime=timestamp,
        )

        if submit_result.get("success"):
            submit_result["scheduled_time"] = schedule_time

        return submit_result

    async def edit(
        self,
        bvid: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        cover_path: Optional[str] = None,
        file_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Edit an existing video's metadata.

        Args:
            bvid: BV number of the video to edit.
            title: New title (if changing).
            description: New description (if changing).
            tags: New tags (if changing).
            cover_path: New cover image path (if changing).
            file_path: Path to video file (required for re-upload).

        Returns:
            Edit result.
        """
        # First get current video info
        async with self._get_client() as client:
            resp = await client.get(
                f"{API_BASE}/x/web-interface/view",
                params={"bvid": bvid},
            )
            data = resp.json()

        if data.get("code") != 0:
            return {"success": False, "message": data.get("message", "Video not found")}

        video = data["data"]

        # Re-upload video file to get a fresh filename
        if file_path and os.path.exists(file_path):
            preupload_result = await self._preupload(file_path)
            if not preupload_result.get("success"):
                return preupload_result
            upload_result = await self._upload_file(file_path, preupload_result)
            if not upload_result.get("success"):
                return upload_result
            new_filename = upload_result["filename"]
        else:
            return {"success": False, "message": "file_path is required for editing (B站 requires re-upload)"}

        # Build edit payload with videos info
        new_title = title or video.get("title")
        videos = [{
            "filename": new_filename,
            "title": new_title,
            "desc": "",
        }]

        edit_data = {
            "aid": video["aid"],
            "videos": videos,
            "title": new_title,
            "desc": description if description is not None else video.get("desc", ""),
            "tag": ",".join(tags) if tags else ",".join(
                t.get("tag_name", "") for t in video.get("tags", []) if t.get("tag_name")
            ),
            "tid": video.get("tid"),
            "copyright": video.get("copyright", 1),
            "csrf": self.auth.csrf,
        }

        # Upload new cover if provided
        if cover_path and os.path.exists(cover_path):
            cover_result = await self._upload_cover(cover_path)
            if cover_result.get("success"):
                edit_data["cover"] = cover_result.get("url", "")

        async with self._get_client() as client:
            resp = await client.post(
                EDIT_VIDEO_URL,
                params={"csrf": self.auth.csrf},
                json=edit_data,
            )
            if resp.status_code != 200:
                return {"success": False, "message": f"HTTP {resp.status_code}: {resp.text[:500]}"}
            try:
                result = resp.json()
            except Exception:
                return {"success": False, "message": f"Invalid JSON response: {resp.text[:500]}"}

        if result.get("code") != 0:
            return {"success": False, "message": result.get("message", "Edit failed")}

        return {
            "success": True,
            "bvid": bvid,
            "message": "Video edited successfully",
        }

    async def delete(self, bvid: str) -> Dict[str, Any]:
        """Delete a video.

        Args:
            bvid: BV number of the video to delete.

        Returns:
            Deletion result.
        """
        # Get AID from BVID
        async with self._get_client() as client:
            resp = await client.get(
                f"{API_BASE}/x/web-interface/view",
                params={"bvid": bvid},
            )
            data = resp.json()

        if data.get("code") != 0:
            return {"success": False, "message": data.get("message", "Video not found")}

        aid = data["data"]["aid"]

        async with self._get_client() as client:
            resp = await client.post(
                DELETE_VIDEO_URL,
                params={"csrf": self.auth.csrf},
                data={
                    "aid": aid,
                    "csrf": self.auth.csrf,
                },
            )
            if resp.status_code != 200:
                return {
                    "success": False,
                    "message": f"HTTP {resp.status_code}: {resp.text[:500]}",
                }
            try:
                result = resp.json()
            except Exception:
                return {
                    "success": False,
                    "message": f"Invalid JSON response: {resp.text[:500]}",
                }

        if result.get("code") != 0:
            return {"success": False, "message": result.get("message", "Delete failed")}

        return {
            "success": True,
            "bvid": bvid,
            "aid": aid,
            "message": "Video deleted successfully",
        }

    async def delete_with_captcha(
        self,
        bvid: str,
        port: int = 18923,
        auto_open: bool = True,
    ) -> Dict[str, Any]:
        """Delete a video with geetest captcha verification via browser.

        Launches a local HTTP server that serves a captcha verification page.
        The user must complete the captcha in their browser to confirm deletion.

        Args:
            bvid: BV number of the video to delete.
            port: Local server port (default 18923).
            auto_open: Whether to automatically open the browser.

        Returns:
            Deletion result dict.
        """
        # Get AID from BVID
        async with self._get_client() as client:
            resp = await client.get(
                f"{API_BASE}/x/web-interface/view",
                params={"bvid": bvid},
            )
            data = resp.json()

        if data.get("code") != 0:
            return {"success": False, "message": data.get("message", "Video not found")}

        aid = data["data"]["aid"]
        title = data["data"].get("title", bvid)

        # Run the captcha server in a thread and wait for result
        result_holder: Dict[str, Any] = {}
        server_done = threading.Event()

        def run_server():
            auth = self.auth
            nonlocal result_holder

            def _get_captcha_info():
                """Fetch fresh geetest captcha challenge."""
                r = httpx.get(
                    CAPTCHA_URL,
                    cookies=auth.cookies,
                    headers={"User-Agent": DEFAULT_HEADERS["User-Agent"]},
                )
                d = r.json()
                if d["code"] != 0:
                    raise Exception(f"Failed to get captcha: {d}")
                return d["data"]

            def _do_delete():
                """Execute the actual delete API call."""
                r = httpx.post(
                    DELETE_VIDEO_URL,
                    cookies=auth.cookies,
                    headers={
                        "User-Agent": DEFAULT_HEADERS["User-Agent"],
                        "Referer": "https://member.bilibili.com/",
                        "Origin": "https://member.bilibili.com",
                    },
                    data={"aid": aid, "csrf": auth.csrf},
                )
                try:
                    d = r.json()
                except Exception:
                    return {"success": False, "message": f"Response parse error: {r.text[:200]}"}
                if d.get("code") == 0:
                    return {"success": True, "bvid": bvid, "aid": aid,
                            "message": f"Video {bvid} deleted successfully"}
                return {"success": False,
                        "message": f"[{d.get('code')}] {d.get('message', 'Delete failed')}"}

            html_content = _build_captcha_html(bvid, title)
            stop_event = threading.Event()

            class Handler(http.server.BaseHTTPRequestHandler):
                def do_GET(self_handler):
                    if self_handler.path == "/captcha-info":
                        try:
                            info = _get_captcha_info()
                            self_handler.send_response(200)
                            self_handler.send_header("Content-Type", "application/json")
                            self_handler.send_header("Cache-Control", "no-cache, no-store")
                            self_handler.end_headers()
                            self_handler.wfile.write(json.dumps(info).encode())
                        except Exception as e:
                            self_handler.send_response(500)
                            self_handler.send_header("Content-Type", "application/json")
                            self_handler.end_headers()
                            self_handler.wfile.write(json.dumps({"error": str(e)}).encode())
                    else:
                        self_handler.send_response(200)
                        self_handler.send_header("Content-Type", "text/html; charset=utf-8")
                        self_handler.end_headers()
                        self_handler.wfile.write(html_content.encode())

                def do_POST(self_handler):
                    if self_handler.path == "/delete":
                        length = int(self_handler.headers["Content-Length"])
                        body = json.loads(self_handler.rfile.read(length))
                        if not body.get("confirmed"):
                            res = {"success": False, "message": "Deletion not confirmed"}
                        else:
                            res = _do_delete()
                        self_handler.send_response(200)
                        self_handler.send_header("Content-Type", "application/json")
                        self_handler.end_headers()
                        self_handler.wfile.write(json.dumps(res, ensure_ascii=False).encode())
                        if res.get("success"):
                            result_holder.update(res)
                            threading.Timer(1, lambda: stop_event.set()).start()

                def log_message(self_handler, fmt, *args):
                    pass

            server = http.server.HTTPServer(("127.0.0.1", port), Handler)
            server.timeout = 1

            if auto_open:
                webbrowser.open(f"http://127.0.0.1:{port}")

            while not stop_event.is_set():
                server.handle_request()

            server.server_close()
            server_done.set()

        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()

        # Wait for the server to finish (user completes captcha or closes)
        await asyncio.get_event_loop().run_in_executor(None, server_done.wait)

        if result_holder:
            return result_holder
        return {"success": False, "message": "Captcha verification was not completed"}

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """Execute a publisher action.

        Args:
            action: Action name ('upload', 'draft', 'schedule', 'edit', 'delete',
                    'delete_with_captcha').
            **kwargs: Additional parameters for the action.

        Returns:
            Action result dict.
        """
        actions = {
            "upload": self.upload,
            "draft": self.draft,
            "schedule": self.schedule,
            "edit": self.edit,
            "delete": self.delete,
            "delete_with_captcha": self.delete_with_captcha,
        }

        handler = actions.get(action)
        if not handler:
            return {"success": False, "message": f"Unknown action: {action}"}

        import inspect
        sig = inspect.signature(handler)
        valid_params = {k: v for k, v in kwargs.items() if k in sig.parameters}

        return await handler(**valid_params)

    async def _preupload(self, file_path: str) -> Dict[str, Any]:
        """Request pre-upload parameters from Bilibili.

        Args:
            file_path: Path to the video file.

        Returns:
            Pre-upload parameters dict.
        """
        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)

        async with self._get_client() as client:
            resp = await client.get(
                PREUPLOAD_URL,
                params={
                    "name": file_name,
                    "size": file_size,
                    "r": "upos",
                    "profile": "ugcupos/bup",
                    "ssl": 0,
                    "version": "2.14.0",
                    "build": 2140000,
                    "upcdn": "bda2",
                    "probe_version": 20221109,
                },
            )
            data = resp.json()

        if "upos_uri" not in data:
            return {"success": False, "message": "Pre-upload failed"}

        return {
            "success": True,
            "upos_uri": data["upos_uri"],
            "auth": data.get("auth"),
            "biz_id": data.get("biz_id"),
            "chunk_size": data.get("chunk_size", 4 * 1024 * 1024),
            "endpoints": data.get("endpoints", []),
            "file_size": file_size,
            "file_name": file_name,
        }

    async def _upload_file(
        self,
        file_path: str,
        preupload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Upload a video file in chunks.

        Args:
            file_path: Path to the video file.
            preupload: Pre-upload parameters from _preupload().

        Returns:
            Upload result with filename.
        """
        upos_uri = preupload["upos_uri"]
        auth = preupload.get("auth")
        biz_id = preupload.get("biz_id")
        chunk_size = preupload.get("chunk_size", 4 * 1024 * 1024)
        file_size = preupload["file_size"]

        # Extract upos key from URI
        upos_key = upos_uri.replace("upos://", "")
        filename = upos_key.split("/")[-1].split(".")[0]

        # Calculate chunk count
        chunk_count = (file_size + chunk_size - 1) // chunk_size

        # Init upload
        upload_base = f"https://upos-sz-upcdnbda2.bilivideo.com/{upos_key}"

        async with self._get_client() as client:
            # Fetch upload ID
            resp = await client.post(
                upload_base,
                params={
                    "uploads": "",
                    "output": "json",
                },
                headers={"X-Upos-Auth": auth} if auth else {},
            )

            try:
                init_data = resp.json()
                upload_id = init_data.get("upload_id", "")
            except Exception:
                return {"success": False, "message": "Failed to initialize upload"}

        # Upload chunks
        with open(file_path, "rb") as f:
            for chunk_idx in range(chunk_count):
                chunk_data = f.read(chunk_size)
                start = chunk_idx * chunk_size
                end = min(start + len(chunk_data), file_size)

                async with self._get_client() as client:
                    resp = await client.put(
                        upload_base,
                        params={
                            "partNumber": chunk_idx + 1,
                            "uploadId": upload_id,
                            "chunk": chunk_idx,
                            "chunks": chunk_count,
                            "size": len(chunk_data),
                            "start": start,
                            "end": end,
                            "total": file_size,
                        },
                        headers={
                            "X-Upos-Auth": auth or "",
                            "Content-Type": "application/octet-stream",
                        },
                        content=chunk_data,
                    )

                    if resp.status_code not in (200, 202):
                        return {
                            "success": False,
                            "message": f"Upload chunk {chunk_idx + 1}/{chunk_count} failed",
                        }

        # Complete upload
        parts = [{"partNumber": i + 1, "eTag": "etag"} for i in range(chunk_count)]

        async with self._get_client() as client:
            resp = await client.post(
                upload_base,
                params={
                    "output": "json",
                    "name": preupload["file_name"],
                    "profile": "ugcupos/bup",
                    "uploadId": upload_id,
                    "biz_id": biz_id or 0,
                },
                json={"parts": parts},
                headers={"X-Upos-Auth": auth or ""},
            )

        return {
            "success": True,
            "filename": filename,
            "upos_uri": upos_uri,
        }

    async def _upload_cover(self, cover_path: str) -> Dict[str, Any]:
        """Upload a cover image.

        Args:
            cover_path: Path to the cover image.

        Returns:
            Upload result with cover URL.
        """
        if not os.path.exists(cover_path):
            return {"success": False, "message": f"Cover file not found: {cover_path}"}

        with open(cover_path, "rb") as f:
            cover_data = f.read()

        # Detect MIME type
        if cover_path.lower().endswith(".png"):
            mime_type = "image/png"
        elif cover_path.lower().endswith((".jpg", ".jpeg")):
            mime_type = "image/jpeg"
        else:
            mime_type = "image/jpeg"

        import base64
        cover_b64 = f"data:{mime_type};base64,{base64.b64encode(cover_data).decode()}"

        async with self._get_client() as client:
            resp = await client.post(
                COVER_UPLOAD_URL,
                data={
                    "cover": cover_b64,
                    "csrf": self.auth.csrf,
                },
            )
            data = resp.json()

        if data.get("code") != 0:
            return {"success": False, "message": data.get("message", "Cover upload failed")}

        return {
            "success": True,
            "url": data.get("data", {}).get("url", ""),
        }

    @staticmethod
    def _get_captcha_info_sync(cookies: Dict[str, str]) -> Dict[str, Any]:
        """Get geetest captcha challenge from Bilibili (synchronous).

        Args:
            cookies: Authentication cookies.

        Returns:
            Captcha challenge data.

        Raises:
            Exception: If captcha request fails.
        """
        resp = httpx.get(
            CAPTCHA_URL,
            cookies=cookies,
            headers={"User-Agent": DEFAULT_HEADERS["User-Agent"]},
        )
        data = resp.json()
        if data["code"] != 0:
            raise Exception(f"Failed to get captcha: {data}")
        return data["data"]

    async def _submit_video(
        self,
        filename: str,
        title: str,
        desc: str = "",
        tags: Optional[List[str]] = None,
        tid: int = 171,
        cover: str = "",
        dynamic: str = "",
        no_reprint: int = 1,
        open_elec: int = 0,
        dtime: int = 0,
    ) -> Dict[str, Any]:
        """Submit a video for publishing.

        Args:
            filename: Uploaded video filename.
            title: Video title.
            desc: Description.
            tags: Tags list.
            tid: Category TID.
            cover: Cover image URL.
            dynamic: Dynamic text.
            no_reprint: Original flag.
            open_elec: Charging flag.
            dtime: Scheduled publish timestamp (0 = immediate).

        Returns:
            Submit result.
        """
        tags = tags or ["bilibili"]

        payload = {
            "videos": [{
                "filename": filename,
                "title": title,
                "desc": "",
            }],
            "title": title,
            "desc": desc,
            "tag": ",".join(tags),
            "tid": tid,
            "cover": cover,
            "dynamic": dynamic,
            "copyright": 1 if no_reprint else 2,
            "no_reprint": no_reprint,
            "open_elec": open_elec,
            "csrf": self.auth.csrf,
        }

        if dtime > 0:
            payload["dtime"] = dtime

        async with self._get_client() as client:
            params = {"csrf": self.auth.csrf}
            resp = await client.post(
                ADD_VIDEO_URL,
                params=params,
                json=payload,
            )
            if resp.status_code != 200:
                return {
                    "success": False,
                    "message": f"HTTP {resp.status_code}: {resp.text[:500]}",
                }
            try:
                data = resp.json()
            except Exception:
                return {
                    "success": False,
                    "message": f"Invalid JSON response: {resp.text[:500]}",
                }

        if data.get("code") != 0:
            return {"success": False, "message": data.get("message", "Submit failed")}

        result_data = data.get("data", {})
        return {
            "success": True,
            "aid": result_data.get("aid"),
            "bvid": result_data.get("bvid"),
            "message": "Video published successfully",
        }
