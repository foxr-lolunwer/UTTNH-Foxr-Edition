import re
import shutil
from pathlib import Path


CATEGORY_PATTERN = re.compile(
    r'^([ \t]*)categories\s*=\s*\{[ \t]*([^{}\r\n]*?)[ \t]*\}[ \t]*$',
    re.MULTILINE
)


def format_categories(content: str) -> str:
    def replace(match: re.Match) -> str:
        indent = match.group(1)
        categories = match.group(2).split()

        # 空 categories 不处理
        if not categories:
            return match.group(0)

        item_indent = indent + "\t"

        lines = [
            f"{indent}categories = {{"
        ]

        for category in categories:
            lines.append(f"{item_indent}{category}")

        lines.append(f"{indent}}}")

        return "\n".join(lines)

    return CATEGORY_PATTERN.sub(replace, content)


def process_file(file_path: Path):
    if not file_path.is_file():
        print("文件不存在")
        return

    # utf-8-sig 可以同时处理 UTF-8 和 UTF-8 BOM
    content = file_path.read_text(encoding="utf-8-sig")

    new_content = format_categories(content)

    if new_content == content:
        print("没有需要处理的 categories")
        return

    # 生成备份文件
    backup_path = file_path.with_name(
        file_path.name + ".bak"
    )

    # 如果已存在备份，不覆盖原始备份
    if backup_path.exists():
        print(f"备份文件已存在，取消处理：{backup_path}")
        return

    # 先备份原文件
    shutil.copy2(file_path, backup_path)

    # 确认备份成功后再写入
    file_path.write_text(
        new_content,
        encoding="utf-8",
        newline="\n"
    )

    print(f"处理完成: {file_path}")
    print(f"原文件备份: {backup_path}")


if __name__ == "__main__":
    set_file_path = r"E:\Documents\Paradox Interactive\Hearts of Iron IV\mod\UTTNH Foxr Edition\common\technologies\zz_FLTE_prod.txt"
    file_path = Path(set_file_path)

    if file_path.is_file():
        process_file(file_path)
    else:
        print("文件不存在")