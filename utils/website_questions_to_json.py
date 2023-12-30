import re
import json

# Source of questions
###### https://www.buzzfeed.com/kellyrissman/family-feud-questions


# Function to parse the file content and convert it into the desired schema
def convert_to_schema(file_content):
    # Splitting the content into sections based on the question number pattern
    question_sections = re.split(r"\n\d+\.", file_content)

    # Removing the first element if it's empty (due to split at the beginning of the text)
    if question_sections and question_sections[0].strip() == "":
        question_sections.pop(0)

    # Preparing the final schema
    schema = {"questions": []}

    for section in question_sections:
        # Splitting each section into lines
        lines = section.strip().split("\n")

        # The first line is the question
        question = lines[0].strip()

        # The rest are answers
        answers = []
        for answer_line in lines[1:]:
            # Extracting answer and score
            match = re.match(r"(.*) \((\d+)\)", answer_line.strip())
            if match:
                answer, score = match.groups()
                answers.append({"answer": answer.strip(), "score": int(score)})

        # Adding to the schema
        schema["questions"].append({"question": question, "answers": answers})
        # Serializing json
        json_object = json.dumps(schema, indent=4)

        # Writing to sample.json
        with open("full_question_list.json", "w") as outfile:
            outfile.write(json_object)

    return schema


# Converting the file content to the desired schema
f = open("website_questions.txt")

converted_schema = convert_to_schema(f.read())
converted_schema
