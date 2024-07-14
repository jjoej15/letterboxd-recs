from . import use_model
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()

origins = [
    "http://localhost:5173",
    "https://letterboxdrecs.netlify.app/",
    "https://letterboxdrecs.netlify.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/")
async def get_recs(users: str, excludeWatchlist: str, popFilter: str, genreFilters: str):
    excludeWatchlist = excludeWatchlist.capitalize()
    genreFilters = genreFilters.split(',') if genreFilters else []
    blended = True if len(users.split(',')) > 1 else False
  
    parameters = {'users': users, 'excludeWatchlist': excludeWatchlist, 'popFilter': popFilter, 'genreFilters': genreFilters, 'blended': blended}

    return await use_model.main(parameters)


if __name__ == '__main__':
    uvicorn.run(app, port=8080, host='0.0.0.0')