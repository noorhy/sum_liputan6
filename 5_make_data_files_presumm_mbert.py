import sys
import os
import shutil
import json, glob
import torch
from transformers import BertTokenizer

SHARD_SIZE = 2000
MIN_SRC_NSENTS = 3
MAX_SRC_NSENTS = 100
MIN_SRC_NTOKENS_PER_SENT = 5
MAX_SRC_NTOKENS_PER_SENT = 200
MIN_TGT_NTOKENS = 5
MAX_TGT_NTOKENS = 500
USE_BERT_BASIC_TOKENIZER = False

main_path = 'data/clean/'
data_path = 'data/presumm/'

class BertData():
    def __init__(self):
        self.tokenizer = BertTokenizer.from_pretrained('bert-base-multilingual-uncased', do_lower_case=True)
        self.sep_token = '[SEP]'
        self.cls_token = '[CLS]'
        self.pad_token = '[PAD]'
        self.tgt_bos = '[unused1]'
        self.tgt_eos = '[unused2]'
        self.tgt_sent_split = '[unused3]'
        self.sep_vid = self.tokenizer.vocab[self.sep_token]
        self.cls_vid = self.tokenizer.vocab[self.cls_token]
        self.pad_vid = self.tokenizer.vocab[self.pad_token]
    
    def preprocess(self, src, tgt, sent_labels, use_bert_basic_tokenizer=False, is_test=False):

        original_src_txt = [' '.join(s) for s in src]

        idxs = [i for i, s in enumerate(src) if (len(s) > MIN_SRC_NTOKENS_PER_SENT)]

        _sent_labels = [0] * len(src)
        for l in sent_labels:
            _sent_labels[l] = 1

        src = [src[i][:MAX_SRC_NTOKENS_PER_SENT] for i in idxs]
        sent_labels = [_sent_labels[i] for i in idxs]
        src = src[:MAX_SRC_NSENTS]
        sent_labels = sent_labels[:MAX_SRC_NSENTS]

        if len(src) < MIN_SRC_NSENTS:
            return None

        src_txt = [' '.join(sent) for sent in src]
        text = f' {self.sep_token} {self.cls_token} '.join(src_txt)

        src_subtokens = self.tokenizer.tokenize(text)

        src_subtokens = [self.cls_token] + src_subtokens + [self.sep_token]
        src_subtoken_idxs = self.tokenizer.convert_tokens_to_ids(src_subtokens)
        _segs = [-1] + [i for i, t in enumerate(src_subtoken_idxs) if t == self.sep_vid]
        segs = [_segs[i] - _segs[i - 1] for i in range(1, len(_segs))]
        segments_ids = []
        for i, s in enumerate(segs):
            segments_ids += s * [0] if (i % 2 == 0) else s * [1]
        cls_ids = [i for i, t in enumerate(src_subtoken_idxs) if t == self.cls_vid]
        sent_labels = sent_labels[:len(cls_ids)]

        tgt_subtokens_str = '[unused1] ' + ' [unused3] '.join(
            [' '.join(self.tokenizer.tokenize(' '.join(tt))) for tt in tgt]) + ' [unused2]'
        tgt_subtoken = tgt_subtokens_str.split()[:MAX_TGT_NTOKENS]
        if len(tgt_subtoken) < MIN_TGT_NTOKENS:
            return None

        tgt_subtoken_idxs = self.tokenizer.convert_tokens_to_ids(tgt_subtoken)

        tgt_txt = '<q>'.join([' '.join(tt) for tt in tgt])
        src_txt = [original_src_txt[i] for i in idxs]

        return src_subtoken_idxs, sent_labels, tgt_subtoken_idxs, segments_ids, cls_ids, src_txt, tgt_txt

def read(fname):
    data = json.loads(open(fname, 'r').readline())
    return data['clean_article'], data['clean_summary'], data['extractive_summary']

def format_to_bert(path):
    bert = BertData()
    files = glob.glob(path)
    p_ct = 0
    dataset = []
    for fname in files:
        #process
        source, tgt, sent_labels = read(fname)
        b_data = bert.preprocess(source, tgt, sent_labels)
        if (b_data is None):
            continue
        src_subtoken_idxs, sent_labels, tgt_subtoken_idxs, segments_ids, cls_ids, src_txt, tgt_txt = b_data
        b_data_dict = {"src": src_subtoken_idxs, "tgt": tgt_subtoken_idxs,
                       "src_sent_labels": sent_labels, "segs": segments_ids, 'clss': cls_ids,
                       'src_txt': src_txt, "tgt_txt": tgt_txt}
        dataset.append(b_data_dict)
        if len(dataset) >= SHARD_SIZE:
            pt_file = data_path + "{:s}.{:d}.bert.pt".format(path.split('/')[-2], p_ct)
            torch.save(dataset, pt_file)
            dataset = []
            p_ct += 1
    if len(dataset) > 0:
        pt_file = data_path + "{:s}.{:d}.bert.pt".format(path.split('/')[-2], p_ct)
        torch.save(dataset, pt_file)
        dataset = []
        p_ct += 1

if os.path.exists(data_path):
    shutil.rmtree(data_path)
os.mkdir(data_path)
format_to_bert(f'{main_path}train/*')
format_to_bert(f'{main_path}dev/*')
format_to_bert(f'{main_path}test/*')
