#!/usr/bin/env python3
"""Bible-Master Admin & Operations Backend Server
零外部依賴（純 Python 3 標準庫），提供專案管理儀表板與 REST API：
  - 專案總覽與四福音統計（3,776 節）
  - 地端 AI 模型節點健康檢查 (E500, A16, De1050, Harness)
  - 自動化測試觸發 (check_all.py, visual_checks.py, verify_text.py)
  - 測試報告、派工進度與任務追蹤
"""
import argparse
import hmac
import http.server
import json
import os
import re
import secrets
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request

HERE = os.path.abspath(os.path.dirname(__file__))
# 站台根目錄（內含 data/ 與 site/）；可用環境變數覆蓋，測試會指到暫存目錄
SITE_ROOT = os.path.abspath(os.environ.get("BIBLE_SITE_ROOT") or os.path.join(HERE, ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
# 後台寫入權杖檔；每次啟動重新產生，可用環境變數覆蓋
TOKEN_FILE = os.path.abspath(os.environ.get("BIBLE_ADMIN_TOKEN_FILE") or os.path.join(HERE, ".token"))

BOOKS = [
    ("mat", "馬太福音", 28, 1071),
    ("mrk", "馬可福音", 16, 678),
    ("luk", "路加福音", 24, 1149),
    ("jhn", "約翰福音", 21, 878),
]

MODEL_NODES = [
    {
        "id": "e500",
        "name": "E500 (主編 · Bonsai 2 27B 160K)",
        "host": "127.0.0.1",
        "port": 8082,
        "url": "http://127.0.0.1:8082/health",
        "alt_url": "http://127.0.0.1:8082/v1/models",
        "hint": "~/project/Bonsai-demo/start_e500_pq2_160k.sh"
    },
    {
        "id": "a16",
        "name": "TUF A16 Tunnel (審核 · Bonsai 2 9B 128K)",
        "host": "127.0.0.1",
        "port": 18083,
        "url": "http://127.0.0.1:18083/health",
        "alt_url": "http://127.0.0.1:18083/v1/models",
        "hint": "systemctl --user start bonsai-a16-tunnel"
    },
    {
        "id": "de1050",
        "name": "De1050 Tunnel (測試 · Qwen 3.5 4B 48K)",
        "host": "127.0.0.1",
        "port": 18087,
        "url": "http://127.0.0.1:18087/api/tags",
        "alt_url": "http://127.0.0.1:18087/v1/models",
        "hint": "systemctl --user start bonsai-de1050-tunnel"
    },
    {
        "id": "harness",
        "name": "Harness Web 控制台",
        "host": "127.0.0.1",
        "port": 3080,
        "url": "http://127.0.0.1:3080/",
        "alt_url": None,
        "hint": "npx @deepseek-ai/dsh web --no-open"
    }
]

REPORT_WHITELIST = ["TEST-REPORT.md", "FAILS.md", "DISPATCH-REPORT.md", "PROGRESS.md", "CHANGELOG.md"]
ACTION_LOCK = threading.Lock()

# ---- 主頁設定（寫入端點）----
BOOK_KEYS = ("mat", "mrk", "luk", "jhn")
HOME_FIELDS = ("book", "ch", "v", "image", "alt", "music")
HOME_DEFAULTS = {
    "book": "luk",
    "ch": 4,
    "v": 27,
    "image": "assets/jordan.jpg",
    "alt": "一位男子站在約但河水中，仰望從雲層灑下的光",
    "music": "assets/home-music.mp3",
}
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp")
MUSIC_EXTS = (".mp3",)
ASSET_RE = re.compile(r"^assets/[A-Za-z0-9._-]+$")
HOME_MAX_BODY = 65536
UPLOAD_MAX = {"image": 5 * 1024 * 1024, "music": 8 * 1024 * 1024}
LOCAL_HOSTNAMES = ("127.0.0.1", "localhost", "::1")
# 允許呼叫 /api/token 與寫入端點的額外主機名（逗號分隔）
ALLOWED_HOSTS = tuple(
    h.strip().lower()
    for h in (os.environ.get("BIBLE_ADMIN_ALLOWED_HOSTS") or "").split(",")
    if h.strip()
)

ADMIN_TOKEN = ""  # 啟動時由 init_token() 產生


def init_token():
    """產生本次啟動的寫入權杖，並以 600 權限寫入權杖檔（每次啟動重新產生）。"""
    global ADMIN_TOKEN
    ADMIN_TOKEN = secrets.token_urlsafe(32)
    fd = os.open(TOKEN_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, ADMIN_TOKEN.encode("utf-8"))
    finally:
        os.close(fd)
    try:
        os.chmod(TOKEN_FILE, 0o600)
    except OSError:
        pass
    return ADMIN_TOKEN


def home_config_path():
    return os.path.join(SITE_ROOT, "data", "home.json")


def load_home_config():
    """讀 home.json；不存在或壞掉時回預設值（深拷貝，避免污染常數）。"""
    cfg = dict(HOME_DEFAULTS)
    try:
        with open(home_config_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            for k in HOME_FIELDS:
                if k in data:
                    cfg[k] = data[k]
    except (OSError, ValueError):
        pass
    return cfg


def list_assets():
    """回傳 (images, music)：site/assets/ 下的檔名，格式 assets/<檔名>，已排序。"""
    images, music = [], []
    assets_dir = os.path.join(SITE_ROOT, "site", "assets")
    try:
        names = sorted(os.listdir(assets_dir))
    except OSError:
        return images, music
    for name in names:
        if not os.path.isfile(os.path.join(assets_dir, name)):
            continue
        low = name.lower()
        if low.endswith(IMAGE_EXTS):
            images.append("assets/" + name)
        elif low.endswith(MUSIC_EXTS):
            music.append("assets/" + name)
    return images, music


def atomic_write_json(path, data):
    """先寫同目錄暫存檔再 os.replace；任何錯誤都清掉暫存檔。"""
    directory = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".home-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def valid_book_data(key):
    """回傳 (chapters, verses_by_ch) 或 None。"""
    if key not in BOOK_KEYS:
        return None
    try:
        with open(os.path.join(SITE_ROOT, "data", key + ".json"), "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("chapters"), list):
        return None
    return data


def validate_home_config(obj):
    """驗證主頁設定；通過回 (cfg, None)，失敗回 (None, 錯誤訊息)。"""
    if not isinstance(obj, dict):
        return None, "內容必須是 JSON 物件"
    if set(obj.keys()) != set(HOME_FIELDS):
        return None, "欄位必須剛好是 book、ch、v、image、alt、music"
    book, ch, v = obj.get("book"), obj.get("ch"), obj.get("v")
    if not isinstance(book, str) or book not in BOOK_KEYS:
        return None, "書卷代號不正確"
    for label, val in (("章", ch), ("節", v)):
        if isinstance(val, bool) or not isinstance(val, int):
            return None, label + "必須是整數"
    data = valid_book_data(book)
    if data is None:
        return None, "讀不到該書卷的經文資料"
    chapters = data.get("chapters") or []
    chapter = None
    for c in chapters:
        if isinstance(c, dict) and c.get("ch") == ch:
            chapter = c
            break
    if chapter is None:
        return None, "指定的章不存在"
    verses = chapter.get("verses") or []
    if not any(isinstance(x, dict) and x.get("v") == v for x in verses):
        return None, "指定的節不存在"

    for label, field, exts in (("圖片", "image", IMAGE_EXTS), ("音樂", "music", MUSIC_EXTS)):
        val = obj.get(field)
        if not isinstance(val, str) or not ASSET_RE.match(val) or ".." in val:
            return None, label + "路徑不正確"
        if not val.lower().endswith(exts):
            return None, label + "副檔名不正確"
        if not os.path.isfile(os.path.join(SITE_ROOT, "site", val)):
            return None, label + "檔案不存在"

    alt = obj.get("alt")
    if not isinstance(alt, str):
        return None, "圖片說明必須是文字"
    alt = alt.strip()
    if not 1 <= len(alt) <= 120:
        return None, "圖片說明長度必須是 1 到 120 字"
    return {
        "book": book,
        "ch": ch,
        "v": v,
        "image": obj["image"],
        "alt": alt,
        "music": obj["music"],
    }, None


def sniff_upload(kind, data):
    """用 magic bytes 判斷真實格式；回副檔名（不含點）或 None。"""
    if kind == "image":
        if data.startswith(b"\xff\xd8\xff"):
            return "jpg"
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "png"
        if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return "webp"
        return None
    if data.startswith(b"ID3"):
        return "mp3"
    if len(data) >= 2 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0:
        return "mp3"
    return None



def probe_url(url, timeout=2.0):
    start = time.time()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BibleMaster-AdminProbe/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = resp.getcode()
            elapsed_ms = int((time.time() - start) * 1000)
            return True, code, elapsed_ms
    except urllib.error.HTTPError as e:
        elapsed_ms = int((time.time() - start) * 1000)
        # 401/403/302 表示服務正在運行中（例如 Harness 需要登入 token）
        if e.code in (200, 301, 302, 401, 403):
            return True, f"HTTP {e.code}", elapsed_ms
        return False, f"HTTP {e.code}", elapsed_ms
    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        return False, str(e), elapsed_ms


class AdminRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=HERE, **kwargs)

    def log_message(self, format, *args):
        # 簡易自訂日誌
        sys.stderr.write("[%s] 後台API: %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), format % args))

    def send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/status":
            self.handle_api_status()
        elif path == "/api/models":
            self.handle_api_models()
        elif path == "/api/tasks":
            self.handle_api_tasks()
        elif path.startswith("/api/report/"):
            report_name = path[len("/api/report/"):]
            self.handle_api_report(report_name)
        elif path == "/api/ping":
            self.send_json({"status": "ok", "time": time.time()})
        elif path == "/api/token":
            self.handle_api_token()
        elif path == "/api/home":
            self.handle_api_home_get()
        elif path.startswith("/api/book/"):
            self.handle_api_book(path[len("/api/book/"):])
        elif path.startswith("/api/"):
            # 未認知的 API 端點
            self.send_json({"error": "找不到該操作端點"}, code=404)
        elif path in ("/", "/index.html", "/admin.js", "/admin.css"):
            # 靜態文件服務
            super().do_GET()
        else:
            # 其他路徑一律回 404
            self.send_json({"error": "找不到檔案"}, code=404)

    def do_HEAD(self):
        # HEAD 套用與 do_GET 完全相同的路由規則；非靜態檔只回標頭、不送內容
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path in ("/", "/index.html", "/admin.js", "/admin.css"):
            # 靜態文件服務（只送標頭，不送 body）
            super().do_HEAD()
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", "0")
            self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # 寫入端點（主頁設定、上傳）需要額外的權杖與 Host 檢查
        if path in ("/api/home", "/api/home/reset", "/api/upload"):
            if not self.check_write_auth():
                return
            try:
                if path == "/api/home":
                    self.handle_api_home_post()
                elif path == "/api/home/reset":
                    self.handle_api_home_reset()
                else:
                    self.handle_api_upload(parsed)
            except Exception:
                self.send_json({"error": "伺服器處理請求時發生錯誤"}, code=500)
            return

        # 權限檢查：必須有 X-Bible-Admin 標頭（值為 "1"）
        if self.headers.get("X-Bible-Admin") != "1":
            self.send_json({"error": "缺少 X-Bible-Admin 標頭"}, code=403)
            return

        # Origin 檢查：若有，必須與同源一致（http:// + Host）
        origin = self.headers.get("Origin")
        if origin is not None:
            host = self.headers.get("Host", "")
            if origin != "http://" + host:
                self.send_json({"error": "不允許的來源"}, code=403)
                return

        if path == "/api/action/check_all":
            self.handle_run_command([sys.executable, "bible-site/tools/check_all.py"], "自動全檢驗 (check_all.py)")
        elif path == "/api/action/visual_checks":
            self.handle_run_command([sys.executable, "bible-site/tests/visual_checks.py"], "視覺與無障礙檢驗 (visual_checks.py)")
        elif path == "/api/action/verify_text":
            self.handle_run_command([sys.executable, "bible-site/tools/verify_text.py"], "經文原文比對 (verify_text.py)")
        elif path == "/api/action/smoke_test":
            self.handle_run_command(["node", "bible-site/tests/smoke.js"], "基礎冒煙測試 (smoke.js)")
        else:
            self.send_json({"error": "找不到該操作端點"}, code=404)

    # ---------- 寫入端點共用檢查 ----------
    @staticmethod
    def host_name(host_header):
        """從 Host 標頭取出主機名（去掉埠號與 IPv6 方括號）。"""
        value = (host_header or "").strip()
        if not value:
            return ""
        if value.startswith("["):
            end = value.find("]")
            return value[1:end].lower() if end != -1 else value.lower()
        if ":" in value:
            return value.rsplit(":", 1)[0].lower()
        return value.lower()

    def host_allowed(self):
        name = self.host_name(self.headers.get("Host"))
        return bool(name) and (name in LOCAL_HOSTNAMES or name in ALLOWED_HOSTS)

    def check_write_auth(self):
        """依序檢查四項寫入權限；任何一項不過就回 403 且不讀內容、不寫檔。"""
        if self.headers.get("X-Bible-Admin") != "1":
            self.send_json({"error": "缺少 X-Bible-Admin 標頭"}, code=403)
            return False
        token = self.headers.get("X-Bible-Token") or ""
        if not ADMIN_TOKEN or not hmac.compare_digest(token, ADMIN_TOKEN):
            self.send_json({"error": "寫入權杖不正確"}, code=403)
            return False
        origin = self.headers.get("Origin")
        if origin is not None and origin != "http://" + self.headers.get("Host", ""):
            self.send_json({"error": "不允許的來源"}, code=403)
            return False
        if not self.host_allowed():
            self.send_json({"error": "不允許的主機位址"}, code=403)
            return False
        return True

    def read_body(self, limit):
        """依 Content-Length 讀取請求內容；超過 limit 回 None（不讀內容）。"""
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except (TypeError, ValueError):
            length = 0
        if length > limit:
            return None
        if length <= 0:
            return b""
        return self.rfile.read(length)

    def reject_too_large(self):
        """回 413；內容不落地、不解析，只把連線上剩餘的位元組讀掉丟棄，
        避免客戶端還在送出內容時就關閉連線而收到 RST（看不到 413）。"""
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except (TypeError, ValueError):
            length = 0
        self.send_json({"error": "內容超過大小上限"}, code=413)
        try:
            self.wfile.flush()
        except OSError:
            pass
        remaining = length
        while remaining > 0:
            try:
                chunk = self.rfile.read(min(65536, remaining))
            except OSError:
                break
            if not chunk:
                break
            remaining -= len(chunk)
        self.close_connection = True

    # ---------- 主頁設定 ----------
    def handle_api_token(self):
        if not self.host_allowed():
            self.send_json({"error": "不允許的主機位址"}, code=403)
            return
        origin = self.headers.get("Origin")
        if origin is not None and origin != "http://" + self.headers.get("Host", ""):
            self.send_json({"error": "不允許的來源"}, code=403)
            return
        self.send_json({"token": ADMIN_TOKEN})

    def handle_api_home_get(self):
        images, music = list_assets()
        self.send_json({
            "config": load_home_config(),
            "defaults": dict(HOME_DEFAULTS),
            "images": images,
            "music": music,
        })

    def handle_api_book(self, key):
        if key not in BOOK_KEYS:
            self.send_json({"error": "找不到該書卷"}, code=404)
            return
        path = os.path.join(SITE_ROOT, "data", key + ".json")
        try:
            with open(path, "rb") as f:
                body = f.read()
        except OSError:
            self.send_json({"error": "讀不到該書卷的經文資料"}, code=404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body)

    def handle_api_home_post(self):
        raw = self.read_body(HOME_MAX_BODY)
        if raw is None:
            self.reject_too_large()
            return
        try:
            obj = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            self.send_json({"error": "內容不是合法的 JSON"}, code=400)
            return
        cfg, err = validate_home_config(obj)
        if err:
            self.send_json({"error": err}, code=400)
            return
        try:
            atomic_write_json(home_config_path(), cfg)
        except Exception:
            self.send_json({"error": "無法寫入主頁設定"}, code=500)
            return
        self.send_json({"ok": True, "config": cfg})

    def handle_api_home_reset(self):
        # 內容不使用，但要把連線上的位元組讀掉，避免影響 keep-alive 的後續請求
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except (TypeError, ValueError):
            length = 0
        if length > 0:
            self.rfile.read(length)
        cfg = dict(HOME_DEFAULTS)
        try:
            atomic_write_json(home_config_path(), cfg)
        except Exception:
            self.send_json({"error": "無法寫入主頁設定"}, code=500)
            return
        self.send_json({"ok": True, "config": cfg})

    def handle_api_upload(self, parsed):
        query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        kind = (query.get("kind") or [""])[0]
        name = (query.get("name") or [""])[0]
        if kind not in UPLOAD_MAX:
            self.send_json({"error": "上傳類型只能是 image 或 music"}, code=400)
            return
        # 原檔名只用於顯示；只取其副檔名做白名單檢查，不影響存檔路徑
        base = os.path.basename(name.replace("\\", "/"))
        ext = os.path.splitext(base)[1].lower()
        allowed = IMAGE_EXTS if kind == "image" else MUSIC_EXTS
        if ext not in allowed:
            self.send_json({"error": "檔案副檔名不正確"}, code=400)
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except (TypeError, ValueError):
            length = 0
        if length <= 0:
            self.send_json({"error": "沒有收到檔案內容"}, code=400)
            return
        if length > UPLOAD_MAX[kind]:
            self.reject_too_large()
            return
        data = self.rfile.read(length)
        real_ext = sniff_upload(kind, data)
        if real_ext is None:
            self.send_json({"error": "檔案格式不符"}, code=400)
            return
        assets_dir = os.path.join(SITE_ROOT, "site", "assets")
        try:
            os.makedirs(assets_dir, exist_ok=True)
        except OSError:
            self.send_json({"error": "無法建立上傳目錄"}, code=500)
            return
        stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
        saved = None
        for _ in range(20):
            filename = "upload-%s-%s.%s" % (stamp, secrets.token_hex(2), real_ext)
            target = os.path.join(assets_dir, filename)
            try:
                fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            except FileExistsError:
                continue
            except OSError:
                self.send_json({"error": "無法建立上傳檔案"}, code=500)
                return
            try:
                with os.fdopen(fd, "wb") as f:
                    f.write(data)
                saved = filename
            except OSError:
                try:
                    os.unlink(target)
                except OSError:
                    pass
                self.send_json({"error": "寫入上傳檔案失敗"}, code=500)
                return
            break
        if saved is None:
            self.send_json({"error": "無法產生不重複的檔名"}, code=500)
            return
        self.send_json({"ok": True, "path": "assets/" + saved, "bytes": len(data)})

    def handle_api_status(self):
        # 1. 前台伺服器檢測
        fe_ok, fe_code, fe_latency = probe_url("http://127.0.0.1:8090/site/index.html", timeout=1.0)
        
        # 2. 四福音資料讀取
        books_stat = []
        total_verses = 0
        all_books_valid = True
        for key, name, exp_ch, exp_v in BOOKS:
            json_file = os.path.join(SITE_ROOT, "data", f"{key}.json")
            f_exists = os.path.isfile(json_file)
            cur_verses = 0
            cur_chapters = 0
            if f_exists:
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        d = json.load(f)
                        cur_chapters = len(d.get("chapters", []))
                        cur_verses = sum(len(c.get("verses", [])) for c in d.get("chapters", []))
                except Exception:
                    pass
            total_verses += cur_verses
            match = (cur_chapters == exp_ch and cur_verses == exp_v)
            if not match:
                all_books_valid = False
            books_stat.append({
                "key": key,
                "name": name,
                "expected_chapters": exp_ch,
                "chapters": cur_chapters,
                "expected_verses": exp_v,
                "verses": cur_verses,
                "file_exists": f_exists,
                "match": match
            })

        # 3. 測試報告狀態
        fails_path = os.path.join(SITE_ROOT, "FAILS.md")
        fails_content = ""
        fails_all_pass = False
        if os.path.isfile(fails_path):
            with open(fails_path, "r", encoding="utf-8") as f:
                fails_content = f.read()
                fails_all_pass = ("全部通過" in fails_content)

        # 4. site 前台核心檔案完整性
        site_required = ["index.html", "chapter.html", "search.html", "card.html", "style.css", "app.js"]
        site_files = {f: os.path.isfile(os.path.join(SITE_ROOT, "site", f)) for f in site_required}
        all_site_files_exist = all(site_files.values())

        data = {
            "project": "Bible-Master 四福音聖經網站",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "frontend": {
                "port": 8090,
                "online": fe_ok,
                "status_code": fe_code if fe_ok else None,
                "latency_ms": fe_latency,
                "url": "http://127.0.0.1:8090/site/index.html",
                "direct_url": "http://127.0.0.1:8090/site/index.html"
            },
            "backend": {
                "port": self.server.server_address[1],
                "online": True
            },
            "books": books_stat,
            "total_verses": total_verses,
            "expected_total_verses": 3776,
            "database_ok": all_books_valid and total_verses == 3776,
            "site_files": site_files,
            "site_files_ok": all_site_files_exist,
            "fails_pass": fails_all_pass,
            "fails_summary": fails_content.splitlines()[0] if fails_content else "無紀錄"
        }
        self.send_json(data)

    def handle_api_models(self):
        results = []
        for node in MODEL_NODES:
            ok, info, latency = probe_url(node["url"], timeout=1.5)
            if not ok and node.get("alt_url"):
                ok, info, latency = probe_url(node["alt_url"], timeout=1.5)
            
            results.append({
                "id": node["id"],
                "name": node["name"],
                "host": node["host"],
                "port": node["port"],
                "online": ok,
                "status_detail": str(info),
                "latency_ms": latency if ok else None,
                "hint": node["hint"]
            })
        self.send_json({"models": results, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")})

    def handle_api_tasks(self):
        tasks_dir = os.path.join(SITE_ROOT, "tasks")
        tasks = []
        if os.path.isdir(tasks_dir):
            for fname in sorted(os.listdir(tasks_dir)):
                if fname.endswith(".md"):
                    fpath = os.path.join(tasks_dir, fname)
                    with open(fpath, "r", encoding="utf-8") as f:
                        content = f.read(2048)
                    role_m = re.search(r"role:\s*([^\n]+)", content)
                    files_m = re.search(r"files:\s*\[([^\]]+)\]", content)
                    tasks.append({
                        "file": fname,
                        "role": role_m.group(1).strip() if role_m else "未指定",
                        "files": files_m.group(1).strip() if files_m else ""
                    })
        self.send_json({"tasks": tasks})

    def handle_api_report(self, report_name):
        safe_name = os.path.basename(report_name)
        if safe_name not in REPORT_WHITELIST:
            self.send_json({"error": "找不到指定報告檔案"}, code=404)
            return
        report_path = os.path.join(SITE_ROOT, safe_name)
        if not os.path.isfile(report_path):
            self.send_json({"error": "找不到指定報告檔案"}, code=404)
            return
        with open(report_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # 最多返回後 250 行，避免過大
        tail = "".join(lines[-250:]) if len(lines) > 250 else "".join(lines)
        self.send_json({"name": safe_name, "content": tail, "total_lines": len(lines)})

    def handle_run_command(self, cmd, title):
        # 同一時間只能執行一個動作
        if not ACTION_LOCK.acquire(blocking=False):
            self.send_json({"error": "已有動作執行中"}, code=409)
            return
        start_t = time.time()
        try:
            p = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=180)
            elapsed = round(time.time() - start_t, 2)
            self.send_json({
                "action": title,
                "success": (p.returncode == 0),
                "exit_code": p.returncode,
                "elapsed_seconds": elapsed,
                "stdout": p.stdout,
                "stderr": p.stderr,
                "output": (p.stdout + "\n" + p.stderr).strip()
            })
        except subprocess.TimeoutExpired:
            self.send_json({
                "action": title,
                "success": False,
                "exit_code": -1,
                "output": f"執行逾時（超過 180 秒）"
            }, code=500)
        except Exception as e:
            self.send_json({
                "action": title,
                "success": False,
                "exit_code": -1,
                "output": f"執行異常：{e}"
            }, code=500)
        finally:
            ACTION_LOCK.release()


class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def run_server(host="127.0.0.1", port=8091):
    init_token()
    server = ThreadingHTTPServer((host, port), AdminRequestHandler)
    print(f"=================================================================")
    print(f" 📖 Bible-Master 後台管理與運維服務啟動成功！")
    print(f" 🌐 後台位址: http://{host if host != '0.0.0.0' else '127.0.0.1'}:{port}/")
    print(f" 📂 服務目錄: {HERE}")
    print(f" ⏱️ 啟動時間: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"=================================================================")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n後台服務接收到終止信號，正常退出。")
    finally:
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bible-Master 後台管理與 API 伺服器")
    parser.add_argument("--host", default="127.0.0.1", help="監聽主機 IP（預設 127.0.0.1，只限本機）")
    parser.add_argument("--port", type=int, default=8091, help="監聽埠號 (預設 8091)")
    args = parser.parse_args()
    run_server(args.host, args.port)
