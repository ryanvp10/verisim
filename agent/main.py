from fastapi import FastAPI

app = FastAPI(title="verisim-api")


@app.get("/health")
def health():
    return {"status": "ok"}
