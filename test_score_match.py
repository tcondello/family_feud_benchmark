#!/usr/bin/env python3
from score_benchmark import answers_match, match_score

def main() -> None:
    assert match_score("eye patch", [{"answer": "Eyepatches", "score": 51}])[0] == 51
    assert match_score("bicycle", [{"answer": "bike", "score": 44}])[0] == 44
    assert answers_match("Shopping", "Shop")
    assert answers_match("Lawnmower", "lawn mower")
    assert answers_match("ramen", "Ramen/Soup")
    assert answers_match("Gaga", "Lady Gaga")
    assert not answers_match("car", "card")
    assert not answers_match("telephone pole", "phone")
    assert not answers_match("Get married", "Get Hitched")
    print("ok")

if __name__ == "__main__":
    main()
