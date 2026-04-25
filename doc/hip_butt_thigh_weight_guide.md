# XPS→PMX 臀部/大腿权重修复指南

> 从 Convert_to_MMD_claude 项目 12 轮迭代 + xps_to_mmd 28 轮迭代踩坑提炼。
> 适用于所有 XPS Lara / DAZ Genesis 系模型。

## 核心原则

**不切权重。** 保留 XPS 原始权重，靠 parent-chain 继承变形。

- 允许：copy（足→足D）、rename（pelvis→下半身）、PRESERVE helper 骨
- 禁止：merge helper 到主骨、手动改单顶点权重、用绝对阈值删权重

---

## 七条硬规则

每条都是血泪教训，绝对不能违反：

1. **永远不手动编辑单顶点权重。** 上臂 twist 问题花了 13 个 commit 改权重，最后发现只差一行 `apply_additional_transform`。
2. **永远不把 helper 骨 (xtra/ThighTwist/muscle_elbow) 合并到主变形骨。** helper 骨有自己的轴向和 XPS 原始分布，合并会丢失独特变形。
3. **永远不用绝对阈值删下半身权重。** `max_d_w >= 0.1 → 删下半身` 在 Reika 上毁了 3510 顶点。正确做法：严格优势 `max_d_w > lower_w`。
4. **永远不把 pelvis helper 骨 reparent 到腰。** 会导致 parent 链不匹配。xtra08 保持 parent=pelvis（→下半身）。
5. **永远不用 proximity-based weight transfer 处理 twist 骨。** 通用距离迁移精度不够，只用双骨线性插值。
6. **永远不把 "xtra/D骨权重比例低" 当 bug 修。** Inase 足D 2.7% vs target 15.1% 是 mesh 密度差异，不是管线问题。
7. **永远不跳诊断层级。** L4→L1→L2→L3 严格顺序，大部分 "腿权重看着不对" 的根因在 L1/L2。

---

## 诊断顺序：L4 → L1 → L2 → L3

### L4 语义层（骨骼名称）
- rename_to_mmd + preset 映射是否正确
- VMD 能否按名字找到骨骼

### L1 几何层（rest pose 对齐）
- `align_arms_to_reference` / `fix_forearm_bend`
- `complete_missing_bones` 补全 MMD 必需骨
- 检查 `bone.head_local` / 方向是否匹配 target

### L2 约束/Parent 链层
- `apply_additional_transform` 是否调用
- twist 骨 additional_transform 属性是否设置（influence 0.25/0.50/0.75）
- D 骨 TRANSFORM 约束是否存在
- helper 骨 parent 链是否正确（xtra08→pelvis→下半身）
- **诊断技巧**：Pose Mode 旋转 parent 骨，看 child 是否跟随。不跟随 = 约束链断裂。

### L3 蒙皮层（权重 — 最后手段）
- 只在 L4/L1/L2 全部排除后才动
- 只用保守操作（见下方）

---

## XPS 骨骼映射

### 必须直接 rename 的骨
| XPS 骨 | MMD 骨 | 说明 |
|--------|--------|------|
| `bip001 pelvis` | `下半身` | 臀部主骨，直接 rename VG，不做 per-vertex-nearest |

### 必须 PRESERVE 的 helper 骨（保留 XPS 原始权重）
| XPS 骨 | parent | 顶点数(Inase) | 说明 |
|--------|--------|---------------|------|
| `xtra04` | 足.L | ~853 | 左大腿内侧 helper |
| `xtra02` | 足.R | ~850 | 右大腿内侧 helper |
| `xtra08` | pelvis | ~1082 | 左臀部/大腿外侧 helper |
| `xtra08opp` | pelvis | ~1228 | 右臀部/大腿外侧 helper |
| `muscle_elbow` | 腕捩 | ~36 | 肘部 helper（不在 twist 内） |
| `foretwist` / `foretwist1` | 手捩 | ~1100+ | 前臂 twist（由 twist operator 处理） |

### 必须清理的控制骨权重
| 骨 | 说明 |
|----|------|
| `全ての親` | 根骨 use_deform=False，头发/头部 3362 verts 留在上面会卡住不动。VG rename 到 `頭` |
| `センター` / `グルーブ` | 控制骨，不应有顶点权重 |

---

## Parent 链修复

### pelvis reparent
XPS pelvis 骨 parent=センター（根），但 MMD 下半身 parent=腰。
xtra08/xtra08opp parent=pelvis → 如果 pelvis 挂在センター下，下半身旋转时 xtra08 不跟随 → 臀部撕裂。

**修复**：`complete_bones` 后把 `unused bip001 pelvis` reparent 到 `下半身`。

```python
pelvis_bone = edit_bones.get("unused bip001 pelvis")
lower_body = edit_bones.get("下半身")
if pelvis_bone and lower_body:
    pelvis_bone.parent = lower_body
```

### 首.parent 丢失 bug
`bone_properties` dict 中首在上半身3之前，`create_or_update_bone` 设 parent 时上半身3尚未创建。
**修复**：二次 pass 重设所有 parent。

---

## 上半身/下半身 head 重合问题

两骨 head 位置相同，per-vertex-nearest 无法区分。

**修复**：Z 坐标判断，低于 `上半身.head.z` 的上半身顶点移到下半身。

```python
if vp.z < ub_z - 0.01:
    lb_vg.add([v.index], g.weight, 'ADD')
    ub_vg.remove([v.index])
```

---

## 下半身权重清理（Lower Body Cleanup）

只在 D 骨权重严格大于下半身权重时才删下半身：

```python
if max_d_w > lower_w:
    verts_to_remove.append(v.index)
```

**绝对不能**用 `max_d_w >= 0.1` 或 `max_d_w > 0` 等绝对阈值。

---

## D 骨陷阱

### 腰キャンセル additional_transform_bone
- 必须是 `腰`，不是 `下半身`
- 如果指向 `下半身`，reimport 后 `_dummy_腰キャンセル` parent=下半身，导致下半身大旋转叠加到腰キャンセル → 腿 IK 剧烈抖动

### D 骨权重 = copy 不是 cut
- `足.L → 足D.L` 是完整复制权重，原骨权重不动
- 不能删原骨权重

### Phase 执行顺序
1. Phase 2: unused → main bone（pelvis→下半身，但 PRESERVE 列表跳过）
2. Phase 1: main bone → D bone（足→足D，copy）
3. Phase 4: Stray fix（distance > body_h * 0.185 才动）
4. Phase 5: Lower Body Cleanup（strict dominance）
5. Phase 6: 全ての親 → 頭

**顺序不能反**。Phase 2 在 Phase 1 之前：unused 权重先合入 main bone，再 copy 到 D bone。

---

## 两种模型架构

### Inase (XNA Lara)
- 4 个 helper 骨：xtra02/04 (parent=thigh) + xtra08/08opp (parent=pelvis)
- 全部 PRESERVE，靠 parent-chain 继承
- Lower Body Cleanup 删 下半身 权重后，xtra08 自然接管臀部变形

### Reika (DAZ Genesis 8)
- 有 lThighTwist/rThighTwist (parent=足.L)，没有 parent=pelvis helper
- ThighTwist 自动保留（无 `unused` 前缀）
- Lower Body Cleanup 必须用 strict dominance（没有 helper 骨补偿，删错直接爆）

**同一管线同时通过两种架构** = 设计正确。

---

## 快速排查清单

遇到臀部/大腿问题时按顺序检查：

1. [ ] 骨骼名是否正确？rename log 有无 Missing？
2. [ ] rest pose 对齐了吗？arm alignment 角度合理？
3. [ ] Pose Mode 旋转 足.L → xtra04/足D.L 跟随吗？
4. [ ] `apply_additional_transform` 调用了吗？
5. [ ] helper 骨 parent 链正确吗？（xtra08→pelvis→下半身，不是→センター）
6. [ ] 下半身 VG 有权重吗？（pelvis 是否成功 rename 过来）
7. [ ] 全ての親 VG 清理了吗？（头发区域不能留在根骨上）
8. [ ] 如果确认是 L3：是 Lower Body Cleanup 过度删除？Stray weight？**永远不手动改单顶点。**
