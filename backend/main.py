from fastapi import FastAPI
import asyncio
from pydantic import BaseModel


class Query(BaseModel):
    query: str
    
app = FastAPI()


@app.get("/")
def health_check():
    return {"status": "running"}

@app.get('/query')
def chat(query: Query):
    if query.query.lower() == "hello":
        return {"query": "Hi"}
    else:
        return {"query": "I don't understand"}