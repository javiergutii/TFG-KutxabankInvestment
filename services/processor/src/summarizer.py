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
            # Verificar endpoint /api/tags
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
    
    def generate_summary(
        self,
        text: str,
        empresa: str,
        max_tokens: int = 800
    ) -> Optional[str]:
        """
        Genera un resumen del texto
        
        Args:
            text: Texto a resumir
            empresa: Nombre de la empresa (para contexto)
            max_tokens: Longitud máxima del resumen
            
        Returns:
            Resumen generado o None si falla
        """
        if not text or len(text.strip()) < 100:
            print(f"   ⚠️  Texto demasiado corto para resumir")
            return None
        
        # Limitar longitud del texto de entrada (Ollama tiene límites de contexto)
        max_input_chars = 15000
        if len(text) > max_input_chars:
            print(f"   ✂️  Texto truncado de {len(text)} a {max_input_chars} caracteres")
            text = text[:max_input_chars] + "..."
        
        # Crear prompt para resumen
        prompt = self._create_summary_prompt(text, empresa)
        
        try:
            # Llamar a Ollama API
            response = requests.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": max_tokens,
                        "top_p": 0.9,
                    }
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            summary = result.get('response', '').strip()
            
            if summary:
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
        """
        Crea el prompt para generar el resumen
        
        Args:
            text: Texto a resumir
            empresa: Nombre de la empresa
            
        Returns:
            Prompt formateado
        """
        prompt = f"""Eres un analista financiero experto. Tu tarea es crear un resumen ejecutivo de la siguiente transcripción de una presentación de resultados de {empresa}.

TRANSCRIPCIÓN:
{text}

INSTRUCCIONES:
1. Crea un resumen estructurado y conciso
2. Incluye los puntos más importantes: resultados financieros, proyecciones, anuncios relevantes
3. Usa lenguaje profesional y claro
4. Organiza la información en secciones lógicas
5. Destaca métricas clave y cifras importantes
6. Escribe en español

RESUMEN EJECUTIVO:"""
        
        return prompt
    
    def generate_answer(
        self,
        question: str,
        context_chunks: list,
        empresa: Optional[str] = None,
        max_tokens: int = 800
    ) -> Optional[str]:
        """
        Genera una respuesta basada en chunks de contexto (para RAG)
        
        Args:
            question: Pregunta del usuario
            context_chunks: Lista de chunks relevantes (texto)
            empresa: Empresa específica (opcional)
            max_tokens: Longitud máxima de la respuesta
            
        Returns:
            Respuesta generada o None si falla
        """
        if not context_chunks:
            return "No se encontró información relevante para responder a tu pregunta."
        
        # Combinar chunks en contexto
        context = "\n\n".join([
            f"[Fragmento {i+1}]: {chunk}"
            for i, chunk in enumerate(context_chunks[:5])  # Limitar a 5 chunks
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
                        "temperature": 0.2,
                        "num_predict": max_tokens,
                        "top_p": 0.9,
                    }
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            answer = result.get('response', '').strip()
            
            return answer if answer else None
                
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
        Crea el prompt para responder preguntas
        
        Args:
            question: Pregunta del usuario
            context: Contexto relevante
            empresa: Empresa específica (opcional)
            
        Returns:
            Prompt formateado
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
4. Responde en español de forma clara y concisa

RESPUESTA:"""
        
        return prompt