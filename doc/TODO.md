# XPS→MMD 待修复项

## 权重问题

### [中] ひじ 权重 = 0
- **日期**: 2026-04-25 发现
- **现象**: 左ひじ/右ひじ VG 在 pipeline 结束后不存在，target 各有 1611 verts
- **已尝试**: gradient split 改为 additive mode（不消费 ひじ 源权重），代码已提交但效果未体现
- **根因推测**: ひじ VG 在 gradient split 之前就已被清空。可能在 mmd_convert (step 5) 或 D 骨 (step 6) 阶段被某步骤移除。需要在 pipeline 每步之间插入 checkpoint 确认 ひじ VG 状态
- **排查方向**: 在 one_click_convert 的 step 5/6/7 之间加 debug print，确认 ひじ VG 在哪一步消失

### [中] 足D 权重过少 (275 vs target 6567)
- **日期**: 2026-04-25 发现
- **现象**: D 骨 copy+clear 时 足 VG 本身就很少 verts，copy 后 D 骨权重不足
- **根因**: VG rename (step 1) 成功把 `leg left thigh` → `左足`，但后续步骤消耗了 足 权重。Step 9 的 VG cleanup 在 D 骨 (step 6) 之后才跑，把旧名 VG 合回 足——此时 足 已经被 D 骨 copy 清空过了
- **修复方向**: 把 VG cleanup 移到 D 骨之前，或者让 D 骨 operator 也检查旧名 VG

### [低] 足 残留 306/596 verts (应为 0)
- **日期**: 2026-04-25 发现
- **现象**: D 骨 copy+clear 后 足 VG 应为 0，但 Step 9 VG cleanup 重新合入了旧名权重
- **根因**: VG cleanup 跑在 D 骨之后，把 `leg left/right thigh` 合入已清空的 `左足/右足`
- **修复方向**: 同上，调整 cleanup 时序

## 骨骼结构

### [低] 指根骨缺失 (人指０/中指０/薬指０/小指０)
- **日期**: 2026-04-25 确认
- **现象**: target 有指根骨 (各 ~1000 verts, parent=手首)，auto 的指骨直接 parent=手首
- **根因**: XPS 没有 carpal 骨，需要新建+从手首 split 权重
- **备注**: 涉及权重切分，按"不切权重"原则暂不实现。后续如有需要再讨论

### [低] 肩/腕捩/手捩 左右不対称
- **日期**: 2026-04-25 确认
- **现象**: 肩 左 1710 vs 右 589 (2.9x)，腕捩/手捩 也有 2x+ 不対称
- **根因**: 腋窝 `_split_chain_weights` 左 1688 vs 右 636 verts (2.66x)，源于 body mesh 几何微妙差异
- **修复方向**: 可加対称性修正 (mirror 左→右或均值化)，但可能对非対称模型引入误差

## 功能增强

### [中] 首1 骨缺失
- **日期**: 2026-04-25 发现
- **现象**: target 有首1 (2595 verts, parent=首)，位于首と頭之间
- **修复方向**: 类似上半身1，用 `_split_chain_weights` 从首 split

### [低] 胸部骨骼映射 (boob → 乳奶)
- **日期**: 2026-04-25 发现
- **现象**: auto 用 `boob left/right 1/2` (XPS 原名)，target 用 `乳奶.L/.R`
- **修复方向**: 在 rename_to_mmd 中加映射，或在 helper_classifier 中识别

### [低] 面部表情骨 (QQ 系列)
- **日期**: 2026-04-25 发现
- **现象**: target 有 QQ1~QQ36 等面部骨 (~500 verts each)，auto 用 XPS 原名
- **修复方向**: 需要 XPS→MMD 面部骨映射表

---

## 已修复记录

| 日期 | 版本 | 问题 | 修复 |
|------|------|------|------|
| 2026-04-25 | v1.3 | pelvis VG 时序 bug (下半身 482→6797) | xps_fixes_operator: 去掉 bone 存在性检查 |
| 2026-04-25 | v1.4 | VG rename 失败 (1410 verts 悬空) | rename_bones: 先 rename VG 再 rename bone |
| 2026-04-25 | v1.4 | one_click VG cleanup map 失效 | 保存 XPS→MMD map 在 rename 前 |
| 2026-04-25 | v1.5 | D 骨 mix_mode AFTER | add_leg_d/add_twist: AFTER → ADD |
| 2026-04-25 | v1.5 | 上半身1 缺失 | complete_bones: 新建+split (5842 verts) |
| 2026-04-25 | v1.5 | 上半身1 被 transfer 吃掉 | xps_fixes: STANDARD_MMD_BONES 白名单 |
| 2026-04-25 | v1.5 | D 骨 VG 用 rename 不用 copy | add_leg_d: 改为 copy+clear |
| 2026-04-25 | v1.5 | 捩 _dummy_/_shadow_ use_deform=True | add_twist: 改 False |
| 2026-04-25 | v1.5 | ひじ gradient split 消费源权重 | add_twist: ひじ→手首 改 additive |
