import os
from pydantic_ai import Agent,tools, RunContext
from dataclasses import dataclass
from pydantic_ai.usage import Usage
import logfire
from chromadb.utils.embedding_functions.ollama_embedding_function import OllamaEmbeddingFunction
from duckduckgo_search import DDGS
import chromadb
from dotenv import load_dotenv
from crawl4ai import *
import asyncio
from backend.prompt import validator_prompt
load_dotenv()

def scrubbing_callback(m: logfire.ScrubMatch):
    if (
        m.path == ('attributes', 'tool_responses', 0, 'content', 0)
        and m.pattern_match.group(0) == 'credential'
    ):
        return m.value
logfire.configure(send_to_logfire='if-token-present',scrubbing=logfire.ScrubbingOptions(callback=scrubbing_callback))


@dataclass
class Deps():
    chroma_client: chromadb.HttpClient
    

agent = Agent('google-gla:gemini-1.5-flash',system_prompt=validator_prompt, deps_type=Deps)
ollama_ef = OllamaEmbeddingFunction(url="http://localhost:11434/api/embeddings", model_name="nomic-embed-text")

def chroma_connect():
    db_url = os.getenv("CHROMA_URL")
    db_port = db_url.split(":")[-1]
    try:
        client = chromadb.HttpClient(host='localhost',port=db_port)
        return client
    except Exception as e:
        print(f"Error connecting to Chroma: {str(e)}")

async def webcontent(url: str) -> str:
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url)
        return result.markdown

@agent.tool_plain
def search_in_browser(search_query:str)-> str:
    """browser extension to search from internet using search query
    Args:
        search_query (str): search query to be searched in browser 
    """
    result = DDGS().text(search_query,max_results=5)
    return result

@agent.tool
def search_in_embed(ctx:RunContext[Deps],search_query:str) -> list[str]:
    """search in embedded reddit posts data
    Args:
        search_query (str): search query to be searched in embedded reddit posts data
    """
    collection = ctx.deps.chroma_client.get_collection(name='reddit_data',embedding_function=ollama_ef)
    if collection is None:
        return "Collection not found"
    result = collection.query(
        query_texts = [search_query],
        include=['documents'],
        n_results = 10
    )
    return result


async def main(query:str):
    client = chroma_connect()
    deps = Deps(chroma_client=client)
    result = await agent.run(query, deps=deps)
    return result.data