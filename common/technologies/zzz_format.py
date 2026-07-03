import sys

class TechItem:
    """科技条目数据模型：用于将解析出的单行文本重新格式化"""
    def __init__(self, tech_id, raw_content):
        self.tech_id = tech_id
        self.raw_content = raw_content
        # 1. 将单行文本解析为语法树
        self.parsed_items = self._parse_tokens(self._tokenize(raw_content))[0]

    def _tokenize(self, text):
        """词法拆分：按空白切分，但保留引号内的完整字符串。"""
        tokens = []
        i = 0
        n = len(text)

        while i < n:
            ch = text[i]
            if ch.isspace():
                i += 1
            elif ch in '{}=><':
                tokens.append(ch)
                i += 1
            elif ch in {'"', "'"}:
                quote = ch
                j = i + 1
                while j < n:
                    if text[j] == '\\' and j + 1 < n:
                        j += 2
                    elif text[j] == quote:
                        break
                    else:
                        j += 1
                tokens.append(text[i:j + 1])
                i = j + 1
            else:
                j = i
                while j < n and not text[j].isspace() and text[j] not in '{}=><':
                    j += 1
                tokens.append(text[i:j])
                i = j

        return tokens

    def _parse_tokens(self, tokens):
        """递归解析：将平铺的词元组装成层级树 (键值对 或 单一条目)"""
        res = []
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token == '}':
                break
            
            # 判断是否为 key = value 或 key > value 的结构
            if i + 1 < len(tokens) and tokens[i+1] in ['=', '>', '<']:
                key = token
                op = tokens[i+1]
                i += 2
                if i < len(tokens) and tokens[i] == '{':
                    # 如果右侧是花括号，递归解析内部块
                    i += 1
                    block_content, consumed = self._parse_tokens(tokens[i:])
                    res.append(('kv', key, op, block_content))
                    i += consumed + 1 # 跳过闭合的 '}'
                else:
                    # 如果右侧是普通字符串/数字
                    res.append(('kv', key, op, tokens[i]))
                    i += 1
            else:
                # 只是一个独立条目 (比如 categories 内部的 artillery)
                res.append(('item', token))
                i += 1
        return res, i

    def _has_stat(self, val):
        """启发式判断：检查块内是否包含战斗数值，用于识别未知的单位/装备修正"""
        if not isinstance(val, list): 
            return False
        stat_keys = {
            'soft_attack', 'hard_attack', 'ap_attack', 'air_attack', 
            'reliability', 'supply_consumption', 'movement', 'mountain',
            "air_defence"
        }
        for child in val:
            if child[0] == 'item': continue
            if child[1] in stat_keys: return True
            if self._has_stat(child[3]): return True
        return False

    def __str__(self):
        """格式化输出：严格按照规则排序和分组"""
        group_0_unknown = []
        group_1_effects = []
        group_2_main = []
        group_3_trailing = []
        group_4_trailing_main = []

        # 2. 对解析出的条目进行归类
        for item in self.parsed_items:
            if item[0] == 'item':
                group_0_unknown.append(item)
                continue
            
            _, key, op, val = item
            
            # 明确属于效果类的键
            if key in ['enable_equipments', 'enable_equipment_modules', 'enable_subunits', 'enable_building',
                       'tech_air_damage_factor', 'static_anti_air_damage_factor', 'static_anti_air_hit_chance_factor']:
                group_1_effects.append(item)
            # 明确属于主要条目的键
            elif key in ['start_year', 'research_cost', 'path', 'folder']:
                group_2_main.append(item)
            # 明确属于尾随条目的键
            elif key in ['force_use_small_tech_layout', 'is_special_project_tech', 'dependencies', 'allow', 'allow_branch', 'on_research_complete', 'special_project_specialization']:
                group_3_trailing.append(item)
            # 明确属于尾随主要条目的键
            elif key in ['categories', 'ai_will_do']:
                group_4_trailing_main.append(item)
            else:
                # 判断未注册的条目是修正块还是真正的未知条目
                if isinstance(val, list) and (self._has_stat(val) or key.startswith('category_') or key.endswith('_brigade')):
                    group_1_effects.append(item)
                else:
                    group_0_unknown.append(item)

        # 定义每组内部的排序规则，按你给定的键顺序输出
        effect_order = {
            'enable_equipments': 0,
            'enable_equipment_modules': 1,
            'enable_subunits': 2,
            'enable_building': 3,
            'tech_air_damage_factor': 4,
            'static_anti_air_damage_factor': 5,
            'static_anti_air_hit_chance_factor': 6,
        }
        main_order = {'start_year': 0, 'research_cost': 1, 'path': 2, 'folder': 3}
        trailing_order = {
            'force_use_small_tech_layout': 0,
            'is_special_project_tech': 1,
            'dependencies': 2,
            'allow': 3,
            'allow_branch': 4,
            'on_research_complete': 5,
            'special_project_specialization': 6,
        }
        trailing_main_order = {'categories': 0, 'ai_will_do': 1}

        group_1_effects.sort(key=lambda x: (effect_order.get(x[1], 99), x[1]))
        group_2_main.sort(key=lambda x: (main_order.get(x[1], 99), x[1]))
        group_3_trailing.sort(key=lambda x: (trailing_order.get(x[1], 99), x[1]))
        group_4_trailing_main.sort(key=lambda x: (trailing_main_order.get(x[1], 99), x[1]))

        # 3. 递归格式化函数
        def format_item(item, indent_level=2):
            tabs = '    ' * indent_level # 使用 4 个空格对齐
            if item[0] == 'item':
                return tabs + item[1]
            
            _, key, op, val = item
            if isinstance(val, str):
                return f"{tabs}{key} {op} {val}"
            
            # --- 以下是单行特例处理 ---
            if key == 'path':
                coeff, leads = "1", ""
                for v_item in val:
                    if v_item[0] != 'item' and v_item[1] == 'research_cost_coeff': coeff = v_item[3]
                    if v_item[0] != 'item' and v_item[1] == 'leads_to_tech': leads = v_item[3]
                if not leads:
                    return ""
                return f"{tabs}path = {{ research_cost_coeff = {coeff} leads_to_tech = {leads} }}"
            
            if key == 'folder':
                name, x, y = "", "0", "0"
                for v_item in val:
                    if v_item[0] != 'item' and v_item[1] == 'name': name = v_item[3]
                    if v_item[0] != 'item' and v_item[1] == 'position':
                        for p_item in v_item[3]:
                            if p_item[0] != 'item' and p_item[1] == 'x': x = p_item[3]
                            if p_item[0] != 'item' and p_item[1] == 'y': y = p_item[3]
                return f"{tabs}folder = {{ name = {name} position = {{ x = {x} y = {y} }} }}"
            
            if key == 'special_project_specialization':
                items_str = " ".join([v[1] for v in val if v[0] == 'item'])
                return f"{tabs}special_project_specialization = {{ {items_str} }}"
            
            # --- 默认多行嵌套处理 ---
            lines = [f"{tabs}{key} {op} {{"]
            for child in val:
                lines.append(format_item(child, indent_level + 1))
            lines.append(f"{tabs}}}")
            return "\n".join(lines)

        # 4. 最终文本拼装，处理空行与 Unknown
        out_lines = [f"    {self.tech_id} = {{"]
        
        # 放置 #Unknown 条目
        if group_0_unknown:
            out_lines.append("        # Unknowns")
            for item in group_0_unknown:
                out_lines.append(format_item(item, 2))
        if group_0_unknown and (group_1_effects or group_2_main or group_3_trailing or group_4_trailing_main):
            out_lines.append("")

        # 放置 Effect 条目
        for item in group_1_effects:
            out_lines.append(format_item(item, 2))
        if group_1_effects and (group_2_main or group_3_trailing or group_4_trailing_main):
            out_lines.append("")

        # 放置 Main 条目
        for item in group_2_main:
            out_lines.append(format_item(item, 2))
        if group_2_main and (group_3_trailing or group_4_trailing_main):
            out_lines.append("")

        # 放置 Trailing 条目
        for item in group_3_trailing:
            out_lines.append(format_item(item, 2))
        if group_3_trailing and group_4_trailing_main:
            out_lines.append("")

        # 放置 Trailing Main 条目
        for item in group_4_trailing_main:
            out_lines.append(format_item(item, 2))

        out_lines.append("    }")
        return "\n".join(out_lines)

class PdxParser:
    @staticmethod
    def format_and_parse(file_path) -> list:
        # ==========================================
        # 1. 读取并清除 # 注释
        # ==========================================
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        cleaned_lines = []
        for line in lines:
            if '#' in line:
                line = line[:line.find('#')]  # 截断 # 及后面的内容
            cleaned_line = line.strip()
            if cleaned_line:  # 忽略空行
                cleaned_lines.append(cleaned_line)

        # ==========================================
        # 2. 合并为一行，加空格分隔
        # ==========================================
        single_line_data = " ".join(cleaned_lines)

        # ==========================================
        # 3. 定位 technologies = { 并提取内部全部内容
        # ==========================================
        tech_start_idx = single_line_data.find('technologies = {')
        if tech_start_idx == -1:
            print("未找到 technologies 块！")
            return []

        content_start = single_line_data.find('{', tech_start_idx) + 1
        
        # 括号匹配算法：找到 technologies 最外层 } 的位置
        brace_count = 1
        pos = content_start
        while pos < len(single_line_data) and brace_count > 0:
            if single_line_data[pos] == '{':
                brace_count += 1
            elif single_line_data[pos] == '}':
                brace_count -= 1
            pos += 1
            
        # 此时 technologies 内部的全部文本（剔除了最外层的 technologies = {}）
        tech_block_content = single_line_data[content_start : pos - 1]

        # ==========================================
        # 4. 依次读取所有的 tech_id = { ... }
        # ==========================================
        tech_items = []
        i = 0
        
        while i < len(tech_block_content):
            # 找到下一个 '='
            eq_idx = tech_block_content.find('=', i)
            if eq_idx == -1:
                break
                
            # 提取 '=' 左边的词作为 tech_id
            left_part = tech_block_content[:eq_idx].strip()
            tech_id = left_part.split()[-1]  # 以空格分割，取最靠近 '=' 的词
            
            # 检查 '=' 右边的内容
            right_start = eq_idx + 1
            # 跳过空格
            while right_start < len(tech_block_content) and tech_block_content[right_start].isspace():
                right_start += 1
                
            if right_start < len(tech_block_content) and tech_block_content[right_start] == '{':
                # 如果右边是 '{'，说明这是一个块（科技块或其它带花括号的条目）
                b_count = 1
                b_pos = right_start + 1
                while b_pos < len(tech_block_content) and b_count > 0:
                    if tech_block_content[b_pos] == '{':
                        b_count += 1
                    elif tech_block_content[b_pos] == '}':
                        b_count -= 1
                    b_pos += 1
                
                # 提取这对括号中间的全部内容
                tech_body = tech_block_content[right_start + 1 : b_pos - 1].strip()
                
                # 过滤掉形如 @main_branch = { ... } (如果有的话)
                if not tech_id.startswith('@'):
                    tech_items.append(TechItem(tech_id, tech_body))
                    
                i = b_pos # 将指针移到块结束之后，继续寻找下一个
            else:
                # 这是一个单行键值对（比如 @main_branch = 0）
                # 我们不需要处理它内部的花括号，直接将指针移到等号后面继续
                i = right_start
                
        return tech_items

format_path = sys.argv[1]
if not format_path:
    print("未提供执行文件")
    exit()
parsed_techs: list = PdxParser.format_and_parse(format_path)
output_path = sys.argv[2] if len(sys.argv) > 2 else format_path

outstr = "technologies = {\n"
for item in parsed_techs:
    outstr += str(item) + "\n"
outstr += "}"
with open(output_path, 'w', encoding='utf-8') as f:
        f.write(outstr)
        print(f"格式化完成，已保存至: {output_path}")