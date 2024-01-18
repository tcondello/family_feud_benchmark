import json

llm_response = open("responses/openAI_response_list.json")
score_card = open("questions/question_list.json")
res_data = json.load(llm_response)
score_data = json.load(score_card)

for question in score_data:
    if question in res_data:
        print(score_data[question].get("answers"))

# if response from LLM in answers
# for answer in answers:
#     if answer.get("answer") == llm_res:
#         print(answer.get("score"))

# print(question.get("question"))
