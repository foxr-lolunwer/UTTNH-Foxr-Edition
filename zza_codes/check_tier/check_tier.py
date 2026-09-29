import re
from typing import List, Dict, Any


def validate_tier_data(file_content: str) -> List[Dict[str, Any]]:
    """
    检查数据结构的合法性并返回报告列表
    """
    lines = file_content.splitlines()
    reports = []

    # 匹配 Header: y = @Tier{n}_{?1} } }
    header_regex = re.compile(r'y\s*=\s*@Tier(\d)_([^\s{}]+)\s*\}\s*\}')
    # 匹配 Dependency: FLTE_tech_tier_{?2}_{n} = {v}
    dep_item_regex = re.compile(r'FLTE_tech_tier_([^\s{}]+)_(\d+)\s*=\s*(\d+)')

    i = 0
    while i < len(lines):
        line = lines[i]
        header_match = header_regex.search(line)

        if header_match:
            start_line = i + 1  # 1-based 行号
            tier_n = header_match.group(1)
            str_p1 = header_match.group(2)

            # 向上/下提取包含 dependencies 的完整区块
            dep_block_text = ""
            block_end_line = start_line

            # 读取当前行及后续行直到 dependencies 块闭合
            bracket_balance = 0
            found_dep = False
            for j in range(i, min(i + 15, len(lines))):  # 假设一个结构在15行以内
                curr_line = lines[j]
                dep_block_text += curr_line + "\n"

                if "dependencies" in curr_line:
                    found_dep = True
                if found_dep:
                    bracket_balance += curr_line.count('{') - curr_line.count('}')
                    if bracket_balance <= 0 and '}' in curr_line:
                        block_end_line = j + 1
                        break

            # 校验 dependencies 中的所有匹配项
            dep_matches = dep_item_regex.findall(dep_block_text)
            errors = []

            if not dep_matches:
                errors.append("未在 dependencies 中找到任何 FLTE_tech_tier 结构")
            else:
                for match_idx, (str_p2, dep_n, val_v) in enumerate(dep_matches, 1):
                    # 规则1: {n} 必须为单个数字且与 Header 一致
                    if dep_n != tier_n:
                        errors.append(f"第 {match_idx} 个依赖项的 {{n}} 不一致: 期望 '{tier_n}'，实际为 '{dep_n}'")

                    # 规则2: {v} 必须等于 1
                    if val_v != "1":
                        errors.append(f"第 {match_idx} 个依赖项的 {{v}} 不合法: 期望 '1'，实际为 '{val_v}'")

            reports.append({
                "line": start_line,
                "tier_n": tier_n,
                "p1": str_p1,
                "dep_count": len(dep_matches),
                "is_valid": len(errors) == 0,
                "errors": errors
            })
        i += 1

    return reports


# ================= 示例测试与使用方法 =================
if __name__ == "__main__":
    with open(
            r"E:\Documents\Paradox Interactive\Hearts of Iron IV\mod\UTTNH Foxr Edition\common\technologies\zz_FLTE_vehc.txt",
            "r", encoding="utf-8") as f:
        results = validate_tier_data(f.read())

        print(f"{'行号':<6} | {'状态':<6} | {'Tier(n)':<8} | {'错误信息'}")
        print("-" * 60)
        for r in results:
            status = "合法" if r["is_valid"] else "非法"
            err_msg = "; ".join(r["errors"]) if r["errors"] else "无"
            print(f"L{r['line']:<5} | {status:<6} | {r['tier_n']:<8} | {err_msg}")
