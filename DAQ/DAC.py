import nidaqmx

DEV = "Dev3"
AO_CH = f"{DEV}/ao0"

MIN_V, MAX_V = -1.0, 1.0

print("원하는 전압을 입력하고 Enter")

with nidaqmx.Task() as ao:
    ao.ao_channels.add_ao_voltage_chan(AO_CH, min_val=MIN_V, max_val=MAX_V)

    while True:
        cmd = input("Voltage > ")

        if cmd.lower() == "q":
            break

        try:
            v = float(cmd)

            if v < MIN_V or v > MAX_V:
                print("범위를 벗어남")
                continue

            ao.write(v)
            print(f"→ {v:.3f} V 출력")

        except:
            print("숫자를 입력해야 함")

print("종료")
