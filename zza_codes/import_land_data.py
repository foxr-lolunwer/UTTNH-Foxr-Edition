import os
import re
import sqlite3
import json

# 字段映射表：源文件键名 → 数据库列名
FIELD_NAME_MAP = {
    "archetype": "archetype_eid",
    "parent": "parent_eid",
    "derived_variant_name": "derived_variant_name_eid",
}

# module_stats_land 表可识别的 stat 字段
MODULE_STAT_FIELDS = [
    "air_attack", "ap_attack", "armor_value", "breakthrough",
    "build_cost_ic", "defense", "entrenchment", "fuel_capacity",
    "fuel_consumption", "hard_attack", "hardness", "maximum_speed",
    "reliability", "soft_attack",
]


def clean_and_merge_file(file_path):
    """彻底剥离注释并将全文件压缩合并为单行字符串，压缩多余空格"""
    cleaned_lines = []
    with open(file_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
        for line in f:
            if '#' in line:
                line = line.split('#')[0]
            cleaned_lines.append(line.strip())
    full_text = " ".join(cleaned_lines)
    return re.sub(r'\s+', ' ', full_text)


def extract_braced_content(text, start_pos):
    """大括号计数状态机：精准截取闭合大括号块，防止多层嵌套提早截断"""
    brace_count = 0
    content = []
    has_started = False
    
    for i in range(start_pos, len(text)):
        char = text[i]
        content.append(char)
        if char == '{':
            brace_count += 1
            has_started = True
        elif char == '}':
            brace_count -= 1
            
        if has_started and brace_count == 0:
            return "".join(content), i + 1
            
    return "".join(content), len(text)


def parse_simple_value(token):
    """把 yes/no 转 1/0，去引号，其他原样返回"""
    if not token:
        return token
    if token.lower() == 'yes':
        return 1
    if token.lower() == 'no':
        return 0
    if len(token) >= 2 and token[0] == '"' and token[-1] == '"':
        return token[1:-1]
    return token


def rebuild_database(db_path, export_json_path):
    """读取 export.json 中的 DDL，从头重建数据库（删旧建新）"""
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f" 🗑️  已删除旧数据库: {db_path}")
    with open(export_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    tables = []
    for obj in data.get("objects", []):
        if obj.get("type") == "table" and "ddl" in obj:
            cursor.execute(obj["ddl"])
            tables.append(obj["name"])
    conn.commit()
    print(f" ✅ 已创建 {len(tables)} 张表: {', '.join(tables)}")
    return conn, cursor


def get_table_columns(cursor, table_name):
    """获取指定表的列名列表，用于盲匹配安全写入"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [col[1] for col in cursor.fetchall()]


def parse_equipment_body(body_text):
    """
    深度重构的单体装备解析引擎
    """
    # 已识别的嵌套键（不会进入 others）
    SPECIAL_NESTED_KEYS = {"resources", "type", "can_convert_from", "upgrades",
                           "module_slots", "module_count_limit", "default_modules", "can_be_produced"}
    # 已识别的扁平键（不会进入 others，要么进入子表要么进入主表字段）
    SPECIAL_FLAT_KEYS = {"type", "upgrade", "module_slots"}
    
    result = {
        "fields": {},               # 对应主表 equipments_land 的列
        "types": [],                # 对应子表 type
        "conversions": [],          # 对应子表 can_convert_from
        "upgrades": [],             # 对应子表 upgrades
        "slots": {},                # 对应 module_slots 和 allowed_module_categories
        "count_limits": [],         # 解析后的 module_count_limit: [{"mid": ..., "category_id": ...}]
        "default_modules": [],       # 解析后的 default_modules: [(slot_id, value)]
        "others_parts": []          # 累积所有其他未识别内容，最后合并为 others 文本
    }
    
    pos = 0
    length = len(body_text)
    
    while pos < length:
        if body_text[pos] == ' ':
            pos += 1
            continue
            
        # 寻找 key = 
        match = re.match(r'([a-zA-Z0-9_\-]+)\s*=\s*', body_text[pos:])
        if match:
            key = match.group(1)
            pos += match.end()
            
            if pos < length and body_text[pos] == '{':
                # 遭遇嵌套大括号块
                block_str, next_pos = extract_braced_content(body_text, pos)
                pos = next_pos
                inner_content = block_str.strip().lstrip('{').rstrip('}').strip()
                
                # --- 分流嵌套处理 ---
                if key == 'resources':
                    res_matches = re.findall(r'([a-zA-Z0-9_\-]+)\s*=\s*([0-9\.]+)', inner_content)
                    for r_key, r_val in res_matches:
                        db_key = f"resource_{r_key}"
                        result["fields"][db_key] = int(float(r_val))
                        
                elif key == 'type':
                    # 兼容格式 B -> type = { infantry = yes } 或 type = { infantry mechanized }
                    type_keys = re.findall(r'([a-zA-Z0-9_\-]+)\s*=', inner_content)
                    if type_keys:
                        result["types"].extend(type_keys)
                    else:
                        result["types"].extend(inner_content.split())
                        
                elif key == 'can_convert_from':
                    result["conversions"].extend(inner_content.split())
                    
                elif key == 'upgrades':
                    # 将大括号内部平铺的所有升级项抓出来 (如 upgrade_1 upgrade_2)
                    # 兼容带有等号和不带等号的情况
                    up_matches = re.findall(r'([a-zA-Z0-9_\-]+)', inner_content)
                    result["upgrades"].extend([u for u in up_matches if u not in ('yes', 'no')])
                    
                elif key == 'module_slots':
                    slot_pattern = re.compile(r'([a-zA-Z0-9_\-]+)\s*=\s*\{')
                    s_pos = 0
                    while s_pos < len(inner_content):
                        s_match = slot_pattern.search(inner_content[s_pos:])
                        if not s_match:
                            break
                        slot_id = s_match.group(1)
                        absolute_start = s_pos + s_match.end() - 1
                        slot_block, next_s_pos = extract_braced_content(inner_content, absolute_start)
                        s_pos = absolute_start + (next_s_pos - absolute_start)
                        
                        slot_body = slot_block.strip().lstrip('{').rstrip('}').strip()
                        req_match = re.search(r'required\s*=\s*(yes|no)', slot_body)
                        is_required = 1 if req_match and req_match.group(1) == 'yes' else 0
                        
                        # 处理 allowed_module_categories 可能有嵌套
                        cat_start = re.search(r'allowed_module_categories\s*=\s*\{', slot_body)
                        if cat_start:
                            cat_block_start = cat_start.end() - 1
                            cat_block_str, _ = extract_braced_content(slot_body, cat_block_start)
                            cat_inner = cat_block_str.strip().lstrip('{').rstrip('}').strip()
                            categories = cat_inner.split()
                        else:
                            cat_match = re.search(r'allowed_module_categories\s*=\s*\{([^{}]+)\}', slot_body)
                            categories = cat_match.group(1).split() if cat_match else []
                        
                        result["slots"][slot_id] = {"required": is_required, "categories": categories}
                        
                elif key == 'module_count_limit':
                    # 解析 module_count_limit = { module = xxx count < 2 } 或 { category = xxx count < 2 }
                    mid = ""
                    category_id = ""
                    mm = re.search(r'module\s*=\s*([a-zA-Z0-9_\-]+)', inner_content)
                    cm = re.search(r'category\s*=\s*([a-zA-Z0-9_\-]+)', inner_content)
                    count_m = re.search(r'count\s*([<>]=?|=)\s*([0-9]+)', inner_content)
                    if mm:
                        mid = mm.group(1)
                    if cm:
                        category_id = cm.group(1)
                    if count_m:
                        count = f"{count_m.group(1)} {count_m.group(2)}"
                    result["count_limits"].append({"mid": mid, "category_id": category_id, "count": count})

                elif key == 'default_modules':
                    # default_modules 内部是平铺键值：slot_id = value
                    dm_pairs = re.findall(r'([a-zA-Z0-9_\-]+)\s*=\s*([a-zA-Z0-9_\-]+)', inner_content)
                    result["default_modules"].extend(dm_pairs)
                    
                elif key == 'can_be_produced':
                    # 将 can_be_produced = { ... } 完整文本存入 others
                    result["others_parts"].append(f"{key} = {block_str.strip()}")
                else:
                    # 未识别的嵌套键：完整保留 key = { ... } 进入 others
                    result["others_parts"].append(f"{key} = {block_str.strip()}")
            else:
                # 普通基础属性键值对
                val_match = re.match(r'([^#\s{}]+)', body_text[pos:])
                if val_match:
                    val = val_match.group(1)
                    pos += val_match.end()
                    
                    # 跳过 module_slots = inherit 这种继承值
                    if key == 'module_slots' and val.lower() == 'inherit':
                        continue
                    
                    val = parse_simple_value(val)
                    if key == 'type':
                        result["types"].append(val)
                    elif key == 'upgrade':
                        result["upgrades"].append(val)
                    else:
                        db_key = FIELD_NAME_MAP.get(key, key)
                        result["fields"][db_key] = val
        else:
            pos += 1
            
    if result["others_parts"]:
        result["fields"]["others"] = " ".join(result["others_parts"])
    return result


def parse_module_body(body_text):
    """解析单个模块条目（equipment_modules 下的一个 mid = { ... }）"""
    result = {
        "fields": {},
        "add_stats": {},
        "multiply_stats": {},
        "can_convert_from": [],
        "forbid_equipment_type": [],
        "forbid_equipment_type_exact_match": [],
        "forbid_equipment_type_exact_match_for_category": {},
        "limit_text": "",
        "others_parts": [],
    }
    pos = 0
    length = len(body_text)
    while pos < length:
        if body_text[pos] == ' ':
            pos += 1
            continue
        match = re.match(r'([a-zA-Z0-9_\-]+)\s*=\s*', body_text[pos:])
        if match:
            key = match.group(1)
            pos += match.end()
            if pos < length and body_text[pos] == '{':
                block_str, next_pos = extract_braced_content(body_text, pos)
                pos = next_pos
                inner = block_str.strip().lstrip('{').rstrip('}').strip()
                if key == 'add_stats':
                    for k, v in re.findall(r'([a-zA-Z0-9_\-]+)\s*=\s*([^\s{}]+)', inner):
                        result["add_stats"][k] = float(v)
                elif key == 'multiply_stats':
                    for k, v in re.findall(r'([a-zA-Z0-9_\-]+)\s*=\s*([^\s{}]+)', inner):
                        result["multiply_stats"][k] = float(v)
                elif key == 'build_cost_resources':
                    for k, v in re.findall(r'([a-zA-Z0-9_\-]+)\s*=\s*([0-9]+)', inner):
                        result["fields"][f"build_cost_resources_{k}"] = int(v)
                elif key == 'can_convert_from':
                    mm = re.search(r'module\s*=\s*([a-zA-Z0-9_\-]+)', inner)
                    cm = re.search(r'category\s*=\s*([a-zA-Z0-9_\-]+)', inner)
                    cost_m = re.search(r'convert_cost_ic\s*=\s*([0-9.]+)', inner)
                    entry = {"module": "", "module_category": "", "convert_cost_ic": 0.0}
                    if mm: entry["module"] = mm.group(1)
                    if cm: entry["module_category"] = cm.group(1)
                    if cost_m: entry["convert_cost_ic"] = float(cost_m.group(1))
                    result["can_convert_from"].append(entry)
                elif key == 'forbid_equipment_type_exact_match_for_category':
                    for k, v in re.findall(r'([a-zA-Z0-9_\-]+)\s*=\s*([a-zA-Z0-9_\-]+)', inner):
                        result["forbid_equipment_type_exact_match_for_category"][k] = v
                elif key == 'limit':
                    result["limit_text"] = inner.strip()
                else:
                    result["others_parts"].append(f"{key} = {block_str.strip()}")
            else:
                val_match = re.match(r'([^#\s{}]+)', body_text[pos:])
                if val_match:
                    val = val_match.group(1)
                    pos += val_match.end()
                    val = parse_simple_value(val)
                    if key == 'forbid_equipment_type_exact_match':
                        result["forbid_equipment_type_exact_match"].append(val)
                    elif key == 'forbid_equipment_type':
                        result["forbid_equipment_type"].append(val)
                    elif key == 'xp_cost':
                        result["fields"]["xp_cost"] = float(val)
                    elif key == 'dismantle_cost_ic':
                        result["fields"]["dismantle_cost_ic"] = float(val)
                    else:
                        result["fields"][key] = val
        else:
            pos += 1
    if result["others_parts"]:
        result["fields"]["others"] = " ".join(result["others_parts"])
    return result


def parse_equipments_block(file_text, filename):
    """解析单个文本中的所有装备条目，返回待写库的结构化数据"""
    root_match = re.search(r'equipments\s*=\s*\{', file_text)
    if not root_match:
        return []
    root_brace_pos = root_match.end() - 1
    root_block, _ = extract_braced_content(file_text, root_brace_pos)
    content = root_block.strip().lstrip('{').rstrip('}').strip()
    parsed = []
    pos = 0
    while pos < len(content):
        item_match = re.match(r'\s*([a-zA-Z0-9_\-]+)\s*=\s*\{', content[pos:])
        if not item_match:
            pos += 1
            continue
        eid = item_match.group(1)
        abs_start = pos + item_match.end() - 1
        item_block, next_pos = extract_braced_content(content, abs_start)
        pos = abs_start + (next_pos - abs_start)
        body = item_block.strip().lstrip('{').rstrip('}').strip()
        parsed.append({"eid": eid, "filename": filename, "data": parse_equipment_body(body)})
    return parsed


def parse_modules_block(file_text):
    """解析单个文本中的所有模块条目，返回待写库的结构化数据"""
    root_match = re.search(r'equipment_modules\s*=\s*\{', file_text)
    if not root_match:
        return []
    root_brace_pos = root_match.end() - 1
    root_block, _ = extract_braced_content(file_text, root_brace_pos)
    content = root_block.strip().lstrip('{').rstrip('}').strip()
    parsed = []
    pos = 0
    while pos < len(content):
        item_match = re.match(r'\s*([a-zA-Z0-9_\-]+)\s*=\s*\{', content[pos:])
        if not item_match:
            pos += 1
            continue
        mid = item_match.group(1)
        abs_start = pos + item_match.end() - 1
        item_block, next_pos = extract_braced_content(content, abs_start)
        pos = abs_start + (next_pos - abs_start)
        body = item_block.strip().lstrip('{').rstrip('}').strip()
        parsed.append({"mid": mid, "data": parse_module_body(body)})
    return parsed


def insert_module_limit_rows(cursor, parsed_modules):
    """先写入模块限制表 modules_limit"""
    try:
        cursor.execute("INSERT OR IGNORE INTO modules_limit (mlid, \"limit\") VALUES (0, '')")
    except sqlite3.Error as e:
        print(f" ❌ 创建 modules_limit 默认行失败: {e}")

    count = 0
    for item in parsed_modules:
        data = item["data"]
        if not data["limit_text"]:
            item["_mlid"] = 0
            continue
        try:
            cursor.execute("INSERT INTO modules_limit (\"limit\") VALUES (?)", (data["limit_text"],))
            item["_mlid"] = cursor.lastrowid
            count += 1
        except sqlite3.Error as e:
            print(f" ❌ [模块 {item['mid']}] modules_limit 写入失败: {e}")
            item["_mlid"] = 0
    return count


def insert_modules_main_rows(cursor, parsed_modules, modules_cols):
    """再写入模块主表 modules"""
    count = 0
    for item in parsed_modules:
        mid = item["mid"]
        data = item["data"]
        main_fields = {"mid": mid, "mlid": item.get("_mlid", 0)}
        for k, v in data["fields"].items():
            if k in modules_cols:
                main_fields[k] = v
        cols = ", ".join(main_fields.keys())
        phs = ", ".join(["?"] * len(main_fields))
        try:
            cursor.execute(f"INSERT OR REPLACE INTO modules ({cols}) VALUES ({phs})", list(main_fields.values()))
            count += 1
        except sqlite3.Error as e:
            print(f" ❌ [模块 {mid}] 主表写入失败: {e}")
    return count


def insert_module_sub_rows(cursor, parsed_modules, stats_cols):
    """最后写入模块子表"""
    count = 0
    for item in parsed_modules:
        mid = item["mid"]
        data = item["data"]
        try:
            add_row = {"mid": mid, "type": "add"}
            for k, v in data["add_stats"].items():
                if k in stats_cols:
                    add_row[k] = v
            if len(add_row) > 2:
                sc = ", ".join(add_row.keys())
                sp = ", ".join(["?"] * len(add_row))
                cursor.execute(f"INSERT INTO module_stats_land ({sc}) VALUES ({sp})", list(add_row.values()))
            mult_row = {"mid": mid, "type": "multiply"}
            for k, v in data["multiply_stats"].items():
                if k in stats_cols:
                    mult_row[k] = v
            if len(mult_row) > 2:
                sc = ", ".join(mult_row.keys())
                sp = ", ".join(["?"] * len(mult_row))
                cursor.execute(f"INSERT INTO module_stats_land ({sc}) VALUES ({sp})", list(mult_row.values()))
            for entry in data["can_convert_from"]:
                cursor.execute(
                    "INSERT INTO can_convert_from_module (give_mid, module, module_category, convert_cost_ic) VALUES (?, ?, ?, ?)",
                    (mid, entry["module"] or None, entry["module_category"] or None, entry["convert_cost_ic"]))
            for ftype in data["forbid_equipment_type"]:
                cursor.execute(
                    "INSERT INTO module_forbid_equipment_type (mid, equipment_type) VALUES (?, ?)",
                    (mid, ftype))
            for ftype in data["forbid_equipment_type_exact_match"]:
                cursor.execute(
                    "INSERT INTO module_forbid_equipment_type_exact_match (mid, equipment_type_exact_match) VALUES (?, ?)",
                    (mid, ftype))
            for cat, ftype in data["forbid_equipment_type_exact_match_for_category"].items():
                cursor.execute(
                    "INSERT INTO module_forbid_equipment_type_exact_match_for_category (mid, category, equipment_type_exact_match) VALUES (?, ?, ?)",
                    (mid, cat, ftype))
            count += 1
        except sqlite3.Error as e:
            print(f" ❌ [模块 {mid}] 子表写入失败: {e}")
    return count


def insert_equipment_main_rows(cursor, parsed_equipments, valid_columns):
    """先写入装备主表 equipments_land"""
    count = 0
    for item in parsed_equipments:
        eid = item["eid"]
        filename = item["filename"]
        data = item["data"]
        main_fields = {"eid": eid, "generate_file": filename}
        for k, v in data["fields"].items():
            if k in valid_columns:
                main_fields[k] = v
        cols = ", ".join(main_fields.keys())
        phs = ", ".join(["?"] * len(main_fields))
        try:
            cursor.execute(f"INSERT OR REPLACE INTO equipments_land ({cols}) VALUES ({phs})",
                           list(main_fields.values()))
            count += 1
        except sqlite3.Error as e:
            print(f" ❌ [装备 {eid}] 主表写入失败: {e}")
    return count


def insert_equipment_sub_rows(cursor, parsed_equipments):
    """再写入装备子表"""
    count = 0
    for item in parsed_equipments:
        eid = item["eid"]
        data = item["data"]
        try:
            for t in data["types"]:
                cursor.execute("INSERT INTO type (eid, type) VALUES (?, ?)", (eid, t))
            for from_eid in data["conversions"]:
                cursor.execute("INSERT INTO can_convert_from_equipment (give_eid, from_eid) VALUES (?, ?)",
                               (eid, from_eid))
            for up in data["upgrades"]:
                cursor.execute("INSERT INTO upgrades (eid, upgrade) VALUES (?, ?)", (eid, up))
            for slot_id, slot_info in data["slots"].items():
                cursor.execute(
                    "INSERT INTO module_slots (eid, slot_id, required) VALUES (?, ?, ?)",
                    (eid, slot_id, slot_info["required"]))
                msid = cursor.lastrowid
                for cat in slot_info["categories"]:
                    cursor.execute(
                        "INSERT INTO allowed_module_categories (msid, module_categorie) VALUES (?, ?)",
                        (msid, cat))
            for slot_id, value in data["default_modules"]:
                cursor.execute(
                    "INSERT INTO default_modules (eid, msid, value) VALUES (?, ?, ?)",
                    (eid, slot_id, value))
            for cl in data["count_limits"]:
                cursor.execute(
                    "INSERT INTO module_count_limit (eid, mid, category_id, count) VALUES (?, ?, ?, ?)",
                    (eid, cl["mid"] or None, cl["category_id"] or None, cl["count"] or None))
            count += 1
        except sqlite3.Error as e:
            print(f" ❌ [装备 {eid}] 子表写入失败: {e}")
    return count


def scan_files(folder_path):
    """递归收集目录下所有 .txt/.asset 文件的完整路径"""
    result = []
    if not os.path.exists(folder_path):
        return result
    for filename in sorted(os.listdir(folder_path)):
        full_path = os.path.join(folder_path, filename)
        if os.path.isdir(full_path):
            result.extend(scan_files(full_path))
        elif filename.endswith(('.txt', '.asset')):
            result.append(full_path)
    return result


def import_folder_two_pass(cursor, folder_path, valid_equip_columns, tables_with_columns):
    """先全量解析，再按模块限制→模块主表→模块子表→装备主表→装备子表依次导入"""
    all_files = scan_files(folder_path)
    parsed_modules = []
    parsed_equipments = []

    print("  --- 阶段 A: 全量解析 ---")
    for fpath in all_files:
        file_text = clean_and_merge_file(fpath)
        parsed_modules.extend(parse_modules_block(file_text))
        parsed_equipments.extend(parse_equipments_block(file_text, os.path.basename(fpath)))

    print(f"  共解析到模块 {len(parsed_modules)} 条，装备 {len(parsed_equipments)} 条")

    print("\n  --- 阶段 B: 依次写入数据库 ---")
    modules_cols = tables_with_columns.get("modules", [])
    stats_cols = tables_with_columns.get("module_stats_land", [])

    print("    1/5: 写入 modules_limit")
    module_limit_count = insert_module_limit_rows(cursor, parsed_modules)
    print(f"      modules_limit: {module_limit_count} 条")

    print("    2/5: 写入 modules")
    module_main_count = insert_modules_main_rows(cursor, parsed_modules, modules_cols)
    print(f"      modules: {module_main_count} 条")

    print("    3/5: 写入模块子表")
    module_sub_count = insert_module_sub_rows(cursor, parsed_modules, stats_cols)
    print(f"      模块子表: {module_sub_count} 条")

    print("    4/5: 写入 equipments_land")
    equip_main_count = insert_equipment_main_rows(cursor, parsed_equipments, valid_equip_columns)
    print(f"      equipments_land: {equip_main_count} 条")

    print("    5/5: 写入装备子表")
    equip_sub_count = insert_equipment_sub_rows(cursor, parsed_equipments)
    print(f"      装备子表: {equip_sub_count} 条")

    return equip_main_count, module_main_count


def print_stats(cursor):
    """打印每张表的行数"""
    tables = [
        "equipments_land", "type", "can_convert_from_equipment", "upgrades",
        "module_slots", "allowed_module_categories", "default_modules",
        "module_count_limit", "modules", "modules_limit",
        "module_stats_land", "can_convert_from_module",
        "module_forbid_equipment_type", "module_forbid_equipment_type_exact_match",
        "module_forbid_equipment_type_exact_match_for_category",
    ]
    print("\n========== 入库统计 ==========")
    for t in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {t}")
            n = cursor.fetchone()[0]
            print(f"  {t:55s} : {n}")
        except sqlite3.Error:
            print(f"  {t:55s} : (表不存在)")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    equipment_dir = os.path.join(script_dir, "equipment")
    export_json = os.path.join(script_dir, "export.json")
    db_file = os.path.join(script_dir, "em.db")
    print(f"装备文件夹: {equipment_dir}")
    print(f"结构参考:   {export_json}")
    print(f"输出数据库: {db_file}")
    print()
    if not os.path.exists(export_json):
        print("❌ export.json 不存在，无法重建数据库")
        return
    print(">>> 阶段 1: 按 export.json 重建数据库")
    conn, cursor = rebuild_database(db_file, export_json)
    tables_with_columns = {}
    for tname in ["equipments_land", "modules", "module_stats_land",
                  "module_count_limit", "module_slots", "allowed_module_categories",
                  "default_modules", "type", "can_convert_from_equipment", "upgrades",
                  "modules_limit", "can_convert_from_module",
                  "module_forbid_equipment_type", "module_forbid_equipment_type_exact_match",
                  "module_forbid_equipment_type_exact_match_for_category"]:
        tables_with_columns[tname] = get_table_columns(cursor, tname)
    valid_equip_columns = set(tables_with_columns["equipments_land"])
    print("\n>>> 阶段 2: 先全量解析，再依次导入")
    total_equip, total_mod = import_folder_two_pass(cursor, equipment_dir, valid_equip_columns, tables_with_columns)
    conn.commit()
    print_stats(cursor)
    conn.close()
    print(f"\n🎉 完成！总计装备 {total_equip} 条, 模块 {total_mod} 条")


if __name__ == "__main__":
    main()