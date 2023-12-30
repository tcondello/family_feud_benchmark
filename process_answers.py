import json

f = open("responses/openAI_response_list.json")
data = json.load(f)
print(data)
for res in data:
    print(res)
# if response from LLM in answers
# for answer in answers:
#     if answer.get("answer") == llm_res:
#         print(answer.get("score"))

# print(question.get("question"))
