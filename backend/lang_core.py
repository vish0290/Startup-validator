import os
import chromadb
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain.tools.retriever import create_retriever_tool
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import create_tool_calling_agent, AgentExecutor
from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv()

mongo_url = os.getenv("MONGO_URL")
def mongo_connect():
    client = MongoClient(mongo_url)
    db = client.sv_chat
    return db


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
    ("system", "you are an expert in validating startup ideas. help the user to validate their startup idea also solve any query that is only releated to startup."),
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
# response = agent_executor.invoke({"input":"How to scale company from seed funding to series A?"})

async def get_response(input,session_id):
    
    response = agent_executor.invoke({"input":input})
    return response['output']