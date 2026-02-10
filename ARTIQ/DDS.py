from artiq.experiment import *


class DDS_raman(EnvExperiment):
    """DDS module raman control_AODver"""

    def build(self):  # This code runs on the host device

        self.setattr_device("core")  # sets core device drivers as attributes

        self.setattr_device("urukul1_ch0")  # RSB
        self.setattr_device("urukul1_ch1")  # BSB
        self.setattr_device("urukul1_ch2")  # AOD1
        self.setattr_device("urukul1_ch3")  # AOD2

        self.setattr_device("ttl16")  # individual AOM
        self.setattr_device("ttl17")  # individual AOD1
        self.setattr_device("ttl18")  # individual AOD2

        self.setattr_device("ttl21")  # RSB
        self.setattr_device("ttl22")  # BSB

        self.setattr_argument("onoff_DDS", BooleanValue(default=False))
        self.setattr_argument("atten", NumberValue(ndecimals=2, step=1))

        self.setattr_argument("individual_AOM_onoff", BooleanValue(default=False))

        self.setattr_argument("individual_AOD1_onoff", BooleanValue(default=False))
        self.setattr_argument("individual_AOD1_freq", NumberValue(ndecimals=8, unit="MHz", step=1))
        self.setattr_argument("individual_AOD1_amp", NumberValue(ndecimals=2, step=1))
        self.setattr_argument("individual_AOD1_phase", NumberValue(default=0.02, ndecimals=4, step=0.01))

        self.setattr_argument("individual_AOD2_onoff", BooleanValue(default=False))
        self.setattr_argument("individual_AOD2_freq", NumberValue(ndecimals=8, unit="MHz", step=1))
        self.setattr_argument("individual_AOD2_amp", NumberValue(ndecimals=2, step=1))
        self.setattr_argument("individual_AOD2_phase", NumberValue(default=0.0, ndecimals=2, step=0.01))


        self.setattr_argument("RM2_onoff", BooleanValue(default=False))
        self.setattr_argument("Redsideband_freq", NumberValue(ndecimals=8, unit="MHz", step=1))
        self.setattr_argument("Redsideband_amp", NumberValue(ndecimals=2, step=1))
        self.setattr_argument("Redsideband_phase", NumberValue(default=0.02, ndecimals=4, step=0.01))
        self.setattr_argument("Bluesideband_freq", NumberValue(ndecimals=8, unit="MHz", step=1))
        self.setattr_argument("Bluesideband_amp", NumberValue(ndecimals=2, step=1))
        self.setattr_argument("Bluesideband_phase", NumberValue(default=0.0, ndecimals=2, step=0.01))

    @kernel  # This code runs on the FPGA
    def run(self):
        self.core.reset()  # resets core device

        self.urukul1_ch0.cpld.init()
        self.urukul1_ch0.init()
        self.urukul1_ch1.cpld.init()
        self.urukul1_ch1.init()
        self.urukul1_ch2.cpld.init()
        self.urukul1_ch2.init()
        self.urukul1_ch3.cpld.init()
        self.urukul1_ch3.init()

        self.urukul1_ch0.set_phase_mode(2)
        self.urukul1_ch1.set_phase_mode(2)
        self.urukul1_ch2.set_phase_mode(2)
        self.urukul1_ch3.set_phase_mode(2)

        self.ttl16.output()
        self.ttl17.output()
        self.ttl18.output()

        self.ttl21.output()
        self.ttl22.output()

        delay(1 * ms)  # 10ms delay

        if self.onoff_DDS == True:  # Turn On when True, Turn off when False.
            self.urukul1_ch0.set_att(self.atten)
            self.urukul1_ch0.sw.on()
            self.urukul1_ch0.set(self.Redsideband_freq, amplitude=self.Redsideband_amp, phase=self.Redsideband_phase)

            self.urukul1_ch1.set_att(self.atten)
            self.urukul1_ch1.sw.on()
            self.urukul1_ch1.set(self.Bluesideband_freq, amplitude=self.Bluesideband_amp, phase=self.Bluesideband_phase)

            self.urukul1_ch2.set_att(self.atten)
            self.urukul1_ch2.sw.on()
            self.urukul1_ch2.set(self.individual_AOD1_freq, amplitude=self.individual_AOD1_amp, phase=self.individual_AOD1_phase)

            self.urukul1_ch3.set_att(self.atten)
            self.urukul1_ch3.sw.on()
            self.urukul1_ch3.set(self.individual_AOD2_freq, amplitude=self.individual_AOD2_amp, phase=self.individual_AOD2_phase)

        else:
            self.urukul1_ch0.sw.off()
            self.urukul1_ch1.sw.off()
            self.urukul1_ch2.sw.off()
            self.urukul1_ch3.sw.off()

        if self.individual_AOM_onoff == True:
            self.ttl16.on()
        else:
            self.ttl16.off()

        if self.individual_AOD1_onoff == True:
            self.ttl17.on()
        else:
            self.ttl17.off()

        if self.individual_AOD2_onoff == True:
            self.ttl18.on()
        else:
            self.ttl18.off()



        if self.RM2_onoff == True:
            with parallel:
                self.ttl21.on()
                self.ttl22.on()
        else:
            with parallel:
                self.ttl21.off()
                self.ttl22.off()