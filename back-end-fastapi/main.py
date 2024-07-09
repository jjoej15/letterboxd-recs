from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

import use_model
import asyncio
import pandas as pd
import pickle
import uvicorn

app = FastAPI()

origins = [
    "http://localhost:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/{user}")
def get_recs(user):
    with open("pickles/model_df.pkl", 'rb') as pkl:
        ratings_df = pickle.load(pkl)

    user = f'/{user}/'
    user_data = ratings_df[ratings_df['User'] == user]

    if user_data.empty:
        raise HTTPException(
            status_code=404, detail=f"User {user} not in database"
        )
    
    return user_data

if __name__ == '__main__':
    uvicorn.run(app, port=8080, host='0.0.0.0')