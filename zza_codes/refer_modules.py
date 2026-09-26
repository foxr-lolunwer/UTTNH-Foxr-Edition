import os
import re
import pprint


# ===================================================================
# 工具：标识符正则（所有 key 命名都遵循此规则）
# ===================================================================
IDENT = r'[a-zA-Z0-9_\-]+'


def clean_and_merge_file(file_path):
    """
    第一步：彻底清洗文件内容（仿 codes.py 风格）
    1. 逐行剥离所有 # 及其后面的注释
    2. 将整张表压缩合并为一行，用单个空格安全连接，彻底干掉所有换行干扰
    """
    cleaned_lines = []
    with open(file_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
        for line in f:
            if '#' in line:
                line = line.split('#')[0]
            cleaned_lines.append(line.strip())

    full_text = " ".join(cleaned_lines)
    full_text = re.sub(r'\s+', ' ', full_text)
    return full_text


def extract_balanced_brace(text, open_pos):
    """
    从 text[open_pos] 的 '{' 开始，用栈式匹配找到对应的闭合 '}' 的位置。
    返回 (inner_start, inner_end) — inner_content = text[inner_start:inner_end]
    如果找不到匹配的闭合括号，返回 None。
    """
    if open_pos >= len(text) or text[open_pos] != '{':
        return None
    brace_count = 1
    pos = open_pos + 1
    while pos < len(text) and brace_count > 0:
        if text[pos] == '{':
            brace_count += 1
        elif text[pos] == '}':
            brace_count -= 1
        if brace_count > 0:
            pos += 1
    if brace_count != 0:
        return None  # 括号不匹配
    return (open_pos + 1, pos)  # inner_start 是 '{' 后一位，inner_end 是 '}' 位置


def parse_block_to_dict(block_text):
    """
    仿 codes.py 的递归解析：把 "key = value" 或 "key = { ... }" 的块解析为 dict。
    值如果是花括号块，递归调用自身；否则（字符串/数字）作为普通值存储。
    支持：带引号字符串、数字、标识符、多层嵌套花括号。
    """
    data = {}
    block_text = block_text.strip()
    pos = 0
    text_len = len(block_text)

    while pos < text_len:
        # 跳过空白
        while pos < text_len and block_text[pos] in ' \t':
            pos += 1
        if pos >= text_len:
            break

        # 匹配 key = ...（key 必须是标识符）
        m = re.match(r'(' + IDENT + r')\s*=\s*', block_text[pos:])
        if not m:
            # 不是 key = 结构，跳过到下一个可能的 key 起点
            # 这种情况通常是残留的无键 token，直接跳过一个字符继续
            pos += 1
            continue

        key = m.group(1)
        pos += m.end()  # 推进到 '=' 后的第一个非空格字符位置

        if pos >= text_len:
            data[key] = ''
            break

        # 分两种情况：值是花括号块 还是 普通值
        if block_text[pos] == '{':
            # —— 情况 A：值是花括号块 ——
            brace_range = extract_balanced_brace(block_text, pos)
            if brace_range is None:
                data[key] = {}
                break
            inner_start, inner_end = brace_range
            inner_content = block_text[inner_start:inner_end].strip()
            if inner_content:
                data[key] = parse_block_to_dict(inner_content)
            else:
                data[key] = {}
            pos = inner_end + 1  # 跳到 '}' 之后
        else:
            # —— 情况 B：值是普通 token ——
            # 尝试匹配带引号字符串
            if block_text[pos] == '"':
                qm = re.match(r'"([^"]*)"', block_text[pos:])
                if qm:
                    data[key] = qm.group(1)
                    pos += qm.end()
                    continue
            # 否则匹配一个连续非空白非花括号 token（数字/标识符）
            tm = re.match(r'([^ \t{}]+)', block_text[pos:])
            if tm:
                data[key] = tm.group(1)
                pos += tm.end()
            else:
                data[key] = ''
                pos += 1

    return data


def extract_modules_folder(folder_path):
    """
    主控流程（仿 codes.py 风格）：遍历指定文件夹
    1. 清洗+合并为单行
    2. 定位 equipment_modules = { ... } 顶层块
    3. 遍历提取每一个 item_id = { ... } 模块条目
    4. 对每个模块内部用 parse_block_to_dict 递归解析
    """
    if not os.path.exists(folder_path):
        print(f"[错误] 路径不存在: {folder_path}")
        return {}

    all_modules = {}
    print(f"开始扫描文件夹: {folder_path} (严格执行单行合并后匹配机制)...")

    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)

        if os.path.isdir(file_path) or not filename.endswith(('.txt', '.asset')):
            continue

        print(f" 📄 正在清洗并合并文件: {filename}")
        file_text = clean_and_merge_file(file_path)

        # —— 定位顶层 equipment_modules = { ... } ——
        root_m = re.search(r'equipment_modules\s*=\s*\{', file_text)
        if not root_m:
            continue

        open_brace_at = root_m.end() - 1  # '{' 的位置
        brace_range = extract_balanced_brace(file_text, open_brace_at)
        if brace_range is None:
            print(f"   ⚠️ equipment_modules 顶层花括号不匹配，跳过文件: {filename}")
            continue
        inner_start, inner_end = brace_range
        modules_content = file_text[inner_start:inner_end].strip()

        # —— 从顶层内容中提取每一个 item_id = { ... } 块 ——
        scan_pos = 0
        c_len = len(modules_content)
        item_header_re = re.compile(r'(' + IDENT + r')\s*=\s*\{')

        while scan_pos < c_len:
            # 跳过空白
            while scan_pos < c_len and modules_content[scan_pos] in ' \t':
                scan_pos += 1
            if scan_pos >= c_len:
                break

            # 尝试匹配 "item_id = {" 起始模式
            hm = item_header_re.match(modules_content, scan_pos)
            if not hm:
                # 跳过一个非关键 token（可能是 limit = { ... } 这种嵌套块的内容，被外层正则定位不到）
                # 简单处理：跳过一个标识符后继续
                sm = re.match(IDENT, modules_content, scan_pos)
                if sm:
                    scan_pos = sm.end()
                else:
                    scan_pos += 1
                continue

            item_id = hm.group(1)
            open_pos = hm.end() - 1  # 指向 '{'
            brace_range = extract_balanced_brace(modules_content, open_pos)
            if brace_range is None:
                print(f"   ⚠️ 模块 '{item_id}' 的花括号不匹配，跳过")
                scan_pos = open_pos + 1
                continue

            inner_s, inner_e = brace_range
            block_content = modules_content[inner_s:inner_e].strip()
            scan_pos = inner_e + 1  # 跳到闭合 '}' 之后继续扫描下一个

            # 递归解析内部结构
            item_data = parse_block_to_dict(block_content)
            item_data['generate_file'] = filename
            all_modules[item_id] = item_data

    return all_modules


def analyze_structure_union(modules_dict):
    """
    核心分析：分析全量模块字典，生成普通属性字段与嵌套条目的结构并集
    返回 (flat_union, nested_union, nested_internal_union)
    nested_internal_union: dict[str, set[str]]  记录每个嵌套键内部使用过的子字段
    """
    union_normal_keys = set()
    union_nested_keys = set()
    nested_internal = {}

    for item_id, item_data in modules_dict.items():
        for key, val in item_data.items():
            if key == 'generate_file':
                continue
            if isinstance(val, dict):
                union_nested_keys.add(key)
                if key not in nested_internal:
                    nested_internal[key] = set()
                for sub_key in val.keys():
                    nested_internal[key].add(sub_key)
            else:
                union_normal_keys.add(key)

    return (sorted(list(union_normal_keys)),
            sorted(list(union_nested_keys)),
            {k: sorted(list(v)) for k, v in nested_internal.items()})


def generate_sqlite_reference(modules_dict, normal_union, nested_union, nested_internal_union,
                             schema_name="equipment_modules"):
    """
    根据结构并集生成 SQLite DDL 建表参考脚本
    - 主表：equipment_modules
    - 子表：equipment_modules_<nested_key>
    """
    ddl_lines = []
    ddl_lines.append("-- ============================================================")
    ddl_lines.append("-- 自动生成：equipment_modules SQLite DDL 参考脚本")
    ddl_lines.append(f"-- 源数据条数：{len(modules_dict)}")
    ddl_lines.append("-- 字段推导：所有条目中至少出现过一次的字段并集")
    ddl_lines.append("-- ============================================================")
    ddl_lines.append("")

    # ---------- 主表 ----------
    ddl_lines.append(f"CREATE TABLE IF NOT EXISTS {schema_name} (")
    ddl_lines.append("    module_id       TEXT PRIMARY KEY,   -- 模块唯一ID (如 tank_gasoline_engine)")
    ddl_lines.append("    generate_file TEXT,               -- 来源文件追踪")

    # 普通字段推断类型
    type_samples = {}
    for item_id, item_data in modules_dict.items():
        for key, val in item_data.items():
            if key == 'generate_file':
                continue
            if isinstance(val, dict):
                continue
            if key not in type_samples:
                type_samples[key] = []
            if len(type_samples[key]) < 5:
                type_samples[key].append(val)

    def guess_sql_type(key, samples):
        """根据样本推断 SQLite 类型"""
        if not samples:
            return "TEXT"
        all_int = True
        all_real = True
        for s in samples:
            try:
                int(s)
            except ValueError:
                all_int = False
                break
        if all_int:
            return "INTEGER"
        for s in samples:
            try:
                float(s)
            except ValueError:
                all_real = False
                break
        if all_real:
            return "REAL"
        return "TEXT"

    for key in normal_union:
        sql_type = guess_sql_type(key, type_samples.get(key, []))
        ddl_lines.append(f"    {key:<28} {sql_type},")

    ddl_lines.append(");")
    ddl_lines.append("")

    # ---------- 子表 ----------
    for nested_key in nested_union:
        sub_fields = nested_internal_union.get(nested_key, [])
        table_name = f"{schema_name}_{nested_key}"
        ddl_lines.append(f"-- 子表：{nested_key} (嵌套块 {nested_key} = {{ ... }} 的内部字段")
        ddl_lines.append(f"CREATE TABLE IF NOT EXISTS {table_name} (")
        ddl_lines.append("    id          INTEGER PRIMARY KEY AUTOINCREMENT,")
        ddl_lines.append("    module_id   TEXT,")
        ddl_lines.append("    stat_key    TEXT,     -- 原嵌套键内部字段名")
        ddl_lines.append("    stat_value  REAL,   -- 原嵌套键内部字段值")
        ddl_lines.append(f"    FOREIGN KEY (module_id) REFERENCES {schema_name}(module_id)")
        ddl_lines.append(");")
        ddl_lines.append("")

        # 统计样例字段，提示性注释
        if sub_fields:
            ddl_lines.append(f"--   {nested_key} 内部观测到的字段名：{', '.join(sub_fields)}")
            ddl_lines.append("")

    ddl_lines.append("-- ============================================================")
    ddl_lines.append("-- 查询示例：获取某模块的所有属性")
    ddl_lines.append("-- ============================================================")
    ddl_lines.append("/*")
    ddl_lines.append("SELECT em.*,")
    if nested_union:
        for nk in nested_union:
            ddl_lines.append(f"       -- {nk}_agg.{nk}_json")
    ddl_lines.append("  FROM equipment_modules em")
    for nk in nested_union:
        ddl_lines.append(f"  -- LEFT JOIN (SELECT module_id, json_group_object(stat_key, stat_value) AS {nk}_json")
        ddl_lines.append(f"  --              FROM equipment_modules_{nk}")
        ddl_lines.append(f"  --             GROUP BY module_id) {nk}_agg ON {nk}_agg.module_id = em.module_id")
    ddl_lines.append(" WHERE em.module_id = 'tank_gasoline_engine';")
    ddl_lines.append("*/")

    return "\n".join(ddl_lines)


# ==================== 控制台运行入口 ====================
if __name__ == "__main__":
    test_folder = "./codes/equipment/modules"
    if not os.path.exists(test_folder):
        test_folder = input("请输入要测试提取的 equipment_modules 文件夹路径: ").strip()

    # 1. 抓取数据
    result_dict = extract_modules_folder(test_folder)

    if not result_dict:
        print("[提示] 未探测到有效装备模块条目。")
        exit()

    # 2. 计算键值结构并集
    normal_union, nested_union, nested_internal = analyze_structure_union(result_dict)

    # 3. 打印输出报告
    print("\n" + "="*60)
    print(f"📋 逆向资产盲抓探测完成！总计成功捕获 {len(result_dict)} 个装备模块条目")
    print("="*60)

    print("\n[🎯 扁平属性键并集 (Union of Normal Fields)]")
    print("--- 以下字段在所有条目中至少出现过一次，可作为设计【主表列】的依据 ---")
    pprint.pprint(normal_union, compact=True, width=80)

    print("\n[🎯 子嵌套条目键并集 (Union of Nested Objects)]")
    print("--- 以下条目为大括号嵌套块，必须作为设计【子表/关联副表】的依据 ---")
    pprint.pprint(nested_union, compact=True, width=80)

    print("\n[🔍 嵌套块内部字段明细 (Internal Fields per Nested Block)]")
    for nk in nested_union:
        internal_fields = nested_internal.get(nk, [])
        print(f"  {nk}: {internal_fields}")

    print("\n" + "="*60)
    print("💡 基于以上并集，自动生成 SQLite DDL 参考脚本...")
    print("="*60)

    # # 4. 生成并打印 SQLite DDL 参考
    # sqlite_ddl = generate_sqlite_reference(
    #     result_dict, normal_union, nested_union, nested_internal
    # )
    # print("\n" + sqlite_ddl)