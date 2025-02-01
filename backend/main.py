from fastapi import FastAPI
import asyncio
from pydantic import BaseModel
# from backend.core import main #using pydantic_ai 
from backend.lang_core import get_response #using Langchain


class Query(BaseModel):
    query: str
    
app = FastAPI()


@app.get("/")
def health_check():
    return {"status": "running"}

@app.get('/query')
async def chat(query: str):
    # return {'message': await main(query)}
    return {'message': await get_response(query)}