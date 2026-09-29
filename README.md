# UTTNH: Foxr Edition

🌐 [Chinese Version / 中文版](zzz_mod_info/README_zh.md)

An independent spin-off mod for *Hearts of Iron IV* (HOI4), engineered for a deeper and more immersive gameplay experience. Based on **UTTNH_2.0**, this mod has received official authorization from the original author for independent maintenance and publication.

Additionally, authorization for assets from other mods has been obtained—either via direct permission or standard open-licensing terms.  
👉 **For detailed permissions and credits, see the `zzz_mod_info` directory.**

---

## 📌 Current Development Status

This mod is currently in the **Content Refinement** phase.

> [!WARNING]
> **DLC Dependencies**  
> This mod deprecates and removes several outdated UTTNH base features (such as custom Military Industrial Organizations and AI strategies).  
> To ensure all core systems function properly, you **must** own the DLCs containing the following mechanics:
> * Tank Designer (*No Step Back*)
> * Aircraft Designer (*By Blood Alone*)
> * Intelligence Agency Systems (*La Résistance*)
> * Special Projects (*Götterdämmerung*)

---

## 🛠️ Completed Core Features

* **Codebase Optimization**: Refactored and streamlined bloated legacy code from UTTNH. This significantly improves readability and general mod compatibility without sacrificing functionality.
* **Technology Level System**: Replaced vanilla tech year restrictions with a novel Tech Level mechanic. Players must now raise their overall Tech Level to research advanced technologies.
* **Building Tier Limits**: Introduced cap constraints for primary state buildings, allowing players to expand building caps through technological advancement.
* **Overhauled Industry & Production Techs**: Completely replaces vanilla industrial tech trees. Offers comprehensive passive bonuses while retaining single-direction vanilla tech mapping for backend compatibility.

---

## 🌐 Supported Languages

Localization support is categorized into **Native Support** and **Inherited Support** based on current maintenance status:

| Language | Status | Notes |
| :--- | :--- | :--- |
| 🇨🇳 **Simplified Chinese** | **Native Support** | Primary development language |
| 🇬🇧 **English** | **Native Support** | Actively maintained |
| 🇷🇺 **Russian** | **Inherited** | Deprecated / Outdated; no active maintenance planned |
| 🇩🇪 **German** | **Inherited** | Deprecated / Outdated; no active maintenance planned |
| 🇫🇷 **French** | **Inherited** | Deprecated / Outdated; no active maintenance planned |

> [!TIP]
> 🤝 **To Community Translators & Collaborators:**  
> We warmly welcome and encourage translators to contribute to localization efforts!
> 
> **💡 Recommended Submission Workflow:**  
> We recommend publishing language translations as **standalone localization sub-mods** on the Steam Workshop. Once uploaded, feel free to reach out (via Steam, Discord, etc.) to have your sub-mod linked on the main Workshop page.

---

## 🧩 Mod Compatibility

⚠️ **The following types of mods are strictly INCOMPATIBLE:**

* **Tech Tree Layout Overhauls**: Any mod that modifies the base tech tree UI layout or injects new technologies directly into tech tree folders.
* **State Interface Overhauls**: Any mod that adds state building slots or alters state UI elements (*compatible ONLY with mods that attach side/popup windows to the state interface*).
* **Custom Building Icons**: Any mod that adds new buildings with **custom building icons**.

---

## 📅 Roadmap

1. **Industrial Capacity Throttle** *(Planned)*: Dynamically scales building speed penalties based on total owned factory count; penalties can be mitigated through industrial research.
2. **Tank Designer & Tech Overhaul** *(Candidate for v0.3.x, inspired by BlackICE)*
3. **Aircraft Designer & Tech Overhaul** *(Candidate for v0.3.x)*
4. **Naval Designer & Tech Overhaul** *(Candidate for v0.3.x, inspired by BlackICE & VNR)*
5. **Army Helicopter Designer & Techs** *(Planned)*: Introduces helicopters as a distinct army equipment type.
6. **Global Economic & Military Ledger** *(Planned)*: View global economic and military rankings with associated bonuses (*incompatible with mods adding non-vanilla equipment*).
7. **Localization File Refactoring** *(Planned)*: Further standardizes key-value strings and file structure for improved localization maintenance.
8. **Expanded Special Projects** *(Planned)*: Certain projects will release alongside vehicle designer overhauls.
9. **Motorized/Vehicle Designer Overhaul** *(Planned)*: Introduces a vehicle designer framework similar to *Millennium Dawn*.
10. **Espionage System Expansion** *(Under Evaluation)*: Core logic is implemented; public integration will depend on community feedback.