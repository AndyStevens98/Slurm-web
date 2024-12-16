import logging
from io import BytesIO

import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse


class CustomFormatter(logging.Formatter):
    grey: str = "\x1b[38;21m"
    green: str = "\x1b[32m"
    yellow: str = "\x1b[33m"
    red: str = "\x1b[31m"
    bold_red: str = "\x1b[31;1m"
    reset: str = "\x1b[0m"
    format_str: str = "{asctime}   {levelname:8s} --- {name}: {message}"

    FORMATS: dict[int, str] = {
        logging.DEBUG: grey + format_str + reset,
        logging.INFO: green + format_str + reset,
        logging.WARNING: yellow + format_str + reset,
        logging.ERROR: red + format_str + reset,
        logging.CRITICAL: bold_red + format_str + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, "%m/%d/%Y %I:%M:%S %p", style="{")
        return formatter.format(record)


logger: logging.Logger = logging.getLogger("main")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(CustomFormatter())
logger.addHandler(ch)

slurm_web_url = "https://slurmweb.ice-mgmt.icl.gtri.org"


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/{path:path}")
async def proxy_get(path: str):
    response = requests.get(f"{slurm_web_url}/{path}", verify=False)
    return response.json()


@app.post("/{path:path}", response_model=None)
async def proxy_post(path: str, request_body: dict, query_params: dict = {}) -> dict | list | str | StreamingResponse:
    response = requests.post(f"{slurm_web_url}/{path}", json=request_body, params=query_params, verify=False)
    content_type = response.headers.get("Content-Type", "")

    if "json" in response.headers["Content-Type"]:
        return response.json()
    elif "html" in response.headers["Content-Type"]:
        return response.text
    elif "image" in response.headers["Content-Type"]:
        image_bytes = BytesIO(response.content)
        return StreamingResponse(
            image_bytes,
            media_type=content_type,  # Automatically use the Content-Type (e.g., image/png, image/jpeg)
        )
    elif content_type:
        logger.error(f"Unhandled content type: {response.headers['Content-Type']}")
        logger.debug(response.text)
        return {}
    else:
        logger.error("Content type not in response headers, something is wrong")
        return {}
