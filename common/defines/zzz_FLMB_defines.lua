NDefines.NGame.END_DATE = "2000.1.1.1"
-- 通用
NDefines.NBuildings.MAX_SHARED_SLOTS = 64
NDefines.NBuildings.MAX_BUILDING_LEVELS = 25 -- 建筑可以拥有的最大等级。 15
-- 基础设施
NDefines.NBuildings.INFRASTRUCTURE_RESOURCE_BONUS = 0.05 -- 每个（未损坏的）基础设施等级对资源的倍增奖励 0.15
NDefines.NMilitary.INFRA_ORG_IMPACT = 0.1 -- 基础设施对组织度恢复的比例因子 0.5
NDefines.NMilitary.INFRASTRUCTURE_MOVEMENT_SPEED_IMPACT = -0.01 -- 低于最大基础设施时每点基础设施的速度惩罚 -0.05
NDefines.NAI.CONSTRUCTION_PRIO_INFRASTRUCTURE = 0.4 -- base prio for infrastructure in the construction queue 0.20
NDefines.NSupply.INFRA_TO_SUPPLY = 0.1 -- each level of infra gives this many supply 0.3
NDefines.NSupply.SUPPLY_FROM_DAMAGED_INFRA = 0.05 -- damaged infrastructure counts as this in supply calcs 0.15
-- 机场
NDefines.NMilitary.PLAN_PORVINCE_AIRFIELD_LEVEL_FACTOR = 0.125 -- 机场等级的奖励因子 0.25
-- 堡垒
NDefines.NMilitary.LAND_COMBAT_FORT_DAMAGE_CHANCE = 20 -- 对堡垒造成伤害的几率。（每100次攻击） 5
NDefines.NMilitary.BASE_FORT_PENALTY = -0.05 -- 堡垒惩罚 0.15
NDefines.NMilitary.PLAN_AREA_DEFENSE_FORT_IMPORTANCE = 0.1 -- 用于为战斗计划系统计算防御区省份的价值，作为其余部分的乘数
NDefines.NMilitary.PLAN_AREA_DEFENSE_COASTAL_FORT_IMPORTANCE = 1.0 -- 用于为战斗计划系统计算防御区省份的价值
NDefines.NMilitary.PLAN_AREA_DEFENSE_COAST_NO_FORT_IMPORTANCE = 0.4 -- 用于为战斗计划系统计算防御区省份的价值
NDefines.NMilitary.PLAN_EXECUTE_CAREFUL_MAX_FORT = 15 -- 如果执行模式设置为谨慎，单位将不会攻击堡垒等级大于或等于此的省份 5
-- NDefines.NAI.LAND_COMBAT_ENEMY_LAND_FORTS_AIR_IMPORTANCE = 3 -- 敌方陆地要塞在该区域的战略重要性 5
-- NDefines.NAI.LAND_COMBAT_ENEMY_COASTAL_FORTS_AIR_IMPORTANCE = 2 -- 敌方沿海战线在该区域的战略重要性 3
NDefines.NAI.LAND_COMBAT_BOMBERS_PER_LAND_FORT_LEVEL = 3 -- 每级敌方陆地要塞所需轰炸机数量 6
NDefines.NAI.LAND_COMBAT_BOMBERS_PER_COASTAL_FORT_LEVEL = 3 -- 每级敌方海岸要塞所需轰炸机数量 6
NDefines.NAI.AREA_DEFENSE_SETTING_FORTS = true -- AI 默认使用哪些区域防御设置 false
NDefines.NAI.AIFC_PATH_COST_PER_FORT_LEVEL = 0.1 -- AIFC 的进攻路径评分（成本乘数） 此乘数计算方式为：1.0 + <define>*要塞等级（仅适用于要塞等级 > 0） 0.3
