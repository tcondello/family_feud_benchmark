# Family Feud question sources

There is no freely redistributable official Fremantle/Hasbro question dump.
This benchmark therefore uses public lists that preserve survey answers and
point values (or cluster counts) in the same spirit as the TV surveys.

## Schema

Every source file uses:

```json
{
  "source": { "name": "...", "homepage": "..." },
  "questions": [
    {
      "question": "Name something with teeth.",
      "answers": [
        { "answer": "Animals", "score": 66 },
        { "answer": "People", "score": 19 }
      ]
    }
  ]
}
```

`questions/question_list.json` keeps the original Buzzfeed-only list for
backward compatibility with the early scripts.

## Sources

| Directory | Origin | Notes |
| --- | --- | --- |
| `buzzfeed/` | [BuzzFeed list](https://www.buzzfeed.com/kellyrissman/family-feud-questions) | Original 115-question source already in the repo |
| `mstiescott/` | [TV episode transcriptions](https://mstiescott.neocities.org/) | Face-off wording + on-board answers/scores from broadcast seasons 5–7 and 16–27 |
| `protoqa/` | [iesl/protoqa-data](https://github.com/iesl/protoqa-data) ([paper](https://arxiv.org/abs/2005.00771)) | Research Family Feud-style dataset (scraped fan surveys + crowdsourced clusters) |
| `all_questions.json` | Combined | De-duplicated union of the sources above |

## Refreshing the data

```bash
pip install -r requirements.txt

# Original Buzzfeed text -> JSON (uses utils/website_questions.txt)
python utils/website_questions_to_json.py

# Wrap existing Buzzfeed JSON with source metadata
python utils/add_buzzfeed_metadata.py

# Download + convert ProtoQA splits
python utils/convert_protoqa.py

# Scrape mstiescott season pages
python utils/scrape_mstiescott.py

# Rebuild the de-duplicated combined file
python utils/build_combined_questions.py
```
