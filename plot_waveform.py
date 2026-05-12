import sounddevice as sd
import numpy as np
import matplotlib.pyplot as plt

def main():
    print("\n--- Registratore e Visualizzatore Onda Sonora ---")
    in_samplerate = sd.query_devices(kind='input')['default_samplerate']
    
    print("Premi Invio per iniziare la registrazione...")
    input()
    
    recorded_chunks = []
    print("Registrazione in corso... (Premi di nuovo Invio per fermare)")
    
    with sd.InputStream(
        samplerate=in_samplerate,
        channels=1,
        dtype='int16',
        callback=lambda indata, frames, time, status: recorded_chunks.append(indata.copy())
    ):
        input()
        
    if not recorded_chunks:
        print("Nessun audio registrato.")
        return

    print("Generazione del grafico in corso...")
    audio_buffer = np.concatenate(recorded_chunks)
    
    # 1. Genera l'asse temporale (durata totale divisa per il campionamento)
    time_axis = np.linspace(0, len(audio_buffer) / in_samplerate, num=len(audio_buffer))
    
    # 2. Disegna il grafico
    plt.figure(figsize=(12, 4))
    plt.plot(time_axis, audio_buffer, color='#007acc')
    plt.title("Forma d'onda dell'Audio Registrato")
    plt.xlabel("Tempo (secondi)")
    plt.ylabel("Ampiezza")
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # Mostra la finestra (il programma si bloccherà qui finché non chiudi la finestra)
    plt.show()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nUscita.")