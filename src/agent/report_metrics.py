# -*- coding: utf-8 -*-
"""
自动聚合评测产物，生成可直接展示的指标与报表。

输入（可通过命令行指定，亦可被 main.py 调用时以默认值传入）：
- 语义报告目录：outputs/semantic_reports/*.json  （当开启 ENABLE_SEMANTIC_VALIDATE=true 时存在）
- 运行日志：outputs/logs/semantic_smoke.log       （冒烟脚本生成，或用户自备日志）
- 预测 SQL：outputs/predictions.sql               （主流程必然生成）

输出：
- outputs/reports/summary.json  总体指标聚合（SPR/Exec/SCE/Avg Revisions/Empty-result/Disagreement 等）
- outputs/reports/details.csv   逐样本明细（index,db_id,question,sql,semantic_*,exec_*,revisions）
- outputs/reports/report.md     课堂可直接粘贴的表格与要点摘要

实现说明：
- 尽量使用标准库，避免额外依赖。
- 对缺失数据保持健壮（例如未开启语义闸门时，无 semantic_reports 也能输出最小报表）。
"""
from __future__ import annotations
import argparse
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Tuple


@dataclass
class Args:
    reports_dir: Path
    log_file: Path | None
    pred_file: Path | None
    out_dir: Path


# =============================
# 解析语义报告 JSON
# =============================

def load_semantic_reports(dir_path: Path) -> List[Dict[str, Any]]:
    """读取语义报告目录（每个样本一个 JSON）。
    返回按文件名排序后的列表，方便与日志位置大致对应。
    """
    if not dir_path.exists():
        return []
    files = sorted(dir_path.glob('*.json'))
    data: List[Dict[str, Any]] = []
    for f in files:
        try:
            data.append(json.loads(f.read_text(encoding='utf-8')))
        except Exception:
            # 单个文件异常不影响整体
            continue
    return data


# =============================
# 解析运行日志（提取执行与修订信息）
# =============================

def parse_log_info(log_file: Path) -> Dict[int, Dict[str, Any]]:
    """从控制台日志中解析逐样本的执行状态、返回行数、修订次数。
    返回：index -> {exec_status: 'ok'|'error'|None, rowcount: int|None, revisions: int|None}
    注意：解析基于中文提示关键字，若用户自改日志格式，可能需要微调正则。
    """
    info: Dict[int, Dict[str, Any]] = {}
    if not (log_file and log_file.exists()):
        return info

    text = log_file.read_text(encoding='utf-8', errors='ignore')

    # 按样本块粗分（基于 "[idx/" 标记）
    blocks = re.split(r"\n=+\n", text)
    idx_pat = re.compile(r"\[(\d+)\/(\d+)\]\s*DB:")
    ok_pat = re.compile(r"执行成功，返回\s+(\d+)\s+行")
    err_pat = re.compile(r"执行失败: ")
    rev_pat = re.compile(r"修订次数:\s*(\d+)")

    for blk in blocks:
        m = idx_pat.search(blk)
        if not m:
            continue
        idx = int(m.group(1))
        # 初始化
        info[idx] = {"exec_status": None, "rowcount": None, "revisions": None}
        # 执行成功
        okm = ok_pat.search(blk)
        if okm:
            info[idx]["exec_status"] = "ok"
            try:
                info[idx]["rowcount"] = int(okm.group(1))
            except Exception:
                info[idx]["rowcount"] = None
        # 执行失败
        if err_pat.search(blk):
            info[idx]["exec_status"] = "error"
        # 修订次数
        rvm = rev_pat.search(blk)
        if rvm:
            try:
                info[idx]["revisions"] = int(rvm.group(1))
            except Exception:
                info[idx]["revisions"] = None

    return info


# =============================
# 聚合与导出
# =============================

def compute_summary(details: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(details) if details else 0
    if total == 0:
        return {"total": 0}

    # 语义
    sem_known = [d for d in details if d.get("semantic_pass") is not None]
    spr = sum(1 for d in sem_known if d.get("semantic_pass") is True) / len(sem_known) if sem_known else None
    disagreement = sum(1 for d in sem_known if d.get("semantic_pass") is False) / len(sem_known) if sem_known else None

    # 执行
    exec_known = [d for d in details if d.get("exec_status") in {"ok", "error"}]
    exec_success = sum(1 for d in exec_known if d.get("exec_status") == "ok") / len(exec_known) if exec_known else None
    empty_result_rate = sum(1 for d in exec_known if d.get("exec_status") == "ok" and (d.get("rowcount") or 0) == 0) / len(exec_known) if exec_known else None

    # 交叉
    sce = None
    if sem_known and exec_known:
        valid = [d for d in details if (d.get("semantic_pass") is True) and (d.get("exec_status") == "ok")]
        sce = len(valid) / total

    # 修订
    rev_vals = [d.get("revisions") for d in details if isinstance(d.get("revisions"), int)]
    avg_revisions = (sum(rev_vals) / len(rev_vals)) if rev_vals else None

    return {
        "total": total,
        "spr": spr,
        "exec_success": exec_success,
        "sce": sce,
        "avg_revisions": avg_revisions,
        "empty_result_rate": empty_result_rate,
        "semantic_disagreement": disagreement,
    }


def export_details_csv(details: List[Dict[str, Any]], out_csv: Path) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "index","db_id","question","sql",
        "semantic_pass","semantic_score","semantic_reason",
        "exec_status","rowcount","revisions",
    ]
    with out_csv.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for d in details:
            row = {k: d.get(k, None) for k in fields}
            w.writerow(row)


def export_summary_json(summary: Dict[str, Any], out_json: Path) -> None:
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')


def export_report_md(details: List[Dict[str, Any]], summary: Dict[str, Any], out_md: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = []
    lines.append("# 评测报告摘要\n")
    lines.append("## 指标汇总\n")
    lines.append("```\n" + json.dumps(summary, ensure_ascii=False, indent=2) + "\n``" + "\n\n")
    lines.append("## 逐样本表格（前20条）\n")
    header = "| 样本ID | DB | pass | score | exec | rows | revisions | reason |\n|---:|---|:---:|---:|:---:|---:|---:|---|\n"
    lines.append(header)
    for d in details[:20]:
        lines.append(
            f"| {d.get('index','')} | {d.get('db_id','')} | {'✅' if d.get('semantic_pass') else '❌' if d.get('semantic_pass') is False else ''} | "
            f"{(d.get('semantic_score') if d.get('semantic_score') is not None else '')} | "
            f"{'✅' if d.get('exec_status')=='ok' else '❌' if d.get('exec_status')=='error' else ''} | "
            f"{d.get('rowcount','')} | {d.get('revisions','')} | {str(d.get('semantic_reason','')).replace('|','/')} |\n"
        )
    out_md.write_text("".join(lines), encoding='utf-8')


def make_details(sem_reports: List[Dict[str, Any]], log_info: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
    details: List[Dict[str, Any]] = []
    if not sem_reports:
        # 无语义报告时，尽量从日志补齐 index 与执行信息（问题/SQL不可得）
        for idx, li in sorted(log_info.items()):
            details.append({
                "index": idx,
                "db_id": None,
                "question": None,
                "sql": None,
                "semantic_pass": None,
                "semantic_score": None,
                "semantic_reason": None,
                "exec_status": li.get("exec_status"),
                "rowcount": li.get("rowcount"),
                "revisions": li.get("revisions"),
            })
        return details

    for rep in sem_reports:
        idx = int(rep.get("index", 0) or 0)
        li = log_info.get(idx, {})
        sem = rep.get("semantic", {})
        details.append({
            "index": idx,
            "db_id": rep.get("db_id"),
            "question": rep.get("question"),
            "sql": rep.get("sql"),
            "semantic_pass": sem.get("pass"),
            "semantic_score": sem.get("score"),
            "semantic_reason": sem.get("reason"),
            "exec_status": li.get("exec_status"),
            "rowcount": li.get("rowcount"),
            "revisions": li.get("revisions"),
        })
    # 按 index 排序
    details.sort(key=lambda x: x.get('index') or 0)
    return details


def generate_reports(args: Args) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    sem_reports = load_semantic_reports(args.reports_dir)
    log_info = parse_log_info(args.log_file) if args.log_file else {}
    details = make_details(sem_reports, log_info)
    summary = compute_summary(details)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    export_details_csv(details, args.out_dir / 'details.csv')
    export_summary_json(summary, args.out_dir / 'summary.json')
    export_report_md(details, summary, args.out_dir / 'report.md')
    return summary, details


def main():
    parser = argparse.ArgumentParser(description="Aggregate metrics and export reports.")
    parser.add_argument('--reports-dir', type=str, default='outputs/semantic_reports')
    parser.add_argument('--log-file', type=str, default='outputs/logs/semantic_smoke.log')
    parser.add_argument('--pred-file', type=str, default='outputs/predictions.sql')
    parser.add_argument('--out-dir', type=str, default='outputs/reports')
    ns = parser.parse_args()

    args = Args(
        reports_dir=Path(ns.reports_dir),
        log_file=Path(ns.log_file) if ns.log_file else None,
        pred_file=Path(ns.pred_file) if ns.pred_file else None,
        out_dir=Path(ns.out_dir),
    )

    summary, _ = generate_reports(args)
    print("[report_metrics] summary:")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
