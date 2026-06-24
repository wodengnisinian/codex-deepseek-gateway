# -*- coding: utf-8 -*-
"""Codex DeepSeek Gateway -- Desktop Launcher  v1.0.1  PySide6 Edition (No Console Popup)"""
import sys, os, re, locale, time, threading, logging, queue, asyncio, socket
from urllib.request import urlopen

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStackedWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QPlainTextEdit, QMessageBox,
    QDialog, QScrollArea,
)
from PySide6.QtCore import (
    Qt, QTimer, QThread, Signal
)
from PySide6.QtGui import (
    QIcon, QPixmap,
)


# ---- PyInstaller -w no-console guard (uvicorn calls isatty()) ----
class _NullStream:
    def write(self, *_args, **_kwargs):
        return 0
    def flush(self):
        pass
    def isatty(self):
        return False

if sys.stdout is None:
    sys.stdout = _NullStream()
if sys.stderr is None:
    sys.stderr = _NullStream()

# ---- Path helpers ----
def get_runtime_dir():
    """Return the directory containing bundled resources.

    Frozen (PyInstaller -F): sys._MEIPASS (temp extraction dir)
    Source: project root (parent of scripts/ if running from there)
    """
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    here = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(here).lower() == "scripts":
        return os.path.dirname(here)
    return here


def resource_path(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def get_app_icon():
    ico = resource_path("app_icon.ico")
    png = resource_path("app_icon.png")
    if os.path.exists(ico):
        icon = QIcon(ico)
        if not icon.pixmap(32, 32).isNull():
            return icon
    if os.path.exists(png):
        return QIcon(png)
    return QIcon()

def get_app_dir():
    """Return the project root directory.
    
    When frozen (PyInstaller -F): directory containing the .exe
    When running from scripts/: parent of scripts/
    Otherwise: directory containing this .py file
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    here = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(here).lower() == "scripts":
        return os.path.dirname(here)
    return here


# ---- Constants ----
GW       = "http://127.0.0.1:3688"
CFG_PATH = os.path.join(os.path.expanduser("~"), ".codex", "config.toml")
ICON_PNG = resource_path("app_icon.png")
ICON_ICO = resource_path("app_icon.ico")

# ---- Theme ----
C = {
    "bg":"#EEF0F2", "cd":"#FFFFFF", "tp":"#FAFAFA", "sb":"#172030",
    "ac":"#5EA0A0", "ac2":"#7EB8B8", "tx":"#111111", "mu":"#667788", "bd":"#E0E2E6",
    "ok":"#4CAF50", "er":"#E57373", "nv":"#95A8B8", "na":"#E8ECF0",
    "lg":"#1A1A20", "lgt":"#CCCCCC", "nh":"#253550", "no":"#253550",
}

# ---- Language ----
def _lang():
    try:
        import ctypes
        lcid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        return "zh" if lcid in (0x0804,0x0404,0x0C04,0x1004,0x1404) else "en"
    except:
        try: l,_=locale.getlocale(); return "zh" if l and l.startswith(("zh","Chinese")) else "en"
        except: return "en"

LNG = _lang()
TS = {
    "title": {"zh":"Codex DeepSeek Gateway \u7f51\u5173","en":"Codex DeepSeek Gateway"},
    "home":  {"zh":"\u9996\u9875","en":"HOME"},
    "config":{"zh":"\u914d\u7f6e","en":"CONFIG"},
    "logs":  {"zh":"\u65e5\u5fd7","en":"LOGS"},
    "about": {"zh":"\u5173\u4e8e","en":"ABOUT"},
    "start": {"zh":"\u25b6 \u542f\u52a8\u7f51\u5173","en":"\u25b6 START GATEWAY"},
    "stop":  {"zh":"\u25a0 \u505c\u6b62\u7f51\u5173","en":"\u25a0 STOP GATEWAY"},
    "welcome":{"zh":"\u6b22\u8fce\u4f7f\u7528 CDG Launcher","en":"Welcome to CDG Launcher"},
    "desc":  {"zh":"\u672c\u5730\u517c\u5bb9\u7f51\u5173 \u2014 Responses API \u2192 DeepSeek Chat","en":"Local gateway: Responses API to DeepSeek Chat"},
    "gw_addr":{"zh":"\u7f51\u5173: http://127.0.0.1:3688/v1","en":"Gateway: http://127.0.0.1:3688/v1"},
    "status": {"zh":"\u72b6\u6001","en":"Status"},
    "model":  {"zh":"\u5f53\u524d\u6a21\u578b","en":"Current Model"},
    "port":   {"zh":"\u7aef\u53e3","en":"Port"},
    "running":{"zh":"\u8fd0\u884c\u4e2d","en":"Running"},
    "stopped":{"zh":"\u672a\u542f\u52a8","en":"Stopped"},
    "checking":{"zh":"\u68c0\u6d4b\u4e2d...","en":"Checking..."},
    "models_ttl":{"zh":"\u652f\u6301\u6a21\u578b","en":"Supported Models"},
    "md_flash":{"zh":"\u6781\u901f\uff0c\u65e5\u5e38\u7f16\u7801","en":"Fastest, daily coding"},
    "md_pro":  {"zh":"\u6df1\u5ea6\u63a8\u7406","en":"Deep reasoning"},
    "md_chat": {"zh":"\u901a\u7528\u5bf9\u8bdd V3","en":"General dialog V3"},
    "md_rea":  {"zh":"\u601d\u7ef4\u94fe R1","en":"Chain-of-thought R1"},
    "apikey_ttl":{"zh":"API Key \u8bbe\u7f6e","en":"API Key Setup"},
    "apikey_hint":{"zh":"\u8f93\u5165 DeepSeek API Key","en":"Enter DeepSeek API Key"},
    "apikey_save":{"zh":"\u4fdd\u5b58 API Key","en":"SAVE API KEY"},
    "apikey_done":{"zh":"\u5df2\u4fdd\u5b58\uff0c\u91cd\u542f\u7ec8\u7aef","en":"Saved. Restart terminal."},
    "apikey_exist":{"zh":"\u5df2\u914d\u7f6e","en":"Configured"},
    "cfg_title":{"zh":"\u7f51\u5173\u914d\u7f6e","en":"Gateway Config"},
    "cfg_editor":{"zh":"Codex Config \u7f16\u8f91\u5668","en":"Codex Config Editor"},
    "cfg_save": {"zh":"\u4fdd\u5b58","en":"SAVE"},
    "cfg_backup":{"zh":"\u5907\u4efd","en":"BACKUP"},
    "cfg_reset":{"zh":"\u91cd\u7f6e","en":"RESET"},
    "cfg_loaded":{"zh":"\u5df2\u52a0\u8f7d: %s","en":"Loaded: %s"},
    "cfg_saved":{"zh":"\u5df2\u4fdd\u5b58","en":"Config saved"},
    "log_title":{"zh":"\u7f51\u5173\u65e5\u5fd7","en":"Gateway Logs"},
    "log_hint": {"zh":"\u70b9\u51fb\u542f\u52a8\uff0c\u65e5\u5fd7\u5b9e\u65f6\u663e\u793a","en":"Click START to see logs"},
    "start_t":  {"zh":"\u542f\u52a8\u7f51\u5173","en":"Start Gateway"},
    "start_m":  {"zh":"\u7f51\u5173\u6b63\u5728\u542f\u52a8","en":"Starting gateway..."},
    "stop_t":   {"zh":"\u505c\u6b62\u7f51\u5173","en":"Stop Gateway"},
    "stop_q":   {"zh":"\u786e\u5b9a\u505c\u6b62\uff1f","en":"Stop the gateway?"},
    "stop_m":   {"zh":"\u5df2\u505c\u6b62","en":"Gateway stopped."},
    "already":  {"zh":"\u7f51\u5173\u5df2\u8fd0\u884c","en":"Gateway already running"},
    "no_gw":    {"zh":"\u672a\u53d1\u73b0\u8fd0\u884c\u7f51\u5173","en":"No running gateway"},
    "error":    {"zh":"\u9519\u8bef","en":"Error"},
    "about_ttl":{"zh":"\u5173\u4e8e CDG Launcher","en":"About CDG Launcher"},
    "about_name":{"zh":"CDG Launcher","en":"CDG Launcher"},
    "about_desc":{"zh":"Codex DeepSeek Gateway","en":"Codex DeepSeek Gateway"},
    "about_author":{"zh":"Author: ZB-WDSN","en":"Author: ZB-WDSN"},
    "about_school":{"zh":"Guizhou Light Industry Technical University","en":"Guizhou Light Industry Technical University"},
    "about_ver": {"zh":"v0.4.0  PySide6 Edition","en":"v0.4.0  PySide6 Edition"},
}
def T(k): return TS.get(k,{}).get(LNG, k)

# ---- Gateway Service ----
class GatewayService:
    @staticmethod
    def health_check(timeout=0.35):
        try:
            r = urlopen(GW + "/health", timeout=timeout)
            return r.status == 200
        except: return False

    @staticmethod
    def models_check(timeout=0.35):
        try:
            r = urlopen(GW + "/v1/models", timeout=timeout)
            return True, r.read().decode()
        except: return False, "{}"

    @staticmethod
    def read_current_model():
        try:
            with open(CFG_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    m = re.match(r'^\s*model\s*=\s*"([^"]+)"', line)
                    if m: return m.group(1)
        except: pass
        return "deepseek-v4-flash"

    @staticmethod
    def api_key_configured():
        """Check if DEEPSEEK_API_KEY is configured (env var or Windows registry)."""
        if os.environ.get("DEEPSEEK_API_KEY", ""):
            return True
        if sys.platform == "win32":
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_READ) as key:
                    val, _ = winreg.QueryValueEx(key, "DEEPSEEK_API_KEY")
                    return bool(val)
            except (FileNotFoundError, OSError):
                pass
        return False

    @staticmethod
    def save_api_key(value):
        """Save DEEPSEEK_API_KEY to env var and Windows registry (no subprocess)."""
        os.environ["DEEPSEEK_API_KEY"] = value
        if sys.platform == "win32":
            try:
                import winreg, ctypes
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE) as key:
                    winreg.SetValueEx(key, "DEEPSEEK_API_KEY", 0, winreg.REG_SZ, value)
                HWND_BROADCAST = 0xFFFF
                WM_SETTINGCHANGE = 0x001A
                ctypes.windll.user32.SendMessageTimeoutW(HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment", 0, 5000, None)
            except Exception:
                pass

    @staticmethod
    def read_config():
        try:
            with open(CFG_PATH, "r", encoding="utf-8") as f: return f.read()
        except: return ""

    @staticmethod
    def save_config(content):
        os.makedirs(os.path.dirname(CFG_PATH), exist_ok=True)
        if os.path.exists(CFG_PATH):
            try:
                bk = CFG_PATH + ".backup-" + time.strftime("%Y%m%d-%H%M%S")
                with open(CFG_PATH, "r", encoding="utf-8") as src:
                    with open(bk, "w", encoding="utf-8") as dst: dst.write(src.read())
            except: pass
        with open(CFG_PATH, "w", encoding="utf-8") as f: f.write(content)

    @staticmethod
    def stop_port_3688():
        """Kill process listening on port 3688 via ctypes (no powershell)."""
        if sys.platform != "win32":
            return
        try:
            import ctypes
            pid = _find_pid_on_port(3688)
            if pid:
                h = ctypes.windll.kernel32.OpenProcess(1, False, pid)
                if h:
                    ctypes.windll.kernel32.TerminateProcess(h, 0)
                    ctypes.windll.kernel32.CloseHandle(h)
        except Exception:
            pass


# ---- Status Worker (QThread) ----
class StatusWorker(QThread):
    result = Signal(bool, bool, str, bool)

    def run(self):
        h_ok = GatewayService.health_check()
        m_ok, _ = GatewayService.models_check()
        model = GatewayService.read_current_model()
        a_ok = GatewayService.api_key_configured()
        self.result.emit(h_ok, m_ok, model, a_ok)


# ---- Gateway Server (Embedded Uvicorn) ----
class QueueLogHandler(logging.Handler):
    """Logging handler that pushes formatted messages into a queue."""

    def __init__(self, log_queue):
        super().__init__()
        self._queue = log_queue

    def emit(self, record):
        try:
            self._queue.put(self.format(record))
        except Exception:
            pass


class GatewayServer(QThread):
    """Run uvicorn + FastAPI app with full diagnostics and exception capture."""

    log_line = Signal(str)

    def __init__(self):
        super().__init__()
        self.server = None
        self._should_stop = threading.Event()

    def _emit(self, msg):
        """Thread-safe log line emitter (safe from any thread in PySide6)."""
        self.log_line.emit(msg)

    def run(self):
        import traceback

        try:
            # ---- Diagnostics ----
            self._emit("[CDG] === Gateway Startup Diagnostics ===")
            self._emit(f"[CDG] sys.executable = {sys.executable}")
            self._emit(f"[CDG] sys.frozen = {getattr(sys, 'frozen', False)}")
            self._emit(f"[CDG] sys._MEIPASS = {getattr(sys, '_MEIPASS', 'N/A')}")
            self._emit(f"[CDG] os.getcwd() = {os.getcwd()}")
            runtime_dir = get_runtime_dir()
            self._emit(f"[CDG] runtime_dir = {runtime_dir}")
            self._emit(f"[CDG] sys.path[:4] = {sys.path[:4]}")
            if getattr(sys, "frozen", False):
                self._emit(f"[CDG] _MEIPASS contents: {sorted(os.listdir(sys._MEIPASS))}")

            # Ensure runtime_dir is in sys.path for imports
            if runtime_dir not in sys.path:
                sys.path.insert(0, runtime_dir)
                self._emit(f"[CDG] Added runtime_dir to sys.path[0]")

            # ---- Import uvicorn ----
            import uvicorn
            self._emit(f"[CDG] uvicorn v{uvicorn.__version__} @ {uvicorn.__file__}")

            # ---- Import FastAPI app ----
            import server
            self._emit(f"[CDG] server module loaded, app object = {server.app}")
            self._emit(f"[CDG] server.__file__ = {server.__file__}")

            # ---- Fix MODEL_CATALOG_PATH for _MEIPASS ----
            server.MODEL_CATALOG_PATH = os.path.join(runtime_dir, "codex", "model_catalog.json")
            catalog_exists = os.path.exists(server.MODEL_CATALOG_PATH)
            self._emit(f"[CDG] MODEL_CATALOG_PATH = {server.MODEL_CATALOG_PATH} (exists={catalog_exists})")

            # ---- Setup uvicorn logging bridge ----
            log_queue = queue.Queue()
            handler = QueueLogHandler(log_queue)
            handler.setFormatter(logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))
            for name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"):
                lg = logging.getLogger(name)
                lg.handlers.clear()
                lg.addHandler(handler)
                lg.setLevel(logging.INFO)
                lg.propagate = False

            # ---- Create uvicorn Server ----
            config = uvicorn.Config(
                server.app,
                host="127.0.0.1",
                port=3688,
                log_level="info",
                access_log=False,
                log_config=None,
            )
            self.server = uvicorn.Server(config)

            # ---- Start log-polling daemon ----
            def poll_logs():
                while not self._should_stop.is_set():
                    try:
                        line = log_queue.get(timeout=0.2)
                        self._emit(line)
                    except queue.Empty:
                        pass

            poll_thread = threading.Thread(target=poll_logs, daemon=True)
            poll_thread.start()

            # ---- Serve ----
            self._emit("[CDG] Calling loop.run_until_complete(server.serve()) ...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.server.serve())
            except (SystemExit, KeyboardInterrupt):
                self._emit("[CDG] Server received SystemExit / KeyboardInterrupt")
            finally:
                loop.close()
            self._emit("[CDG] uvicorn server.serve() returned normally")

        except Exception:
            self._emit("[CDG] ========================================")
            self._emit("[CDG] FATAL ERROR in gateway startup:")
            for line in traceback.format_exc().splitlines():
                self._emit(f"[CDG]   {line}")
            self._emit("[CDG] ========================================")
        finally:
            self._should_stop.set()
            self._emit("[CDG] GatewayServer.run() exiting")

    def shutdown(self):
        self._emit("[CDG] Shutdown requested")
        if self.server:
            self.server.should_exit = True
        self._should_stop.set()



# ---- Main Window ----
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(T("title"))
        self.resize(900, 560)
        self.setMinimumSize(760, 480)
        self._gw_server = None
        self._log_reader = None
        self._status_worker = None
        self._nav_btns = {}
        self._status_dots = {}
        self._status_lbls = {}
        # Set icon BEFORE building UI for immediate taskbar reflection

        # Anti-duplicate-start guards
        self._is_starting = False
        self._last_start_time = 0.0
        self._start_debounce_sec = 3.0

        app_icon = get_app_icon()
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)
        self._setup_ui()
        # Deferred status refresh
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._async_refresh)
        self._refresh_timer.setInterval(10000)
        QTimer.singleShot(400, self._start_refresh)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        # Sidebar
        sidebar = self._build_sidebar()
        main_layout.addWidget(sidebar)
        # Right side: status + pages
        right = QWidget()
        right.setStyleSheet("background-color:" + C["bg"] + ";")
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(0)
        status_bar = self._build_status_bar()
        rv.addWidget(status_bar)
        self._stack = QStackedWidget()
        self._home_page = HomePage(self)
        self._config_page = ConfigPage(self)
        self._logs_page = LogsPage(self)
        self._stack.addWidget(self._home_page)
        self._stack.addWidget(self._config_page)
        self._stack.addWidget(self._logs_page)
        rv.addWidget(self._stack)
        main_layout.addWidget(right)

    def _build_sidebar(self):
        sb = QFrame()
        sb.setFixedWidth(175)
        sb.setStyleSheet("background-color:" + C["sb"] + "; border:none;")
        layout = QVBoxLayout(sb)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        header = QWidget()
        hl = QVBoxLayout(header)
        hl.setContentsMargins(16, 20, 16, 12)
        if os.path.exists(ICON_PNG):
            px = QPixmap(ICON_PNG).scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            il = QLabel()
            il.setPixmap(px)
            il.setAlignment(Qt.AlignmentFlag.AlignLeft)
            hl.addWidget(il)
        tl = QLabel("CDG Launcher")
        tl.setStyleSheet("color:" + C["na"] + "; font-size:14px; font-weight:bold;")
        hl.addWidget(tl)
        layout.addWidget(header)
        # Nav buttons
        for key, label in [("home", T("home")), ("config", T("config")), ("logs", T("logs"))]:
            btn = QPushButton("  " + label)
            btn.setFixedHeight(40)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                "background-color:" + C["sb"] + ";"
                "color:" + C["nv"] + ";"
                "font-size:11px; font-weight:bold;"
                "border:none; border-left:3px solid " + C["sb"] + ";"
                "text-align:left; padding-left:22px;")
            btn.clicked.connect(lambda checked, k=key: self._navigate(k))
            layout.addWidget(btn)
            self._nav_btns[key] = btn
        layout.addStretch()
        # About button at bottom
        abtn = QPushButton("  " + T("about"))
        abtn.setFixedHeight(34)
        abtn.setCursor(Qt.CursorShape.PointingHandCursor)
        abtn.setStyleSheet(
            "background-color:" + C["sb"] + ";"
            "color:" + C["nv"] + ";"
            "font-size:10px; border:none;"
            "border-top:1px solid " + C["nh"] + ";"
            "text-align:left; padding-left:22px;")
        abtn.clicked.connect(self._show_about)
        layout.addWidget(abtn)
        return sb

    def _build_status_bar(self):
        bar = QFrame()
        bar.setFixedHeight(44)
        bar.setStyleSheet("background-color:" + C["tp"] + "; border-bottom:1px solid " + C["bd"] + ";")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)
        self._page_title = QLabel(T("welcome"))
        self._page_title.setStyleSheet("color:" + C["tx"] + "; font-size:14px; font-weight:bold;")
        layout.addWidget(self._page_title)
        layout.addStretch()
        for key, label in [("gw","GW"), ("md","MD"), ("ap","API"), ("pt","PT")]:
            dot = QLabel("\u25cf")
            dot.setFixedSize(14, 14)
            dot.setStyleSheet("color:" + C["mu"] + "; font-size:9px;")
            lbl = QLabel(label)
            lbl.setStyleSheet("color:" + C["mu"] + "; font-size:9px; font-weight:bold;")
            layout.addWidget(dot)
            layout.addWidget(lbl)
            layout.addSpacing(4)
            self._status_dots[key] = dot
            self._status_lbls[key] = lbl
        return bar

    def _navigate(self, key):
        for k, btn in self._nav_btns.items():
            active = (k == key)
            btn.setStyleSheet(
                "background-color:" + (C["no"] if active else C["sb"]) + ";"
                "color:" + (C["na"] if active else C["nv"]) + ";"
                "font-size:11px; font-weight:bold;"
                "border:none; border-left:3px solid " + (C["ac"] if active else C["sb"]) + ";"
                "text-align:left; padding-left:22px;")
        pages = {"home": 0, "config": 1, "logs": 2}
        self._stack.setCurrentIndex(pages.get(key, 0))
        titles = {"home": T("welcome"), "config": T("cfg_title"), "logs": T("log_title")}
        self._page_title.setText(titles.get(key, ""))

    def _start_refresh(self):
        self._refresh_timer.start()
        self._async_refresh()

    def _async_refresh(self):
        if self._status_worker and self._status_worker.isRunning():
            return
        self._status_worker = StatusWorker()
        self._status_worker.result.connect(self._on_status_result)
        self._status_worker.start()

    def _on_status_result(self, h_ok, m_ok, model, a_ok):
        results = {"gw": h_ok, "md": m_ok, "ap": h_ok and a_ok, "pt": h_ok}
        for key in ("gw", "md", "ap", "pt"):
            ok = results[key]
            clr = C["ok"] if ok else C["er"]
            self._status_dots[key].setStyleSheet("color:" + clr + "; font-size:9px;")
            self._status_lbls[key].setStyleSheet("color:" + clr + "; font-size:9px; font-weight:bold;")
        self._home_page.update_status(results)

    def _is_port_listening(self, port=3688, host="127.0.0.1"):
        """Check if port is already occupied using socket connect."""
        try:
            import socket as _sock
            s = _sock.socket(_sock.AF_INET, _sock.SOCK_STREAM)
            s.settimeout(0.3)
            result = s.connect_ex((host, port))
            s.close()
            return result == 0
        except Exception:
            return False

    def start_gateway(self):
        """Start the gateway server (user-initiated, debounced, guarded)."""
        now = time.time()

        # Guard: already starting
        if self._is_starting:
            self._logs_page.append_log("[CDG] Gateway start already in progress, please wait...")
            return

        # Guard: debounce
        if now - self._last_start_time < self._start_debounce_sec:
            self._logs_page.append_log("[CDG] Please wait before starting again...")
            return

        # Guard: health check (already running)
        if GatewayService.health_check(0.3):
            QMessageBox.information(self, T("start_t"), T("already"))
            return

        # Guard: port occupied by external process
        if self._is_port_listening(3688):
            QMessageBox.warning(self, T("start_t"),
                "绔彛 3688 宸茶鍗犵敤鎴栫綉鍏冲凡杩愯" if LNG == "zh" else
                "Port 3688 is occupied or gateway is already running")
            return

        self._is_starting = True
        self._last_start_time = now

        self._logs_page.clear_log()
        self._logs_page.append_log("[CDG] " + T("start_m"))
        self._logs_page.append_log(f"[CDG] Starting embedded uvicorn on {GW} (PID={os.getpid()})")
        self._gw_server = GatewayServer()
        self._gw_server.log_line.connect(self._logs_page.append_log)
        self._gw_server.finished.connect(self._on_server_finished)
        self._gateway_thread = self._gw_server
        self._gw_server.start()
        self._home_page.set_gateway_buttons(starting=True, running=False)

    def _on_server_finished(self):
        """Called when GatewayServer QThread finishes."""
        self._is_starting = False
        self._logs_page.append_log("[CDG] Gateway thread finished")
        self._home_page.set_gateway_buttons(starting=False, running=False)
        self._gw_server = None
        self._gateway_thread = None
        if not getattr(self, "_user_stopped", False):
            QTimer.singleShot(2000, self._async_refresh)

    def stop_gateway(self):
        """Stop the gateway (user-initiated)."""
        reply = QMessageBox.question(self, T("stop_t"), T("stop_q"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._user_stopped = True
        self._is_starting = False

        # If embedded server is alive, shut it down
        if self._gw_server and self._gw_server.isRunning():
            self._logs_page.append_log("[CDG] Shutting down gateway...")
            try:
                if self._gw_server.server:
                    self._gw_server.server.should_exit = True
            except Exception:
                pass
            self._gw_server.shutdown()
            self._home_page.set_gateway_buttons(starting=False, running=False)
            QTimer.singleShot(2000, self._async_refresh)
            QMessageBox.information(self, T("stop_t"), T("stop_m"))
            return

        if not GatewayService.health_check(0.3):
            QMessageBox.information(self, T("stop_t"), T("no_gw"))
            return

        # Port 3688 is alive but not our server -- offer force kill
        reply2 = QMessageBox.question(self, T("stop_t"),
            "端口 3688 可能被其他程序占用，确定强制关闭？" if LNG == "zh" else "Port 3688 may be used by another program. Force close?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply2 == QMessageBox.StandardButton.Yes:
            GatewayService.stop_port_3688()
            QTimer.singleShot(1000, self._async_refresh)
            QMessageBox.information(self, T("stop_t"), T("stop_m"))

    def _show_about(self):
        dlg = AboutDialog(self)
        dlg.exec()

    def closeEvent(self, event):
        if self._gw_server and self._gw_server.isRunning():
            try:
                if self._gw_server.server:
                    self._gw_server.server.should_exit = True
            except Exception:
                pass
            self._gw_server.shutdown()
            self._gw_server.wait(3000)
        self._gateway_thread = None
        self._gw_server = None
        self._home_page.set_gateway_buttons(starting=False, running=False)
        event.accept()


# ---- About Dialog ----
class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(T("about_ttl"))
        self.setFixedSize(360, 320)
        self.setStyleSheet("background-color:" + C["sb"] + ";")
        app_icon = get_app_icon()
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 24, 30, 24)
        for text, size, color in [
            (T("about_name"), 16, C["na"]),
            (T("about_desc"), 10, C["nv"]),
            ("", 8, C["nv"]),
            (T("about_author"), 12, C["na"]),
            (T("about_school"), 10, C["na"]),
            ("", 8, C["nv"]),
            (T("about_ver"), 10, C["ac"]),
        ]:
            if not text:
                layout.addSpacing(8)
                continue
            lbl = QLabel(text)
            lbl.setStyleSheet("color:" + color + "; font-size:" + str(size) + "px; font-weight:bold;")
            layout.addWidget(lbl)
        layout.addStretch()
        btn = QPushButton("OK")
        btn.setStyleSheet(
            "background-color:" + C["ac"] + "; color:#FFF; font-weight:bold;"
            "font-size:12px; border:none; border-radius:4px; padding:8px 40px;")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)


# ---- Home Page ----
class HomePage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self._mw = main_window
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("background-color:" + C["bg"] + ";")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet(
            "QScrollArea { border:none; background-color:" + C["bg"] + "; }"
            + " QScrollBar:vertical { width:10px; background:" + C["bg"] + "; }"
            + " QScrollBar::handle:vertical { background:" + C["nv"] + "; border-radius:5px; min-height:30px; }"
            + " QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0px; }"
        )
        content = QWidget()
        content.setStyleSheet("background-color:" + C["bg"] + ";")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Welcome card
        wc = self._card()
        wl = QVBoxLayout(wc)
        wl.setContentsMargins(16, 14, 16, 14)
        wl.addWidget(self._title_label(T("welcome")))
        wl.addWidget(self._desc_label(T("gw_addr")))
        wl.addSpacing(6)
        # Buttons
        bl = QHBoxLayout()
        self._start_btn = self._btn(T("start"), C["ac"], self._mw.start_gateway)
        self._stop_btn = self._btn(T("stop"), C["er"], self._mw.stop_gateway)
        bl.addWidget(self._start_btn)
        bl.addWidget(self._stop_btn)
        bl.addStretch()
        wl.addLayout(bl)
        layout.addWidget(wc)

        # KPI cards
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(10)
        self._kpi_status_v = self._kpi_card(T("status"), T("checking"))
        self._kpi_model_v = self._kpi_card(T("model"), GatewayService.read_current_model())
        self._kpi_port_v = self._kpi_card(T("port"), "3688")
        kpi_layout.addWidget(self._kpi_status_v)
        kpi_layout.addWidget(self._kpi_model_v)
        kpi_layout.addWidget(self._kpi_port_v)
        layout.addLayout(kpi_layout)

        # Models card
        mc = self._card()
        ml = QVBoxLayout(mc)
        ml.setContentsMargins(16, 12, 16, 12)
        ml.addWidget(self._title_label(T("models_ttl")))
        for mid, desc in [
            ("deepseek-v4-flash", T("md_flash")),
            ("deepseek-v4-pro", T("md_pro")),
            ("deepseek-chat", T("md_chat")),
            ("deepseek-reasoner", T("md_rea")),
        ]:
            rl = QHBoxLayout()
            rl.addWidget(QLabel(mid))
            rl.itemAt(0).widget().setStyleSheet("color:" + C["tx"] + "; font-size:10px; font-family:Consolas;")
            rl.addWidget(QLabel(desc))
            rl.itemAt(1).widget().setStyleSheet("color:" + C["mu"] + "; font-size:9px;")
            rl.addStretch()
            ml.addLayout(rl)
        layout.addWidget(mc)

        # API Key card
        ak = self._card()
        al = QVBoxLayout(ak)
        self._api_card_layout = al
        al.setContentsMargins(16, 12, 16, 12)
        al.addWidget(self._title_label(T("apikey_ttl")))
        al.addWidget(self._desc_label(T("apikey_hint")))
        irl = QHBoxLayout()
        self._api_entry = QLineEdit()
        self._api_entry.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_entry.setPlaceholderText("sk-...")
        self._api_entry.setStyleSheet(
            "background-color:" + C["cd"] + "; color:" + C["tx"] + ";"
            "border:1px solid " + C["bd"] + "; padding:6px; font-size:10px; border-radius:3px;")
        irl.addWidget(self._api_entry)
        save_btn = self._btn(T("apikey_save"), C["ac"], self._save_api_key)
        irl.addWidget(save_btn)
        al.addLayout(irl)
        if GatewayService.api_key_configured():
            al.addWidget(self._desc_label(T("apikey_exist")))
        self._api_lbl = al.itemAt(al.count()-1).widget() if al.count() > 2 else None
        layout.addWidget(ak)
        layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _card(self):
        f = QFrame()
        f.setStyleSheet(
            "QFrame { background-color:" + C["cd"] + ";"
            "border:1px solid " + C["bd"] + "; border-radius:6px; }")
        return f

    def _title_label(self, text):
        l = QLabel(text)
        l.setStyleSheet("color:" + C["tx"] + "; font-size:13px; font-weight:bold; border:none;")
        return l

    def _desc_label(self, text):
        l = QLabel(text)
        l.setStyleSheet("color:" + C["mu"] + "; font-size:10px; border:none;")
        return l

    def _btn(self, text, color, callback):
        b = QPushButton(text)
        b.setStyleSheet(
            "background-color:" + color + "; color:#FFF; font-weight:bold;"
            "font-size:11px; border:none; border-radius:4px; padding:8px 16px;")
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.clicked.connect(callback)
        return b

    def _kpi_card(self, label, value):
        f = QFrame()
        f.setStyleSheet(
            "QFrame { background-color:" + C["cd"] + ";"
            "border:1px solid " + C["bd"] + "; border-radius:6px; }")
        l = QVBoxLayout(f)
        l.setContentsMargins(12, 10, 12, 10)
        lbl = QLabel(label)
        lbl.setStyleSheet("color:" + C["mu"] + "; font-size:9px; border:none;")
        l.addWidget(lbl)
        val = QLabel(value)
        val.setStyleSheet("color:" + C["ac"] + "; font-size:16px; font-weight:bold; border:none;")
        l.addWidget(val)
        f._val_lbl = val
        return f

    def set_gateway_buttons(self, starting=False, running=False):
        if hasattr(self, "_start_btn"):
            self._start_btn.setEnabled(not starting and not running)
        if hasattr(self, "_stop_btn"):
            self._stop_btn.setEnabled(starting or running)

    def update_status(self, results):
        ok = results.get("gw", False)
        clr = C["ok"] if ok else C["er"]
        txt = T("running") if ok else T("stopped")
        self._kpi_status_v._val_lbl.setText(txt)
        self._kpi_status_v._val_lbl.setStyleSheet(
            "color:" + clr + "; font-size:16px; font-weight:bold; border:none;")

    def _save_api_key(self):
        val = self._api_entry.text().strip()
        if not val:
            QMessageBox.warning(self, T("apikey_ttl"), T("apikey_hint"))
            return
        GatewayService.save_api_key(val)
        if not self._api_lbl:
            self._api_lbl = self._desc_label(T("apikey_exist"))
            self._api_card_layout.addWidget(self._api_lbl)
        self._api_lbl.setText(T("apikey_exist"))
        QMessageBox.information(self, T("apikey_ttl"), T("apikey_done"))


# ---- Config Page ----
class ConfigPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self._mw = main_window
        self._original = ""
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("background-color:" + C["bg"] + ";")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet(
            "QScrollArea { border:none; background-color:" + C["bg"] + "; }"
            + " QScrollBar:vertical { width:10px; background:" + C["bg"] + "; }"
            + " QScrollBar::handle:vertical { background:" + C["nv"] + "; border-radius:5px; min-height:30px; }"
            + " QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0px; }"
        )
        content = QWidget()
        content.setStyleSheet("background-color:" + C["bg"] + ";")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        # Info card
        ic = self._card()
        il = QVBoxLayout(ic)
        il.setContentsMargins(16, 12, 16, 12)
        il.addWidget(self._title(T("cfg_title")))
        model = GatewayService.read_current_model()
        for lb, vl in [
            ("Port", GW),
            ("API", GW + "/v1"),
            ("Health", GW + "/health"),
            ("Model", model),
            ("Timeout", "300s"),
            ("Retries", "3"),
        ]:
            row = QHBoxLayout()
            lbl = QLabel(lb)
            lbl.setStyleSheet("color:" + C["mu"] + "; font-size:10px; min-width:70px;")
            row.addWidget(lbl)
            val = QLabel(vl)
            val.setStyleSheet("color:" + C["tx"] + "; font-size:10px; font-family:Consolas;")
            row.addWidget(val)
            row.addStretch()
            il.addLayout(row)
        layout.addWidget(ic)

        # Editor card
        ec = self._card()
        el = QVBoxLayout(ec)
        el.setContentsMargins(16, 12, 16, 12)
        el.addWidget(self._title(T("cfg_editor")))
        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("color:" + C["mu"] + "; font-size:9px;")
        el.addWidget(self._status_lbl)
        self._editor = QPlainTextEdit()
        self._editor.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._editor.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._editor.setMinimumHeight(260)
        self._editor.setStyleSheet(
            "background-color:" + C["lg"] + "; color:" + C["lgt"] + ";"
            "font-family:Consolas; font-size:10px; border:1px solid " + C["bd"] + ";")
        el.addWidget(self._editor)
        # Buttons
        bl = QHBoxLayout()
        bl.addWidget(self._btn(T("cfg_save"), C["ac"], self._save))
        bl.addWidget(self._btn(T("cfg_backup"), C["ac2"], self._backup))
        bl.addWidget(self._btn(T("cfg_reset"), C["mu"], self._reset))
        bl.addStretch()
        el.addLayout(bl)
        layout.addWidget(ec)
        scroll.setWidget(content)
        outer.addWidget(scroll)
        self._load_config()

    def _card(self):
        f = QFrame()
        f.setStyleSheet(
            "QFrame { background-color:" + C["cd"] + ";"
            "border:1px solid " + C["bd"] + "; border-radius:6px; }")
        return f

    def _title(self, text):
        l = QLabel(text)
        l.setStyleSheet("color:" + C["tx"] + "; font-size:13px; font-weight:bold; border:none;")
        return l

    def _btn(self, text, color, callback):
        b = QPushButton(text)
        b.setStyleSheet(
            "background-color:" + color + "; color:#FFF; font-weight:bold;"
            "font-size:11px; border:none; border-radius:4px; padding:6px 14px;")
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.clicked.connect(callback)
        return b

    def _load_config(self):
        content = GatewayService.read_config()
        if not content:
            self._status_lbl.setText("\u672a\u627e\u5230 config.toml" if LNG == "zh" else "config.toml not found")
            self._original = ""
            self._editor.setPlainText("")
            return
        self._original = content
        self._editor.setPlainText(content)
        self._status_lbl.setText(T("cfg_loaded") % CFG_PATH)

    def _save(self):
        content = self._editor.toPlainText()
        GatewayService.save_config(content)
        self._original = content
        self._status_lbl.setText(T("cfg_saved"))
        QMessageBox.information(self, T("cfg_editor"), T("cfg_saved"))

    def _backup(self):
        content = self._editor.toPlainText()
        bk = CFG_PATH + ".backup-" + time.strftime("%Y%m%d-%H%M%S")
        os.makedirs(os.path.dirname(CFG_PATH), exist_ok=True)
        with open(bk, "w", encoding="utf-8") as f: f.write(content)
        QMessageBox.information(self, T("cfg_editor"), bk)

    def _reset(self):
        reply = QMessageBox.question(self, T("cfg_editor"),
            "Reset to original?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self._editor.setPlainText(self._original)


# ---- Logs Page ----
class LogsPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self._mw = main_window
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("background-color:" + C["bg"] + ";")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)

        lbl = QLabel(T("log_title"))
        lbl.setStyleSheet("color:" + C["tx"] + "; font-size:13px; font-weight:bold;")
        layout.addWidget(lbl)

        self._log_box = QPlainTextEdit()
        self._log_box.setReadOnly(True)
        self._log_box.setStyleSheet(
            "background-color:" + C["lg"] + "; color:" + C["lgt"] + ";"
            "font-family:Consolas; font-size:10px; border:1px solid " + C["bd"] + ";")
        self._log_box.setPlaceholderText(T("log_hint"))
        layout.addWidget(self._log_box)

        bl = QHBoxLayout()
        clr_btn = QPushButton("Clear")
        clr_btn.setStyleSheet(
            "background-color:" + C["mu"] + "; color:#FFF; font-weight:bold;"
            "font-size:10px; border:none; border-radius:3px; padding:4px 12px;")
        clr_btn.clicked.connect(self.clear_log)
        bl.addWidget(clr_btn)
        bl.addStretch()
        layout.addLayout(bl)

    def append_log(self, text):
        self._log_box.moveCursor(self._log_box.textCursor().MoveOperation.End)
        self._log_box.insertPlainText(text + "\n")
        self._log_box.moveCursor(self._log_box.textCursor().MoveOperation.End)

    def clear_log(self):
        self._log_box.clear()


# ---- Entry Point ----
def main():
    # Windows AppUserModelID MUST be set BEFORE QApplication for taskbar icon
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "ZB-WDSN.CDGLauncher")
        except Exception:
            pass
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app_icon = get_app_icon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)
    window = MainWindow()
    if not app_icon.isNull():
        window.setWindowIcon(app_icon)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()


# ---- PyInstaller Command ----
# IMPORTANT: Delete build/, dist/, and *.spec before rebuilding.
#
# Windows no-console build (NO powershell/cmd popups):
#   pyinstaller --clean --noconfirm -F -w --noconsole --windowed ^
#     --name "CDG Launcher" --icon "app_icon.ico" ^
#     --add-data "app_icon.ico;." --add-data "app_icon.png;." ^
#     --add-data "codex;codex" ^
#     scripts/launcher_pyside6.py
#
# The spec file (CDGLauncher.spec) must set console=False.


# ===================================================================
# ---- Windows helper: find PID listening on a TCP port (ctypes) ----
# ===================================================================
def _find_pid_on_port(port):
    """Find the PID of the process listening on a TCP port.
    Uses Windows IP Helper API via ctypes (no powershell/subprocess).
    Returns None if not found or on error."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class MIB_TCPROW_OWNER_PID(ctypes.Structure):
            _fields_ = [
                ("dwState", wintypes.DWORD),
                ("dwLocalAddr", wintypes.DWORD),
                ("dwLocalPort", wintypes.DWORD),
                ("dwRemoteAddr", wintypes.DWORD),
                ("dwRemotePort", wintypes.DWORD),
                ("dwOwningPid", wintypes.DWORD),
            ]

        AF_INET = 2
        TCP_TABLE_OWNER_PID_LISTENER = 4

        buf_size = wintypes.DWORD(0)
        ctypes.windll.iphlpapi.GetExtendedTcpTable(
            None, ctypes.byref(buf_size), False,
            AF_INET, TCP_TABLE_OWNER_PID_LISTENER, 0,
        )

        if buf_size.value == 0:
            return None

        buf = ctypes.create_string_buffer(buf_size.value)
        ret = ctypes.windll.iphlpapi.GetExtendedTcpTable(
            buf, ctypes.byref(buf_size), False,
            AF_INET, TCP_TABLE_OWNER_PID_LISTENER, 0,
        )
        if ret != 0:
            return None

        num_entries = ctypes.c_uint32.from_buffer(buf, 0).value
        row_array = (MIB_TCPROW_OWNER_PID * num_entries).from_buffer(buf, 4)

        target = __import__("socket").htons(port)
        for row in row_array:
            if row.dwLocalPort == target:
                return row.dwOwningPid
        return None
    except Exception:
        return None
