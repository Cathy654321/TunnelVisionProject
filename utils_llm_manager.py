import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

def GPT_Response(prompt, model="gpt-3.5-turbo", max_tokens=100, temperature=0.01):
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model=model,
        temperature=temperature,
        max_tokens=max_tokens
    )
    return chat_completion.choices[0].message.content.strip()

def testGPT():
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant."
            },
            {
                "role": "user",
                "content": "What is the capital of China?",
            }
        ],

        model="gpt-3.5-turbo",
        temperature=0.01,
        max_tokens=100
    )

    print(chat_completion.choices[0].message.content)

if __name__ == '__main__':
    response = GPT_Response(prompt="what is the capital of China?")
    print(response)
