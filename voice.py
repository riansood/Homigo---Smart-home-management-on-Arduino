import serial
import wave
import time

# === CONFIGURATION ===
SERIAL_PORT = 'COM4'       # Replace with your actual port
BAUD_RATE = 115200
DURATION = 10               # Record duration in seconds
SAMPLE_RATE = 16000
OUTPUT_FILE = 'recording.wav'

# === SERIAL SETUP ===
print("Opening serial port...")
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
time.sleep(2)  # Let Arduino reset

# === TRIGGER RECORDING ===
print("Sending 'click' command to start recording...")
ser.write(b'click\r')  # \r ends the command for Arduino

# === CAPTURE AUDIO OVER TIME ===
print(f"Recording for {DURATION} seconds...")
start_time = time.time()
audio_bytes = bytearray()

while time.time() - start_time < DURATION:
    if ser.in_waiting:
        audio_bytes.extend(ser.read(ser.in_waiting))

# === SAVE TO WAV FILE ===
print("Saving to WAV file...")
with wave.open(OUTPUT_FILE, 'wb') as wf:
    wf.setnchannels(1)         # Mono
    wf.setsampwidth(2)         # 2 bytes = 16-bit samples
    wf.setframerate(SAMPLE_RATE)
    wf.writeframes(audio_bytes)

ser.close()
print(f"Audio saved to: {OUTPUT_FILE} ({len(audio_bytes)} bytes)")