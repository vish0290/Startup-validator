import httpx
from pymongo import MongoClient
import os
from dotenv import load_dotenv
import pandas as pd
import asyncio
import chromadb
from chromadb.utils.embedding_functions.ollama_embedding_function import OllamaEmbeddingFunction
load_dotenv()

db_url = os.getenv("MONGODB_URL")
chroma_url = os.getenv("CHROMA_URL")
ollama_url = os.getenv("OLLAMA_URL")
def mongo_connect():        
    try:
        client = MongoClient(db_url)
        db = client.reddit
        post_db = db['post_new']
        comment_db = db['comment']
        return post_db, comment_db
    except Exception as e:
        print(f"Error connecting to MongoDB: {str(e)}")

def chroma_connect():
    db_port = chroma_url.split(":")[-1]
    try:
        client = chromadb.HttpClient(host='localhost',port=db_port)
        return client
    except Exception as e:
        print(f"Error connecting to Chroma: {str(e)}")
        exit()

def upload_to_mongo(df,db):
    try:
        records = df.to_dict(orient='records')
        db.insert_many(records)
        print("Data uploaded to MongoDB")
    except Exception as e:
        print(f"Error uploading data to MongoDB: {str(e)}")


async def get_comments(post_ids,comment_db):
    for post_id in post_ids:
        async with httpx.AsyncClient() as client:
            url = f'https://www.reddit.com/comments/{post_id}.json'
            try:
                response = await client.get(url)
                data = response.json()
                comments = data[1]['data']['children']
                comment_list = []
                for comment in comments:
                    comment_data = comment['data']
                    comment_list.append(
                        {
                            'id': comment_data['id'],
                            'body': comment_data['body'],
                            'created_utc': comment_data['created_utc'],
                            'score': comment_data['score'],
                            'parent_id': comment_data['parent_id'],
                            'subreddit': comment_data['subreddit']
                        }
                    )
                df = pd.DataFrame(comment_list)
                upload_to_mongo(df,comment_db)
                print(f"Request {post_id} - Status code: {response.status_code}")
            except Exception as e:
                print(f"request failed:{post_id} {str(e)}")
           
            


async def get_post_data(url,post_db,comment_db):
    df3 = pd.DataFrame()
    after_post_id = None
    for i in range(10):
        async with httpx.AsyncClient() as client:
            params = {
                                'limit': 100,
                                't':'all',
                                'after': after_post_id
                            }
            try:
                response = await client.get(url, params=params)
                print(f"Request {i} - Status code: {response.status_code}")
            except Exception as e:
                print(f"request failed:{i} {str(e)}")
            json_data = response.json()
            df = pd.DataFrame(json_data['data']['children'])
            df2 = pd.DataFrame(list(df['data']))
            df2 = df2[['id','title','selftext','subreddit','created_utc','num_comments','url']]
            df3 = pd.concat([df3,df2])
            after_post_id = json_data['data']['after']
            print(len(df3))
    df3 = df3.drop_duplicates(subset=['id'])
    post_ids = df3['id'].tolist()
    upload_to_mongo(df3,post_db)
    print(len(df3))    
    await get_comments(post_ids,comment_db)
    

def load_from_csv(file_path,db):
    try:
        df = pd.read_csv(file_path)
        upload_to_mongo(df,db)
        return df
    except Exception as e:
        print(f"Error loading data from csv: {str(e)}")
        exit()
        return None
        


def create_embeddings(chroma_client,ollama_ef,post_df,comment_df):
    processed_data = []
    metadata = []
    ids = []
    comment_df['parent_id'] = comment_df['parent_id'].apply(lambda x: x.split('_')[1])
    for i in post_df:
        comments = comment_df[comment_df['parent_id'] == i['id']]
        comments = str(comments['body'].tolist())
        processed_data.append({
            'id': i['id'],
            'title': i['title'],
            'selftext': i['selftext'],
            'comments': comments
        })
        metadata.append({
            'id': i['id'],
            'subreddit': i['subreddit'],
            'url': i['url']
        })
        ids.append(i['id'])
    try:   
        collection = chroma_client.create_collection(name='reddit_data',embedding_function=ollama_ef)
        collection.add(
            documents = processed_data,
            metadatas = metadata,
            ids = ids
        )
        print("Embeddings created")
    except Exception as e:
        print(f"Error creating embeddings: {str(e)}")
        exit()
              
async def main():
    
    post_db, comment_db = mongo_connect()
    print("Preparing data")
    post_data = load_from_csv('./backend/dataset/post_data.csv',post_db)
    comments_data = load_from_csv('./backend/dataset/comment_data.csv',comment_db)
    if post_data is not None and comments_data is not None:
        print("Data loaded from csv")
    else:
        print("dataset not found")
        print("Fetching data from Reddit")
        endpoints = ['/r/startups','/r/Entrepreneur']
        for endpoint in endpoints:
            url = f"https://www.reddit.com{endpoint}/new.json"
            await get_post_data(url,post_db,comment_db)
            print("Data fetched from Reddit")    


    print("Data preparation completed")
    print("Preparing Embeddings")
    post_data = post_db.find()
    comment_data = comment_db.find()
    post_df = pd.DataFrame(list(post_data))
    comment_df = pd.DataFrame(list(comment_data))
    
    chroma_client = chroma_connect()
    ollama_ef = OllamaEmbeddingFunction(url=f"{ollama_url}/api/embeddings", model_name="nomic-embed-text")
    create_embeddings(chroma_client,ollama_ef,post_df,comment_df)
    print("Embeddings created, All tasks completed")
    

    
asyncio.run(main())
    
