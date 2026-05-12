import sounddevice as sd

input_device_info = sd.query_devices(kind='input')
output_device_info = sd.query_devices(kind='output')

in_samplerate = input_device_info['default_samplerate']
out_samplerate = output_device_info['default_samplerate']

print("--- Default Input Device ---")
print(input_device_info)
print(f"Default Input Sample Rate: {in_samplerate} Hz")
#############################################################à
print("\n--- Default Output Device ---")
print(output_device_info)
print(f"Default Output Sample Rate: {out_samplerate} Hz")