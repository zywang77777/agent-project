# 后端HLD：DeepSeek工具调用初版

本文件描述2026年11月15日实现的版本。根目录原有HLD属于课堂规则演示阶段，设计范围以本文件及实际代码为准。

## 结构

浏览器通过同源HTTP访问Python标准库服务，POST提交调查后获得job_id，再轮询进度。服务最多并发一份调查。每份调查绑定一组模拟网络观测，独立创建工具会话、证据编号和输出目录。

Agent通过HTTPS调用DeepSeek Chat Completions原生工具接口。模型提出function调用，Python校验工具名和参数、执行工具，再用tool消息把结果交回模型。达到有效结论或轮数上限后结束；错误不会静默转成规则建议。

## 模型、Tool与Skill

采用一个轻量自实现Agent，无第三方Agent框架。Python负责确定性计算、输入校验与文件保存，模型负责选择查询、组织候选原因与解释证据。C组每次实际读取专业SKILL.md，B组不读取；二者共用基础输出规则。A组直接获得同范围的原始数据，没有Python工具或专业Skill。

工具包括get_link_metrics、compare_paths、inspect_access、calculate_queue_delay。网络工具只访问绑定案例，不能任意访问文件、网络或设备。队列计算要求先读取链路，输入与观测记录一致，且满足稳定性和假设条件；否则返回不适用或参数错误。

## 接口

| 接口 | 请求/响应 |
| --- | --- |
| GET /api/health | 服务状态、模型名称、是否配置密钥 |
| GET /api/cases | 八组公开案例与示意拓扑，不含评测标准 |
| POST /api/config | JSON api_key；仅写内存，响应不回传密钥 |
| POST /api/diagnose | JSON case_id、symptom、group；202返回job_id，忙碌时409 |
| GET /api/jobs/{id} | running/done/error、事件、工具返回、最终结果 |

## 输出与验证

最终结果包含category、summary、至少两个hypotheses、recommendations和limitations。假设含状态、理由、支持与反对证据编号。B/C引用实际工具结果的E编号，A引用直接提供原始数据的R编号，不把A的原始数据标记成真实工具调用。

程序验证JSON结构、类别枚举、证据ID存在性和B/C至少两种工具。格式错误给模型明确反馈以纠正。它不验证自然语言全部专业推断是否成立，因此仍需独立评分。

每次保存run.csv、tools.csv、model_calls.csv及完整result.json；新增的公开config.json记录参数与数据/提示词摘要，不含密钥。输出目录带时间与随机后缀，保留历史版本和失败运行。

## 边界

仅监听127.0.0.1，面向本机课程使用；JSON和同源检查限制网页配置入口。无生产用户鉴权、数据库、真实设备采集、自动配置更改或恢复未完成任务功能。任务在进程内运行，关闭服务会中断正在执行的调查。

评测答案只由evaluate.py读取，Agent不加载rubrics.json。当前案例是公开开发集，初次三组结果用于探索与联调，不能替代独立测试集、多次重复和人工证据复核。
