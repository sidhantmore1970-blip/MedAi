from dotenv import load_dotenv, find_dotenv
import os
import base64
from io import BytesIO
from typing import List

from langchain_google_genai import ChatGoogleGenerativeAI, HarmCategory, HarmBlockThreshold
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.pydantic_v1 import BaseModel, Field
from PIL import Image
import location

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')


# ---- Structured output schemas ----
class PatientInfo(BaseModel):
    patient_name: str = Field(description="Patient's name, or 'Not provided'")
    age: str = Field(description="Patient's age, or 'Not provided'")
    Date: str = Field(description="Prescription date, or 'Not provided'")


class PrescriptionItem(BaseModel):
    medications: str
    Dosage: str
    Frequency: str = Field(description="Include timing, e.g. '1-0-1 (after meals)'")
    Duration: str
    Map_link: str


class PrescriptionOutput(BaseModel):
    patient_info: PatientInfo
    Prescription_info: List[PrescriptionItem]


class Handwritting_Extraction:
    def __init__(self):
        load_dotenv(find_dotenv())

        # Safety settings
        self.Safety_Settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

    def get_system_prompt(self, location_data):
        self.map_link_url = location.get_location(location_data)

        self.sys_prompt = '''
        You are an expert-level Medical Data Extraction tool. Your primary function is to analyze images of medical prescriptions and extract key information in a highly structured, machine-readable format.
        ## Your Task
        1. Perform OCR on all provided handwritten and printed text.
        2. Identify and extract key medical entities.
        3. Ensure that no two medication entries are identical.
        4. Include timings (e.g., 'after meals') within the frequency column.
        5. Add this link to the Map_link column for every entry: {}
        6. Fetch the patient details as patient_info compulsory, if not found return 'not provided'
        7. Importantly: only extract these columns: 'medications','Dosage','Frequency','Duration','Map_link' and
           in patient_info the columns are: 'Name','Age','Date'.

        ## Critical Guardrails
        * You are NOT a doctor. Do not provide medical advice.
        * If the image is blurry, respond that the image is unreadable.
        * If a field is missing, use "Not provided".
        '''.format(self.map_link_url)

        return self.sys_prompt

    def _image_to_base64(self, image: Image.Image) -> str:
        buffered = BytesIO()
        image_format = image.format or "PNG"
        image.save(buffered, format=image_format)
        return base64.b64encode(buffered.getvalue()).decode("utf-8"), image_format.lower()

    def extracting_presc_data(self, image_file, location_data):
        self.system_Prompt = self.get_system_prompt(location_data)

        # Initialize LangChain Gemini chat model
        self.model = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
            safety_settings=self.Safety_Settings,
        )

        # Bind structured output schema (handles JSON parsing for us)
        structured_model = self.model.with_structured_output(PrescriptionOutput)

        try:
            # Open and resize the image
            image = Image.open(image_file)

            max_width = 1024
            if image.width > max_width:
                ratio = max_width / image.width
                new_height = int(image.height * ratio)
                image = image.resize((max_width, new_height), Image.LANCZOS)

            image_b64, img_format = self._image_to_base64(image)

            messages = [
                SystemMessage(content=self.system_Prompt),
                HumanMessage(
                    content=[
                        {"type": "text", "text": "Extract the prescription data from this image."},
                        {
                            "type": "image_url",
                            "image_url": f"data:image/{img_format};base64,{image_b64}",
                        },
                    ]
                ),
            ]

            # Returns a validated PrescriptionOutput pydantic object (use .dict() for JSON)
            return structured_model.invoke(messages)

        except Exception as e:
            raise Exception(f'Error occured in Extracting prescription data: {e}')
