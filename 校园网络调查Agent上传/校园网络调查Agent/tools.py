"""确定性的网络工具。工具查询当前案例，绝不读取评测答案。"""
import copy
import math


def spec(name, description, properties=None, required=None):
    return {"type": "function", "function": {"name": name, "description": description,
            "parameters": {"type": "object", "properties": properties or {},
                           "required": required or [], "additionalProperties": False}}}


TOOL_SPECS = [
    spec("get_link_metrics", "查询链路基线/异常指标、容量及排队模型输入；缺失字段为 null。",
         {"link_id": {"type": "string", "enum": ["L1", "L2", "L3", "L4"]}}, ["link_id"]),
    spec("compare_paths", "比较故障前后同一端点间的有序路径、方向与可用性，检查变化。"),
    spec("inspect_access", "读取接入交换机端口错误与无线/有线对照测量，可检查设备及无线因素。"),
    spec("calculate_queue_delay", "校验已查询模型参数及适用条件，计算单个队列的 M/M/1 Wq/W；不能当作端到端 RTT。",
         {"link_id": {"type": "string", "enum": ["L1", "L2", "L3", "L4"]},
          "arrival_pps": {"type": "number"}, "service_pps": {"type": "number"}},
         ["link_id", "arrival_pps", "service_pps"]),
]


def calculate_queue_delay(arrival_pps, service_pps, assumptions_met=True):
    """λ、μ 单位为包/秒。Wq=λ/[μ(μ-λ)] 秒；只计算单服务器单队列。"""
    for x in (arrival_pps, service_pps):
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
            raise ValueError("到达率和服务率必须为有限数字，单位为包/秒")
    if arrival_pps < 0 or service_pps <= 0:
        raise ValueError("到达率必须非负，服务率必须大于零")
    if not assumptions_met:
        return {"applicable": False, "reason": "该模拟案例未满足泊松到达、指数服务与稳态等 M/M/1 假设，拒绝套用"}
    if arrival_pps >= service_pps:
        return {"applicable": False, "reason": "λ≥μ，不存在有限的稳态平均排队时延"}
    return {"applicable": True, "rho": arrival_pps / service_pps,
            "queue_delay_ms": 1000 * arrival_pps / (service_pps * (service_pps - arrival_pps)),
            "system_delay_ms": 1000 / (service_pps - arrival_pps),
            "scope": "单个队列的理论平均值；不能直接替代端到端 RTT，也不能单独证明根因"}


class ToolSession:
    """绑定一份案例，只允许白名单工具；逐次给真实返回结果分配证据编号。"""
    def __init__(self, case):
        self.case = copy.deepcopy(case)
        self.evidence = []
        self.metrics_read = set()

    def call(self, name, args):
        if not isinstance(args, dict):
            raise ValueError("参数应为 JSON 对象")
        schema = next((s["function"]["parameters"] for s in TOOL_SPECS if s["function"]["name"] == name), None)
        if schema is None:
            raise ValueError("工具不在白名单中")
        if set(args) - set(schema["properties"]) or set(schema["required"]) - set(args):
            raise ValueError("工具参数缺失或包含未定义字段")
        if name == "get_link_metrics":
            link = args["link_id"]
            if link not in self.case["links"]:
                raise ValueError("链路不存在")
            result = {"link_id": link, **self.case["links"][link]}
            self.metrics_read.add(link)
        elif name == "compare_paths":
            p = self.case["paths"]
            known = p["baseline"] is not None and p["current"] is not None
            result = {**p, "changed": (p["baseline"] != p["current"]) if known else None,
                      "scope": "只记录已观测方向的路径，未观测反向路径不能推断为不变"}
        elif name == "inspect_access":
            result = self.case["access"]
        else:
            link = args["link_id"]
            if link not in self.metrics_read:
                raise ValueError("请先查询该链路指标，不能凭空提供参数")
            model = self.case["links"][link].get("queue_model")
            if model is None:
                raise ValueError("缺少排队模型参数")
            if args["arrival_pps"] != model["arrival_pps"] or args["service_pps"] != model["service_pps"]:
                raise ValueError("参数与已查询记录不一致，不允许编造输入")
            result = calculate_queue_delay(args["arrival_pps"], args["service_pps"], model["assumptions_met"])
        item = {"evidence_id": f"E{len(self.evidence)+1:03d}", "tool": name,
                "arguments": copy.deepcopy(args), "data": copy.deepcopy(result), "source": "人工构造的模拟校园网络数据"}
        self.evidence.append(item)
        return item
