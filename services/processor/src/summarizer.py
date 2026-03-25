"""
Generador de resúmenes usando Groq (llama-3.3-70b)
"""
from pathlib import Path
from typing import Optional
from groq import Groq

from config import GROQ_API_KEY, GROQ_MODEL, GROQ_MAX_TOKENS


class GroqSummarizer:
    """
    Genera resúmenes de texto usando Groq API
    """

    def __init__(self):
        print(f"Inicializando Groq Summarizer")
        print(f"   Modelo: {GROQ_MODEL}")

        if not GROQ_API_KEY:
            raise ValueError("❌ GROQ_API_KEY no configurada. Añádela como variable de entorno.")

        self.client = Groq(api_key=GROQ_API_KEY)
        self.model = GROQ_MODEL
        self.max_tokens = GROQ_MAX_TOKENS

        self._check_availability()

    def _check_availability(self):
        """
        Verifica que la API key sea válida haciendo una llamada mínima
        """
        try:
            self.client.models.list()
            print(f"   Groq disponible con modelo '{self.model}'")
        except Exception as e:
            print(f"   ⚠️  No se pudo conectar a Groq: {e}")
            print(f"   💡 Verifica que GROQ_API_KEY sea correcta")

    def generate_summary(
        self,
        text: str,
        empresa: str,
    ) -> Optional[str]:
        """
        Genera un resumen prospectivo del texto
        """
        if not text or len(text.strip()) < 100:
            print(f"   ⚠️  Texto demasiado corto para resumir")
            return None

        prompt = self._create_summary_prompt(text, empresa)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.15,
                max_tokens=self.max_tokens,
            )
            summary = response.choices[0].message.content.strip()

            if summary:
                return summary
            else:
                print(f"   ⚠️  Respuesta vacía de Groq")
                return None

        except Exception as e:
            print(f"   ❌ Error llamando a Groq: {e}")
            return None

    def _create_summary_prompt(self, text: str, empresa: str) -> str:
        prompt_path = Path(__file__).parent / "prompt_earnings_calls.txt"

        try:
            template = prompt_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise FileNotFoundError(
                f"❌ No se encontró el archivo de prompt en '{prompt_path}'. "
                "Asegúrate de que 'prompt_earnings_calls.txt' está en el mismo directorio que summarizer.py."
            )

        return template.replace("{text}", text).replace("{empresa}", empresa)

    def generate_answer(
        self,
        question: str,
        transcript: str,
        empresa: Optional[str] = None,
    ) -> Optional[str]:
        """
        Genera una respuesta basada en la transcripción completa
        """
        if not transcript or len(transcript.strip()) < 100:
            return "No se encontró transcripción para responder a tu pregunta."

        prompt = self._create_qa_prompt(question, transcript, empresa)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.15,
                max_tokens=self.max_tokens,
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"   ❌ Error generando respuesta: {e}")
            return None
    def _create_qa_prompt(
        self,
        question: str,
        transcript: str,
        empresa: Optional[str] = None
    ) -> str:
        empresa_text = f" de {empresa}" if empresa else ""
 
        prompt_path = Path(__file__).parent / "prompt_qa.txt"
 
        try:
            template = prompt_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise FileNotFoundError(
                f"❌ No se encontró el archivo de prompt en '{prompt_path}'. "
                "Asegúrate de que 'prompt_qa.txt' está en el mismo directorio que summarizer.py."
            )
 
        return (
            template
            .replace("{empresa_text}", empresa_text)
            .replace("{context}", transcript)
            .replace("{question}", question)
        )