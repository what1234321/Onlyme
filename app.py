
from flask import Flask, render_template, request, jsonify
import json
import requests
from datetime import datetime, timedelta, timezone
KST = timezone(timedelta(hours=9))

app = Flask(__name__)
API_KEY = '9777155c8a3cc183254aee7ad5ebbafe'

city_map = {
    '서울': 'Seoul', '부산': 'Busan', '대구': 'Daegu', '인천': 'Incheon', '광주': 'Gwangju', '대전': 'Daejeon',
    '울산': 'Ulsan', '세종': 'Sejong', '수원': 'Suwon', '춘천': 'Chuncheon', '청주': 'Cheongju', '전주': 'Jeonju',
    '목포': 'Mokpo', '창원': 'Changwon', '진주': 'Jinju', '안동': 'Andong', '포항': 'Pohang', '강릉': 'Gangneung',
    '속초': 'Sokcho', '평택': 'Pyeongtaek', '김해': 'Gimhae', '양산': 'Yangsan', '구미': 'Gumi', '여수': 'Yeosu',
    '순천': 'Suncheon', '군산': 'Gunsan', '김천': 'Gimcheon', '제주': 'Jeju'
}

HISTORY_FILE = 'history.json'
WEATHER_HISTORY_FILE = 'weather_history.json'

from datetime import datetime, timedelta, timezone  # 파일 상단에 추가

KST = timezone(timedelta(hours=9))  # 한국 시간대 설정

def save_search_history(city):
    # 도시 이름 변환
    if city in city_map:
        kor = city
        eng = city_map[city]
    elif city in city_map.values():
        eng = city
        kor = next(k for k, v in city_map.items() if v == city)
    else:
        # 못 찾는 경우, 영문만 그대로 출력
        kor = city
        eng = city

    display_city = f"{kor} ({eng})"  # ✅ 한글+영문 병기
    
    try:
        with open(HISTORY_FILE, 'r') as f:
            history = json.load(f)
    except FileNotFoundError:
        history = []
    history_entry = {
        'city': display_city,
        'timestamp': datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')
    }
    history.append(history_entry)
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=4)

@app.route('/history')
def view_history():
    try:
        with open(HISTORY_FILE, 'r') as f:
            history = json.load(f)
    except FileNotFoundError:
        history = []
    return render_template('history.html', history=history)

def save_weather_history(city, weather):
    today = datetime.now().strftime('%Y-%m-%d')
    try:
        with open(WEATHER_HISTORY_FILE, 'r') as f:
            all_history = json.load(f)
    except FileNotFoundError:
        all_history = {}
    city_history = all_history.get(city, [])
    for entry in city_history:
        if entry['date'] == today:
            entry['temperature'] = weather['temperature']
            entry['humidity'] = weather['humidity']
            break
    else:
        city_history.append({
            'date': today,
            'temperature': weather['temperature'],
            'humidity': weather['humidity']
        })
    city_history = city_history[-3:]
    all_history[city] = city_history
    with open(WEATHER_HISTORY_FILE, 'w') as f:
        json.dump(all_history, f, indent=4)

def get_recent_weather_data(city):
    try:
        with open(WEATHER_HISTORY_FILE, 'r') as f:
            all_history = json.load(f)
            return all_history.get(city, [])
    except FileNotFoundError:
        return []

def get_weather(city):
    # 한글 도시명을 영문으로 변환
    if city in city_map:
        city = city_map[city]

    url = f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric&lang=kr'
    response = requests.get(url)
    data = response.json()
    if data.get('cod') != 200:
        return {'city': city, 'error': '날씨 정보를 불러올 수 없습니다.'}
    return {
        'city': city,
        'temperature': data['main']['temp'],
        'humidity': data['main']['humidity'],
        'description': data['weather'][0]['description'],
        'rain': data.get('rain', {}).get('1h', 0),
        'error': None
    }
    
def classify_weather_type(description):
    if '비' in description or '소나기' in description:
        return 'rainy'
    elif '눈' in description:
        return 'snowy'
    elif '구름' in description:
        return 'cloudy'
    elif '맑음' in description:
        return 'sunny'
    else:
        return 'default'

@app.route('/')
def home():
    city = request.args.get('city', 'Seoul')
    weather = get_weather(city)
    if not weather.get('error'):
        save_search_history(city)
        save_weather_history(city, weather)
    history_data = get_recent_weather_data(city)
    if len(history_data) >= 2:
        yesterday = history_data[-2]
        weather['delta_temp'] = weather['temperature'] - yesterday['temperature']
        weather['delta_humidity'] = weather['humidity'] - yesterday['humidity']
    else:
        weather['delta_temp'] = None
        weather['delta_humidity'] = None
    chart_data = {
        'dates': [d['date'] for d in history_data],
        'temps': [d['temperature'] for d in history_data],
        'humidities': [d['humidity'] for d in history_data]
    }
    # 날씨 설명을 바탕으로 weather_type 결정
    weather_type = classify_weather_type(weather['description'])

    return render_template('index.html', weather=weather, chart_data=chart_data,
        weather_type=weather_type)

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
