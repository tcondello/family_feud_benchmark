import json
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def call_openAI(question):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {
                "role": "system",
                "content": "I am going to ask you a series of questions when you answer I want you to say just the answer for example Question: name something with 4 wheels Response: car",
            },
            {"role": "user", "content": question},
        ],
    )
    # print(response.choices[0].message.content)
    return response.choices[0].message.content


f = open("question_list.json")
data = json.load(f)
questions = data.get("questions")
response_list = list()
llm_dict = dict()
for question in questions:
    q = question.get("question")
    answers = question.get("answers")

    openAI_res = call_openAI(q)

    print(f"Question: {q} Response: {openAI_res}")

    response_list.append({q: openAI_res})

llm_dict["OpenAI"] = response_list

json_object = json.dumps(llm_dict["OpenAI"], indent=4)

with open("response_list.json", "w") as outfile:
    outfile.write(json_object)
