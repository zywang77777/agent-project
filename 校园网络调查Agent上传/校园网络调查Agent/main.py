"""VS Code 运行入口：启动网页服务；参数均在此处集中修改。"""
from pathlib import Path
import os

# ===== 服务与模型设置（没有训练过程） =====
HOST = "127.0.0.1"                # 仅在本机使用
PORT = 8000                       # 浏览器访问端口
MODEL = "deepseek-flash"           # DeepSeek 模型名称，可按账号支持情况修改
API_BASE = "https://api.deepseek.com"
REQUEST_TIMEOUT = 90              # 单次模型请求等待秒数
MAX_ROUNDS = 8                    # 每次调查最多调用模型的轮数
MAX_TOOL_CALLS = 16               # 每次调查最多执行工具的次数
TEMPERATURE = 0                   # 尽量减少输出波动，仍不保证完全相同
DEFAULT_GROUP = "C"               # A=直接 LLM，B=Agent+Tools，C=再加 Skill
ROOT = Path(__file__).resolve().parent
DATASET_DIR = ROOT / "dataset"
OUTPUT_DIR = ROOT / "results"     # 每次调查自动创建新目录，保留历史记录
SKILL_FILE = ROOT / "skills" / "network-investigation" / "SKILL.md"


def settings():
    """供服务和评测共用；密钥只从进程环境或网页输入读取。"""
    return dict(model=MODEL, api_base=API_BASE, timeout=REQUEST_TIMEOUT,
                max_rounds=MAX_ROUNDS, max_tools=MAX_TOOL_CALLS,
                temperature=TEMPERATURE, dataset_dir=DATASET_DIR,
                output_dir=OUTPUT_DIR, skill_file=SKILL_FILE,
                api_key=os.environ.get("DEEPSEEK_API_KEY", "").strip())


def main():
    from backend.main import serve
    serve(HOST, PORT, settings(), DEFAULT_GROUP)


if __name__ == "__main__":
    main()
