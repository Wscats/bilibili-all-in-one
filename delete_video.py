"""Delete a Bilibili video with geetest captcha verification."""

import json
import http.server
import threading
import webbrowser
import httpx

SESSDATA = "your_sessdata_here"
BILI_JCT = "your_bili_jct_here"
BVID = "your_bvid_here"
AID = 0  # your_aid_here

server_should_stop = threading.Event()


def get_captcha_info():
    """Get geetest captcha challenge from Bilibili."""
    resp = httpx.get(
        "https://passport.bilibili.com/x/passport-login/captcha",
        cookies={"SESSDATA": SESSDATA},
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
    )
    data = resp.json()
    if data["code"] != 0:
        raise Exception(f"Failed to get captcha: {data}")
    return data["data"]


def build_html():
    """Build HTML page with geetest captcha widget.

    The captcha is loaded dynamically via /captcha-info API to always get
    a fresh challenge, avoiding the 'old challenge' error on reload.
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
        <p>BVID: <span class="bvid">{BVID}</span></p>
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
            // Clear previous captcha widget
            document.getElementById('captcha-box').innerHTML = '';
            setStatus('正在获取验证码...', 'loading');

            // Always fetch fresh captcha info from server
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
                    var token = captchaInfo.token;

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

                            // Send delete request (captcha is just for user confirmation,
                            // the actual B站 delete API does not require captcha params)
                            fetch("/delete", {{
                                method: "POST",
                                headers: {{ "Content-Type": "application/json" }},
                                body: JSON.stringify({{
                                    confirmed: true
                                }})
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

        // Auto-init on page load
        initCaptcha();
    </script>
</body>
</html>"""


class CaptchaHandler(http.server.BaseHTTPRequestHandler):
    html_content = ""

    def do_GET(self):
        if self.path == "/captcha-info":
            # Provide fresh captcha info via API (always a new challenge)
            try:
                info = get_captcha_info()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-cache, no-store")
                self.end_headers()
                self.wfile.write(json.dumps(info).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(self.html_content.encode())

    def do_POST(self):
        if self.path == "/delete":
            content_length = int(self.headers["Content-Length"])
            body = self.rfile.read(content_length)
            data = json.loads(body)

            if not data.get("confirmed"):
                result = {"success": False, "message": "未确认删除操作"}
            else:
                print("  收到确认，正在调用删除 API...")
                result = delete_video()
                print(f"  删除结果: {json.dumps(result, ensure_ascii=False)}")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode())

            if result.get("success"):
                threading.Timer(2, lambda: server_should_stop.set()).start()

    def log_message(self, format, *args):
        pass


def delete_video():
    """Delete video via Bilibili API.

    The delete API only requires aid + csrf, no captcha params needed.
    This matches the behavior in publisher.py's delete method.
    """
    cookies = {"SESSDATA": SESSDATA, "bili_jct": BILI_JCT}
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Referer": "https://member.bilibili.com/",
        "Origin": "https://member.bilibili.com",
    }

    resp = httpx.post(
        "https://member.bilibili.com/x/web/archive/delete",
        cookies=cookies,
        headers=headers,
        data={
            "aid": AID,
            "csrf": BILI_JCT,
        },
    )

    print(f"  B站 API 响应: {resp.status_code} {resp.text[:300]}")
    try:
        data = resp.json()
    except Exception:
        return {"success": False, "message": f"响应解析失败: {resp.text[:200]}"}

    if data.get("code") == 0:
        return {"success": True, "message": f"视频 {BVID} 已成功删除！"}
    else:
        return {"success": False, "message": f"[{data.get('code')}] {data.get('message', '删除失败')}"}


def main():
    print(f"准备删除视频: BVID={BVID}, AID={AID}")

    CaptchaHandler.html_content = build_html()

    port = 18923
    server = http.server.HTTPServer(("127.0.0.1", port), CaptchaHandler)
    server.timeout = 1

    url = f"http://127.0.0.1:{port}"
    print(f"\n🌐 请在浏览器中完成验证码验证: {url}")
    webbrowser.open(url)

    while not server_should_stop.is_set():
        server.handle_request()

    server.server_close()
    print("\n✅ 操作完成，服务器已关闭。")


if __name__ == "__main__":
    main()
