import os
import shutil
from pathlib import Path


def find_and_copy_asset_files(input_dir, output_dir):
    """
    查找所有.asset文件并复制到输出目录

    参数:
        input_dir: 输入文件夹路径（会递归搜索所有子文件夹）
        output_dir: 输出文件夹路径

    规则:
        1. 只处理路径中包含 'entities' 的.asset文件
        2. 重命名为: {顶级子文件夹名称}_{原文件名}.asset
        3. 跳过不包含 'entities' 的路径
    """

    # 转换为Path对象便于操作
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    # 检查输入目录是否存在
    if not input_path.exists():
        print(f"[错误] 输入文件夹不存在: {input_dir}")
        return

    # 创建输出目录（如果不存在）
    output_path.mkdir(parents=True, exist_ok=True)

    # 统计信息
    stats = {
        'total_found': 0,
        'copied': 0,
        'skipped_no_entities': 0,
        'errors': 0
    }

    # 递归查找所有.asset文件
    asset_files = list(input_path.rglob('*.asset'))
    stats['total_found'] = len(asset_files)

    print(f"[信息] 找到 {stats['total_found']} 个 .asset 文件")
    print(f"[信息] 输出目录: {output_path.absolute()}")
    print("-" * 60)

    for asset_file in asset_files:
        try:
            # 获取相对于输入目录的路径
            rel_path = asset_file.relative_to(input_path)

            # 检查路径中是否包含 'entities'
            # 注意：使用 'entities' 作为路径的一部分来判断（不区分大小写）
            if 'entities' not in str(rel_path).lower():
                stats['skipped_no_entities'] += 1
                print(f"[跳过] {rel_path} (路径中不包含 'entities')")
                continue

            # 获取顶级子文件夹名称（输入目录下的第一级子目录）
            # 例如: input_dir/subfolder1/subfolder2/file.asset -> subfolder1
            parts = rel_path.parts
            if len(parts) > 0:
                top_folder = parts[0]  # 顶级子文件夹
            else:
                top_folder = "root"

            # 构建新文件名: {顶级子文件夹名称}_{原文件名}.asset
            new_filename = f"{top_folder}_{asset_file.name}"
            new_filepath = output_path / new_filename

            # 如果目标文件已存在，添加序号避免覆盖
            counter = 1
            original_new_filepath = new_filepath
            while new_filepath.exists():
                # 在文件名后添加序号
                name_without_ext = original_new_filepath.stem
                new_filename = f"{name_without_ext}_{counter}{original_new_filepath.suffix}"
                new_filepath = output_path / new_filename
                counter += 1

            # 复制文件
            shutil.copy2(asset_file, new_filepath)
            stats['copied'] += 1

            print(f"[复制] {rel_path} -> {new_filepath.name}")

        except Exception as e:
            stats['errors'] += 1
            print(f"[错误] 处理 {asset_file} 时出错: {e}")

    # 打印统计信息
    print("-" * 60)
    print("[完成] 处理完成!")
    print(f"  - 总共找到: {stats['total_found']} 个 .asset 文件")
    print(f"  - 已复制: {stats['copied']} 个")
    print(f"  - 跳过 (不包含entities): {stats['skipped_no_entities']} 个")
    print(f"  - 错误: {stats['errors']} 个")
    print(f"  - 输出目录: {output_path.absolute()}")


def main():
    """主函数 - 交互式输入"""
    print("=" * 60)
    print("📁 .asset 文件筛选与复制工具")
    print("=" * 60)

    input_dir = r"E:\SteamLibrary\steamapps\common\Hearts of Iron IV\dlc"
    output_dir = r"./asset/out"

    # 执行复制
    find_and_copy_asset_files(input_dir, output_dir)


# 如果直接运行脚本，执行main函数
if __name__ == "__main__":
    main()