import sounddevice as sd
import numpy as np
import sys
import os
from dotenv import set_key

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
        
        # Calcoliamo una soglia ideale assumendo che la calibrazione sia stata fatta in silenzio (rumore di fondo)
        suggested_threshold = int(max_peak * 1.2)
        
        print(f"Consigli: Imposta 'silence_threshold' a circa {int(max_peak * 0.7)} se stavi parlando,")
        print(f"o a circa {suggested_threshold} se eri in silenzio (rumore di fondo).")
        
        # Salvataggio automatico nel file .env
        env_path = ".env"
        try:
            if not os.path.exists(env_path):
                open(env_path, 'w').close()
            set_key(env_path, "SILENCE_THRESHOLD", str(suggested_threshold))
            print(f"\n[INFO] Soglia per il rumore di fondo ({suggested_threshold}) salvata automaticamente in '{env_path}'.")
        except Exception as e:
            print(f"\n[ERRORE] Impossibile salvare automaticamente nel file .env: {e}")

if __name__ == "__main__":
    calibrate_mic()