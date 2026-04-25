# 表情 (Morph) 调研报告

> 调研日期: 2026-04-25
> 目标: 为 xps_to_mmd 项目设计 MMD 标准表情系统
> 状态: 调研完成，设计文档完成，实现延后

---

## 一、调研方法

| # | 来源 | 方法 | 关键发现 |
|---|------|------|---------|
| 1 | Convert_to_MMD_claude 代码 | 读 morph_transfer_poc.py + morph_rigs.py | Path A/B/C 全部失败，Path D 成功 |
| 2 | Convert_to_MMD_claude 文档 | 读 morph_path_d_lessons.md 等 | 跨 mesh 传输在唇/眼睑薄层区域不可靠 |
| 3 | mmd_tools API | 读源码 grep morph | shape key = vertex morph，需注册到 mmd_root |
| 4 | PMX 规范 | 互联网调研 | 5 种 morph 类型，4 个面板分类 |
| 5 | MMD 标准表情列表 | 互联网调研 (日文) | 30+ 标准表情，VMD 用日文名匹配 |
| 6 | VRM/ARKit 映射 | 互联网调研 | 标准化表情集可作为泛化参考 |
| 7 | CATS/Copy-to-MMD-Visemes | 互联网调研 | 名字映射工具，shape key 转 morph |

---

## 二、MMD Morph 体系

### 2.1 Morph 类型

| 类型 ID | 名称 | 说明 | Blender 实现 |
|---------|------|------|-------------|
| 0 | Group | 组合多个 morph 到一个滑块 | mmd_tools group morph |
| 1 | Vertex | 顶点位移（经典表情） | Blender shape key |
| 2 | Bone | 骨骼姿态 | mmd_tools bone morph |
| 3 | UV | UV 坐标偏移 | mmd_tools UV morph |
| 8 | Material | 材质属性变化（颜色/透明度） | mmd_tools material morph |

**Vertex morph 是核心**——大多数面部表情都是 vertex morph。

### 2.2 面板分类

| Panel ID | 名称 | 位置 (MikuMikuDance) |
|----------|------|---------------------|
| 1 | 眉 (Eyebrow) | 左下 |
| 2 | 目 (Eye) | 左上 |
| 3 | 口 (Mouth) | 右上 |
| 4 | その他 (Other) | 右下 |

### 2.3 MMD 标准表情完整列表

**口 (Mouth) — Panel 3：**

| 日文 | 罗马字 | 说明 | 优先级 |
|------|--------|------|--------|
| あ | a | 张嘴 | P0 |
| い | i | 咧嘴 | P0 |
| う | u | 嘟嘴 | P0 |
| え | e | "诶" | P0 |
| お | o | 圆嘴 | P0 |
| ん | n | 闭嘴哼 | P1 |
| にやり | niyari | 坏笑 | P1 |
| ▲ | | 三角嘴 | P2 |
| ∧ | | 倒三角 | P2 |
| ω | | 猫嘴 | P2 |
| ぺろっ | pero | 吐舌 | P2 |

**目 (Eye) — Panel 2：**

| 日文 | 罗马字 | 说明 | 优先级 |
|------|--------|------|--------|
| まばたき | mabataki | 双眼闭 | P0 |
| 笑い | warai | 笑眼 | P0 |
| ウィンク | wink | 左眨 | P0 |
| ウィンク右 | wink_R | 右眨 | P0 |
| びっくり | bikkuri | 惊讶（大眼） | P1 |
| じと目 | jitome | 不屑眼 | P1 |
| なごみ | nagomi | 安详 =_= | P2 |
| はぅ | hau | 幸运 >_< | P2 |
| キリッ | kiri | 锐利 | P2 |
| 瞳小 | hitomi_shou | 瞳孔缩小 | P2 |
| 瞳大 | hitomi_dai | 瞳孔放大 | P2 |

**眉 (Eyebrow) — Panel 1：**

| 日文 | 罗马字 | 说明 | 优先级 |
|------|--------|------|--------|
| 真面目 | majime | 严肃（平眉） | P0 |
| 困る | komaru | 困扰（八字眉） | P0 |
| 怒り | ikari | 生气（倒八字） | P0 |
| 上 | ue | 挑眉 | P0 |
| 下 | shita | 压眉 | P1 |
| にこり | nikori | 欢快眉 | P2 |

**その他 (Other) — Panel 4：**

| 日文 | 说明 | 类型 | 优先级 |
|------|------|------|--------|
| 照れ | 脸红 | Material morph | P2 |
| 涙 | 眼泪 | Vertex morph | P2 |

**P0 = 最小可用集 (19 个)**，P1 = 标准扩展，P2 = 完整集。

**关键**：VMD 动作数据用精确的日文名匹配。名字错一个字 morph 就不响应。

### 2.4 Blender 中的实现方式

Vertex morph = Blender shape key：

```python
# 确保 Basis 存在
if mesh.data.shape_keys is None:
    mesh.shape_key_add(name='Basis', from_mix=False)

# 创建 morph
sk = mesh.shape_key_add(name='あ', from_mix=False)
for i, v in enumerate(mesh.data.vertices):
    sk.data[i].co = v.co + offset_vector  # 顶点偏移

# 注册到 mmd_tools
mmd_root = model.rootObject().mmd_root
item = mmd_root.vertex_morphs.add()
item.name = 'あ'
item.category = 'MOUTH'  # 'EYE', 'EYEBROW', 'OTHER'
```

---

## 三、Path A/B/C/D 方案对比

### 为什么 Path D 是唯一可行方案

| 方案 | 方法 | 结果 | 失败原因 |
|------|------|------|---------|
| Path A | TPS + IDW + Jacobian 跨 mesh 传输 | 失败 | 上唇偏移被鼻区域稀释→嘟嘴而非张嘴 |
| Path B | KDTree 近邻传输 | 失败 | 源/目标 頭 骨位置不同→坐标反转 |
| Path C | XPS 原生骨骼配方 | 失败 | XPS rig 太简单（每眼只有 1 根眼睑骨） |
| **Path D** | **按 VG 语义槽位程序化合成** | **成功 19/19** | — |

### Path D 核心设计

**不做跨 mesh 传输**。每个 morph 用源 mesh 自己的 VG 作为 mask，施加预定义偏移量。

```python
# 语义槽位（通用）
UNIVERSAL_RECIPES = {
    'あ': {
        'jaw': (0, 1, -3),           # mm 单位偏移
        'lip.lower.*': (0, 2, -5),   # 通配符展开 L/M/R
        'lip.upper.*': (0, 0, 0.5),
    },
}

# Rig 映射（per-model）
XPS_INASE_MAP = {
    'lip.upper.L': ['head lip upper left'],
    'lip.lower.M': ['head lip lower middle'],
    'jaw': ['head jaw'],
    # ... 20+ 槽位
}
```

**为什么有效**：
- VG 是零污染 mask（不在 VG 里的顶点偏移量 = 0）
- 不需要跨 mesh 几何对应
- 对薄层高密度区域（唇/眼睑）鲁棒
- 任何有面部 VG 的模型都能用

**代价**：每种新 rig 格式需要写一套 rig_map（~20 个槽位映射）。Recipe（偏移量配方）是通用的。

### Mesh 角色分配

不同 mesh 应用不同子集的 morph：

| Mesh 角色 | 应用的 morph | 检测方法 |
|----------|------------|---------|
| primary_face | 全部 19 个 | 包含 lip/eyelid VG |
| eyelashes | 眼相关（まばたき 等） | 包含 eyelash VG |
| eyebrow | 眉相关（困る/怒り 等） | 包含 eyebrow VG |
| eyeball | 眼球后退辅助 | 包含 eyeball VG |

### 眼球后退 (Eyeball Recede)

**发现**：下眼睑闭合时无法物理覆盖眼球（眼球底部比眼睑低 3.2mm）。
**解决**：闭眼 morph 同时让眼球 Y+6mm 后退到眼窝内。

---

## 四、设计方案

### 4.1 架构

```
morph_operator.py (新文件)
├── OBJECT_OT_generate_morphs        — 一键生成 19 个标准 morph
├── detect_rig(mesh)                  — 自动检测 rig 类型
├── bake_programmatic_morph(...)      — 核心: VG mask + offset → shape key
├── bake_eyeball_recede(...)          — 眼球后退辅助
└── MORPH_RECIPES                     — 通用配方（19 个）

morph_rigs.py (新文件)
├── XPS_INASE_MAP                     — Inase VG 槽位映射
├── DAZ_G8_MAP                        — DAZ Genesis 8 映射
└── detect_rig_type(mesh)             — 从 VG 特征自动检测
```

### 4.2 实现计划

1. **从 Convert_to_MMD_claude 移植** morph_transfer_poc.py 核心逻辑
2. **适配 xps_to_mmd pipeline** — 在 step 5 (mmd_tools_convert) 之后执行
3. **注册到 mmd_root** — 设置正确的 category
4. **UI 按钮** — 放在面板的通用工具区域
5. **验证** — PMX 导出 → reimport → VMD 播放检查表情响应

### 4.3 通用性标记

```python
# TODO(generalize): rig_map 目前只有 XPS_INASE 和 DAZ_G8
# 新增 rig 格式需要：
# 1. 添加 VG 特征签名到 detect_rig()
# 2. 写一套 20+ 槽位的 VG 映射
# Recipe（偏移量配方）是通用的，不需要改
```

### 4.4 不实现的部分（明天继续）

- Material morph（照れ 脸红等）
- Bone morph
- Group morph
- 非标准表情（▲/ω/ぺろっ 等 P2 级别）
- 眼球后退的侧向过滤（只闭单眼时只后退对应侧）

---

## 五、Path D 踩坑教训

1. **数据匹配 ≠ 视觉匹配**——max offset 12mm + 方向正确 ≠ 视觉正确。必须截图对比。
2. **跨 mesh 传输在薄层高密度区域根本不可靠**——唇/眼睑相邻顶点法线微差导致 bind 到不同源区域→撕裂。
3. **先探测源模型能力**——检查源 mesh 是否有 >= 10 个语义 VG 再尝试 recipe。
4. **滑块漂移**——测试 morph A 忘了复位，测 morph B 看到 A+B 叠加。需要 `set_morph_synced()` 先清零。
5. **模板选择**——Target PMX 可能用 bone_morph 而非 vertex_morph（Purifier Inase 的 'あ' 只有 7.5mm 颌旋转）。

---

## 六、参考来源

### 代码参考
- Convert_to_MMD_claude/experimental/morph_transfer_poc.py — Path D 完整实现
- Convert_to_MMD_claude/experimental/morph_rigs.py — Rig 映射
- mmd_tools/core/morph.py — FnMorph 类
- Copy-to-MMD-Visemes — shape key 名字映射插件

### 文档
- Convert_to_MMD_claude/doc/morph_path_d_lessons.md — Path D 胜出分析
- Convert_to_MMD_claude/doc/morph_post_mortem_2026_04_18.md — A/B/C 失败分析
- Convert_to_MMD_claude/doc/morph_generalization_architecture.md — 泛化架构

### 互联网
- PMXEditor Expression Names (Elinital, DeviantArt)
- MMD Facial Expressions Chart V2 (Inochi-PM, DeviantArt)
- PMX v2.0/2.1 Morph Format Specification
- mmd_tools Morph Creation Tutorial (powroupi wiki)
- CATS Blender Plugin morph handling
