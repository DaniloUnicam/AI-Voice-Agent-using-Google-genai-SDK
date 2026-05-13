import speech_recognition as sr
import threading

class MessageTranscriber:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.stop_listening = None

    def _callback(self, recognizer, audio):
        """
        Viene chiamata automaticamente ogni volta
        che viene rilevata una frase.
        """
        try:
            text = recognizer.recognize_google(audio, language="it-IT")
            print(text, end=" ", flush=True)

        except sr.UnknownValueError:
            pass

        except sr.RequestError as e:
            print(f"\nErrore API speech recognition: {e}")

    def transcribe_live(self):
        """
        Avvia la trascrizione live finché
        l'utente non preme Enter.
        """

        with self.microphone as source:
            print("Calibrazione microfono...")
            self.recognizer.adjust_for_ambient_noise(source)

        input("\nPremi Enter per iniziare...")

        print("Sto ascoltando... Premi Enter per fermare.\n")

        self.stop_listening = self.recognizer.listen_in_background(
            self.microphone,
            self._callback
        )

        input()

        self.stop_listening(wait_for_stop=False)

        print("\n\nTrascrizione terminata.")


if __name__ == "__main__":
    transcriber = MessageTranscriber()
    transcriber.transcribe_live()