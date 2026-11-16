"""不消耗 API 的检查：公式、边界、案例一致性和 Agent 工具回传。"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import calculate_queue_delay, ToolSession
from agent import investigate, validate_result
from main import settings


class CoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads((ROOT / "dataset/cases.json").read_text(encoding="utf-8"))

    def test_queue_formula_and_boundaries(self):
        self.assertAlmostEqual(calculate_queue_delay(950,1000)["queue_delay_ms"],19)
        self.assertFalse(calculate_queue_delay(1000,1000)["applicable"])
        self.assertFalse(calculate_queue_delay(400,1000,False)["applicable"])
        for x in (-1, float("nan"), True):
            with self.assertRaises(ValueError):
                calculate_queue_delay(x,1000)

    def test_tools_reject_guessed_parameters(self):
        session=ToolSession(self.cases[0])
        args=dict(link_id="L1",arrival_pps=950,service_pps=1000)
        with self.assertRaises(ValueError):session.call("calculate_queue_delay",args)
        session.call("get_link_metrics",{"link_id":"L1"})
        with self.assertRaises(ValueError):session.call("calculate_queue_delay",{**args,"arrival_pps":900})
        self.assertEqual(session.call("calculate_queue_delay",args)["data"]["queue_delay_ms"],19)
        with self.assertRaises(ValueError):session.call("read_file",{})

    def test_missing_data_not_zero(self):
        s=ToolSession(self.cases[6])
        self.assertIsNone(s.call("get_link_metrics",{"link_id":"L1"})["data"]["current"]["queue_packets"])
        self.assertIsNone(s.call("compare_paths",{})["data"]["changed"])

    def test_case_paths_match_topology(self):
        for c in self.cases:
            self.assertNotIn("expected_category",c)
            links={x["id"]:x for x in c["topology"]["links"]}
            for period in ("baseline","current"):
                path=c["paths"][period]
                if path is None:continue
                ids=c["paths"][period+"_links"]
                self.assertEqual(len(ids),len(path)-1)
                for i,key in enumerate(ids):
                    self.assertEqual((links[key]["from"],links[key]["to"]),tuple(path[i:i+2]))

    def test_real_dispatch_roundtrip_with_fake_model(self):
        # 模拟的只有外部模型响应，工具仍实际运行。在线联调另行保存。
        finish={"category":"congestion","summary":"模拟数据支持拥塞迹象", "hypotheses":[
            {"name":"拥塞","status":"supported","reason":"队列增加","supporting_evidence":["E001"],"opposing_evidence":[]},
            {"name":"路径变化","status":"weakened","reason":"已测去程相同","supporting_evidence":[],"opposing_evidence":["E002"]}],
            "recommendations":["复核队列"],"limitations":["仅模拟数据"]}
        def tc(i,name,args):return {"id":i,"type":"function","function":{"name":name,"arguments":json.dumps(args,ensure_ascii=False)}}
        responses=[({"role":"assistant","content":None,"tool_calls":[tc("1","get_link_metrics",{"link_id":"L1"}),tc("2","compare_paths",{})]}, {}, "test"),
                   ({"role":"assistant","content":None,"tool_calls":[tc("3","finish_investigation",finish)]},{},"test")]
        with tempfile.TemporaryDirectory() as tmp,patch("agent.chat",side_effect=responses) as model:
            config=settings();config["output_dir"]=Path(tmp)
            result=investigate(config,self.cases[0],"测试","C")
            self.assertEqual(result["status"],"ok")
            self.assertEqual(len(result["evidence"]),2)
            self.assertTrue(any(x.get("role")=="tool" for x in model.call_args[0][1]))
            self.assertTrue((Path(tmp)/result["run_id"]/"tools.csv").exists())
        finish["hypotheses"][0]["supporting_evidence"]=["E999"]
        with self.assertRaises(ValueError):validate_result(finish,[],"C")


if __name__ == "__main__":
    unittest.main()
