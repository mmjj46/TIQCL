from pyspcm import *
from spcm_tools import *
import sys
import numpy as np
import matplotlib.pyplot as plt
import time

"""

[ CONTENT ]

(1) Card connection and Setup
   • AWG 연결 설정
      • Local
      • Remote : ip 주소 필요
   • Basic parameter 설정
      • Repetition
      • Step
      • Sample rate (MS/s)
      • Timeout (ms)
   • Channel 설정
      • Channel 0, 1 : Enable 여부, Max.Voltage
   • Trigger 설정
      • Ext.trigger
      • SW trigger
   • Clock 설정
      • Enable 여부, 10 MHz
   • Safety 설정
      • 이런저런 limit
   • 기타
      • Cardmode (SINGLERESTART)

(2) Various scan function calculation
   • Standard scan
      • time scan
      • frequency scan
   • Raman MS scan
   • Pulse shaping scan

(3) Sample transfer and Card connection

"""

# *** AWG 연결 설정 ----------------------------------------------------------

""" Connection """
setup_connection = False  # True: Local | False: Remote

# in case of False (=Remote connection)...
ip_address = "192.168.0.26"
inst_number = "inst0"  # inst0 ~ inst5

# *** Basic parameter 설정 ----------------------------------------------------------

""" Repetition """  # (=> SPC_LOOPS)
rep_number = 1  # 0: infinite loop
scan_rep_number = 1  # 1: Default

""" Step """  # (=> jj => llNumSteps)
step_number = 100

""" Samplerate (MS/s) """  # (=> SPC_SAMPLERATE) check the max. samplerate of AWG card
samplerate = 10000  # MS/s

""" Timeout (ms) """  # (=> SPC_TIMEOUT)
timeout = 100000  # ms

# *** AWG configuration  ----------------------------------------------------------

# Channel 설정 -----

""" Channel """
# CH0+ is main exp, CH1+ is for test
ch_number = 0  # 0: CH0 | 1: CH1 | 2: CH0 & CH1 (both)

ch_enable0 = 1  # 0: OFF | 1: PLUS (ON) | 2: MINUS
ch_enable1 = 0  # 0: OFF | 1: PLUS (ON) | 2: MINUS
ch_enable = [ch_enable0, ch_enable1]

# MW exp. : 350 mV | Raman exp. : 360 mV
ch_max_voltage0 = 360  # mV
ch_max_voltage1 = 360  # mV
ch_max_voltage = [ch_max_voltage0, ch_max_voltage1]

# Trigger 설정 -----

""" Ext. Trigger """
trig_number = 2  # 0 or 1: External Trigger | 2: Software Trigger

""" Ext. trigger level (mV) """  # (=> SPC_TRIG_EXT0_LEVEL0)
ext_trig_level = 2000  # mV (ARTIQ TTL = 3.8 V)

# Clock 설정 -----

""" Ref. Clock """  # (=> SPC_REFERENCECLOCK)
setup_ext_clock = False  # ON/OFF (always ON)
clock_MHz = 10  # MHz

# Safety 설정 -----

""" Experimental limit (mV) """  # (=> SPC_AMP0) DO NOT EXCEED THE LIMIT!!!!!!!!!!!
experimental_limit = 360  # mV

""" Channel output limit (mV) """
ch_max_voltage_limit = 500  # mV

""" Trig input limit (mV) """
max_trig_input_limit = 5000  # mV

# 기타

""" Card mode """
card_mode = "SPC_REP_STD_SINGLERESTART"  # SPC_REP_STD_SINGLE, SPC_REP_STD_MULTI

""" Trigger mode """
trig_mode = "SPC_TM_POS"  # SPC_TM_POS | SPC_TM_NEG | SPC_TM_BOTH

# *** Waveform, delay viewer 버튼 ----------------------------------------------------------

# Waveform viewer
SHOW_WAVEFORMS = True
jj_show = 2

# Delay viewer
SHOW_TIMES = True

# Pulse length viewer
SHOW_PULSELENGTH = True

# RUN 할 때 거쳐야 하는 안전장치

# (Raman AOM) Experimental limit 체크
if max(ch_max_voltage) > experimental_limit:
	sys.stdout.write(f"Error: Output voltage exceeds {experimental_limit} mV. Exiting...\n")
	exit(1)

# Channel output voltage limit 체크
if experimental_limit > ch_max_voltage_limit:
	sys.stdout.write(f"Error: Output voltage exceeds the limit. Exiting...\n")
	exit(1)

# External trigger limit 체크
if ext_trig_level > max_trig_input_limit:
	sys.stdout.write(f"Error: Ext. Trigger level exceeds the limit. Exiting...\n")
	exit(1)

# **************************************************************************
# AWG Card setting
# **************************************************************************

# open card

# Local 연결
if setup_connection == True:
    hCard = spcm_hOpen("/dev/spcm0")

# Remote 연결
elif setup_connection == False:
    remote_address = f"TCPIP[0]::{ip_address}::{inst_number}::INSTR"
    print(f"Connecting to AWG: {remote_address}")

    hCard = spcm_hOpen(
        create_string_buffer(remote_address.encode())
    )

else:
    print("Invalid connection. Select Local or Remote.")
    exit(1)

if not hCard:
    sys.stdout.write("no card found...\n")
    exit(1)

print("AWG connection successful!")

# Card type
lCardType = int32(0)
spcm_dwGetParam_i32(hCard, SPC_PCITYP, byref(lCardType))

# Serial number
lSerialNumber = int32(0)
spcm_dwGetParam_i32(hCard, SPC_PCISERIALNO, byref(lSerialNumber))

# Function type
lFncType = int32(0)
spcm_dwGetParam_i32(hCard, SPC_FNCTYPE, byref(lFncType))

# get card type name from driver
'''qwValueBufferLen = 20
pValueBuffer = pvAllocMemPageAligned(qwValueBufferLen)
spcm_dwGetParam_ptr(hCard, SPC_PCITYP, pValueBuffer, qwValueBufferLen)
sCardName = pValueBuffer.value.decode('UTF-8')'''

# Check if the card is for Analog output (AO). AWG is for AO (i.e., SPCM_TYPE_AO)
if lFncType.value == SPCM_TYPE_AO or lFncType.value == SPCM_TYPE_DO or lFncType.value == SPCM_TYPE_DIO:
    sys.stdout.write(
        "Found AWG card, serial number: {0}\n".format(lSerialNumber.value)
    )
else:
    sys.stdout.write(
        "This card is not supported by this analog output example.\n"
        "Serial number: {0}\n".format(lSerialNumber.value)
    )
    spcm_vClose(hCard)
    exit(1)

qwChEnable = int64(ch_number + 1)
spcm_dwSetParam_i64(hCard, SPC_CHENABLE, qwChEnable)

lSetChannels = int32(0)
spcm_dwGetParam_i32(hCard, SPC_CHCOUNT, byref(lSetChannels))

lBytesPerSample = int32(0)
spcm_dwGetParam_i32(hCard, SPC_MIINST_BYTESPERSAMPLE, byref(lBytesPerSample))

#### AWG configuration

# Set external clock
# (Rubidium clock as 10 MHz reference, this synchronizes our external trigger pulses together)
if setup_ext_clock == True:
	spcm_dwSetParam_i32(hCard, SPC_CLOCKMODE, SPC_CM_EXTREFCLOCK)  # Set to reference clock mode
	spcm_dwSetParam_i32(hCard, SPC_REFERENCECLOCK, MEGA(clock_MHz))

# ... and no clock output
spcm_dwSetParam_i32(hCard, SPC_CLOCKOUT, 0)

# Set card mode = Single Restart
spcm_dwSetParam_i32(hCard, SPC_CARDMODE, SPC_REP_STD_SINGLERESTART)

# Set loop number to loop infinite time in Single Restart mode
spcm_dwSetParam_i64(hCard, SPC_LOOPS, int32(rep_number))

# Set sample rate
spcm_dwSetParam_i64(hCard, SPC_SAMPLERATE, MEGA(samplerate))

# Set timeout duration
spcm_dwSetParam_i32(hCard, SPC_TIMEOUT, int32(timeout))

# Set the trigger
szErrorTextBuffer = create_string_buffer(256)  # Error buffer
if trig_number == 0:
	# External trigger 0
	dwError_SPC_TRIG_ORMASK = spcm_dwSetParam_i32(hCard, SPC_TRIG_ORMASK, SPC_TMASK_EXT0)
	if dwError_SPC_TRIG_ORMASK != ERR_OK:
		sys.stdout.write(f"dwError_SPC_TRIG_ORMASK = {dwError_SPC_TRIG_ORMASK}\n")
		spcm_dwGetErrorInfo_i32(hCard, ptr32(), ptr32(), szErrorTextBuffer)
		sys.stdout.write(f"szErrorTextBuffer = '{szErrorTextBuffer.value.decode()}'\n")
		spcm_vClose(hCard)
		exit(1)
	spcm_dwSetParam_i32(hCard, SPC_TRIG_EXT0_MODE, SPC_TM_POS)
	spcm_dwSetParam_i32(hCard, SPC_TRIG_EXT0_LEVEL0, ext_trig_level)
	spcm_dwSetParam_i32(hCard, SPC_TRIG_ANDMASK, 0)

elif trig_number == 1:
	# External trigger 1
	dwError_SPC_TRIG_ORMASK = spcm_dwSetParam_i32(hCard, SPC_TRIG_ORMASK, SPC_TMASK_EXT1)
	if dwError_SPC_TRIG_ORMASK != ERR_OK:
		sys.stdout.write(f"dwError_SPC_TRIG_ORMASK = {dwError_SPC_TRIG_ORMASK}\n")
		spcm_dwGetErrorInfo_i32(hCard, ptr32(), ptr32(), szErrorTextBuffer)
		sys.stdout.write(f"szErrorTextBuffer = '{szErrorTextBuffer.value.decode()}'\n")
		spcm_vClose(hCard)
		exit(1)
	spcm_dwSetParam_i32(hCard, SPC_TRIG_EXT1_MODE, SPC_TM_POS)
	spcm_dwSetParam_i32(hCard, SPC_TRIG_EXT1_LEVEL0, ext_trig_level)
	spcm_dwSetParam_i32(hCard, SPC_TRIG_ANDMASK, 0)

elif trig_number == 2:
	# Software trigger
	spcm_dwSetParam_i32(hCard, SPC_TRIG_ORMASK, SPC_TMASK_SOFTWARE)
	spcm_dwSetParam_i32(hCard, SPC_TRIG_ANDMASK, 0)
	spcm_dwSetParam_i32(hCard, SPC_TRIG_CH_ORMASK0, 0)
	spcm_dwSetParam_i32(hCard, SPC_TRIG_CH_ORMASK1, 0)
	spcm_dwSetParam_i32(hCard, SPC_TRIG_CH_ANDMASK0, 0)
	spcm_dwSetParam_i32(hCard, SPC_TRIG_CH_ANDMASK1, 0)
	spcm_dwSetParam_i32(hCard, SPC_TRIGGEROUT, 0)

else:
	print("Invalid trigger. Please enter 0 (Trig0) or 2 (SW trigger).")

# Set the analog output(AO) channels
if ch_number == 0:
	# Channel 0
	spcm_dwSetParam_i32(hCard, SPC_AMP0, ch_max_voltage[0])
	# Use PLUS(+) output
	spcm_dwSetParam_i64(hCard, SPC_ENABLEOUT0, ch_enable[0])

elif ch_number == 1:
	# Channel 1
	spcm_dwSetParam_i32(hCard, SPC_AMP1, ch_max_voltage[1])
	# Use PLUS(+) output
	spcm_dwSetParam_i64(hCard, SPC_ENABLEOUT1, ch_enable[1])

elif ch_number == 2:
	# Channel 0
	spcm_dwSetParam_i32(hCard, SPC_AMP0, ch_max_voltage[0])
	spcm_dwSetParam_i64(hCard, SPC_ENABLEOUT0, ch_enable[0])
	# Channel 1
	spcm_dwSetParam_i32(hCard, SPC_AMP1, ch_max_voltage[1])
	spcm_dwSetParam_i64(hCard, SPC_ENABLEOUT1, ch_enable[1])

else:
	print("Invalid channel. Please enter 0 (Ch0) or 1 (Ch1) or 2(Ch0&1).")


#
# **************************************************************************
# (2) Various scan function calculation
# **************************************************************************
#

##### Supplementary function, this is not scan function.
# 유틸리티(컴퓨터 계산보조) 함수입니다.

def waveform_sine(samplerate, freq_MHz, phase_rad, amp, time_us, time_offset_us=0):
	time = int(round(time_us * samplerate))
	offset = int(round(time_offset_us * samplerate))

	indices = offset + np.arange(time, dtype=np.float64)

	f_over_fs = freq_MHz / samplerate
	omega_dt = 2 * np.pi * f_over_fs

	# Float domain sine (-1.0 ~ +1.0)
	waveform_float = amp * np.sin(omega_dt * indices + phase_rad)

	# safety clip
	waveform_float = np.clip(waveform_float, -1.0, 1.0)

	# int16 conversion (NO -32768 issue)
	waveform_int16 = np.round(waveform_float * 32767).astype(np.int16)

	return waveform_int16

def multiple_of_64(sample_length):
	aligned = ((sample_length + 63) // 64) * 64
	return aligned

def multiple_of_2048(sample_length):
	aligned = ((sample_length + 2047) // 2048) * 2048
	return aligned

def collect_all_buffers_and_lengths(scan_fn, jj, samplerate):
	# using this function, we calculate all jj waveforms before the main loop

	all_buffers = []
	all_llMemSamples = []

	for ii in range(jj):
		pnBuffer_view, llMemSamples = scan_fn(ii, samplerate)

		all_buffers.append(pnBuffer_view)
		all_llMemSamples.append(llMemSamples)

	return all_buffers, all_llMemSamples

def collect_all_2ch_buffers_and_lengths(scan_fn_ch0, scan_fn_ch1, step_number, samplerate):
	"""
	scan_fn_ch0: Ch0용 파형 생성 함수 (time_scan 등)
	scan_fn_ch1: Ch1용 파형 생성 함수 (freq_scan 등)
	step_number: 전체 스캔 단계 수 (jj)
	samplerate: 샘플링 레이트 (MS/s)
	"""
	all_interleaved_buffers = []
	all_llMemSamples = [] # 이 값은 '한 채널당 샘플 수'가 아니라 '전체 인터리빙된 샘플 수'를 저장하게 됩니다.

	for ii in range(step_number):
		# 1. 각 채널의 파형을 독립적으로 계산
		# 기존 함수가 (pnBuffer_view, llMemSamples)를 반환한다고 가정
		wave0, len0 = scan_fn_ch0(ii, samplerate)
		wave1, len1 = scan_fn_ch1(ii, samplerate)

		# 2. 두 채널 중 더 긴 길이를 기준으로 정렬(Alignment) 확인
		# M5i.6357은 채널당 샘플 수가 64의 배수여야 함
		max_len = max(len0, len1)
		#aligned_len = int(multiple_of_64(max_len))
		aligned_len = int(max_len)

		# 3. 인터리빙된 통합 버퍼 생성 (2채널이므로 길이는 2배)
		# [Ch0_0, Ch1_0, Ch0_1, Ch1_1, ...] 구조
		interleaved_buffer = np.zeros(aligned_len * 2, dtype=np.int16)

		# 4. 데이터 배치 (짝수 인덱스: Ch0, 홀수 인덱스: Ch1)
		# np.pad를 사용하여 길이가 짧은 쪽은 뒤를 0으로 채움
		interleaved_buffer[0::2] = np.pad(wave0, (0, aligned_len - len0))
		interleaved_buffer[1::2] = np.pad(wave1, (0, aligned_len - len1))

		# 5. 메모리 확보를 위해 개별 파형 삭제
		del wave0
		del wave1

		# 6. 결과 저장
		all_interleaved_buffers.append(interleaved_buffer)
		# 전체 전송 샘플 수 (aligned_len * 2) 저장
		all_llMemSamples.append(aligned_len * 2)

	return all_interleaved_buffers, all_llMemSamples


##### Main experiment function
# 실제 실험에 쓰이는 스캔용 함수입니다.

# STAGE 1 : [왕쉬움] Basic scan function
def time_scan(jj, samplerate):
	"""Monotonic sine wave generator
	(순수 Time scan: freq/phase 고정, pulse 길이만 jj에 비례해서 증가)"""

	# ↓↓↓ [수정] freq_scan 등에서 찾은 실제 carrier 공진 주파수로 반드시 교체할 것
	freq_CAR_MHz = 71.822
	freq_RSB_MHz = 70.8604
	freq_BSB_MHz = 72.7836

	# Frequency (MHz)
	freq_single_MHz = freq_CAR_MHz
	# (1, 2, 5, 8, threshold, 15 )
	# Zeeman sigma- 192.044 MHz, thres 8.6737 kHz
	# Zeeman sigma+ 207.966 Mhz, thres 10.5309 kHz

	# Phase (Rad)
	phase_single_rad = 0.0

	# Amplitude
	amp_single = 1
	# 0 ≤ amp_single ≤ 1

	# Time scan step (µs)
	# also Sample length, which increases proportionally with each jj loop as the time step
	start_time_us = 0
	step_time_us = 1
	total_time_us = start_time_us + jj * step_time_us

	if total_time_us == 0:
		llMemSamples = multiple_of_64(2048)
		pnBuffer_view = np.zeros(llMemSamples, dtype=np.int16)

		return pnBuffer_view, llMemSamples

	# Calculate the sample length
	len_total = int(round(total_time_us * samplerate))

	# Zero-padding to match 64-aligned system
	llMemSamples = multiple_of_64(len_total)

	# Set pnBuffer's view
	pnBuffer_view = np.zeros(llMemSamples, dtype=np.int16)

	# Filling in the Buffer and zero-padding
	pnBuffer_view[:len_total] = waveform_sine(samplerate, freq_single_MHz,
                              phase_single_rad, amp_single, total_time_us)

	return pnBuffer_view, llMemSamples

def freq_scan(jj, samplerate):
	"""Monotonic sine wave generator"""

	# Frequency (MHz) and freq scan step (kHz)
	freq_CAR_MHz = 71.75
	freq_RSB_MHz = 70.580
	freq_BSB_MHz = 73.035

	start_freq_MHz = freq_BSB_MHz
	step_freq_kHz = 0.5
	freq_scan_MHz = start_freq_MHz + jj * 0.001 * step_freq_kHz

	# Phase (Rad)
	phase_single_rad = 0.0

	# Amplitude
	amp_single = 0.01 #0.04 # 0.6  # 0 ≤ amp_single ≤ 1

	# Gate time (us)
	total_time_us = 300

	# Calculate the sample length
	len_total = int(round(total_time_us * samplerate))

	# Zero-padding to match 64-aligned system
	llMemSamples = multiple_of_64(len_total)

	# Set pnBuffer's view
	pnBuffer_view = np.zeros(llMemSamples, dtype=np.int16)

	# Fill buffer and zero-pad
	pnBuffer_view[:len_total] = waveform_sine(samplerate, freq_scan_MHz, phase_single_rad, amp_single, total_time_us)

	return pnBuffer_view, llMemSamples


# STAGE 2 : [쉬움] Basic scan function 응용
def freq_scan_RSBBSB(jj, samplerate, step = step_number):
	"""Monotonic sine wave generator
	EX step_number = 300 , RSB step = BSB step = 150."""

	half_step = step//2

	# Frequency (MHz) and freq scan step (kHz)
	start_freq_MHz = 70.83
	step_freq_kHz = 0.5

	# Sideband frequency (MHz)
	freq_CAR_MHz = 71.822
	freq_RSB_MHz = start_freq_MHz
	freq_BSB_MHz = 2 * freq_CAR_MHz - (freq_RSB_MHz + half_step * 0.001 * step_freq_kHz)

	# Phase (Rad)
	phase_single_rad = 0.0

	# Amplitude
	amp_single = 0.03   # 0 ≤ amp_single ≤ 1

	# Gate time (us)
	total_time_us = 120

	if jj < step//2:
		freq_scan_MHz = freq_RSB_MHz + jj * 0.001 * step_freq_kHz

	else:
		freq_scan_MHz = freq_BSB_MHz + (jj-half_step) * 0.001 * step_freq_kHz

	# Calculate the sample length
	len_total = int(round(total_time_us * samplerate))

	# Zero-padding to match 64-aligned system
	llMemSamples = multiple_of_64(len_total)

	# Set pnBuffer's view
	pnBuffer_view = np.zeros(llMemSamples, dtype=np.int16)

	# Fill buffer and zero-pad
	pnBuffer_view[:len_total] = waveform_sine(samplerate, freq_scan_MHz, phase_single_rad, amp_single, total_time_us)

	return pnBuffer_view, llMemSamples

def single_phase_scan(jj, samplerate):
	"""Monotonic sine wave generator for single-phase scan"""

	# Frequency (MHz)
	freq_single_MHz = 71.838

	# Phase (Rad) and Phase scan step
	phase_single_rad = 0.0
	step_phase_rad = 0.1
	total_phase_rad = step_phase_rad * np.pi * jj

	# Amplitude
	amp_single = 1  # 0 ≤ amp_single ≤ 1

	# Rabi pi-time (us)
	# [참고] time_scan에서 구한 π-time 값으로 반드시 교체할 것
	pi_time_us = 10
	half_pi_time_us = 0.5 * pi_time_us

	# Calculate the sample length
	len_half_pi = int(round(half_pi_time_us * samplerate))
	len_total = 2 * len_half_pi

	# Zero-padding to match 64-aligned system
	llMemSamples = multiple_of_64(len_total)

	# Set pnBuffer's view
	pnBuffer_view = np.zeros(llMemSamples, dtype=np.int16)

	## Half-pi-pulse gate
	pnBuffer_view[0:len_half_pi] = waveform_sine(samplerate, freq_single_MHz, phase_single_rad, amp_single, half_pi_time_us)

	## Half-pi-pulse gate (for phase scan)
	pnBuffer_view[len_half_pi:] = waveform_sine(samplerate, freq_single_MHz, total_phase_rad, amp_single,
												 half_pi_time_us)

	return pnBuffer_view, llMemSamples


# STAGE 3 : [보통] Duotone scan, various modulation
def MS_time_scan(jj, samplerate):
	"""Duotone sine wave generator
	(pnBuffer_view 작성, waveform_sine 호출 최소화)"""

	# Detuning (kHz)
	detuning_kHz = 10

	# Frequency (MHz)
	#freq_RSB_MHz = 70.643 - 0.001 * detuning_kHz
	#freq_BSB_MHz = 73.033 + 0.001 * detuning_kHz

	# Frequency (MHz)
	freq_RSB_MHz = 70.5749710
	freq_BSB_MHz = 73.0693810

	# Phase (Rad)
	phase_single_rad = 0.0

	# Amplitude
	amp_RSB = 1 # 0 ≤ amp_single ≤ 1
	amp_BSB = 1

	# Time scan step (µs)
	start_time_us = 0
	step_time_us = 10
	total_time_us = start_time_us + jj * step_time_us

	if total_time_us == 0:
		llMemSamples = multiple_of_2048(1)
		pnBuffer_view = np.zeros(llMemSamples, dtype=np.int16)

		return pnBuffer_view, llMemSamples

	# Calculate the sample length
	len_total = int(round(total_time_us * samplerate))

	# Zero-padding to match 64-aligned system
	llMemSamples = multiple_of_64(len_total)

	# Set pnBuffer's view
	pnBuffer_view = np.zeros(llMemSamples, dtype=np.int16)

	## MS gate
	# RSB
	pnBuffer_view[:len_total] = waveform_sine(
		samplerate, freq_RSB_MHz, phase_single_rad, 0.5 * amp_RSB, total_time_us
	)
	# BSB
	pnBuffer_view[:len_total] += waveform_sine(
		samplerate, freq_BSB_MHz, phase_single_rad, 0.5 * amp_BSB, total_time_us
	)

	return pnBuffer_view, llMemSamples

def MS_freq_scan(jj, samplerate):
	"""Duotone sine wave generator
	= SDF """

	# Frequency (MHz) and step frequency
	freq_RSB_MHz = 70.2
	freq_BSB_MHz = 73.476
	step_freq_kHz = 1
	freq_RSB_scan_MHz = freq_RSB_MHz + jj * 0.001 * step_freq_kHz
	freq_BSB_scan_MHz = freq_BSB_MHz - jj * 0.001 * step_freq_kHz

	# Phase (Rad) and Phase scan step
	phase_single_rad = 0.0

	# Amplitude
	amp_RSB = 0.5  # 0 ≤ amp_single ≤ 1
	amp_BSB = 0.5

	# MS gate time (us)
	total_time_us = 100

	# Calculate the sample length
	len_total = int(round(total_time_us * samplerate))

	# Zero-padding to match 64-aligned system
	llMemSamples = multiple_of_64(len_total)

	# Set pnBuffer's view
	pnBuffer_view = np.zeros(llMemSamples, dtype=np.int16)

	## MS gate
	# RSB
	pnBuffer_view[:len_total] = waveform_sine(
		samplerate, freq_RSB_scan_MHz, phase_single_rad, 0.5 * amp_RSB, total_time_us
	)
	# BSB
	pnBuffer_view[:len_total] += waveform_sine(
		samplerate, freq_BSB_scan_MHz, phase_single_rad, 0.5 * amp_BSB, total_time_us
	)

	return pnBuffer_view, llMemSamples

def MS_phase_scan(jj, samplerate):
	"""Duotone sine wave generator
	(pnBuffer_view 작성, waveform_sine 호출 최소화)
	= Parity scan"""

	# Frequency (MHz)
	freq_single_MHz = 71.8219480
	freq_RSB_MHz = 70.5742400
	freq_BSB_MHz = 73.0696560

	# Phase (Rad) and Phase scan step
	phase_single_rad = 0.0

	start_phase_rad = 0.0
	step_phase_rad = 0.1
	total_phase_rad = start_phase_rad + step_phase_rad * np.pi * jj

	# Amplitude
	amp_single = 0.3  # 0 ≤ amp_single ≤ 1
	amp_RSB = 1
	amp_BSB = 1

	# Rabi pi-time (us)
	pi_time_us = 16.127272
	half_pi_time_us = 0.5 * pi_time_us

	# MS gate time (us)
	MS_time_us = 130.2337696

	# Each gate's length calculation
	len_MS = int(round(MS_time_us * samplerate))
	len_half_pi = int(round(half_pi_time_us * samplerate))

	# Calculate the sample length
	len_total = len_MS + len_half_pi

	# Zero-padding to match 64-aligned system
	llMemSamples = multiple_of_64(len_total)

	# Set pnBuffer's view
	pnBuffer_view = np.zeros(llMemSamples, dtype=np.int16)

	## MS gate
	# RSB
	pnBuffer_view[:len_MS] = waveform_sine(
		samplerate, freq_RSB_MHz, phase_single_rad, 0.5 * amp_RSB, MS_time_us
	)
	# BSB
	pnBuffer_view[:len_MS] += waveform_sine(
		samplerate, freq_BSB_MHz, phase_single_rad, 0.5 * amp_BSB, MS_time_us
	)

	## Half-pi-pulse gate
	pnBuffer_view[len_MS : len_MS + len_half_pi] = waveform_sine(
		samplerate, freq_single_MHz, total_phase_rad, amp_single, half_pi_time_us)

	return pnBuffer_view, llMemSamples

def MS_amp_scan(jj, samplerate):
	"""Duotone sine wave generator
	(pnBuffer_view 작성, waveform_sine 호출 최소화)"""

	# Frequency (MHz)
	freq_RSB_MHz = 70.5917250
	freq_BSB_MHz = 73.0503170

	# Phase (Rad) and Phase scan step
	phase_single_rad = 0.0

	# Amplitude
	start_amp_RSB = 1.0
	start_amp_BSB = 1.0
	step_amp = -0.1


	# Amplitude clipping (preventing (-) amp value)
	total_amp_RSB = np.clip(start_amp_RSB + step_amp * jj, 0.0, 1.0)
	total_amp_BSB = np.clip(start_amp_BSB + step_amp * jj, 0.0, 1.0)

	# MS gate time (us)
	total_time_us = 127.2750414

	# Calculate the sample length
	len_total = int(round(total_time_us * samplerate))

	# Zero-padding to match 64-aligned system
	llMemSamples = multiple_of_64(len_total)

	# Set pnBuffer's view
	pnBuffer_view = np.zeros(llMemSamples, dtype=np.int16)

	## MS gate
	# RSB
	pnBuffer_view[:len_total] = waveform_sine(
		samplerate, freq_RSB_MHz, phase_single_rad, 0.5 * total_amp_RSB, total_time_us
	)
	# BSB
	pnBuffer_view[:len_total] += waveform_sine(
		samplerate, freq_BSB_MHz, phase_single_rad, 0.5 * total_amp_BSB, total_time_us
	)

	return pnBuffer_view, llMemSamples


# STAGE 4 : [어려움] Pulse shaping 1 - "DM" pulse
def MW_DM_time_scan(jj, samplerate):
	"""
	Pulse shaping time scan with composite pulses.
	Structure per pulse: [Anti-phase(α)] - [In-phase(1 + 2α)] - [Anti-phase(α)]
	Sequence: [Shaped Pulse]
	"""

	alpha = 0
	freq_single_MHz = 200.010

	phase_rad = 0.0
	amp = 1.0

	start_time_us = 0
	step_time_us = 1

	total_time_us = start_time_us + jj * step_time_us

	# 예외 처리 [1]: jj = 0이거나 시간이 0이면 펄스가 없는 공백 버퍼 반환
	if total_time_us == 0:
		# 장비 최소 조건이 2048샘플이 아니라면 multiple_of_64(0) 또는 64도 가능합니다.
		llMemSamples = multiple_of_64(2048)
		pnBuffer_view = np.zeros(llMemSamples, dtype=np.int16)
		return pnBuffer_view, llMemSamples

	# 1. 시간 파라미터 정의
	t_extra = total_time_us * alpha
	t_main = total_time_us * (1 + 2 * alpha)

	# 2. 샘플 수 정의 (round로 정수 확정)
	n_extra = int(round(t_extra * samplerate))
	n_main = int(round(t_main * samplerate))

	# 전체 길이는 조각들의 합으로 정의
	actual_pulse_samples = n_extra + n_main + n_extra
	llMemSamples = multiple_of_64(actual_pulse_samples)

	pnBuffer_view = np.zeros(llMemSamples, dtype=np.int16)

	# 3. 데이터 채우기 (역산된 정확한 시간 유입으로 ValueError 원천 차단)
	curr_idx = 0

	# [Segment 1] [Anti-phase(α)]
	if n_extra > 0:
		duration_extra_us = n_extra / samplerate
		offset_us = curr_idx / samplerate
		pnBuffer_view[curr_idx : curr_idx + n_extra] = waveform_sine(
			samplerate, freq_single_MHz, phase_rad + np.pi, amp, duration_extra_us, offset_us
		)
		curr_idx += n_extra

	# [Segment 2] [In-phase(1 + 2α)]
	if n_main > 0:
		duration_main_us = n_main / samplerate
		offset_us = curr_idx / samplerate
		pnBuffer_view[curr_idx : curr_idx + n_main] = waveform_sine(
			samplerate, freq_single_MHz, phase_rad, amp, duration_main_us, offset_us
		)
		curr_idx += n_main

	# [Segment 3] [Anti-phase(α)]
	if n_extra > 0:
		duration_extra_us = n_extra / samplerate
		offset_us = curr_idx / samplerate
		pnBuffer_view[curr_idx : curr_idx + n_extra] = waveform_sine(
			samplerate, freq_single_MHz, phase_rad + np.pi, amp, duration_extra_us, offset_us
		)

	return pnBuffer_view, llMemSamples

def MW_DM_freq_scan(jj, samplerate):
	"""Detuning error robust gate with phase-tracked segments"""

	alpha = 1.27  # 0일 때는 Main 펄스만 나가고, 0보다 크면 앞뒤로 Extra 펄스가 붙음
	start_freq_MHz = 199.96
	step_freq_kHz = 1
	freq_scan_MHz = start_freq_MHz + jj * 0.001 * step_freq_kHz

	phase_rad = 0.0
	amp = 1
	total_time_us = 5.9726095

	# 1. 시간 파라미터 정의
	t_extra = total_time_us * alpha
	t_main = total_time_us * (1 + 2 * alpha)

	# 2. 샘플 수 정의 (정수형으로 확실하게 못박음)
	n_extra = int(round(t_extra * samplerate))
	n_main = int(round(t_main * samplerate))

	# 전체 길이는 실제 채워질 샘플들의 합
	actual_pulse_samples = n_extra + n_main + n_extra
	llMemSamples = multiple_of_64(actual_pulse_samples)

	pnBuffer_view = np.zeros(llMemSamples, dtype=np.int16)

	# 3. 데이터 채우기 (샘플 개수 기반 정밀 제어)
	curr_idx = 0

	# [Segment 1] 역위상 Extra (alpha)
	# n_extra가 0보다 클 때만 실제로 생성하고 진입합니다.
	if n_extra > 0:
		duration_extra_us = n_extra / samplerate
		offset_us = curr_idx / samplerate
		pnBuffer_view[curr_idx : curr_idx + n_extra] = \
		   waveform_sine(samplerate, freq_scan_MHz, phase_rad + np.pi, amp, duration_extra_us, offset_us)
		curr_idx += n_extra

	# [Segment 2] 정위상 Main (1 + 2*alpha)
	duration_main_us = n_main / samplerate
	offset_us = curr_idx / samplerate
	pnBuffer_view[curr_idx : curr_idx + n_main] = \
	   waveform_sine(samplerate, freq_scan_MHz, phase_rad, amp, duration_main_us, offset_us)
	curr_idx += n_main

	# [Segment 3] 역위상 Extra (alpha)
	if n_extra > 0:
		duration_extra_us = n_extra / samplerate
		offset_us = curr_idx / samplerate
		pnBuffer_view[curr_idx : curr_idx + n_extra] = \
		   waveform_sine(samplerate, freq_scan_MHz, phase_rad + np.pi, amp, duration_extra_us, offset_us)
		curr_idx += n_extra

	return pnBuffer_view, llMemSamples

def MW_DM_alpha_scan(jj, samplerate):
	"""Detuning error robust gate with phase-tracked segments"""

	# alpha = 0.00~2.00까지 step 0.01로 pi/2-pulse scan할것

	alpha_start = 0.00  # pi-pulse 스캔 시 1/3, pi/2-pulse 스캔 시 1.27
	alpha_step = 0.01
	alpha = alpha_start + jj * alpha_step

	freq_single_MHz = 200.010

	phase_rad = 0.0
	amp = 1
	total_time_us = 7.22615  # 6.67855

	if total_time_us == 0:
		llMemSamples = multiple_of_64(2048)
		pnBuffer_view = np.zeros(llMemSamples, dtype=np.int16)

		return pnBuffer_view, llMemSamples

	# 1. 시간 파라미터 정의
	t_extra = total_time_us * alpha
	# 정위상 묶음 (alpha + main + alpha = 1 + 4*alpha가 아니라,
	# 사용자의 로직에 따르면 alpha + main + alpha = 1 + 2*alpha)
	t_main = total_time_us * (1 + 2 * alpha)

	# 2. 샘플 수 정의 (정수형으로 확정하여 오차 방지)
	n_extra = int(round(t_extra * samplerate))
	n_main = int(round(t_main * samplerate))

	# 전체 길이는 조각들의 합으로 정의
	actual_pulse_samples = n_extra + n_main + n_extra
	llMemSamples = multiple_of_64(actual_pulse_samples)

	pnBuffer_view = np.zeros(llMemSamples, dtype=np.int16)

	# 3. 데이터 채우기 (보여주신 fill_shaped_pulse 로직 적용)
	curr_idx = 0
	curr_time = 0.0

	# [Segment 1] 역위상 Extra (alpha)
	# -1을 곱하는 대신 phase + pi를 사용하여 위상을 뒤집음 (더 정석적인 방법)
	pnBuffer_view[curr_idx: curr_idx + n_extra] = \
		waveform_sine(samplerate, freq_single_MHz, phase_rad + np.pi, amp, t_extra, curr_time)

	curr_idx += n_extra
	curr_time += (n_extra / samplerate)  # 반올림 오차 방지를 위해 실제 생성된 샘플 수만큼 시간 전진

	# [Segment 2] 정위상 Main (1 + 2*alpha)
	pnBuffer_view[curr_idx: curr_idx + n_main] = \
		waveform_sine(samplerate, freq_single_MHz, phase_rad, amp, t_main, curr_time)

	curr_idx += n_main
	curr_time += (n_main / samplerate)

	# [Segment 3] 역위상 Extra (alpha)
	pnBuffer_view[curr_idx: curr_idx + n_extra] = \
		waveform_sine(samplerate, freq_single_MHz, phase_rad + np.pi, amp, t_extra, curr_time)

	return pnBuffer_view, llMemSamples

def MW_DM_Ramsey(jj, samplerate):
	"""
	Ramsey experiment with 5-segment composite pulses.
	Structure per pulse: [Anti-phase(α)] - [In-phase(1 + 2α)] - [Anti-phase(α)]
	Sequence: [Pulse 1] - [Delay] - [Pulse 2]
	"""
	# 1. 물리 파라미터 정의
	alpha = 0
	freq_MHz = 200.0105
	phase_rad = 0.0
	amp = 1.0

	# 펄스 폭 정의 (half-pi pulse 기준)
	pi_time_us = 11.8551
	t_basis = 0.5 * pi_time_us  # 기준이 되는 pi/2 pulse 길이

	# Ramsey Delay 계산
	start_delay_us = 0
	step_delay_us = 2000
	delay_us = start_delay_us + jj * step_delay_us

	# 세그먼트별 시간 계산
	t_extra = t_basis * alpha
	t_main_combined = t_basis * (1 + 2 * alpha)
	t_shaped_total = t_basis * (1 + 4 * alpha)

	# 2. 샘플 수 계산 (정수형 확정으로 인덱스 에러 방지)
	n_extra = int(round(t_extra * samplerate))
	n_main_combined = int(round(t_main_combined * samplerate))
	n_shaped = n_extra + n_main_combined + n_extra
	n_delay = int(round(delay_us * samplerate))

	# 전체 메모리 할당 (Pulse + Delay + Pulse)
	actual_total_samples = 2 * n_shaped + n_delay
	llMemSamples = multiple_of_64(actual_total_samples)
	pnBuffer_view = np.zeros(llMemSamples, dtype=np.int16)

	# 3. 펄스 생성 도우미 함수 (내부 함수)
	def insert_shaped_pulse(start_idx, start_time):
		curr_idx = start_idx
		curr_time = start_time

		# [Segment 1] 역위상 Extra (α)
		if n_extra > 0:
			pnBuffer_view[curr_idx: curr_idx + n_extra] = \
				waveform_sine(samplerate, freq_MHz, phase_rad + np.pi, amp, t_extra, curr_time)
			curr_idx += n_extra
			curr_time += (n_extra / samplerate)

		# [Segment 2] 정위상 Main (1 + 2α)
		pnBuffer_view[curr_idx: curr_idx + n_main_combined] = \
			waveform_sine(samplerate, freq_MHz, phase_rad, amp, t_main_combined, curr_time)
		curr_idx += n_main_combined
		curr_time += (n_main_combined / samplerate)

		# [Segment 3] 역위상 Extra (α)
		if n_extra > 0:
			pnBuffer_view[curr_idx: curr_idx + n_extra] = \
				waveform_sine(samplerate, freq_MHz, phase_rad + np.pi, amp, t_extra, curr_time)

	# 4. 시퀀스 조립
	# 첫 번째 펄스 삽입 (t=0)
	insert_shaped_pulse(0, 0.0)

	# 두 번째 펄스 삽입 (t = t_shaped + delay 이후)
	# n_shaped와 n_delay를 인덱스로 사용하여 정확한 위치에 배치
	idx_2nd = n_shaped + n_delay
	t_2nd_start = (n_shaped + n_delay) / samplerate  # 샘플 기반의 정밀한 시간 계산

	insert_shaped_pulse(idx_2nd, t_2nd_start)

	return pnBuffer_view, llMemSamples

# STAGE 5 : [왕어려움] Pulse shaping 2 - "HG" pulse
def HG_MS_freq_scan(jj, samplerate):
	"""Duotone sine wave generator
	(pnBuffer_view 작성, waveform_sine 호출 최소화)"""

	# Pulse Gaussian parameter
	tau_d_us = 20
	T_over_tau = 8

	# Optimal HG coefficient
	coef_HG_index = [ 0, 2, 4, 6, 8 ]
	coef_HG_list = [ 0, 2, 4, 6, 8 ]

	def HG(u, m):
		"""
		Hermite-Gaussian 기저 함수 자체 구현
		f(u) = N_m * H_m(u) * exp(-u^2 / 2)
		"""
		# Hermite 다항식 계수 계산 (NumPy 내장)
		herm_coeffs = [0] * m + [1]
		H_m = np.polynomial.hermite.Hermite(herm_coeffs)

		# Normalization constant N_m
		from math import factorial
		N_m = (np.pi ** (-0.25)) / np.sqrt(factorial(m) * (2 ** m))

		return N_m * H_m(u) * np.exp(-(u ** 2) / 2)

	# coef_HG_list 이용한 pulse amp shape
	# amp 설정
	# amp * solution_shaped * sine(RSB+BSB)

	# Frequency (MHz)
	freq_RSB_MHz = 70.5749710
	freq_BSB_MHz = 73.0693810

	# Phase (Rad)
	phase_RSB_rad = 0.0
	phase_BSB_rad = 0.0

	# Amplitude
	start_amp_RSB = 1.0
	start_amp_BSB = 1.0
	step_amp = 0

	# Amplitude clipping (preventing (-) amp value)
	total_amp_RSB = np.clip(start_amp_RSB + step_amp * jj, 0.0, 1.0)
	total_amp_BSB = np.clip(start_amp_BSB + step_amp * jj, 0.0, 1.0)

	# MS gate time (us)
	total_time_us = tau_d_us * T_over_tau

	# Calculate the sample length
	len_total = int(round(total_time_us * samplerate))

	# Zero-padding to match 64-aligned system
	llMemSamples = multiple_of_64(len_total)

	# Set pnBuffer's view
	pnBuffer_view = np.zeros(llMemSamples, dtype=np.int16)

	## MS gate
	# RSB
	pnBuffer_view[:len_total] = waveform_sine(
		samplerate, freq_RSB_MHz, phase_RSB_rad, 0.5 * total_amp_RSB, total_time_us
	)
	# BSB
	pnBuffer_view[:len_total] += waveform_sine(
		samplerate, freq_BSB_MHz, phase_BSB_rad, 0.5 * total_amp_BSB, total_time_us
	)

	return pnBuffer_view, llMemSamples


#
# **************************************************************************
# (3) Sample transfer and card operation
# **************************************************************************
#


#### Sample and buffer preparation

### Choose the scan function
""" Single channel (CH0+ = Raman2) """
calculate_func = time_scan
#calculate_func = freq_scan
#calculate_func = MS_phase_scan
#calculate_func = MS_time_scan
#calculate_func = MS_amp_scan

# Two channel (CH0+ & CH1+)
""" Two channel (CH0+ & CH1+) """
calculate_func_ch0 = time_scan
calculate_func_ch1 = freq_scan

start_time = time.perf_counter() # Buffer calculation start

# collect_all_buffers_and_lengths
# buffers : all waveforms for jj | lengths : all llMemSamples for jj

if ch_number == 2:
	buffers, lengths = collect_all_2ch_buffers_and_lengths(calculate_func_ch0, calculate_func_ch1, step_number, samplerate)

else:
	buffers, lengths = collect_all_buffers_and_lengths(calculate_func, step_number, samplerate)

end_time = time.perf_counter() # Buffer calculation end
execution_time = end_time - start_time
print(f"Buffer calculation time: {execution_time:.6f} seconds")

# 순수한 정수 숫자로 최대 길이를 먼저 가져옵니다.
pure_max_samples = int(max(lengths))

# 샘플당 총 바이트 수를 미리 계산합니다.
bytes_per_sample = lBytesPerSample.value * lSetChannels.value

# 버퍼 크기를 계산한 뒤 uint64로 감쌉니다.
# 최대 샘플 길이를 넘는지 아닌지 알 수 있음
qwBufferSize = uint64(pure_max_samples * bytes_per_sample)
print(f"Max sample length = {pure_max_samples/samplerate} us ")
print(f"Max sample byte = {(pure_max_samples * bytes_per_sample) / 1024:.2f} kB")

# 만약 다른 코드에서 llMemSamplesMax를 요구한다면 선언
llMemSamplesMax = int64(pure_max_samples)

# 메모리를 할당합니다.
pvBuffer = pvAllocMemPageAligned(qwBufferSize.value)

# 최대 크기의 넘파이 뷰를 딱 '한 번'만 열어둡니다.
pnBuffer = cast(pvBuffer, ptr16)
pnBuffer_full_view = np.ctypeslib.as_array(pnBuffer, shape=(pure_max_samples,))

assert lFncType.value == SPCM_TYPE_AO

# Data transmission time checker
transmission_times = []


#### Main loop
for jj in range(step_number):
	print(f"Sample : jj = {jj}")

	# Record jj-th cycle start time
	start_time = time.time()

	# 이번 스텝의 샘플 수 가져오기
	pure_samples = int(lengths[jj])

	# 샘플 수를 레지스터에 등록
	current_memsize = int64(pure_samples)
	spcm_dwSetParam_i64(hCard, SPC_MEMSIZE, current_memsize)

	# 실제 전송 바이트 계산 (상단에서 만든 bytes_per_sample 활용)
	calculated_bytes = pure_samples * bytes_per_sample


	# =================================================================
	# [안전장치 추가] 하드웨어 DMA 최소 전송 단위 및 정렬 조건 방어
	# =================================================================
	# 규칙 1: 최소 2048 바이트 이상이어야 함
	if calculated_bytes < 2048:
		calculated_bytes = 2048

	# 규칙 2: 전송 바이트 크기는 반드시 64바이트의 배수여야 함
	if calculated_bytes % 64 != 0:
		calculated_bytes = ((calculated_bytes // 64) + 1) * 64

	# 최종 안전이 검증된 바이트 크기를 uint64로 포장
	current_transfer_bytes = uint64(calculated_bytes)

	# 매번 배열을 새로 정의하지 않고, 미리 열어둔 뷰의 앞부분에 펄스를 덮어씁니다.
	pnBuffer_full_view[:pure_samples] = buffers[jj]

	# Transfer the calculated sample
	sys.stdout.write("Starting the DMA transfer and waiting until data is in board memory\n")

	# 딱 이번 스텝의 바이트만큼만 전송하여 유령 잔상 차단
	spcm_dwDefTransfer_i64(hCard, SPCM_BUF_DATA, SPCM_DIR_PCTOCARD, int32(0), pvBuffer, int64(0), current_transfer_bytes)
	spcm_dwSetParam_i32(hCard, SPC_M2CMD, M2CMD_DATA_STARTDMA | M2CMD_DATA_WAITDMA)

	sys.stdout.write("... data has been transferred to board memory\n")
	sys.stdout.write(f"The expected number of triggers to receive: {rep_number}\n")
	sys.stdout.write(f"Starting the card ... ")
	sys.stdout.write(f"Waiting for all signals to be generated (timeout = {timeout} ms) ... ")

	# Start the card
	dwErrorStart = spcm_dwSetParam_i32(hCard, SPC_M2CMD,
							   M2CMD_CARD_START | M2CMD_CARD_ENABLETRIGGER | M2CMD_CARD_WAITREADY)

	# Error Check
	szErrorTextBuffer = create_string_buffer(256)
	dwErrorCode = spcm_dwGetErrorInfo_i32(hCard, ptr32(), ptr32(), szErrorTextBuffer)

	if dwErrorCode != ERR_OK:
		sys.stdout.write("... Error!\n")
		print(f"Error {dwErrorCode}: {szErrorTextBuffer.value.decode()}")
		spcm_vClose(hCard)
		exit(1)

	# Stop the card
	sys.stdout.write("Stopping the card ... ")
	spcm_dwSetParam_i32(hCard, SPC_M2CMD, M2CMD_CARD_STOP)
	sys.stdout.write("done\n")

	# Record jj-th cycle end time
	end_time = time.time()

	# Transmission time appending
	transmission_time = end_time - start_time
	transmission_times.append(transmission_time)

print("done")
spcm_vClose(hCard)


# Time viewer
if SHOW_TIMES == True:
	# Show the data transmission times for each step
	print("- - - Transmission times for each step:")
	for jj, t in enumerate(transmission_times):
		print(f"- jj = {jj}: {t:.4f} seconds")

	plt.plot(range(step_number), transmission_times, marker='o', linestyle='-', color='g')
	plt.title('Data transmission time')
	plt.xlabel('Step Number')
	plt.ylabel('Time (seconds)')
	plt.grid(True)
	plt.show()

# Waveform(buffer) viewer
if SHOW_WAVEFORMS == True:
	# Show the waveform for each step
	plt.plot(buffers[jj_show][:1000], label=f"jj = {jj_show}")
	plt.title('')
	plt.title(f'Waveform (Buffer for jj={jj_show})')
	plt.xlabel('Datapoint (0.1 ns)')
	plt.ylabel('Amplitude')
	plt.legend()
	plt.grid(True)

	# # --- 폴더 생성 및 엑셀 저장 코드 ---
	# folder_path = "C:/Users/user\Downloads"
	#
	# # 1. 지정한 폴더가 없으면 새로 생성
	# if not os.path.exists(folder_path):
	# 	os.makedirs(folder_path)
	# 	print(f"폴더가 존재하지 않아 '{folder_path}'를 생성했습니다.")
	#
	# # 2. 데이터를 데이터프레임으로 변환
	# df = pd.DataFrame(buffers[jj_show], columns=['Amplitude'])
	#
	# # 3. 전체 파일 경로 생성 (폴더 경로 + 파일명)
	# file_name = f"waveform_data_{jj_show}.xlsx"
	# full_path = os.path.join(folder_path, file_name)
	#
	# # 4. 엑셀 파일로 저장
	# df.to_excel(full_path, index_label='Datapoint_Index')
	#
	# print(f"데이터가 다음 위치에 저장되었습니다: {full_path}")

	plt.show()

# Pulse length viewer
if SHOW_PULSELENGTH == True:
	plt.figure(figsize=(8, 5))

	# lengths 리스트 자체를 Y축으로 두고 한 번에 그립니다.
	# X축은 자동으로 0부터 step_number-1 까지 매핑됩니다.
	plt.plot(lengths, marker='o', linestyle='-', color='b', label='Pulse Length')

	plt.title('Total Waveform Length per Scan Step (jj)')
	plt.xlabel('Scan Step (jj)')
	plt.ylabel('Datapoint (1 sample = 0.1 ns)')
	plt.grid(True, linestyle='--', alpha=0.6)
	plt.legend()
	plt.show()