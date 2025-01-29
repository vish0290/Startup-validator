from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain.schema import Document
import pandas as pd

# Data Initialization
def init_data(file_path):
    df = pd.read_csv("rag.csv") 
    docs = [Document(page_content=str(row)) for _, row in df.iterrows()]
    # loader = CSVLoader(file_path)
    # docs = loader.load()
    return docs

# Embedding Generation
def generate_embeddings(docs):
    text_splitter = RecursiveCharacterTextSplitter()
    documents = text_splitter.split_documents(docs)
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    vector = FAISS.from_documents(documents, embeddings)
    return vector

# Retrieval
def create_retriever(vector):
    retriever = vector.as_retriever()
    return retriever

# User Response
def get_response(user_input, retriever):
    model = OllamaLLM(model="mistral-nemo")
    prompt = ChatPromptTemplate.from_template("""Answer the following question based only on the provided context:

<context>
{context}
</context>

Question: {input}""")
    document_chain = create_stuff_documents_chain(model, prompt)
    retrieval_chain = create_retrieval_chain(retriever, document_chain)
    response = retrieval_chain.invoke({"input": user_input})
    return response["answer"]

# Initialize data and create retriever
docs = init_data("rag.csv")
vector = generate_embeddings(docs)
retriever = create_retriever(vector)