#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
批量文件内容替换工具（无命令行参数，直接配置变量）
支持正则表达式、递归目录、自动备份、扩展名过滤
"""

import sys
import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional

# ==================== 用户配置区域 ====================

# 1. 替换字典：{ "原始文本": "替换文本" }
# REPLACEMENTS = {
#     " y = 0 ": " y = @Tier1_1 ",
#     " y = 2 ": " y = @Tier1_2 ",
#     " y = 4 ": " y = @Tier2_1 ",
#     " y = 6 ": " y = @Tier2_2 ",
#     " y = 8 ": " y = @Tier3_1 ",
#     " y = 10 ": " y = @Tier3_2 ",
#     " y = 12 ": " y = @Tier4_1 ",
#     " y = 14 ": " y = @Tier4_2 ",
#     " y = 16 ": " y = @Tier5_1 ",
#     " y = 18 ": " y = @Tier5_2 ",
#     " y = 20 ": " y = @Tier6_1 ",
#     " y = 22 ": " y = @Tier6_2 ",
#     " y = 24 ": " y = @Tier7_1 ",
#     " y = 26 ": " y = @Tier7_2 ",
#     " y = 28 ": " y = @Tier8_1 ",
#     " y = 30 ": " y = @Tier8_2 ",
# }
REPLACEMENTS = {
    "y = @Tier8_2 } }": "y = @Tier8_2 } }\n        dependencies = { FLTE_tech_tier_ordn_8 = 1 }",
    "y = @Tier8_1 } }": "y = @Tier8_1 } }\n        dependencies = { FLTE_tech_tier_ordn_8 = 1 }",
    "y = @Tier7_2 } }": "y = @Tier7_2 } }\n        dependencies = { FLTE_tech_tier_ordn_7 = 1 }",
    "y = @Tier7_1 } }": "y = @Tier7_1 } }\n        dependencies = { FLTE_tech_tier_ordn_7 = 1 }",
    "y = @Tier6_2 } }": "y = @Tier6_2 } }\n        dependencies = { FLTE_tech_tier_ordn_6 = 1 }",
    "y = @Tier6_1 } }": "y = @Tier6_1 } }\n        dependencies = { FLTE_tech_tier_ordn_6 = 1 }",
    "y = @Tier5_2 } }": "y = @Tier5_2 } }\n        dependencies = { FLTE_tech_tier_ordn_5 = 1 }",
    "y = @Tier5_1 } }": "y = @Tier5_1 } }\n        dependencies = { FLTE_tech_tier_ordn_5 = 1 }",
    "y = @Tier4_2 } }": "y = @Tier4_2 } }\n        dependencies = { FLTE_tech_tier_ordn_4 = 1 }",
    "y = @Tier4_1 } }": "y = @Tier4_1 } }\n        dependencies = { FLTE_tech_tier_ordn_4 = 1 }",
    "y = @Tier3_2 } }": "y = @Tier3_2 } }\n        dependencies = { FLTE_tech_tier_ordn_3 = 1 }",
    "y = @Tier3_1 } }": "y = @Tier3_1 } }\n        dependencies = { FLTE_tech_tier_ordn_3 = 1 }",
    "y = @Tier2_2 } }": "y = @Tier2_2 } }\n        dependencies = { FLTE_tech_tier_ordn_2 = 1 }",
    "y = @Tier2_1 } }": "y = @Tier2_1 } }\n        dependencies = { FLTE_tech_tier_ordn_2 = 1 }",
    "y = @Tier1_2 } }": "y = @Tier1_2 } }\n        dependencies = { FLTE_tech_tier_ordn_1 = 1 }",
    "y = @Tier1_1 } }": "y = @Tier1_1 } }\n        dependencies = { FLTE_tech_tier_ordn_1 = 1 }",
}

# 2. 目标文件或目录（二选一）
TARGET_FILE = r"./zz_FLTE_support.txt" if len(sys.argv) < 2 else sys.argv[1]
TARGET_DIR = ""

# 3. 处理选项
USE_REGEX = False           # 是否将 REPLACEMENTS 的键作为正则表达式
CASE_SENSITIVE = True       # 是否区分大小写（仅对普通字符串有效，正则由模式本身控制）
RECURSIVE = True            # 处理目录时是否递归子目录
EXTENSIONS = []  # 仅处理这些扩展名（空列表表示全部）
BACKUP = True               # 是否生成 .bak 备份文件
ENCODING = "utf-8"          # 读写编码（自动尝试 gbk 等）

# ====================================================

class FileReplacer:
    def __init__(self):
        self.replacements = REPLACEMENTS
        self.use_regex = USE_REGEX
        self.case_sensitive = CASE_SENSITIVE
        self.backup = BACKUP
        self.encoding = ENCODING
        self.stats = {"processed": 0, "modified": 0, "failed": 0, "total": 0}

    def _read_file(self, path: Path) -> Optional[str]:
        for enc in (self.encoding, "gbk", "utf-8-sig"):
            try:
                with open(path, "r", encoding=enc) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"⚠️ 读取失败 {path}: {e}")
                return None
        print(f"⚠️ 无法解码 {path}")
        self.stats["failed"] += 1
        return None

    def _write_file(self, path: Path, content: str) -> bool:
        try:
            with open(path, "w", encoding=self.encoding) as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"⚠️ 写入失败 {path}: {e}")
            self.stats["failed"] += 1
            return False

    def _apply(self, content: str) -> tuple:
        modified = content
        total = 0
        for old, new in self.replacements.items():
            if old == new:
                continue
            if self.use_regex:
                flags = 0 if self.case_sensitive else re.IGNORECASE
                try:
                    pattern = re.compile(old, flags)
                    modified, count = pattern.subn(new, modified)
                    total += count
                except re.error as e:
                    print(f"⚠️ 正则错误 '{old}': {e}")
            else:
                if self.case_sensitive:
                    count = modified.count(old)
                    if count:
                        modified = modified.replace(old, new)
                        total += count
                else:
                    # 不区分大小写：使用正则 re.IGNORECASE 实现
                    pattern = re.compile(re.escape(old), re.IGNORECASE)
                    modified, count = pattern.subn(new, modified)
                    total += count
        return modified, total

    def process_file(self, path: Path) -> bool:
        if not path.is_file() or path.suffix == ".bak":
            return False
        content = self._read_file(path)
        if content is None:
            return False
        new_content, count = self._apply(content)
        if new_content == content:
            print(f"⏭️ 未变更: {path}")
            return True
        if self.backup:
            shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
        if self._write_file(path, new_content):
            print(f"✅ 已修改: {path} (替换 {count} 处)")
            self.stats["modified"] += 1
            self.stats["total"] += count
            return True
        return False

    def process_directory(self, dir_path: Path):
        pattern = "**/*" if RECURSIVE else "*"
        for p in dir_path.glob(pattern):
            if not p.is_file() or p.suffix == ".bak":
                continue
            if EXTENSIONS and p.suffix.lower() not in [e.lower() for e in EXTENSIONS]:
                continue
            self.process_file(p)

    def run(self):
        if TARGET_FILE:
            self.process_file(Path(TARGET_FILE))
        elif TARGET_DIR:
            self.process_directory(Path(TARGET_DIR))
        else:
            print("❌ 请配置 TARGET_FILE 或 TARGET_DIR")
            return
        print("\n" + "=" * 50)
        print(f"📊 修改文件: {self.stats['modified']} | 失败: {self.stats['failed']} | 总替换: {self.stats['total']}")
        print("=" * 50)


if __name__ == "__main__":
    replacer = FileReplacer()
    replacer.run()