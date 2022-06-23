import re
from glob import glob
from convert_brat_to_tacred import get_annotation_from_file

words_to_label = {
    # "газ": "COMMODITY",
    # "газом": "COMMODITY",
    # "газа": "COMMODITY",
    # "уголь": "COMMODITY",
    # "угля": "COMMODITY",
    # "углем": "COMMODITY",
    # "грипп": "DISEASE",
    # "Уголь": "COMMODITY",
    # "нефть": "COMMODITY",
    # "Нефть": "COMMODITY",
    # "нефтью": "COMMODITY",
    # "нефти": "COMMODITY",
    # "рубль": "CURRENCY",
    # "рублей": "CURRENCY",
    # "рублем": "CURRENCY",
    # "доллар": "CURRENCY",
    # "долларов": "CURRENCY",
    # "долларом": "CURRENCY",
    # "гривен": "CURRENCY",
    "евро": "CURRENCY",

}

txt_files = glob("data/annotation_files/*.txt")

for filename in txt_files:
    with open(filename) as f:
        text = f.read()
    ann_filename = filename.replace(".txt", ".ann")
    annotation = get_annotation_from_file(ann_filename)
    last_ner_index = max(
        int(a["code"][1:]) for a in annotation if a["type"] == "NER"
    )
    last_ner_index += 1
    for word, label in words_to_label.items():
        space_word = f" {word}[\n .,]+?"
        word_indices = list(re.finditer(space_word, text))
        for found_index in word_indices:
            file_annotations = [
                a
                for a in annotation
                if a["type"] == "NER"
                and a["start"] == found_index.start() + 1
                and a["end"] == found_index.end() - 1
                and a["ann_type"] == label
            ]
            if file_annotations:
                continue
            if text[found_index.start() + 1: found_index.end() - 1] == word:
                ner_line = f"T{last_ner_index}\t{label} {found_index.start() + 1} {found_index.end() - 1}\t{word}\n"
            else:
                raise Exception
            with open(ann_filename, "a") as f:
                f.write(ner_line)
            last_ner_index += 1
