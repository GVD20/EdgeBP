import serial
import serial.tools.list_ports
import matplotlib.pyplot as plt
import numpy as np
import time
from matplotlib.animation import FuncAnimation
from collections import deque
import matplotlib
import threading
from scipy import signal

# 设置matplotlib使用中文
matplotlib.rcParams['font.sans-serif'] = ['SimHei']  # 使用黑体
matplotlib.rcParams['axes.unicode_minus'] = False  # 正常显示负号

# 数据存储队列
max_points = 500  # 10秒的数据点 (假设每秒约50个数据点)
time_data = deque(maxlen=max_points)
red_data = deque(maxlen=max_points)
ir_data = deque(maxlen=max_points)
# 添加滤波后的数据队列
red_filtered_data = deque(maxlen=max_points)
ir_filtered_data = deque(maxlen=max_points)

# 串口连接状态
connected = False
serial_port = None

# 创建图形
plt.style.use('ggplot')
fig, ((ax1, ax3), (ax2, ax4)) = plt.subplots(2, 2, figsize=(14, 8))
fig.suptitle('PPG 实时波形监测', fontsize=16)

# 初始化线条对象 - 原始数据
line1, = ax1.plot([], [], 'r-', lw=1.5, alpha=0.7)
line2, = ax2.plot([], [], 'b-', lw=1.5, alpha=0.7)

# 初始化线条对象 - 滤波后数据
line3, = ax3.plot([], [], 'r-', lw=2)
line4, = ax4.plot([], [], 'b-', lw=2)

# 初始化坐标轴标题
ax1.set_title('红光原始波形')
ax1.set_ylabel('信号值')
ax3.set_title('红光滤波后波形')
ax3.set_ylabel('信号值')

ax2.set_title('红外光原始波形')
ax2.set_ylabel('信号值')
ax2.set_xlabel('时间')
ax4.set_title('红外光滤波后波形')
ax4.set_ylabel('信号值')
ax4.set_xlabel('时间')

# 低通滤波器设计
def design_filter():
    # 设计低通滤波器
    # 采样频率(Hz), 根据实际情况可能需要调整
    fs = 50.0
    # 截止频率(Hz), 根据需要过滤的噪声频率调整
    cutoff = 5.0
    # 设置滤波器参数
    nyquist = 0.5 * fs
    normal_cutoff = cutoff / nyquist
    # 创建5阶巴特沃斯低通滤波器
    b, a = signal.butter(5, normal_cutoff, btype='low', analog=False)
    return b, a

# 应用滤波器
def apply_filter(data, b, a):
    if len(data) > 10:  # 确保有足够的数据点
        filtered_data = signal.filtfilt(b, a, list(data))
        return filtered_data
    return list(data)  # 数据不足时返回原始数据

# 获取可用串口列表
def get_serial_ports():
    ports = list(serial.tools.list_ports.comports())
    return ports

# 打印可用端口列表
def print_ports(ports):
    print("可用串口列表:")
    for i, port in enumerate(ports):
        print(f"{i+1}: {port.device} - {port.description}")

# 数据队列锁
data_lock = threading.Lock()

# 更新图形
def update_plot(frame):
    global connected, red_filtered_data, ir_filtered_data
    
    if not connected:
        return line1, line2, line3, line4
    
    with data_lock:
        # 创建数据的副本，避免线程安全问题
        time_data_copy = list(time_data)
        red_data_copy = list(red_data)
        ir_data_copy = list(ir_data)
    
    # 更新X轴范围
    x_data = list(range(len(time_data_copy)))
    
    # 设计滤波器
    b, a = design_filter()
    
    # 应用滤波器
    if len(red_data_copy) > 10:
        try:
            red_filtered = apply_filter(red_data_copy, b, a)
            ir_filtered = apply_filter(ir_data_copy, b, a)
            
            # 确保过滤后的数据长度与x_data匹配
            red_filtered = red_filtered[:len(x_data)]
            ir_filtered = ir_filtered[:len(x_data)]
            
            # 更新滤波后的数据队列
            red_filtered_data = deque(red_filtered, maxlen=max_points)
            ir_filtered_data = deque(ir_filtered, maxlen=max_points)
        except ValueError as e:
            print(f"滤波错误: {e}")
            # 发生错误时使用原始数据
            red_filtered_data = deque(red_data_copy, maxlen=max_points)
            ir_filtered_data = deque(ir_data_copy, maxlen=max_points)
    
    # 更新原始数据线条
    line1.set_data(x_data, red_data_copy)
    line2.set_data(x_data, ir_data_copy)
    
    # 更新滤波后数据线条
    line3.set_data(x_data[:len(red_filtered_data)], list(red_filtered_data))
    line4.set_data(x_data[:len(ir_filtered_data)], list(ir_filtered_data))
    
    # 动态调整Y轴范围 - 原始数据
    if len(red_data_copy) > 0:
        red_min, red_max = min(red_data_copy), max(red_data_copy)
        red_range = red_max - red_min
        if red_range > 0:  # 避免除零问题
            ax1.set_ylim(red_min - red_range * 0.1, red_max + red_range * 0.1)
        ax1.set_xlim(0, len(x_data))
    
    if len(ir_data_copy) > 0:
        ir_min, ir_max = min(ir_data_copy), max(ir_data_copy)
        ir_range = ir_max - ir_min
        if ir_range > 0:  # 避免除零问题
            ax2.set_ylim(ir_min - ir_range * 0.1, ir_max + ir_range * 0.1)
        ax2.set_xlim(0, len(x_data))
    
    # 动态调整Y轴范围 - 滤波后数据
    if len(red_filtered_data) > 0:
        red_f_min, red_f_max = min(red_filtered_data), max(red_filtered_data)
        red_f_range = red_f_max - red_f_min
        if red_f_range > 0:  # 避免除零问题
            ax3.set_ylim(red_f_min - red_f_range * 0.1, red_f_max + red_f_range * 0.1)
        ax3.set_xlim(0, len(x_data))
    
    if len(ir_filtered_data) > 0:
        ir_f_min, ir_f_max = min(ir_filtered_data), max(ir_filtered_data)
        ir_f_range = ir_f_max - ir_f_min
        if ir_f_range > 0:  # 避免除零问题
            ax4.set_ylim(ir_f_min - ir_f_range * 0.1, ir_f_max + ir_f_range * 0.1)
        ax4.set_xlim(0, len(x_data))
    
    return line1, line2, line3, line4

# 读取串口数据的线程
def read_serial():
    global connected, serial_port
    
    while connected:
        try:
            if serial_port.in_waiting:
                line = serial_port.readline().decode('utf-8').strip()
                print(line)
                
                # 解析PPG数据
                if "PPG_RAW" in line:
                    try:
                        parts = line.split(',')
                        if len(parts) >= 4:
                            seq = int(parts[1])
                            red = int(parts[2])
                            ir = int(parts[3])
                            
                            # 将数据添加到队列，使用锁确保线程安全
                            with data_lock:
                                time_data.append(seq)
                                red_data.append(red)
                                ir_data.append(ir)
                    except Exception as e:
                        print(f"解析错误: {e}")
            else:
                # 添加小延迟，避免CPU占用过高
                time.sleep(0.001)
        except Exception as e:
            print(f"读取错误: {e}")
            connected = False
            break

# 主函数
def main():
    global connected, serial_port, red_filtered_data, ir_filtered_data
    
    # 初始化滤波数据队列
    red_filtered_data = deque(maxlen=max_points)
    ir_filtered_data = deque(maxlen=max_points)
    
    # 获取可用串口
    ports = get_serial_ports()
    
    if not ports:
        print("未检测到可用串口！")
        return
    
    print_ports(ports)
    
    # 用户选择串口
    try:
        choice = int(input("请选择串口号码: ")) - 1
        if choice < 0 or choice >= len(ports):
            print("无效的选择！")
            return
        
        port = ports[choice].device
        baudrate = 115200
        
        # 连接串口
        print(f"正在连接到 {port}, 波特率: {baudrate}...")
        serial_port = serial.Serial(port, baudrate, timeout=1)
        connected = True
        
        # 启动读取串口的线程
        read_thread = threading.Thread(target=read_serial)
        read_thread.daemon = True
        read_thread.start()
        
        # 创建动画
        ani = FuncAnimation(fig, update_plot, interval=50, blit=True, 
                           cache_frame_data=False, save_count=100)
        plt.tight_layout()
        plt.show()
        
        # 动画结束后关闭串口
        connected = False
        if serial_port and serial_port.is_open:
            serial_port.close()
            print("串口已关闭")
            
    except Exception as e:
        print(f"发生错误: {e}")
        if serial_port and serial_port.is_open:
            serial_port.close()
            print("串口已关闭")
        connected = False

if __name__ == "__main__":
    main()