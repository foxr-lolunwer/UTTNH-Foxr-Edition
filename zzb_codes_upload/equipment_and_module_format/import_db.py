import os
import re
import sqlite3
import json

# ============================================================
# 数据库 DDL —— 完全对齐 export.json 结构，并补充缺失的表
# ============================================================

DDL_STATEMENTS = [
    # === 装备主表 ===
    """CREATE TABLE IF NOT EXISTS equipments (
        eid TEXT PRIMARY KEY,
        active INTEGER,
        is_archetype INTEGER,
        is_convertable INTEGER,
        is_buildable INTEGER,
        supply_truck INTEGER,
        group_by TEXT,
        picture TEXT,
        fuel_consumption REAL,
        build_cost_ic REAL,
        additional_collateral_damage REAL,
        lend_lease_cost REAL,
        maximum_speed REAL,
        interface_category TEXT,
        manpower INTEGER,
        year INTEGER,
        resource_oil INTEGER,
        resource_aluminium INTEGER,
        resource_rubber INTEGER,
        resource_tungsten INTEGER,
        resource_chromium INTEGER,
        resource_steel INTEGER,
        resource_coal INTEGER,
        reliability REAL,
        priority REAL,
        sprite TEXT,
        visual_level INTEGER,
        l_air_attack REAL,
        l_ap_attack REAL,
        l_armor_value REAL,
        l_breakthrough REAL,
        l_defense REAL,
        l_hard_attack REAL,
        l_hardness REAL,
        l_max_military_factories REAL,
        l_railway_gun_attack REAL,
        l_soft_attack REAL,
        a_air_agility REAL,
        a_air_defence REAL,
        a_air_map_icon_frame REAL,
        a_air_range REAL,
        a_air_superiority REAL,
        a_interface_overview_category_index REAL,
        a_naval_strike_attack REAL,
        a_naval_strike_targetting REAL,
        a_weight REAL,
        n_anti_air_attack REAL,
        n_armor_value REAL,
        n_carrier_size REAL,
        n_hg_armor_piercing REAL,
        n_hg_attack REAL,
        n_lg_armor_piercing REAL,
        n_lg_attack REAL,
        n_max_organisation REAL,
        n_max_strength REAL,
        n_naval_dominance_factor REAL,
        n_naval_range REAL,
        n_naval_speed REAL,
        n_offensive_weapons INTEGER,
        n_sub_attack REAL,
        n_sub_detection REAL,
        n_sub_visibility REAL,
        n_surface_detection REAL,
        n_surface_visibility REAL,
        n_torpedo_attack REAL,
        n_visual_tech_level_addition REAL,
        abbreviation TEXT,
        module_inherit INTEGER,
        others TEXT,
        generate_file TEXT NOT NULL
    )""",

    # === 装备子表 ===
    """CREATE TABLE IF NOT EXISTS parent (
        eid    TEXT REFERENCES equipments (eid) ON DELETE CASCADE NOT NULL,
        parent TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS type (
        eid TEXT REFERENCES equipments(eid) ON DELETE CASCADE NOT NULL,
        type TEXT NOT NULL
    )""",

    """CREATE TABLE IF NOT EXISTS can_convert_from (
        give_eid TEXT REFERENCES equipments(eid) ON DELETE CASCADE NOT NULL,
        from_eid TEXT REFERENCES equipments(eid) ON DELETE CASCADE NOT NULL
    )""",

    """CREATE TABLE IF NOT EXISTS upgrades (
        eid TEXT REFERENCES equipments(eid) ON DELETE CASCADE NOT NULL,
        upgrade TEXT NOT NULL
    )""",

    """CREATE TABLE IF NOT EXISTS archetype (
        eid TEXT REFERENCES equipments(eid) ON DELETE CASCADE NOT NULL,
        archetype TEXT REFERENCES equipments(eid) ON DELETE CASCADE NOT NULL
    )""",

    """CREATE TABLE IF NOT EXISTS derived_variant_name (
        eid TEXT REFERENCES equipments(eid) ON DELETE CASCADE NOT NULL,
        derived_variant_name TEXT
    )""",

    """CREATE TABLE IF NOT EXISTS allow_mission_type (
        eid TEXT REFERENCES equipments(eid) ON DELETE CASCADE NOT NULL,
        type TEXT NOT NULL
    )""",

    """CREATE TABLE IF NOT EXISTS module_slots (
        msid INTEGER PRIMARY KEY AUTOINCREMENT,
        eid TEXT REFERENCES equipments(eid) ON DELETE CASCADE NOT NULL,
        slot_id TEXT NOT NULL,
        required INTEGER NOT NULL,
        inherit INTEGER
    )""",

    """CREATE TABLE IF NOT EXISTS allowed_module_categories (
        msid INTEGER NOT NULL
            REFERENCES module_slots (msid) ON DELETE CASCADE,
        module_categorie TEXT NOT NULL
    )""",

    """CREATE TABLE IF NOT EXISTS default_modules (
        eid TEXT REFERENCES equipments(eid) ON DELETE CASCADE NOT NULL,
        msid TEXT NOT NULL,
        value TEXT NOT NULL
    )""",

    """CREATE TABLE IF NOT EXISTS module_count_limit (
        eid TEXT REFERENCES equipments(eid) ON DELETE CASCADE NOT NULL,
        mid TEXT,
        category_id TEXT,
        count TEXT
    )""",

    # === 模块主表 ===
    """CREATE TABLE IF NOT EXISTS m_modules (
        mid TEXT PRIMARY KEY,
        abbreviation TEXT,
        category TEXT,
        sfx TEXT,
        xp_cost REAL,
        dismantle_cost_ic REAL,
        build_cost_resources_oil INTEGER,
        build_cost_resources_aluminium INTEGER,
        build_cost_resources_rubber INTEGER,
        build_cost_resources_tungsten INTEGER,
        build_cost_resources_steel INTEGER,
        build_cost_resources_chromium INTEGER,
        build_cost_resources_coal INTEGER,
        mlid INTEGER DEFAULT 0,
        gui_category TEXT,
        dismantle_cost_resources_oil INTEGER,
        dismantle_cost_resources_aluminium INTEGER,
        dismantle_cost_resources_rubber INTEGER,
        dismantle_cost_resources_tungsten INTEGER,
        dismantle_cost_resources_steel INTEGER,
        dismantle_cost_resources_chromium INTEGER,
        dismantle_cost_resources_coal INTEGER,
        others TEXT,
        generate_file TEXT NOT NULL
    )""",

    """CREATE TABLE IF NOT EXISTS m_parent (
        mid TEXT REFERENCES m_modules(mid) ON DELETE CASCADE NOT NULL,
        parent TEXT NOT NULL
    )""",

    """CREATE TABLE IF NOT EXISTS m_add_equipment_type (
        mid TEXT REFERENCES m_modules(mid) ON DELETE CASCADE NOT NULL,
        type TEXT NOT NULL
    )""",

    """CREATE TABLE IF NOT EXISTS m_allow_mission_type (
        mid TEXT REFERENCES m_modules(mid) ON DELETE CASCADE NOT NULL,
        type TEXT NOT NULL
    )""",

    """CREATE TABLE IF NOT EXISTS m_module_forbid_equipment_type (
        mid TEXT REFERENCES m_modules(mid) ON DELETE CASCADE NOT NULL,
        equipment_type TEXT NOT NULL
    )""",

    """CREATE TABLE IF NOT EXISTS m_module_forbid_equipment_type_exact_match (
        mid TEXT REFERENCES m_modules(mid) ON DELETE CASCADE NOT NULL,
        equipment_type_exact_match TEXT NOT NULL
    )""",

    """CREATE TABLE IF NOT EXISTS m_module_forbid_equipment_type_exact_match_for_category (
        mid TEXT REFERENCES m_modules(mid) ON DELETE CASCADE,
        category TEXT NOT NULL,
        equipment_type_exact_match TEXT NOT NULL
    )""",

    """CREATE TABLE IF NOT EXISTS m_allow_equipment_type (
        mid                  TEXT REFERENCES m_modules (mid) ON DELETE CASCADE
                                  NOT NULL,
        type TEXT NOT NULL
    )""",

    # === 模块统计 ===
    """CREATE TABLE IF NOT EXISTS m_module_stats (
        stats_id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL,
        mid TEXT REFERENCES m_modules(mid) ON DELETE CASCADE NOT NULL,
        build_cost_ic REAL,
        fuel_consumption REAL,
        maximum_speed REAL,
        reliability REAL,
        l_air_attack REAL,
        l_ap_attack REAL,
        l_armor_value REAL,
        l_breakthrough REAL,
        l_defense REAL,
        l_entrenchment REAL,
        l_fuel_capacity REAL,
        l_hard_attack REAL,
        l_hardness REAL,
        l_soft_attack REAL,
        a_air_agility REAL,
        a_air_attack REAL,
        a_air_bombing REAL,
        a_air_defence REAL,
        a_air_ground_attack REAL,
        a_air_range REAL,
        a_mines_planting REAL,
        a_mines_sweeping REAL,
        a_night_penalty REAL,
        a_sub_detection REAL,
        a_surface_detection REAL,
        a_thrust REAL,
        a_weight REAL,
        a_naval_strike_attack REAL,
        a_naval_strike_targetting REAL,
        n_anti_air_attack REAL,
        n_armor_value REAL,
        n_carrier_size REAL,
        n_carrier_sub_detection REAL,
        n_carrier_surface_detection REAL,
        n_convoy_raiding_coordination REAL,
        n_hg_armor_piercing REAL,
        n_lg_armor_piercing REAL,
        n_max_strength REAL,
        n_mines_planting REAL,
        n_mines_sweeping REAL,
        n_naval_heavy_gun_hit_chance_factor REAL,
        n_naval_light_gun_hit_chance_factor REAL,
        n_naval_range REAL,
        n_naval_speed REAL,
        n_naval_torpedo_damage_reduction_factor REAL,
        n_naval_torpedo_enemy_critical_chance_factor REAL,
        n_naval_torpedo_hit_chance_factor REAL,
        n_naval_weather_penalty_factor REAL,
        n_sub_attack REAL,
        n_sub_detection REAL,
        n_sub_visibility REAL,
        n_submarine_carrier_size REAL,
        n_surface_detection REAL,
        n_torpedo_attack REAL
    )""",

    # === 模块限制 ===
    """CREATE TABLE IF NOT EXISTS m_modules_limit (
        mlid INTEGER PRIMARY KEY AUTOINCREMENT,
        "limit" TEXT
    )""",

    # === 模块转换来源 ===
    """CREATE TABLE IF NOT EXISTS m_can_convert_from (
        give_mid TEXT REFERENCES m_modules(mid) ON DELETE CASCADE NOT NULL,
        module TEXT,
        module_category TEXT,
        convert_cost_ic REAL
    )""",

    # === 模块关键部件 ===
    """CREATE TABLE IF NOT EXISTS m_critical_parts (
        mid TEXT REFERENCES m_modules(mid) ON DELETE CASCADE NOT NULL,
        critical_part TEXT NOT NULL
    )""",

    # === 模块禁止类别 ===
    """CREATE TABLE IF NOT EXISTS m_forbid_module_categories (
        mid TEXT REFERENCES m_modules(mid) ON DELETE CASCADE NOT NULL,
        forbid_module_categorie TEXT NOT NULL
    )""",

    # # === 任务类型统计限制 ===
    # """CREATE TABLE IF NOT EXISTS m_mission_type_stats_limit (
    #     mtslid  INTEGER PRIMARY KEY AUTOINCREMENT,
    #     [limit] TEXT    NOT NULL
    # )""",

    # === 任务类型统计 ===
    """CREATE TABLE IF NOT EXISTS m_mission_type_stats (
        mid TEXT REFERENCES m_modules(mid) ON DELETE CASCADE NOT NULL,
        [limit] TEXT NOT NULL,
        stats_id INTEGER REFERENCES m_module_stats(stats_id) ON DELETE CASCADE NOT NULL
    )""",
]

# ============================================================
# 字段映射：源文件键 → 数据库列名
# ============================================================

# 你可以手动把某个文件映射到 land / air / naval。
# 默认未命中时按 land 处理。
FILE_TYPE_MAP = {
    "infantry.txt": "land",
    "anti_air.txt": "land",
    "anti_tank.txt": "land",
    "artillery.txt": "land",
    "armored_car.txt": "land",
    "amechanized.txt": "land",
    "amphibious_mechanized.txt": "land",
    "mechanized.txt": "land",
    "motorized.txt": "land",
    "support.txt": "land",
    "tank_amphibious.txt": "land",
    "tank_chassis.txt": "land",
    "IFV.txt": "land",
    "railway_gun.txt": "land",
    "plane_airframes.txt": "air",
    "transport_plane.txt": "air",
    "ship_hull_carrier.txt": "naval",
    "ship_hull_cruiser.txt": "naval",
    "ship_hull_heavy.txt": "naval",
    "ship_hull_light.txt": "naval",
    "ship_hull_submarine.txt": "naval",
    "convoys.txt": "naval",
    "trains.txt": "land",
    "modules/00_plane_modules.txt": "air",
    "modules/00_ship_modules.txt": "naval",
    "modules/00_tank_modules.txt": "land",
}

# 装备主表：源文件中不带前缀的陆战属性 → 数据库 l_ 前缀列
LAND_STAT_MAP = {
    "soft_attack": "l_soft_attack",
    "hard_attack": "l_hard_attack",
    "ap_attack": "l_ap_attack",
    "air_attack": "l_air_attack",
    "defense": "l_defense",
    "breakthrough": "l_breakthrough",
    "hardness": "l_hardness",
    "armor_value": "l_armor_value",
    "entrenchment": "l_entrenchment",
    "fuel_capacity": "l_fuel_capacity",
    "max_military_factories": "l_max_military_factories",
    "railway_gun_attack": "l_railway_gun_attack",
}

# 模块统计：源文件中不带前缀的陆战属性 → 数据库 l_ 前缀列（与上面相同，但用于模块 add_stats / multiply_stats）
MODULE_LAND_STAT_MAP = {
    "soft_attack": "l_soft_attack",
    "hard_attack": "l_hard_attack",
    "ap_attack": "l_ap_attack",
    "air_attack": "l_air_attack",
    "defense": "l_defense",
    "breakthrough": "l_breakthrough",
    "hardness": "l_hardness",
    "armor_value": "l_armor_value",
    "entrenchment": "l_entrenchment",
    "fuel_capacity": "l_fuel_capacity",
}

# 装备主表：源文件中不带前缀的海军属性 → 数据库 n_ 前缀列
NAVAL_EQUIP_STAT_MAP = {
    "anti_air_attack": "n_anti_air_attack",
    "armor_value": "n_armor_value",
    "carrier_size": "n_carrier_size",
    "hg_attack": "n_hg_attack",
    "lg_attack": "n_lg_attack",
    "lg_armor_piercing": "n_lg_armor_piercing",
    "hg_armor_piercing": "n_hg_armor_piercing",
    "max_organisation": "n_max_organisation",
    "max_strength": "n_max_strength",
    "naval_dominance_factor": "n_naval_dominance_factor",
    "naval_range": "n_naval_range",
    "naval_speed": "n_naval_speed",
    "offensive_weapons": "n_offensive_weapons",
    "sub_attack": "n_sub_attack",
    "sub_detection": "n_sub_detection",
    "sub_visibility": "n_sub_visibility",
    "surface_detection": "n_surface_detection",
    "surface_visibility": "n_surface_visibility",
    "torpedo_attack": "n_torpedo_attack",
    "visual_tech_level_addition": "n_visual_tech_level_addition",
}
# 模块统计：源文件中不带前缀的海军属性 → 数据库 n_ 前缀列
MODULE_NAVAL_STAT_MAP = {
    "anti_air_attack": "n_anti_air_attack",
    "armor_value": "n_armor_value",
    "carrier_size": "n_carrier_size",
    "carrier_sub_detection": "n_carrier_sub_detection",
    "carrier_surface_detection": "n_carrier_surface_detection",
    "convoy_raiding_coordination": "n_convoy_raiding_coordination",
    "hg_armor_piercing": "n_hg_armor_piercing",
    "lg_armor_piercing": "n_lg_armor_piercing",
    "max_strength": "n_max_strength",
    "mines_planting": "n_mines_planting",
    "mines_sweeping": "n_mines_sweeping",
    "naval_heavy_gun_hit_chance_factor": "n_naval_heavy_gun_hit_chance_factor",
    "naval_light_gun_hit_chance_factor": "n_naval_light_gun_hit_chance_factor",
    "naval_torpedo_damage_reduction_factor": "n_naval_torpedo_damage_reduction_factor",
    "naval_torpedo_enemy_critical_chance_factor": "n_naval_torpedo_enemy_critical_chance_factor",
    "naval_torpedo_hit_chance_factor": "n_naval_torpedo_hit_chance_factor",
    "naval_weather_penalty_factor": "n_naval_weather_penalty_factor",
    "sub_detection": "n_sub_detection",
    "submarine_carrier_size": "n_submarine_carrier_size",
    "surface_detection": "n_surface_detection",
    "sub_visibility": "n_sub_visibility",
    "torpedo_attack": "n_torpedo_attack",
    "naval_range": "n_naval_range",
    "naval_speed": "n_naval_speed",
}

# 装备主表：源文件中不带前缀的空军属性 → 数据库 a_ 前缀列
AIR_EQUIP_STAT_MAP = {
    "air_agility": "a_air_agility",
    "air_defence": "a_air_defence",
    "air_map_icon_frame": "a_air_map_icon_frame",
    "air_range": "a_air_range",
    "air_superiority": "a_air_superiority",
    "interface_overview_category_index": "a_interface_overview_category_index",
    "naval_strike_attack": "a_naval_strike_attack",
    "naval_strike_targetting": "a_naval_strike_targetting",
    "weight": "a_weight",
}

# 模块统计：源文件中不带前缀的空军属性 → 数据库 a_ 前缀列
MODULE_AIR_STAT_MAP = {
    "air_agility": "a_air_agility",
    "air_attack": "a_air_attack",
    "air_bombing": "a_air_bombing",
    "air_defence": "a_air_defence",
    "air_ground_attack": "a_air_ground_attack",
    "air_range": "a_air_range",
    "mines_planting": "a_mines_planting",
    "mines_sweeping": "a_mines_sweeping",
    "night_penalty": "a_night_penalty",
    "sub_detection": "a_sub_detection",
    "surface_detection": "a_surface_detection",
    "thrust": "a_thrust",
    "weight": "a_weight",

    "naval_strike_attack": "a_naval_strike_attack",
    "naval_strike_targetting": "a_naval_strike_targetting",
}

# 合并：模块统计统一映射
# MODULE_STAT_MAP = {}
# MODULE_STAT_MAP.update(MODULE_LAND_STAT_MAP)
# MODULE_STAT_MAP.update(MODULE_NAVAL_STAT_MAP)
# MODULE_STAT_MAP.update(MODULE_AIR_STAT_MAP)

# 装备主表可直接识别的列名（不需要特殊映射）
KNOWN_EQUIP_COLS = {
    "active", "is_archetype", "is_convertable", "is_buildable", "supply_truck",
    "group_by", "picture", "fuel_consumption", "build_cost_ic",
    "additional_collateral_damage", "lend_lease_cost", "maximum_speed",
    "interface_category", "manpower", "year", "reliability", "priority",
    "sprite", "abbreviation", "visual_level",
}

# 装备主表完整有效列名
EQUIP_COLUMNS = None  # 运行时从数据库获取
MODULE_COLUMNS = None


# ============================================================
# 工具函数
# ============================================================

def clean_and_merge_file(file_path):
    """剥离注释并将全文件压缩合并为单行字符串"""
    cleaned_lines = []
    with open(file_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
        for line in f:
            if '#' in line:
                line = line.split('#')[0]
            cleaned_lines.append(line.strip())
    full_text = " ".join(cleaned_lines)
    return re.sub(r'\s+', ' ', full_text)


def extract_braced_content(text, start_pos):
    """大括号计数状态机：精准截取闭合大括号块"""
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
    """yes/no → 1/0，去引号"""
    if not token:
        return token
    if token.lower() == 'yes':
        return 1
    if token.lower() == 'no':
        return 0
    if len(token) >= 2 and token[0] == '"' and token[-1] == '"':
        return token[1:-1]
    return token


def get_table_columns(cursor, table_name):
    """获取指定表的列名列表"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [col[1] for col in cursor.fetchall()]


def get_file_type(file_path):
    """根据文件名/相对路径返回 land / air / naval。"""
    if not file_path:
        return "land"

    normalized = os.path.basename(file_path).replace('\\', '/')
    rel_path = file_path.replace('\\', '/')
    candidates = [normalized, rel_path, rel_path.split('/')[-1]]
    for candidate in candidates:
        if candidate in FILE_TYPE_MAP:
            return FILE_TYPE_MAP[candidate]
    return "land"


def get_equipment_stat_map(file_type):
    """根据文件类型返回装备属性映射。"""
    if file_type == "air":
        return {**LAND_STAT_MAP, **AIR_EQUIP_STAT_MAP}
    if file_type == "naval":
        return {**LAND_STAT_MAP, **NAVAL_EQUIP_STAT_MAP}
    return LAND_STAT_MAP


def get_module_stat_map(file_type):
    """根据文件类型返回模块统计映射。"""
    if file_type == "air":
        return {**MODULE_LAND_STAT_MAP, **MODULE_AIR_STAT_MAP}
    if file_type == "naval":
        return {**MODULE_LAND_STAT_MAP, **MODULE_NAVAL_STAT_MAP}
    return MODULE_LAND_STAT_MAP


# ============================================================
# 装备解析
# ============================================================

def parse_equipment_body(eid, body_text, file_type="land"):
    """解析单个装备条目 { ... } 内部"""
    stat_map = get_equipment_stat_map(file_type)

    result = {
        "fields": {},
        "types": [],
        "conversions": [],
        "upgrades": [],
        "slots": {},
        "count_limits": [],
        "default_modules": [],
        "archetype": None,
        "parent": None,
        "derived_variant_name": None,
        "add_equipment_type": [],
        "allow_mission_type": [],
        "others_parts": [],
    }

    # 初始化 module_inherit 默认状态
    result["fields"]["module_inherit"] = 0

    pos = 0
    length = len(body_text)

    while pos < length:
        if body_text[pos] == ' ':
            pos += 1
            continue

        match = re.match(r'([a-zA-Z0-9_\-]+)\s*=\s*', body_text[pos:])
        if not match:
            pos += 1
            continue

        key = match.group(1)
        pos += match.end()

        # ============================================================
        # 🔵 场景 A：等号右侧是标准的 大括号数据块 { ... }
        # ============================================================
        if pos < length and body_text[pos] == '{':
            block_str, next_pos = extract_braced_content(body_text, pos)
            pos = next_pos
            inner = block_str.strip().lstrip('{').rstrip('}').strip()

            if key == 'resources':
                for r_key, r_val in re.findall(r'([a-zA-Z0-9_\-]+)\s*=\s*([0-9\.]+)', inner):
                    result["fields"][f"resource_{r_key}"] = int(float(r_val))

            elif key == 'type':
                type_keys = re.findall(r'([a-zA-Z0-9_\-]+)\s*=', inner)
                if type_keys:
                    result["types"].extend(type_keys)
                else:
                    result["types"].extend(inner.split())

            elif key == 'can_convert_from':
                result["conversions"].extend(inner.split())

            elif key == 'upgrades':
                up_matches = re.findall(r'([a-zA-Z0-9_\-]+)', inner)
                result["upgrades"].extend([u for u in up_matches if u not in ('yes', 'no')])

            elif key == 'module_slots':
                # 1. 🔍 放宽正则：只匹配到等号，不要强行限定后面必须是大括号 '{'
                slot_pattern = re.compile(r'([a-zA-Z0-9_\-]+)\s*=\s*')
                s_pos = 0

                while s_pos < len(inner):
                    s_match = slot_pattern.search(inner[s_pos:])
                    if not s_match:
                        break

                    slot_id = s_match.group(1)
                    # 将指针推进到等号后面的位置
                    abs_start = s_pos + s_match.end()

                    # 2. 核心分流判定：检查等号右侧第一个有效字符是不是大括号
                    if abs_start < len(inner) and inner[abs_start] == '{':
                        # 🔵 通道一：正常大括号插槽块 { required = yes ... }
                        slot_block, nxt = extract_braced_content(inner, abs_start)
                        s_pos = nxt  # 推进滑窗指针

                        slot_body = slot_block.strip().lstrip('{').rstrip('}').strip()
                        req_match = re.search(r'required\s*=\s*(yes|no)', slot_body)
                        is_required = 1 if req_match and req_match.group(1) == 'yes' else 0

                        cat_start = re.search(r'allowed_module_categories\s*=\s*\{', slot_body)
                        if cat_start:
                            cb_start = cat_start.end() - 1
                            cat_block, _ = extract_braced_content(slot_body, cb_start)
                            cat_inner = cat_block.strip().lstrip('{').rstrip('}').strip()
                            categories = cat_inner.split()
                        else:
                            cat_match = re.search(r'allowed_module_categories\s*=\s*\{([^{}]+)\}', slot_body)
                            categories = cat_match.group(1).split() if cat_match else []

                        # 普通大括号槽位，inherit 记录为 0
                        result["slots"][slot_id] = {
                            "required": is_required,
                            "categories": categories,
                            "inherit": 0
                        }
                    else:
                        # 🟢 通道二：一维赋值槽位 (如 fixed_ship_battery_slot = inherit)
                        val_match = re.match(r'([^#\s{}]+)', inner[abs_start:])
                        if val_match:
                            val_str = val_match.group(1).strip()
                            s_pos = abs_start + val_match.end()  # 推进滑窗指针

                            # 🎯 精准捕获槽位级别的 inherit 属性
                            if val_str.lower() == 'inherit':
                                result["slots"][slot_id] = {
                                    "required": 0,
                                    "categories": [],
                                    "inherit": 1  # 标记当前具体槽位为继承模式
                                }
                        else:
                            s_pos = abs_start + 1

            elif key == 'module_count_limit':
                mid = ""
                category_id = ""
                mm = re.search(r'module\s*=\s*([a-zA-Z0-9_\-]+)', inner)
                cm = re.search(r'category\s*=\s*([a-zA-Z0-9_\-]+)', inner)
                count_m = re.search(r'count\s*([<>]=?|=)\s*([0-9]+)', inner)
                if mm:
                    mid = mm.group(1)
                if cm:
                    category_id = cm.group(1)
                count = f"{count_m.group(1)} {count_m.group(2)}" if count_m else ""
                result["count_limits"].append({"mid": mid, "category_id": category_id, "count": count})

            elif key == 'default_modules':
                dm_pairs = re.findall(r'([a-zA-Z0-9_\-]+)\s*=\s*([a-zA-Z0-9_\-]+)', inner)
                result["default_modules"].extend(dm_pairs)

            elif key == 'add_equipment_type':
                result["add_equipment_type"].extend(inner.split())

            elif key == 'allow_mission_type':
                result["allow_mission_type"].extend(inner.split())

            elif key == 'can_be_produced':
                result["others_parts"].append(f"can_be_produced = {block_str.strip()}")

            else:
                result["others_parts"].append(f"{key} = {block_str.strip()}")

        # ============================================================
        # 🟢 场景 B：等号右侧是普通一维单值赋值（如 inherit 或 archetype = xxx）
        # ============================================================
        else:
            val_match = re.match(r'([^#\s{}]+)', body_text[pos:])
            if not val_match:
                pos += 1
                continue
            val = val_match.group(1)
            pos += val_match.end()

            # 🎯 核心修正：捕获一维模式下的 module_slots = inherit，标记并推进
            if key == 'module_slots' and val.lower() == 'inherit':
                result["fields"]["module_inherit"] = 1
                continue

            val = parse_simple_value(val)

            if key == 'type':
                result["types"].append(val)
            elif key == 'upgrade':
                result["upgrades"].append(val)
            elif key == 'archetype':
                result["archetype"] = val
            elif key == 'parent':
                result["parent"] = val
            elif key == 'derived_variant_name':
                result["derived_variant_name"] = val
            elif key == 'allow_mission_type':
                result["allow_mission_type"].append(val)
            elif key in stat_map:
                result["fields"][stat_map[key]] = val
            else:
                result["fields"][key] = val

    if result["others_parts"]:
        result["fields"]["others"] = " ".join(result["others_parts"])
    return result


def parse_equipments_block(file_text, filename):
    """解析文件中的 equipments = { ... } 块，支持多个顶层块"""
    file_type = get_file_type(filename)

    all_parsed = []
    pattern = re.compile(r'equipments\s*=\s*\{')
    file_pos = 0

    while True:
        root_match = pattern.search(file_text, file_pos)
        if not root_match:
            break

        root_brace_pos = root_match.end() - 1
        try:
            root_block, end_pos = extract_braced_content(file_text, root_brace_pos)
            content = root_block.strip().lstrip('{').rstrip('}').strip()

            # 原有的解析逻辑
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
                all_parsed.append({
                    "eid": eid,
                    "filename": filename,
                    "data": parse_equipment_body(eid, body, file_type=file_type)
                })

            file_pos = end_pos  # 移动到当前块结束后继续搜索

        except Exception as e:
            print(f"解析 equipments 块时出错 (位置 {root_match.start()}): {e}")
            file_pos = root_match.end()
            continue

    return all_parsed


# ============================================================
# 模块解析
# ============================================================

def parse_module_body(body_text, file_type="land"):
    """解析单个模块条目 mid = { ... } 内部"""
    stat_map = get_module_stat_map(file_type)

    result = {
        "fields": {},
        "add_stats": {},
        "multiply_stats": {},
        "add_average_stats": {},
        "can_convert_from": [],
        "parent": None,
        "add_equipment_type": [],
        "allow_mission_type": [],
        "allow_equipment_type": [],
        "forbid_equipment_type": [],
        "forbid_equipment_type_exact_match": [],
        "forbid_equipment_type_exact_match_for_category": {},
        "critical_parts": [],
        "forbid_module_categories": [],
        "mission_type_stats": [],
        "limit_text": "",
        "others_parts": [],
    }

    NESTED_KEYS = {
        "add_stats", "multiply_stats", "add_average_stats",
        "build_cost_resources", "dismantle_cost_resources", "can_convert_from",
        "forbid_equipment_type_exact_match_for_category",
        "limit", "add_equipment_type", "allow_mission_type", "allow_equipment_type",
        "critical_parts", "forbid_module_categories", "mission_type_stats",
    }

    pos = 0
    length = len(body_text)

    while pos < length:
        if body_text[pos] == ' ':
            pos += 1
            continue

        match = re.match(r'([a-zA-Z0-9_\-]+)\s*=\s*', body_text[pos:])
        if not match:
            pos += 1
            continue

        key = match.group(1)
        pos += match.end()

        if pos < length and body_text[pos] == '{':
            block_str, next_pos = extract_braced_content(body_text, pos)
            pos = next_pos
            inner = block_str.strip().lstrip('{').rstrip('}').strip()

            if key == 'add_stats':
                for k, v in re.findall(r'([a-zA-Z0-9_\-]+)\s*=\s*([^\s{}]+)', inner):
                    mapped = stat_map.get(k, k)
                    result["add_stats"][mapped] = float(v)
                    # result["add_stats"][k] = float(v)

            elif key == 'multiply_stats':
                for k, v in re.findall(r'([a-zA-Z0-9_\-]+)\s*=\s*([^\s{}]+)', inner):
                    mapped = stat_map.get(k, k)
                    result["multiply_stats"][mapped] = float(v)
                    # result["add_stats"][k] = float(v)

            elif key == 'add_average_stats':
                for k, v in re.findall(r'([a-zA-Z0-9_\-]+)\s*=\s*([^\s{}]+)', inner):
                    mapped = stat_map.get(k, k)
                    result["add_average_stats"][mapped] = float(v)
                    # result["add_stats"][k] = float(v)

            elif key == 'build_cost_resources':
                for k, v in re.findall(r'([a-zA-Z0-9_\-]+)\s*=\s*([0-9]+)', inner):
                    result["fields"][f"build_cost_resources_{k}"] = int(v)

            elif key == 'dismantle_cost_resources':
                for k, v in re.findall(r'([a-zA-Z0-9_\-]+)\s*=\s*([0-9]+)', inner):
                    result["fields"][f"dismantle_cost_resources_{k}"] = int(v)

            elif key == 'can_convert_from':
                mm = re.search(r'module\s*=\s*([a-zA-Z0-9_\-]+)', inner)
                cm = re.search(r'module_category\s*=\s*([a-zA-Z0-9_\-]+)', inner)
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

            elif key == 'add_equipment_type':
                result["add_equipment_type"].extend(inner.split())

            elif key == 'allow_mission_type':
                result["allow_mission_type"].extend(inner.split())

            elif key == 'allow_mission_type':
                result["allow_mission_type"].extend(inner.split())

            elif key == 'critical_parts':
                result["critical_parts"].extend(inner.split())

            elif key == 'forbid_module_categories':
                result["forbid_module_categories"].extend(inner.split())

            elif key == 'mission_type_stats':
                mts = {"limits": [], "add_stats": {}, "multiply_stats": {}, "add_average_stats": {}}
                mts_pos = 0
                while mts_pos < len(inner):
                    if inner[mts_pos].isspace():
                        mts_pos += 1
                        continue

                    mts_match = re.match(r'(limit|add_stats|multiply_stats|add_average_stats)\s*=\s*\{',
                                         inner[mts_pos:])
                    if not mts_match:
                        mts_pos += 1
                        continue

                    mts_key = mts_match.group(1)
                    abs_mts = mts_pos + mts_match.end() - 1
                    mts_block, mts_next = extract_braced_content(inner, abs_mts)
                    mts_pos = mts_next  # 🚀 直接精准更新外层滑窗指针

                    mts_inner = mts_block.strip().lstrip('{').rstrip('}').strip()

                    if mts_key == 'limit':
                        # 移除可能残留的双引号，碎解为纯净元素列表
                        mts["limits"] = mts_inner.replace('"', '').split()
                    else:
                        # 动态捕捉 add_stats / multiply_stats / add_average_stats 树内部的扁平键值对
                        for sk, sv in re.findall(r'([a-zA-Z0-9_\-]+)\s*=\s*([^\s{}]+)', mts_inner):
                            mapped_key = stat_map.get(sk, sk)
                            # 保证 sv 去除尾部多余符号后转换为标准的数值
                            try:
                                # ✨ 核心写入：根据 mts_key 动态写入对应的 add_stats, multiply_stats, 或 add_average_stats
                                mts[mts_key][mapped_key] = float(sv)
                            except ValueError:
                                # 兼容可能存在的一维特定特殊字符串
                                mts[mts_key][mapped_key] = sv

                # 🔒 当单个 mission_type_stats 的 while 状态机完全跑完、所有子块收集完毕后，安全闭环灌入结果
                result["mission_type_stats"].append(mts)

            else:
                result["others_parts"].append(f"{key} = {block_str.strip()}")

        else:
            val_match = re.match(r'([^#\s{}]+)', body_text[pos:])
            if not val_match:
                pos += 1
                continue
            val = val_match.group(1)
            pos += val_match.end()
            val = parse_simple_value(val)

            if key == 'parent':
                result["parent"] = val
            elif key == 'add_equipment_type':
                result["add_equipment_type"].append(val)
            elif key == 'allow_mission_type':
                result["allow_mission_type"].append(val)
            elif key == 'allow_equipment_type':
                result["allow_equipment_type"].append(val)
            elif key == 'forbid_equipment_type_exact_match':
                result["forbid_equipment_type_exact_match"].append(val)
            elif key == 'forbid_equipment_type':
                result["forbid_equipment_type"].append(val)
            elif key == 'xp_cost':
                result["fields"]["xp_cost"] = float(val)
            elif key == 'dismantle_cost_ic':
                result["fields"]["dismantle_cost_ic"] = float(val)
            elif key in stat_map:
                # 模块主表也可能有 stats（如 build_cost_ic），但通常是顶层字段
                result["fields"][stat_map[key]] = val
            else:
                result["fields"][key] = val

    if result["others_parts"]:
        result["fields"]["others"] = " ".join(result["others_parts"])
    return result


def parse_modules_block(file_text, filename):
    """解析文件中的 equipment_modules = { ... } 块，并优先解析顶层 limit"""
    file_type = get_file_type(f"modules/{filename}")
    root_match = re.search(r'equipment_modules\s*=\s*\{', file_text)
    if not root_match:
        return []
    root_brace_pos = root_match.end() - 1
    root_block, _ = extract_braced_content(file_text, root_brace_pos)
    content = root_block.strip().lstrip('{').rstrip('}').strip()

    parsed = []
    limit_text = ""
    pos = 0
    while pos < len(content):
        if content[pos].isspace():
            pos += 1
            continue

        limit_match = re.match(r'limit\s*=\s*\{', content[pos:])
        if limit_match:
            abs_start = pos + limit_match.end() - 1
            limit_block, next_pos = extract_braced_content(content, abs_start)
            pos = abs_start + (next_pos - abs_start)
            limit_text = limit_block.strip().lstrip('{').rstrip('}').strip()
            continue

        item_match = re.match(r'([a-zA-Z0-9_\-]+)\s*=\s*\{', content[pos:])
        if not item_match:
            pos += 1
            continue
        mid = item_match.group(1)
        abs_start = pos + item_match.end() - 1
        item_block, next_pos = extract_braced_content(content, abs_start)
        pos = abs_start + (next_pos - abs_start)
        body = item_block.strip().lstrip('{').rstrip('}').strip()
        if mid == "ship_armor_bc_3":
            pass
        parsed.append({"mid": mid, "filename": filename, "data": parse_module_body(body, file_type=file_type), "_limit_text": limit_text})
    return parsed


def parse_modules_block2(file_text, filename):
    """解析文件中的 equipment_modules = { ... } 块，并优先解析顶层 limit，支持多个顶层块"""
    file_type = get_file_type(f"modules/{filename}")

    all_parsed = []
    pattern = re.compile(r'equipment_modules\s*=\s*\{')
    file_pos = 0

    while True:
        root_match = pattern.search(file_text, file_pos)
        if not root_match:
            break

        root_brace_pos = root_match.end() - 1
        try:
            root_block, end_pos = extract_braced_content(file_text, root_brace_pos)
            content = root_block.strip().lstrip('{').rstrip('}').strip()

            # 原有的解析逻辑
            limit_text = ""
            pos = 0
            while pos < len(content):
                if content[pos].isspace():
                    pos += 1
                    continue

                limit_match = re.match(r'limit\s*=\s*\{', content[pos:])
                if limit_match:
                    abs_start = pos + limit_match.end() - 1
                    limit_block, next_pos = extract_braced_content(content, abs_start)
                    pos = abs_start + (next_pos - abs_start)
                    limit_text = limit_block.strip().lstrip('{').rstrip('}').strip()
                    continue

                item_match = re.match(r'([a-zA-Z0-9_\-]+)\s*=\s*\{', content[pos:])
                if not item_match:
                    pos += 1
                    continue
                mid = item_match.group(1)
                abs_start = pos + item_match.end() - 1
                item_block, next_pos = extract_braced_content(content, abs_start)
                pos = abs_start + (next_pos - abs_start)
                body = item_block.strip().lstrip('{').rstrip('}').strip()
                all_parsed.append({
                    "mid": mid,
                    "filename": filename,
                    "data": parse_module_body(body, file_type=file_type),
                    "_limit_text": limit_text
                })

            file_pos = end_pos  # 移动到当前块结束后继续搜索

        except Exception as e:
            print(f"解析 equipment_modules 块时出错 (位置 {root_match.start()}): {e}")
            file_pos = root_match.end()
            continue

    return all_parsed

# ============================================================
# 数据库写入
# ============================================================

def setup_database(db_path):
    """创建数据库及所有表"""
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()
    for ddl in DDL_STATEMENTS:
        cursor.execute(ddl)
    conn.commit()
    # 插入默认 m_modules_limit 行
    cursor.execute("INSERT OR IGNORE INTO m_modules_limit (mlid, \"limit\") VALUES (0, '')")
    conn.commit()
    return conn, cursor


def write_module_limits(cursor, parsed_modules):
    """写入模块 limit 到 m_modules_limit 表，并为同一文件中的模块共享 mlid"""
    limit_cache = {}
    for item in parsed_modules:
        limit_text = item.get("_limit_text", "")
        if not limit_text:
            item["_mlid"] = 0
            continue

        if limit_text not in limit_cache:
            try:
                cursor.execute("INSERT INTO m_modules_limit (\"limit\") VALUES (?)", (limit_text,))
                limit_cache[limit_text] = cursor.lastrowid
            except sqlite3.Error as e:
                print(f" ⚠ [模块 {item['mid']}] m_modules_limit 写入失败: {e}")
                limit_cache[limit_text] = 0

        item["_mlid"] = limit_cache[limit_text]


def write_modules_main(cursor, parsed_modules):
    """写入模块主表 m_modules"""
    global MODULE_COLUMNS
    if MODULE_COLUMNS is None:
        MODULE_COLUMNS = set(get_table_columns(cursor, "m_modules"))
    count = 0
    for item in parsed_modules:
        mid = item["mid"]
        data = item["data"]
        filename = item["filename"]
        main_fields = {"mid": mid, "mlid": item.get("_mlid", 0), "generate_file": filename}
        for k, v in data["fields"].items():
            if k in MODULE_COLUMNS:
                main_fields[k] = v
        cols = ", ".join(main_fields.keys())
        phs = ", ".join(["?"] * len(main_fields))
        try:
            cursor.execute(f"INSERT OR REPLACE INTO m_modules ({cols}) VALUES ({phs})", list(main_fields.values()))
            count += 1
        except sqlite3.Error as e:
            print(f" ⚠ [模块 {mid}] 主表写入失败: {e}")
    return count


def write_modules_sub(cursor, parsed_modules):
    """写入模块子表：m_module_stats, m_parent, m_can_convert_from, forbid 等"""
    count = 0
    stats_columns = set(get_table_columns(cursor, "m_module_stats"))
    saved_filename = ""
    MODULE_STAT_MAP = []
    for item in parsed_modules:
        mid = item["mid"]
        data = item["data"]
        has_any = False

        if mid == "ship_armor_bc_3":
            pass
        filename = item["filename"]
        if saved_filename != filename:
            saved_filename = filename
            match FILE_TYPE_MAP[f"modules/{filename}"]:
                case "land": MODULE_STAT_MAP = MODULE_LAND_STAT_MAP
                case "naval": MODULE_STAT_MAP = MODULE_NAVAL_STAT_MAP
                case "air": MODULE_STAT_MAP = MODULE_AIR_STAT_MAP

        # --- add_stats → m_module_stats ---
        add_row = {"mid": mid, "type": "add"}
        for k, v in data["add_stats"].items():
            if k in MODULE_STAT_MAP:
                add_row[MODULE_STAT_MAP[k]] = v
            elif k in stats_columns:
                add_row[k] = v
        if len(add_row) > 2:
            try:
                sc = ", ".join(add_row.keys())
                sp = ", ".join(["?"] * len(add_row))
                cursor.execute(f"INSERT INTO m_module_stats ({sc}) VALUES ({sp})", list(add_row.values()))
                has_any = True
            except sqlite3.Error as e:
                print(f" ⚠ [模块 {mid}] m_module_stats(add) 写入失败: {e}")

        # --- multiply_stats → m_module_stats ---
        mult_row = {"mid": mid, "type": "multiply"}
        for k, v in data["multiply_stats"].items():
            if k in MODULE_STAT_MAP:
                mult_row[k] = v
            elif k in stats_columns:
                mult_row[k] = v
            else:
                print(f"不存在的属性{k}")
        if len(mult_row) > 2:
            try:
                sc = ", ".join(mult_row.keys())
                sp = ", ".join(["?"] * len(mult_row))
                cursor.execute(f"INSERT INTO m_module_stats ({sc}) VALUES ({sp})", list(mult_row.values()))
                has_any = True
            except sqlite3.Error as e:
                print(f" ⚠ [模块 {mid}] m_module_stats(multiply) 写入失败: {e}")

        # --- add_average_stats → m_module_stats ---
        avg_row = {"mid": mid, "type": "add_average"}
        for k, v in data["add_average_stats"].items():
            if k in MODULE_STAT_MAP:
                avg_row[k] = v
            elif k in stats_columns:
                avg_row[k] = v
            else:
                print(f"不存在的属性{k}")
        if len(avg_row) > 2:
            try:
                sc = ", ".join(avg_row.keys())
                sp = ", ".join(["?"] * len(avg_row))
                cursor.execute(f"INSERT INTO m_module_stats ({sc}) VALUES ({sp})", list(avg_row.values()))
                has_any = True
            except sqlite3.Error as e:
                print(f" ⚠ [模块 {mid}] m_module_stats(add_average) 写入失败: {e}")

        # --- parent → m_parent ---
        if data["parent"]:
            try:
                cursor.execute(
                    "INSERT INTO m_parent (mid, parent) VALUES (?, ?)",
                    (mid, data["parent"]))
                has_any = True
            except sqlite3.Error as e:
                print(f" ⚠ [模块 {mid}] m_parent 写入失败: {e}")

        # --- can_convert_from → m_can_convert_from ---
        for entry in data["can_convert_from"]:
            try:
                cursor.execute(
                    "INSERT INTO m_can_convert_from (give_mid, module, module_category, convert_cost_ic) VALUES (?, ?, ?, ?)",
                    (mid, entry["module"] or None, entry["module_category"] or None, entry["convert_cost_ic"]))
                has_any = True
            except sqlite3.Error as e:
                print(f" ⚠ [模块 {mid}] m_can_convert_from 写入失败: {e}")

        # --- add_equipment_type → m_add_equipment_type ---
        for t in data["add_equipment_type"]:
            try:
                cursor.execute(
                    "INSERT INTO m_add_equipment_type (mid, type) VALUES (?, ?)",
                    (mid, t))
                has_any = True
            except sqlite3.Error as e:
                print(f" ⚠ [模块 {mid}] m_add_equipment_type 写入失败: {e}")

        # --- allow_mission_type → m_allow_mission_type ---
        for t in data["allow_mission_type"]:
            try:
                cursor.execute(
                    "INSERT INTO m_allow_mission_type (mid, type) VALUES (?, ?)",
                    (mid, t))
                has_any = True
            except sqlite3.Error as e:
                print(f" ⚠ [模块 {mid}] m_allow_mission_type 写入失败: {e}")

        # --- allow_equipment_type → m_allow_equipment_type ---
        for t in data["allow_equipment_type"]:
            try:
                cursor.execute(
                    "INSERT INTO m_allow_equipment_type (mid, type) VALUES (?, ?)",
                    (mid, t))
                has_any = True
            except sqlite3.Error as e:
                print(f" ⚠ [模块 {mid}] m_allow_equipment_type 写入失败: {e}")

        # --- forbid_equipment_type → m_module_forbid_equipment_type ---
        for ft in data["forbid_equipment_type"]:
            try:
                cursor.execute(
                    "INSERT INTO m_module_forbid_equipment_type (mid, equipment_type) VALUES (?, ?)",
                    (mid, ft))
                has_any = True
            except sqlite3.Error as e:
                print(f" ⚠ [模块 {mid}] m_module_forbid_equipment_type 写入失败: {e}")

        # --- forbid_equipment_type_exact_match → m_module_forbid_equipment_type_exact_match ---
        for ft in data["forbid_equipment_type_exact_match"]:
            try:
                cursor.execute(
                    "INSERT INTO m_module_forbid_equipment_type_exact_match (mid, equipment_type_exact_match) VALUES (?, ?)",
                    (mid, ft))
                has_any = True
            except sqlite3.Error as e:
                print(f" ⚠ [模块 {mid}] m_module_forbid_equipment_type_exact_match 写入失败: {e}")

        # --- forbid_equipment_type_exact_match_for_category ---
        for cat, ft in data["forbid_equipment_type_exact_match_for_category"].items():
            try:
                cursor.execute(
                    "INSERT INTO m_module_forbid_equipment_type_exact_match_for_category (mid, category, equipment_type_exact_match) VALUES (?, ?, ?)",
                    (mid, cat, ft))
                has_any = True
            except sqlite3.Error as e:
                print(f" ⚠ [模块 {mid}] m_module_forbid_equipment_type_exact_match_for_category 写入失败: {e}")

        # --- critical_parts → m_critical_parts ---
        for cp in data["critical_parts"]:
            try:
                cursor.execute(
                    "INSERT INTO m_critical_parts (mid, critical_part) VALUES (?, ?)",
                    (mid, cp))
                has_any = True
            except sqlite3.Error as e:
                print(f" ⚠ [模块 {mid}] m_critical_parts 写入失败: {e}")

        # --- forbid_module_categories → m_forbid_module_categories ---
        for fc in data["forbid_module_categories"]:
            try:
                cursor.execute(
                    "INSERT INTO m_forbid_module_categories (mid, forbid_module_categorie) VALUES (?, ?)",
                    (mid, fc))
                has_any = True
            except sqlite3.Error as e:
                print(f" ⚠ [模块 {mid}] m_forbid_module_categories 写入失败: {e}")

        # --- mission_type_stats → m_mission_type_stats_limit + m_mission_type_stats ---
        for mts in data["mission_type_stats"]:
            # 先收集所有 stats_id（每个 stats 类型插入 m_module_stats）
            # print(mid + str(mts))
            stats_ids = []
            for stats_type in ["add_stats", "multiply_stats", "add_average_stats"]:
                # type_map = {"add_stats": "add", "multiply_stats": "multiply", "add_average_stats": "add_average"}
                stats_row = {"mid": mid, "type": stats_type}
                if mid == "bomb_locks" and stats_type == "add_average_stats":
                    pass
                for k, v in mts[stats_type].items():
                    if k in MODULE_STAT_MAP:
                        stats_row[k] = v
                    elif k in stats_columns:
                        stats_row[k] = v
                    else:
                        print(f"不存在的属性{k}")
                # print(f"mts: {mts}\nmts[{stats_type}].items(): {mts[stats_type].items()}\nstats_row: {stats_row}\n")
                if len(stats_row) > 2:
                    try:
                        sc = ", ".join(stats_row.keys())
                        sp = ", ".join(["?"] * len(stats_row))
                        cursor.execute(f"INSERT INTO m_module_stats ({sc}) VALUES ({sp})", list(stats_row.values()))
                        stats_ids.append(cursor.lastrowid)
                    except sqlite3.Error as e:
                        print(f" ⚠ [模块 {mid}] m_mission_type_stats(stats) 写入失败: {e}")

            # 每个 limit 单独入库，然后与每个 stats_id 做 N:N 关联
            for limit_val in mts["limits"]:
                try:
                    for stats_id in stats_ids:
                        cursor.execute(
                            "INSERT INTO m_mission_type_stats (mid, [limit], stats_id) VALUES (?, ?, ?)",
                            (mid, limit_val, stats_id))
                    has_any = True
                except sqlite3.Error as e:
                    print(f" ⚠ [模块 {mid}] m_mission_type_stats 写入失败: {e}")

        if has_any:
            count += 1
    return count


def write_equipments_main(cursor, parsed_equipments):
    """写入装备主表 equipments"""
    global EQUIP_COLUMNS
    if EQUIP_COLUMNS is None:
        EQUIP_COLUMNS = set(get_table_columns(cursor, "equipments"))

    count = 0
    for item in parsed_equipments:
        eid = item["eid"]
        filename = item["filename"]
        data = item["data"]
        main_fields = {"eid": eid, "generate_file": filename}

        if eid == "ship_hull_carrier_1":
            pass

        for k, v in data["fields"].items():
            if k in EQUIP_COLUMNS:
                if k == "module_inherit":
                    pass
                main_fields[k] = v

        cols = ", ".join(main_fields.keys())
        phs = ", ".join(["?"] * len(main_fields))
        try:
            cursor.execute(f"INSERT OR REPLACE INTO equipments ({cols}) VALUES ({phs})", list(main_fields.values()))
            count += 1
        except sqlite3.Error as e:
            print(f" ⚠ [装备 {eid}] 主表写入失败: {e}")
    return count


def write_equipments_sub(cursor, parsed_equipments):
    """写入装备子表：type, can_convert_from, upgrades, archetype, derived_variant_name,
       allow_mission_type, module_slots, allowed_module_categories, default_modules, module_count_limit"""
    count = 0
    for item in parsed_equipments:
        eid = item["eid"]
        data = item["data"]
        has_any = False

        # --- type ---
        for t in data["types"]:
            try:
                cursor.execute("INSERT INTO type (eid, type) VALUES (?, ?)", (eid, t))
                has_any = True
            except sqlite3.Error as e:
                print(f" ⚠ [装备 {eid}] type 写入失败: {e}")

        # --- can_convert_from ---
        for from_eid in data["conversions"]:
            try:
                cursor.execute("INSERT INTO can_convert_from (give_eid, from_eid) VALUES (?, ?)", (eid, from_eid))
                has_any = True
            except sqlite3.Error as e:
                print(f" ⚠ [装备 {eid}] can_convert_from 写入失败: {e}")

        # --- upgrades ---
        for up in data["upgrades"]:
            try:
                cursor.execute("INSERT INTO upgrades (eid, upgrade) VALUES (?, ?)", (eid, up))
                has_any = True
            except sqlite3.Error as e:
                print(f" ⚠ [装备 {eid}] upgrades 写入失败: {e}")

        # --- parent ---
        if data["parent"]:
            try:
                cursor.execute("INSERT INTO parent (eid, parent) VALUES (?, ?)", (eid, data["parent"]))
                has_any = True
            except sqlite3.Error as e:
                print(f" ⚠ [装备 {eid}] type 写入失败: {e}")
        # --- archetype ---
        if data["archetype"]:
            try:
                cursor.execute("INSERT INTO archetype (eid, archetype) VALUES (?, ?)", (eid, data["archetype"]))
                has_any = True
            except sqlite3.Error as e:
                print(f" ⚠ [装备 {eid}] archetype 写入失败: {e}")

        # --- derived_variant_name ---
        if data["derived_variant_name"]:
            try:
                cursor.execute("INSERT INTO derived_variant_name (eid, derived_variant_name) VALUES (?, ?)",
                               (eid, data["derived_variant_name"]))
                has_any = True
            except sqlite3.Error as e:
                print(f" ⚠ [装备 {eid}] derived_variant_name 写入失败: {e}")

        # --- allow_mission_type ---
        for t in data["allow_mission_type"]:
            try:
                cursor.execute("INSERT INTO allow_mission_type (eid, type) VALUES (?, ?)", (eid, t))
                has_any = True
            except sqlite3.Error as e:
                print(f" ⚠ [装备 {eid}] allow_mission_type 写入失败: {e}")

        # --- module_slots + allowed_module_categories ---
        if not data.get("module_inherit", False):
            for slot_id, slot_info in data["slots"].items():
                try:
                    cursor.execute(
                        "INSERT INTO module_slots (eid, slot_id, required, inherit) VALUES (?, ?, ?, ?)",
                        (eid, slot_id, slot_info["required"], slot_info["inherit"]))
                    msid = cursor.lastrowid
                    for cat in slot_info["categories"]:
                        try:
                            cursor.execute(
                                "INSERT INTO allowed_module_categories (msid, module_categorie) VALUES (?, ?)",
                                (msid, cat))
                        except sqlite3.Error as e:
                            print(f" ⚠ [装备 {eid}] allowed_module_categories (slot={slot_id}) 写入失败: {e}")
                    has_any = True
                except sqlite3.Error as e:
                    print(f" ⚠ [装备 {eid}] module_slots (slot={slot_id}) 写入失败: {e}")
        # --- default_modules ---
        for slot_id, value in data["default_modules"]:
            try:
                cursor.execute(
                    "INSERT INTO default_modules (eid, msid, value) VALUES (?, ?, ?)",
                    (eid, slot_id, value))
                has_any = True
            except sqlite3.Error as e:
                print(f" ⚠ [装备 {eid}] default_modules 写入失败: {e}")

        # --- module_count_limit ---
        for cl in data["count_limits"]:
            try:
                cursor.execute(
                    "INSERT INTO module_count_limit (eid, mid, category_id, count) VALUES (?, ?, ?, ?)",
                    (eid, cl["mid"] or None, cl["category_id"] or None, cl["count"] or None))
                has_any = True
            except sqlite3.Error as e:
                print(f" ⚠ [装备 {eid}] module_count_limit 写入失败: {e}")

        if has_any:
            count += 1
    return count


# ============================================================
# 文件扫描
# ============================================================

def scan_files(folder_path):
    """递归收集目录下所有 .txt/.asset 文件"""
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


# ============================================================
# 统计输出
# ============================================================

def print_stats(cursor):
    """打印每张表的行数"""
    tables = [
        "equipments", "type", "can_convert_from", "upgrades",
        "archetype", "derived_variant_name", "allow_mission_type",
        "module_slots", "allowed_module_categories", "default_modules",
        "module_count_limit",
        "m_modules", "m_module_stats", "m_parent",
        "m_add_equipment_type", "m_allow_mission_type", "m_allow_equipment_type"
        "m_module_forbid_equipment_type",
        "m_module_forbid_equipment_type_exact_match",
        "m_module_forbid_equipment_type_exact_match_for_category",
        "m_modules_limit", "m_can_convert_from",
        "m_critical_parts", "m_forbid_module_categories",
        "m_mission_type_stats", "m_mission_type_stats_limit",
    ]
    print("\n" + "=" * 60)
    print("  入库统计")
    print("=" * 60)
    for t in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {t}")
            n = cursor.fetchone()[0]
            print(f"  {t:55s} : {n}")
        except sqlite3.Error:
            print(f"  {t:55s} : (表不存在)")


# ============================================================
# 主流程
# ============================================================

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    equipment_dir = os.path.join(script_dir, "equipment")
    db_file = os.path.join(script_dir, "em.db")

    print(f"装备文件夹: {equipment_dir}")
    print(f"输出数据库: {db_file}")
    print()

    if not os.path.exists(equipment_dir):
        print("❌ equipment 文件夹不存在！")
        return

    # 1. 建库
    print(">>> 阶段 1: 创建数据库及表结构")
    conn, cursor = setup_database(db_file)

    # 2. 扫描所有文件
    all_files = scan_files(equipment_dir)
    print(f"\n>>> 阶段 2: 扫描到 {len(all_files)} 个文件，开始解析...")

    parsed_equipments = []
    parsed_modules = []

    for fpath in all_files:
        file_text = clean_and_merge_file(fpath)
        fname = os.path.basename(fpath)

        eqs = parse_equipments_block(file_text, fname)
        if eqs:
            for eq in eqs:
                parsed_equipments.append(eq)

        mods = parse_modules_block2(file_text, fname)
        if mods:
            parsed_modules.extend(mods)
            # for mod in mods:
            #     parsed_modules.extend(mod)

    print(f"  解析到装备 {len(parsed_equipments)} 条，模块 {len(parsed_modules)} 条")

    # 3. 依次写入
    print(f"\n>>> 阶段 3: 写入数据库")

    print("  [1/6] m_modules_limit ...")
    write_module_limits(cursor, parsed_modules)

    print("  [2/6] m_modules 主表 ...")
    n_mod_main = write_modules_main(cursor, parsed_modules)
    print(f"         → {n_mod_main} 条")

    print("  [3/6] 模块子表 (stats, parent, convert, forbid) ...")
    n_mod_sub = write_modules_sub(cursor, parsed_modules)
    print(f"         → {n_mod_sub} 个模块的子表数据")

    print("  [4/6] equipments 主表 ...")
    n_eq_main = write_equipments_main(cursor, parsed_equipments)
    print(f"         → {n_eq_main} 条")

    print("  [5/6] 装备子表 ...")
    n_eq_sub = write_equipments_sub(cursor, parsed_equipments)
    print(f"         → {n_eq_sub} 个装备的子表数据")

    print("  [6/6] 提交事务 ...")
    conn.commit()

    print_stats(cursor)
    conn.close()
    print(f"\n✅ 完成！")

    # 验证一些数据
    print(f"\n--- 样例验证 ---")
    conn2 = sqlite3.connect(db_file)
    c2 = conn2.cursor()
    for tbl in ["equipments", "m_modules"]:
        c2.execute(f"SELECT COUNT(*) FROM {tbl}")
        print(f"  {tbl}: {c2.fetchone()[0]} 行")
    c2.execute("SELECT eid FROM equipments LIMIT 5")
    print(f"  装备样例: {[r[0] for r in c2.fetchall()]}")
    c2.execute("SELECT mid FROM m_modules LIMIT 5")
    print(f"  模块样例: {[r[0] for r in c2.fetchall()]}")
    conn2.close()


if __name__ == "__main__":
    main()