#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LHandPro 手指位置安全范围测试程序

功能：
- 单独控制每个手指，测试安全位置范围
- 可视化显示手指位置关系
- 检测潜在碰撞风险
- 记录安全位置范围
"""

import sys
import time
import keyboard
from typing import List, Dict, Tuple
from lhandpro_controller import LHandProController


class FingerRangeTester:
    """手指安全范围测试器"""

    def __init__(self, controller: LHandProController, dof_active: int):
        self.controller = controller
        self.dof_active = dof_active

        # 手指定义（根据实际自由度调整）
        self.fingers = {
            0: {"name": "拇指", "min_safe": 0, "max_safe": 10000, "collision_with": [1]},
            1: {"name": "食指", "min_safe": 0, "max_safe": 10000, "collision_with": [0]},
            2: {"name": "中指", "min_safe": 0, "max_safe": 10000, "collision_with": []},
            3: {"name": "无名指", "min_safe": 0, "max_safe": 10000, "collision_with": []},
            4: {"name": "小指", "min_safe": 0, "max_safe": 10000, "collision_with": []},
            5: {"name": "拇指旋转", "min_safe": 0, "max_safe": 10000, "collision_with": []},
        }

        # 当前位置
        self.current_positions = [0] * dof_active

        # 安全范围记录
        self.safe_ranges = {}

    def print_menu(self):
        """打印主菜单"""
        print("\n" + "=" * 70)
        print("手指位置安全范围测试程序")
        print("=" * 70)
        print("【测试模式】")
        print("  1. 单指测试 - 单独移动每个手指，观察碰撞")
        print("  2. 对指测试 - 测试拇指与食指的协调运动")
        print("  3. 全手张开/闭合 - 测试整体运动")
        print("  4. 自定义位置 - 输入特定位置值测试")
        print("  5. 连续扫描 - 自动扫描所有手指的安全范围")
        print("  6. 显示当前安全范围记录")
        print("  0. 退出")
        print("-" * 70)
        print("操作提示：")
        print("  - 使用数字键选择模式")
        print("  - 测试过程中按 'Q' 停止当前测试")
        print("  - 发现碰撞时立即按空格键记录当前位置")
        print("=" * 70)

    def get_current_positions(self) -> List[int]:
        """获取当前所有手指位置"""
        positions = []
        for i in range(1, self.dof_active + 1):
            try:
                pos = self.controller.lhp.get_now_position(i)
                positions.append(pos)
            except:
                positions.append(0)
        return positions

    def move_single_finger(self, finger_idx: int, target_pos: int, velocity: int = 3000):
        """移动单个手指"""
        if finger_idx >= self.dof_active:
            print(f"错误：手指索引 {finger_idx} 超出范围")
            return False

        # 构建位置列表
        positions = self.current_positions.copy()
        positions[finger_idx] = max(0, min(10000, target_pos))

        success = self.controller.move_to_positions(
            positions=positions,
            velocity=velocity,
            max_current=500,
            wait_time=0.5
        )

        if success:
            self.current_positions = positions
            actual_pos = self.get_current_positions()
            print(
                f"  {self.fingers[finger_idx]['name']}: 目标={positions[finger_idx]}, 实际={actual_pos[finger_idx] if finger_idx < len(actual_pos) else 'N/A'}")

        return success

    def test_single_finger(self):
        """单指测试模式"""
        print("\n【单指测试模式】")
        print("选择要测试的手指：")

        for i in range(self.dof_active):
            name = self.fingers.get(i, {}).get('name', f'关节{i}')
            print(f"  {i}. {name}")

        try:
            choice = input("\n输入手指编号 (0-{}): ".format(self.dof_active - 1))
            finger_idx = int(choice)
            if finger_idx < 0 or finger_idx >= self.dof_active:
                print("无效选择")
                return
        except ValueError:
            print("请输入数字")
            return

        finger_name = self.fingers.get(finger_idx, {}).get('name', f'关节{finger_idx}')
        print(f"\n测试 {finger_name} (索引 {finger_idx})")
        print("操作：")
        print("  [↑/W] 增加位置 (+500)")
        print("  [↓/S] 减少位置 (-500)")
        print("  [A] 自动从0扫描到10000")
        print("  [空格] 记录当前位置为安全/碰撞边界")
        print("  [Q] 退出单指测试")

        step = 500
        auto_scan = False
        scan_direction = 1

        while True:
            if keyboard.is_pressed('q'):
                print("\n退出单指测试")
                break

            if keyboard.is_pressed('space'):
                current = self.current_positions[finger_idx]
                print(f"\n  [记录] {finger_name} 当前位置: {current}")
                print("  输入备注 (safe/collision/none): ", end="")
                note = input().strip().lower()
                if note in ['safe', 'collision']:
                    self.safe_ranges[finger_idx] = {
                        'position': current,
                        'type': note,
                        'finger': finger_name
                    }
                    print(f"  已记录: {finger_name}@{current} = {note}")
                time.sleep(0.3)  # 防抖

            if keyboard.is_pressed('a'):
                auto_scan = not auto_scan
                print(f"\n  自动扫描: {'开启' if auto_scan else '关闭'}")
                time.sleep(0.3)

            if auto_scan:
                # 自动扫描
                new_pos = self.current_positions[finger_idx] + (step * scan_direction)
                if new_pos > 10000:
                    new_pos = 10000
                    scan_direction = -1
                elif new_pos < 0:
                    new_pos = 0
                    scan_direction = 1
                    auto_scan = False
                    print("  扫描完成")

                self.move_single_finger(finger_idx, new_pos)
                time.sleep(0.1)
            else:
                # 手动控制
                if keyboard.is_pressed('up') or keyboard.is_pressed('w'):
                    new_pos = min(10000, self.current_positions[finger_idx] + step)
                    self.move_single_finger(finger_idx, new_pos)
                    time.sleep(0.2)

                elif keyboard.is_pressed('down') or keyboard.is_pressed('s'):
                    new_pos = max(0, self.current_positions[finger_idx] - step)
                    self.move_single_finger(finger_idx, new_pos)
                    time.sleep(0.2)

    def test_thumb_index_coordination(self):
        """拇指与食指协调测试（最容易碰撞的组合）"""
        print("\n【拇指-食指协调测试】")
        print("此测试用于确定拇指和食指的安全运动范围")
        print("操作：")
        print("  [1] 固定拇指，移动食指")
        print("  [2] 固定食指，移动拇指")
        print("  [3] 对指运动（捏合）")
        print("  [Q] 退出")

        if self.dof_active < 2:
            print("错误：自由度不足，无法测试")
            return

        mode = '1'

        while True:
            if keyboard.is_pressed('q'):
                break

            if keyboard.is_pressed('1'):
                mode = '1'
                print("\n模式: 固定拇指，移动食指")
                time.sleep(0.3)
            elif keyboard.is_pressed('2'):
                mode = '2'
                print("\n模式: 固定食指，移动拇指")
                time.sleep(0.3)
            elif keyboard.is_pressed('3'):
                mode = '3'
                print("\n模式: 对指运动")
                time.sleep(0.3)

            # 显示当前位置
            positions = self.get_current_positions()
            thumb_pos = positions[0] if len(positions) > 0 else 0
            index_pos = positions[1] if len(positions) > 1 else 0
            gap = abs(thumb_pos - index_pos)

            print(f"\r拇指: {thumb_pos:5d} | 食指: {index_pos:5d} | 间距: {gap:5d} | 模式: {mode}", end="")

            if mode == '1':
                # 固定拇指在5000，移动食指
                self.move_single_finger(0, 5000)
                if keyboard.is_pressed('up'):
                    self.move_single_finger(1, index_pos + 200)
                    time.sleep(0.1)
                elif keyboard.is_pressed('down'):
                    self.move_single_finger(1, index_pos - 200)
                    time.sleep(0.1)

            elif mode == '2':
                # 固定食指在5000，移动拇指
                self.move_single_finger(1, 5000)
                if keyboard.is_pressed('up'):
                    self.move_single_finger(0, thumb_pos + 200)
                    time.sleep(0.1)
                elif keyboard.is_pressed('down'):
                    self.move_single_finger(0, thumb_pos - 200)
                    time.sleep(0.1)

            elif mode == '3':
                # 对指运动 - 同时向中间移动
                if keyboard.is_pressed('up'):
                    # 捏合
                    self.move_single_finger(0, min(10000, thumb_pos + 200))
                    self.move_single_finger(1, max(0, index_pos - 200))
                    time.sleep(0.1)
                elif keyboard.is_pressed('down'):
                    # 张开
                    self.move_single_finger(0, max(0, thumb_pos - 200))
                    self.move_single_finger(1, min(10000, index_pos + 200))
                    time.sleep(0.1)

            time.sleep(0.05)

        print("\n退出协调测试")

    def test_full_hand(self):
        """全手张开/闭合测试"""
        print("\n【全手张开/闭合测试】")
        print("测试所有手指同时运动，观察协调性")
        print("操作：")
        print("  [空格] 在张开的闭合之间切换")
        print("  [↑] 增加闭合程度")
        print("  [↓] 减少闭合程度")
        print("  [Q] 退出")

        # 定义几种典型姿势
        poses = {
            'open': [0, 0, 0, 0, 0, 0],
            'half': [5000, 5000, 5000, 5000, 5000, 5000],
            'close': [9000, 9000, 9000, 9000, 9000, 9000],
            'pinch': [8000, 8000, 0, 0, 0, 5000],  # 捏合姿势
        }

        current_pose_name = 'open'
        target_positions = poses['open'][:self.dof_active]

        while True:
            if keyboard.is_pressed('q'):
                break

            changed = False

            if keyboard.is_pressed('space'):
                # 切换姿势
                if current_pose_name == 'open':
                    current_pose_name = 'close'
                else:
                    current_pose_name = 'open'
                target_positions = poses[current_pose_name][:self.dof_active]
                print(f"\n切换到姿势: {current_pose_name} -> {target_positions}")
                changed = True
                time.sleep(0.3)

            elif keyboard.is_pressed('1'):
                current_pose_name = 'pinch'
                target_positions = poses['pinch'][:self.dof_active]
                print(f"\n捏合姿势: {target_positions}")
                changed = True
                time.sleep(0.3)

            if changed:
                self.controller.move_to_positions(
                    positions=target_positions,
                    velocity=5000,
                    max_current=500,
                    wait_time=1.0
                )
                self.current_positions = target_positions

            # 显示当前实际位置
            actual = self.get_current_positions()
            print(f"\r当前: {actual} | 目标姿势: {current_pose_name}    ", end="")
            time.sleep(0.1)

        print("\n退出全手测试")

    def custom_position_test(self):
        """自定义位置测试"""
        print("\n【自定义位置测试】")
        print(f"输入{self.dof_active}个位置值（0-10000），用空格分隔")
        print("示例: 5000 3000 0 0 0 0")
        print("输入 'q' 退出")

        while True:
            user_input = input("\n输入位置值: ").strip()

            if user_input.lower() == 'q':
                break

            try:
                positions = [int(x) for x in user_input.split()]

                if len(positions) != self.dof_active:
                    print(f"错误：需要{self.dof_active}个值，提供了{len(positions)}个")
                    continue

                # 限制范围
                positions = [max(0, min(10000, p)) for p in positions]

                print(f"移动到: {positions}")

                success = self.controller.move_to_positions(
                    positions=positions,
                    velocity=3000,
                    max_current=400,
                    wait_time=2.0
                )

                if success:
                    self.current_positions = positions
                    actual = self.get_current_positions()
                    print(f"实际位置: {actual}")

                    # 检查差异
                    diff = [abs(a - b) for a, b in zip(actual, positions)]
                    max_diff = max(diff) if diff else 0
                    if max_diff > 100:
                        print(f"⚠️ 警告：位置偏差较大 (最大{max_diff})")
                else:
                    print("运动失败")

            except ValueError:
                print("输入格式错误，请输入数字")

    def auto_scan_range(self):
        """自动扫描所有手指的安全范围"""
        print("\n【自动扫描安全范围】")
        print("此功能将自动扫描每个手指从0到10000的运动")
        print("观察是否有异常（碰撞、卡顿、异响）")
        print("按空格键记录当前位置，按Q跳过当前手指")

        for finger_idx in range(self.dof_active):
            finger_name = self.fingers.get(finger_idx, {}).get('name', f'关节{finger_idx}')
            print(f"\n--- 扫描 {finger_name} (索引{finger_idx}) ---")

            # 先回到0位置
            self.move_single_finger(finger_idx, 0)
            time.sleep(1.0)

            # 逐步增加到10000
            step = 200
            test_positions = list(range(0, 10001, step))

            for i, pos in enumerate(test_positions):
                if keyboard.is_pressed('q'):
                    print("  跳过")
                    break

                self.move_single_finger(finger_idx, pos)

                # 显示进度条
                progress = (i + 1) / len(test_positions) * 100
                print(f"\r  进度: [{('=' * int(progress // 5)).ljust(20)}] {progress:.1f}% 位置:{pos:5d}", end="")

                # 检测按键记录
                if keyboard.is_pressed('space'):
                    actual = self.get_current_positions()
                    actual_pos = actual[finger_idx] if finger_idx < len(actual) else pos
                    print(f"\n  [记录] {finger_name} 在位置 {actual_pos}")
                    print("  输入备注: ", end="")
                    note = input().strip()
                    if note:
                        key = f"{finger_idx}_{pos}"
                        self.safe_ranges[key] = {
                            'finger': finger_name,
                            'position': actual_pos,
                            'note': note
                        }
                    time.sleep(0.3)

                time.sleep(0.05)

            print()  # 换行

    def show_safe_ranges(self):
        """显示记录的安全范围"""
        print("\n" + "=" * 70)
        print("已记录的安全范围")
        print("=" * 70)

        if not self.safe_ranges:
            print("暂无记录")
            return

        # 按手指分组
        by_finger = {}
        for key, data in self.safe_ranges.items():
            finger = data.get('finger', 'Unknown')
            if finger not in by_finger:
                by_finger[finger] = []
            by_finger[finger].append(data)

        for finger, records in by_finger.items():
            print(f"\n{finger}:")
            for r in sorted(records, key=lambda x: x['position']):
                pos = r['position']
                note = r.get('note', r.get('type', 'unknown'))
                print(f"  位置 {pos:5d}: {note}")

        print("=" * 70)

        # 生成建议配置
        print("\n建议配置（基于记录的安全范围）：")
        for finger_idx in range(self.dof_active):
            finger_name = self.fingers.get(finger_idx, {}).get('name', f'关节{finger_idx}')
            records = [r for r in self.safe_ranges.values() if r.get('finger') == finger_name]

            if records:
                safe_positions = [r['position'] for r in records if
                                  'safe' in r.get('note', '').lower() or r.get('type') == 'safe']
                collision_positions = [r['position'] for r in records if
                                       'collision' in r.get('note', '').lower() or r.get('type') == 'collision']

                min_safe = min(safe_positions) if safe_positions else 0
                max_safe = max(safe_positions) if safe_positions else 10000

                if collision_positions:
                    max_safe = min(collision_positions) - 500  # 留出500余量

                print(f"  {finger_name}: 建议范围 [{min_safe}, {max_safe}]")

    def run(self):
        """运行测试主循环"""
        # 初始位置
        print("回到初始位置（全张开）...")
        self.controller.move_to_positions(
            positions=[0] * self.dof_active,
            velocity=5000,
            max_current=400,
            wait_time=2.0
        )
        self.current_positions = [0] * self.dof_active

        while True:
            self.print_menu()

            try:
                choice = input("\n选择测试模式: ").strip()
            except EOFError:
                break

            if choice == '0' or choice.lower() == 'q':
                print("退出测试程序")
                break
            elif choice == '1':
                self.test_single_finger()
            elif choice == '2':
                self.test_thumb_index_coordination()
            elif choice == '3':
                self.test_full_hand()
            elif choice == '4':
                self.custom_position_test()
            elif choice == '5':
                self.auto_scan_range()
            elif choice == '6':
                self.show_safe_ranges()
            else:
                print("无效选择")


def main():
    print("LHandPro 手指位置安全范围测试程序")
    print("=" * 70)
    print("⚠️ 警告：测试过程中请密切观察机械手运动！")
    print("⚠️ 发现异常立即按Ctrl+C或关闭程序！")
    print("=" * 70)

    with LHandProController(communication_mode="ECAT") as controller:
        try:
            print("\n正在连接EtherCAT设备...")
            connected = controller.connect(
                enable_motors=True,
                home_motors=True,
                home_wait_time=3.0,
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

            # 启动测试器
            tester = FingerRangeTester(controller, dof_active)
            tester.run()

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
                controller.stop_motors()
                print("✅ 电机已停止")

                print("回到零位...")
                controller.home(wait_time=3.0)
                print("✅ 已回零")
            except Exception as e:
                print(f"清理过程出错: {e}")

    print("\n程序执行完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())