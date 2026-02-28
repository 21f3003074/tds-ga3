from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import sys
from io import StringIO
import traceback
import re

app = FastAPI()

# CORS (important)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CodeRequest(BaseModel):
    code: str

def execute_python_code(code: str):
    old_stdout = sys.stdout
    sys.stdout = StringIO()

    try:
        exec(code)
        output = sys.stdout.getvalue()
        return {"success": True, "output": output}
    except Exception:
        output = traceback.format_exc()
        return {"success": False, "output": output}
    finally:
        sys.stdout = old_stdout


def extract_error_lines(traceback_text: str):
    # Find "line X" patterns
    lines = re.findall(r'line (\d+)', traceback_text)
    return list(set(int(num) for num in lines))


@app.post("/code-interpreter")
async def run_code(request: CodeRequest):

    execution = execute_python_code(request.code)

    if execution["success"]:
        return {
            "error": [],
            "result": execution["output"]
        }

    # If error → extract line numbers from traceback
    error_lines = extract_error_lines(execution["output"])

    return {
        "error": error_lines,
        "result": execution["output"]
    }
