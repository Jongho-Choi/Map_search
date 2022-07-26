import requests, folium, concurrent
import pandas as pd
import numpy as np
from scipy import spatial
from folium import plugins
from model.Auth import auth, url

## 지역 검색(알고리즘 상 3개의 지역만으로 한정 함)
## 보편적인 명칭은 검색수가 지나치게 많아 정확성이 낮아짐
## 고유 명칭일 수록 정확성 높아짐
## Vworld 보다 Kakao map 정확도 높음
## Kakao map 보다 Vworld가 검색 가능량이 많음

## Vworld맵에서 지역 정보 저장
## 각 장소별 특성 및 상태 반환
def info(name, size=1, page=1):
    params = {'request' : 'search',
              'crs' : 'EPSG:4326)',
              'query' : name,
              'size' : size,
              'page' : page,
              'type' : 'place',
              'errorformat' : 'json',
              'key' : auth}
    results = requests.get(url, params=params).json()
    status = results['response']['status']
    return results, status

## 페이지 반환
def pages(data):
    return int(data['response']['record']['total'])//1000 + 1

# ## 모든 위치와 장소명 배열로 반환
# def total_position(place, pages, size=1000):
#     data = np.empty((0,3), int)
#     for i in range(1, pages+1):
#         places, _ = info(place, size, page=i)
#         for j in range(len(places['response']['result']['items'])):
#             title = places['response']['result']['items'][j]['title']
#             x     = places['response']['result']['items'][j]['point']['x']
#             y     = places['response']['result']['items'][j]['point']['y']
#             data = np.append(data, [[x, y, title]], axis=0)
#     return data

## API 호출
def get_data(place, page, size = 1000):
    places = [place] * page
    size = [size] * page
    pages = [i for i in range(1, page+1)]

    temp = []
    with concurrent.futures.ThreadPoolExecutor() as executor :
        results = executor.map(info, places, size, pages)
        for place in results:
            temp.append(place)

    return temp

## 위치데이터 획득
def get_position(place, page):
    data = np.empty((0,3), int)
    if page == 1:
        data = get_position2(place, 0, page)
    elif page == 2:
        start_page = [0, int(page/2)]
        end_page = [int(page/2), page]
        place2 = [place, place]
    elif page == 3:
        start_page = [0, int(page/3), int(page*2/3)]
        end_page = [int(page/3), int(page*2/3), page]
        place2 = [place, place, place]
    elif page == 4:
        start_page = [0, int(page/4), int(page*2/4), int(page*3/4)]
        end_page = [int(page/4), int(page*2/4), int(page*3/4), page]
        place2 = [place, place, place,place]
    else :
        start_page = [0, int(page/5), int(page*2/5), int(page*3/5), int(page*4/5)]
        end_page = [int(page/5), int(page*2/5), int(page*3/5), int(page*4/5), page]
        place2 = [place, place, place, place, place]
    if page == 1:
        pass
    else :
        with concurrent.futures.ThreadPoolExecutor() as executor :
            results = executor.map(get_position2, place2, start_page, end_page)
            for place in results:
                data = np.append(data, place, axis = 0)

    return data

def get_position2(place, start_page, end_page):
    data = np.empty((0,3), int)
    for i in range(start_page, end_page):
        for j in range(len(place[i][0]['response']['result']['items'])):
            title = place[i][0]['response']['result']['items'][j]['title']
            x     = place[i][0]['response']['result']['items'][j]['point']['x']
            y     = place[i][0]['response']['result']['items'][j]['point']['y']
            data = np.append(data, [[x, y, title]], axis=0)
    return data

## 1. 제일 수가 적은 지역 찾고 
## 2. A, B, C(제일 적은 수) 재배치
def small_num_of_places(A_place,B_place,C_place,search_names):
    len_a = len(A_place)
    len_b = len(B_place)
    len_c = len(C_place)
    if (len_a <= len_b) and (len_a <= len_c):
        return B_place, C_place, A_place, [search_names[1], search_names[2], search_names[0]]
    elif (len_b <= len_a) and (len_a <= len_c):
        return A_place, C_place, B_place, [search_names[0], search_names[2], search_names[1]]
    else:
        return A_place, B_place, C_place, search_names

## 3. C를 기준으로 가장 가까운 A,B 지역 탐색
def find_nearest(A_place, B_place, C_place):
    ## A-C 최근접 찾기
    AC_place = np.empty((0,3), int)
    BC_place = np.empty((0,3), int)
    treeA = spatial.KDTree(A_place[:, :2].astype(np.float32))
    treeB = spatial.KDTree(B_place[:, :2].astype(np.float32))
    for C_value in C_place[:, :2].astype(np.float32):
        temp_AC = A_place[ treeA.query([C_value])[1] ]
        temp_BC = B_place[ treeB.query([C_value])[1] ]
        AC_place = np.append(AC_place, temp_AC, axis=0)
        BC_place = np.append(BC_place, temp_BC, axis=0)
    return AC_place, BC_place, C_place

## 데이터프레임으로 변경
def toDataframe(A_place, B_place, C_place, search_names):
    df_A = pd.DataFrame(A_place, columns=['Long1','Lat1', search_names[0]])
    df_B = pd.DataFrame(B_place, columns=['Long2','Lat2', search_names[1]])
    df_C = pd.DataFrame(C_place, columns=['Long3','Lat3', search_names[2]])
    df_ABC = pd.concat([df_A, df_B, df_C], axis = 1)
    df_ABC[['Long1', 'Long2', 'Long3', 'Lat1', 'Lat2', 'Lat3']] = df_ABC[['Long1', 'Long2', 'Long3', 'Lat1', 'Lat2', 'Lat3']].astype(np.float32)
    return df_ABC
    
## 세 지점의 중심좌표로 부터의 거리 계산
def min_distance(ABC_place):
    ABC_place['distance'] = np.nan
    for index, i in ABC_place.iterrows():
        long_center = (i['Long1'] + i['Long2']  + i['Long3'] )/3
        lat_center  = (i['Lat1'] + i['Lat2']  + i['Lat3'] )/3
        distance = np.max([((lat_center-i['Lat1'])**2 + (long_center-i['Long1'])**2)**(1/2),
                           ((lat_center-i['Lat2'])**2 + (long_center-i['Long2'])**2)**(1/2), 
                           ((lat_center-i['Lat3'])**2 + (long_center-i['Long3'])**2)**(1/2)])
        ABC_place.loc[index, 'Long_center'] = long_center
        ABC_place.loc[index, 'Lat_center'] = lat_center
        ABC_place.loc[index, 'distance'] = distance
    return ABC_place

## distance 기준으로 가장 가까운 지점 정렬 및 인덱스 초기화
def nearest(ABC_place):
    ABC_nearest = ABC_place.sort_values(by=['distance'],axis=0).reset_index(drop=True)
    return ABC_nearest

## 기준 좌표 설정
def std_map(df_top_5, zoom=12):
    loc = []
    lat_center = np.mean(df_top_5['Lat_center'].mean())
    long_center = np.mean(df_top_5['Long_center'].mean())
    map = folium.Map(location=[lat_center,long_center],
                    zoom_start=zoom
                    )
    ## map의 name, id를 임의로 지정     
    map._name = "map"
    map._id = "2"    
    return map

## 맵에 지역 포인팅
def point2map(map, df_top_5, search_names, w3w_words, sentence):
    html_t1 = "<h5>" +  "w3w /// " + w3w_words + "<h5>" + "<hr>"
    html_t2 = "<h5>" +  "&nbsp;&nbsp;" + sentence[0] + "<h5>"
    html_t3 = "<h5>" +  "&nbsp;&nbsp;" + sentence[1] + "<h5>"
    html_t4 = "<h5>" +  "&nbsp;&nbsp;" + sentence[2] + "<h5>"
    
    html = html_t1 + html_t2 + html_t3 + html_t4
    iframe = folium.IFrame(html, width=290, height=180)
    popup = folium.Popup(iframe)

    folium.Marker([df_top_5['Lat_center'][0], df_top_5['Long_center'][0]], tooltip='이 장소의 의미는?', popup = popup, icon=folium.Icon(icon = 'star', color = 'red')).add_to(map)
    for i in range(len(df_top_5)):
        for j in range(1,4):
            folium.Marker([df_top_5[f'Lat{j}'][i], df_top_5[f'Long{j}'][i]], tooltip=df_top_5[search_names[j-1]][i]).add_to(map)
    return map

## 3개 지역 binding
def draw_circle(map, df_top_5):
    for i in range(len(df_top_5)):
        if i == 0:
            folium.Circle([df_top_5['Lat_center'][i],df_top_5['Long_center'][i]], radius = df_top_5['distance'][i]*120000, color = 'red', fill = 'red').add_to(map)
        if df_top_5['distance'][i] < 0.015:
            folium.Circle([df_top_5['Lat_center'][i],df_top_5['Long_center'][i]], radius = df_top_5['distance'][i]*120000).add_to(map)
    # os.remove('./flask_app/templates/position.html')
    # map.save('./flask_app/templates/position.html')

    return map 

## 미니맵 
def mini_map(map):
    minimap = plugins.MiniMap()
    map.add_child(minimap)
    return map

if __name__ == '__main__' :
    ## 테스트
    place1, place2, place3 = '호구포역', '미니스톱', 'CGV'
    url = "https://api.vworld.kr/req/search"
    search_names = [place1, place2, place3]
    ## 각 장소별 특성 및 상태 반환
    A, A_status = info(place1)
    B, B_status = info(place2)
    C, C_status = info(place3) ## 검색이 안될경우 status = 'NOT_FOUND'
    ## 페이지 반환
    A_pages = pages(A)
    B_pages = pages(B)
    C_pages = pages(C)
    ## 모든 위치와 장소명 배열로 반환
    # A = total_position(place1, A_pages)
    # B = total_position(place2, B_pages)
    # C = total_position(place3, C_pages)
    # ## 1. 제일 수가 적은 지역 찾고 
    ## 2. A, B, C(제일 적은 수) 재배치
    ## 3. C를 기준으로 가장 가까운 A,B 지역 탐색
    A, B, C, search_names = small_num_of_places(A, B, C, search_names)
    A, B, C = find_nearest(A, B, C)
    ## 데이터프레임으로 변경
    ABC = toDataframe(A, B, C, search_names)
    ## 세 지점의 중심좌표로 부터의 거리 계산
    ABC = min_distance(ABC)
    ## distance 기준으로 가장 가까운 지점 정렬 및 인덱스 초기화
    ABC_nearest = nearest(ABC)
    ## Top 5 선정
    df_top_5 = ABC_nearest.head(5)
    ## 기준 좌표 설정
    map = std_map(df_top_5)
    ## 맵에 지역 포인팅
    map = point2map(map, df_top_5, search_names)
    ## 3개 지역 binding
    map = draw_circle(map, df_top_5)
    ## 미니맵
    map = mini_map(map)

    map.save('./flask_app/templates/position.html')
