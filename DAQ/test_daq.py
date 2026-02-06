import nidaqmx
from nidaqmx.constants import TerminalConfiguration

dev = "Dev3"

print("=== 루프백 테스트 (AO0 → AI0) ===")

# 1. AO0에 0.3V 출력
with nidaqmx.Task() as ao:
    ao.ao_channels.add_ao_voltage_chan(f"{dev}/ao0", min_val=-1.0, max_val=1.0)
    ao.write(0.3)
    print("AO0 = 0.3V 출력 완료")
    input("AI0 연결 확인 후 Enter...")

# 2. AI0 읽기
with nidaqmx.Task() as ai:
    ai.ai_channels.add_ai_voltage_chan(
        f"{dev}/ai0",
        terminal_config=TerminalConfiguration.RSE,  # 단일 끝단
        min_val=-1.0, max_val=1.0
    )
    value = ai.read()  # 단일 값 = float
    print(f"AI0 읽음: {value:.3f} V")  # value[0] → value

if abs(value - 0.3) < 0.05:
    print("루프백 성공!")
else:
    print(f"예상 0.3V, 실제 {value:.3f}V. 연결 확인")

"""
1. AI 0 - AO 0을 BNC 선으로 연결한 경우 -> 원하는 전압인 0.3V 출력 완료
2. AI 0 - AO 0을 연결한 선을 해제한 경우 -> 임의 전압 발생 => ADC 작동성 (루프백) 확인 완료
"""
