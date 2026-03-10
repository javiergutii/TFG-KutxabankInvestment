"""
Generador de resúmenes usando Ollama
"""
import requests
import json
from typing import Optional

from config import OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_TIMEOUT


class OllamaSummarizer:
    """
    Genera resúmenes de texto usando Ollama
    """
    
    def __init__(self):
        """
        Inicializa el generador de resúmenes
        """
        self.host = OLLAMA_HOST
        self.model = OLLAMA_MODEL
        self.timeout = OLLAMA_TIMEOUT
        
        print(f"🤖 Inicializando Ollama Summarizer")
        print(f"   Host: {self.host}")
        print(f"   Modelo: {self.model}")
        
        # Verificar que Ollama esté disponible
        self._check_ollama_availability()
    
    def _check_ollama_availability(self):
        """
        Verifica que Ollama esté disponible y el modelo descargado
        """
        try:
            response = requests.get(
                f"{self.host}/api/tags",
                timeout=10
            )
            response.raise_for_status()
            
            models = response.json().get('models', [])
            model_names = [m.get('name', '').split(':')[0] for m in models]
            
            if self.model.split(':')[0] not in model_names:
                print(f"   ⚠️  Modelo '{self.model}' no encontrado en Ollama")
                print(f"   📋 Modelos disponibles: {', '.join(model_names)}")
                print(f"   💡 Para descargar el modelo, ejecuta: ollama pull {self.model}")
            else:
                print(f"   ✅ Ollama disponible con modelo '{self.model}'")
                
        except requests.exceptions.RequestException as e:
            print(f"   ⚠️  No se pudo conectar a Ollama: {e}")
            print(f"   💡 Asegúrate de que Ollama esté ejecutándose")
    
    def _fix_encoding(self, text: str) -> str:
        """
        Corrige problemas de encoding comunes en texto generado por Ollama
        """
        # Mapeo de caracteres mal codificados a correctos
        replacements = {
            '├│': 'ó',
            '├í': 'á',
            '├®': 'é',
            '├¡': 'í',
            '├║': 'ú',
            '├▒': 'ñ',
            '┬░': '°',
            '├Ç': 'Á',
            '├ë': 'É',
            '├ô': 'Ó',
            '├Ü': 'Ú',
            '├æ': 'Ñ',
            '┬¿': '¿',
            '┬í': '¡',
            '├¿': 'ü',
            '├ô': 'Ô',
        }
        
        for bad, good in replacements.items():
            text = text.replace(bad, good)
        
        return text
    
    def generate_summary(
        self,
        text: str,
        empresa: str,
        max_tokens: int = 1200
    ) -> Optional[str]:
        """
        Genera un resumen del texto
        """
        if not text or len(text.strip()) < 100:
            print(f"   ⚠️  Texto demasiado corto para resumir")
            return None
        
        # Crear prompt mejorado
        prompt = self._create_summary_prompt(text, empresa)
        
        try:
            response = requests.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.15,
                        "num_predict": max_tokens,
                        "top_p": 0.9,
                        "num_ctx": 32768,
                    }
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            summary = result.get('response', '').strip()
            
            if summary:
                # Corregir encoding
                summary = self._fix_encoding(summary)
                return summary
            else:
                print(f"   ⚠️  Respuesta vacía de Ollama")
                return None
                
        except requests.exceptions.Timeout:
            print(f"   ⏱️  Timeout esperando respuesta de Ollama ({self.timeout}s)")
            return None
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Error llamando a Ollama: {e}")
            return None
        except Exception as e:
            print(f"   ❌ Error inesperado generando resumen: {e}")
            return None
    
    def _create_summary_prompt(self, text: str, empresa: str) -> str:
        
        prompt = f"""
            Eres un analista financiero senior. Tu única tarea es extraer y resumir información \
            de la siguiente transcripción de {empresa}. 

            REGLA ABSOLUTA: Solo puedes incluir datos que aparezcan literalmente en el texto. \
            Si un dato no está en la transcripción, escribe "no mencionado". \
            Nunca calcules, interpoloes ni infergas cifras. Ante la duda, "no mencionado".

            TRANSCRIPCIÓN:
            {text}

            INSTRUCCIONES:

            1. ESTRUCTURA - usa estas secciones:
            - Resultados Financieros Consolidados
            - Métricas por Geografía (solo incluye las geografías y métricas mencionadas explícitamente)
            - Transacciones y Movimientos Estratégicos
            - Guidance y Proyecciones
            - Otros puntos relevantes

            2. FORMATO:
            - Profesional y conciso
            - Bullet points dentro de cada sección
            - Solo español, sin caracteres corruptos
            - Sin negritas ni asteriscos
            - Máximo 1000 palabras

            3. CUANDO NO ENCUENTRES UN DATO:
            - No lo omitas silenciosamente
            - Escribe explícitamente "no mencionado en la transcripción"
            - Nunca uses cifras de tu conocimiento previo sobre {empresa}
            """

        return prompt
    
    def generate_answer(
        self,
        question: str,
        context_chunks: list,
        empresa: Optional[str] = None,
        max_tokens: int = 1200
    ) -> Optional[str]:
        """
        Genera una respuesta basada en chunks de contexto (para RAG)
        """
        if not context_chunks:
            return "No se encontró información relevante para responder a tu pregunta."
        
        # Combinar chunks en contexto
        context = "\n\n".join([
            f"[Fragmento {i+1}]: {chunk}"
            for i, chunk in enumerate(context_chunks[:5])
        ])
        
        # Crear prompt para Q&A
        prompt = self._create_qa_prompt(question, context, empresa)
        
        try:
            response = requests.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.15,
                        "num_predict": max_tokens,
                        "top_p": 0.9,
                        "num_ctx": 32768,
                    }
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            answer = result.get('response', '').strip()
            
            if answer:
                # Corregir encoding
                answer = self._fix_encoding(answer)
                return answer
            else:
                return None
                
        except Exception as e:
            print(f"   ❌ Error generando respuesta: {e}")
            return None
    
    def _create_qa_prompt(
        self,
        question: str,
        context: str,
        empresa: Optional[str] = None
    ) -> str:
        """
        Prompt para responder preguntas con contexto
        """
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