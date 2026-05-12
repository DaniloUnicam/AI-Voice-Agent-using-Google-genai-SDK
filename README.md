# 🎙️ Assistente Vocale Multimodale con Gemini Live API

Questo progetto implementa un assistente vocale in tempo reale (Voice-to-Voice) utilizzando la **Live API** di Google Gemini. Sfrutta connessioni WebSocket per inviare l'audio del microfono direttamente al modello e riprodurre l'audio generato in risposta, riducendo al minimo la latenza.

## 📦 Dipendenze e Requisiti

Il progetto richiede **Python 3.9+** e utilizza `uv` come gestore di pacchetti per garantire installazioni fulminee.

Le librerie principali utilizzate sono:
- `google-genai`: L'SDK ufficiale di Google per interagire con l'API di Gemini.
- `sounddevice`: Per la registrazione dal microfono e la riproduzione dell'audio.
- `numpy`: Per la manipolazione efficiente dei buffer audio in array di dati.
- `python-dotenv`: Per il caricamento sicuro della chiave API dal file `.env`.
- `matplotlib`: (Usata solo nello script `plot_waveform.py` per visualizzare il grafico).

## 🚀 Installazione e Configurazione

1. **Crea l'ambiente virtuale** (se non lo hai già fatto):
   ```bash
   uv venv
   ```

2. **Attiva l'ambiente virtuale**:
   - Su Windows (PowerShell):
     ```powershell
     .\.venv\Scripts\Activate.ps1
     ```

3. **Installa le dipendenze**:
   Assicurati di essere nell'ambiente virtuale e lancia:
   ```bash
   uv pip install google-genai sounddevice numpy python-dotenv matplotlib
   ```

4. **Configura le variabili d'ambiente**:
   Crea un file chiamato `.env` nella cartella principale del progetto e inserisci la tua API Key di Google Gemini e (opzionalmente) la soglia di silenzio per l'agente continuo:
   ```env
   GEMINI_API_KEY=la_tua_chiave_api_qui
   SILENCE_THRESHOLD=3000
   ```

## 📂 Struttura del Progetto e Spiegazione dei File

### 1. `continuous_agent.py` (Script Principale)
È il cuore dell'applicazione e la versione più avanzata dell'agente. Avvia una sessione continua (full-duplex) in tempo reale, simulando una vera e propria telefonata. Rileva automaticamente quando stai parlando e quando fai una pausa tramite un Noise Gate, inviando o silenziando il segnale di conseguenza. Supporta trascrizioni (Speech-to-Text) native ed evita accavallamenti durante la riproduzione delle risposte.
**Esecuzione:**
```powershell
python .\continuous_agent.py
```
*(Supporta il flag opzionale `--threshold` per sovrascrivere temporaneamente il valore del file .env)*

### 2. `calibrate_mic.py` (Utility di Calibrazione)
Strumento indispensabile per configurare il Noise Gate utilizzato da `continuous_agent.py`. Misura il rumore di fondo della tua stanza (o il volume della tua voce) e imposta automaticamente il valore ottimale di `SILENCE_THRESHOLD` nel tuo file `.env`.
**Esecuzione:**
```powershell
python .\calibrate_mic.py
```

### 3. `agent_main.py` (Script Push-to-Talk)
La versione originale dell'agente che utilizza un approccio "Push-to-Talk". Gestisce la registrazione dell'audio, l'invio in streaming tramite la Live API e la riproduzione automatica della risposta. Richiede input manuale tramite tastiera per iniziare e terminare la registrazione.
**Esecuzione:**
```powershell
python .\agent_main.py
```

### 4. `find_audio_devices.py` (Utility Dispositivi Audio)
Questo script è fondamentale per il debug e la configurazione hardware. Interroga il tuo sistema operativo per trovare i **microfoni (input)** e gli **altoparlanti (output)** predefiniti e scoprire la loro frequenza di campionamento nativa (`default_samplerate`).
**Esecuzione:**
```powershell
python .\find_audio_devices.py
```

### 5. `list_models.py` (Utility Modelli Gemini)
Uno script di supporto che si collega a Google GenAI usando la tua chiave API e stampa nel terminale l'elenco completo di tutti i modelli disponibili (inclusi quelli sperimentali `-exp` o `live`). Utile per aggiornare gli script principali quando Google rilascia nuovi modelli per l'audio.
**Esecuzione:**
```powershell
python .\list_models.py
```

### 6. `plot_waveform.py`
Uno script di test e analisi che mostra un approccio precedente. Permette di registrare un segmento audio, salvarlo in un buffer, riprodurlo per verifica e, tramite la libreria `matplotlib`, **disegnare il grafico della forma d'onda audio** a schermo.
**Esecuzione:**
```powershell
python .\plot_waveform.py
```



---
*Progetto sviluppato e ottimizzato per l'integrazione di interfacce vocali con LLM di ultima generazione.*