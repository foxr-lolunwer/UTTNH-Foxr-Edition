# UTTNH: Foxr Edition

🌐 [Chinese Version / 中文版](README_zh.md)

A standalone, authorized fork of **UTTNH_2.0** for Hearts of Iron IV (HOI4), tailored for a deeper and more immersive gameplay experience. This project has received explicit permission from the original author to be independently maintained, updated, and published.

👉 **[View Authorization](Authorization.png)**

---

## 📌 Current Status

The mod is currently in a **code refactoring stage**.

> [!NOTE]
> The current phase strictly focuses on code sanitization and backend framework implementation. No unique custom gameplay mechanics or content have been added yet.

> [!WARNING]
> This fork removes a substantial amount of legacy UTTNH content, such as outdated modifications to Military Industrial Organizations (MIOs) and AI strategies.
> Due to limited development resources, you must own at least the DLCs that introduce the Tank Designer and Aircraft Designer features to use this mod.

---

## 🛠️ Optimizations & Fixes Applied

While no new custom mechanics have been introduced yet, this edition implements the following critical improvements over the baseline UTTNH:

*   **Up-to-date Compatibility**: Successfully integrated and adapted **major** codebase changes from all official HOI4 updates (including patch 1.17 and its accompanying DLC *Thunder at Our Gates*) released since UTTNH's last update.
*   **Tech Tree Code Formatting**: Re-engineered and strictly formatted the original technology script files. Properties have been reordered, indentation normalized, and path logic standardized to maximize future modding and expansion efficiency.
*   **Code Sanitization & Streamlining**: Purged unnecessary and redundant files, making the mod more lightweight while keeping all core functionality intact.
*   **Integrated Chinese Localization**: Fully incorporated the localization assets from the UTTNH_2.0 CNT project, which was initiated and co-authored by myself.

---

## 🌐 Supported Languages

This mod currently includes localization support for the following languages, categorized by their maintenance status:

* **🇬🇧 English** - **Native Support**.
* **🇨🇳 Chinese** - **Native Support**. Fully integrated with the UTTNH_2.0 CNT localization project, fully maintained and updated by myself.
* **🇷🇺 Russian** - **Inherited from upstream**. Retains the legacy translation from the original UTTNH mod. Due to limited development resources, **I will not actively maintain or update this language**.
* **🇩🇪 German** - **Inherited from upstream**. Retains the legacy translation from the original UTTNH mod. Likewise, **this is not included in my future maintenance plans**.

> [!TIP]
> 🤝 **To Translators & Community Contributors:**
> I highly welcome and encourage developers and translators of any other languages to join in! This mod is more than excited to support a diverse language ecosystem in the future.
> 
> **⚠️ Translation Advice for the Current Stage:**
> Please note that the mod is currently undergoing **heavy backend refactoring, meaning the codebase and localization text are highly unstable. Therefore, it is NOT recommended to start any active translation work at this stage.**
> 
> **💡 Submission Model:**
> I highly suggest that translators publish their respective language packs as **standalone localization sub-mods** on the Steam Workshop. 
> Once you have completed the upload, you can contact me (via Steam, etc.) to have the link to your language pack added here.
---

## 📅 Roadmap

1.  **Black ICE-Style Construction Tech**: Introduce deeper and more comprehensive industry construction and infrastructure modifiers. (Development is mostly complete, currently awaiting integration with the tier system)
2.  **Tech-Tier System**: Lower the rigid year-based restrictions of UTTNH technologies and replace them with a dynamic research tier system. (Awaiting backend refactoring completion)
3.  **Doctrine Tree Overhaul**: Completely rewrite existing doctrine logic and extend the overall length and depth of the doctrine trees. (Planned for later)
4.  ...
