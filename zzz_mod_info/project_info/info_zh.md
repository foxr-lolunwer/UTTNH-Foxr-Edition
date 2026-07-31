# 推荐开发流程

项目开发说明，用于推荐开发流程。开发者不需要掌握所有技能，根据需求选择合适的工具与配置即可。

[English Version / 英文版](info.md)

---

## 推荐插件 / 软件

### 1. VSCode（代码编写 / GUI设计 / GFX引用编辑 / 科技树设计）

主要使用 VSCode 进行代码编写、GUI设计、GFX引用编辑以及科技树设计。`Hoi4 Mod Utilities` 提供了便利的 HOI4 界面可视化功能。

#### 插件推荐

* **Recommended**
  * `chaofan.hoi4modutilities` - GUI/科技树预览
  * `tboby.paradox-syntax` - 代码提示高亮
* **Optional**
  * `tboby.cwtools-vscode` - 代码提示规则库
  * `Thinker.secondary-explorer` - 右侧的第二个资源管理器，参考用
  * `ms-python.python` - Python编辑，编辑器快速运行.py文件
  * `ms-python.debugpy` - Python Debug 更推荐使用PyCharm

#### VSCode 的工作区配置注释

```json5
{
    "folders": [
        {
            "name": "BASE", // 项目文件夹
            "path": "."
        },
        {
            "name": "RELEASE", // release.py的导出文件夹
            "path": "../A UTTNH Fxor Edition"
        },
        {
            "name": "TECH EP", // 我自己之前做的科技拓展模组，用于参考
            "path": "../tech ep"
        },
        // ...在此处添加其他参考文件夹路径
        {
            "name": "HOI4-RO", // HOI4原版路径，用于查找用法等
            "path": "E:/SteamLibrary/steamapps/common/Hearts of Iron IV"
        }
    ],
    "settings": {
        // 设置只读限制，防止误修改HOI4原版文件或创意工坊文件等
        "files.readonlyInclude": {
            "E:/SteamLibrary/steamapps/workshop/content/394360/**": true,
            "E:/SteamLibrary/steamapps/common/Hearts of Iron IV/**": true,
            "E:/Documents/Paradox Interactive/Hearts of Iron IV/mod/tech ep/**": true,
        },
        // 关闭默认的点击文件自动在资源管理器定位
        // 关闭编辑器的预览模式，这个模式会导致打开多个文件时会自动关闭未保存的文件
        "explorer.autoReveal": false,
        "workbench.editor.enablePreview": false,
        "workbench.editor.enablePreviewFromQuickOpen": false,
        // Secondary Explorer设置，这里对应工作区的第四个文件夹，即HOI4-RO
        "secondaryExplorer.paths": [
            "${workspaceFolders[4]}"
        ]
    }
}
```

---

### 2. JetBrains IDE（代码编写 / 本地化文件编写）

适合在代码编写过程中有频繁检查错误需求的开发者，或用于本地化文件编写。

#### 插件推荐

* **Recommended**
  * `Paradox Chronicle By DragonKnightofBreeze`

#### 说明

* **功能特点**：
  * 用来进行代码编写（有需要频繁检查错误的需求）以及 `.yml` 本地化文件编写。
  * `Paradox Chronicle` 的提示能力比 `CWTools` 更强大，但有时过多的提示信息反而不利于开发。
  * `.yml` 本地化文件本身并不复杂，`Paradox Chronicle` 提供了适用于 HOI4 的 yml 文件规则，还提供了格式化工具（一键设置颜色等），能极大提升编写效率。
* **软件选择**：
  * 通常 IDEA 的内存占用比 VSCode 多。
  * 如果需要兼顾 Python 脚本编写与运行，可以使用 PyCharm（注：Python 脚本对于本项目其他开发者而言并非核心内容）。


> **额外说明**：
> 上面两个提供代码语法检查的插件规则库均不是最新/一定正确的，一些新语法往往会导致误报错
---

### 3. PhotoShop（纹理编辑）

* **必要项**：**必须安装 DDS 插件**才能编辑 DDS 文件。
* **推荐项**：NVIDIA Texture Tools（DDS 插件）。
* **操作注意**：保存时选择 **“存储为”** 而不是 “导出”。
* **参数对应选项参考**：[截图](NVT_DDS.png)

---

### 4. Paint\.NET（纹理编辑）

* **特点**：比 PhotoShop 更轻量，建议一般只用来处理低级任务。
* **格式支持**：原生支持 DDS 格式。
* **参数对应选项参考**：[截图（白色警告）](Paint_DDS.png)

> **DDS 保存规范**：
> DDS 文件需要保存为 **32位 BGRA 无符号** 类型（对应各自插件/平台选项，详见上述截图）。

---

## 开发者工作流程速查表

1. **代码编写 / GUI设计 / GFX引用编辑 / 科技树设计**：主要使用 **VSCode**，配合 `Hoi4 Mod Utilities` 进行可视化预览。
2. **代码排查 / 本地化编写**：使用 **JetBrains IDE**，利用 `Paradox Chronicle` 进行实时的语法检查以及 `.yml` 彩色文本格式化处理。
3. **纹理处理**：基础低级任务使用 **Paint\.NET**，复杂纹理处理使用 **PhotoShop**（必须安装 DDS 插件），导出时统一选择 **32位 BGRA 无符号** 类型。也可以使用PNG格式的纹理。
