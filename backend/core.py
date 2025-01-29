from pydantic_ai import Agent,tools, RunContext
from dataclasses import dataclass
from backend.prompt import validator_prompt
from duckduckgo_search import DDGS
from chromadb.utils.embedding_functions.ollama_embedding_function import OllamaEmbeddingFunction
import chromadb
import os
from dotenv import load_dotenv
load_dotenv()


@dataclass
class Deps():
    chroma_client: chromadb.HttpClient
    

agent = Agent('ollama:llama3.2',system_prompt=validator_prompt)
ollama_ef = OllamaEmbeddingFunction(url="http://localhost:11434/api/embeddings", model_name="nomic-embed-text")

def chroma_connect():
    db_url = os.getenv("CHROMA_URL")
    db_port = db_url.split(":")[1]
    try:
        client = chromadb.HttpClient(host='localhost',port=db_port)
        return client
    except Exception as e:
        print(f"Error connecting to Chroma: {str(e)}")


@agent.tool
def search_in_browser(search_query:str)-> str:
    """browser extension to search from internet using search query
    Args:
        search_query (str): search query to be searched in browser 
    """
    result = DDGS().text(search_query,max_results=5)
    return result

@agent.tool
def search_in_embed(search_query:str,ctx:RunContext[Deps]) -> list[str]:
    """search in embedded reddit posts data
    Args:
        search_query (str): search query to be searched in embedded reddit posts data
    """
    
    collection = ctx.deps.chroma_client.get_collection(name='reddit_data',embedding_function=ollama_ef)
    if collection is None:
        return "Collection not found"
    result = collection.query(
        query_texts = [search_query],
        n_results = 10
    )
    return result


