import json
from openai import OpenAI

# defaults to getting the key using os.environ.get("OPENAI_API_KEY")
client = OpenAI()

response = client.chat.completions.create(
    model="gpt-3.5-turbo-1106",
    response_format={"type": "json_object"},
    messages=[
        {
            "role": "system",
            "content": "I am going to ask you a series of questions when you answer I want you to say just the answer for example Question: name something with 4 wheels Response: car",
        },
        {"role": "user", "content": "Name something with teeth"},
    ],
)
print(response.choices[0].message.content)
print("done")
# Source of questions
###### https://www.buzzfeed.com/kellyrissman/family-feud-questions

# # Opening JSON file
# f = open("questions.json")
# data = json.load(f)
# questions = data.get("questions")
# for question in questions:
#     q = question.get("question")
#     answers = question.get("answers")
#     # call LLM with question

#     # if response from LLM in answers
#     llm_res = "Janitor"
#     for answer in answers:
#         if answer.get("answer") == llm_res:
#             print(answer.get("score"))

#     print(question.get("question"))
