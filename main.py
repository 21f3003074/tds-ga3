from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import sys
from io import StringIO
import traceback
import os
from typing import List
from google import genai
from google.genai import types

app = FastAPI()

# CORS (important for testing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request model
class CodeRequest(BaseModel):
    code: str

# -------- TOOL FUNCTION --------
def execute_python_code(code: str) -> dict:
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

# -------- AI ERROR ANALYSIS --------
class ErrorAnalysis(BaseModel):
    error_lines: List[int]

def analyze_error_with_ai(code: str, tb: str) -> List[int]:
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    prompt = f"""
Analyze the following Python code and traceback.
Identify the exact line numbers where the error occurred.

CODE:
{code}

TRACEBACK:
{tb}

Return only the line numbers.
"""

    response = client.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "error_lines": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(type=types.Type.INTEGER)
                    )
                },
                required=["error_lines"]
            )
        )
    )

    result = ErrorAnalysis.model_validate_json(response.text)
    return result.error_lines

# -------- ENDPOINT --------
@app.post("/code-interpreter")
async def run_code(request: CodeRequest):

    execution = execute_python_code(request.code)

    # If success → no AI needed
    if execution["success"]:
        return {
            "error": [],
            "result": execution["output"]
        }

    # If error → call AI
    error_lines = analyze_error_with_ai(request.code, execution["output"])

    return {
        "error": error_lines,
        "result": execution["output"]
    }
