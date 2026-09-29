import os
import json5
from pathlib import Path


class HOI4ModuleExporter:
    def __init__(self, data):
        self.data = data
        self.output_lines = []

    def calculate_value(self, val_obj, mount, level, context_vals):
        """解析数值对象，处理动态公式、自我引用与自定义小数保留"""
        if isinstance(val_obj, (int, float)):
            return round(val_obj, 3) if isinstance(val_obj, float) else val_obj

        base = val_obj.get("base", 0)
        # 处理自我引用
        if isinstance(base, str):
            if base in context_vals:
                base = context_vals.get(base, 0)
            else:
                print(f"⚠️ 警告: 自我引用解析失败，未在 add_stats 中找到属性 '{base}'，已默认设为 1。")
                base = 1

        mnt_val = mount if mount is not None else 1
        lvl_val = level if level is not None else 1

        add_factor = val_obj.get("add_factor", 0.0)
        mount_factor = val_obj.get("mount_factor", 0.0)
        factor = val_obj.get("factor", 1.0)

        # 计算公式：
        # add_factor 仅随 level 提升生效 (level - 1)
        # mount_factor 仅随 mount 提升生效 (mount - 1)
        # 以基准值做底，叠加等级和炮塔数量的影响，最后乘全局系数
        calc_val = base * (1 + add_factor * (lvl_val - 1)) * (1 + mount_factor * (mnt_val - 1)) * factor

        round_digits = val_obj.get("round", 3)
        if round_digits <= 0:
            return int(round(calc_val, 0))
        return round(calc_val, round_digits)

    def dict_to_pdx(self, data_dict, indent=1):
        """将 Python 字典递归转换为 Paradox 脚本格式"""
        lines = []
        tab = "\t" * indent
        for key, value in data_dict.items():
            if isinstance(value, dict):
                lines.append(f"{tab}{key} = {{")
                lines.append(self.dict_to_pdx(value, indent + 1))
                lines.append(f"{tab}}}")
            elif isinstance(value, list):
                if all(isinstance(x, str) for x in value):
                    lines.append(f"{tab}{key} = {{ " + " ".join(value) + " }")
                else:
                    for item in value:
                        lines.append(f"{tab}{key} = {item}")
            else:
                v_str = "yes" if isinstance(value, bool) and value else (
                    "no" if isinstance(value, bool) else str(value))
                lines.append(f"{tab}{key} = {v_str}")
        return "\n".join(lines)

    def generate(self):
        self.output_lines.append("equipment_modules = {")

        for module_base_id, config in self.data.items():
            # 仅打印一次注释
            module_category = config.get("module_category", module_base_id)
            self.output_lines.append(f"\t# {module_category}")

            # 获取 mount 列表
            mounts = config.get("mount", [None])
            if not isinstance(mounts, list):
                mounts = [mounts]

            # 解析 level 逻辑 (大于1的整数代表1至n级，1或不填代表无等级)
            level_cfg = config.get("level", 1)
            if isinstance(level_cfg, int) and level_cfg > 1:
                levels = list(range(1, level_cfg + 1))
            else:
                levels = [None]

            # 双重循环处理 level 和 mount 的组合
            for lvl in levels:
                for mnt in mounts:
                    # 动态构建 module_id
                    module_id = module_base_id
                    if mnt is not None:
                        module_id += f"_m{mnt}"
                    if lvl is not None:
                        module_id += f"_l{lvl}"

                    pdx_module = {}
                    context_vals = {}

                    # 填入元数据
                    for meta_key in ["category", "gui_category", "parent", "abbreviation", "gfx", "sfx"]:
                        if meta_key in config:
                            pdx_module[meta_key] = config[meta_key]

                    # 属性修饰区块计算
                    for stat_block in ["add_stats", "multiply_stats", "add_average_stats"]:
                        if stat_block in config:
                            pdx_module[stat_block] = {}
                            for stat_key, stat_val in config[stat_block].items():
                                val = self.calculate_value(stat_val, mnt, lvl, context_vals)
                                context_vals[stat_key] = val
                                pdx_module[stat_block][stat_key] = val

                    # 改装逻辑
                    if "can_convert_from" in config:
                        conv_cfg = config["can_convert_from"]
                        conv_block = {}

                        if "module" in conv_cfg:
                            conv_block["module"] = module_id if conv_cfg["module"] else conv_cfg["module"]

                        if "module_category" in conv_cfg:
                            conv_block["module_category"] = module_category if conv_cfg["module_category"] else conv_cfg["module_category"]

                        if "convert_cost_ic" in conv_cfg:
                            use_mount_scale = conv_cfg["convert_cost_ic"].get("mount", True)
                            mock_mount = mnt if use_mount_scale else 1
                            conv_block["convert_cost_ic"] = self.calculate_value(
                                conv_cfg["convert_cost_ic"], mock_mount, lvl, context_vals
                            )
                        pdx_module["can_convert_from"] = conv_block

                    # 独立成本与消耗计算
                    for cost_key in ["dismantle_cost_ic", "manpower"]:
                        if cost_key in config:
                            val = self.calculate_value(config[cost_key], mnt, lvl, context_vals)
                            pdx_module[cost_key] = val

                    for meta_key in ["critical_parts", "forbid_module_categories", "allowed_module_categories"]:
                        if meta_key in config:
                            pdx_module[meta_key] = config[meta_key]

                    # 组装并追加输出
                    self.output_lines.append(f"\t{module_id} = {{")
                    self.output_lines.append(self.dict_to_pdx(pdx_module, indent=2))
                    self.output_lines.append("\t}")

        self.output_lines.append("}")
        return "\n".join(self.output_lines)


def batch_export_modules(json5_file_paths, output_folder):
    """批量读取 JSON5 并导出同名 txt 到目标文件夹"""
    os.makedirs(output_folder, exist_ok=True)

    for file_path in json5_file_paths:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json5.load(f)

            exporter = HOI4ModuleExporter(data)
            pdx_content = exporter.generate()

            base_name = Path(file_path).stem
            output_path = os.path.join(output_folder, f"{base_name}.txt")

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(pdx_content)

            print(f"✅ 成功导出: {output_path}")

        except Exception as e:
            print(f"❌ 导出失败 {file_path}: {str(e)}")


# 你可以通过调用 batch_export_modules(['路径1.json5', ...], '输出目录') 来执行处理
# ==========================================
# 运行配置区
# ==========================================
if __name__ == "__main__":
    # 定义输入的 JSON5 文件列表
    INPUT_JSON5_FILES = [
        "guns.json5",
        "fixed_slot.json5",
        # "data/ca_guns.json5",
        # "data/dd_torpedoes.json5"
    ]

    # 定义输出的目标文件夹
    OUTPUT_FOLDER = "out"

    # 执行批量导出
    batch_export_modules(INPUT_JSON5_FILES, OUTPUT_FOLDER)
