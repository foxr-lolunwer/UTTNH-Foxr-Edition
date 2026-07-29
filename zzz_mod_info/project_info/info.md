# Recommended Development Workflow

Project development guide recommending the development workflow. Developers do not need to master all skills; simply choose the appropriate tools and configurations based on your needs.

[Chinese Version / 中文版](info_zh.md)

---

## Recommended Plugins / Software

### 1. VSCode (Code Editing / GUI Design / GFX Reference Editing / Tech Tree Design)

VSCode is primarily used for code editing, GUI design, GFX reference editing, and tech tree design. `Hoi4 Mod Utilities` provides convenient visual preview features for the HOI4 interface.

#### Plugin Recommendations

* **Recommended**
  * `chaofan.hoi4modutilities` - GUI / Tech tree preview
  * `tboby.cwtools-vscode` - Code completion rules library
  * `tboby.paradox-syntax` - Code highlighting
* **Optional**
  * `Thinker.secondary-explorer` - A second file explorer on the right side, useful for reference
  * `ms-python.python` - Python editing, allows quickly running .py files in the editor
  * `ms-python.debugpy` - Python debugging (PyCharm is more recommended for this)

#### VSCode Workspace Configuration Notes

```json5
{
    "folders": [
        {
            "name": "BASE", // Project folder
            "path": "."
        },
        {
            "name": "RELEASE", // Export folder for release.py
            "path": "../A UTTNH Fxor Edition"
        },
        {
            "name": "TECH EP", // A tech expansion mod I made previously, used for reference
            "path": "../tech ep"
        },
        // ...Add other reference folder paths here
        {
            "name": "HOI4-RO", // Vanilla HOI4 path, used for checking usages, etc.
            "path": "E:/SteamLibrary/steamapps/common/Hearts of Iron IV"
        }
    ],
    "settings": {
        // Set read-only restrictions to prevent accidental modifications to vanilla HOI4 files or Workshop files
        "files.readonlyInclude": {
            "E:/SteamLibrary/steamapps/workshop/content/394360/**": true,
            "E:/SteamLibrary/steamapps/common/Hearts of Iron IV/**": true,
            "E:/Documents/Paradox Interactive/Hearts of Iron IV/mod/tech ep/**": true,
        },
        // Disable auto-revealing files in the explorer when clicked
        // Disable editor preview mode, which automatically closes unsaved files when opening multiple files
        "explorer.autoReveal": false,
        "workbench.editor.enablePreview": false,
        "workbench.editor.enablePreviewFromQuickOpen": false,
        // Secondary Explorer settings, corresponding to the fourth folder in the workspace (HOI4-RO)
        "secondaryExplorer.paths": [
            "${workspaceFolders[4]}"
        ]
    }
}
```

---

### 2. JetBrains IDE (Code Editing / Localization File Editing)

Suitable for developers who need to check for errors frequently during code editing, or for editing localization files.

#### Plugin Recommendations

* **Recommended**
  * `Paradox Chronicle By DragonKnightofBreeze`

#### Description

* **Features**:
  * Used for code editing (when frequent error checking is needed) and `.yml` localization file editing.
  * The code completion of `Paradox Chronicle` is more powerful than `CWTools`, but sometimes excessive prompts can be counterproductive for development.
  * `.yml` localization files themselves are not complex; `Paradox Chronicle` provides yml file rules adapted for HOI4, as well as formatting tools (like one-click color setting), which greatly improves editing efficiency.
* **Software Choice**:
  * Generally, IDEA consumes more memory than VSCode.
  * If you need to write and run Python scripts as well, you can use PyCharm (Note: Python scripts are not core content for other developers in this project).

> **Additional Note**:
> The rule libraries of the two plugins providing syntax checking above are not always the latest/strictly correct. Some new syntax will often cause false-positive errors.

---

### 3. PhotoShop (Texture Editing)

* **Requirement**: You **must install a DDS plugin** to edit DDS files.
* **Recommendation**: NVIDIA Texture Tools (DDS plugin).
* **Operation Note**: Choose **"Save As"** instead of "Export" when saving.
* **Parameter options reference**: [Screenshot](NVT_DDS.png)

---

### 4. Paint\.NET (Texture Editing)

* **Characteristics**: More lightweight than PhotoShop; it is generally recommended only for handling low-level tasks.
* **Format Support**: Natively supports the DDS format.
* **Parameter options reference**: [Screenshot (White Warning)](Paint_DDS.png)

> **DDS Saving Specifications**:
> DDS files must be saved as the **32-bit BGRA Unsigned** type (corresponding to the respective plugin/platform options, see the screenshots above).

---

## Developer Workflow Quick Reference

1. **Code Editing / GUI Design / GFX Reference Editing / Tech Tree Design**: Primarily use **VSCode**, combined with `Hoi4 Mod Utilities` for visual previewing.
2. **Code Troubleshooting / Localization Editing**: Use **JetBrains IDE**, utilizing `Paradox Chronicle` for real-time syntax checking and `.yml` colored text formatting.
3. **Texture Processing**: Use **Paint\.NET** for basic low-level tasks, and **PhotoShop** (DDS plugin required) for complex texture processing. Uniformly select the **32-bit BGRA Unsigned** type when exporting. PNG format textures can also be used.

---
*Note: This English translation was generated by Gemini.*