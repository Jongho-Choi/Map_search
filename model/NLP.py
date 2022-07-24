#from transformers import PreTrainedTokenizerFast, GPT2LMHeadModel
import pickle
import torch
# from konlpy.tag import Okt
# from collections import Counter
import re
# from model.memory_check import memory_usage

## KoGPT2, tokenizer 복호화
def import_model():
    ## Load tokenizer
    with open("./data/tokenizer.pkl","rb") as fr:
        tokenizer = pickle.load(fr)
    ## Load KoGPT2 model
    with open("./data/model.pkl","rb") as fr:
        model = pickle.load(fr)
    return tokenizer, model

## 주어진 연속된 단어로 문장 제작
def words2text(words, tokenizer, model):
    input_ids = tokenizer.encode(words)
    gen_ids = model.generate(torch.tensor([input_ids]),
                            max_length=32,
                            repetition_penalty=1.6,
                            pad_token_id=tokenizer.pad_token_id,
                            eos_token_id=tokenizer.eos_token_id,
                            bos_token_id=tokenizer.bos_token_id,
                            use_cache=True)
    generated = tokenizer.decode(gen_ids[0,:].tolist())
    return generated

# def key_word(generated, words):
#     # Okt 객체 선언
#     okt = Okt()
#     print(generated)
#     memory_usage('before okt.nouns')
#     noun = okt.nouns(generated)
#     memory_usage('after okt.nouns')

#     print('okt', noun)
#     # 한 글자 제외
#     words = words.replace(" ", "").split(',')
#     for i,v in enumerate(noun):
#         if len(v)<2:
#             noun.pop(i)
#         if v in words :
#             noun.pop(i)
#     count = Counter(noun)
#     noun_list = count.most_common(1)
#     del generated, okt, noun, words, i, v, count
#     memory_usage('del okt.nouns')
#     print(noun_list[0][0])
#     return noun_list[0][0]

# 주어진 단어 사용하여 문장 만들기
# 1. 단어1 -> 문장1
# 2. 문장1 + 단어2 -> 문장2
# 3. 문장3 + 단어3 -> 문장3(최종문장)
def toText(words, tokenizer, model):
    word = words.replace(' ', '').split(',')
    sentence = []
    point = 0
    i = 0
    for v in word:
        if i == 0 :
          text = v
        else:
          text = sentence[i-1] +' '+ v
        print(f'주어진 단어 {i+1} :', v)
        input_ids = tokenizer.encode(text)
        point1 = []
        gen_ids = model.generate(
            torch.tensor([input_ids]),
            max_length=point+20,
            repetition_penalty=1.9,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
            bos_token_id=tokenizer.bos_token_id,
            use_cache=True)
            
            ## do_sample=True 적용시마다 다른 문장이 생성됨
            # do_sample=True, 
            # temperature=0.8,
            # top_p=0.95,
            # top_k=50

        generated = tokenizer.decode(gen_ids[0,:].tolist())
        point1.append([0,generated.find('.', point)])
        point1.append([1,generated.find(',', point)])
        point1.append([2,generated.find('?', point)])
        point1.append([3,generated.find('!', point)])
        test = []
        
        for index in range(4):
            if point1[index][1] < (point + 5):
                point1[index][1] = point + 21

        point1.sort(key=lambda x:x[1])

        
        print(f'주어진 문장 {i+1} :', generated)
        
        if point1[0][1] == (point + 21) :
            sentence.append(generated[point:point1[0][1]+1] +'...')
            point = point1[0][1]-point + 3 + 2
        else :
            sentence.append(generated[point:point1[0][1]+1])
            point = point1[0][1]-point + 2

        print(f'완료된 문장 {i+1} :', sentence[i])
        print('')
        
        i += 1
    
    for i in range(3):
        sentence[i] = re.sub('[^0-9가-힣.,!?\n ]', '', sentence[i])
    
    print('전체 : ', sentence)
    return sentence

if __name__ == '__main__' :
    ## 기본 정보
    words = '안심, 곧바로, 색깔'
    tokenizer, model = import_model()
    generated = words2text(words, tokenizer, model)
    #key_word_ = key_word(generated)
