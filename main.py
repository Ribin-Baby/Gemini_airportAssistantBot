from fastapi import FastAPI, responses
import gradio as gr
from model_interface import demo
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

@app.get("/")
def index():
    return responses.FileResponse("pages/index.html")

app = gr.mount_gradio_app(app, demo, path="/gradio")