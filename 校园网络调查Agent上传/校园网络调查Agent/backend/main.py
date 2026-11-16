"""本机 HTTP 服务；根目录 main.py 是推荐入口，本文件也可直接运行。"""
import json
import threading
import uuid
import sys
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from agent import investigate


def serve(host, port, config, default_group):
    cases = json.loads((config["dataset_dir"] / "cases.json").read_text(encoding="utf-8"))
    jobs = {}
    lock = threading.RLock()
    busy = threading.Semaphore(1)  # 避免重复点击产生大量模型请求

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(ROOT / "frontend"), **kwargs)

        def log_message(self, fmt, *args):
            pass  # 不记录请求正文、密钥或用户描述

        def send_json(self, status, data):
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == "/api/health":
                self.send_json(200, {"status": "ok", "mode": "DeepSeek 调查 Agent · 模拟数据",
                                     "model": config["model"], "configured": bool(config["api_key"]), "default_group": default_group})
            elif path == "/api/cases":
                self.send_json(200, {"cases": [{k: c[k] for k in ("id", "title", "symptom", "description", "topology")} for c in cases]})
            elif path.startswith("/api/jobs/"):
                with lock:
                    job = jobs.get(path.rsplit("/", 1)[-1])
                    self.send_json(200 if job else 404, job or {"error": "调查记录不存在"})
            elif path.startswith("/api/"):
                self.send_json(404, {"error": "接口不存在"})
            else:
                super().do_GET()

        def do_POST(self):
            if self.headers.get("Origin") not in (None, f"http://{host}:{port}", f"http://localhost:{port}"):
                self.send_json(403, {"error": "仅接受本机页面请求"})
                return
            try:
                if self.headers.get_content_type() != "application/json":
                    raise ValueError("只接受 JSON 请求")
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 16000:
                    raise ValueError("请求为空或过长")
                data = json.loads(self.rfile.read(length).decode("utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("请求应为 JSON 对象")
                path = urlsplit(self.path).path
                if path == "/api/config":
                    key = data.get("api_key")
                    if not isinstance(key, str) or not key.startswith("sk-") or len(key) > 256:
                        raise ValueError("请输入有效格式的 DeepSeek API Key")
                    with lock:
                        config["api_key"] = key.strip()
                    self.send_json(200, {"configured": True})
                    return
                if path != "/api/diagnose":
                    self.send_json(404, {"error": "接口不存在"})
                    return
                symptom = data.get("symptom")
                if not isinstance(symptom, str) or not 1 <= len(symptom.strip()) <= 2000:
                    raise ValueError("问题描述需要1至2000字")
                case = next((c for c in cases if c["id"] == data.get("case_id")), None)
                if case is None:
                    raise ValueError("请先选择一个有数据的调查案例")
                group = data.get("group", default_group)
                if group not in ("A", "B", "C"):
                    raise ValueError("未知实验配置")
                if not config["api_key"]:
                    raise ValueError("请先输入 DeepSeek API Key")
                if not busy.acquire(blocking=False):
                    self.send_json(409, {"error": "已有调查正在执行，请等待结束后重试"})
                    return
                job_id = uuid.uuid4().hex
                with lock:
                    if len(jobs) >= 32:
                        finished = next((k for k,v in jobs.items() if v["status"] != "running"), None)
                        if finished:
                            del jobs[finished]
                    jobs[job_id] = {"job_id": job_id, "status": "running", "events": []}
                    run_config = dict(config)

                def worker():
                    def emit(event):
                        with lock:
                            jobs[job_id]["events"].append(event)
                    try:
                        payload = investigate(run_config, case, symptom.strip(), group, emit)
                        with lock:
                            jobs[job_id].update(status="done", payload=payload)
                    except Exception:
                        with lock:
                            jobs[job_id].update(status="error", error="服务执行失败，请检查输出目录是否可写。")
                    finally:
                        busy.release()
                threading.Thread(target=worker, daemon=True).start()
                self.send_json(202, {"job_id": job_id})
            except (ValueError, UnicodeDecodeError) as exc:
                message = str(exc) if not isinstance(exc, json.JSONDecodeError) else "JSON 格式无效"
                self.send_json(400, {"error": message})

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"校园网络调查 Agent：http://{host}:{port}/", flush=True)
    print("模型：" + config["model"] + "；密钥" + ("已配置" if config["api_key"] else "请在网页输入"), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    from main import main
    main()
