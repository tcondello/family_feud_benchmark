import json
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def call_openAI(question):
    response = client.chat.completions.create(
        # Kept for backwards compatibility; prefer `run_benchmark.py` for
        # the multi-provider latest-model suite.
        model="gpt-5.5",
        messages=[
            {
                "role": "system",
                "content": "I am going to ask you a series of questions when you answer I want you to say just the answer for example Question: name something with 4 wheels Response: car",
            },
            {"role": "user", "content": question},
        ],
        max_completion_tokens=64,
    )
    # print(response.choices[0].message.content)
    return response.choices[0].message.content


# Prefer the combined multi-source set; fall back to the original Buzzfeed list.
question_paths = (
    "questions/all_questions.json",
    "questions/question_list.json",
    "question_list.json",
)
data = None
for path in question_paths:
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        break
    except FileNotFoundError:
        continue
if data is None:
    raise FileNotFoundError(f"No question file found in {question_paths}")

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

with open("responses/response_list.json", "w") as outfile:
    outfile.write(json_object)
