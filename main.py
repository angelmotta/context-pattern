import requests
from flask import Flask, request
import redis
import uuid

app = Flask(__name__)


@app.route('/')
def hello_world():
    return '<h2>Laboratorio Context</h2>'

# Connect to the Redis server
redis_host = 'localhost'  
redis_port = 6380 
redis_db = 0  
redis_password = None 


redis_client = redis.StrictRedis(
    host=redis_host, port=redis_port, db=redis_db, password=redis_password, decode_responses=True
)

def get_lat_long_from_new(place):
    url = f'https://geocoding-api.open-meteo.com/v1/search?name={place}'
    r_coordinates = requests.get(url)
    jsonData = r_coordinates.json()
    return jsonData['results'][0]['latitude'], jsonData['results'][0]['longitude']


def get_lat_long_from_old(place):
    url = f'https://nominatim.openstreetmap.org/search?q={place}&format=json'
    r_coordinates = requests.get(url)
    jsonData = r_coordinates.json()
    return jsonData[0]['lat'], jsonData[0]['lon']


@app.route('/place')
def get_lat_lon():
    userId = request.args.get('userId')
    contextId = request.args.get('contextId')
    place = request.args.get('place')
    app_context = {'userId': userId}

    print(contextId)

    print("Usuario:", userId)
    if contextId is None and place is None:
        print("Bad request")
        responseError = {
            "message": "Bad request",
        }
        return responseError, 400
    
    # Test redis
    try:
        if contextId is None:
            contextId = str(uuid.uuid4())
            print("ContextId:", contextId)
            redis_client.set(contextId, place)
        else:
            if place is None:
                retrieved_place = redis_client.get(contextId)
                print("Retrieved value:", retrieved_place)
                # Handle contextKey doesn't exist in DB
                if retrieved_place is None:
                    # throw error
                    raise "ContextKey doesn't exist in DB"
                place = retrieved_place
            else:
                redis_client.set(contextId, place)


    except redis.RedisError as e:
        print("Error connecting to Redis:", e)
        # return error 500
        responseError = {
            "message": "Error connecting to Redis",
        }
        return responseError, 500


    except Exception as e:
        responseError = {
            "message": "Error: contextId not found",
        }
        return responseError, 404

    # if client.is_enabled('nuevoapi', app_context):
    #     print("Usando nuevo API")
    #     lat_res, lon_res = get_lat_long_from_new(place)
    # else:
    print("Usando viejo API")
    lat_res, lon_res = get_lat_long_from_old(place)

    print("Latitud:", lat_res)
    print("Longitud:", lon_res)

    url_weather_daily = f'https://api.open-meteo.com/v1/forecast?latitude={lat_res}&longitude={lon_res}&forecast_days' \
                        f'=2&daily=temperature_2m_max,temperature_2m_min&timezone=GMT'

    r_weather = requests.get(url_weather_daily)
    weather_json = r_weather.json()

    response = {}

    temperature = {'max': weather_json['daily']['temperature_2m_max'][0],
                   'min': weather_json['daily']['temperature_2m_min'][0]}

    response['temperature'] = temperature
    response['contextId'] = contextId
    # response['new-api'] = client.is_enabled('nuevoapi', app_context)

    return response


if __name__ == '__main__':
    app.run(debug=False, port=5000)
