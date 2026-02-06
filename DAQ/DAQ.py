import nidaqmx
import numpy as np
from nidaqmx.constants import AcquisitionType


class DAQInterface:
    def __init__(
        self,
        device="Dev3",
        ai_channel="ai0",
        ao_channel="ao0",
        fs=1_000_000,
        ai_min=-10.0,
        ai_max=10.0
    ):
        self.device = device
        self.ai_channel = f"{device}/{ai_channel}"
        self.ao_channel = f"{device}/{ao_channel}"
        self.fs = fs
        self.ai_min = ai_min
        self.ai_max = ai_max

    def read(self, n_samples: int):
        with nidaqmx.Task() as task:
            task.ai_channels.add_ai_voltage_chan(
                self.ai_channel,
                min_val=self.ai_min,
                max_val=self.ai_max
            )

            task.timing.cfg_samp_clk_timing(
                rate=self.fs,
                sample_mode=AcquisitionType.FINITE,
                samps_per_chan=n_samples
            )

            data = task.read(
                number_of_samples_per_channel=n_samples,
                timeout=10.0
            )

        return np.array(data)

    def write(self, voltage: float):
        voltage = max(min(voltage, 0.1), -0.1)  # ±0.1 V 제한
        with nidaqmx.Task() as task:
            task.ao_channels.add_ao_voltage_chan(
                self.ao_channel,
                min_val=-10.0,
                max_val=10.0
            )
            task.write(voltage)

