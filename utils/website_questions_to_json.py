import re
import json

# Source of questions:
# https://www.buzzfeed.com/kellyrissman/family-feud-questions

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = Path(__file__).with_name("website_questions.txt")
OUTPUT_PATHS = (
    ROOT / "questions" / "question_list.json",
    ROOT / "questions" / "buzzfeed" / "question_list.json",
)


def convert_to_schema(file_content):
    # Splitting the content into sections based on the question number pattern
    question_sections = re.split(r"\n\d+\.", file_content)

    # Removing the first element if it's empty (due to split at the beginning of the text)
    if question_sections and question_sections[0].strip() == "":
        question_sections.pop(0)

    schema = {"questions": []}

    for section in question_sections:
        lines = section.strip().split("\n")
        question = lines[0].strip()

        answers = []
        for answer_line in lines[1:]:
            match = re.match(r"(.*) \((\d+)\)", answer_line.strip())
            if match:
                answer, score = match.groups()
                answers.append({"answer": answer.strip(), "score": int(score)})

        schema["questions"].append({"question": question, "answers": answers})

    return schema


if __name__ == "__main__":
    converted_schema = convert_to_schema(INPUT_PATH.read_text(encoding="utf-8"))
    plain = json.dumps(converted_schema, indent=4) + "\n"
    OUTPUT_PATHS[0].write_text(plain, encoding="utf-8")

    with_source = {
        "source": {
            "name": "buzzfeed",
            "description": (
                "Family Feud questions compiled in BuzzFeed's "
                "'115 Family Feud Questions To Liven Up Game Night' list."
            ),
            "homepage": "https://www.buzzfeed.com/kellyrissman/family-feud-questions",
        },
        "questions": converted_schema["questions"],
    }
    OUTPUT_PATHS[1].parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATHS[1].write_text(json.dumps(with_source, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT_PATHS[0]} and {OUTPUT_PATHS[1]} ({len(converted_schema['questions'])} questions)")
