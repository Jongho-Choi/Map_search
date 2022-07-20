from transformers import PreTrainedTokenizerFast, GPT2LMHeadModel
import torch
import pickle
from konlpy.tag import Okt
from collections import Counter
import os

# print(os.path.realpath(__file__))

def import_model():
    ## Load tokenizer
    with open("./data/tokenizer.pkl","rb") as fr:
        tokenizer = pickle.load(fr)
    ## Load KoGPT2 model
    with open("./data/model.pkl","rb") as fr:
        model = pickle.load(fr)
    return tokenizer, model

def words2text(words, tokenizer, model):
    input_ids = tokenizer.encode(words)
    gen_ids = model.generate(torch.tensor([input_ids]),
                            max_length=64,
                            repetition_penalty=1.5,
                            pad_token_id=tokenizer.pad_token_id,
                            eos_token_id=tokenizer.eos_token_id,
                            bos_token_id=tokenizer.bos_token_id,
                            use_cache=True)
    generated = tokenizer.decode(gen_ids[0,:].tolist())
    return generated

def key_word(generated):
    # Okt 객체 선언
    okt = Okt()
    noun = okt.nouns(generated)

    # 한 글자 제외
    for i,v in enumerate(noun):
        if len(v)<2:
            noun.pop(i)
                
    count = Counter(noun)
        
    # 명사 빈도 카운트
    noun_list = count.most_common(1)
    return noun_list[0][0]

if __name__ == '__main__' :
    ## 기본 정보
    words = '안심, 곧바로, 색깔'
    tokenizer, model = import_model()
    generated = words2text(words, tokenizer, model)
    key_word_ = key_word(generated)
