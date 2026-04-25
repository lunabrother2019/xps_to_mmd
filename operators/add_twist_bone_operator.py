import bpy
import math
from bpy.props import StringProperty
from mathutils import Vector

class OBJECT_OT_add_twist_bone(bpy.types.Operator):
    """对腕部和手部骨骼进行捩骨骼设置"""
    bl_idname = "object.xps_add_twist_bone"
    bl_label = "添加腕捩骨骼"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # 获取当前选中的骨架对象
        obj = context.active_object
        if obj is None or obj.type != 'ARMATURE':
            self.report({'ERROR'}, "请先选择一个骨架对象")
            return {'CANCELLED'}

        # 切换到编辑模式
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = obj.data.edit_bones

        # 定义腕捩和手捩骨骼的名称
        # 注意：根据JSON数据，需要创建单独的腕捩和手捩骨骼，以及三个细分的捩骨骼
        twist_bones_def = [
            # 左侧
            ("左腕", ["左腕捩", "左腕捩1", "左腕捩2", "左腕捩3"]),
            ("左ひじ", ["左手捩", "左手捩1", "左手捩2", "左手捩3"]),
            # 右侧
            ("右腕", ["右腕捩", "右腕捩1", "右腕捩2", "右腕捩3"]),
            ("右ひじ", ["右手捩", "右手捩1", "右手捩2", "右手捩3"])
        ]

        for bone_name, twist_names in twist_bones_def:
            if bone_name not in edit_bones:
                continue

            # 获取骨骼
            base_bone = edit_bones[bone_name]
            parent_bone = base_bone.parent
            children_bones = [child for child in edit_bones if child.parent == base_bone]

            # 保存原骨骼的位置和方向
            bone_head = base_bone.head
            bone_tail = base_bone.tail
            bone_vector = bone_tail - bone_head
            bone_length = bone_vector.length

            # 创建捩骨骼
            twist_bones = []
            # 先创建所有捩骨骼
            for i, twist_name in enumerate(twist_names):
                # 创建新骨骼
                twist_bone = edit_bones.new(twist_name)
                
                if i == 0:
                    # 第一个骨骼是主要的捩骨骼（如左腕捩）
                    # 位置在原骨骼的中间到尾部之间，参考JSON数据
                    t = 0.6
                    twist_head = bone_head + bone_vector * t
                    twist_tail = bone_head + bone_vector * 1.0
                    twist_bone.head = twist_head
                    twist_bone.tail = twist_tail
                else:
                    # 后三个是细分的捩骨骼（如腕捩1.L、腕捩2.L、腕捩3.L）
                    # 基于原骨骼的方向和长度计算位置，参考JSON数据
                    t = (i) * 0.2  # 0.2, 0.4, 0.6
                    twist_head = bone_head + bone_vector * t
                    # 设置骨骼位置，方向向上（沿Z轴正方向）
                    # 参考JSON数据，向上延伸约0.08单位
                    twist_bone.head = twist_head
                    twist_bone.tail = twist_head + Vector((0, 0, 0.08))
                
                # 设置骨骼方向
                if i == 0:
                    # 主要的捩骨骼（如左腕捩、左手捩）保持原始roll
                    twist_bone.roll = base_bone.roll
                else:
                    # 只有1、2、3对应的捩骨骼需要设置扭转为0
                    twist_bone.roll = 0.0
                
                # 设置为非相连项
                twist_bone.use_connect = False
                
                twist_bones.append(twist_bone)
            
            # 然后创建shadow和dummy骨骼，放到捩2和3之间
            for i, twist_bone in enumerate(twist_bones):
                if i > 0:  # 跳过主要的捩骨骼（如左腕捩）
                    # 计算捩2和3之间的位置，所有shadow和dummy骨骼都放在这里
                    if len(twist_bones) > 3:
                        # 计算捩2和捩3之间的中点
                        twist2_head = twist_bones[2].head
                        twist3_head = twist_bones[3].head
                        shadow_head = (twist2_head + twist3_head) / 2
                    else:
                        # 如果没有捩3，就放在捩2的位置
                        if len(twist_bones) > 2:
                            shadow_head = twist_bones[2].head
                        else:
                            shadow_head = twist_bone.head
                    
                    # 创建shadow骨骼
                    shadow_bone_name = f"_shadow_{twist_bone.name}"
                    shadow_bone = edit_bones.new(shadow_bone_name)
                    shadow_bone.head = shadow_head
                    shadow_bone.tail = shadow_head + Vector((0, 0, 0.08))  # 尾部在头部上方
                    shadow_bone.parent = base_bone
                    shadow_bone.use_connect = False
                    # 只有1、2、3对应的shadow骨骼需要设置扭转为0
                    shadow_bone.roll = 0.0
                    
                    # 创建dummy骨骼，与shadow骨骼位置相同
                    dummy_bone_name = f"_dummy_{twist_bone.name}"
                    dummy_bone = edit_bones.new(dummy_bone_name)
                    dummy_bone.head = shadow_bone.head  # 与shadow骨骼位置相同
                    dummy_bone.tail = shadow_bone.tail  # 与shadow骨骼位置相同
                    # 只有1、2、3对应的dummy骨骼需要设置扭转为0
                    dummy_bone.roll = 0.0
                    
                    # 根据骨骼类型设置正确的父级
                    if "腕捩" in twist_bone.name:
                        # 查找腕捩骨骼作为dummy骨骼的父级
                        main_twist_name = twist_bone.name.replace("1", "").replace("2", "").replace("3", "")
                        if main_twist_name in edit_bones:
                            dummy_bone.parent = edit_bones[main_twist_name]
                        else:
                            dummy_bone.parent = base_bone
                    elif "手捩" in twist_bone.name:
                        # 查找手捩骨骼作为dummy骨骼的父级
                        main_twist_name = twist_bone.name.replace("1", "").replace("2", "").replace("3", "")
                        if main_twist_name in edit_bones:
                            dummy_bone.parent = edit_bones[main_twist_name]
                        else:
                            dummy_bone.parent = base_bone
                    else:
                        dummy_bone.parent = base_bone
                    
                    dummy_bone.use_connect = False

            # 设置骨骼层级，参考JSON数据
            # 所有捩骨骼的父级都是原骨骼
            for twist_bone in twist_bones:
                twist_bone.parent = base_bone
            
            # 将原骨骼的子骨骼移到第一个捩骨骼下（如左腕捩）
            # 这样可以保持与参考JSON数据一致的父子关系
            if twist_bones:
                for child in children_bones:
                    # 保存子骨骼的原始位置
                    original_head = child.head.copy()
                    original_tail = child.tail.copy()
                    
                    # 移动父级
                    child.parent = twist_bones[0]
                    # 设置为非相连项
                    child.use_connect = False
                    
                    # 恢复子骨骼的原始位置
                    child.head = original_head
                    child.tail = original_tail

        # 添加约束
        self.setup_constraints(obj)

        # 不切权重：保留 XPS 原始权重，靠 parent-chain + additional_transform 继承变形
        # 切换回对象模式
        bpy.ops.object.mode_set(mode='OBJECT')
        #仅选择骨架对象
        bpy.context.view_layer.objects.active = obj
        # 对创建的骨骼进行分组，直接调用collection_operator中的操作符
        bpy.ops.object.xps_create_bone_group()
        self.report({'INFO'}, "成功拆分腕捩骨骼并设置权重和约束")
        return {'FINISHED'}
    def setup_constraints(self, obj):
        """为腕捩和手捩骨骼添加约束"""
        # 切换到姿态模式
        bpy.ops.object.mode_set(mode='POSE')
        
        pose_bones = obj.pose.bones
        
        # 锁定腕捩和手捩骨骼的移动以及X和Z轴的旋转
        for bone in pose_bones:
            if "腕捩" in bone.name or "手捩" in bone.name:
                # 锁定移动
                bone.lock_location[0] = True
                bone.lock_location[1] = True
                bone.lock_location[2] = True
                # 锁定X和Z轴的旋转，只允许Y轴旋转
                bone.lock_rotation[0] = True
                bone.lock_rotation[1] = False
                bone.lock_rotation[2] = True
        
        # 为腕捩骨骼添加约束
        for side in ['左', '右']:
            # 腕捩骨骼约束
            for i in range(1, 4):  # 腕捩1, 腕捩2, 腕捩3
                twist_bone_name = f"{side}腕捩{i}"
                if twist_bone_name in pose_bones:
                    twist_bone = pose_bones[twist_bone_name]
                    
                    # 清除现有约束
                    for constraint in twist_bone.constraints:
                        twist_bone.constraints.remove(constraint)
                    
                    # 添加TRANSFORM约束
                    transform_constraint = twist_bone.constraints.new('TRANSFORM')
                    transform_constraint.name = "mmd_additional_rotation"
                    transform_constraint.target = obj
                    transform_constraint.subtarget = f"_shadow_{side}腕捩{i}"
                    transform_constraint.influence = 1.0
                    transform_constraint.use_motion_extrapolate = True
                    # 设置所有者空间为局部空间
                    transform_constraint.owner_space = 'LOCAL'
                    # 设置目标空间为局部空间
                    transform_constraint.target_space = 'LOCAL'
                    # 设置从旋转映射到旋转
                    transform_constraint.map_from = 'ROTATION'
                    transform_constraint.map_to = 'ROTATION'
                    # 设置映射自的模式为XYZ欧拉
                    transform_constraint.from_rotation_mode = 'XYZ'
                    # 设置映射模式为XYZ欧拉
                    transform_constraint.to_euler_order = 'XYZ'
                    # 设置混合选项为初始后
                    transform_constraint.mix_mode_rot = 'AFTER'
                    
                    # 设置旋转范围（将角度转换为弧度）
                    transform_constraint.from_min_x_rot = math.radians(-180.0)
                    transform_constraint.from_min_y_rot = math.radians(-180.0)
                    transform_constraint.from_min_z_rot = math.radians(-180.0)
                    transform_constraint.from_max_x_rot = math.radians(180.0)
                    transform_constraint.from_max_y_rot = math.radians(180.0)
                    transform_constraint.from_max_z_rot = math.radians(180.0)
                    
                    # 根据骨骼索引设置不同的旋转限制（将角度转换为弧度）
                    influence_map = {1: 0.25, 2: 0.5, 3: 0.75}
                    angle = 45.0 * i
                    transform_constraint.to_min_x_rot = math.radians(-angle)
                    transform_constraint.to_min_y_rot = math.radians(-angle)
                    transform_constraint.to_min_z_rot = math.radians(-angle)
                    transform_constraint.to_max_x_rot = math.radians(angle)
                    transform_constraint.to_max_y_rot = math.radians(angle)
                    transform_constraint.to_max_z_rot = math.radians(angle)

                    twist_bone.mmd_bone.has_additional_rotation = True
                    twist_bone.mmd_bone.additional_transform_bone = f"{side}腕捩"
                    twist_bone.mmd_bone.additional_transform_influence = influence_map[i]

            # 为手捩骨骼添加约束
            for i in range(1, 4):  # 手捩1, 手捩2, 手捩3
                twist_bone_name = f"{side}手捩{i}"
                if twist_bone_name in pose_bones:
                    twist_bone = pose_bones[twist_bone_name]
                    
                    # 清除现有约束
                    for constraint in twist_bone.constraints:
                        twist_bone.constraints.remove(constraint)
                    
                    # 添加TRANSFORM约束
                    transform_constraint = twist_bone.constraints.new('TRANSFORM')
                    transform_constraint.name = "mmd_additional_rotation"
                    transform_constraint.target = obj
                    transform_constraint.subtarget = f"_shadow_{side}手捩{i}"
                    transform_constraint.influence = 1.0
                    transform_constraint.use_motion_extrapolate = True
                    # 设置所有者空间为局部空间
                    transform_constraint.owner_space = 'LOCAL'
                    # 设置目标空间为局部空间
                    transform_constraint.target_space = 'LOCAL'
                    # 设置从旋转映射到旋转
                    transform_constraint.map_from = 'ROTATION'
                    transform_constraint.map_to = 'ROTATION'
                    # 设置映射自的模式为XYZ欧拉
                    transform_constraint.from_rotation_mode = 'XYZ'
                    # 设置映射模式为XYZ欧拉
                    transform_constraint.to_euler_order = 'XYZ'
                    # 设置混合选项为初始后
                    transform_constraint.mix_mode_rot = 'AFTER'
                    
                    # 设置旋转范围（将角度转换为弧度）
                    transform_constraint.from_min_x_rot = math.radians(-180.0)
                    transform_constraint.from_min_y_rot = math.radians(-180.0)
                    transform_constraint.from_min_z_rot = math.radians(-180.0)
                    transform_constraint.from_max_x_rot = math.radians(180.0)
                    transform_constraint.from_max_y_rot = math.radians(180.0)
                    transform_constraint.from_max_z_rot = math.radians(180.0)
                    
                    # 根据骨骼索引设置不同的旋转限制（将角度转换为弧度）
                    influence_map = {1: 0.25, 2: 0.5, 3: 0.75}
                    angle = 45.0 * i
                    transform_constraint.to_min_x_rot = math.radians(-angle)
                    transform_constraint.to_min_y_rot = math.radians(-angle)
                    transform_constraint.to_min_z_rot = math.radians(-angle)
                    transform_constraint.to_max_x_rot = math.radians(angle)
                    transform_constraint.to_max_y_rot = math.radians(angle)
                    transform_constraint.to_max_z_rot = math.radians(angle)

                    twist_bone.mmd_bone.has_additional_rotation = True
                    twist_bone.mmd_bone.additional_transform_bone = f"{side}手捩"
                    twist_bone.mmd_bone.additional_transform_influence = influence_map[i]

        # 为shadow骨骼添加COPY_TRANSFORMS约束
        for side in ['左', '右']:
            # 腕捩shadow骨骼
            for i in range(1, 4):
                shadow_bone_name = f"_shadow_{side}腕捩{i}"
                if shadow_bone_name in pose_bones:
                    shadow_bone = pose_bones[shadow_bone_name]
                    
                    # 清除现有约束
                    for constraint in shadow_bone.constraints:
                        shadow_bone.constraints.remove(constraint)
                    
                    # 添加COPY_TRANSFORMS约束
                    copy_constraint = shadow_bone.constraints.new('COPY_TRANSFORMS')
                    copy_constraint.name = "mmd_tools_at_dummy"
                    copy_constraint.target = obj
                    copy_constraint.subtarget = f"_dummy_{side}腕捩{i}"
                    copy_constraint.influence = 1.0
                    # 设置为姿态空间
                    copy_constraint.owner_space = 'POSE'
                    copy_constraint.target_space = 'POSE'
            
            # 手捩shadow骨骼
            for i in range(1, 4):
                shadow_bone_name = f"_shadow_{side}手捩{i}"
                if shadow_bone_name in pose_bones:
                    shadow_bone = pose_bones[shadow_bone_name]
                    
                    # 清除现有约束
                    for constraint in shadow_bone.constraints:
                        shadow_bone.constraints.remove(constraint)
                    
                    # 添加COPY_TRANSFORMS约束
                    copy_constraint = shadow_bone.constraints.new('COPY_TRANSFORMS')
                    copy_constraint.name = "mmd_tools_at_dummy"
                    copy_constraint.target = obj
                    copy_constraint.subtarget = f"_dummy_{side}手捩{i}"
                    copy_constraint.influence = 1.0
                    # 设置为姿态空间
                    copy_constraint.owner_space = 'POSE'
                    copy_constraint.target_space = 'POSE'


def register():
    bpy.utils.register_class(OBJECT_OT_add_twist_bone)

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_add_twist_bone)

if __name__ == "__main__":
    register()