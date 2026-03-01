import os
from config import logger
from langchain_core.language_models import BaseLanguageModel

def create_groq_model(
        model_name: str = "llama-3.1-70b-versatile", 
        temperature: float = 0.8
    ) -> BaseLanguageModel:
    
    from langchain_groq import ChatGroq

    try:
        return ChatGroq(model_name=model_name, 
                        temperature=temperature, 
                        max_tokens=2048)
        
    except Exception as e:
        raise Exception(f"Error: Failed to initialize Groq model: {str(e)}.")
    
def create_ollama_model(
        base_url: str = "http://localhost:11434", 
        model_name: str = "llama3.1:70b", 
        temperature: float = 0.6
    ) -> BaseLanguageModel:
    
    from langchain_ollama import ChatOllama
    
    try:
        model = ChatOllama(
            base_url=base_url,
            model=model_name,
            keep_alive="1h",
            num_predict=4096,
            temperature=temperature,
            format="json",
        )
        model.generate("") #preload the model
    except Exception as e:
        raise Exception(f"Error: Failed to initialize Ollama model: {str(e)}")
    
    return model
    
def create_openai_model(
        model_name: str = "gpt-4o", 
        temperature: float = 0.8
    ) -> BaseLanguageModel:
    
    from langchain_openai import ChatOpenAI
    
    try:
        return ChatOpenAI(model_name=model_name, temperature=temperature)
        
    except Exception as e:
        raise Exception(f"Error: Failed to initialize Openai model: {str(e)}")

def create_mistral_model(
        model_name: str = "mistral-large-latest", 
        temperature: float = 0.8
    ) -> BaseLanguageModel:
    
    from langchain_mistralai.chat_models import ChatMistralAI
    
    try:
        return ChatMistralAI(model_name=model_name, temperature=temperature)
    except Exception as e:
        raise Exception(f"Error: Failed to initialize Openai model: {str(e)}")

def create_google_model(
        model_name: str = "gemini-1.5-pro", 
        temperature: float = 0.9
    ) -> BaseLanguageModel:
    
    from langchain_google_genai import ChatGoogleGenerativeAI
    
    try:
        return ChatGoogleGenerativeAI(model=model_name, temperature=temperature)
    except Exception as e:
        raise Exception(f"Error: Failed to initialize Google model: {str(e)}")
    
def create_anthropic_model(
        model_name: str = "claude-3-7-sonnet-latest", 
        temperature: float = 0.8
    ) -> BaseLanguageModel:
    
    from langchain_anthropic import ChatAnthropic
    
    try:
        return ChatAnthropic(
            model_name=model_name, 
            temperature=temperature,
            max_retries=3
        )
    except Exception as e:
        raise Exception(f"Error: Failed to initialize Anthropic model: {str(e)}")

def create_grok_model(
        model_name: str = "grok-beta",
        base_url: str = "https://api.x.ai/v1",
        temperature: float = 0.8
    ) -> BaseLanguageModel:
    
    from langchain_openai import ChatOpenAI
    
    try:
        grok_api_key = os.getenv("GROK_API_KEY")
        return ChatOpenAI(
            api_key=grok_api_key, 
            base_url=base_url, 
            model_name=model_name, 
            temperature=temperature,
            max_retries=3
        )
        
    except Exception as e:
        raise Exception(f"Error: Failed to initialize Grok model: {str(e)}")

def create_deepseek_model(
        model_name: str = "deepseek-chat",
        base_url: str = "https://api.deepseek.com",
        temperature: float = 1
    ) -> BaseLanguageModel:
    
    from langchain_openai import ChatOpenAI
    
    try:
        deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        return ChatOpenAI(
            api_key=deepseek_api_key, 
            base_url=base_url, 
            model_name=model_name, 
            temperature=temperature,
            max_retries=3
        )
        
    except Exception as e:
        raise Exception(f"Error: Failed to initialize Grok model: {str(e)}")