import matplotlib
matplotlib.use("TkAgg")

import nidaqmx
import time
import numpy as np
import matplotlib.pyplot as plt
from collections import deque
from nidaqmx.constants import TerminalConfiguration

DEV = "Dev3"
AI_CH = f"{DEV}/ai0"
AO_CH = f"{DEV}/ao0"

AI_MIN, AI_MAX = -10.0, 10.0
AO_MIN, AO_MAX = -10.0, 10.0

# =====================
# 제어 파라미터
# =====================
kp = 0.7

# =====================
# 노이즈 설정 (외란)
# =====================
NOISE_STD = 0.02   # V

# =====================
# 기준 파형 설정
# =====================
MODE = "sine"   # "step" or "sine"

STEP_VALUE = 0.5

SINE_FREQ = 0.5   # Hz
SINE_AMP = 0.5

# =====================
# 그래프
# =====================
WINDOW = 200

in_buf = deque([0]*WINDOW, maxlen=WINDOW)
out_buf = deque([0]*WINDOW, maxlen=WINDOW)
ref_buf = deque([0]*WINDOW, maxlen=WINDOW)

plt.ion()
fig, ax = plt.subplots(figsize=(10,5))

line_ref, = ax.plot(ref_buf, label="Reference", linewidth=2)
line_in, = ax.plot(in_buf, label="Input (AI + noise)")
line_out, = ax.plot(out_buf, label="Output (AO)", linestyle="--")

ax.set_ylim(-1.2, 1.2)
ax.legend()
ax.set_title("Real-time DAQ Control with Disturbance")

print("실행 중...")

t0 = time.time()

try:
    with nidaqmx.Task() as ai, nidaqmx.Task() as ao:

        ai.ai_channels.add_ai_voltage_chan(
            AI_CH,
            terminal_config=TerminalConfiguration.RSE,
            min_val=AI_MIN,
            max_val=AI_MAX
        )

        ao.ao_channels.add_ao_voltage_chan(
            AO_CH,
            min_val=AO_MIN,
            max_val=AO_MAX
        )

        while True:
            t = time.time() - t0

            # =====================
            # 기준 생성
            # =====================
            if MODE == "step":
                if t < 2:
                    setpoint = 0.0
                else:
                    setpoint = STEP_VALUE

            elif MODE == "sine":
                setpoint = SINE_AMP * np.sin(2*np.pi*SINE_FREQ*t)

            # =====================
            # 입력 읽기
            # =====================
            sensor = ai.read()

            # ===== noise 추가 =====
            noise = np.random.normal(0.5, NOISE_STD)
            sensor_noisy = sensor + noise

            # =====================
            # P 제어
            # =====================
            error = setpoint - sensor_noisy
            output = sensor_noisy + kp * error

            # 제한
            output = max(min(output, AO_MAX), AO_MIN)

            # =====================
            # 출력
            # =====================
            ao.write(output)

            # =====================
            # 버퍼
            # =====================
            ref_buf.append(setpoint)
            in_buf.append(sensor_noisy)
            out_buf.append(output)

            # =====================
            # 그래프 업데이트
            # =====================
            line_ref.set_ydata(ref_buf)
            line_in.set_ydata(in_buf)
            line_out.set_ydata(out_buf)

            plt.pause(0.001)

            time.sleep(0.02)

except KeyboardInterrupt:
    print("종료")

finally:
    plt.ioff()
    plt.show()
