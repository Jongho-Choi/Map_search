import what3words
def to_w3w(df_top_5, w3w_auth):
    lat = df_top_5['Lat_center'][0]
    long = df_top_5['Long_center'][0]
    geocoder = what3words.Geocoder(w3w_auth)
    result = geocoder.convert_to_3wa(what3words.Coordinates(lat, long), language='ko')
    words = result['words']
    return words