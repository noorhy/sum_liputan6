#!/usr/bin/env python
# coding: utf-8

import json
import glob
import json
import re, os

regex_bracket = r"\(([^)]+)\)"
punctuation = '.,!?\'\[]();"'
unknown = set()

def cleanhtml(raw_html):
    cleanr = re.compile('<.*?>')
    return re.sub(cleanr, '', raw_html)

def clean_article(article):
    article = cleanhtml(article)
    article = article.replace('\n', ' ')
    sentences = []
    words = []
    for word in article.split(' '):
        word = word.replace('–', '-')
        word = word.replace('__', '').replace('--', '')
        word = word.replace('&quot', '"')
        word = word.strip()
        if len(word) > 0:
            tokens = re.findall(r"[\w'\%\&\-\/\=\+\*$£]+|[\[\]().,!?\:;\"\“\”]", word)
            words += tokens
            try:
                if tokens[-1] in '.!?':
                    sentences.append(words)
                    words = []
            except:
                unknown.add(word)
    if words != []:
        if words[-1][-1] not in '.!?':
            words.append('.')
        sentences.append(words)
    return sentences

def get_string(sentences):
    all_sentence = []
    for sentence in sentences:
        all_sentence += sentence
    return ' '.join(all_sentence)


def process(PATH, DST):
    os.makedirs(DST, exist_ok=True)
    files = glob.glob(PATH)
    for file in files:
        data = json.load(open(file))
        article = data['content']
        summary = data['summary']
        if (len(article.split())>30 and len(summary.split())>10):
            article_arr = clean_article(article)
            summary_arr = clean_article(summary)
            clean_data = {'id': data['id'], 'url': data['url']}
            article_v2 = get_string(article_arr).split()
            summary_v2 = get_string(summary_arr).split()

            if len(article_v2) < len(article.split()) or len(summary_v2) < len(summary.split()):
                print(data['id'])

            clean_data['clean_article'] = article_arr
            clean_data['clean_summary'] = summary_arr
            with open(DST+str(clean_data['id'])+'.json', 'w') as json_file:
                json.dump(clean_data, json_file)


process('data/raw/train/*', 'data/clean/train/')
process('data/raw/dev/*', 'data/clean/dev/')
process('data/raw/test/*', 'data/clean/test/')
print(unknown)

