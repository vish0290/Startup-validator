import os
import uuid
import chromadb
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain.tools.retriever import create_retriever_tool
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.schema import AIMessage, HumanMessage
from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv()

mongo_url = os.getenv("MONGO_URL")
def mongo_connect():
    client = MongoClient(mongo_url)
    db = client.sv_chat
    return db.chat_history

def message_extract(data):
    messages = []
    for msg in data:
        if msg["type"] == "human":
            messages.append(HumanMessage(msg["content"]))
        else:
            messages.append(AIMessage(msg["content"]))
    return messages

def create_session_id():
    return str(uuid.uuid4())

store = {}
def fetch_session_history(session_id) -> BaseChatMessageHistory:
    collection = mongo_connect()
    if collection.find_one({"session_id": session_id}) is None:
        collection.insert_one({"session_id": session_id, "chat_history": f"{ChatMessageHistory()}"})
        store[session_id] = ChatMessageHistory()
    else:
        data = collection.find_one({"session_id": session_id})
        messages = message_extract(data["chat_history"])
        history = ChatMessageHistory()
        history.messages.extend(messages)
        store[session_id] = history
        
    return store[session_id]

def update_memory(store,session_id,collection):
    if session_id in store:
        message_data = [{"type": msg.type, "content": msg.content} for msg in store[session_id].messages]
        collection.update_one({"session_id": session_id}, {"$set": {"chat_history": message_data}})
    else:
        print("Session not found") 

chroma_url = os.getenv("CHROMA_URL")
chroma_port = chroma_url.split(":")[-1]
client = chromadb.HttpClient(host='localhost', port=chroma_port)
embedding_model = OllamaEmbeddings(model='nomic-embed-text')
langchain_chroma = Chroma(
    client=client,
    collection_name="reddit_data",
    embedding_function=embedding_model
)
embed_retriever = langchain_chroma.as_retriever()
retriever_tool = create_retriever_tool(
    embed_retriever,
    "reddit_data",
    "Search for user experience about the startup and entrepreneur related topics"
)
web_search = DuckDuckGoSearchRun()

tools = [retriever_tool, web_search]

message_format = [
    ("system", "you are an expert in validating startup ideas. help the user to validate their startup idea also solve any query that is only releated to startup.{context}"),
    ("human", "{input}"),
     ("placeholder", "{agent_scratchpad}")
    ]
prompt = ChatPromptTemplate.from_messages(message_format)
llm = ChatOpenAI(
    api_key='ollama',
    model='llama3.2',
    base_url='http://localhost:11434/v1'
)
llm = llm.bind_tools(tools)
agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent,tools=tools)
agent_with_memory = RunnableWithMessageHistory(
    agent_executor,
    fetch_session_history,
    input_messages_key="input",
    output_messages_key="output",
    history_messages_key="chat_history")

# response = agent_executor.invoke({"input":"How to scale company from seed funding to series A?"})

async def get_response(input,session_id):
    collection = mongo_connect()
    if session_id is None:
        session_id = create_session_id()
    response = agent_with_memory.invoke({'input':input},config={"session_id": session_id})
    print(store)
    update_memory(store,session_id,collection)
    return response['output']