import sounddevice as sd
import numpy as np
import sys

def calibrate_mic():
    # Ricava la frequenza di campionamento predefinita
    fs = int(sd.query_devices(kind='input')['default_samplerate'])
    
    print("\n--- Calibratore di Soglia Microfono ---")
    print(f"Frequenza: {fs} Hz | Dispositivo: {sd.query_devices(kind='input')['name']}")
    print("Premi Ctrl+C per uscire e salvare il valore ideale.\n")
    print("Legenda: [Volume Attuale] | Picco Massimo")
    
    max_peak = 0

    def callback(indata, frames, time, status):
        nonlocal max_peak
        if status:
            print(status, file=sys.stderr)
        
        # Calcola il volume massimo nel chunk attuale
        volume_norm = np.max(np.abs(indata))
        
        if volume_norm > max_peak:
            max_peak = volume_norm

        # Crea una barra visiva
        bar_length = 40
        # Normalizziamo su un limite più realistico (es. 8000) per rendere la barra reattiva
        filled_length = int(bar_length * (volume_norm / 8000))
        filled_length = min(bar_length, filled_length) # Evita che la barra esca dai limiti visivi
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        
        # Stampa dinamica sulla stessa riga
        sys.stdout.write(f"\rValore: {int(volume_norm):5d} | [{bar}] | Picco: {int(max_peak):5d}")
        sys.stdout.flush()

    try:
        with sd.InputStream(channels=1, dtype='int16', callback=callback, samplerate=fs):
            while True:
                sd.sleep(100)
    except KeyboardInterrupt:
        print(f"\n\nCalibrazione terminata.")
        print(f"Consiglio: Imposta 'silence_threshold' a circa {int(max_peak * 0.7)} "
              f"se stavi parlando, o poco sopra {int(max_peak)} se eri in silenzio.")

if __name__ == "__main__":
    calibrate_mic()