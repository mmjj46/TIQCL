from artiq.experiment import *


class DAC_10CH(EnvExperiment):
    """Zotino DAC 10채널 개별 제어 시험용"""

    def build(self):
        self.setattr_device("core")
        self.setattr_device("zotino0")

        # 10개의 채널을 개별적으로 설정 (CH0 ~ CH9)
        for i in range(10):
            arg_name = f"CH{i}_voltage"
            self.setattr_argument(arg_name,
                                  NumberValue(default=0.0,
                                              unit="V",
                                              precision=3,
                                              step=0.01,
                                              min=-10.0,
                                              max=10.0))

    @kernel
    def run(self):
        self.core.reset()
        self.core.break_realtime()

        self.zotino0.init()
        delay(200 * us)

        # 10개 채널에 순차적으로 전압 기록
        for i in range(10):
            voltage = getattr(self, f"CH{i}_voltage")
            self.zotino0.write_dac(i, voltage)

        # 모든 채널 전압을 동시에 하드웨어에 반영
        self.zotino0.load()
        delay(100 * us)