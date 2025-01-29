from fastapi import FastAPI
import asyncio
from pydantic import BaseModel
from backend.core import main


class Query(BaseModel):
    query: str
    
app = FastAPI()


@app.get("/")
def health_check():
    return {"status": "running"}

@app.get('/query')
async def chat(query: str):
    return {'message': await main(query)}