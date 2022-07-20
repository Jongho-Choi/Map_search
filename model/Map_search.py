import requests
import pandas as pd
import numpy as np
from scipy import spatial
import folium
from folium import plugins
import os

## Vworld맵에서 지역 정보 저장
## 각 장소별 특성 및 상태 반환
def info(name, key, url, size=1, page=1):
    params = {'request' : 'search',
              'crs' : 'EPSG:4326)',
              'query' : name,
              'size' : size,
              'page' : page,
              'type' : 'place',
              'errorformat' : 'json',
              'key' : key}
    results = requests.get(url, params=params).json()
    status = results['response']['status']
    return results, status

## 페이지 반환
def pages(data):
    return int(data['response']['record']['total'])//1000 + 1

## 모든 위치와 장소명 배열로 반환
def total_position(place, key, url, pages, size=1000):
    data = np.empty((0,3), int)
    for i in range(1, pages+1):
        places, _ = info(place, key, url, size, page=i)
        for j in range(len(places['response']['result']['items'])):
            title = places['response']['result']['items'][j]['title']
            x     = places['response']['result']['items'][j]['point']['x']
            y     = places['response']['result']['items'][j]['point']['y']
            data = np.append(data, [[x, y, title]], axis=0)
    return data

## 1. 제일 수가 적은 지역 찾고 
## 2. A, B, C(제일 적은 수) 재배치

def small_num_of_places(A,B,C,search_names):
    len_a = len(A)
    len_b = len(B)
    len_c = len(C)
    if (len_a <= len_b) and (len_a <= len_c):
        return B, C, A, [search_names[1], search_names[2], search_names[0]]
    elif (len_b <= len_a) and (len_a <= len_c):
        return A, C, B, [search_names[0], search_names[2], search_names[1]]
    else:
        return A, B, C, search_names

## 3. C를 기준으로 가장 가까운 A,B 지역 탐색
def find_nearest(A, B, C):
    ## A-C 최근접 찾기
    AC = np.empty((0,3), int)
    BC = np.empty((0,3), int)
    treeA = spatial.KDTree(A[:, :2].astype(np.float32))
    treeB = spatial.KDTree(B[:, :2].astype(np.float32))
    for C_value in C[:, :2].astype(np.float32):
        temp_AC = A[ treeA.query([C_value])[1] ]
        temp_BC = B[ treeB.query([C_value])[1] ]
        AC = np.append(AC, temp_AC, axis=0)
        BC = np.append(BC, temp_BC, axis=0)

    return AC, BC, C

## 데이터프레임으로 변경
def toDataframe(A, B, C, search_names):
    df_A = pd.DataFrame(A, columns=['Long1','Lat1', search_names[0]])
    df_B = pd.DataFrame(B, columns=['Long2','Lat2', search_names[1]])
    df_C = pd.DataFrame(C, columns=['Long3','Lat3', search_names[2]])
    df_ABC = pd.concat([df_A, df_B, df_C], axis = 1)
    df_ABC[['Long1', 'Long2', 'Long3', 'Lat1', 'Lat2', 'Lat3']] = df_ABC[['Long1', 'Long2', 'Long3', 'Lat1', 'Lat2', 'Lat3']].astype(np.float32)
    return df_ABC
    
## 세 지점의 중심좌표로 부터의 거리 계산
def min_distance(ABC):
    ABC['distance'] = np.nan
    for index, i in ABC.iterrows():
        long_center = (i['Long1'] + i['Long2']  + i['Long3'] )/3
        lat_center  = (i['Lat1'] + i['Lat2']  + i['Lat3'] )/3
        distance = np.max([((lat_center-i['Lat1'])**2 + (long_center-i['Long1'])**2)**(1/2),
                           ((lat_center-i['Lat2'])**2 + (long_center-i['Long2'])**2)**(1/2), 
                           ((lat_center-i['Lat3'])**2 + (long_center-i['Long3'])**2)**(1/2)])
        ABC.loc[index, 'Long_center'] = long_center
        ABC.loc[index, 'Lat_center'] = lat_center
        ABC.loc[index, 'distance'] = distance
    return ABC

## distance 기준으로 가장 가까운 지점 정렬 및 인덱스 초기화
def nearest(ABC):
    ABC_nearest = ABC.sort_values(by=['distance'],axis=0).reset_index(drop=True)
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
def point2map(map, df_top_5, search_names, w3w_words, key_word_):
    html_t1 = "<h5>" +  "w3w /// " + w3w_words + "<h5>" + "<hr class='one'>"
    html_t2 = "<h5>" +  "이 장소의 대표 키워드는 "+ "<h5>"
    html_t3 = "<h3>" +  "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;" + key_word_ + "<h3>"
    html_t4 = "<h5>" +  """&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                           &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;입니다."""+ "<h5>"
    html = html_t1 + html_t2 + html_t3 + html_t4
    iframe = folium.IFrame(html, width=220, height=200)
    popup = folium.Popup(iframe)

    folium.Marker([df_top_5['Lat_center'][0], df_top_5['Long_center'][0]], tooltip='키워드', popup = popup, icon=folium.Icon(icon = 'star', color = 'red')).add_to(map)
    for i in range(len(df_top_5)):
        for j in range(1,4):
            folium.Marker([df_top_5[f'Lat{j}'][i], df_top_5[f'Long{j}'][i]], tooltip=df_top_5[search_names[j-1]][i]).add_to(map)
    return map

## 3개 지역 binding
def draw_circle(map, df_top_5):
    for i in range(len(df_top_5)):
        if df_top_5['distance'][i] < 0.01:
            if i == 0:
                folium.Circle([df_top_5['Lat_center'][i],df_top_5['Long_center'][i]], radius = df_top_5['distance'][i]*100000, color = 'red', fill = 'red').add_to(map)
            else :
                folium.Circle([df_top_5['Lat_center'][i],df_top_5['Long_center'][i]], radius = df_top_5['distance'][i]*100000).add_to(map)
    #os.remove('./flask_app/templates/position.html')
    #map.save('./flask_app/templates/position.html')
    # map.save('./flask_app/templates/position.html')
    return map 

## 미니맵 
def mini_map(map):
    minimap = plugins.MiniMap()
    map.add_child(minimap)
    return map

## 지역 검색(알고리즘 상 3개의 지역만으로 한정 함)

## 검색 지역 3개 예시
## 보편적인 명칭은 검색수가 지나치게 많아 정확성이 낮아짐
## 고유 명칭일 수록 정확성 높아짐
if __name__ == '__main__' :
    import Auth
    ## 기본 정보
    place1, place2, place3 = '호구포역', '미니스톱', 'CGV'
    key = Auth.auth
    url = "https://api.vworld.kr/req/search"
    search_names = [place1, place2, place3]
    ## 각 장소별 특성 및 상태 반환
    A, A_status = info(place1, key, url)
    B, B_status = info(place2, key, url)
    C, C_status = info(place3, key, url) ## 검색이 안될경우 status = 'NOT_FOUND'
    ## 페이지 반환
    A_pages = pages(A)
    B_pages = pages(B)
    C_pages = pages(C)
    ## 모든 위치와 장소명 배열로 반환
    A = total_position(place1, key, url, A_pages)
    B = total_position(place2, key, url, B_pages)
    C = total_position(place3, key, url, C_pages)
    ## 1. 제일 수가 적은 지역 찾고 
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
