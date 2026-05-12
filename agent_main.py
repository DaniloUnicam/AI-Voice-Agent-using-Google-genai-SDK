import sounddevice as sd
import numpy as np
import os
from google import genai
from google.genai import types
import asyncio
from dotenv import load_dotenv

load_dotenv()

# Configurazione Agente
# Il client pesca automaticamente GEMINI_API_KEY dal file .env
client = genai.Client()
 
# Per interagire nativamente con l'audio bidirezionale dobbiamo usare la Live API
# Assicuriamoci di usare la versione stabile o quella mostrata nella lista dei modelli
agent_model = "gemini-3.1-flash-live-preview"

agent_instructions = (
    "Repeat the user's question back to them, and then answer it. Note that the user is "
    "speaking to you via a voice interface. "
    "Keep your responses concise, conversational, and easily translatable to voice."
)

async def main():
    in_samplerate = sd.query_devices(kind='input')['default_samplerate']
    
    print("\n--- Inizializzazione Assistente Vocale (Gemini Live API) ---")
    
    # 1. Configurazione della sessione Live API (WebSocket)
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=types.Content(
            parts=[types.Part.from_text(text=agent_instructions)]
        )
    )

    # Avviamo la connessione Live persistente
    async with client.aio.live.connect(model=agent_model, config=config) as session:
        while True:
            cmd = input("Premi Invio per parlare (o digita 'q' per uscire): ")
            if cmd.lower() == "q":
                print("Uscita...")
                break
            
            print("In ascolto... (Premi di nuovo Invio per interrompere la registrazione)")
            recorded_chunks = []

            # Registrazione
            with sd.InputStream(
                samplerate=in_samplerate,
                channels=1,
                dtype='int16',
                callback=lambda indata, frames, time, status: recorded_chunks.append(indata.copy())
            ):
                input()

            if not recorded_chunks:
                continue

            recording = np.concatenate(recorded_chunks, axis=0)
            
            # La Live API gestisce molto bene l'audio PCM grezzo
            pcm_data = recording.tobytes()
            # Specifichiamo il sample rate dinamico derivato dal microfono
            mime_type = f"audio/pcm;rate={int(in_samplerate)}"

            print("L'assistente sta elaborando...")
            
            # 2. Inviamo l'audio tramite WebSocket
            await session.send_realtime_input(
                audio=types.Blob(data=pcm_data, mime_type=mime_type)
            )
            # Segnaliamo la fine del turno per evitare latenze nell'attesa del VAD (Voice Activity Detection)
            await session.send_client_content(turn_complete=True)

            # 3. Estraiamo testo e audio dallo stream di risposta
            audio_data = bytearray()
            text_response = ""
            
            async for response in session.receive():
                if response.server_content and response.server_content.model_turn:
                    for part in response.server_content.model_turn.parts:
                        if part.text:
                            text_response += part.text
                        if part.inline_data:
                            audio_data.extend(part.inline_data.data)
                
                # Se il turno è completato, interrompiamo l'ascolto per questo messaggio
                if response.server_content and response.server_content.turn_complete:
                    break

            print(f"Assistente: {text_response.strip()}")

            # 4. Riproduciamo l'audio generato da Gemini (PCM a 24000 Hz)
            if audio_data:
                print("Riproduzione vocale in corso...")
                audio_np = np.frombuffer(audio_data, dtype=np.int16)
                sd.play(audio_np, samplerate=24000)
                sd.wait()
            else:
                print("(Nessuna risposta vocale ricevuta.)")
            
            print("------------------------------------------------")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgramma terminato.")