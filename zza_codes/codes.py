import os
import re
import pprint

def clean_and_merge_file(file_path):
    """
    第一步：彻底清洗文件内容
    1. 逐行剥离所有 # 及其后面的注释
    2. 将整张表压缩合并为一行，用单个空格安全连接，彻底干掉所有换行干扰
    """
    cleaned_lines = []
    with open(file_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
        for line in f:
            if '#' in line:
                line = line.split('#')[0]
            cleaned_lines.append(line.strip())
            
    # 用空格合并为单行文本，并把连续的多个空格压缩为一个空格
    full_text = " ".join(cleaned_lines)
    full_text = re.sub(r'\s+', ' ', full_text)
    return full_text


def parse_single_equipment_block(block_text):
    """
    第三步：对切分出来的单个装备内部微型块进行【全自动盲抓】
    """
    data = {}
    
    # 1. 自动识别所有类似 "key = {" 的子嵌套条目，盲初始化为空字典 {} 占位
    nested_keys = re.findall(r'([a-zA-Z0-9_\-]+)\s*=\s*\{', block_text)
    for nkey in nested_keys:
        data[nkey] = {} 

    # 2. 自动识别普通的一维基础键值对 (如 year = 1936 等)
    kv_pairs = re.findall(r'([a-zA-Z0-9_\-]+)\s*=\s*([a-zA-Z0-9_\-\.]+)', block_text)
    for key, value in kv_pairs:
        if key not in data:
            data[key] = value
            
    return data


def extract_equipment_folder(folder_path):
    """
    主控流程：遍历指定文件夹（不深入子文件夹），执行“清洗->合并->切割->通用盲匹配”
    """
    if not os.path.exists(folder_path):
        print(f"[错误] 路径不存在: {folder_path}")
        return {}

    all_equipments = {}
    print(f"开始扫描文件夹: {folder_path} (严格执行单行合并后匹配机制)...")
    
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        
        if os.path.isdir(file_path) or not filename.endswith(('.txt', '.asset')):
            continue
            
        print(f" 📄 正在清洗并合并文件: {filename}")
        
        file_text = clean_and_merge_file(file_path)
        
        # 定位顶层的 equipments = { ... } 内部核心内容
        root_match = re.search(r'equipments\s*=\s*\{(.*)\}', file_text)
        if not root_match:
            continue
            
        equipments_content = root_match.group(1).strip()
        
        # 精准斩断提取出每一个 item_id = { ... } 块
        item_pattern = re.compile(r'([a-zA-Z0-9_\-]+)\s*=\s*\{\s*([^{}]*(?:\{[^{}]*\}[^{}]*)*)\s*\}')
        
        items = item_pattern.findall(equipments_content)
        for item_id, block_text in items:
            item_data = parse_single_equipment_block(block_text.strip())
            
            # 记录生成文件追踪印记 (generate_file)
            item_data['generate_file'] = filename
            
            # 载入总库
            all_equipments[item_id] = item_data

    return all_equipments


def analyze_structure_union(equipments_dict):
    """
    核心新增：分析全量装备字典，生成普通属性字段与嵌套条目的【结构并集】
    """
    union_normal_keys = set()
    union_nested_keys = set()
    
    for item_id, item_data in equipments_dict.items():
        for key, val in item_data.items():
            # 排除我们框架自带的附加追踪列
            if key == 'generate_file':
                continue
                
            if isinstance(val, dict):
                # 如果值是字典，说明是嵌套块
                union_nested_keys.add(key)
            else:
                # 否则是普通扁平一维键值对
                union_normal_keys.add(key)
                
    return sorted(list(union_normal_keys)), sorted(list(union_nested_keys))


# ==================== 控制台运行入口 ====================
if __name__ == "__main__":
    test_folder = "./codes/equipment" 
    if not os.path.exists(test_folder):
        test_folder = input("请输入要测试提取的 equipment 文件夹路径: ").strip()

    # 1. 抓取数据
    result_dict = extract_equipment_folder(test_folder)
    
    if not result_dict:
        print("[提示] 未探测到有效装备条目。")
        exit()

    # 2. ✨ 计算键值结构并集
    normal_union, nested_union = analyze_structure_union(result_dict)
    
    # 3. 打印输出报告
    print("\n" + "="*60)
    print(f"📋 逆向资产盲抓探测完成！总计成功捕获 {len(result_dict)} 个装备条目")
    print("="*60)
    
    print("\n[🎯 扁平属性键并集 (Union of Normal Fields)]")
    print("--- 以下字段在所有条目中至少出现过一次，可作为设计【主表列】的依据 ---")
    pprint.pprint(normal_union, compact=True, width=80)
    
    print("\n[🎯 子嵌套条目键并集 (Union of Nested Objects)]")
    print("--- 以下条目为大括号嵌套块，必须作为设计【子表/关联副表】的依据 ---")
    pprint.pprint(nested_union, compact=True, width=80)
    
    print("\n" + "="*60)
    print("💡 提示：你可以基于上方打印的两个并集列表，开始规划你的 SQLite DDL 建表脚本了。")
    print("="*60)