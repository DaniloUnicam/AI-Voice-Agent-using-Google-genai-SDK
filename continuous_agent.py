import sounddevice as sd
import numpy as np
from google import genai
from google.genai import types # type: ignore
import asyncio
from dotenv import load_dotenv
import sys
import threading

load_dotenv()
# Tested Agent models: gemini-3.1-flash-live-preview
class ContinuousVoiceAgent:
    def __init__(self, model="gemini-2.5-flash-native-audio-preview-12-2025"):
        self.client = genai.Client()
        self.model = model
        # La Live API supporta nativamente l'audio in ingresso a 16000 Hz
        self.in_samplerate = 16000
        # Frequenza di campionamento attesa per l'output da Gemini
        self.out_samplerate = 24000
        
        self.audio_in_queue = None
        self.audio_out_queue = None
        self.loop = None
        
        self.is_running = False
        
        # Buffer persistente per l'audio in uscita
        self.audio_buffer = bytearray()
        self.buffer_lock = threading.Lock()
        
        self.agent_instructions = (
            "Sei un assistente vocale in tempo reale impegnato in una telefonata. "
            "Rispondi in modo conciso, naturale e conversazionale. "
            "Non usare formattazione markdown (come asterischi o grassetti) perché le tue "
            "risposte verranno riprodotte vocalmente. Adattati alla lingua dell'utente."
        )

    def _audio_input_callback(self, indata, frames, cb_time, status):
        """Callback invocata da sounddevice ad ogni nuovo chunk audio in input."""
        if status:
            print(f"Status microfono: {status}", file=sys.stderr)

        # Invia costantemente l'audio senza Noise Gate:
        # La VAD (Voice Activity Detection) nativa di Gemini Live API rileva automaticamente pause e parlato.
        self.loop.call_soon_threadsafe(self.audio_in_queue.put_nowait, indata.copy())

    def _audio_output_callback(self, outdata, frames, time_info, status):
        """Callback invocata da sounddevice per richiedere audio da riprodurre."""
        if status:
            print(f"Status speaker: {status}", file=sys.stderr)
            
        bytes_needed = frames * 2 # 2 byte per sample (int16)
        
        with self.buffer_lock:
            available_bytes = len(self.audio_buffer)
            
            if available_bytes >= bytes_needed:
                chunk = self.audio_buffer[:bytes_needed]
                del self.audio_buffer[:bytes_needed]
                outdata[:] = np.frombuffer(chunk, dtype=np.int16).reshape(-1, 1)
            elif available_bytes > 0:
                chunk = self.audio_buffer[:available_bytes]
                del self.audio_buffer[:]
                padding = bytes_needed - available_bytes
                chunk += b'\x00' * padding
                outdata[:] = np.frombuffer(chunk, dtype=np.int16).reshape(-1, 1)
            else:
                outdata[:] = np.zeros((frames, 1), dtype=np.int16)

    async def _send_audio_loop(self, session):
        # Task che preleva costantemente l'audio dal microfono e lo invia via WebSocket
        mime_type = f"audio/pcm;rate={self.in_samplerate}"
        
        while self.is_running:
            try:
                # Preleviamo audio dalla coda in modo continuo
                data = await self.audio_in_queue.get()
                pcm_data = data.tobytes()
                
                await session.send_realtime_input(
                    audio=types.Blob(data=pcm_data, mime_type=mime_type)
                )
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"\nErrore nell'invio audio: {e}")
                break

    async def _receive_loop(self, session):
        """Task che riceve i pacchetti (testo e audio) e li smista."""
        is_printing_ai_text = False
        try:
            async for response in session.receive():
                if response.server_content:
                    content = response.server_content
                    
                    # --- GESTIONE NATIVA DELL'INTERRUZIONE (BARGE-IN) ---
                    if getattr(content, "interrupted", False):
                        # L'utente ha iniziato a parlare mentre l'agente parlava: puliamo i buffer!
                        with self.buffer_lock:
                            self.audio_buffer.clear()
                        while not self.audio_out_queue.empty():
                            try:
                                self.audio_out_queue.get_nowait()
                            except asyncio.QueueEmpty:
                                break
                                
                        sys.stdout.write("\n\033[K[INTERRUZIONE] L'utente sta parlando...\n")
                        sys.stdout.flush()
                        is_printing_ai_text = False
                        continue

                    # 1. Trascrizione dell'utente (Speech-to-Text nativo di Gemini)
                    if getattr(content, "input_transcription", None):
                        sys.stdout.write(f"\r\033[K[TU]: {content.input_transcription.text}\n")
                        sys.stdout.flush()

                    # 2. Trascrizione AI
                    if getattr(content, "output_transcription", None):
                        prefix = "\r\033[K[GEMINI]: " if not is_printing_ai_text else ""
                        sys.stdout.write(f"{prefix}{content.output_transcription.text}")
                        sys.stdout.flush()
                        is_printing_ai_text = True

                    # 3. Audio dell'assistente
                    if getattr(content, "model_turn", None):
                        for part in content.model_turn.parts:
                            if getattr(part, "inline_data", None):
                                await self.audio_out_queue.put(part.inline_data.data)
                
                # Quando Gemini finisce una frase
                if response.server_content and getattr(response.server_content, "turn_complete", False):
                    if is_printing_ai_text:
                        sys.stdout.write("\n")
                        sys.stdout.flush()
                        is_printing_ai_text = False
                        
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"\nErrore nella ricezione: {e}")

    async def _play_audio_loop(self):
        """Task che estrae l'audio dalla coda asincrona e lo passa al buffer condiviso."""
        while self.is_running:
            try:
                chunk = await asyncio.wait_for(self.audio_out_queue.get(), timeout=0.1)
                with self.buffer_lock:
                    self.audio_buffer.extend(chunk)
            except asyncio.TimeoutError:
                pass
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"\nErrore nella gestione buffer audio: {e}")
                break

    async def start(self):
        """Avvia e coordina l'intera telefonata."""
        self.loop = asyncio.get_running_loop()
        self.audio_in_queue = asyncio.Queue()
        self.audio_out_queue = asyncio.Queue()

        self.is_running = True
        print("\n--- Chiamata continua in corso (Gemini Live API) ---")
        print("Il microfono è sempre attivo. Inizia pure a parlare!")
        print("L'agente gestisce nativamente le pause e le interruzioni.")
        print("Premi Ctrl+C nel terminale per riagganciare.\n")
        
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=types.Content(
                parts=[types.Part.from_text(text=self.agent_instructions)]
            ),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig()
        )

        try:
            async with self.client.aio.live.connect(model=self.model, config=config) as session:
                # Apriamo il canale in ascolto permanente sul microfono
                in_blocksize = int(self.in_samplerate * 0.1)
                
                # Stream di ingresso
                in_stream = sd.InputStream(
                    samplerate=self.in_samplerate,
                    channels=1,
                    dtype='int16',
                    blocksize=in_blocksize,
                    callback=self._audio_input_callback
                )
                
                # Stream di uscita
                out_blocksize = int(self.out_samplerate * 0.1)
                out_stream = sd.OutputStream(
                    samplerate=self.out_samplerate,
                    channels=1,
                    dtype='int16',
                    blocksize=out_blocksize,
                    callback=self._audio_output_callback
                )
                
                with in_stream, out_stream:
                    # Eseguiamo tutti i task in parallelo
                    await asyncio.gather(
                        self._send_audio_loop(session),
                        self._receive_loop(session),
                        self._play_audio_loop()
                    )
        except asyncio.CancelledError:
            pass
        finally:
            self.is_running = False
            sd.stop()
            print("\nChiamata terminata.")

if __name__ == "__main__":
    agent = ContinuousVoiceAgent()
    try:
        asyncio.run(agent.start())
    except KeyboardInterrupt:
        print("\nChiusura forzata dall'utente.")