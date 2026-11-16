"""点击运行三组对照。会真实调用 API；参数置顶，结果逐条保存 CSV。"""
from pathlib import Path
from datetime import datetime
import getpass
import json
import uuid
import time
import atexit
from urllib import request
from main import settings
from agent import investigate, write_csv

# ===== 评价设置，与模型训练无关 =====
CASE_IDS = ["C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08"]
GROUPS = ["A", "B", "C"]
REPEATS = 1  # 初次运行每组每例一次；正式评测可改为3，保留所有运行
USE_RUNNING_SERVER = True  # 推荐：先运行 main.py 并在网页配置密钥，评测复用内存配置
SERVER_URL = "http://127.0.0.1:8000"


def server_json(path, data=None):
    req=request.Request(SERVER_URL+path, data=None if data is None else json.dumps(data).encode("utf-8"),
                        headers={"Content-Type":"application/json"})
    with request.urlopen(req,timeout=30) as response:return json.load(response)


def run_case(config,case,group):
    if not USE_RUNNING_SERVER:return investigate(config,case,case["symptom"],group)
    job=server_json("/api/diagnose",dict(case_id=case["id"],symptom=case["symptom"],group=group))
    while True:
        state=server_json("/api/jobs/"+job["job_id"])
        if state["status"]=="done":return state["payload"]
        if state["status"]=="error":raise RuntimeError(state["error"])
        time.sleep(1)


def main():
    config=settings()
    if USE_RUNNING_SERVER:
        health=server_json("/api/health")
        if not health["configured"]:raise SystemExit("请先在网页中配置 DeepSeek 密钥。")
        config["model"]=health["model"]
    elif not config["api_key"]:
        config["api_key"]=getpass.getpass("请输入 DeepSeek API Key（不回显、不保存）：").strip()
    if not USE_RUNNING_SERVER and not config["api_key"]:
        raise SystemExit("未输入密钥，评测未开始。")
    cases=json.loads((config["dataset_dir"]/"cases.json").read_text(encoding="utf-8"))
    # 答案只在评测端读取，绝不传入 investigate。
    rubrics={r["case_id"]:r for r in json.loads((config["dataset_dir"]/"rubrics.json").read_text(encoding="utf-8"))}
    batch=Path(config["output_dir"])/("evaluation_"+datetime.now().strftime("%Y%m%d_%H%M%S")+"_"+uuid.uuid4().hex[:6])
    batch.mkdir(parents=True)
    (batch/"config.json").write_text(json.dumps({"model":config["model"],"temperature":config["temperature"],"case_ids":CASE_IDS,"groups":GROUPS,"repeats":REPEATS,"protocol":"v1.1-dev-not-heldout"},ensure_ascii=False,indent=2),encoding="utf-8")
    rows=[]
    batch_state={"status":"incomplete","planned_runs":len(CASE_IDS)*len(GROUPS)*REPEATS}
    def save_batch_state():
        (batch/"batch_status.json").write_text(json.dumps({**batch_state,"completed_runs":len(rows)},ensure_ascii=False,indent=2),encoding="utf-8")
    save_batch_state()
    atexit.register(save_batch_state)
    fields=["run_id","case_id","group","repeat","model","status","predicted","expected","conclusion_match","required_tool_coverage","elapsed_seconds","human_task_success","human_evidence_complete","error"]
    for case in cases:
        if case["id"] not in CASE_IDS:continue
        rule=rubrics[case["id"]]
        for group in GROUPS:
            for repeat in range(1,REPEATS+1):
                print(f"运行 {case['id']} / {group} / {repeat}",flush=True)
                p=run_case(config,case,group)
                used={e["tool"] for e in p["evidence"]}
                predicted=p["result"]["category"] if p["result"] else ""
                rows.append(dict(run_id=p["run_id"],case_id=case["id"],group=group,repeat=repeat,model=config["model"],status=p["status"],predicted=predicted,expected=rule["expected_category"],conclusion_match=int(predicted==rule["expected_category"]),required_tool_coverage="" if group=="A" else len(used&set(rule["required_tools"]))/len(rule["required_tools"]),elapsed_seconds=p["elapsed_seconds"],human_task_success="",human_evidence_complete="",error=p["error"]))
                write_csv(batch/"evaluation.csv",rows,fields)
                if p["error"] and ("密钥" in p["error"] or "余额" in p["error"]):
                    print("账号错误，已保存当前结果并停止，避免重复无效请求。")
                    return
    print("结果："+str(batch))
    batch_state["status"]="complete"
    print("自动类别匹配率不是完整任务成功率；人工复核列留空，不能当作已经评过分。")


if __name__=="__main__":main()
