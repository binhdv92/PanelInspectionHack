import uvicorn, multiprocessing

if __name__ == "__main__":
    multiprocessing.freeze_support()
    #uvicorn.run("api:app", host="0.0.0.0", port=80, reload=False, workers=8)
    uvicorn.run("api:app", host="0.0.0.0", port=80, reload=True)





