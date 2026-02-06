import numpy as np
import matplotlib.pyplot as plt
from DAQ import DAQInterface

FS = 100_000      # 일부러 낮게
N = 5000

daq = DAQInterface(
    device="Dev3",
    ai_channel="ai0",
    fs=FS,
    ai_min=-1.0,
    ai_max=1.0
)

x = daq.read(N)

print("평균 전압:", np.mean(x))
print("최소 전압:", np.min(x))
print("최대 전압:", np.max(x))

plt.plot(x)
plt.xlabel("Sample")
plt.ylabel("Voltage [V]")
plt.title("ADC Raw Input")
plt.show()
