import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    llm = ChatGoogleGenerativeAI(model='gemini-2.0-flash', temperature=0.3, timeout=10, max_retries=1)
    result = llm.invoke('Say hello in one word')
    print('LLM OK:', result.content)
except Exception as e:
    print('LLM ERROR:', type(e).__name__, str(e)[:200])
