import os
import hashlib
import json

"""
计算文件哈希，会导出json表
可根据json表直接替换和删除重复文件
"""


def calculate_sha256(file_path, block_size=65536):
    """高效计算大文件/二进制文件的 SHA-256 哈希值"""
    sha256 = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            for block in iter(lambda: f.read(block_size), b''):
                sha256.update(block)
        return sha256.hexdigest()
    except Exception as e:
        print(f"[错误] 无法读取文件 {file_path}: {e}")
        return None


def scan_and_deduplicate_dds(target_dir, output_json_path="./dds_replacement_map.json"):
    if not os.path.exists(target_dir):
        print(f"[错误] 目标目录不存在: {target_dir}")
        return

    print(f"🔍 开始扫描目录 {target_dir} 下的所有 .dds 文件...")

    # 哈希映射表：{ "sha256_hash": "第一个发现该哈希的纯净物理路径" }
    hash_to_kept_file = {}

    # 最终的替换映射字典：{ "需要被删除/替换的重复文件路径": "应当保留的唯一文件路径" }
    replacement_map = {}

    total_files = 0
    duplicate_count = 0

    # 深度遍历目录
    for root, _, files in os.walk(target_dir):
        for file in files:
            if file.lower().endswith('.dds'):
                total_files += 1
                full_path = os.path.normpath(os.path.join(root, file))

                # 计算当前 dds 的唯一特征哈希
                file_hash = calculate_sha256(full_path)
                if not file_hash:
                    continue

                if file_hash in hash_to_kept_file:
                    # 🚨 发现重复！记录该死胡同路径，将其映射到第一个遇到的唯一路径上
                    kept_file_path = hash_to_kept_file[file_hash]
                    replacement_map[full_path] = kept_file_path
                    duplicate_count += 1
                else:
                    # 🟢 首次发现该特征，作为基准“保留文件”锁定
                    hash_to_kept_file[file_hash] = full_path

    print("\n" + "=" * 50)
    print("🏁 图像哈希去重扫描报告:")
    print(f"   📦 总计扫描到 .dds 文件: {total_files} 个")
    print(f"   ✨ 保持唯一的独立文件: {len(hash_to_kept_file)} 个")
    print(f"   🚨 检测到的重复冗余文件: {duplicate_count} 个")
    print("=" * 50)

    # 将路径替换表写入 JSON 文件，方便后续的自动化脚本或文本批量替换工具读取
    out_dir = os.path.dirname(output_json_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(output_json_path, "w", encoding="utf-8") as json_f:
        # indent=4 保证输出的 JSON 具有良好的可读性
        json.dump(replacement_map, json_f, ensure_ascii=False, indent=4)

    print(f"💾 路径替换映射表已成功导出至: {output_json_path}")
    return replacement_map


def apply_deduplication_and_clean(json_map_path, target_dir):
    if not os.path.exists(json_map_path):
        print(f"[错误] 找不到路径替换表 JSON 文件: {json_map_path}")
        return
    if not os.path.exists(target_dir):
        print(f"[错误] 目标扫描目录不存在: {target_dir}")
        return

    # 1. 载入去重映射表
    with open(json_map_path, "r", encoding="utf-8") as f:
        replacement_map = json.load(f)

    if not replacement_map:
        print("[提示] 替换映射表为空，无需执行任何操作。")
        return

    print(f"📊 成功载入映射表，共有 {len(replacement_map)} 个冗余资产等待清理...")

    # ============================================================
    # 阶段一：全量执行文本文件内的路径替换
    # ============================================================
    print("\n🚀 [1/2] 开始扫描并批量替换文本文件中的路径引用...")

    # 规范化映射表中的路径斜杠，防止因为系统的不同（\ 或 /）导致文本无法精确匹配
    normalized_map = {
        os.path.normpath(k).replace("\\", "/"): os.path.normpath(v).replace("\\", "/")
        for k, v in replacement_map.items()
    }

    text_extensions = ('.txt', '.gfx', '.asset')
    updated_files_count = 0

    for root, _, files in os.walk(target_dir):
        for file in files:
            if file.lower().endswith(text_extensions):
                file_path = os.path.join(root, file)

                # 读取文本内容
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as tf:
                        content = tf.read()
                except Exception as e:
                    print(f"⚠️ 无法读取文本文件 {file_path}: {e}")
                    continue

                # 逐条比对和替换路径
                is_modified = False
                for old_path, new_path in normalized_map.items():
                    # 在 P 社脚本中，路径可能带有双引号或不带，直接用纯路径字符串进行全球全局 replace
                    if old_path in content:
                        content = content.replace(old_path, new_path)
                        is_modified = True

                    # 兜底支持：有些脚本可能用了反斜杠，一并做替换兼容
                    old_path_alt = old_path.replace("/", "\\")
                    if old_path_alt in content:
                        content = content.replace(old_path_alt, new_path.replace("/", "\\"))
                        is_modified = True

                # 如果内容发生变更，严格写回硬盘（无 BOM 的 standard UTF-8）
                if is_modified:
                    try:
                        with open(file_path, "w", encoding="utf-8", newline="\n") as tf:
                            tf.write(content)
                        updated_files_count += 1
                    except Exception as e:
                        print(f"❌ 写入修改后的文件失败 {file_path}: {e}")

    print(f"✅ 文本替换阶段完毕！共检测并修正了 {updated_files_count} 个脚本文件的内部引用。")

    # ============================================================
    # 阶段二：全部替换完毕后，执行物理垃圾图像的彻底删除
    # ============================================================
    print("\n🗑️ [2/2] 文本引用重构安全闭环，开始执行多余物理图像文件擦除...")

    deleted_images_count = 0
    missing_images_count = 0

    # 遍历 JSON 里的每一条需要被替换/删除的 Key 路径
    for old_file_rel in replacement_map.keys():
        # 补全其在当前 Mod 根目录下的物理路径
        phys_delete_path = os.path.normpath(os.path.join(target_dir, old_file_rel))

        # if os.path.exists(phys_delete_path):
        #     try:
        #         os.remove(phys_delete_path)
        #         deleted_images_count += 1
        #     except Exception as e:
        #         print(f"❌ 物理删除失败: {phys_delete_path}，原因: {e}")
        # else:
        #     # 可能是之前已经手工清理过或路径不准确
        #     missing_images_count += 1

    print("\n" + "=" * 50)
    print("🏁 资产清洗与精简流水线报告:")
    print(f"   📝 修正文本/脚本资产: {updated_files_count} 个")
    print(f"   💥 物理粉碎冗余 .dds 贴图: {deleted_images_count} 张")
    if missing_images_count > 0:
        print(f"   ❓ 预备清单中在磁盘上已被提前移除的文件: {missing_images_count} 个")
    print("=" * 50)

if __name__ == "__main__":
    # scan_and_deduplicate_dds(r"E:\Documents\Paradox Interactive\Hearts of Iron IV\mod\UTTNH Foxr Edition\gfx\interface\FLTE",
    #                          "./gfx/hash.json")
    apply_deduplication_and_clean("./gfx/hash.json",
                                  r"E:\Documents\Paradox Interactive\Hearts of Iron IV\mod\UTTNH Foxr Edition\interface\FLTE_GFX")