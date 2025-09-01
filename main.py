from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from scraper.scraper import scrape_website

app = FastAPI()


@app.get("/")
def root():
    return {"message": "Contact Scraper API is running"}


@app.get("/scrap")
def scrap(website: str = Query(...)):
    result = scrape_website(website)
    return JSONResponse(content=result or {"error": "Could not scrape site"})
