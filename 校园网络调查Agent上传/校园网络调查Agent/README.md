# 校园网络故障调查 Agent · 初版

浏览器输入现象，DeepSeek 选择工具，Python 查询和计算模拟网络数据，最后展示假设、证据、反证、结论与建议。

**先阅读：[使用说明.md](使用说明.md)**。该文档以通俗语言介绍框架、功能、启动方法、输出文件、三组评测和限制。

## 快速运行

1. VS Code 打开本文件夹，选择可用 Python。当前配置为 `D:\anaconda\Anaconda3\python.exe`（3.12.4）。业务代码仅用标准库，复用现有解释器，不是独立环境。
2. 点击运行根目录 `main.py`，浏览器打开 http://127.0.0.1:8000/ 。
3. 在网页模型设置输入自己的 DeepSeek API Key；仅存内存，不写入项目。也可设置进程环境变量 `DEEPSEEK_API_KEY`。
4. 选择案例和配置C，点击生成调查建议；展开工具记录查看输入输出。
5. Ctrl+C停止服务。重新启动后需重新输入密钥。

命令行等效入口：`python main.py`。API、端口、模型参数都在该文件顶部。默认模型为 `deepseek-flash`，实际返回模型标识保存在 `model_calls.csv`。

## 文件

- `main.py`：统一运行入口与配置。
- `agent.py`：轻量单Agent、DeepSeek原生工具调用、Skill加载、结构校验和CSV存档。
- `tools.py`：指标查询、路径比较、接入设备/无线检查、M/M/1计算。
- `backend/main.py`：本地静态页面和异步调查接口。
- `frontend/`：深色调查工作台、示意拓扑、实时调用进度和记录下载。
- `dataset/`：八组人工模拟观测，以及仅供评测的独立标准。
- `skills/network-investigation/SKILL.md`：实际加载的专业调查方法。
- `evaluate.py`：A/B/C三组批量比较；顶部设置评价参数，默认复用已配置的本地服务。
- `plot_results.py`：从已有CSV生成SVG图，不调用模型。
- `tests/test_core.py`：无API消耗的核心检查。
- `results/`：每次调查的CSV、JSON和各轮评测结果，不覆盖旧记录。
- `历史版本/`：此前课堂规则演示代码备份；原有课堂文档和截图保留。

## 接口

- GET `/api/health`：服务与模型配置状态，不返回密钥。
- GET `/api/cases`：公开案例入口与示意拓扑，不返回评测答案。
- POST `/api/config`：仅在内存中配置密钥。
- POST `/api/diagnose`：提交 `case_id`、`symptom`、`group`，返回调查任务ID。
- GET `/api/jobs/{id}`：获取进度、真实工具记录和最终结构化结果。

## 检查与评测

点击运行 `tests/test_core.py`，或使用 `python -m unittest discover -s tests -v`。

批量比较：保持服务运行且已在网页配置密钥，再运行 `evaluate.py`。默认8案例×3组×1次，产生真实API请求；需要重复时改REPEATS。结果逐条保存CSV，失败保留。之后运行 `plot_results.py` 从CSV出图。

A获得相同原始数据，B通过工具查询和计算，C额外加载专业Skill。自动类别匹配及工具覆盖只能作为初步指标，人工任务成功/证据完整列留空待复核。开发案例结果不是独立测试集上的可靠性证明。

## 已知限制

没有真实网络测量、设备修改、多轮用户追问或完整实时拓扑；自由描述只绑定选定案例。结构和证据ID检查不能保证专业判断正确。API失败会明确报告，不以规则建议冒充模型结果。最终PDF报告、独立测试集和完整人工评价仍待后续完成。
