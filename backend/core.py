import os
from fastapi import HTTPException
from pydantic_ai import Agent,tools, RunContext
from pydantic import BaseModel
from dataclasses import dataclass
from pydantic_ai.usage import Usage
import logfire
from chromadb.utils.embedding_functions.ollama_embedding_function import OllamaEmbeddingFunction
from duckduckgo_search import DDGS
import chromadb
from dotenv import load_dotenv
from crawl4ai import *
import asyncio
import uuid
import json
from pymongo import MongoClient
from backend.prompt import validator_prompt,test_prompt,guard_prompt
from typing import Optional,List
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart
)
from brave_search_python_client import BraveSearch


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

class Part(BaseModel):
    content: str
    dynamic_ref: Optional[str] = None
    part_kind: str
    tool_name: Optional[str] = None
    timestamp: Optional[str] = None

class ChatModel(BaseModel):
    parts: List[Part]
    kind: str
    timestamp: Optional[str] = None

def EvalModel(BaseModel):
    relevant: bool


agent = Agent('groq:deepseek-r1-distill-llama-70b',system_prompt=test_prompt, deps_type=Deps,retries=5)
ollama_ef = OllamaEmbeddingFunction(url="http://localhost:11434/api/embeddings", model_name="nomic-embed-text")

def mongo_connect():
    mongo_url = os.getenv("MONGO_URL")
    client = MongoClient(mongo_url)
    db = client.pyd_chat_history
    return db.chat_history


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

def create_session_id():
    return str(uuid.uuid4())

# Fetch session history from MongoDB
def clean_part_data(part_data, expected_fields):
    return {key: value for key, value in part_data.items() if key in expected_fields}

def fetch_session_history(session_id,new_session) -> list:
    collection = mongo_connect()
    session = collection.find_one({"session_id": session_id})

    if session is None and new_session is None:
        return None
    elif session is None and new_session is True:
        collection.insert_one({"session_id": session_id, "chat_history": []})
        return []

    chat_history = []
    session['chat_history'] = session['chat_history'][:10] 
    for chat in session.get("chat_history", []):
        parts = []
        for p in chat["parts"]:
            if p["part_kind"] == "text":
                parts.append(TextPart(**clean_part_data(p, TextPart.__annotations__)))
            else:
                parts.append(UserPromptPart(**clean_part_data(p, UserPromptPart.__annotations__)))

        if chat["kind"] == "request":
            chat_history.append(ModelRequest(parts))
        elif chat["kind"] == "response":
            chat_history.append(ModelResponse(parts, chat["timestamp"]))
    
    return chat_history


def update_chat_history(session_id, chat_history):
    collection = mongo_connect()
    data = json.loads(chat_history)

    # Ensure compatibility with Pydantic models
    # chat_models = [ChatModel(**item) for item in data ]
    filtered_data = [
    item for item in data
    if all(part['part_kind'] not in ['tool-call', 'tool-return'] for part in item.get('parts', []))
    ]
    chat_models = [ChatModel(**item) for item in filtered_data]
    
    
    # Fetch current chat history
    existing_data = collection.find_one({"session_id": session_id}).get("chat_history", [])
    
    # Append new messages
    for model in chat_models:
        existing_data.append(model.model_dump())

    # Update MongoDB
    collection.update_one(
        {"session_id": session_id},
        {"$set": {"chat_history": existing_data}}
    )
   

@agent.tool_plain
async def search_in_browser(search_query:str)-> list[str]:
    """browser extension to search from internet using search query
    Args:
        search_query (str): search query to be searched in browser 
    """
    result = DDGS().text(search_query,max_results=5)
    # urls = [res['href'] for res in result]
    # web_data = [ await webcontent(url) for url in urls]
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


async def main(query:str, session_id):
    client = chroma_connect()
    new_session = None
    if session_id == "new":
        session_id = create_session_id()
        new_session = True
          
    chat_history = fetch_session_history(session_id,new_session)
    if chat_history is None:
        raise HTTPException(status_code=404, detail="Session not found")
    deps = Deps(chroma_client=client)
    result = await agent.run(query, deps=deps,message_history=chat_history)
    update_chat_history(session_id, result.new_messages_json())    
    return {'session_id': session_id, 'message': result.data}




