#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CANFD通信库封装
提供扫描、连接、断开、发送以及接收回调功能
使用python-can库实现
"""

import threading
import time
import os
import subprocess
from typing import Optional, Callable, List
import can

# 常量定义
STATUS_OK = 0

# DLC到数据长度的映射
dlc2len = [0, 1, 2, 3, 4, 5, 6, 7, 8, 12, 16, 20, 24, 32, 48, 64]

class CANFDException(Exception):
    """CANFD操作异常"""
    pass


class CANFD:
    """CANFD通信类 - 使用python-can库实现"""
    
    def __init__(self):
        """初始化CANFD实例"""
        # 内部状态
        self._is_connected = False
        self._device_index = 0
        self._channel_index = 0
        self._bus = None
        self._interface = ""
        self._nom_baudrate = 1000000
        self._dat_baudrate = 5000000
        self._receive_thread = None
        self._receive_stop_event = threading.Event()
        self._receive_callback = None
    
    def scan(self) -> int:
        """扫描CANFD设备
        
        Returns:
            int: 找到的设备数量
            
        Raises:
            CANFDException: 扫描失败时抛出
        """
        try:
            # 扫描/sys/class/net目录查找CAN接口
            can_interfaces = []
            if os.path.exists("/sys/class/net"):
                for ifname in os.listdir("/sys/class/net"):
                    if ifname.startswith("can"):
                        can_interfaces.append(ifname)
            return len(can_interfaces)
        except Exception as e:
            raise CANFDException(f"扫描设备异常: {e}")
    
    def _setup_can_interface(self, ifname: str, nom_baudrate: int, dat_baudrate: int) -> bool:
        """设置CAN接口参数
        
        Args:
            ifname: CAN接口名称
            nom_baudrate: 标称波特率
            dat_baudrate: 数据波特率
            
        Returns:
            bool: 设置成功返回True，否则返回False
        """
        try:
            # 重置USB CAN设备
            subprocess.run(["modprobe", "-r", "gs_usb"], capture_output=True)
            subprocess.run(["modprobe", "gs_usb"], capture_output=True)
            subprocess.run(["bash", "-c", "echo 'a8fa 8598' | sudo tee /sys/bus/usb/drivers/gs_usb/new_id"], 
                         capture_output=True)
            
            # 设置CAN接口参数
            subprocess.run(["ip", "link", "set", ifname, "down"], capture_output=True)
            cmd = ["ip", "link", "set", ifname, "type", "can", 
                  "bitrate", str(nom_baudrate),
                  "dbitrate", str(dat_baudrate),
                  "fd", "on",
                  "loopback", "off",
                  "listen-only", "off"]
            subprocess.run(cmd, capture_output=True)
            subprocess.run(["ip", "link", "set", ifname, "up"], capture_output=True)
            return True
        except Exception as e:
            print(f"设置CAN接口失败: {e}")
            return False
    
    def connect(self, device_index: int = 0, channel_index: int = 0,
                nom_baudrate: int = 1000000, dat_baudrate: int = 5000000) -> bool:
        """连接CANFD设备
        
        Args:
            device_index: 设备索引
            channel_index: 通道索引
            nom_baudrate: 标称波特率
            dat_baudrate: 数据波特率
            
        Returns:
            bool: 连接成功返回True，否则返回False
            
        Raises:
            CANFDException: 连接失败时抛出
        """
        try:
            # 保存设备和通道索引
            self._device_index = device_index
            self._channel_index = channel_index
            self._nom_baudrate = nom_baudrate
            self._dat_baudrate = dat_baudrate
            
            # 扫描可用的CAN接口
            can_interfaces = []
            if os.path.exists("/sys/class/net"):
                for ifname in os.listdir("/sys/class/net"):
                    if ifname.startswith("can"):
                        can_interfaces.append(ifname)
            
            if device_index < 0 or device_index >= len(can_interfaces):
                raise CANFDException(f"设备索引无效: {device_index}")
            
            self._interface = can_interfaces[device_index]
            
            # 设置CAN接口参数
            if not self._setup_can_interface(self._interface, nom_baudrate, dat_baudrate):
                raise CANFDException("设置CAN接口失败")
            
            # 使用python-can库创建CAN FD总线
            try:
                # 配置CAN FD总线
                config = {
                    'interface': 'socketcan',
                    'channel': self._interface,
                    'bitrate': nom_baudrate,
                    'fd': True,
                    'can_filters': []
                }
                self._bus = can.Bus(**config)
            except Exception as e:
                raise CANFDException(f"创建CAN FD总线失败: {e}")
            
            # 设置连接状态
            self._is_connected = True
            return True
            
        except Exception as e:
            if self._bus:
                try:
                    self._bus.shutdown()
                except:
                    pass
                self._bus = None
            raise CANFDException(f"连接设备异常: {e}")
    
    def disconnect(self) -> bool:
        """断开CANFD设备连接
        
        Returns:
            bool: 断开成功返回True，否则返回False
            
        Raises:
            CANFDException: 断开失败时抛出
        """
        try:
            if not self._is_connected:
                return True
            
            # 停止接收线程
            if self._receive_thread and self._receive_thread.is_alive():
                self._receive_stop_event.set()
                self._receive_thread.join(timeout=1.0)
            
            # 关闭总线
            if self._bus:
                try:
                    self._bus.shutdown()
                except:
                    pass
                self._bus = None
            
            # 关闭CAN接口
            if self._interface:
                try:
                    subprocess.run(["ip", "link", "set", self._interface, "down"], 
                                 capture_output=True)
                except:
                    pass
            
            # 重置状态
            self._is_connected = False
            self._interface = ""
            self._receive_callback = None
            return True
            
        except Exception as e:
            raise CANFDException(f"断开设备异常: {e}")
    
    def send(self, id: int, data: bytes, frame_type: int = 0x04, extern_flag: int = 0,
             remote_flag: int = 0) -> bool:
        """发送CANFD数据
        
        Args:
            id: 消息ID
            data: 要发送的数据
            frame_type: 帧类型 (默认0x04表示CANFD帧)
            extern_flag: 扩展帧标志 (0: 标准帧, 1: 扩展帧)
            remote_flag: 远程帧标志 (0: 数据帧, 1: 远程帧)
            
        Returns:
            bool: 发送成功返回True，否则返回False
            
        Raises:
            CANFDException: 发送失败时抛出
        """
        try:
            if not self._is_connected:
                raise CANFDException("设备未连接")
            
            # 检查数据长度
            data_len = len(data)
            if data_len > 64:
                raise CANFDException("数据长度不能超过64字节")
            
            # 创建CAN FD消息
            msg = can.Message(
                arbitration_id=id,
                data=data,
                is_extended_id=extern_flag,
                is_remote_frame=remote_flag,
                is_fd=True,
                bitrate_switch=True
            )
            
            # 发送消息
            try:
                self._bus.send(msg)
            except Exception as e:
                raise CANFDException(f"发送数据失败: {e}")
            
            return True
            
        except Exception as e:
            raise CANFDException(f"发送数据异常: {e}")
    
    def set_receive_callback(self, callback: Optional[Callable[[dict], None]]) -> None:
        """设置接收回调函数
        
        Args:
            callback: 接收回调函数，参数为字典格式的CANFD消息
        """
        self._receive_callback = callback
        
        # 如果回调不为None且未启动接收线程，则启动接收线程
        if callback and not (self._receive_thread and self._receive_thread.is_alive()):
            self._start_receive_thread()
    
    def _start_receive_thread(self) -> None:
        """启动接收线程"""
        if not self._is_connected:
            raise CANFDException("设备未连接")
        
        self._receive_stop_event.clear()
        self._receive_thread = threading.Thread(target=self._receive_loop)
        self._receive_thread.daemon = True
        self._receive_thread.start()
    
    def _receive_loop(self) -> None:
        """接收循环线程"""
        try:
            while not self._receive_stop_event.is_set():
                try:
                    # 接收消息
                    msg = self._bus.recv(timeout=0.1)
                    
                    if msg:
                        # 构建消息字典
                        canfd_msg = {
                            "id": msg.arbitration_id,
                            "timestamp": int(msg.timestamp * 1000),
                            "frame_type": 0x04,  # CANFD帧
                            "dlc": next((i for i, val in enumerate(dlc2len) if val == len(msg.data)), 15),
                            "data_len": len(msg.data),
                            "extern_flag": 1 if msg.is_extended_id else 0,
                            "remote_flag": 1 if msg.is_remote_frame else 0,
                            "bus_status": 0,
                            "err_status": 0,
                            "te_counter": 0,
                            "re_counter": 0,
                            "data": msg.data
                        }
                        
                        # 调用回调函数
                        if self._receive_callback:
                            try:
                                self._receive_callback(canfd_msg)
                            except Exception as e:
                                print(f"CANFD接收回调异常: {e}")
                except Exception as e:
                    # 其他错误，短暂休眠后继续
                    time.sleep(0.01)
                
                # 短暂休眠，避免CPU占用过高
                time.sleep(0.001)
                
        except Exception as e:
            print(f"CANFD接收线程异常: {e}")
            # 发生异常时自动断开连接
            if self._is_connected:
                try:
                    self.disconnect()
                except:
                    pass
    
    @property
    def is_connected(self) -> bool:
        """设备是否已连接
        
        Returns:
            bool: 已连接返回True，否则返回False
        """
        return self._is_connected
    
    def __del__(self):
        """析构函数，确保资源释放"""
        try:
            if self._is_connected:
                self.disconnect()
        except:
            pass


# 示例用法
if __name__ == "__main__":
    def receive_callback(msg):
        """接收回调函数示例"""
        print(f"接收到CANFD消息:")
        print(f"  ID: 0x{msg['id']:X}")
        print(f"  数据长度: {msg['data_len']}")
        print(f"  数据: {[hex(b) for b in msg['data']]}")
        print(f"  时间戳: {msg['timestamp']}")
        print(f"  帧类型: {msg['frame_type']}")
    
    try:
        # 创建CANFD实例
        canfd = CANFD()
        
        # 扫描设备
        device_count = canfd.scan()
        print(f"扫描到 {device_count} 个CANFD设备")
        
        if device_count == 0:
            print("未找到CANFD设备")
            exit()
        
        # 连接设备
        print("正在连接CANFD设备...")
        canfd.connect(nom_baudrate=1000000, dat_baudrate=5000000)
        print("CANFD设备连接成功")
        
        # 设置接收回调
        canfd.set_receive_callback(receive_callback)
        
        # 发送测试数据
        print("发送测试数据...")
        test_data = bytes([0x01, 0x06, 0x00, 0x01, 0x00, 0x01, 0x00, 0x01, 0x00, 0x01, 0x00, 0x01, 0x00, 0x01])
        canfd.send(0x500 + 1, test_data)      

        print("测试数据发送成功")
        
        # 保持程序运行
        print("按Ctrl+C退出程序")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n用户中断程序")
    except CANFDException as e:
        print(f"CANFD错误: {e}")
    except Exception as e:
        print(f"其他错误: {e}")
    finally:
        # 确保断开连接
        if 'canfd' in locals() and canfd.is_connected:
            print("正在断开CANFD设备连接...")
            canfd.disconnect()
            print("CANFD设备已断开连接")
