import os
import re


def parse_single_yml(file_path: str) -> dict[str, str]:
    """
    解析单个 YML 本地化文件：
    1. 强制忽略第一行（语言标记行）
    2. 忽略 # 注释
    3. 提取所有的 key 和 value
    """
    kv_map = {}
    if not os.path.exists(file_path):
        return kv_map

    kv_pattern = re.compile(r'^\s*([a-zA-Z0-9_.\-]+)(?::\d*)?\s*:\s*"(.*)"')

    with open(file_path, "r", encoding="utf-8-sig", errors="ignore") as f:
        lines = f.readlines()

    # 第一行强制略过（通常为 l_simplified_chinese:）
    for line in lines[1:]:
        line_str = line.strip()
        # 忽略以 # 开头的纯注释行或空行
        if not line_str or line_str.startswith("#"):
            continue

        # 剥离行内尾随注释 #
        if "#" in line_str:
            line_str = line_str.split("#")[0].strip()

        match = kv_pattern.match(line_str)
        if match:
            key, value = match.group(1), match.group(2)
            kv_map[key] = value

    return kv_map


def build_global_ref_dict(ref_dir: str) -> dict[str, str]:
    """
    一口气扫描并解析参照文件夹下的【所有】.yml 文件，汇总为一个全局字典
    """
    global_kv = {}
    total_files = 0

    print("🔍 正在一次性预加载并构建【全局参照 Key 数据库】...")
    for root, _, files in os.walk(ref_dir):
        for file_name in files:
            if file_name.endswith(".yml"):
                file_path = os.path.join(root, file_name)
                file_kv = parse_single_yml(file_path)
                global_kv.update(file_kv)
                total_files += 1

    print(f"✅ 全局参照库加载完毕！共解析 {total_files} 个参照文件，提取到 {len(global_kv)} 个唯一的 Key。\n")
    return global_kv


def process_yml_directories(ref_dir: str, target_dir: str, output_dir: str):
    """
    基于全局字典执行比对与分流导出
    """
    os.makedirs(output_dir, exist_ok=True)
    replace_dir = os.path.join(output_dir, "replace")

    kv_pattern = re.compile(r'^\s*([a-zA-Z0-9_.\-]+)(?::\d*)?\s*:\s*"(.*)"')

    # 1. 一口气预加载全部参照库
    global_ref_kv = build_global_ref_dict(ref_dir)

    processed_files_count = 0
    total_deleted_count = 0
    total_replaced_count = 0

    # 2. 遍历待处理文件夹
    for root, _, files in os.walk(target_dir):
        for file_name in files:
            if not file_name.endswith(".yml"):
                continue

            target_file_path = os.path.join(root, file_name)
            rel_path = os.path.relpath(target_file_path, target_dir)
            output_file_path = os.path.join(output_dir, rel_path)

            output_lines = []
            replace_lines = []

            with open(target_file_path, "r", encoding="utf-8-sig", errors="ignore") as f:
                all_raw_lines = f.readlines()

            if not all_raw_lines:
                continue

            # 捕获并保留第一行原样输出（语言声明头）
            first_line_header = all_raw_lines[0].rstrip("\r\n")
            output_lines.append(first_line_header)

            file_del_count = 0
            file_rep_count = 0

            # 从第 2 行开始逐行扫描（第一行略过解析）
            for line in all_raw_lines[1:]:
                raw_line = line.rstrip("\r\n")
                stripped = raw_line.strip()

                # 纯注释行与空行原样保留在主导出文件中
                if not stripped or stripped.startswith("#"):
                    output_lines.append(raw_line)
                    continue

                match = kv_pattern.match(raw_line)
                if match:
                    key, val = match.group(1), match.group(2)
                    indent = raw_line[:len(raw_line) - len(raw_line.lstrip())]

                    # 判定 1：Key 存在且 Value 相同 -> 原文件注释为 # FLTE code del {key}
                    if key in global_ref_kv and global_ref_kv[key] == val:
                        output_lines.append(f"{indent}# FLTE code del {key}")
                        file_del_count += 1

                    # 判定 2：Key 存在但 Value 不同 -> 原文件注释为 # FLTE code replace {key}，并提取至 replace/R_{old_name}
                    elif key in global_ref_kv and global_ref_kv[key] != val:
                        output_lines.append(f"{indent}# FLTE code replace {key}")
                        replace_lines.append(raw_line)
                        file_rep_count += 1

                    # 判定 3：Key 完全不存在 -> 原样保留
                    else:
                        output_lines.append(raw_line)
                else:
                    output_lines.append(raw_line)

            # 3. 写出主查重导出文件
            os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
            with open(output_file_path, "w", encoding="utf-8", newline="\n") as f:
                f.write("\n".join(output_lines) + "\n")

            # 4. 如果有 Value 不同的条目，导出至 replace/R_{old_name}
            if replace_lines:
                os.makedirs(replace_dir, exist_ok=True)
                replace_file_name = f"R_{file_name}"
                replace_file_path = os.path.join(replace_dir, replace_file_name)

                # 新文件保留并带上原第一行的语言声明
                content_to_write = [first_line_header] + replace_lines
                with open(replace_file_path, "w", encoding="utf-8", newline="\n") as f:
                    f.write("\n".join(content_to_write) + "\n")

            processed_files_count += 1
            total_deleted_count += file_del_count
            total_replaced_count += file_rep_count
            print(
                f"📄 [已处理] {rel_path} -> del注释: {file_del_count} 处, replace注释: {file_rep_count} 处 (已提取至 replace/R_{file_name})")

    print(f"\n🎉 全局交叉比对完成！共处理 {processed_files_count} 个待处理文件。")
    print(f"   ├─ 累积 del 注释项: {total_deleted_count} 条")
    print(f"   └─ 累积 replace 注释与提取项: {total_replaced_count} 条 (存放于 '{replace_dir}')")


if __name__ == "__main__":
    REF_FOLDER = "./check_reference_yml"  # 1. 参照文件夹（全局预加载）
    TARGET_FOLDER = "./check_target_yml"  # 2. 待处理文件夹
    OUTPUT_FOLDER = "./check_output_yml"  # 3. 导出文件夹

    process_yml_directories(REF_FOLDER, TARGET_FOLDER, OUTPUT_FOLDER)
