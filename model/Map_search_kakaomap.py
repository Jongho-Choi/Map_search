import requests
import pandas as pd
import numpy as np
import folium
import Auth2 #카카오맵
import os

#import Auth
## kakao맵에서 지역 정보 저장
def find_places(name, page):
    url = 'https://dapi.kakao.com/v2/local/search/keyword.json'
    params = {'query': name, 'page': page}
    headers = {"Authorization": f"KakaoAK {Auth2.auth}"}

    total = requests.get(url, params=params, headers=headers).json()['meta']['total_count']

    if total > 30:
        places = requests.get(url, params=params, headers=headers).json()['documents']
    elif (total > 15) & (page < 3):
        places = requests.get(url, params=params, headers=headers).json()['documents']
    elif (total > 0) & (page < 2) :
        places = requests.get(url, params=params, headers=headers).json()['documents']
    else :   
        places = None
    return places, total

## 정보 전처리
def places_info(name, places, i):
    long = []
    lat = []
    place_name = []
    if places != None:
        for place in places:
            long.append(float(place['x']))
            lat.append(float(place['y']))
            place_name.append(place['place_name'])
            # road_address.append(place['road_address_name'])
            # place_url.append(place['place_url'])
            # ID.append(place['id'])

    temp_array = np.array([place_name, lat, long]).T
    df = pd.DataFrame(temp_array, columns = [name, f'Lat{i}', f'Long{i}'])
    return df

## 지역 입력하여 각각의 위치정보 획득
def info(search_names):
    df = None
    df_sum = None
    i=1
    totals = []
    for name in search_names:
        for page in range(1,4):
            places, total = find_places(name, page)
            places_df = places_info(name, places, i)

            if df is None:
                df = places_df
            elif places_df is None:
                continue
            else:
                df = pd.concat([df, places_df], join='outer', ignore_index = True)
        if df_sum is None:
            df_sum = df
        elif df is None:
            continue
        else:
            df_sum = pd.concat([df_sum, df], axis=1)
        #print(len(df))    
        totals.append(len(df))
        df = None
        i += 1
    df_sum = df_sum.astype({'Lat1':'float32', 'Lat2':'float32', 'Lat3':'float32', 'Long1':'float32', 'Long2':'float32', 'Long3':'float32'})
    return df_sum, totals

## 세 지점의 최대거리 계산
def min_distance(df_sum, totals, search_names):
    df_rows = pd.DataFrame(columns=[search_names[0],'Lat1','Long1',search_names[1],'Lat2','Long2',search_names[2],'Lat3','Long3','Lat_center','Long_center','distance'])
    row = 0
    total_row = 0

    for i in range(totals[0]):
        for j in range(totals[1]):
            for k in range(totals[2]):
                total_row = row + j + k
                lat1 = df_sum.loc[i]['Lat1']
                lat2 = df_sum.loc[j]['Lat2']
                lat3 = df_sum.loc[k]['Lat3']
                long1 = df_sum.loc[i]['Long1']
                long2 = df_sum.loc[j]['Long2']
                long3 = df_sum.loc[k]['Long3']
                lat_mean = (lat1+lat2+lat3)/3
                long_mean = (long1+long2+long3)/3

                distance = np.max([((lat_mean-lat1)**2 + (long_mean-long1)**2)**(1/2), ((lat_mean-lat2)**2 + (long_mean-long2)**2)**(1/2), ((lat_mean-lat3)**2 + (long_mean-long3)**2)**(1/2)])
                df_rows.loc[total_row] = [df_sum.loc[i][search_names[0]], lat1, long1,
                                          df_sum.loc[j][search_names[1]], lat2, long2,
                                          df_sum.loc[k][search_names[2]], lat3, long3,
                                          lat_mean, long_mean, distance]
            row = row + k
        row = row + j
    return df_rows

## distance 기준으로 가장 가까운 지점 정렬 및 인덱스 초기화
def nearest(df_rows):
    df_rows_nearest = df_rows.sort_values(by=['distance'],axis=0).reset_index(drop=True)
    return df_rows_nearest

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
def point2map(map, df_top_5, search_names):
    folium.Marker([df_top_5['Lat_center'][0], df_top_5['Long_center'][0]], tooltip='추정위치', icon=folium.Icon(icon = 'star', color = 'red')).add_to(map)
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
    os.remove('./flask_app/templates/position.html')
    map.save('./flask_app/templates/position.html')
    # map.save('./flask_app/templates/position.html')
    return map 

## 지역 검색(알고리즘 상 3개의 지역만으로 한정 함)

## 검색 지역 3개 예시
## 보편적인 명칭은 검색수가 지나치게 많아 정확성이 낮아짐
## 고유 명칭일 수록 정확성 높아짐
if __name__ == '__main__' :
    import Auth2
    search_names = ['서울송중초등학교', '금황빌딩', '햇살마루']

    ## 검색 결과
    df_sum, totals = info(search_names)
    ## 지역간 거리 확인
    df_rows = min_distance(df_sum, totals, search_names)
    ## 가장 가까운 지역 선정
    df_rows_nearest = nearest(df_rows)
    ## Top # 선정
    df_top_5 = df_rows_nearest.head(5)
    ## 기준 좌표 설정
    map = std_map(df_top_5)
    ## 맵에 지역 포인팅
    map = point2map(map, df_top_5, search_names)
    ## 3개 지역 binding
    map = draw_circle(map, df_top_5)

    map.save('./flask_app/templates/position.html')
