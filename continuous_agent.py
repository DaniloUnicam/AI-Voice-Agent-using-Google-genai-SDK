import sounddevice as sd
import numpy as np
from google import genai
from google.genai import types # type: ignore
import asyncio
from dotenv import load_dotenv
import queue
import sys
import os
import argparse

load_dotenv()

class ContinuousVoiceAgent:
    def __init__(self, model="gemini-3.1-flash-live-preview", silence_threshold=None):
        self.client = genai.Client()
        self.model = model
        # Ricava automaticamente la frequenza di campionamento del microfono di sistema
        self.in_samplerate = int(sd.query_devices(kind='input')['default_samplerate'])
        
        # Soglia di volume sotto la quale consideriamo l'audio "silenzio" (es. rumore di fondo)
        env_threshold = os.getenv("SILENCE_THRESHOLD")
        self.silence_threshold = silence_threshold if silence_threshold is not None else (int(env_threshold) if env_threshold else 3000)
        
        # Coda per raccogliere i chunk audio in arrivo dal microfono
        self.audio_in_queue = queue.Queue()
        # Coda per gestire l'audio in risposta da Gemini
        self.audio_out_queue = asyncio.Queue()
        
        self.is_running = False
        self.agent_is_speaking = False
        self.receiving_turn = False
        self.agent_instructions = (
            "Sei un assistente vocale in tempo reale impegnato in una telefonata. "
            "Rispondi in modo conciso, naturale e conversazionale. "
            "Non usare formattazione markdown (come asterischi o grassetti) perché le tue "
            "risposte verranno riprodotte vocalmente. Adattati alla lingua dell'utente."
        )

    def _audio_input_callback(self, indata, frames, time, status):
        """Callback invocata da sounddevice ad ogni nuovo chunk audio in input."""
        if status:
            print(f"Status microfono: {status}", file=sys.stderr)
            
        # Se l'agente sta rispondendo, disattiviamo l'ascolto inviando silenzio assoluto
        if self.agent_is_speaking:
            self.audio_in_queue.put(np.zeros_like(indata))
            return

        # Calcoliamo l'ampiezza massima (volume) del chunk corrente
        volume = np.max(np.abs(indata))
        
        # Noise Gate: se il volume supera la soglia, inviamo l'audio reale
        if volume > self.silence_threshold:
            self.audio_in_queue.put(indata.copy())
        else:
            # Se è sotto la soglia (rumore di fondo), inviamo silenzio assoluto
            # Questo aiuta drasticamente il VAD di Gemini a capire che abbiamo smesso di parlare
            self.audio_in_queue.put(np.zeros_like(indata))

    async def _send_audio_loop(self, session):
        """Task che preleva costantemente l'audio dal microfono e lo invia via WebSocket."""
        mime_type = f"audio/pcm;rate={self.in_samplerate}"
        while self.is_running:
            try:
                # asyncio.to_thread previene il blocco dell'Event Loop principale
                data = await asyncio.to_thread(self.audio_in_queue.get, True, 0.1)
                pcm_data = data.tobytes()
                
                # Inviamo i pacchetti in modo continuo (full-duplex) senza mai chiudere il turno
                await session.send_realtime_input(
                    audio=types.Blob(data=pcm_data, mime_type=mime_type)
                )
            except queue.Empty:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"\nErrore nell'invio audio: {e}")
                break

    async def _receive_loop(self, session):
        """Task che riceve i pacchetti (testo e audio) e li smista."""
        ai_speaking = False
        try:
            async for response in session.receive():
                if response.server_content:
                    content = response.server_content
                    
                    # 1. Trascrizione dell'utente (Speech-to-Text nativo di Gemini)
                    if getattr(content, "input_transcription", None):
                        print(f"\n[TU]: {content.input_transcription.text}")

                    # 2. Testo e audio dell'assistente
                    if content.model_turn:
                        self.receiving_turn = True
                        self.agent_is_speaking = True
                        for part in content.model_turn.parts:
                            if part.text:
                                if not ai_speaking:
                                    print("[GEMINI]: ", end="", flush=True)
                                    ai_speaking = True
                                print(part.text, end="", flush=True)
                            if part.inline_data:
                                await self.audio_out_queue.put(part.inline_data.data)
                
                # Quando Gemini finisce una frase, andiamo a capo nella console
                if response.server_content and response.server_content.turn_complete:
                    print("\n")
                    ai_speaking = False
                    self.receiving_turn = False
                    if self.audio_out_queue.empty():
                        self.agent_is_speaking = False
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"\nErrore nella ricezione: {e}")

    async def _play_audio_loop(self):
        """Task che estrae l'audio, lo accorpa per non farlo saltare e lo riproduce."""
        while self.is_running:
            try:
                # Aspettiamo il primo chunk audio utile
                chunk = await asyncio.wait_for(self.audio_out_queue.get(), timeout=0.1)
                audio_data = bytearray(chunk)
                
                # Piccolo buffer per accumulare chunk adiacenti ed evitare "scatti" tra le parole
                await asyncio.sleep(0.2)
                while not self.audio_out_queue.empty():
                    audio_data.extend(self.audio_out_queue.get_nowait())
                
                if audio_data:
                    audio_np = np.frombuffer(audio_data, dtype=np.int16)
                    
                    # Riproduciamo l'audio asincronamente. Gemini usa PCM a 24000 Hz.
                    sd.play(audio_np, samplerate=24000)
                    
                    # Calcoliamo la durata matematica del chunk audio per metterci in pausa 
                    # in modo asincrono, in modo da non bloccare la ricezione dal websocket
                    duration = len(audio_np) / 24000.0
                    
                    # AGGIUNTA DEL TEMPO EXTRA: attendiamo la durata dell'audio + 0.5 secondi di sicurezza.
                    # Questo evita categoricamente che l'audio venga "tagliato" dai loop successivi.
                    await asyncio.sleep(duration + 0.5)
                    
                    # Se la coda audio è vuota e non stiamo più ricevendo dati, l'agente ha finito
                    if self.audio_out_queue.empty() and not self.receiving_turn:
                        self.agent_is_speaking = False

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"\nErrore nella riproduzione audio: {e}")
                break

    async def start(self):
        """Avvia e coordina l'intera telefonata."""
        self.is_running = True
        print("\n--- Chiamata continua in corso (Gemini Live API) ---")
        print("Il microfono è sempre attivo. Inizia pure a parlare!")
        print("Premi Ctrl+C nel terminale per riagganciare.\n")
        
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=types.Content(
                parts=[types.Part.from_text(text=self.agent_instructions)]
            ),
            input_audio_transcription=types.AudioTranscriptionConfig()
        )

        try:
            async with self.client.aio.live.connect(model=self.model, config=config) as session:
                # Apriamo il canale in ascolto permanente sul microfono
                with sd.InputStream(
                    samplerate=self.in_samplerate,
                    channels=1,
                    dtype='int16',
                    callback=self._audio_input_callback
                ):
                    # Eseguiamo tutti i task in parallelo senza blocchi reciproci
                    await asyncio.gather(
                        self._send_audio_loop(session),
                        self._receive_loop(session),
                        self._play_audio_loop()
                    )
        except asyncio.CancelledError:
            pass
        finally:
            self.is_running = False
            sd.stop() # Ferma forzatamente l'audio al termine della chiamata
            print("\nChiamata terminata.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Avvia l'agente vocale continuo.")
    parser.add_argument("--threshold", type=int, default=None, 
                        help="Valore per la soglia di silenzio (sovrascrive il .env). Es: --threshold 4000")
    args = parser.parse_args()
    
    agent = ContinuousVoiceAgent(silence_threshold=args.threshold)
    try:
        asyncio.run(agent.start())
    except KeyboardInterrupt:
        print("\nChiusura forzata dall'utente.")