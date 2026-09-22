import os
from openai import OpenAI

# pip install openai

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"]
)

command = (
    
)

completion = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {
            "role": "system",
            "content": (
                "You are a person named Sinujk who speaks Hindi, "
                "Odia, and English. He is from India and is a coder. "
                "Analyze the chat history and respond naturally like "
                "Sinujk, as a real person."
            )
        },
        {
            "role": "user",
            "content": command
        }
    ]
)

print(completion.choices[0].message.content)