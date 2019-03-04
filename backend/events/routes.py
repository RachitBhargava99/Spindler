from flask import Blueprint, request, current_app
from backend.models import User, Result, Fav, SearchStream, Keyword, SearchKeywordRel
from backend import db
import json
from sqlalchemy import and_
import geocoder
import requests
from backend import config
from datetime import timedelta, datetime

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
    received_res = result['collection']['items']  ##storing search results until all are accumulated
    num_p_extra = result['collection']['metadata']['total_hits'] // 100  ##number of more pages to load data from

    for i in range(2, num_p_extra + 2):
        map_to_send['page'] = i
        query = requests.get(current_app.config['BASE_URL'] + current_app.config['SEARCH_URL'], params=map_to_send)
        result = query.json()
        received_res += result['collection']['items']

    num_res = 0

    for each in received_res:
        if (Result.query.filter_by(nasa_id=each['data'][0]['nasa_id'])).first() is None:
            new_res = Result(
                name=each['data'][0]['title'],
                center=each['data'][0]['center']
                if each['data'][0].get('center') is not None else "No Center Information Provided",
                last_updated=datetime.strptime(each['data'][0]['date_created'], "%Y-%m-%dT%H:%M:%SZ"),
                thumb_img=([x['href'] for x in each['links']
                            if x.get('render') is not None and x['render'] == "image"][0])
                if each.get('links') is not None else "",
                description=((each['data'][0]['description'])
                             if len(each['data'][0]['description']) <= 16383
                             else each['data'][0]['description'][:16379] + "...")
                if each['data'][0].get('description') is not None else "",
                nasa_id=each['data'][0]['nasa_id']
            )
            db.session.add(new_res)
            num_res += 1
    db.session.commit()

    return json.dumps({
        'data': received_res,
        'num_res': num_res,
        'num_ret': result['collection']['metadata']['total_hits']
        }
    )


@events.route('/result/fav', methods=['POST'])
def add_to_favorite():
    request_json = request.get_json()

    auth_token = request_json['auth_token']
    user_id = User.verify_auth_token(auth_token)

    if user_id is None:
        return json.dumps({'status': 0, 'error': "User credentials invalid"})

    result_id = request_json['result_id']

    new_fav = Fav(user_id=user_id, res_id=result_id)
    db.session.add(new_fav)
    db.session.commit()

    return json.dumps({'status': 1})


@events.route('/result/stream/add', methods=['POST'])
def add_to_stream():
    request_json = request.get_json()

    auth_token = request_json['auth_token']
    user_id = User.verify_auth_token(auth_token)

    if user_id is None:
        return json.dumps({'status': 0, 'error': "User credentials invalid"})

    q = request_json['q']
    center = request_json['center']
    location = request_json['location']
    media_type = request_json['media_type']
    photographer = request_json['photographer']
    keywords = request_json['keywords'] ##list of keywords

    new_stream = SearchStream(q=q, center=center, location=location, media_type=media_type, photographer=photographer)
    db.session.add(new_stream)

    for each in keywords:
        curr_key = Keyword.query.filter_by(name=each).first()
        if curr_key is not None:
            new_sw_rel = SearchKeywordRel(ss_id=new_stream.id, kw_id=curr_key.id)
            db.session.add(new_sw_rel)
        else:
            new_key = Keyword(name=each)
            db.session.add(new_key)
            new_sw_rel = SearchKeywordRel(ss_id=new_stream.id, kw_id=new_key.id)
            db.session.add(new_sw_rel)
    db.session.commit()

    return json.dumps({'status': 1})
