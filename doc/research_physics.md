# 刚体物理调研报告

> 调研日期: 2026-04-25
> 目标: 为 xps_to_mmd 项目设计并实现 MMD 标准物理（身体碰撞 + 头发 + 胸部 + 裙子/衣物）
> 状态: 调研完成，进入实现阶段

---

## 一、调研方法

本次调研从 7 个来源并行收集信息：

| # | 来源 | 方法 | 关键发现 |
|---|------|------|---------|
| 1 | Convert_to_MMD_claude 代码 | 读 physics_operator.py + doc/ | 三层架构、bone-local 坐标、breast 中线塌陷 |
| 2 | mmd_tools API | 读源码 + grep 用法 | createRigidBody/createJoint 完整签名 |
| 3 | 远端记忆 (18.224.30.14) | SSH 查 memory/ | Tier 1/3 实现细节、已知 bug |
| 4 | xps_to_mmd 现有实现 | 读 physics_operator.py | 3 个 operator 已实现（body/hair/breast） |
| 5 | PMXEditor 原理 | 互联网调研 (日文社区) | 剛体参数、碰撞组、关节弹簧 |
| 6 | 自动物理工具 SOTA | 互联网调研 (PmxTailor 等) | 20+ 工具对比、无全自动方案 |
| 7 | MMD 物理参数最佳实践 | 互联网调研 (具体数值) | Oomary 法、曲面自動設定、柔軟剤 |

### 调研结论

1. **没有工具能从 mesh 全自动生成物理**——都需要人工识别哪些骨链是头发/裙子/披风
2. **我们的 physics_operator.py 已经实现了 body/hair/breast**，但参数需要对齐 MMD 最佳实践
3. **clone_physics.py 是 Tier 1 方案**（从 target PMX 克隆），但我们的目标是无 target 也能跑
4. **关键缺失：裙子/衣物物理**——需要新增 operator

---

## 二、MMD 物理体系

### 2.1 刚体类型

| 类型 | 代码 | 用途 | 行为 |
|------|------|------|------|
| Bone追従 (Static) | 0 | 身体骨（头/躯干/四肢） | 只跟骨运动，不受物理影响，作为碰撞墙 |
| 物理演算 (Dynamic) | 1 | 头发末端/裙子/配饰 | 受重力影响，驱动骨运动 |
| 物理+ボーン (Dynamic+Bone) | 2 | 头发根部/胸部/领带 | 受物理影响但会回弹到骨位置 |

**规则**：每个 Dynamic 刚体必须通过 Joint 链追溯到一个 Static 刚体，否则会掉到地上。

### 2.2 碰撞组规范

没有官方标准，但社区共识：

| 组 | 用途 | 备注 |
|---|------|------|
| 0 (Group 1) | 身体（静态） | 头/躯干/手臂/腿 |
| 1 (Group 2) | 头发（动态） | |
| 2 (Group 3) | 胸部（动态） | |
| 3 (Group 4) | 裙子/衣物（动态） | |
| 4+ | 配饰/额外 | |
| 15 (Group 16) | **保留给 MMD 地面** | 不要用于模型刚体 |

**碰撞规则**：
- 同类动态体（如所有头发链）设为**不与自身组碰撞**（防抖动）
- 头发/裙子**应与身体碰撞**（防穿模）
- 头发和裙子之间**通常不碰撞**（防干涉）

### 2.3 刚体参数最佳实践

#### 身体（静态）

| 参数 | 值 | 备注 |
|------|---|------|
| Mass | 1.0 | 静态体无所谓 |
| Move Damping | 0.5 | |
| Rot Damping | 0.5 | |
| Friction | 0.5 | |
| Bounce | 0.0 | |
| Shape | CAPSULE | 四肢用胶囊，头用球 |

#### 头发链

| 位置 | Mass | Move Damping | Rot Damping | Friction | Bounce |
|------|------|-------------|-------------|----------|--------|
| 根 (Dynamic+Bone) | 0.5 | 0.556 | 0.999 | 0 | 0 |
| 中间 (Dynamic) | 0.3→0.05 梯度 | 0.6→0.8 | 0.999 | 0 | 0 |
| 末端 (Dynamic) | 0.05→0.01 | 0.9 | 1.0 | 0 | 0 |

**核心原则**：质量沿链递减（末端轻 = 更飘逸），移动阻尼递增，旋转阻尼始终接近 1.0。

#### 胸部

| 参数 | 值 | 备注 |
|------|---|------|
| Mass | 0.5-1.0 | |
| Move Damping | 0.05-0.5 | 低 = 更弹 |
| Rot Damping | 0.05-0.5 | |
| Friction | 0 | |
| Bounce | 0.0 | **绝不超过 0.05**——否则会飞 |
| Shape | SPHERE | |
| Spring Angular | 2000 | 强回弹 |
| Rotation Limit | ±5° | |

#### 裙子链

| 位置 | Mass | Move Damping | Rot Damping |
|------|------|-------------|-------------|
| 顶部 (Static) | 1.0 | 0.90 | 0.90 |
| 中间 (Dynamic) | 0.3→0.1 | 0.90→0.995 | 0.90→0.995 |
| 底部 (Dynamic) | 0.1→0.01 | 0.995 | 0.995 |

### 2.4 关节参数

#### 头发关节

| 轴 | 保守 | 飘逸 |
|---|------|------|
| X (前后) | ±5° | ±30° |
| Y (扭转) | ±3° | ±5° (始终小) |
| Z (左右) | ±5° | ±30° |
| 弹簧 | 0 | 0 |
| 移动限制 | 0,0,0 | 0,0,0 |

**链内梯度**：根部紧，末端松。Y 轴（扭转）始终最小。

#### 裙子垂直关节

| 轴 | 值 | 备注 |
|---|------|------|
| X (前摆) | 0→+15° | 只正方向（不往后穿过身体） |
| Y (扭转) | ±5° | 最小 |
| Z (侧摆) | ±5° | |
| 弹簧旋转 | 0-10 | |

#### 裙子水平关节

| 参数 | 值 |
|------|---|
| 移动限制 | ±0.5（各轴） |
| 旋转 X | ±20° |
| 旋转 Y | ±60° |
| 旋转 Z | ±30°（底部 = 0，防卷曲） |
| 弹簧 | 50-200 |

### 2.5 裏ジョイント（反向关节）

普通关节力只从 A 传到 B。链 5+ 个动态体时，末端碰撞力无法回传到根部导致断裂。

**解决方案**：在同一位置创建第二个关节，A/B 对调，实现双向传力。

适用于：长发垂直链、长裙垂直链。不需要：水平关节（已经环形）、最顶部关节（静态到动态）。

### 2.6 刚体尺寸

| 参数 | 公式 |
|------|------|
| 胶囊高度 | bone_length × 0.8 |
| 胶囊半径 | max(0.2, 顶点包围盒宽度 × 0.5) |
| 身体碰撞半径 | 略大于实际 mesh（宁可悬浮不穿模） |
| 最小功能尺寸 | ~0.1（更小会飞出去） |

---

## 三、现有代码分析

### 3.1 xps_to_mmd/operators/physics_operator.py

已实现 3 个 operator：

| Operator | 功能 | 状态 |
|----------|------|------|
| generate_body_rigid_bodies | 20 个静态碰撞胶囊（脊柱/头/四肢） | 完成 |
| generate_hair_physics | 动态链检测（关键词匹配）+ 梯度参数 | 完成 |
| generate_breast_physics | 球形 Dynamic+Bone + 弹簧关节 | 完成 |

**缺失**：裙子/衣物物理。

### 3.2 bl/scripts/clone_physics.py

Tier 1 方案：从 target PMX 克隆物理。

- 骨骼本地坐标存储（解决跨模型比例差异）
- 骨长比例缩放
- JSON 模板提取/应用

### 3.3 Convert_to_MMD_claude 三层架构

| Tier | 方法 | 适用场景 |
|------|------|---------|
| 1 | Clone from target PMX | 有 target 时最优（100% 精度） |
| 2 | Template JSON | 有预设时 |
| 3 | Auto-chain generation | 无 target 无预设时 |

---

## 四、设计方案

### 4.1 目标

增强现有 physics_operator.py：
1. 优化参数对齐 MMD 最佳实践
2. 新增裙子/衣物物理检测和生成
3. 保持通用性（先 Inase 通过，标记 TODO(generalize)）

### 4.2 实现计划

#### Phase 1: 优化现有 operator 参数（本次实现）

对齐 body/hair/breast 参数到调研结果的最佳实践值。

#### Phase 2: 新增衣物链检测（本次实现）

检测逻辑：
1. 遍历所有未被 body/hair/breast 覆盖的骨链
2. 按位置和 parent 关系分类（下半身子骨且非腿 = 裙子候选）
3. 生成级联刚体 + 垂直/水平关节

```python
# TODO(generalize): 裙子检测目前基于 parent=下半身 + 位置，
# 不同 XPS 模型裙子骨命名不同，可能需要更多启发式
```

#### Phase 3: 验证

1. 生成后 `build_rig()` 激活物理
2. 播放动画检查头发/胸部自然晃动
3. 检查碰撞组正确（不穿模）
4. 对比 target（如有）的刚体数量

### 4.3 不实现的部分

- 裏ジョイント（反向关节）——当前链长度不需要
- 多层物理——复杂度过高
- 衣物材质预设系统（PmxTailor 级别）——未来重构

---

## 五、参考来源

### 日文社区
- Oomary's Guide to Hair Physics (LearnMMD)
- RGBA Blog: 曲面自動設定 / 胸部物理
- 柔軟剤プラグイン Guide (ニコニコ)
- MMD Tips: 剛体設定 / 関節設定 (ニコニコブロマガ)

### 工具
- PmxTailor (miu200521358) — 最流行的自动物理工具
- 曲面自動設定プラグイン (くろら) — 42,675+ downloads
- 柔軟剤プラグイン — 简单一键物理
- BoneX (oimoyu) — Blender PhysX 方案

### 代码参考
- Convert_to_MMD_claude/operators/physics_operator.py — Tier 1/3
- bl/scripts/clone_physics.py — 物理克隆/模板
- mmd_tools/core/model.py — createRigidBody/createJoint API

### PMX 规范
- PMX v2.0/2.1 File Format Specification
- mmd_tools core/rigid_body.py 常量定义
