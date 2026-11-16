"""仅从 evaluate.py 已保存的 CSV 画图，不调用模型、不硬编码结果。"""
from pathlib import Path
from datetime import datetime
import csv
import statistics

# ===== 绘图设置 =====
ROOT=Path(__file__).resolve().parent
CSV_PATH=None  # 可填 Path('绝对路径')；None自动选择最近的 evaluation.csv


def main():
    candidates=list((ROOT/"results").glob("evaluation_*/evaluation.csv"))
    path=Path(CSV_PATH) if CSV_PATH else max(candidates,key=lambda p:p.stat().st_mtime,default=None)
    if path is None:raise SystemExit("还没有评测CSV，请先运行 evaluate.py。")
    rows=list(csv.DictReader(path.open(encoding="utf-8-sig",newline="")))
    # SVG采用标准库生成，既无绘图依赖，也不会重新执行模型。
    groups=[g for g in ("A","B","C") if any(r["group"]==g for r in rows)]
    bars=[]
    for i,g in enumerate(groups):
        rs=[r for r in rows if r["group"]==g]
        rate=statistics.mean(float(r["conclusion_match"]) for r in rs)
        sec=statistics.mean(float(r["elapsed_seconds"]) for r in rs)
        x=100+i*170;h=rate*220
        bars.append(f'<rect x="{x}" y="{290-h}" width="85" height="{h}" fill="#447c58"/><text x="{x+42}" y="{275-h}" text-anchor="middle">{rate:.1%}</text><text x="{x+42}" y="315" text-anchor="middle">{g} (n={len(rs)})</text><text x="{x+42}" y="343" text-anchor="middle">平均 {sec:.1f} 秒</text>')
    svg='<svg xmlns="http://www.w3.org/2000/svg" width="660" height="410" viewBox="0 0 660 410"><rect width="660" height="410" fill="white"/><g font-family="Microsoft YaHei, sans-serif" font-size="15" fill="#223328"><text x="35" y="35" font-size="21">三组结论类别匹配率（自动指标）</text><text x="35" y="65">失败运行计入分母；不等同于完整任务成功率</text><path d="M70 80V290H610" fill="none" stroke="#777"/>'+''.join(bars)+'<text x="35" y="390" font-size="12">数据源：同目录 evaluation.csv；开发案例上的探索性结果</text></g></svg>'
    target=path.parent/("comparison_"+datetime.now().strftime("%H%M%S")+".svg")
    target.write_text(svg,encoding="utf-8")
    print("图已保存："+str(target))


if __name__=="__main__":main()
