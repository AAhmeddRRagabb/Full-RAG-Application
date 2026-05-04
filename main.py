# ------------------------------------------------------
# Main Workflow
# ------------------------------------------------------

from fastapi import FastAPI
app = FastAPI()


@app.get("/welcome")
def welcome():
    return {
        'Hello' : 'Ahmed'
    }