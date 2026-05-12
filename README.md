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
   Crea un file chiamato `.env` nella cartella principale del progetto e inserisci la tua API Key di Google Gemini:
   ```env
   GEMINI_API_KEY=la_tua_chiave_api_qui
   ```

## 📂 Struttura del Progetto e Spiegazione dei File

### 1. `agent_main.py` (Script Principale)
È il cuore dell'applicazione. Avvia una sessione WebSocket bidirezionale (`bidiGenerateContent`) con il modello `gemini-3.1-flash-live-preview`. 
Gestisce la registrazione dell'audio grezzo (PCM), l'invio in streaming tramite la Live API e la riproduzione automatica della voce sintetizzata da Gemini in risposta.
**Esecuzione:**
```powershell
python .\agent_main.py
```
*(Premi Invio per registrare, parla nel microfono, poi premi nuovamente Invio per inviare. Infine premi 'q' per uscire.)*

### 2. `find_audio_devices.py` (Utility Dispositivi Audio)
Questo script è fondamentale per il debug e la configurazione hardware. Interroga il tuo sistema operativo per trovare i **microfoni (input)** e gli **altoparlanti (output)** predefiniti. 
È utilissimo eseguirlo se l'assistente non ti sente, per verificare che il microfono corretto sia impostato come default nel sistema operativo e per scoprire la sua frequenza di campionamento nativa (`default_samplerate`), necessaria per evitare distorsioni.
**Esecuzione:**
```powershell
python .\find_audio_devices.py
```

### 3. `list_models.py` (Utility Modelli Gemini)
Un semplice script di supporto che si collega a Google GenAI usando la tua chiave API e stampa nel terminale l'elenco completo di tutti i modelli a cui hai accesso (inclusi quelli sperimentali `-exp` o `live`). Utile per aggiornare `agent_main.py` quando Google rilascia nuovi modelli per l'audio.
**Esecuzione:**
```powershell
python .\list_models.py
```

### 4. `plot_waveform.py`
Uno script di test e analisi che mostra un approccio precedente. Permette di registrare un segmento audio, salvarlo in un buffer, riprodurlo per verifica e, tramite la libreria `matplotlib`, **disegnare il grafico della forma d'onda audio** a schermo.
**Esecuzione:**
```powershell
python .\plot_waveform.py
```

---
*Progetto sviluppato e ottimizzato per l'integrazione di interfacce vocali con LLM di ultima generazione.*