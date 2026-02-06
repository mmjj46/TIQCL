import nidaqmx
from nidaqmx.constants import TerminalConfiguration
import numpy as np
import time
import matplotlib.pyplot as plt
from scipy.fft import fft, fftfreq

# =========================
# 기본 설정
# =========================
DEV = "Dev3"
AI_CH = f"{DEV}/ai0"
AO_CH = f"{DEV}/ao0"

AI_MIN, AI_MAX = -1.0, 1.0
AO_MIN, AO_MAX = -1.0, 1.0


# =========================
# 0. AO → AI 루프백 단일 테스트
# =========================
def loopback_test(voltage=0.4):
    print("\n=== [0] AO → AI 루프백 테스트 ===")

    with nidaqmx.Task() as ao:
        ao.ao_channels.add_ao_voltage_chan(
            AO_CH,
            min_val=AO_MIN,
            max_val=AO_MAX
        )
        ao.write(voltage)

    time.sleep(0.1)

    with nidaqmx.Task() as ai:
        ai.ai_channels.add_ai_voltage_chan(
            AI_CH,
            terminal_config=TerminalConfiguration.RSE,
            min_val=AI_MIN,
            max_val=AI_MAX
        )
        val = ai.read()

    print(f"AO 출력: {voltage:.3f} V | AI 입력: {val:.3f} V")
    return val


# =========================
# 1. DC 제어 루프 (P 제어)
# =========================
def dc_control_loop(setpoint=0.5, kp=0.6, loops=10, delay=0.3):
    print("\n=== [1] DC 제어 루프 (P 제어) ===")
    print(f"Setpoint={setpoint}, Kp={kp}")

    history = []

    for i in range(loops):
        # ADC
        with nidaqmx.Task() as ai:
            ai.ai_channels.add_ai_voltage_chan(
                AI_CH,
                terminal_config=TerminalConfiguration.RSE,
                min_val=AI_MIN,
                max_val=AI_MAX
            )
            sensor = ai.read()

        # 제어 연산 (FPGA 역할)
        error = setpoint - sensor
        output = sensor + kp * error

        # DAC
        with nidaqmx.Task() as ao:
            ao.ao_channels.add_ao_voltage_chan(
                AO_CH,
                min_val=AO_MIN,
                max_val=AO_MAX
            )
            ao.write(output)

        history.append((i, sensor, output))

        print(
            f"Loop {i+1:02d} | "
            f"Sensor={sensor:+.4f} V | "
            f"Error={error:+.4f} V | "
            f"Output={output:+.4f} V"
        )

        time.sleep(delay)

    return history


# =========================
# 2. 사인파 추종 (논리 검증용)
# =========================
def sine_tracking_test(freq=2.0, amp=0.4, duration=2.0):
    print("\n=== [2] 사인파 추종 테스트 (논리 시뮬) ===")

    t = np.linspace(0, duration, int(duration * 100))
    target = amp * np.sin(2 * np.pi * freq * t)

    out_log = []

    for i, ref in enumerate(target):
        # 실제 환경에서는 AI에서 읽힘
        sensor = 0.9 * ref + np.random.normal(0, 0.01)

        # 단순 추종 제어
        output = 1.1 * sensor

        out_log.append((ref, sensor, output))

        print(
            f"t={i:03d} | "
            f"Target={ref:+.3f} V | "
            f"Sensor={sensor:+.3f} V | "
            f"Output={output:+.3f} V"
        )

        time.sleep(0.01)

    return out_log


# =========================
# 3. FFT 주파수 분석 (푸리에 변환)
# =========================
def fft_test(fs=10000, samples=5000):
    print("\n=== [3] FFT 주파수 분석 ===")

    with nidaqmx.Task() as ai:
        ai.ai_channels.add_ai_voltage_chan(
            AI_CH,
            terminal_config=TerminalConfiguration.RSE,
            min_val=AI_MIN,
            max_val=AI_MAX
        )
        ai.timing.cfg_samp_clk_timing(
            rate=fs,
            sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
            samps_per_chan=samples
        )

        x = np.array(ai.read(number_of_samples_per_channel=samples))

    # FFT
    yf = fft(x)
    xf = fftfreq(len(x), 1 / fs)

    peak_freq = xf[np.argmax(np.abs(yf[:len(yf)//2]))]

    print(f"검출된 주요 주파수: {peak_freq:.2f} Hz")

    # Plot
    plt.figure(figsize=(10, 6))

    plt.subplot(2, 1, 1)
    plt.plot(x)
    plt.title("Time Domain")
    plt.ylabel("Voltage [V]")

    plt.subplot(2, 1, 2)
    plt.plot(xf[:len(x)//2], np.abs(yf[:len(yf)//2]))
    plt.title("Frequency Domain (FFT)")
    plt.xlabel("Frequency [Hz]")
    plt.ylabel("Magnitude")

    plt.tight_layout()
    plt.show()

    return peak_freq


# =========================
# 메인 실행 순서
# =========================
if __name__ == "__main__":

    # 0. 루프백 확인
    loopback_test(0.4)

    # 1. DC 제어 루프
    dc_control_loop(
        setpoint=0.5,
        kp=0.6,
        loops=10,
        delay=0.3
    )

    # 2. 사인파 추종 (논리 검증)
    sine_tracking_test(
        freq=2.0,
        amp=0.4,
        duration=2.0
    )

    # 3. FFT (사인파 입력 상태에서 실행)
    fft_test(
        fs=10000,
        samples=5000
    )
"""
연속적인 물리 신호(analog)를 이산적인 sample (ADC)로 보고 디지털 연산을 거쳐 DAC로 다시 검증
1. DC 제어 루프: 원하는 상태와 현재 상태의 차이를 보정 (Hz 성능) 
2. 사인파 추종: 시간에 따라 계속 변하는 압력을 시스템이 잘 따라가는지, 시간 응답 (특정 주파수 성능)
3. 푸리에 변환: 주파수 한계를 확인, 전체 시스템의 주파수가 알맞게 변환되었는지..?
"""

