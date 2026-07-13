import os
import shutil
from pathlib import Path
import pathspec

MOD_TEXT = '''\
version="0.2.0"
tags={
\t"Gameplay"
\t"Graphics"
\t"Historical"
\t"Military"
\t"Technologies"
}
name="UTTNH: Foxr Edition"
supported_version="1.19.*"
'''


def sync_with_ignore_mechanism(descriptor_mod_text, ignore_file=".myignore", dest_dir="../destination"):
    # 1. 初始化路径
    # Path(__file__).parent 指向脚本所在的当前文件夹
    src_path = Path(__file__).parent.resolve()
    dest_path = Path(dest_dir).resolve()
    ignore_conf = src_path / ignore_file
    # 2. 清空目标文件夹
    if dest_path.exists():
        print(f"正在清空目标目录: {dest_path}...")
        # 删除整个目录再重建，确保彻底清空
        shutil.rmtree(dest_path)

    dest_path.mkdir(parents=True, exist_ok=True)
    # 3. 加载忽略规则
    spec = None
    if not ignore_conf.exists():
        print(f"警告: 未找到规则文件 {ignore_file}，将复制所有文件。")
        spec = pathspec.PathSpec.from_lines('gitwildmatch', [])
    else:
        with open(ignore_conf, 'r', encoding='utf-8') as f:
            spec = pathspec.PathSpec.from_lines('gitwildmatch', f)
    print(f"开始从 {src_path} 复制文件（已启用忽略机制）...")
    # 4. 遍历并执行“忽略”逻辑
    count = 0
    # rglob('*') 递归搜索
    for file in src_path.rglob('*'):
        # 只处理文件（文件夹会随文件创建）
        if file.is_file():
            # 计算相对于当前脚本目录的路径
            rel_path = file.relative_to(src_path)
            # --- 核心逻辑：如果不匹配规则，则进行复制 ---
            if spec and not spec.match_file(str(rel_path)):
                # 防止脚本意外把自己复制进去了（如果 dest 在 src 内部）
                if dest_path in file.parents:
                    continue

                target_file = dest_path / rel_path
                target_file.parent.mkdir(parents=True, exist_ok=True)

                shutil.copy2(file, target_file)
                count += 1
                # print(f"[已复制] {rel_path}") # 如果文件太多可以注释掉这一行
    print(f"\n任务完成！共复制了 {count} 个文件到 {dest_path}")
    descriptor_file_path = os.path.join(dest_dir, "descriptor.mod")
    try:
        with open(descriptor_file_path, 'w', encoding='utf-8') as f:
            f.write(descriptor_mod_text)
        print(f"成功创建descriptor.mod文件: {descriptor_file_path}")
    except Exception as e:
        print(f"创建descriptor.mod文件时出错: {e}")


if __name__ == "__main__":
    # 你可以在这里修改规则文件名和目标位置
    sync_with_ignore_mechanism(MOD_TEXT, "release.ignore", "../A UTTNH Fxor Edition")
