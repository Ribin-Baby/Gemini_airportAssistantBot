import vertexai
import os
from datetime import datetime
from vertexai.generative_models import (
    Content,
    FunctionDeclaration,
    GenerativeModel,
    Part,
    Tool,
    ChatSession
)
import random
import gradio as gr
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import warnings
warnings.filterwarnings("ignore")
load_dotenv()

APP_MAILID = os.getenv("MAIL_FROM")
APP_PWD = os.getenv("APP_PWD")

# Define project information
PROJECT_ID = "manifest-shade-328408"  # @param {type:"string"}
LOCATION = "us-central1"  # @param {type:"string"}

# Initialize Vertex AI
vertexai.init(project=PROJECT_ID, location=LOCATION)

config = {
    "max_output_tokens": 2048,
    "temperature": 0,
    "top_p": 0.69
}

get_baggage_support_func = FunctionDeclaration(
    name="get_baggage_support",
    description="Function to get the support for baggage items in case of baggage lost at airport, need to extract all required properties",
    parameters={
        "type": "object",
        "properties": {"name": {"type": "string", "description": "Name of the user"},
                       "email": {"type": "string", "description": "Email address of the user"},
                       "date": {"type": "string", "description": "Date of flight"},
                       "airline_name": {"type": "string", "description": "Extracted name of the airline company"},
                       "flight_number": {"type": "string", "description": "Extracted flight number"},
                       "departure_airport": {"type": "string", "description": "Extracted departured airport location"},
                       "arrival_airport": {"type": "string", "description": "Extracted arrival airport location"}
                       },
                    "required": [
                        "name", "email", "date", "airline_name", "flight_number", "departure_airport", "arrival_airport"
                    ]
    },
)

support_tool = Tool(
    function_declarations=[get_baggage_support_func],
)


def sendMail(mail_to, mail_body):
    # Prepare actual message
    mimemsg = MIMEMultipart()
    mimemsg['From']=APP_MAILID
    mimemsg['To']="ribinkannoth@gmail.com"
    mimemsg['Cc']=mail_to
    mimemsg['Subject']='Baggage LOST SUPPORT!'
    mimemsg.attach(MIMEText(mail_body, 'html'))
    try:
        connection = smtplib.SMTP(host='smtp.gmail.com', port=587, timeout=5)
        connection.ehlo()
        connection.starttls()
        connection.login(APP_MAILID, APP_PWD)
        connection.send_message(mimemsg)
        connection.quit()
        print('successfully sent the mail 👍')
    except:
        print("failed to send mail 👎")


class Chatbot:
    # with custom history
    def __init__(self, model) -> None:
        self.model = model
        self.chat = model #self.model.start_chat()
        self.history = []
        self.refresh_history()
        
    def chitchat(self, message, history=""):
        print("USER:", message)
        if type(message) == str:
            # Define the user's prompt in a Content object that we can reuse in model calls
            user_prompt_content = Content(
                role="user",
                parts=[
                    Part.from_text(message),
                ],
            )
            # Add the current chat to the history
        else:
            # if the user's prompt already in a Content object 
            user_prompt_content = message
        self.history.extend([user_prompt_content])
        response = self.chat.generate_content(self.history, tools=[support_tool])
        # print("HISTORY: ", self.history)
        print("BOT:", response)
        self.history.extend([response.candidates[0].content])

        if response.candidates[0].content.parts[0].function_call.name == "get_baggage_support":
            args = response.candidates[0].content
            # print("Response:", response)
            function_response = self.get_baggage_suport(args)
            response = self.chitchat(function_response)
            self.refresh_history()
            return response

        else:
            args = response.candidates[0].content.parts[0].text
            return args 
        
    def get_baggage_suport(self, args):
        args = args.parts[0].function_call.args
        time_now = datetime.now()
        id = time_now.timestamp()
        response_msg = f"Have raised a complaint at time: {time_now}, with complaint id:{str(int(id))} on behalf of {args['name']}, and status of the complaint was sent to {args['name']}'s E-mail id: {args['email']}, give a summary to the user."
        user_info = "\n"
        for key, value in args.items():
            user_info += f"<li>{key}: {value}</li>\n"
        # Function to send mail here
        mail = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Baggage Loss Complaint</title>
</head>
<body>
    <p>Hi Support Team,</p>
    <p>{args['name']} has lost a luggage at the airport during his/her flight on {args['date']}.</p>
    <p>More details are given below:</p>
    <ul>
        {user_info}
        <li>Complaint Registered On: {time_now}</li>
        <li>Complaint/Ticket ID: {str(int(id))}</li>
    </ul>
    <p>Best,</p>
    <p>BOT</p>
</body>
</html>
"""
        print("sending MAIL...")
        print(mail)
        sendMail(args['email'], mail)
        # Define the user's prompt in a Content object if function call is triggered
        response_msg = Content(role="function", parts=[
                                        Part.from_function_response(
                                            name="get_baggage_support",
                                            response={
                                                "content":  response_msg,
                                            },
                                        ),])
        return response_msg
    
    def refresh_history(self):
        self.history = []
        # SYSTEM PROMT
        self.system_promt = Part.from_text("""#INSTRUCTION: You are an airport baggage support assistant BOT. Verify that all details are provided from user side, if any details is missing ask follow-up questions to the user and collect all required datas, Never makeup data fields that you don't know. if the user is having a normal conversation reply accordingly.""") #if all required details are collected respond in json schema with collected details for function calling applications, or else continue asking follow-up questions to the user."""
        self.model_response = Part.from_text("""yes i can act as an Airport Baggage Support Assistant Bot. i can get baggage support from airport side.""")
        self.history.extend([Content(
                role="user",
                parts=[
                    self.system_promt,
                ],
            ),
            Content(
                role="model",
                parts=[
                    self.model_response,
                ],
            )])
    
interface_description = """
<strong>This application an airport support assistant, which helps you to raise
complaints reguarding baggage lost or delayed.</strong><br/>

"""

# STARTING POINT
model = GenerativeModel(model_name="gemini-1.0-pro-001", generation_config=config)
bot = Chatbot(model)
demo = gr.ChatInterface(fn=bot.chitchat, description=interface_description, title="Airport Assistant BOT", 
                        retry_btn=None, undo_btn=None, theme="light")
# demo = gr.Interface(fn=bot.chitchat, allow_flagging="never", inputs="textbox", 
#                     description=interface_description,  title="Airport Assistant BOT",
#                     outputs="textbox",
#                     theme="light")
# demo.launch(debug=True, server_name="127.0.0.1", server_port=8080, prevent_thread_lock=True)
        