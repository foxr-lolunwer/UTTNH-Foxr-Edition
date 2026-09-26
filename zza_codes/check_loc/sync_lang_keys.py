import os
import re


def detect_source_language(source_dir: str) -> tuple[str, str]:
    """
    自动检测数据源文件夹（如中文）中第一个 .yml 文件的第一行语言标记。
    返回 (全标记, 语言Key)，例如 ("l_simplified_chinese:", "simplified_chinese")
    """
    for root, _, files in os.walk(source_dir):
        for file_name in files:
            if file_name.endswith(".yml"):
                file_path = os.path.join(root, file_name)
                with open(file_path, "r", encoding="utf-8-sig", errors="ignore") as f:
                    first_line = f.readline().strip()
                    if first_line.startswith("l_"):
                        # 提炼出内部的 loc_key，例如 l_simplified_chinese: -> simplified_chinese
                        loc_key = first_line.rstrip(":").replace("l_", "")
                        print(f"🌐 自动检测到数据源语言: Header='{first_line}', LocKey='{loc_key}'")
                        return first_line, loc_key

    return "l_simplified_chinese:", "simplified_chinese"  # 默认兜底语言


def parse_source_kv_map(source_dir: str) -> dict[str, str]:
    """
    预扫描并解析数据源文件夹（如中文库）下的【所有】.yml 文件，
    构建全库 Key -> Value 映射字典。
    """
    kv_map = {}
    total_files = 0
    kv_pattern = re.compile(r'^\s*([a-zA-Z0-9_.\-]+)(?::\d*)?\s*:\s*"(.*)"')

    print("🔍 正在预加载目标语言（数据源）的全局 Key-Value 映射库...")
    for root, _, files in os.walk(source_dir):
        for file_name in files:
            if file_name.endswith(".yml"):
                file_path = os.path.join(root, file_name)
                total_files += 1

                with open(file_path, "r", encoding="utf-8-sig", errors="ignore") as f:
                    lines = f.readlines()

                # 跳过第一行语言标记行，遍历提取 Key-Value
                for line in lines[1:]:
                    line_str = line.strip()
                    if not line_str or line_str.startswith("#"):
                        continue

                    if "#" in line_str:
                        line_str = line_str.split("#")[0].strip()

                    match = kv_pattern.match(line_str)
                    if match:
                        key, val = match.group(1), match.group(2)
                        kv_map[key] = val

    print(f"✅ 数据源加载完毕！共解析 {total_files} 个文件，提取到 {len(kv_map)} 个有效的翻译 Key。\n")
    return kv_map


def rename_file_for_lang(file_name: str, target_loc_key: str) -> str:
    """
    根据规则将文件名中的 _l_{loc_key}.yml 替换为目标语言后缀
    例如: FLTE_plane_designer_l_english.yml -> FLTE_plane_designer_l_simplified_chinese.yml
    """
    filename_pattern = re.compile(r'^(.*_l_)[a-zA-Z0-9_\-]+(\.yml)$')
    match = filename_pattern.match(file_name)
    if match:
        prefix = match.group(1)
        ext = match.group(2)
        return f"{prefix}{target_loc_key}{ext}"
    else:
        # 如果文件名不符合 _l_{loc_key} 标准，按原名输出
        return file_name


def sync_language_keys(template_dir: str, source_dir: str, output_dir: str):
    """
    以 template_dir (如英文) 为结构模版，从 source_dir (如中文) 匹配 Value 填入：
    1. 保持目录结构，并将文件名如 name_l_english.yml 改写为 name_l_simplified_chinese.yml。
    2. 将第一行语言声明自动替换为数据源的语言标识。
    3. 匹配到 Value 则替换；未匹配到则注释为 # FLTE code add error {key}。
    """
    os.makedirs(output_dir, exist_ok=True)
    kv_pattern = re.compile(r'^\s*([a-zA-Z0-9_.\-]+)(?::\d*)?\s*:\s*"(.*)"')

    # 1. 检测数据源语言标记
    target_lang_header, target_loc_key = detect_source_language(source_dir)

    # 2. 预加载数据源全库字典
    source_kv = parse_source_kv_map(source_dir)

    processed_files_count = 0
    total_mapped_count = 0
    total_error_count = 0

    # 3. 遍历模版文件夹
    for root, _, files in os.walk(template_dir):
        for file_name in files:
            if not file_name.endswith(".yml"):
                continue

            template_file_path = os.path.join(root, file_name)

            # 计算文件夹内的相对路径
            rel_dir = os.path.relpath(root, template_dir)

            # 核心替换 1：改写文件名为目标语言的后缀
            new_file_name = rename_file_for_lang(file_name, target_loc_key)

            if rel_dir == ".":
                output_file_path = os.path.join(output_dir, new_file_name)
                display_path = new_file_name
            else:
                output_file_path = os.path.join(output_dir, rel_dir, new_file_name)
                display_path = os.path.join(rel_dir, new_file_name)

            output_lines = []

            with open(template_file_path, "r", encoding="utf-8-sig", errors="ignore") as f:
                all_raw_lines = f.readlines()

            if not all_raw_lines:
                continue

            # 核心替换 2：第一行替换为数据源的语言标记
            output_lines.append(target_lang_header)

            file_mapped_count = 0
            file_error_count = 0

            # 从第 2 行开始扫描
            for line in all_raw_lines[1:]:
                raw_line = line.rstrip("\r\n")
                stripped = raw_line.strip()

                # 原原本本保留模版中的原注释和空行
                if not stripped or stripped.startswith("#"):
                    output_lines.append(raw_line)
                    continue

                match = kv_pattern.match(raw_line)
                if match:
                    key = match.group(1)
                    indent = raw_line[:len(raw_line) - len(raw_line.lstrip())]

                    # 判定：在目标语言字典中成功找到对应的 Value
                    if key in source_kv:
                        target_val = source_kv[key]
                        output_lines.append(f'{indent}{key}: "{target_val}"')
                        file_mapped_count += 1
                    else:
                        # 未找到对应 Value，生成错误注释行
                        output_lines.append(f"{indent}# FLTE code add error {key}")
                        file_error_count += 1
                else:
                    output_lines.append(raw_line)

            # 写出同步与重命名后的文件
            os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
            with open(output_file_path, "w", encoding="utf-8-sig", newline="\n") as f:
                f.write("\n".join(output_lines) + "\n")

            processed_files_count += 1
            total_mapped_count += file_mapped_count
            total_error_count += file_error_count
            print(
                f"📄 [已生成] {file_name} ➔ {display_path} (成功: {file_mapped_count} 处, 缺失: {file_error_count} 处)")

    print(f"\n🎉 跨语言 Key 与文件名同步完全结束！")
    print(f"   ├─ 文件名语言后缀更新为: '_l_{target_loc_key}.yml'")
    print(f"   ├─ 成功同步映射 Value: {total_mapped_count} 条")
    print(f"   └─ 缺失并标记 Error 项: {total_error_count} 条")


if __name__ == "__main__":
    # 配置路径：
    TEMPLATE_FOLDER = "./sync_temple_yml"   # 1. 结构模版文件夹（如英文）
    SOURCE_FOLDER = "./sync_shource_yml"    # 2. 数据源文件夹（如中文）
    OUTPUT_FOLDER = "./sync_synced_yml"     # 3. 输出导出的结果文件夹

    sync_language_keys(TEMPLATE_FOLDER, SOURCE_FOLDER, OUTPUT_FOLDER)
