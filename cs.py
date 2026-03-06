#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LHandPro 抓握矿泉水瓶测试程序（使用位置控制 0-10000）
"""

import sys
import time
import keyboard
from typing import List, Dict
from lhandpro_controller import LHandProController

# 传感器ID枚举
LSS_FINGER_1_1 = 1
LSS_FINGER_1_2 = 2
LSS_FINGER_2_1 = 3
LSS_FINGER_2_2 = 4
LSS_FINGER_3_1 = 5
LSS_FINGER_3_2 = 6
LSS_FINGER_4_1 = 7
LSS_FINGER_4_2 = 8
LSS_FINGER_5_1 = 9
LSS_FINGER_5_2 = 10
LSS_HAND_PALM = 11

# 控制模式枚举
LCM_POSITION = 0
LCM_VELOCITY = 1
LCM_TORQUE = 2


def print_force_data(sensor_data: Dict[int, Dict[str, float]]):
    """格式化打印力感应数据"""
    sensor_names = {
        1: "拇指指尖", 2: "拇指指腹",
        3: "食指指尖", 4: "食指指腹",
        5: "中指指尖", 6: "中指指腹",
        7: "无名指指尖", 8: "无名指指腹",
        9: "小指指尖", 10: "小指指腹",
        11: "手掌"
    }

    if not sensor_data:
        print("暂无传感器数据")
        return

    print("\n┌──────────┬──────────┬──────────┬──────────┬──────────┐")
    print("│  传感器  │ 法向力   │ 切向力   │ 方向(°)  │ 接近度   │")
    print("├──────────┼──────────┼──────────┼──────────┼──────────┤")

    for sensor_id in sorted(sensor_data.keys()):
        name = sensor_names.get(sensor_id, f"未知{sensor_id}")
        data = sensor_data[sensor_id]
        normal = data.get('normal', 0.0)
        tangential = data.get('tangential', 0.0)
        direction = data.get('direction', 0.0)
        proximity = data.get('proximity', 0.0)

        print(f"│ {name:8} │ {normal:8.3f} │ {tangential:8.3f} │ {direction:8.1f} │ {proximity:8.3f} │")

    print("└──────────┴──────────┴──────────┴──────────┴──────────┘")


def get_all_sensor_data(controller) -> Dict[int, Dict[str, float]]:
    """获取所有传感器的数据"""
    sensor_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    data = {}

    for sid in sensor_ids:
        try:
            sensor_data = {}

            try:
                sensor_data['normal'] = controller.lhp.get_finger_normal_force(sid)
            except:
                sensor_data['normal'] = 0.0

            try:
                sensor_data['tangential'] = controller.lhp.get_finger_tangential_force(sid)
            except:
                sensor_data['tangential'] = 0.0

            try:
                sensor_data['direction'] = controller.lhp.get_finger_force_direction(sid)
            except:
                sensor_data['direction'] = 0.0

            try:
                sensor_data['proximity'] = controller.lhp.get_finger_proximity(sid)
            except:
                sensor_data['proximity'] = 0.0

            if any(v != 0.0 for v in sensor_data.values()):
                data[sid] = sensor_data

        except Exception as e:
            pass

    return data


def get_finger_tip_forces(controller) -> Dict[str, float]:
    """获取各手指指尖的力"""
    tip_sensors = {
        '拇指': LSS_FINGER_1_1,
        '食指': LSS_FINGER_2_1,
        '中指': LSS_FINGER_3_1,
        '无名指': LSS_FINGER_4_1,
        '小指': LSS_FINGER_5_1
    }

    forces = {}
    for name, sid in tip_sensors.items():
        try:
            forces[name] = controller.lhp.get_finger_normal_force(sid)
        except:
            forces[name] = 0.0

    return forces


def safe_move(controller, positions: List[int], velocity: int = 5000, max_current: int = 800, wait_time: float = 2.0):
    """
    安全移动：先设置所有参数，再执行运动
    """
    dof = len(positions)

    # 设置控制模式为位置控制
    for i in range(dof):
        motor_id = i + 1
        try:
            controller.lhp.set_control_mode(motor_id, LCM_POSITION)
        except Exception as e:
            print(f"  设置电机{motor_id}控制模式警告: {e}")

    # 设置目标位置
    for i, pos in enumerate(positions):
        motor_id = i + 1
        # 确保位置在有效范围内
        safe_pos = max(0, min(10000, int(pos)))
        try:
            controller.lhp.set_target_position(motor_id, safe_pos)
        except Exception as e:
            print(f"  设置电机{motor_id}位置警告: {e}")

    # 设置速度（使用位置速度）
    for i in range(dof):
        motor_id = i + 1
        try:
            controller.lhp.set_position_velocity(motor_id, velocity)
        except Exception as e:
            print(f"  设置电机{motor_id}速度警告: {e}")

    # 设置电流
    for i in range(dof):
        motor_id = i + 1
        try:
            controller.lhp.set_max_current(motor_id, max_current)
        except Exception as e:
            print(f"  设置电机{motor_id}电流警告: {e}")

    # 执行运动
    try:
        controller.lhp.move_motors(0)
        time.sleep(wait_time)
        return True
    except Exception as e:
        print(f"  运动执行警告: {e}")
        return False


def grasp_sequence(controller: LHandProController, dof_active: int):
    """
    执行抓握矿泉水瓶的完整序列
    使用位置控制（0-10000）
    """

    print("\n" + "=" * 60)
    print("开始抓握序列测试")
    print("=" * 60)

    # 定义抓握位置（0-10000）
    grasp_positions = {




        'open': [0, 0, 0, 0, 0, 0],  # 完全张开
        'pre_grasp': [2000, 3000, 3000, 3000, 3000, 2000],  # 预抓取
        'grasp': [3000, 4000, 4000, 4000, 4000, 4000],  # 闭合抓握
        'tight': [5500, 6000, 6000, 6000, 6000, 4000],  # 紧握
    }

    # 确保位置列表长度匹配自由度
    for key in grasp_positions:
        grasp_positions[key] = grasp_positions[key][:dof_active]

    velocity = 5000  # 位置速度（当量/秒）
    max_current = 800  # 最大电流（千分比）

    # ========== 步骤1: 张开手指 ==========
    print("\n【步骤1/5】张开手指（准备位置）")
    print(f"目标位置: {grasp_positions['open']}")

    success = safe_move(controller, grasp_positions['open'], velocity, max_current, 2.0)
    if not success:
        print("⚠️ 运动可能未完成")

    # 读取实际位置
    actual_positions = []
    for i in range(dof_active):
        try:
            pos = controller.lhp.get_now_position(i + 1)
            actual_positions.append(pos)
        except:
            actual_positions.append(0)

    print(f"实际位置: {actual_positions}")
    print("✅ 已到达准备位置")

    # 等待用户放置瓶子
    print("\n请放置矿泉水瓶到抓取位置...")
    print("按 Enter 键继续，或按 Esc 取消")

    start_time = time.time()
    while True:
        if keyboard.is_pressed('esc'):
            print("\n用户取消操作")
            return False
        if keyboard.is_pressed('enter'):
            break
        if time.time() - start_time > 30:
            print("\n等待超时")
            return False
        time.sleep(0.1)

    # ========== 步骤2: 预抓取 ==========
    print("\n【步骤2/5】预抓取（靠近瓶子）")
    print(f"目标位置: {grasp_positions['pre_grasp']}")

    safe_move(controller, grasp_positions['pre_grasp'], velocity // 2, max_current, 1.5)
    print("✅ 已到达预抓取位置")

    # ========== 步骤3: 闭合抓握 ==========
    print("\n【步骤3/5】闭合抓握")
    print(f"目标位置: {grasp_positions['grasp']}")
    print("正在抓取并实时监测力数据...")

    safe_move(controller, grasp_positions['grasp'], velocity // 2, max_current, 1.0)

    # 实时监测力数据
    print("\n实时力感应数据监测（持续3秒）：")
    start_time = time.time()
    force_history = []

    while time.time() - start_time < 3.0:
        if keyboard.is_pressed('esc'):
            print("\n紧急停止！")
            try:
                controller.lhp.stop_motors(0)
            except:
                pass
            return False

        sensor_data = get_all_sensor_data(controller)
        if sensor_data:
            print_force_data(sensor_data)

        tip_forces = get_finger_tip_forces(controller)
        force_history.append(tip_forces.copy())

        total_force = sum(tip_forces.values())
        print(f"\n指尖总法向力: {total_force:.3f}N | 各指: {tip_forces}")

        if total_force > 2.0:
            print(f"⚡ 抓握有力，接触良好 (总力: {total_force:.3f}N)")

        time.sleep(0.5)

    # ========== 步骤4: 保持抓握 ==========
    print("\n【步骤4/5】保持抓握（最大力度）")
    print(f"目标位置: {grasp_positions['tight']}")

    safe_move(controller, grasp_positions['tight'], velocity // 3, max_current, 1.5)

    print("\n最终抓握力数据：")
    sensor_data = get_all_sensor_data(controller)
    print_force_data(sensor_data)

    if force_history:
        avg_forces = {}
        for finger in force_history[0].keys():
            values = [d[finger] for d in force_history if finger in d]
            if values:
                avg_forces[finger] = sum(values) / len(values)
        print(f"\n抓握过程平均力: {avg_forces}")

    # 保持5秒
    print("\n保持抓握5秒，可以提起瓶子...")
    for i in range(5):
        if keyboard.is_pressed('esc'):
            print("\n紧急停止！")
            try:
                controller.lhp.stop_motors(0)
            except:
                pass
            return False

        tip_forces = get_finger_tip_forces(controller)
        total_force = sum(tip_forces.values())
        print(f"[{5 - i}秒] 总法向力: {total_force:.3f}N")
        time.sleep(1.0)

    # ========== 步骤5: 释放 ==========
    print("\n【步骤5/5】释放瓶子")
    print(f"目标位置: {grasp_positions['open']}")

    safe_move(controller, grasp_positions['open'], velocity, max_current, 2.0)
    print("✅ 已释放瓶子")

    return True


def main():
    print("LHandPro 抓握矿泉水瓶测试程序 (SDK v1.5)")
    print("=" * 60)
    print("使用位置控制（0-10000）")
    print("=" * 60)

    with LHandProController(communication_mode="ECAT") as controller:
        try:
            print("\n正在连接EtherCAT设备...")
            connected = controller.connect(
                enable_motors=True,
                home_motors=True,
                home_wait_time=8.0,
                device_index=6,
                auto_select=False
            )

            if not connected:
                print("❌ 设备连接失败")
                return 1

            print("✅ 设备连接成功")

            dof_total, dof_active = controller.get_dof()
            print(f"\n设备信息:")
            print(f"  - 总共自由度: {dof_total}")
            print(f"  - 主动自由度: {dof_active}")

            # 启用触觉传感器
            try:
                controller.lhp.set_sensor_enable(True)
                print("  - 触觉传感器: 已启用")
            except Exception as e:
                print(f"  - 触觉传感器: 启用失败 ({e})")

            # 设置控制模式
            print("\n设置控制模式...")
            for i in range(1, dof_active + 1):
                try:
                    controller.lhp.set_control_mode(i, LCM_POSITION)
                except Exception as e:
                    print(f"  电机{i}: 设置失败 - {e}")

            # 执行抓握序列
            success = grasp_sequence(controller, dof_active)

            if success:
                print("\n" + "=" * 60)
                print("✅ 抓握测试成功完成")
                print("=" * 60)

        except KeyboardInterrupt:
            print("\n\n程序被用户中断")
        except Exception as e:
            print(f"\n程序运行出错: {e}")
            import traceback
            traceback.print_exc()
            return 1
        finally:
            print("\n清理中...")
            try:
                controller.lhp.stop_motors(0)
                print("✅ 电机已停止")
            except:
                pass

            try:
                print("回到零位...")
                controller.lhp.home_motors(0)
                time.sleep(3.0)
                print("✅ 已回零")
            except Exception as e:
                print(f"回零过程出错: {e}")

    print("\n程序执行完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())