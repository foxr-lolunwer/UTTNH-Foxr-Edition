import json5 as json
# import math

# 属性保留小数位数配置字典
STAT_PRECISION = {
    "reliability": 3,  # 可靠性保留 3 位
    "build_cost_ic": 0,
    "convert_cost_ic": 0,
    "default": 1  # 未列出的属性默认保留 1 位
}


def format_stat_value(stat_name: str, val: float) -> str:
    """根据字典中指定的位数对属性值进行 round 格式化，去掉末尾无意义的 0"""
    precision = STAT_PRECISION.get(stat_name, STAT_PRECISION["default"])
    rounded_val = round(val, precision)
    if precision == 0 or rounded_val.is_integer():
        return str(int(rounded_val))
    return f"{rounded_val:.{precision}f}".rstrip('0').rstrip('.')


def calculate_mount_factor(mount: int, factor) -> float:
    """计算联装数衰减系数 (2 到 5)"""
    if mount <= 1:
        return 1.0
    return 1.0 + (sum(0.85 ** (k - 1) for k in range(2, mount + 1)) * factor)


def compute_stat_value(cfg: dict, mount: int, level: int, all_calculated_stats: dict) -> float:
    """通用属性数值计算核心引擎"""
    raw_base = cfg.get("base", 0)
    if isinstance(raw_base, str):
        base_val = all_calculated_stats.get(raw_base, 0.0)
    else:
        base_val = float(raw_base)

    add_factor = cfg.get("add_factor", 0.0)
    factor = cfg.get("factor", 1.0)
    val = base_val * (1.0 + (level - 1) * add_factor) * factor

    # 仅当联装数 > 1 时，才计算联装衰减与 mount_factor
    if mount > 1:
        apply_mount = cfg.get("mount", True)
        if apply_mount:
            m_factor = calculate_mount_factor(mount, cfg.get("mount_factor", 1.0))
            val *= m_factor

    return val


def generate_hoi4_script(data: dict) -> str:
    lines = ["equipment_modules = {"]

    for base_id, spec in data.items():
        category = spec.get("module_category", base_id)
        mounts = spec.get("mount", [1])
        max_level = spec.get("level", 1)
        critical_parts = spec.get("critical_parts", [])

        # 在该数据集第一个生成模块前放置不缩进的注释
        lines.append(f"  # {base_id}")

        for m in mounts:
            for l in range(1, max_level + 1):
                module_id = f"{base_id}_m{m}_l{l}"
                lines.append(f"    {module_id} = {{")
                lines.append(f"        category = {category}")

                calculated_stats = {}

                # 处理 add_stats
                if "add_stats" in spec:
                    lines.append("        add_stats = {")
                    for stat_name, cfg in spec["add_stats"].items():
                        val = compute_stat_value(cfg, m, l, calculated_stats)
                        calculated_stats[stat_name] = val
                        lines.append(f"            {stat_name} = {format_stat_value(stat_name, val)}")
                    lines.append("        }")

                # 处理 multiply_stats
                if "multiply_stats" in spec:
                    lines.append("        multiply_stats = {")
                    for stat_name, cfg in spec["multiply_stats"].items():
                        val = compute_stat_value(cfg, m, l, calculated_stats)
                        calculated_stats[stat_name] = val
                        lines.append(f"            {stat_name} = {format_stat_value(stat_name, val)}")
                    lines.append("        }")

                # 处理 can_convert_from
                if "can_convert_from" in spec:
                    conv = spec["can_convert_from"]
                    target_cat = conv.get("module_category")
                    if target_cat == "this":
                        target_cat = category

                    lines.append("        can_convert_from = {")
                    lines.append(f"            module_category = {target_cat}")

                    if "convert_cost_ic" in conv:
                        cost_cfg = conv["convert_cost_ic"]
                        val = compute_stat_value(cost_cfg, m, l, calculated_stats)
                        lines.append(f"            convert_cost_ic = {format_stat_value('convert_cost_ic', val)}")
                    lines.append("        }")

                # 处理 critical_parts
                if critical_parts:
                    parts_str = " ".join(critical_parts)
                    lines.append(f"        critical_parts = {{ {parts_str} }}")

                lines.append("    }")

    lines.append("}")
    return "\n".join(lines)


if __name__ == "__main__":
    # 示例运行：读取 in_data.json 并导出到 out_modules.txt
    import os

    # 模拟从文件加载数据
    input_file = "ship_gun.json5"
    output_file = r"out/ship_gun.txt"

    if os.path.exists(input_file):
        with open(input_file, "r", encoding="utf-8") as f:
            # 如果 json 文件带有 // 注释，请使用 json5.load(f)
            data = json.load(f)

        result_text = generate_hoi4_script(data)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result_text)
        print(f"成功导出至 {output_file}")
