from flask import Blueprint, request, current_app
from backend.models import User, Result
from backend import db
import json
from sqlalchemy import and_
import geocoder
import requests
from backend import config
from datetime import timedelta

events = Blueprint('queues', __name__)


@events.route('/event', methods=['GET'])
def checker():
    return "Hello"


@events.route('/search', methods=['POST'])
def search_now():
    request_json = request.get_json()

    map_received = {
        'q': request_json['q'],
        'center': request_json['center'],
        'description': request_json['description'],
        'description_508': request_json['description_508'],
        'keywords': request_json['keywords'],
        'location': request_json['location'],
        'media_type': request_json['media_type'],
        'nasa_id': request_json['nasa_id'],
        'photographer': request_json['photographer'],
        'secondary_creator': request_json['secondary_creator'],
        'title': request_json['title'],
        'year_start': request_json['year_start'],
        'year_end': request_json['year_end']
    }

    map_to_send = {}
    for each in map_received:
        if map_received[each] != '':
            map_to_send[each] = map_received[each]

    query = requests.get(current_app.config['BASE_URL'] + current_app.config['SEARCH_URL'], params=map_to_send)
    result = query.json()
    received_res = result['collection']['items'] ##storing search results until all are accumulated
    num_p_extra = result['collection']['metadata']['total_hits'] // 100 ##number of more pages to load data from

    for i in range(1, num_p_extra + 1):
        map_to_send['page'] = i
        query = requests.get(current_app.config['BASE_URL'] + current_app.config['SEARCH_URL'], params=map_to_send)
        result = query.json()
        received_res += result['collection']['items']

    return json.dumps({'data': received_res})
