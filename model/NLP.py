#from transformers import PreTrainedTokenizerFast, GPT2LMHeadModel
import pickle
import torch
#from konlpy.tag import Okt
#from collections import Counter
import re

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

def key_word(generated, words):
    # Okt 객체 선언
    okt = Okt()
    print(generated)
    noun = okt.nouns(generated)
    print('okt', noun)
    # 한 글자 제외
    words = words.replace(" ", "").split(',')
    for i,v in enumerate(noun):
        if len(v)<2:
            noun.pop(i)
        if v in words :
            noun.pop(i)
    count = Counter(noun)
    noun_list = count.most_common(1)
    print(noun_list[0][0])
    return noun_list[0][0]

# 주어진 단어 사용하여 문장 만들기
# 1. 단어1 -> 문장1
# 2. 문장1 + 단어2 -> 문장2
# 3. 문장3 + 단어3 -> 문장3(최종문장)

def toText(words, tokenizer, model):
    word = words.replace(' ', '').split(',')
    sentence = ''
    point = 0
    i = 1
    for v in word:
        text = sentence +' '+ v
        print(f'주어진 단어 {i} :', v)
        input_ids = tokenizer.encode(text)
        for j in range(50):
            point1 = []
            gen_ids = model.generate(
                torch.tensor([input_ids]),
                max_length=point+21,
                repetition_penalty=1.6,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
                bos_token_id=tokenizer.bos_token_id,
                use_cache=True,
                do_sample=True,
                temperature=0.7,
                text_size=20,
                top_p=0.95,
                top_k=50)
            
            generated = tokenizer.decode(gen_ids[0,:].tolist())
            point1.append([0,generated.find('.', point)])
            point1.append([1,generated.find(',', point)])
            point1.append([2,generated.find('?', point)])
            point1.append([3,generated.find('!', point)])
            test = []
            for index in range(4):
                if point1[index] == -1:
                    point1[index][1] = point + 21
                elif point1[index][1] < (point + 5) or point1[index][1] >= (point + 20) :
                    point1[index][1] = point + 21
            point1.sort(key=lambda x:x[1])
            if point1[0][1] == (point + 21) :
                continue
            else :
                break
        
        sentence = generated[:point1[0][1]+1]
        print(f'주어진 문장 {i} :', generated)
        print(f'완료된 문장 {i} :', generated[point:point1[0][1]+1])
        print('')
        point = point1[0][1]+1
        i += 1
    
    sentence = re.sub('[^0-9가-힣.,!? ]', '', sentence)
    
    print('전체 : ', sentence)
    return sentence

if __name__ == '__main__' :
    ## 기본 정보
    words = '안심, 곧바로, 색깔'
    tokenizer, model = import_model()
    generated = words2text(words, tokenizer, model)
    key_word_ = key_word(generated)
