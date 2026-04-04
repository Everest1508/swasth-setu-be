"""
Symptom Checker Service using Groq API
"""
import logging
import os
import time
from groq import Groq
import httpx

logger = logging.getLogger(__name__)


class SymptomCheckerService:
    """Service for analyzing symptoms using Groq AI"""
    
    @staticmethod
    def analyze_symptoms(symptoms: str, groq_api_key: str, max_retries: int = 3) -> dict:
        """
        Analyze symptoms using Groq API with Llama 3.1 model
        
        Args:
            symptoms: Description of symptoms
            groq_api_key: Groq API key
            max_retries: Maximum number of retry attempts (default: 3)
            
        Returns:
            dict with 'analysis' key on success, or 'error' key on failure
        """
        try:
            if not symptoms or not symptoms.strip():
                return {'error': 'Symptoms description is required'}
            
            if not groq_api_key or not groq_api_key.strip():
                return {'error': 'Groq API key is required'}
            
            # Temporarily remove proxy environment variables if they exist
            # to prevent httpx from trying to use them (httpx 0.28+ doesn't support proxies param)
            original_http_proxy = os.environ.pop('HTTP_PROXY', None)
            original_https_proxy = os.environ.pop('HTTPS_PROXY', None)
            original_http_proxy_lower = os.environ.pop('http_proxy', None)
            original_https_proxy_lower = os.environ.pop('https_proxy', None)
            
            try:
                # Initialize Groq client with increased timeout and retry settings
                # Groq API can sometimes be slow, so we increase timeouts
                client = Groq(
                    api_key=groq_api_key,
                    timeout=30.0,  # 30 seconds total timeout
                    max_retries=2  # Built-in retry mechanism
                )
                
                # Construct prompt for medical analysis
                prompt = f"""You are a medical assistant helping to analyze symptoms. 
Please provide a helpful analysis of the following symptoms:

Symptoms: {symptoms}

Please provide:
1. Possible conditions or causes (with appropriate disclaimers)
2. General recommendations (with emphasis on consulting a healthcare professional)
3. When to seek immediate medical attention
4. General self-care tips if applicable

Important: This is not a substitute for professional medical advice. Always consult with a qualified healthcare provider for proper diagnosis and treatment.

Format your response in clear, easy-to-read markdown format."""

                # Retry logic with exponential backoff
                last_error = None
                for attempt in range(max_retries):
                    try:
                        logger.info(f"Attempting Groq API call (attempt {attempt + 1}/{max_retries})")
                        
                        # Call Groq API
                        chat_completion = client.chat.completions.create(
                            messages=[
                                {
                                    "role": "system",
                                    "content": "You are a helpful medical assistant. Provide clear, informative, and responsible medical guidance. Always emphasize the importance of consulting healthcare professionals."
                                },
                                {
                                    "role": "user",
                                    "content": prompt
                                }
                            ],
                            model="llama-3.1-8b-instant",
                            temperature=0.7,
                            max_tokens=1000,
                        )
                        
                        # Extract response
                        analysis = chat_completion.choices[0].message.content
                        
                        logger.info("Symptom analysis completed successfully")
                        return {'analysis': analysis}
                        
                    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as e:
                        last_error = e
                        error_type = type(e).__name__
                        logger.warning(f"Connection error on attempt {attempt + 1}: {error_type} - {str(e)}")
                        
                        if attempt < max_retries - 1:
                            # Exponential backoff: wait 1s, 2s, 4s
                            wait_time = 2 ** attempt
                            logger.info(f"Retrying in {wait_time} seconds...")
                            time.sleep(wait_time)
                        else:
                            logger.error(f"All {max_retries} attempts failed with connection error")
                            return {'error': 'Unable to connect to the AI service. Please check your internet connection and try again.'}
                    
                    except Exception as e:
                        # For non-connection errors, don't retry
                        last_error = e
                        raise
                
                # If we get here, all retries failed
                if last_error:
                    raise last_error
                    
            finally:
                # Restore proxy environment variables if they existed
                if original_http_proxy:
                    os.environ['HTTP_PROXY'] = original_http_proxy
                if original_https_proxy:
                    os.environ['HTTPS_PROXY'] = original_https_proxy
                if original_http_proxy_lower:
                    os.environ['http_proxy'] = original_http_proxy_lower
                if original_https_proxy_lower:
                    os.environ['https_proxy'] = original_https_proxy_lower
            
        except httpx.ConnectError as e:
            error_message = str(e)
            logger.error(f"Connection error in symptom analysis: {error_message}")
            return {'error': 'Unable to connect to the AI service. Please check your internet connection and try again.'}
        
        except httpx.TimeoutException as e:
            error_message = str(e)
            logger.error(f"Timeout error in symptom analysis: {error_message}")
            return {'error': 'The AI service took too long to respond. Please try again.'}
        
        except Exception as e:
            error_message = str(e)
            error_type = type(e).__name__
            logger.error(f"Error in symptom analysis ({error_type}): {error_message}")
            
            # Provide user-friendly error messages
            if "api_key" in error_message.lower() or "authentication" in error_message.lower() or "401" in error_message:
                return {'error': 'Invalid Groq API key. Please check your API key and try again.'}
            elif "rate limit" in error_message.lower() or "quota" in error_message.lower() or "429" in error_message:
                return {'error': 'API rate limit exceeded. Please try again later.'}
            elif "model" in error_message.lower() or "404" in error_message:
                return {'error': 'Model unavailable. Please try again later.'}
            elif "connection" in error_message.lower() or "connect" in error_message.lower():
                return {'error': 'Unable to connect to the AI service. Please check your internet connection and try again.'}
            else:
                return {'error': f'An error occurred while analyzing symptoms: {error_message}'}

