"""
Generador de resúmenes usando Groq (llama-3.3-70b)
"""
from typing import Optional
from groq import Groq

from config import GROQ_API_KEY, GROQ_MODEL, GROQ_MAX_TOKENS


class GroqSummarizer:
    """
    Genera resúmenes de texto usando Groq API
    """

    def __init__(self):
        print(f"🤖 Inicializando Groq Summarizer")
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
            print(f"   ✅ Groq disponible con modelo '{self.model}'")
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

        prompt = f"""Eres un analista de inteligencia prospectiva especializado en conferencias de resultados corporativos. Tu único objetivo es extraer lo que se dice sobre el FUTURO: perspectivas, tendencias, riesgos y preocupaciones. No resumes el pasado; identificas señales hacia adelante.

TRANSCRIPCIÓN:
{text}

EMPRESA: {empresa}

---

SECCIÓN 1 — PERSPECTIVAS DE LA COMPAÑÍA

Extrae únicamente declaraciones explícitas sobre el futuro de la compañía: guidance, objetivos, planes estratégicos, inversiones previstas, cambios de modelo de negocio, expansión geográfica, lanzamientos de productos, M&A, etc.

- Solo incluye lo que aparezca literalmente en la transcripción.
- ANTES DE ESCRIBIR CUALQUIER DATO: localiza la frase exacta en la transcripción. Si no puedes citar textualmente de dónde viene, NO lo incluyas y escribe "no mencionado". Esto aplica especialmente a cifras y porcentajes.
- Si no se menciona guidance o proyecciones concretas, escribe: "no se proporcionó guidance en esta conferencia".
- Formato: bullet points con la métrica o tema, el horizonte temporal si se menciona, y la cifra o dirección indicada.

---

SECCIÓN 2 — PERSPECTIVAS DEL SECTOR

Extrae lo que la dirección dice sobre el entorno macroeconómico, la industria, la competencia, los cambios regulatorios o tecnológicos que se esperan. Solo lo que ellos mencionan; no aportes contexto externo. No añadas observaciones generales del sector que no aparezcan explícitamente en la transcripción.

---

SECCIÓN 3 — INQUIETUDES DE LOS ANALISTAS

Esta es la sección más importante. Sigue estos pasos en orden:

PASO 1: Recorre la transcripción de principio a fin e identifica CADA pregunta formulada por un analista. Haz una lista numerada exhaustiva de todas ellas, indicando el nombre del analista y su banco si aparecen en la transcripción.

PASO 2: Con esa lista, responde:

a) TEMAS MÁS REPETIDOS: Agrupa las preguntas por tema e indica cuántas preguntas corresponden a cada tema y qué analistas las formularon. Ordena por frecuencia descendente.

b) PREOCUPACIONES PRINCIPALES: ¿Qué subyace en las preguntas? Identifica la inquietud real detrás de cada bloque temático (ej: si varios preguntan por el capex, la inquietud real puede ser la presión sobre el flujo de caja libre).

c) PREGUNTAS SIN RESPUESTA CLARA: Señala preguntas donde la dirección esquivó, respondió de forma vaga, redirigió, o dijo explícitamente que no puede dar detalles hasta completar la revisión estratégica. Para cada una, indica textualmente qué respondió la dirección.

---

REGLAS ABSOLUTAS:
- Nada de datos históricos salvo que sirvan de base para una proyección explícita.
- Si algo no aparece en la transcripción, escribe "no mencionado".
- Solo español. Sin negritas, sin asteriscos.
- Máximo 1200 palabras en total."""

        return prompt

    def generate_answer(
        self,
        question: str,
        context_chunks: list,
        empresa: Optional[str] = None,
    ) -> Optional[str]:
        """
        Genera una respuesta basada en chunks de contexto (para RAG)
        """
        if not context_chunks:
            return "No se encontró información relevante para responder a tu pregunta."

        context = "\n\n".join([
            f"[Fragmento {i+1}]: {chunk}"
            for i, chunk in enumerate(context_chunks[:5])
        ])

        prompt = self._create_qa_prompt(question, context, empresa)

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
        context: str,
        empresa: Optional[str] = None
    ) -> str:
        empresa_text = f" de {empresa}" if empresa else ""

        prompt = f"""Eres un asistente experto en análisis de transcripciones financieras{empresa_text}.

CONTEXTO RELEVANTE:
{context}

PREGUNTA: {question}

INSTRUCCIONES:
1. Responde basándote ÚNICAMENTE en el contexto proporcionado
2. Si la información no está en el contexto, indícalo claramente
3. Sé específico y menciona cifras o datos concretos cuando sea posible
4. Cita el número de fragmento de donde sacas la información
5. Responde en español de forma clara y concisa
6. IMPORTANTE: "billion" en inglés = mil millones (no billón español)

RESPUESTA:"""

        return prompt