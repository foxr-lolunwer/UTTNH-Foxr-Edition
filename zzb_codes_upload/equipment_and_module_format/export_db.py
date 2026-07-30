import os
import sqlite3

# ============================================================
# ⚙️ 全局核心静态配置变量（杜绝写在方法内部，方便全局复用与无损扩展）
# ============================================================

# 1. 模块生成文件名与游戏大类类型的映射字典
FILE_TYPE_MAP = {
    "modules/00_plane_modules.txt": "air",
    "modules/00_ship_modules.txt": "naval",
    "modules/00_tank_modules.txt": "land",
}

# 全部合并为一张总反向映射表（数据库 → 源文件）
ALL_STAT_MAP_REVERSED = {
    # ========== 陆战属性 ==========
    "l_soft_attack": "soft_attack",
    "l_hard_attack": "hard_attack",
    "l_ap_attack": "ap_attack",
    "l_air_attack": "air_attack",
    "l_defense": "defense",
    "l_breakthrough": "breakthrough",
    "l_hardness": "hardness",
    "l_armor_value": "armor_value",
    "l_entrenchment": "entrenchment",
    "l_fuel_capacity": "fuel_capacity",
    "l_max_military_factories": "max_military_factories",
    "l_railway_gun_attack": "railway_gun_attack",

    # ========== 海军属性 ==========
    "n_anti_air_attack": "anti_air_attack",
    "n_armor_value": "armor_value",
    "n_carrier_size": "carrier_size",
    "n_hg_attack": "hg_attack",
    "n_lg_attack": "lg_attack",
    "n_lg_armor_piercing": "lg_armor_piercing",
    "n_hg_armor_piercing": "hg_armor_piercing",
    "n_max_organisation": "max_organisation",
    "n_max_strength": "max_strength",
    "n_naval_dominance_factor": "naval_dominance_factor",
    "n_naval_range": "naval_range",
    "n_naval_speed": "naval_speed",
    "n_offensive_weapons": "offensive_weapons",
    "n_sub_attack": "sub_attack",
    "n_sub_detection": "sub_detection",
    "n_sub_visibility": "sub_visibility",
    "n_surface_detection": "surface_detection",
    "n_surface_visibility": "surface_visibility",
    "n_torpedo_attack": "torpedo_attack",
    "n_visual_tech_level_addition": "visual_tech_level_addition",
    "n_carrier_sub_detection": "carrier_sub_detection",
    "n_carrier_surface_detection": "carrier_surface_detection",
    "n_convoy_raiding_coordination": "convoy_raiding_coordination",
    "n_mines_planting": "mines_planting",
    "n_mines_sweeping": "mines_sweeping",
    "n_naval_heavy_gun_hit_chance_factor": "naval_heavy_gun_hit_chance_factor",
    "n_naval_light_gun_hit_chance_factor": "naval_light_gun_hit_chance_factor",
    "n_naval_torpedo_damage_reduction_factor": "naval_torpedo_damage_reduction_factor",
    "n_naval_torpedo_enemy_critical_chance_factor": "naval_torpedo_enemy_critical_chance_factor",
    "n_naval_torpedo_hit_chance_factor": "naval_torpedo_hit_chance_factor",
    "n_naval_weather_penalty_factor": "naval_weather_penalty_factor",
    "n_submarine_carrier_size": "submarine_carrier_size",

    # ========== 空军属性 ==========
    "a_air_agility": "air_agility",
    "a_air_defence": "air_defence",
    "a_air_map_icon_frame": "air_map_icon_frame",
    "a_air_range": "air_range",
    "a_air_superiority": "air_superiority",
    "a_interface_overview_category_index": "interface_overview_category_index",
    "a_naval_strike_attack": "naval_strike_attack",
    "a_naval_strike_targetting": "naval_strike_targetting",
    "a_weight": "weight",
    "a_air_attack": "air_attack",
    "a_air_bombing": "air_bombing",
    "a_air_ground_attack": "air_ground_attack",
    "a_night_penalty": "night_penalty",
    "a_thrust": "thrust",
}

# 2. 数据库平铺资源列与 PDX 标准树状属性名称的映射清单
RESOURCE_FIELDS_MAP = [
    ("oil", "build_cost_resources_oil", "dismantle_cost_resources_oil"),
    ("aluminium", "build_cost_resources_aluminium", "dismantle_cost_resources_aluminium"),
    ("rubber", "build_cost_resources_rubber", "dismantle_cost_resources_rubber"),
    ("tungsten", "build_cost_resources_tungsten", "dismantle_cost_resources_tungsten"),
    ("steel", "build_cost_resources_steel", "dismantle_cost_resources_steel"),
    ("chromium", "build_cost_resources_chromium", "dismantle_cost_resources_chromium"),
    ("coal", "build_cost_resources_coal", "dismantle_cost_resources_coal")
]

# 3. 模块主表的基础标准字段查询映射（Mid 必须为第一列，Generate_File、Mlid 必须在尾部以供状态机切块）
MODULE_SELECT_COLUMNS = [
    "m.mid", "m.abbreviation", "m.category", "m.sfx", "m.xp_cost", "m.dismantle_cost_ic", "m.gui_category",
    "m.build_cost_resources_oil", "m.build_cost_resources_aluminium", "m.build_cost_resources_rubber",
    "m.build_cost_resources_tungsten", "m.build_cost_resources_steel", "m.build_cost_resources_chromium",
    "m.build_cost_resources_coal",
    "m.dismantle_cost_resources_oil", "m.dismantle_cost_resources_aluminium", "m.dismantle_cost_resources_rubber",
    "m.dismantle_cost_resources_tungsten", "m.dismantle_cost_resources_steel", "m.dismantle_cost_resources_chromium",
    "m.dismantle_cost_resources_coal",
    "m.others", "m.generate_file", "m.mlid"
]


# ============================================================
# 🛠️ 模块反向编译生成器核心方法
# ============================================================

def compile_modules_to_intermediary(db_path):
    """
    第一步重构：将基础模块数据与高维 stats 属性关联，编译并输出一个可用于流水线流转的中间体字典。
    注：外部已提供全局常量 FILE_TYPE_MAP, RESOURCE_FIELDS_MAP, MODULE_SELECT_COLUMNS 以及 ALL_STAT_MAP_REVERSED。
    """
    if not os.path.exists(db_path):
        print(f"[错误] 数据库不存在: {db_path}")
        return {}

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. 动态调取外部 MODULE_SELECT_COLUMNS 提取主表数据
    columns_str = ", ".join(MODULE_SELECT_COLUMNS)
    try:
        cursor.execute(f"SELECT {columns_str} FROM m_modules m")
        module_rows = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"[错误] 读取模块主表失败: {e}")
        conn.close()
        return {}

    # 初始化中间体流转大字典
    intermediary_modules_dict = {}

    print("🔄 正在初始化中间体字典并还原模块核心属性...")

    for m_row in module_rows:
        mid = m_row["mid"]
        lines = []

        # 1:1 构建模块头部及非空基础数据
        lines.append(f"\t{mid} = {{")
        if m_row["abbreviation"]: lines.append(f'\t\tabbreviation = "{m_row["abbreviation"]}"')
        if m_row["category"]:     lines.append(f"\t\tcategory = {m_row['category']}")
        if m_row["sfx"]:          lines.append(f"\t\tsfx = {m_row['sfx']}")
        if m_row["gui_category"]: lines.append(f"\t\tgui_category = {m_row['gui_category']}")

        if m_row["xp_cost"] and m_row["xp_cost"] != 0:
            lines.append(
                f"\t\txp_cost = {int(m_row['xp_cost']) if m_row['xp_cost'].is_integer() else m_row['xp_cost']}")
        if m_row["dismantle_cost_ic"] and m_row["dismantle_cost_ic"] != 0:
            lines.append(
                f"\t\tdismantle_cost_ic = {int(m_row['dismantle_cost_ic']) if m_row['dismantle_cost_ic'].is_integer() else m_row['dismantle_cost_ic']}")

        # 遍历全局列表组装 build_cost_resources 块
        build_lines = [f"\t\t\t{res_k} = {m_row[b_col]}" for res_k, b_col, _ in RESOURCE_FIELDS_MAP if
                       m_row[b_col] and m_row[b_col] > 0]
        if build_lines:
            lines.append("\t\tbuild_cost_resources = {")
            lines.extend(build_lines)
            lines.append("\t\t}")

        # 遍历全局列表组装 dismantle_cost_resources 块
        dismantle_lines = [f"\t\t\t{res_k} = {m_row[d_col]}" for res_k, _, d_col in RESOURCE_FIELDS_MAP if
                           m_row[d_col] and m_row[d_col] > 0]
        if dismantle_lines:
            lines.append("\t\tdismantle_cost_resources = {")
            lines.extend(dismantle_lines)
            lines.append("\t\t}")

        # 还原残余复杂脚本
        if m_row["others"]:
            lines.append(f"\t\t{m_row['others'].strip()}")

        # 暂不写入结尾大括号，记录核心控制元数据，装入大字典
        intermediary_modules_dict[mid] = {
            "generate_file": m_row["generate_file"],
            "mlid": m_row["mlid"],
            "lines": lines
        }

    # ============================================================
    # 2. 核心进阶：调取 m_module_stats 表，解构并进行多类冲突校验合并
    # ============================================================
    print("🔄 正在读取 m_module_stats 并智能清洗组装属性状态块...")
    try:
        cursor.execute("SELECT * FROM m_module_stats")
        stats_rows = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"[错误] 读取模块 stats 表失败: {e}")
        conn.close()
        return intermediary_modules_dict

    # 外部未包含该映射，我们显式声明内部 type 与大括号名转换
    STATS_TYPE_BLOCK_MAP = {
        "add": "add_stats",
        "multiply": "multiply_stats",
        "add_average": "add_average_stats"
    }

    # 为每个 mid 准备一个子类型的属性聚合字典，结构：{ mid: { "add_stats": { "air_attack": 5 } } }
    mid_stats_accumulator = {}

    for s_row in stats_rows:
        s_mid = s_row["mid"]
        s_type = s_row["type"]

        # 排除孤立脏数据
        if s_mid not in intermediary_modules_dict:
            continue

        block_name = STATS_TYPE_BLOCK_MAP.get(s_type.lower())
        if not block_name:
            continue

        if s_mid not in mid_stats_accumulator:
            mid_stats_accumulator[s_mid] = {}
        if block_name not in mid_stats_accumulator[s_mid]:
            mid_stats_accumulator[s_mid][block_name] = {}

        current_block_dict = mid_stats_accumulator[s_mid][block_name]

        # 遍历 m_module_stats 行中所有潜在的属性列
        for db_column in s_row.keys():
            if db_column in ("stats_id", "type", "mid"):
                continue

            val = s_row[db_column]
            if val is None or val == 0:
                continue

            # ✨ 核心修正：由于外部 ALL_STAT_MAP_REVERSED 不含基础这 4 个通用列，这里进行硬编码强行转换
            if db_column in ("build_cost_ic", "fuel_consumption", "maximum_speed", "reliability"):
                pdx_stat_key = db_column
            else:
                # 其余高维 a_/l_/n_ 属性走外部传入的逆向映射字典
                pdx_stat_key = ALL_STAT_MAP_REVERSED.get(db_column)

            if not pdx_stat_key:
                continue

            # 多类合并冲突检测与覆盖预警
            if pdx_stat_key in current_block_dict:
                if current_block_dict[pdx_stat_key] != val:
                    print(
                        f"⚠️ [合并数据警告] 模块 {s_mid} 的 {block_name} 块内部检测到键冲突: 列 {db_column} 试图将属性 '{pdx_stat_key}' 的值由 {current_block_dict[pdx_stat_key]} 覆盖更改为 {val}。已应用新数据。")

            current_block_dict[pdx_stat_key] = val

    # ============================================================
    # 3. 完美结合：将清洗合并后的 stats 树渲染追加进中间体行列表中
    # ============================================================
    for mid, blocks in mid_stats_accumulator.items():
        lines = intermediary_modules_dict[mid]["lines"]

        for block_name, stats_dict in blocks.items():
            if not stats_dict:
                continue

            lines.append(f"\t\t{block_name} = {{")
            for stat_k, stat_v in stats_dict.items():
                formatted_v = int(stat_v) if isinstance(stat_v, float) and stat_v.is_integer() else stat_v
                lines.append(f"\t\t\t{stat_k} = {formatted_v}")
            lines.append("\t\t}")

    conn.close()
    print(f"🎉 第一步重构圆满完成！中间体字典内已缓存 {len(intermediary_modules_dict)} 个模块的开放行级资产。")
    return intermediary_modules_dict


def append_module_subtables_to_intermediary(db_path, intermediary_modules_dict):
    """
    第二步重构：将 1:N 关系的子表数据（add_equipment_type, allow_mission_type,
    critical_parts, forbid_module_categories）批量追加进中间体字典的行列表中。
    """
    if not os.path.exists(db_path) or not intermediary_modules_dict:
        return intermediary_modules_dict

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. 定义子表相关的元数据配置清单 (数据库表名, 对应PDX属性键名, 属性列名)
    SUBTABLES_CONFIG = [
        ("m_add_equipment_type", "add_equipment_type", "type"),
        ("m_allow_mission_type", "allow_mission_type", "type"),
        ("m_allow_equipment_type", "allow_equipment_type", "type"),
        ("m_critical_parts", "critical_parts", "critical_part"),
        ("m_forbid_module_categories", "forbid_module_categories", "forbid_module_categorie")
    ]

    print("🔄 正在读取 1:N 关联子表并动态向中间体字典追加属性块...")

    # 2. 依次遍历处理每一个子表
    for table_name, pdx_key, column_name in SUBTABLES_CONFIG:
        # 聚合查询：一次性按 mid 将所有平铺行组织起来，提升编译效率
        query = f"SELECT mid, {column_name} FROM {table_name} ORDER BY mid"
        try:
            cursor.execute(query)
            rows = cursor.fetchall()
        except sqlite3.Error as e:
            print(f"[提示] 读取子表 {table_name} 失败或表不存在，跳过此属性处理。原因: {e}")
            continue

        # 将查询结果在内存中整理为映射：{ mid: ["val1", "val2"] }
        sub_data_map = {}
        for mid, val in rows:
            if not val:
                continue
            if mid not in sub_data_map:
                sub_data_map[mid] = []
            sub_data_map[mid].append(val.strip())

        # 3. 将聚合好的字符串列表以 PDX 标准语法追加进中间体行列表
        for mid, items in sub_data_map.items():
            # 只有当该 mid 确实存在于我们第一步初始化的主模块字典中时才进行追加
            if mid in intermediary_modules_dict:
                lines = intermediary_modules_dict[mid]["lines"]

                # 喷吐标准的嵌套格式
                lines.append(f"\t\t{pdx_key} = {{")
                for item in items:
                    lines.append(f"\t\t\t{item}")
                lines.append("\t\t}")

    conn.close()
    print("🎉 第二步 1:N 子表数据无损追加完毕！")
    return intermediary_modules_dict


def append_module_flat_subtables_to_intermediary(db_path, intermediary_modules_dict):
    """
    第三步重构：将需要平铺多行输出的关联表数据（parent, forbid_equipment_type,
    forbid_equipment_type_exact_match）以单行重复（key = value）的形式追加进中间体行列表中。
    """
    if not os.path.exists(db_path) or not intermediary_modules_dict:
        return intermediary_modules_dict

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. 配置平铺表元数据清单 (数据库表名, 最终生成的PDX键名, 存储值的列名)
    FLAT_TABLES_CONFIG = [
        ("m_parent", "parent", "parent"),
        ("m_module_forbid_equipment_type", "forbid_equipment_type", "equipment_type"),
        ("m_module_forbid_equipment_type_exact_match", "forbid_equipment_type_exact_match",
         "equipment_type_exact_match")
    ]

    print("🔄 正在读取平铺关联表，动态追加单行重复属性（key = value）...")

    # 2. 依次处理每一个需要平铺多行的子表
    for table_name, pdx_key, column_name in FLAT_TABLES_CONFIG:
        query = f"SELECT mid, {column_name} FROM {table_name} ORDER BY mid"
        try:
            cursor.execute(query)
            rows = cursor.fetchall()
        except sqlite3.Error as e:
            print(f"[提示] 读取平铺表 {table_name} 失败或表不存在，跳过处理。原因: {e}")
            continue

        # 内存映射聚合：将一个 mid 对应的多个平铺值收集到列表中
        flat_data_map = {}
        for mid, val in rows:
            if not val:
                continue
            if mid not in flat_data_map:
                flat_data_map[mid] = []
            flat_data_map[mid].append(val.strip())

        # 3. 核心平铺逻辑：打破大括号约束，每一个值单独喷吐占领一行
        for mid, values in flat_data_map.items():
            if mid in intermediary_modules_dict:
                lines = intermediary_modules_dict[mid]["lines"]

                # ✨ 核心修正：顺着列表循环，直接生成多行并列的扁平代码
                for val in values:
                    lines.append(f"\t\t{pdx_key} = {val}")

    conn.close()
    print("🎉 第三步 扁平单行属性追加完毕！")
    return intermediary_modules_dict


def append_module_mix_subtables_to_intermediary(db_path, intermediary_modules_dict):
    """
    第四步重构：将混合键值对表（m_module_forbid_equipment_type_exact_match_for_category）
    以大括号内嵌键值对（key = value）的形式，追加进中间体字典的行列表中。
    """
    if not os.path.exists(db_path) or not intermediary_modules_dict:
        return intermediary_modules_dict

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    table_name = "m_module_forbid_equipment_type_exact_match_for_category"
    pdx_key = "forbid_equipment_type_exact_match_for_category"

    print("🔄 正在读取混合关联表，动态追加内嵌键值对大括号块...")

    # 1. 抓取所有行，并按 mid 排序以确保数据流的连续性
    query = f"SELECT mid, category, equipment_type_exact_match FROM {table_name} ORDER BY mid"
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"[提示] 读取混合表 {table_name} 失败或表不存在，跳过处理。原因: {e}")
        conn.close()
        return intermediary_modules_dict

    # 2. 内存映射聚合：将数据整理为 { mid: [ (category, val), (category, val) ] }
    mix_data_map = {}
    for mid, cat, val in rows:
        if not cat or not val:
            continue
        if mid not in mix_data_map:
            mix_data_map[mid] = []
        mix_data_map[mid].append((cat.strip(), val.strip()))

    # 3. 核心混合还原逻辑：渲染出大括号包裹的一维键值对树
    for mid, kv_pairs in mix_data_map.items():
        if mid in intermediary_modules_dict:
            lines = intermediary_modules_dict[mid]["lines"]

            # 开启大括号外壳
            lines.append(f"\t\t{pdx_key} = {{")

            # ✨ 核心混合渲染：在大括号内部输出一维键值对
            for cat, val in kv_pairs:
                lines.append(f"\t\t\t{cat} = {val}")

            # 闭合大括号外壳
            lines.append("\t\t}")

    conn.close()
    print("🎉 第四步 混合大括号键值对追加完毕！")
    return intermediary_modules_dict


def append_module_mission_type_stats_to_intermediary(db_path, intermediary_modules_dict):
    """
    第五步重构：解析具有深度嵌套和多块平铺特性的 m_mission_type_stats，
    联合查询 m_module_stats 属性树，以独立的扁平复合块形式追加进中间体字典中。
    注：外部已提供全局常量 ALL_STAT_MAP_REVERSED。
    """
    if not os.path.exists(db_path) or not intermediary_modules_dict:
        return intermediary_modules_dict

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. 核心联合查询
    query = """
        SELECT 
            mts.mid, mts.[limit] AS limit_text, ms.*
        FROM m_mission_type_stats mts
        JOIN m_module_stats ms ON mts.stats_id = ms.stats_id
        ORDER BY mts.mid, mts.[limit], mts.stats_id
    """

    try:
        cursor.execute(query)
        rows = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"[提示] 读取任务状态联合表失败，跳过处理。原因: {e}")
        conn.close()
        return intermediary_modules_dict

    STATS_TYPE_BLOCK_MAP = {
        "add": "add_stats",
        "multiply": "multiply_stats",
        "add_average": "add_average_stats"
    }

    # 2. 先按 mid + limit 分组收集所有行数据
    # 数据结构：{ mid: { limit: [ 行数据列表 ] } }
    limit_groups = {}

    for row in rows:
        mid = row["mid"]
        limit_text = row["limit_text"]
        ms_type = row["type"]

        if mid not in intermediary_modules_dict:
            continue

        # 解析 block_name
        if ms_type in STATS_TYPE_BLOCK_MAP.values():
            block_name = ms_type
        else:
            block_name = STATS_TYPE_BLOCK_MAP.get(ms_type.lower())
        if not block_name:
            continue

        # 提取 stats 属性
        stats_dict = {}
        for db_column in row.keys():
            if db_column in ("stats_id", "type", "mid", "limit_text"):
                continue
            val = row[db_column]
            if val is None or val == 0:
                continue

            if db_column in ("build_cost_ic", "fuel_consumption", "maximum_speed", "reliability"):
                pdx_stat_key = db_column
            else:
                pdx_stat_key = ALL_STAT_MAP_REVERSED.get(db_column)

            if not pdx_stat_key:
                continue
            stats_dict[pdx_stat_key] = val

        if not stats_dict:
            continue

        # 按 mid -> limit 组织数据
        if mid not in limit_groups:
            limit_groups[mid] = {}
        if limit_text not in limit_groups[mid]:
            limit_groups[mid][limit_text] = []

        limit_groups[mid][limit_text].append({
            "block_name": block_name,
            "stats": stats_dict
        })

    # 3. 收集每个 mid 的所有 limit 值，用于后续判断哪些 limit 组合完全相同
    # 数据结构：{ mid: [ { "limits": {limit1, limit2, ...}, "blocks": { block_name: merged_stats } } ] }
    # 先将每个独立的 limit 作为一个初始条目，然后合并 limit 集合完全相同的条目
    import json

    mission_stats_merged = {}

    for mid, limit_data in limit_groups.items():
        if mid not in mission_stats_merged:
            mission_stats_merged[mid] = []

        # 为每个独立的 limit 创建初始条目
        limit_entries = {}
        for limit_text, row_list in limit_data.items():
            # 合并该 limit 下的所有 stats（来自不同 stats_id）
            merged_blocks = {}
            for row_data in row_list:
                block_name = row_data["block_name"]
                if block_name not in merged_blocks:
                    merged_blocks[block_name] = {}
                # 合并 stats，冲突时覆盖
                for stat_k, stat_v in row_data["stats"].items():
                    if stat_k in merged_blocks[block_name] and merged_blocks[block_name][stat_k] != stat_v:
                        print(
                            f"⚠️ [任务状态冲突警告] 模块 {mid} 在任务限制为 {limit_text} 的 {block_name} 块内部检测到冲突: {stat_k} 值不一致。已应用新数据。")
                    merged_blocks[block_name][stat_k] = stat_v

            # 生成该 limit 下 blocks 的指纹（排序后 JSON 序列化）
            sorted_blocks = {}
            for bn in sorted(merged_blocks.keys()):
                sorted_blocks[bn] = dict(sorted(merged_blocks[bn].items()))
            fingerprint = json.dumps(sorted_blocks, sort_keys=True)

            limit_entries[limit_text] = {
                "limits": {limit_text},
                "blocks": merged_blocks,
                "fingerprint": fingerprint
            }

        # 4. 合并具有完全相同 blocks 指纹的 limit_entries
        # 先按指纹分组
        fingerprint_groups = {}
        for limit_text, entry in limit_entries.items():
            fp = entry["fingerprint"]
            if fp not in fingerprint_groups:
                fingerprint_groups[fp] = {
                    "limits": set(),
                    "blocks": entry["blocks"]
                }
            fingerprint_groups[fp]["limits"].add(limit_text)

        # 现在尝试进一步合并：如果两组或多组指纹的 limits 集合完全相同，则它们的 blocks 也应该合并
        # 先按 limits 的排序元组分组
        final_groups = {}
        for fp, group_data in fingerprint_groups.items():
            limits_tuple = tuple(sorted(group_data["limits"]))
            if limits_tuple not in final_groups:
                final_groups[limits_tuple] = {
                    "limits": group_data["limits"],
                    "blocks": {}
                }
            # 合并 blocks
            for block_name, stats_dict in group_data["blocks"].items():
                if block_name not in final_groups[limits_tuple]["blocks"]:
                    final_groups[limits_tuple]["blocks"][block_name] = {}
                for stat_k, stat_v in stats_dict.items():
                    if stat_k in final_groups[limits_tuple]["blocks"][block_name] and \
                       final_groups[limits_tuple]["blocks"][block_name][stat_k] != stat_v:
                        print(
                            f"⚠️ [任务状态冲突警告] 模块 {mid} 在合并相同 limit 组时检测到 {block_name} 块中 {stat_k} 值冲突。已应用新数据。")
                    final_groups[limits_tuple]["blocks"][block_name][stat_k] = stat_v

        mission_stats_merged[mid] = list(final_groups.values())

    # 5. 渲染输出
    for mid, entries in mission_stats_merged.items():
        lines = intermediary_modules_dict[mid]["lines"]

        for entry in entries:
            limits = sorted(entry["limits"])

            lines.append("\t\tmission_type_stats = {")

            # limit 块使用大括号包裹
            if len(limits) == 1:
                lines.append(f"\t\t\tlimit = {{ {limits[0]} }}")
            else:
                lines.append("\t\t\tlimit = {")
                for limit_text in limits:
                    lines.append(f"\t\t\t\t{limit_text}")
                lines.append("\t\t\t}")

            # 输出各 stats 块
            for block_name in sorted(entry["blocks"].keys()):
                stats_dict = entry["blocks"][block_name]
                if not stats_dict:
                    continue

                lines.append(f"\t\t\t{block_name} = {{")
                for stat_k, stat_v in sorted(stats_dict.items()):
                    formatted_v = int(stat_v) if isinstance(stat_v, float) and stat_v.is_integer() else stat_v
                    lines.append(f"\t\t\t\t{stat_k} = {formatted_v}")
                lines.append("\t\t\t}")

            lines.append("\t\t}")

    conn.close()
    print("🎉 第五步 嵌套任务类型属性块合流追加完毕！")
    return intermediary_modules_dict


def append_module_conversion_sources_to_intermediary(db_path, intermediary_modules_dict):
    """
    第六步重构（新增）：解析 1:N 嵌套且具有互斥过滤规则的 m_can_convert_from 改装来源表，
    将其以大括号嵌套块的形式安全追加进中间体字典的行列表中。
    """
    if not os.path.exists(db_path) or not intermediary_modules_dict:
        return intermediary_modules_dict

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    table_name = "m_can_convert_from"
    pdx_key = "can_convert_from"

    print("🔄 正在读取改装来源表，动态追加可改装前置大括号块...")

    # 1. 抓取改装来源关联的所有核心维度，依据 give_mid (即模块的 mid) 组织排序
    query = f"SELECT give_mid, module, module_category, convert_cost_ic FROM {table_name} ORDER BY give_mid"
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"[提示] 读取改装来源表 {table_name} 失败或表不存在，跳过处理。原因: {e}")
        conn.close()
        return intermediary_modules_dict

    # 2. 内存空间多维聚合：将相同 give_mid 下的所有改装配置行收拢到字典列表中
    # 结构：{ "light_tank_chassis_0": [ { "module": "xxx", ... }, ... ] }
    conversion_data_map = {}
    for row in rows:
        g_mid = row["give_mid"]
        mod = row["module"].strip() if row["module"] else None
        cat = row["module_category"].strip() if row["module_category"] else None
        cost = row["convert_cost_ic"]

        # 🚨 硬核前置防线：根据规则，module 和 module_category 不能同时为空，为空的直接过滤
        if not mod and not cat:
            continue

        if g_mid not in conversion_data_map:
            conversion_data_map[g_mid] = []

        conversion_data_map[g_mid].append({
            "module": mod,
            "module_category": cat,
            "convert_cost_ic": cost
        })

    # 3. 核心文本渲染：遍历聚合数据，为对应的模块 lines 原地无损追加 P 社语法块
    for g_mid, conf_list in conversion_data_map.items():
        if g_mid in intermediary_modules_dict:
            lines = intermediary_modules_dict[g_mid]["lines"]

            # ✨ 核心处理：由于一个模块内部可能有多个并列的 can_convert_from = { ... } 声明，这里必须用循环平铺
            for conf in conf_list:
                lines.append(f"\t\t{pdx_key} = {{")

                # 只有不为空的时候才写，为空的字段自动隐形，不留痕迹
                if conf["module_category"]:
                    lines.append(f"\t\t\tmodule_category = {conf['module_category']}")
                if conf["module"]:
                    lines.append(f"\t\t\tmodule = {conf['module']}")

                # 费用非空且大于 0 时记录，智能转整对齐排版
                if conf["convert_cost_ic"] is not None and conf["convert_cost_ic"] > 0:
                    formatted_cost = int(conf["convert_cost_ic"]) if conf["convert_cost_ic"].is_integer() else conf[
                        "convert_cost_ic"]
                    lines.append(f"\t\t\tconvert_cost_ic = {formatted_cost}")

                lines.append("\t\t}")

    conn.close()
    print("🎉 第六步 可改装来源块合流追加完毕！")
    return intermediary_modules_dict


def finalize_and_export_module_files(db_path, intermediary_modules_dict, output_dir="./output_modules"):
    """
    模块流水线最终落盘闭环阶段：
    1. 为每个模块追加闭合大括号 "\t}"
    2. 查询 m_modules_limit 表关联 mlid 触发器
    3. 按照 generate_file 与 mlid 进行双重无损块聚合，生成标准的 equipment_modules 文本文件。
    """
    if not intermediary_modules_dict:
        print("[提示] 中间体字典为空，未生成任何模块配置文件。")
        return

    # ============================================================
    # 阶梯 1：为中间体字典中所有模块的 lines 列表追加闭合大括号 "\t}"
    # ============================================================
    for module_data in intermediary_modules_dict.values():
        if "lines" in module_data and isinstance(module_data["lines"], list):
            module_data["lines"].append("\t}")

    # ============================================================
    # 阶梯 2：连通数据库，把所有的 mlid 和 limit 限制条件拉平载入内存缓存
    # ============================================================
    if not os.path.exists(db_path):
        print(f"[错误] 数据库不存在，无法读取 mlid 外键映射: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    limit_map = {}
    try:
        # 使用方括号转义 SQLite 保留字 [limit]
        cursor.execute("SELECT mlid, [limit] FROM m_modules_limit")
        for mlid, lim_text in cursor.fetchall():
            limit_map[mlid] = lim_text.strip() if lim_text else ""
    except sqlite3.Error as e:
        print(f"[错误] 读取 m_modules_limit 条件表失败: {e}")
        conn.close()
        return
    finally:
        conn.close()

    # ============================================================
    # 阶梯 3：按 generate_file -> mlid 对模块进行多维空间聚合
    # 数据嵌套结构：{ "00_tank_modules.txt": { 1: [line1, line2, ...], 2: [...] } }
    # ============================================================
    file_structures = {}

    for mid, m_data in intermediary_modules_dict.items():
        gen_file = m_data["generate_file"]
        mlid = m_data["mlid"]
        module_lines = m_data["lines"]

        # 规范化文件名输出（补齐或者统一 modules/ 目录前缀，根据你的部署需求可调）
        if not gen_file.startswith("modules/"):
            gen_file = f"modules/{gen_file}"

        # 第一层：初始化目标文件容器
        if gen_file not in file_structures:
            file_structures[gen_file] = {}

        # 第二层：将相同 mlid 的模块行列表挂载到同一个限制槽位下
        if mlid not in file_structures[gen_file]:
            file_structures[gen_file][mlid] = []

        # 将当前模块的所有行拷贝合并注入
        file_structures[gen_file][mlid].extend(module_lines)

    # ============================================================
    # 阶梯 4：严格按照 P 社编译标准进行多块代码文本渲染与落盘
    # ============================================================
    os.makedirs(output_dir, exist_ok=True)

    print("🚀 正在结合 mlid 触发大括号并渲染出最终的模块资产配置文件...")

    for full_file_path, mlid_groups in file_structures.items():
        final_file_lines = []

        # 顺着 mlid 组进行平铺渲染（例如一个文件里有 mlid=1 和 mlid=2 两个条件大块）
        for mlid, aggregated_lines in mlid_groups.items():
            # 获取当前 mlid 对应的 limit 文本
            limit_clause = limit_map.get(mlid, "")

            # 🌲 编译开启当前限制条件下的全局头外壳
            final_file_lines.append("equipment_modules = {")

            if limit_clause:
                # 兼容你清洗时保存的带大括号或单行结构的 limit 内容
                # 比如：limit = { has_dlc = "Gotterdammerung" }
                final_file_lines.append(f"\tlimit = {{ {limit_clause} }}")

            # 🌲 灌入所有绑定在此限制条件下的独立模块内部代码行
            final_file_lines.extend(aggregated_lines)

            # 🌲 闭合当前的全局头外壳
            final_file_lines.append("}\n")

        # 计算物理落盘的真实完整文件名
        pure_filename = os.path.basename(full_file_path)
        target_phys_path = os.path.join(output_dir, pure_filename)

        # 落地：严格遵循无 BOM 的标准 UTF-8 和 Unix 换行符
        with open(target_phys_path, "w", encoding="utf-8", newline="\n") as out_f:
            out_f.write("\n".join(final_file_lines))

        print(f"📝 [生成成功] 模块资产池配置文件已完美重构写入: {target_phys_path}")

    print("🎉 全套模块反向编译、冲突合并去重与多层级条件大括号组装流水线已完美闭环！")


def export_module(db_path, output_dir="./mod_output"):
    a = compile_modules_to_intermediary(db_path)
    b = append_module_subtables_to_intermediary(db_path, a)
    c = append_module_flat_subtables_to_intermediary(db_path, b)
    d = append_module_mix_subtables_to_intermediary(db_path, c)
    e = append_module_mission_type_stats_to_intermediary(db_path, d)
    f = append_module_conversion_sources_to_intermediary(db_path, e)
    finalize_and_export_module_files(db_path, f, "./mod_output")


# ============================================================
# ⚙️ 全局核心静态配置变量（装备主表专用配置流）
# ============================================================

# 1. 类似布尔值的字段清单（1 映射为 yes，0 映射为 no，为空不填）
EQUIPMENT_BOOL_FIELDS = [
    "active", "is_archetype", "is_convertable", "is_buildable", "supply_truck"
]
# 2. 基础常规属性列与 PDX 脚本实际属性键名的映射
EQUIPMENT_BASE_STAT_MAP = {
    "group_by": "group_by",
    "picture": "picture",
    "fuel_consumption": "fuel_consumption",
    "build_cost_ic": "build_cost_ic",
    "additional_collateral_damage": "additional_collateral_damage",
    "lend_lease_cost": "lend_lease_cost",
    "maximum_speed": "maximum_speed",
    "interface_category": "interface_category",
    "manpower": "manpower",
    "year": "year",
    "reliability": "reliability",
    "priority": "priority",
    "sprite": "sprite",
    "visual_level": "visual_level",
    "abbreviation": "abbreviation"
}
# 3. 资源开销列映射（一维平铺映射为 resources = { ... } 嵌套块）
EQUIPMENT_RESOURCE_MAP = [
    ("oil", "resource_oil"),
    ("aluminium", "resource_aluminium"),
    ("rubber", "resource_rubber"),
    ("tungsten", "resource_tungsten"),
    ("chromium", "resource_chromium"),
    ("steel", "resource_steel"),
    ("coal", "resource_coal")
]
EQUIPMENT_HIGH_STAT_MAP = ALL_STAT_MAP_REVERSED


def compile_equipments_to_intermediary(db_path):
    """
    装备重构流水线第一步（动态列优化版）：自动从元数据获取表的所有列，无损全开放生成流转字典。
    注：外部已提供全局常量 EQUIPMENT_BOOL_FIELDS, EQUIPMENT_BASE_STAT_MAP, EQUIPMENT_RESOURCE_MAP, EQUIPMENT_HIGH_STAT_MAP。
    """
    if not os.path.exists(db_path):
        print(f"[错误] 数据库不存在: {db_path}")
        return {}

    conn = sqlite3.connect(db_path)
    # 🎯 核心机制：让查询返回可以通过列名访问的 Row 对象，同时它也是一个类字典结构，支持 row.keys() 动态获取列名
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # 🚀 动态安全打法：直接全量 SELECT，不再拼接任何硬编码列名数组
        cursor.execute("SELECT * FROM equipments")
        rows = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"[错误] 动态读取装备主表失败，请核对表是否存在: {e}")
        conn.close()
        return {}

    intermediary_equipments_dict = {}

    print("🔄 正在通过【动态列自适应流】深度还原装备基础资产树...")

    for row in rows:
        eid = row["eid"]
        lines = []

        # 1. 喷吐装备头部
        lines.append(f"\t{eid} = {{")

        # 🚀 ✨ 动态列核心机制：直接从当前行数据中反向捞取数据库中真实存在的全部列名
        all_db_columns = row.keys()

        # 2. 处理 bool 属性映射 (1 -> yes, 0 -> no)
        for bool_col in EQUIPMENT_BOOL_FIELDS:
            if bool_col in all_db_columns:
                val = row[bool_col]
                if val is not None:
                    bool_str = "yes" if val == 1 else "no"
                    lines.append(f"\t\t{bool_col} = {bool_str}")

        # 3. 映射常规基础与细分属性
        for db_col, pdx_key in EQUIPMENT_BASE_STAT_MAP.items():
            if db_col in all_db_columns:
                val = row[db_col]
                if val is not None and val != "":
                    if isinstance(val, str) and db_col in ("abbreviation"):
                        lines.append(f'\t\t{pdx_key} = "{val}"')
                    else:
                        formatted_v = int(val) if isinstance(val, float) and val.is_integer() else val
                        lines.append(f"\t\t{pdx_key} = {formatted_v}")

        # 4. 组装嵌套的资源消耗块 resources = { ... }
        resource_lines = []
        for res_name, res_col in EQUIPMENT_RESOURCE_MAP:
            if res_col in all_db_columns:
                r_val = row[res_col]
                if r_val and r_val > 0:
                    resource_lines.append(f"\t\t\t{res_name} = {r_val}")
        if resource_lines:
            lines.append("\t\tresources = {")
            lines.extend(resource_lines)
            lines.append("\t\t}")

        # 5. 平铺展开高维细分陆海空战斗属性
        for db_col, pdx_key in EQUIPMENT_HIGH_STAT_MAP.items():
            if db_col in all_db_columns:
                val = row[db_col]
                if val is not None and val != 0:
                    formatted_v = int(val) if isinstance(val, float) and val.is_integer() else val
                    lines.append(f"\t\t{pdx_key} = {formatted_v}")

        # 6. 核心特判：当 module_inherit 激活时，写入一维继承标志
        if "module_inherit" in all_db_columns and row["module_inherit"] == 1:
            lines.append("\t\tmodule_slots = inherit")

        # 7. 原汁原味还原 others 残余脚本段
        if "others" in all_db_columns and row["others"]:
            lines.append(f"\t\t{row['others'].strip()}")

        # 8. 装填进入待流转的全局开放字典
        intermediary_equipments_dict[eid] = {
            "generate_file": row["generate_file"] if "generate_file" in all_db_columns else "units/equipments/default.txt",
            "lines": lines
        }

    conn.close()
    print(f"🎉 动态列加载完成！已在内存中全开放缓存 {len(intermediary_equipments_dict)} 个装备的核心数据行。")
    return intermediary_equipments_dict


def append_equipment_flat_subtables_to_intermediary(db_path, intermediary_equipments_dict):
    """
    装备重构流水线第二步：将需要平铺多行输出的关联表数据（archetype, allow_mission_type,
    derived_variant_name, type）以单行重复（key = value）的形式追加进装备中间体行列表中。
    """
    if not os.path.exists(db_path) or not intermediary_equipments_dict:
        return intermediary_equipments_dict

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. 配置平铺表元数据清单 (数据库表名, 最终生成的 PDX 键名, 存储值的列名)
    EQUIP_FLAT_TABLES_CONFIG = [
        ("parent", "parent", "parent"),
        ("archetype", "archetype", "archetype"),
        ("allow_mission_type", "allow_mission_type", "type"),
        ("derived_variant_name", "derived_variant_name", "derived_variant_name"),
        ("type", "type", "type")
    ]

    print("🔄 正在读取装备平铺关联表，动态追加单行属性（key = value）...")

    # 2. 依次处理每一个需要平铺多行的装备子表
    for table_name, pdx_key, column_name in EQUIP_FLAT_TABLES_CONFIG:
        # 按 eid 排序确保数据流聚合的连续性与稳定性
        query = f"SELECT eid, {column_name} FROM {table_name} ORDER BY eid"
        try:
            cursor.execute(query)
            rows = cursor.fetchall()
        except sqlite3.Error as e:
            print(f"[提示] 读取装备平铺表 {table_name} 失败或表不存在，跳过处理。原因: {e}")
            continue

        # 内存映射聚合：将一个 eid 对应的多个平铺值收集到列表中
        flat_data_map = {}
        for eid, val in rows:
            if val is None or val == "":
                continue

            # 💡 强核自适应转换：如果 val 带有 .txt 后缀（如在某些衍生变体命名配置中），
            # 或者是字符串文本，按需进行规范化去重去空
            val_str = str(val).strip()
            if not val_str:
                continue

            if eid not in flat_data_map:
                flat_data_map[eid] = []
            flat_data_map[eid].append(val_str)

        # 3. 核心平铺逻辑：打破大括号约束，每一个元素直接单独喷吐占领一行
        for eid, values in flat_data_map.items():
            if eid in intermediary_equipments_dict:
                lines = intermediary_equipments_dict[eid]["lines"]

                # 顺着数值列表循环，直接生成多行并列的扁平资产代码
                for val in values:
                    lines.append(f'\t\t{pdx_key} = {val}')
                    # # 如果是带引号的复杂命名（比如派生变体名），可以视原版规范保留或直接输出
                    # if pdx_key == "derived_variant_name" and not val.startswith('"'):
                    #     lines.append(f'\t\t{pdx_key} = {val}')
                    # else:
                    #     lines.append(f"\t\t{pdx_key} = {val}")

    conn.close()
    print("🎉 第二步 装备扁平单行属性追加完毕！数据流正继续向后平稳流转。")
    return intermediary_equipments_dict


def append_equipment_nested_subtables_to_intermediary(db_path, intermediary_equipments_dict):
    """
    装备重构流水线第三步：将 1:N 纯列表大括号嵌套关系子表数据（can_convert_from, upgrades）
    批量追加进装备中间体行列表中。
    """
    if not os.path.exists(db_path) or not intermediary_equipments_dict:
        return intermediary_equipments_dict

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. 配置嵌套表元数据清单 (数据库表名, 最终生成的 PDX 键名, 存储值的列名)
    EQUIP_NEST_TABLES_CONFIG = [
        ("can_convert_from", "can_convert_from", "from_eid"),
        ("upgrades", "upgrades", "upgrade")
    ]

    print("🔄 正在读取装备大括号嵌套关联表，动态追加内部属性块...")

    # 2. 依次遍历处理每一个嵌套子表
    for table_name, pdx_key, column_name in EQUIP_NEST_TABLES_CONFIG:
        # 使用第一个字段（关联外部主表的 eid 或 give_eid）进行排序聚合
        # 注意：can_convert_from 表的主键列是 give_eid
        main_id_col = "give_eid" if table_name == "can_convert_from" else "eid"

        query = f"SELECT {main_id_col}, {column_name} FROM {table_name} ORDER BY {main_id_col}"
        try:
            cursor.execute(query)
            rows = cursor.fetchall()
        except sqlite3.Error as e:
            print(f"[提示] 读取装备嵌套表 {table_name} 失败或表不存在，跳过处理。原因: {e}")
            continue

        # 内存映射聚合：将一个主装备 eid 对应的多个子弹头/升级项收集到列表中
        nest_data_map = {}
        for m_id, val in rows:
            if val is None or val == "":
                continue
            val_str = str(val).strip()
            if not val_str:
                continue

            if m_id not in nest_data_map:
                nest_data_map[m_id] = []
            nest_data_map[m_id].append(val_str)

        # 3. 核心大括号包裹组装逻辑
        for m_id, items in nest_data_map.items():
            if m_id in intermediary_equipments_dict:
                lines = intermediary_equipments_dict[m_id]["lines"]

                # 开启大括号外壳
                lines.append(f"\t\t{pdx_key} = {{")
                # 遍历将数组里的每一个独立字符串节点写入新行
                for item in items:
                    lines.append(f"\t\t\t{item}")
                # 闭合大括号外壳
                lines.append("\t\t}")

    conn.close()
    print("🎉 第三步 装备大括号紧凑嵌套块追加完毕！继续维持不封口状态。")
    return intermediary_equipments_dict


def append_equipment_slots_controls_to_intermediary(db_path, intermediary_equipments_dict):
    """
    装备重构流水线第四步：解析 1:N 嵌套大括号且带有特殊符号拼接的子表数据
    （default_modules, module_count_limit）追加进装备中间体行列表中。
    """
    if not os.path.exists(db_path) or not intermediary_equipments_dict:
        return intermediary_equipments_dict

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # ============================================================
    # 1. 解析 default_modules 表 (标准大括号键值对)
    # ============================================================
    print("🔄 正在读取 default_modules 表，动态追加默认插槽预装块...")
    try:
        cursor.execute("SELECT eid, msid, value FROM default_modules ORDER BY eid")
        dm_rows = cursor.fetchall()

        dm_map = {}
        for row in dm_rows:
            eid = row["eid"]
            if eid not in dm_map:
                dm_map[eid] = []
            dm_map[eid].append((row["msid"].strip(), row["value"].strip()))

        for eid, kv_pairs in dm_map.items():
            if eid in intermediary_equipments_dict:
                lines = intermediary_equipments_dict[eid]["lines"]
                lines.append("\t\tdefault_modules = {")
                for msid, val in kv_pairs:
                    lines.append(f"\t\t\t{msid} = {val}")
                lines.append("\t\t}")
    except sqlite3.Error as e:
        print(f"[提示] 读取 default_modules 失败或表不存在: {e}")

    # ============================================================
    # 2. 解析 module_count_limit 表 (特殊运算符平铺嵌套)
    # ============================================================
    print("🔄 正在读取 module_count_limit 表，动态追加插槽数量限制块...")
    try:
        cursor.execute("SELECT eid, mid, category_id, count FROM module_count_limit ORDER BY eid")
        mcl_rows = cursor.fetchall()

        mcl_map = {}
        for row in mcl_rows:
            eid = row["eid"]
            if eid not in mcl_map:
                mcl_map[eid] = []
            mcl_map[eid].append({
                "mid": row["mid"].strip() if row["mid"] else None,
                "category_id": row["category_id"].strip() if row["category_id"] else None,
                "count": row["count"].strip() if row["count"] else None
            })

        for eid, limit_list in mcl_map.items():
            if eid in intermediary_equipments_dict:
                lines = intermediary_equipments_dict[eid]["lines"]

                # ✨ 核心处理：由于一个装备里可以有多个并列的 module_count_limit 块，循环写出
                for limit_data in limit_list:
                    lines.append("\t\tmodule_count_limit = {")

                    # 互斥嗅探非空写出
                    if limit_data["mid"]:
                        lines.append(f"\t\t\tmodule = {limit_data['mid']}")
                    if limit_data["category_id"]:
                        lines.append(f"\t\t\tcategory = {limit_data['category_id']}")

                    # 🎯 核心防线：count 在 P 社里是 "count < 2"，所以直接当字符串并列喷吐，绝不能加等号
                    if limit_data["count"]:
                        lines.append(f"\t\t\tcount {limit_data['count']}")

                    lines.append("\t\t}")
    except sqlite3.Error as e:
        print(f"[提示] 读取 module_count_limit 失败或表不存在: {e}")

    conn.close()
    print("🎉 第四步 装备控制子表追加完毕！")
    return intermediary_equipments_dict


def append_equipment_module_slots_to_intermediary(db_path, intermediary_equipments_dict):
    """
    装备重构流水线第五步（插槽树级联）：
    1. 校验全局 module_inherit 状态冲突并喷吐警告
    2. 深度联表聚合 module_slots 与 allowed_module_categories
    3. 完美还原大括号嵌套树或插槽级一维 "slot_id = inherit" 语法。
    """
    if not os.path.exists(db_path) or not intermediary_equipments_dict:
        return intermediary_equipments_dict

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("🔄 正在读取插槽主子表，开始构建高维模块插槽树（module_slots）...")

    # 1. 核心联合查询：将具体插槽数据和它的允许分类（allowed_module_categories）一口气拉出
    # 按照 eid, msid 物理排序，保证数据流在内存中连续、不发生错位
    query = """
        SELECT 
            s.msid, s.eid, s.slot_id, s.required, s.inherit,
            c.module_categorie
        FROM module_slots s
        LEFT JOIN allowed_module_categories c ON s.msid = c.msid
        ORDER BY s.eid, s.msid
    """

    try:
        cursor.execute(query)
        rows = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"[提示] 读取插槽树失败或表不存在，跳过处理。原因: {e}")
        conn.close()
        return intermediary_equipments_dict

    # 2. 深度多维空间聚合
    # 数据嵌套结构：{ eid: { slot_id: { "required": 1, "inherit": 0, "categories": [...] } } }
    slots_accumulator = {}

    for row in rows:
        eid = row["eid"]
        slot_id = row["slot_id"]
        msid = row["msid"]

        # 过滤孤立装备数据
        if eid not in intermediary_equipments_dict:
            continue

        # 嵌套层级动态初始化
        if eid not in slots_accumulator:
            slots_accumulator[eid] = {}
        if slot_id not in slots_accumulator[eid]:
            slots_accumulator[eid][slot_id] = {
                "required": row["required"],
                "inherit": row["inherit"],
                "categories": []
            }

        # 压入当前插槽允许的模块分类（过滤空值）
        if row["module_categorie"]:
            slots_accumulator[eid][slot_id]["categories"].append(row["module_categorie"].strip())

    # ============================================================
    # 3. 核心冲突检测与技术文本渲染
    # ============================================================
    for eid, slots_tree in slots_accumulator.items():
        lines = intermediary_equipments_dict[eid]["lines"]

        # ✨ 核心防线：检查第一步生成的行中是否已经带有 "module_slots = inherit"
        # 通过在已有 lines 列表中物理搜寻来判定，彻底解耦
        if any("module_slots = inherit" in line for line in lines):
            print(
                f"⚠️ [插槽树冲突警告] 装备 {eid} 已经在主表中声明了全局 module_inherit = 1，但子表中依然存在其特化的具体插槽配置行！接着输出以确保资产完备。")

        # 开启插槽树的全局外壳
        lines.append("\t\tmodule_slots = {")

        # 遍历装备下的每一个独立插槽
        for slot_id, slot_data in slots_tree.items():

            # 🟢 场景 A：命中插槽级特化继承（inherit = 1）
            if slot_data["inherit"] == 1:
                lines.append(f"\t\t\t{slot_id} = inherit")

            # 🔵 场景 B：正常的大括号嵌套插槽属性树
            else:
                lines.append(f"\t\t\t{slot_id} = {{")

                # 转换必填状态 bool (1 -> yes, 0 -> no)
                req_str = "yes" if slot_data["required"] == 1 else "no"
                lines.append(f"\t\t\t\trequired = {req_str}")

                # 追加分类限制块
                if slot_data["categories"]:
                    lines.append("\t\t\t\tallowed_module_categories = {")
                    for category in slot_data["categories"]:
                        lines.append(f"\t\t\t\t\t{category}")
                    lines.append("\t\t\t\t}")

                lines.append("\t\t\t}")

        # 闭合插槽树的全局外壳
        lines.append("\t\t}")

    conn.close()
    print("🎉 第五步 级联多维模块插槽树追加完毕！数据链高完备开放。")
    return intermediary_equipments_dict


def finalize_and_export_equipment_files(intermediary_equipments_dict, output_dir="./output_equipments"):
    """
    装备流水线最终收尾落盘阶段（带语法重排优化版）：
    1. 特殊处理 "module_slots = inherit"，将其物理位置移动到当前装备体内部的最后一行。
    2. 为所有装备的 lines 列表安全补上尾部闭合大括号 "\t}"
    3. 根据 generate_file 路径进行纯粹的文件分类并执行物理写出。
    """
    if not intermediary_equipments_dict:
        print("[提示] 装备中间体字典为空，未生成任何配置文件。")
        return

    # ============================================================
    # 阶梯 1：语法位置调优，将 module_slots = inherit 强制移动到末尾并封口
    # ============================================================
    for equip_data in intermediary_equipments_dict.values():
        if "lines" in equip_data and isinstance(equip_data["lines"], list):
            lines = equip_data["lines"]

            # ✨ 核心重排机制：寻找是否包含目标继承单行
            inherit_line = None
            for line in lines:
                if "module_slots = inherit" in line:
                    inherit_line = line
                    break

            # 如果存在，将其从原有队列里剔除，并安全插到当前列表的最末尾
            if inherit_line:
                lines.remove(inherit_line)
                lines.append(inherit_line)

            # 补上尾部闭合大括号 "\t}"
            lines.append("\t}")

    # ============================================================
    # 阶梯 2：直接按 generate_file 进行一维路径分类聚合
    # ============================================================
    file_output_structures = {}

    for eid, e_data in intermediary_equipments_dict.items():
        gen_file = e_data["generate_file"]
        equip_lines = e_data["lines"]

        if not gen_file or not isinstance(gen_file, str):
            gen_file = "common/units/equipments/default_equipments.txt"

        gen_file = gen_file.replace("\\", "/")

        if gen_file not in file_output_structures:
            file_output_structures[gen_file] = []

        file_output_structures[gen_file].extend(equip_lines)

    # ============================================================
    # 阶梯 3：顶级语法外壳渲染与物理落盘
    # ============================================================
    os.makedirs(output_dir, exist_ok=True)

    print("🚀 正在通过【后置重排流】，渲染最终的装备（Equipments）资产池文本...")

    for rel_file_path, aggregated_lines in file_output_structures.items():
        final_file_content = []
        final_file_content.append("equipments = {")
        final_file_content.extend(aggregated_lines)
        final_file_content.append("}")

        full_output_path = os.path.join(output_dir, rel_file_path)
        sub_file_dir = os.path.dirname(full_output_path)
        if sub_file_dir:
            os.makedirs(sub_file_dir, exist_ok=True)

        with open(full_output_path, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(final_file_content))

        print(f"📄 [重排编译成功] 装备配置文件已安全写出: {full_output_path}")

    print("\n🎉 装备后置重排优化完毕，全系统流水线完美闭环！")


def export_equipment(db_path, output_dir="./mod_output/equipments"):
    a = compile_equipments_to_intermediary(db_path)
    b = append_equipment_flat_subtables_to_intermediary(db_path, a)
    c = append_equipment_nested_subtables_to_intermediary(db_path, b)
    d = append_equipment_module_slots_to_intermediary(db_path, c)
    e = append_equipment_slots_controls_to_intermediary(db_path, d)
    finalize_and_export_equipment_files(e, output_dir)
    # z = e
    # print("\n".join(z["medium_tank_chassis"]["lines"]))
    # print("\n".join(z["medium_tank_chassis_0"]["lines"]))
    # print("\n".join(z["small_plane_airframe_0"]["lines"]))


if __name__ == "__main__":
    db_path = "./em.db"
    # export_module(db_path)
    export_equipment(db_path)



