from flask import Flask, render_template, request
from model.Map_search import info, pages, small_num_of_places, find_nearest, toDataframe, min_distance
from model.Map_search import nearest, std_map, point2map, draw_circle, mini_map, get_data, get_position
from model.NLP import import_model, toText
from model.w3w import to_w3w
from model.memory_check import memory_usage
import gc, concurrent.futures, time

app = Flask(__name__, static_url_path="/static")

@app.route('/', methods=['GET', 'POST'])
def index():
    ## 메모리 사용량 확인용
    memory_usage('start ...')
    try:
        if request.method == 'GET':    
            lat = 37.566535
            long = 126.97796919
            zoom = 7.2
            
            return render_template('main.html', lat=lat, long=long, zoom=zoom),200

        if request.method == 'POST':
            test = '여기닷!!'
            if request.form['id_1'] and request.form['id_2'] and request.form['id_3']:
                place1 = request.form['id_1']
                place2 = request.form['id_2']
                place3 = request.form['id_3']

                search_names = [place1, place2, place3]

                ## 각 장소별 특성 및 상태 반환(쓰레드 적용)
                temp = []
                with concurrent.futures.ThreadPoolExecutor() as executor :
                    results = executor.map(info, search_names)
                    for result in results:
                        temp.append(result)

                A_place, A_status = temp[0]
                if A_status != 'OK':
                    return render_template('error.html', text = '', place = place1), 400
                B_place, B_status = temp[1]
                if B_status != 'OK':
                    return render_template('error.html', text = '', place = place2), 400
                C_place, C_status = temp[2] ## 검색이 안될경우 status = 'NOT_FOUND'    
                if C_status != 'OK':
                    return render_template('error.html', text = '', place = place3), 400

                ## 페이지 반환
                A_pages = pages(A_place)
                B_pages = pages(B_place)
                C_pages = pages(C_place)
                places = [place1, place2, place3]
                ABC_page = [A_pages, B_pages, C_pages]
                start = time.perf_counter()
                A_place = get_data(places[0], ABC_page[0])
                B_place = get_data(places[1], ABC_page[1])
                C_place = get_data(places[2], ABC_page[2])

                A_place = get_position(A_place, ABC_page[0])
                B_place = get_position(B_place, ABC_page[1])
                C_place = get_position(C_place, ABC_page[2])
                finish = time.perf_counter()
                print(f'1 - Finished in {round(finish-start, 2)} second(s)')

                ## 1. 제일 수가 적은 지역 찾고 
                ## 2. A, B, C(제일 적은 수) 재배치
                ## 3. C를 기준으로 가장 가까운 A,B 지역 탐색
                start = time.perf_counter()
                A_place, B_place, C_place, search_names = small_num_of_places(A_place, B_place, C_place, search_names)
                A_place, B_place, C_place = find_nearest(A_place, B_place, C_place)
                ## 데이터프레임으로 변경
                ABC_place = toDataframe(A_place, B_place, C_place, search_names)
                ## 세 지점의 중심좌표로 부터의 거리 계산
                ABC_place = min_distance(ABC_place)
                              
                ## distance 기준으로 가장 가까운 지점 정렬 및 인덱스 초기화
                ABC_nearest = nearest(ABC_place)
                ## Top 5 선정
                df_top_5 = ABC_nearest.head(5)
                del ABC_nearest, ABC_place, A_place, B_place, C_place, places, ABC_page
                ## 좌표로 w3w 얻기
                w3w_words = to_w3w(df_top_5)
                ## words로 문장 얻기
                words = w3w_words.replace('.', ', ')
                tokenizer, model = import_model()

                word = words.replace(' ', '').split(',')
                tokenizers = [tokenizer,tokenizer,tokenizer]
                models = [model,model,model]
                sentence = []
                with concurrent.futures.ThreadPoolExecutor() as executor :
                    results = executor.map(toText, word, tokenizers, models)
                    for result in results:
                        sentence.append(result)
                finish = time.perf_counter()
                print(f'4 - Finished in {round(finish-start, 2)} second(s)')
                
                memory_usage('model start ...')
                ### 메모리 삭제
                del tokenizer, tokenizers, model, models, words
                gc.collect()
                memory_usage('model end ...')

                #key_word_ = key_word(sentence, words)
                #memory_usage('morpheme transformation')

                ### !오류확인!
                # if test == '여기닷!!':
                #     return render_template('error.html', text = '', place = test), 400

                ## 기준 좌표 설정
                map = std_map(df_top_5)
                ## 맵에 지역 포인팅
                map = point2map(map, df_top_5, search_names, w3w_words, sentence)
                ## 3개 지역 binding
                map = draw_circle(map, df_top_5)
                ## 미니맵
                map = mini_map(map)
                ## folium 지도 object --> html
                map = map._repr_html_()
                ## html 내용 수정 (map size 조절)
                map = map[:37] + 'position: absolute;top: 0;bottom: 0;right: 0;left: 0;' + map[94:]
                ## 잔여 메모리 삭제!
                del df_top_5, search_names, w3w_words, sentence
                gc.collect()
                return render_template('main2.html', place1=place1, place2=place2, place3=place3, map=map), 200
            else:
                text_1 = ''
                text_2 = ''
                text_3 = ''
                if request.form['id_1'] == '' :
                    text_1 = '첫번째'
                
                if request.form['id_2'] == '' :
                    text_2 = '두번째'
                
                if request.form['id_3'] == '' :
                    text_3 = '세번째'
                text = text_1 + ' ' + text_2 + ' ' + text_3

                return render_template('error.html', text = text, place = ''), 400
        
    except Exception as e:    
        return 'HTML을 불러올수 없습니다.' + e, 400

@app.route('/about')
def about():

    return render_template('about.html'),200

@app.route('/services')
def services():

    return render_template('services.html'),200

@app.route('/contact')
def contact():

    return render_template('contact.html'),200

@app.route('/thanks')
def thanks():

    return render_template('thankyou.html'),200

if __name__ == '__main__':
    app.run(port=8080, debug=True)