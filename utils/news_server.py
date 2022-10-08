import json
import os
import time
from datetime import datetime

import feedparser
import pytz
import razdel
import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer

# model_ckpt = "cointegrated/rubert-tiny2"
model_ckpt = "multilabel_ner_rured2"
tokenizer = AutoTokenizer.from_pretrained(model_ckpt)
model = AutoModelForTokenClassification.from_pretrained(model_ckpt)

with open("multilabel_ner_rured2/id_to_label.json") as f:
    id_to_label = json.load(f)
    id_to_label = {int(k): v for k, v in id_to_label.items()}


def predict(text: str):
    tokenized = tokenizer(text, return_offsets_mapping=True)
    input_ids = torch.tensor([tokenized["input_ids"]], dtype=torch.long)
    token_type_ids = torch.tensor(
        [tokenized["token_type_ids"]], dtype=torch.long
    )
    attention_mask = torch.tensor(
        [tokenized["attention_mask"]], dtype=torch.long
    )
    offset_mapping = tokenized["offset_mapping"]
    preds = model(
        **{
            "input_ids": input_ids,
            "token_type_ids": token_type_ids,
            "attention_mask": attention_mask,
        }
    )
    logits = preds.logits
    results = []
    prev_label = ""
    for i, token in enumerate(input_ids[0]):
        word = tokenizer.convert_ids_to_tokens([token])[0]
        # print(word)
        if token > 3:
            class_ids = (logits[0][i] > -1).nonzero()
            if class_ids.shape[0] >= 1:
                class_names = [id_to_label[int(cl)] for cl in class_ids]
            else:
                class_names = [id_to_label[int(logits[0][i].argmax())]]
            if word.startswith("##"):
                results[-1][0] += word[2:]
                results[-1][2][1] = offset_mapping[i][1]
            else:
                results.append([word, class_names, list(offset_mapping[i])])
        else:
            class_names = []
    return results


rss = {
    "РБК": {
        "url": "http://static.feed.rbc.ru/rbc/logical/footer/news.rss",
        "keys": [
            "title",
            "rbc_news_full-text",
            "rbc_news_pdalink",
            "rbc_news_newsmodifdate",
            # "author",
            # "rbc_news_tag",
            # "rbc_news_newsline",
            # "rbc_news_source"
        ],
        "folder": "rbc",
        "filetag": "rbc_news_news_id",
    }
}


def predict_text(text):
    """Simplified ner
    We consider that two named entities of the same type are separated
    at least by a comma or a preposition
    Так как модель плохо предсказывает B- и E-, то упрощаем разбор
    Считаем, что две сущности одного типа разделены хотя бы запятой.
    Случаи типа "Сказал министр министру" будут разобраны неправильно
    (получим одну сущность "министр министру")

    Args:
        text (_type_): _description_
    """
    sents = razdel.sentenize(text)
    ners = []
    brat_ners = []
    for sent in sents:
        ner_preds = predict(sent.text)
        last_word_ners = dict()
        sent_ners = []
        for i, (word, ners, word_pos) in enumerate(ner_preds):
            if ners == ["O"]:
                for po in last_word_ners:
                    sent_ners.append([po, *last_word_ners[po]])
                last_word_ners = dict()
                # word + space
                continue
            ners = [n for n in ners if n != "O"]
            ners = [n[2:] for n in ners]
            if not last_word_ners:
                last_word_ners = {
                    n: list(word_pos) for n in ners
                }
            else:
                intersected = set(last_word_ners.keys()).intersection(
                    set(ners)
                )
                new_entries = set(ners).difference(set(last_word_ners.keys()))
                pop_entries = set(last_word_ners.keys()).difference(set(ners))
                for intersect in intersected:
                    last_word_ners[intersect][1] = word_pos[1]
                for ne in new_entries:
                    last_word_ners[ne] = list(word_pos)
                for po in pop_entries:
                    sent_ners.append([po, *last_word_ners[po]])
                    last_word_ners.pop(po)
        for ner in sent_ners:
            ner[1] += sent.start
            ner[2] += sent.start
            ner_text = text[ner[1] : ner[2]]
            if not ner_text:
                continue
            ner.append(ner_text)
            brat_ners.append(ner)
    return brat_ners


def predict_rss():
    source_folder = "/home/denis/brat/data"
    for name, data in rss.items():
        news = feedparser.parse(data["url"])
        for entry in news["entries"]:
            texts = [entry.get(key) for key in data["keys"]]
            texts = [t if t else "" for t in texts]
            full_text = "\n\n".join(texts)
            if len(full_text) > 2000:
                continue
            if len(full_text) < 500:
                continue
            filename = entry[data["filetag"]] + ".txt"
            date = entry["rbc_news_date"].replace(".", "-")
            path = f"{source_folder}/{data['folder']}/{date}/{filename}"
            date_path = f"{source_folder}/{data['folder']}/{date}/"
            if not os.path.exists(date_path):
                os.mkdir(date_path)
            if not os.path.exists(path):
                ann_filename = path.replace(".txt", ".ann")
                preds = predict_text(full_text)
                annotation = ""
                for i, p in enumerate(preds):
                    annotation += f"T{i}\t{p[0]} {p[1]} {p[2]}\t{p[3]}\n"
                if len(preds) > 90:
                    continue
                if len(preds) < 30:
                    continue
                with open(path, "w") as f:
                    f.write(full_text)
                with open(ann_filename, "w") as f:
                    f.write(annotation)

while True:
    predict_rss()
    print(datetime.now(pytz.timezone("Europe/Moscow")))
    # every 4 hours
    time.sleep(60 * 60 * 4)
