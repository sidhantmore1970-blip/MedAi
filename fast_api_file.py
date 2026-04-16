from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
#from PIL import Image
import io
import Extracting_prescription_data
import traceback
from fastapi.middleware.cors import CORSMiddleware
import json
import re
import Critical_Warinings
import SQLLITE3_DataBase
from AI_assistant_logic import MedicalAssistant

api = FastAPI()

# --- 1. Mount Static Files (So you can open the Frontend) ---
api.mount("/static", StaticFiles(directory="static"), name="static")

@api.get("/")
async def read_root():
    return FileResponse('static/test1.html')

# --- Initialize AI ---
ai_bot = MedicalAssistant()

class MedicationItem(BaseModel):
    medications: str
    Dosage: str
    Frequency: str
    Duration: str
    Map_link: str 

class PrescriptionRequest(BaseModel):
    Prescription_info: List[MedicationItem]

class ChatRequest(BaseModel):
    message: str


api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

# --- 2. Fixed Endpoint ---
@api.post('/data_extraction')
async def prescription_dataExtraction(
    image: UploadFile = File(...),
    # FIX: Use 'user_location' to match frontend key. Use Form(None) for optional form data.
    user_location: Optional[str] = Form(None) 
):
    try:
        content = await image.read()
        img_byte = io.BytesIO(content)
        
        # FIX: Parse the JSON string from frontend into a Dictionary
        loc_data_dict = None
        if user_location:
            try:
                loc_data_dict = json.loads(user_location)
                print(f"Received Location: {loc_data_dict}") # Debug print
            except Exception as e:
                print(f"Error parsing location: {e}")

        # Pass the parsed dictionary to your extraction logic
        obj = Extracting_prescription_data.Handwritting_Extraction()
        result = obj.extracting_presc_data(img_byte, loc_data_dict)
        
        response = ''
        for chunk in result:
            if chunk.parts:
                response += chunk.text
        
        match = re.search(r'(\{.*\})', response, re.DOTALL)
        clean_json = match.group(1) if match else response
        data = json.loads(clean_json)
        return data

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
@api.post('/critical_warnings', response_model=None)
async def critical_warnings_handler(extracted_data : PrescriptionRequest):
    warn_obj = Critical_Warinings.warnings()
    warn_response = warn_obj.analyzing_critical_warnings(extracted_data.model_dump())
    return warn_response

@api.post('/post_into_db')
def save_to_sql(payload:dict):
    sql_obj = SQLLITE3_DataBase.medi_data_base()
    result = sql_obj.save_to_db(payload)
    return result

@api.get('/get_Saved_data')
def get_saved_details():
    sql_obj = SQLLITE3_DataBase.medi_data_base()
    result = sql_obj.display_table()
    # If using pandas in SQLLITE3_DataBase, convert to dict:
    return result.to_dict(orient='records') 
    

@api.post("/chat")
async def chat_endpoint(req: ChatRequest):
    try:
        response_text = ai_bot.process_chat(req.message, session_key="default_user")
        return {"response": response_text}
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))