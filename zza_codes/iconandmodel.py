import os
import sqlite3
import shutil
import re
from collections import defaultdict

def clean_and_merge_file(file_path):
    """彻底剥离注释并将全文件压缩合并为单行字符串"""
    cleaned_lines = []
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
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

def init_database(db_path):
    if os.path.exists(db_path):
        os.remove(db_path)
    """自动建立 Pool 架构的三张关联表"""
    conn = sqlite3.connect(db_path)
    # 开启外键约束支持
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()



    cursor.executescript("""
        CREATE TABLE pool (
            pool_id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag TEXT NOT NULL,
            equipment_id TEXT NOT NULL,
            limit_text TEXT
        );

        CREATE TABLE icons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pool_id INTEGER REFERENCES pool(pool_id) ON DELETE CASCADE NOT NULL,
            original_id TEXT NOT NULL,
            formatted_id TEXT NOT NULL
        );

        CREATE TABLE models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pool_id INTEGER REFERENCES pool(pool_id) ON DELETE CASCADE NOT NULL,
            original_id TEXT NOT NULL,
            formatted_id TEXT NOT NULL
        );
        
        CREATE TABLE pool_tank (
            pool_id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag TEXT NOT NULL,
            equipment_id TEXT NOT NULL,
            limit_text TEXT,
            icon_path TEXT NOT NULL
        );
        
        CREATE TABLE tank_models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pool_id INTEGER REFERENCES pool_tank(pool_id) ON DELETE CASCADE NOT NULL,
            original_id TEXT NOT NULL,
            formatted_id TEXT NOT NULL
        );
    """)
    conn.commit()
    return conn

def parse_and_import_pools(conn, file_path, db_path="pools.db"):
    if not os.path.exists(file_path):
        print(f"[错误] 文件不存在: {file_path}")
        return

    cursor = conn.cursor()

    print(f"正在清洗并合并文件: {file_path} ...")
    full_text = clean_and_merge_file(file_path)

    # ------------------------------------------------------------
    # 第一层：解析出顶级 Tag (如 default = { ... }, GER = { ... })
    # ------------------------------------------------------------
    pos = 0
    while pos < len(full_text):
        tag_match = re.search(r'([a-zA-Z0-9_\-]+)\s*=\s*\{', full_text[pos:])
        if not tag_match:
            break

        tag = tag_match.group(1)
        tag_start = pos + tag_match.end() - 1

        tag_block, next_pos = extract_braced_content(full_text, tag_start)
        pos = next_pos

        tag_content = tag_block.strip()[1:-1].strip()  # 剥去最外层大括号

        # ------------------------------------------------------------
        # 第二层：在 Tag 内部，解析 Equipment (如 small_plane_airframe = { ... })
        # ------------------------------------------------------------
        eq_pos = 0
        while eq_pos < len(tag_content):
            eq_match = re.search(r'([a-zA-Z0-9_\-]+)\s*=\s*\{', tag_content[eq_pos:])
            if not eq_match:
                break

            equipment_id = eq_match.group(1)
            eq_start = eq_pos + eq_match.end() - 1

            eq_block, next_eq_pos = extract_braced_content(tag_content, eq_start)
            eq_pos = next_eq_pos

            eq_content = eq_block.strip()[1:-1].strip()  # 剥去最外层大括号

            # ------------------------------------------------------------
            # 第三层：寻找 pool = { ... } 并提取 limit, icons, models
            # ------------------------------------------------------------
            pool_match = re.search(r'pool\s*=\s*\{', eq_content)
            if pool_match:
                pool_start = pool_match.end() - 1
                pool_block, _ = extract_braced_content(eq_content, pool_start)
                pool_content = pool_block.strip()[1:-1].strip()

                limit_text = None
                icons_list = []
                models_list = []

                p_pos = 0
                while p_pos < len(pool_content):
                    if pool_content[p_pos] == ' ':
                        p_pos += 1
                        continue

                    attr_match = re.match(r'(limit|icons|models)\s*=\s*', pool_content[p_pos:])
                    if attr_match:
                        attr_key = attr_match.group(1)
                        p_pos += attr_match.end()

                        if p_pos < len(pool_content) and pool_content[p_pos] == '{':
                            # 如果是大括号块
                            attr_block, next_p_pos = extract_braced_content(pool_content, p_pos)
                            p_pos = next_p_pos

                            if attr_key == 'limit':
                                # limit 保存完整的大括号结构文本
                                limit_text = attr_block.strip()
                            else:
                                # icons 或 models: 剥离大括号并拆分内部词条
                                inner_str = attr_block.strip()[1:-1].strip()
                                items = inner_str.split()
                                if attr_key == 'icons':
                                    icons_list.extend(items)
                                elif attr_key == 'models':
                                    models_list.extend(items)
                        else:
                            # 兜底：如果 limit 没有加大括号（而是 limit = yes 之类）
                            val_match = re.match(r'([^#\s{}]+)', pool_content[p_pos:])
                            if val_match:
                                if attr_key == 'limit':
                                    limit_text = val_match.group(1)
                                p_pos += val_match.end()
                    else:
                        p_pos += 1

                # ------------------------------------------------------------
                # 第四步：物理事务入库与 ID 自动化格式运算
                # ------------------------------------------------------------
                try:
                    # 1. 插入主表 pool
                    cursor.execute(
                        "INSERT INTO pool (tag, equipment_id, limit_text) VALUES (?, ?, ?)",
                        (tag, equipment_id, limit_text)
                    )
                    pool_id = cursor.lastrowid

                    # 2. 写入 icons 关联表，自动生成 formatted_id
                    for i, orig_icon in enumerate(icons_list, start=1):
                        fmt_icon = f"GFX{("_" + tag) if tag != "default" else ""}_{equipment_id}_medium_icon_{i}"
                        cursor.execute(
                            "INSERT INTO icons (pool_id, original_id, formatted_id) VALUES (?, ?, ?)",
                            (pool_id, orig_icon, fmt_icon)
                        )

                    # 3. 写入 models 关联表，自动生成 formatted_id
                    for i, orig_model in enumerate(models_list, start=1):
                        fmt_model = f"{(tag + "_") if tag != "default" else ""}{equipment_id}_medium_entity_{i}"
                        cursor.execute(
                            "INSERT INTO models (pool_id, original_id, formatted_id) VALUES (?, ?, ?)",
                            (pool_id, orig_model, fmt_model)
                        )
                except sqlite3.Error as e:
                    print(f" ❌ [插入失败] {tag} -> {equipment_id} 异常: {e}")

    conn.commit()
    print("🎉 Pool 数据及格式化 ID 自动转化全部入库完毕！")


def generate_formatted_pools(db_path="pools.db", output_dir="./output_pools"):
    if not os.path.exists(db_path):
        print(f"[错误] 数据库不存在: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"正在连接数据库 {db_path}，开始反向重构并分别导出 icons 和 models 资产池...")

    # 1. 提取所有唯一的顶级 Tag (如 default, GER 等)
    cursor.execute("SELECT DISTINCT tag FROM pool ORDER BY tag")
    tags = [r[0] for r in cursor.fetchall()]

    if not tags:
        print("[提示] 数据库中没有可用的 pool 数据。")
        conn.close()
        return

    # 分别初始化两个文件的数据流列表
    file_lines_icons = []
    file_lines_models = []

    # 2. 按照顶级 Tag 遍历组装
    for tag in tags:
        file_lines_icons.append(f"{tag} = {{")
        file_lines_models.append(f"{tag} = {{")

        # 获取该 tag 下所有的 equipment
        cursor.execute("SELECT pool_id, equipment_id, limit_text FROM pool WHERE tag = ?", (tag,))
        equipments = cursor.fetchall()

        for pool_id, eq_id, limit_text in equipments:




            # 🟢 [Icons 块还原]：严格使用数据库中新生成的格式化 ID (formatted_id)
            cursor.execute("SELECT formatted_id FROM icons WHERE pool_id = ? ORDER BY id", (pool_id,))
            icons = [r[0] for r in cursor.fetchall()]
            if icons:
                # 🔹 icons 文件流构建
                file_lines_icons.append(f"\t{eq_id} = {{")
                file_lines_icons.append("\t\tpool = {")
                if limit_text:
                    file_lines_icons.append(f"\t\t\tlimit = {limit_text}")
                file_lines_icons.append("\t\t\ticons = {")
                for icon in icons:
                    file_lines_icons.append(f"\t\t\t\t{icon}")
                file_lines_icons.append("\t\t\t}")
                # 闭合当前装备的 pool 块
                file_lines_icons.append("\t\t}")
                file_lines_icons.append("\t}")

            # 🟠 [Models 块还原]：按照要求暂时退回不格式化状态，读取 original_id
            cursor.execute("SELECT original_id FROM models WHERE pool_id = ? ORDER BY id", (pool_id,))
            models = [r[0] for r in cursor.fetchall()]
            if models:
                # 🔹 models 文件流构建
                file_lines_models.append(f"\t{eq_id} = {{")
                file_lines_models.append("\t\tpool = {")
                if limit_text:
                    file_lines_models.append(f"\t\t\tlimit = {limit_text}")
                file_lines_models.append("\t\t\tmodels = {")
                for model in models:
                    file_lines_models.append(f"\t\t\t\t{model}")
                file_lines_models.append("\t\t\t}")
                file_lines_models.append("\t\t}")
                file_lines_models.append("\t}")

        # 闭合当前国家 tag 块
        file_lines_icons.append("}\n")
        file_lines_models.append("}\n")

    conn.close()

    # 3. 严格遵循无 BOM 的标准 UTF-8 分别写入两个文件
    os.makedirs(output_dir, exist_ok=True)

    # 导出 Icons 资产文件
    output_path_icons = os.path.join(output_dir, "formatted_pools_icons.txt")
    with open(output_path_icons, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(file_lines_icons))
    print(f"📄 [生成成功] 格式化 Icons 文件已写入: {output_path_icons}")

    # 导出 Models 资产文件
    output_path_models = os.path.join(output_dir, "formatted_pools_models.txt")
    with open(output_path_models, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(file_lines_models))
    print(f"📄 [生成成功] 原始 Models 文件已写入: {output_path_models}")

def parse_source_gfx(gfx_path):
    """
    使用“先脱水清洗合并单行，再正则匹配”的绝对安全逻辑解析 GFX 文件
    返回字典: { "GFX_old_id": "gfx/interface/old_path.dds" }
    """
    gfx_map = {}

    if not os.path.exists(gfx_path):
        print(f"[错误] 指定的来源 GFX 文件不存在: {gfx_path}")
        return gfx_map

    print(f"正在清洗并解析旧 GFX 文件: {gfx_path} ...")

    # 1. 严格防线：先彻底清除所有 # 注释，并将全文件拉平为只有空格隔开的单行字符串
    full_text = clean_and_merge_file(gfx_path)

    # 2. 在绝对纯净的单行文本上执行匹配
    # 此时不论原文件怎么换行、怎么缩进，都已经变成了标准的 name = "A" texturefile = "B"
    pattern = re.compile(r'name\s*=\s*"([^"]+)"\s*texturefile\s*=\s*"([^"]+)"', re.IGNORECASE)

    matches = pattern.findall(full_text)
    for name, tex in matches:
        gfx_map[name] = tex

    print(f"✅ 在脱水后的旧 GFX 中成功提取到 {len(gfx_map)} 条贴图路径。")
    return gfx_map

def get_clean_filename(fmt_id, tag):
    file_name = fmt_id
    # 1. 强力剥离统一的 UI 前缀 'GFX_' (4个字符)
    if file_name.startswith("GFX_"):
        file_name = file_name[4:]
    # 2. 强力剥离特定的国家前缀，比如 'SWE_' (tag长度 + 1个下划线)
    # 排除通用池 'default'，因为通用池的名字里本来就没有 'default_'
    if tag.lower() != "default" and file_name.startswith(f"{tag}_"):
        file_name = file_name[len(tag) + 1:]
    return file_name

def migrate_physical_textures(db_path, gfx_map, mod_root_dir):
    """
    连接数据库，将旧贴图物理文件复制/移动到新的格式化路径
    """
    id_missing_list: list = []
    file_missing_dict:dict = {}
    if not os.path.exists(db_path):
        print(f"[错误] 数据库不存在: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 联合查询获取原始 ID、新 ID 和 Tag
    query = """
        SELECT p.tag, i.original_id, i.formatted_id 
        FROM icons i 
        JOIN pool p ON i.pool_id = p.pool_id
    """
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"[错误] 数据库查询失败: {e}")
        return

    success_count = 0
    missing_in_gfx = 0

    print("\n🚀 开始执行物理文件大迁移...")

    for tag, orig_id, fmt_id in rows:
        dir_tag = "general" if tag.lower() == "default" else tag

        # 1. 检查这个原始 ID 是否在你提供的旧 GFX 文件里
        if orig_id not in gfx_map:
            missing_in_gfx += 1
            id_missing_list.append(orig_id)
            continue

        # 2. 组装旧文件的绝对物理路径
        orig_tex_rel = gfx_map[orig_id]
        # os.path.normpath 用来将游戏内路径 (gfx/...) 转换为当前系统支持的路径斜杠
        orig_phys_path = os.path.join(mod_root_dir, os.path.normpath(orig_tex_rel))

        if not os.path.exists(orig_phys_path):
            file_missing_dict[orig_id] = orig_tex_rel
            continue

        # 3. 组装新文件的格式化目标路径
        target_tex_rel = f"gfx/interface/FLTE/equipment_designer_icon/{dir_tag}/{get_clean_filename(fmt_id, tag)}.dds"
        target_phys_path = os.path.join(mod_root_dir, os.path.normpath(target_tex_rel))

        # 自动创建目标文件夹（如果尚不存在）
        os.makedirs(os.path.dirname(target_phys_path), exist_ok=True)

        # 4. 执行文件操作
        try:
            # 💡 强烈建议使用 copy2 保留原文件。如果确定要剪切移动，请改为 shutil.move(orig_phys_path, target_phys_path)
            shutil.copy2(orig_phys_path, target_phys_path)
            success_count += 1
        except Exception as e:
            print(f"❌ 复制 {orig_id} 时出错: {e}")

    print("\n" + "=" * 50)
    print("🏁 资产迁移报告:")
    print(f"✅ 成功迁移贴图: {success_count} 张")
    print("=" * 50)


    return id_missing_list, file_missing_dict

def generate_smart_gfx(db_path, id_missing_list, file_missing_dict, icon_output_path, model_output_path):
    """
    接收迁移阶段传来的异常清单，分别导出 icon 和 model 两个独立的 GFX 文件。
    - icon：使用 formatted_id + 智能纹理路径（保持原有三态判定逻辑）
    - model：暂时使用 original_id（非格式化数据）
    两者都严格按照 pool 结构（tag -> equipment_id）组织，并保留 limit 等其它字段。
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # ============================================================
    # 第一部分：导出 icon GFX
    # ============================================================
    icon_query = """
        SELECT p.tag, p.equipment_id, i.original_id, i.formatted_id 
        FROM icons i 
        JOIN pool p ON i.pool_id = p.pool_id 
        ORDER BY p.tag, p.equipment_id, i.id
    """
    cursor.execute(icon_query)
    icon_rows = cursor.fetchall()

    icon_lines = ["spriteTypes = {"]
    current_eq_id = None
    stats_normal = 0

    print("\n🚀 [2/2 - 1/2] 渲染 icon GFX 文件...")

    for tag, equipment_id, orig_id, fmt_id in icon_rows:
        if current_eq_id != equipment_id:
            icon_lines.append(f"# {equipment_id}")
            current_eq_id = equipment_id

        dir_tag = "general" if tag.lower() == "default" else tag
        comment = ""

        # ----------------------------------------------------
        # 核心判定 1：ID 缺失名单 (指向原版科技包路径)
        # ----------------------------------------------------
        if orig_id in id_missing_list:
            core_name = orig_id
            if core_name.startswith("GFX_"):
                core_name = core_name[4:]
            if core_name.endswith("_medium"):
                core_name = core_name[:-7]

            texture_path = f"gfx/interface/technologies/{core_name}.dds"
            comment = " # use hoi4 miss"

        # ----------------------------------------------------
        # 核心判定 2：物理缺失名单 (保留原版给定的源路径)
        # ----------------------------------------------------
        elif orig_id in file_missing_dict:
            # 直接从字典中提取源 GFX 声明的老相对路径
            texture_path = file_missing_dict[orig_id]
            comment = " # use hoi4 keep"

        # ----------------------------------------------------
        # 正常生成名单：走格式化路径
        # ----------------------------------------------------
        else:
            texture_path = f"gfx/interface/FLTE/equipment_designer_icon/{dir_tag}/{get_clean_filename(fmt_id, tag)}.dds"
            stats_normal += 1

        sprite_line = f'\tspriteType = {{ name = "{fmt_id}" texturefile = "{texture_path}" }}{comment}'
        icon_lines.append(sprite_line)

    icon_lines.append("}\n")

    icon_dir = os.path.dirname(icon_output_path)
    if icon_dir:
        os.makedirs(icon_dir, exist_ok=True)

    with open(icon_output_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(icon_lines))

    print(f"✅ icon GFX 已写出: {icon_output_path} (共 {len(icon_rows)} 条)")

    # ============================================================
    # 第二部分：导出 model GFX（暂时使用 original_id，即非格式化数据）
    # ============================================================
    model_query = """
        SELECT p.tag, p.equipment_id, m.original_id, m.formatted_id 
        FROM models m 
        JOIN pool p ON m.pool_id = p.pool_id 
        ORDER BY p.tag, p.equipment_id, m.id
    """
    cursor.execute(model_query)
    model_rows = cursor.fetchall()

    model_lines = ["spriteTypes = {"]
    current_eq_id = None

    print("\n🚀 [2/2 - 2/2] 渲染 model GFX 文件（暂时使用 original_id）...")

    for tag, equipment_id, orig_id, fmt_id in model_rows:
        if current_eq_id != equipment_id:
            model_lines.append(f"# {equipment_id}")
            current_eq_id = equipment_id

        # 暂时使用 original_id（非格式化数据），后续可改为 fmt_id
        name_to_use = orig_id
        sprite_line = f'\tspriteType = {{ name = "{name_to_use}" }}'
        model_lines.append(sprite_line)

    model_lines.append("}\n")

    model_dir = os.path.dirname(model_output_path)
    if model_dir:
        os.makedirs(model_dir, exist_ok=True)

    with open(model_output_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(model_lines))

    print(f"✅ model GFX 已写出: {model_output_path} (共 {len(model_rows)} 条)")

    # ============================================================
    # 统计输出
    # ============================================================
    print("\n" + "=" * 50)
    print(f"🎉 双路 GFX 导出完毕")
    print(f"📊 icon 渲染分类统计:")
    print(f"   🟢 纯本地重构资产: {stats_normal} 个")
    print(f"   🟡 映射原版科技路径 (id_missing): {len(id_missing_list)} 个")
    print(f"   🟠 保留原版源路径 (file_missing): {len(file_missing_dict)} 个")
    print(f"📊 model 临时导出: {len(model_rows)} 条（使用 original_id 非格式化数据）")
    print("=" * 50)


# ============================================================
# 第一阶段：自动初始化数据库与数据清洗搬运
# ============================================================

def parse_and_import_tanks(conn, file_path, db_path, mod_root_dir):
    """
    解析坦克配置文件。
    icon：直接对齐物理硬盘，命中则搬运，未命中则跳过。
    model：保持原逻辑，解析 original_id 并录入 1:N 关联表。
    """
    if not os.path.exists(file_path):
        print(f"[错误] 输入文件不存在: {file_path}")
        return

    cursor = conn.cursor()

    print(f"🔄 正在清洗并合并坦克文件: {file_path} ...")
    full_text = clean_and_merge_file(file_path)

    pos = 0
    import_count = 0

    while pos < len(full_text):
        tag_match = re.search(r'([a-zA-Z0-9_\-]+)\s*=\s*\{', full_text[pos:])
        if not tag_match:
            break

        tag = tag_match.group(1)
        tag_start = pos + tag_match.end() - 1

        tag_block, next_pos = extract_braced_content(full_text, tag_start)
        pos = next_pos
        tag_content = tag_block.strip()[1:-1].strip()

        eq_pos = 0
        while eq_pos < len(tag_content):
            eq_match = re.search(r'([a-zA-Z0-9_\-]+)\s*=\s*\{', tag_content[eq_pos:])
            if not eq_match:
                break

            equipment_id = eq_match.group(1)
            eq_start = eq_pos + eq_match.end() - 1

            eq_block, next_eq_pos = extract_braced_content(tag_content, eq_start)
            eq_pos = next_eq_pos
            eq_content = eq_block.strip()[1:-1].strip()

            pool_match = re.search(r'pool\s*=\s*\{', eq_content)
            if pool_match:
                pool_start = pool_match.end() - 1
                pool_block, _ = extract_braced_content(eq_content, pool_start)
                pool_content = pool_block.strip()[1:-1].strip()

                limit_text = None
                raw_icon_paths = set()
                raw_models_list = []

                p_pos = 0
                while p_pos < len(pool_content):
                    if pool_content[p_pos] == ' ':
                        p_pos += 1
                        continue

                    attr_match = re.match(r'(limit|icons|models)\s*=\s*', pool_content[p_pos:])
                    if attr_match:
                        attr_key = attr_match.group(1)
                        p_pos += attr_match.end()

                        if p_pos < len(pool_content) and pool_content[p_pos] == '{':
                            attr_block, next_p_pos = extract_braced_content(pool_content, p_pos)
                            p_pos = next_p_pos

                            inner_str = attr_block.strip()[1:-1].strip()
                            if attr_key == 'limit':
                                limit_text = attr_block.strip()
                            elif attr_key == 'icons':
                                # icon 收集路径字符串（剥离双引号）
                                cleaned_icon_str = inner_str.replace('"', '')
                                raw_icon_paths.update(cleaned_icon_str.split())
                            elif attr_key == 'models':
                                # model 与原来相同，收集列表
                                raw_models_list.extend(inner_str.split())
                        else:
                            val_match = re.match(r'([^#\s{}]+)', pool_content[p_pos:])
                            if val_match:
                                if attr_key == 'limit':
                                    limit_text = val_match.group(1)
                                p_pos += val_match.end()
                    else:
                        p_pos += 1

                # ----------------------------------------------------
                # ✨ 核心修正：使用 enumerate 顺着 pool 内部顺序为物理文件重命名
                # ----------------------------------------------------
                for i, orig_icon_path in enumerate(raw_icon_paths, start=1):
                    # 1. 拼出其原版在硬盘上的绝对物理路径
                    orig_phys_path = os.path.join(mod_root_dir, os.path.normpath(orig_icon_path))

                    # ❌ 防线 1：如果老物理文件在硬盘上根本不存在，直接跳过
                    if not os.path.exists(orig_phys_path):
                        target_tex_rel = orig_icon_path
                        print(orig_icon_path)
                    else:
                        # 🟢 防线 2：文件存在，严格根据装备 ID 格式化出全新的物理文件名
                        # 举例：ger_basic_light_tank_chassis -> ger_basic_light_tank_chassis_icon_1.dds
                        formatted_filename = f"{equipment_id}_icon_{i}.dds"

                        dir_tag = "general" if tag.lower() == "default" else tag
                        target_tex_rel = f"gfx/interface/FLTE/equipment_designer_icon/{dir_tag}/{formatted_filename}"
                        target_phys_path = os.path.join(mod_root_dir, os.path.normpath(target_tex_rel))

                        # 2. 执行磁盘物理搬运与重命名
                        os.makedirs(os.path.dirname(target_phys_path), exist_ok=True)

                        shutil.copy2(orig_phys_path, target_phys_path)

                    # 3. 一步到位：将搬运成功、且完美格式化后的物理路径存入主表
                    cursor.execute(
                        "INSERT INTO pool_tank (tag, equipment_id, limit_text, icon_path) VALUES (?, ?, ?, ?)",
                        (tag, equipment_id, limit_text, target_tex_rel)
                    )
                    pool_id = cursor.lastrowid

                    # 4. 保持旧代码逻辑：models 逻辑和原来完全相同，生成格式化 ID 录入副表
                    for j, orig_model in enumerate(raw_models_list, start=1):
                        fmt_model = f"{(tag + "_") if tag != "default" else ""}{equipment_id}_medium_entity_{i}"

                        cursor.execute(
                            "INSERT INTO tank_models (pool_id, original_id, formatted_id) VALUES (?, ?, ?)",
                            (pool_id, orig_model.replace('"', ''), fmt_model)
                        )
                    import_count += 1

    conn.commit()
    print(f"📊 阶段一完毕：成功导入 {import_count} 组坦克有效资产。")

# ============================================================
# 第二阶段：严格根据数据库内容 1:1 输出格式化坦克代码文件
# ============================================================

def generate_formatted_tanks(db_path, output_dir="./output_tanks"):
    """
    反向重构文本：将坦克资产池分别导出为独立的 icons 和 models 文件。
    """
    if not os.path.exists(db_path):
        print(f"[错误] 数据库不存在: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT tag FROM pool_tank ORDER BY tag")
    tags = [r[0] for r in cursor.fetchall()]

    if not tags:
        print("[提示] 数据库中没有可用的坦克 pool 数据。")
        conn.close()
        return

    # 1. ✨ 解耦：分别初始化 icons 和 models 的文件流列表
    file_lines_icons = []
    file_lines_models = []

    print(f"🔄 正在结合一步到位 icon 路径与原版 model 逻辑，分别渲染输出文件...")

    # 2. 按照顶级 Tag 遍历组装
    for tag in tags:
        file_lines_icons.append(f"{tag} = {{")
        file_lines_models.append(f"{tag} = {{")

        cursor.execute("SELECT DISTINCT equipment_id FROM pool_tank WHERE tag = ?", (tag,))
        equipments = [r[0] for r in cursor.fetchall()]

        for eq_id in equipments:
            cursor.execute("SELECT pool_id, limit_text FROM pool_tank WHERE tag = ? AND equipment_id = ? LIMIT 1",
                           (tag, eq_id))
            pool_id, limit_text = cursor.fetchone()

            # 🟢 [Icons 分支]：获取该装备底盘下基于装备 ID 命名成功的有效物理路径
            cursor.execute("SELECT icon_path FROM pool_tank WHERE tag = ? AND equipment_id = ?", (tag, eq_id))
            valid_icons = [r[0] for r in cursor.fetchall()]
            if valid_icons:
                # 🔹 2a. 构建 icons 文件流的装备头
                file_lines_icons.append(f"\t{eq_id} = {{")
                file_lines_icons.append("\t\tpool = {")
                if limit_text:
                    file_lines_icons.append(f"\t\t\tlimit = {limit_text}")
                file_lines_icons.append("\t\t\ticons = {")
                for icon_p in valid_icons:
                    file_lines_icons.append(f'\t\t\t\t"{icon_p}"')
                file_lines_icons.append("\t\t\t}")
                # 分别闭合当前装备的 pool 块
                file_lines_icons.append("\t\t}")
                file_lines_icons.append("\t}")

            # 🟠 [Models 分支]：保持旧代码逻辑，输出格式化后的关联 ID（不带双引号）
            cursor.execute("SELECT original_id FROM tank_models WHERE pool_id = ? ORDER BY id", (pool_id,))
            valid_models = [r[0] for r in cursor.fetchall()]
            if valid_models:
                # 🔹 2b. 构建 models 文件流的装备头
                file_lines_models.append(f"\t{eq_id} = {{")
                file_lines_models.append("\t\tpool = {")
                if limit_text:
                    file_lines_models.append(f"\t\t\tlimit = {limit_text}")
                file_lines_models.append("\t\t\tmodels = {")
                for model_id in valid_models:
                    file_lines_models.append(f"\t\t\t\t{model_id}")
                file_lines_models.append("\t\t\t}")
                file_lines_models.append("\t\t}")
                file_lines_models.append("\t}")





        # 分别闭合当前国家 tag 块
        file_lines_icons.append("}\n")
        file_lines_models.append("}\n")

    conn.close()

    # 3. ✨ 物理输出：严格遵循无 BOM 的标准 UTF-8 分别写入两个独立文件
    os.makedirs(output_dir, exist_ok=True)

    # 导出纯路径版坦克 Icons 资产文件
    output_path_icons = os.path.join(output_dir, "tank_pools_icons.txt")
    with open(output_path_icons, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(file_lines_icons))
    print(f"📄 [生成成功] 格式化坦克 Icons 文件已写入: {output_path_icons}")

    # 导出关联键名版坦克 Models 资产文件
    output_path_models = os.path.join(output_dir, "tank_pools_models.txt")
    with open(output_path_models, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(file_lines_models))
    print(f"📄 [生成成功] 格式化坦克 Models 文件已写入: {output_path_models}")

#  asset

def get_all_db_mappings(db_path):
    """
    联合读取 pools.db 中的空军飞机和陆军坦克模型映射关系
    返回两个映射字典: { "old_original_entity_id": "new_formatted_id" }
    """
    air_map = {}
    tank_map = {}

    if not os.path.exists(db_path):
        print(f"[错误] 找不到指定的数据库文件: {db_path}")
        return air_map, tank_map

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. 读取空军飞机模型映射 (来自 models 表)
    try:
        cursor.execute("SELECT original_id, formatted_id FROM models")
        for orig, fmt in cursor.fetchall():
            air_map[orig.strip()] = fmt.strip()
    except sqlite3.OperationalError:
        print("[提示] 数据库中未发现常规空军 models 表。")

    # 2. 读取陆军坦克模型映射 (来自 tank_models 表)
    try:
        cursor.execute("SELECT original_id, formatted_id FROM tank_models")
        for orig, fmt in cursor.fetchall():
            tank_map[orig.strip()] = fmt.strip()
    except sqlite3.OperationalError:
        print("[提示] 数据库中未发现陆军 tank_models 表。")

    return air_map, tank_map


def process_asset_folder(asset_dir, air_map, tank_map):
    """
    遍历整个 asset 文件夹，解构并利用映射缓存将所有 entity 重建分类
    """
    # 缓存准备生成的两个目标文件的内容流列表
    air_output_lines = []
    tank_output_lines = []

    if not os.path.exists(asset_dir):
        print(f"[错误] 资产文件夹不存在: {asset_dir}")
        return air_output_lines, tank_output_lines

    print("🔄 开始深度解构并清洗所有 .asset 文件流...")

    for filename in os.listdir(asset_dir):
        if not filename.endswith('.asset') or os.path.isdir(os.path.join(asset_dir, filename)):
            continue

        # 核心判定：检查当前文件名前缀是否包含 'UTTNH_'
        is_uttnh_file = filename.upper().startswith("UTNH_")
        if is_uttnh_file:
            pass

        file_path = os.path.join(asset_dir, filename)
        full_text = clean_and_merge_file(file_path)

        # 使用顶级词条扫描器，精准定位并截取每一个顶级 entity = { ... }
        pos = 0
        while pos < len(full_text):
            entity_match = re.search(r'entity\s*=\s*\{', full_text[pos:])
            if not entity_match:
                break

            absolute_start = pos + entity_match.end() - 1
            # 状态机精准吞下整块
            block_str, next_pos = extract_braced_content(full_text, absolute_start)
            pos = next_pos

            # 提取出花括号内部核心属性
            inner_body = block_str.strip().lstrip('{').rstrip('}').strip()

            # 核心提取：唯独精准解析 name 字段，其余内容通过位置截取和正则原封不动保留
            name_match = re.search(r'name\s*=\s*"([^"]+)"', inner_body, re.IGNORECASE)
            if not name_match:
                continue

            old_name = name_match.group(1).strip()

            # ----------------------------------------------------
            # 核心路由分流逻辑：检索该旧名称属于空军还是陆军映射
            # ----------------------------------------------------
            target_file_type = None
            new_name = None

            if old_name in air_map:
                target_file_type = 'air'
                new_name = air_map[old_name]
            elif old_name in tank_map:
                target_file_type = 'tank'
                new_name = tank_map[old_name]
            else:
                # 兜底：如果模型在数据库的资产池里从未出现过，则不予格式化和移档
                continue

            # ----------------------------------------------------
            # 核心文本重组：剥离旧的 name 行，换上全新的 name 规则
            # ----------------------------------------------------
            # 彻底去掉原来的 name = "xxx" 段落，合并其余所有原汁原味的属性字段
            rest_body = re.sub(r'name\s*=\s*"[^"]+"', '', inner_body, flags=re.IGNORECASE).strip()
            # 压缩多余连续空格，统一对齐
            rest_body = re.sub(r'\s+', ' ', rest_body)

            # ----------------------------------------------------
            # ✨ 核心修正：根据 clone 规则，实现原版文件属性的一键截断
            # ----------------------------------------------------
            new_inner_lines = [f'\tname = "{new_name}"']

            if not is_uttnh_file:
                # 🟢 场景 A：原版文件 (前缀不为 UTTNH_) -> 只写 name 和 clone，后面内容直接不要了
                new_inner_lines.append(f'\tclone = "{old_name}"')

            else:
                # 🔵 场景 B：模组自身文件 (前缀为 UTTNH_) -> 保持原逻辑，无损还原所有技术属性
                # 彻底去掉原来的 name = "xxx" 段落，合并其余所有原汁原味的属性字段
                rest_body = re.sub(r'name\s*=\s*"[^"]+"', '', inner_body, flags=re.IGNORECASE).strip()
                rest_body = re.sub(r'\s+', ' ', rest_body)

                # 动态抓取非 name 的所有其它对齐键值对
                attr_pairs = re.findall(r'([a-zA-Z0-9_\-]+)\s*=\s*("[^"]+"|[a-zA-Z0-9_\-\.]+)', rest_body)
                for attr_k, attr_v in attr_pairs:
                    if attr_k.lower() != 'name':
                        new_inner_lines.append(f'\t{attr_k} = {attr_v}')

            # 拼装回完美缩进的标准 P 社 entity 块结构
            reconstructed_block = "entity = {\n" + "\n".join(new_inner_lines) + "\n}\n"

            # 归流分发至对应的飞机或坦克数据流中
            if target_file_type == 'air':
                air_output_lines.append(reconstructed_block)
            elif target_file_type == 'tank':
                tank_output_lines.append(reconstructed_block)

    return air_output_lines, tank_output_lines


def output_refactored_assets(db_path, asset_dir, output_dir="./output_assets"):
    """执行总控闭环"""
    # 1. 批量调取数据库两路映射缓存
    air_map, tank_map = get_all_db_mappings(db_path)
    print(f"📊 数据库映射载入成功: 空军飞机实体 {len(air_map)} 个, 陆军坦克实体 {len(tank_map)} 个。")

    if not air_map and not tank_map:
        print("[提示] 没有任何有效的映射数据，程序终止。")
        return

    # 2. 多文件流状态机动态切割重组
    air_blocks, tank_blocks = process_asset_folder(asset_dir, air_map, tank_map)

    os.makedirs(output_dir, exist_ok=True)

    # 3. 渲染写出不带 BOM 的标准 UTF-8 空军模型文件
    if air_blocks:
        air_file_path = os.path.join(output_dir, "FLTE_air_generated.asset")
        with open(air_file_path, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(air_blocks))
        print(f"📄 [生成成功] 空军飞机模型集中声明文件: {air_file_path} (共 {len(air_blocks)} 个条目)")

    # 4. 渲染写出不带 BOM 的标准 UTF-8 陆军坦克模型文件
    if tank_blocks:
        tank_file_path = os.path.join(output_dir, "FLTE_tank_generated.asset")
        with open(tank_file_path, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(tank_blocks))
        print(f"📄 [生成成功] 陆军坦克模型集中声明文件: {tank_file_path} (共 {len(tank_blocks)} 个条目)")


if __name__ == "__main__":
    mod_dir = r"E:\Documents\Paradox Interactive\Hearts of Iron IV\mod\UTTNH Foxr Edition"
    db_path = r"gfx/db_file.db"
    conn = init_database(db_path)
    # AIR
    parse_and_import_pools(conn, r"gfx/00_plane_icons.txt", db_path)
    generate_formatted_pools(db_path, r"gfx/01_plane_icons/")
    parse_source: dict = parse_source_gfx(r"gfx\IE_AIR.gfx") | parse_source_gfx(r"gfx\IE_AIR_BBA.gfx")
    id_missing_list, file_missing_dict = migrate_physical_textures(db_path, parse_source, mod_dir)
    # generate_smart_gfx(db_path, id_missing_list, file_missing_dict,
    #                     r"gfx/03_plane_icons.gfx",
    #                     r"gfx/03_plane_models.gfx")
    # TANK
    parse_and_import_tanks(conn,f"gfx/00_tank_icons.txt", db_path, mod_dir)
    generate_formatted_tanks(db_path, f"gfx/03_tank_icons/")

    output_refactored_assets(db_path, r"gfx/asset", "./output_assets")

    conn.close()