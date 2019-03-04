from flask import Blueprint, request, current_app
from backend.models import User, Result, Fav, SearchStream, Keyword, SearchKeywordRel
from backend import db, mail
import json
from sqlalchemy import and_
import geocoder
import requests
from backend import config
from datetime import timedelta, datetime
from flask_mail import Message

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
    user = User.verify_auth_token(auth_token)

    if user is None:
        return json.dumps({'status': 0, 'error': "User credentials invalid"})

    q = request_json['q']
    center = request_json['center']
    location = request_json['location']
    media_type = request_json['media_type']
    photographer = request_json['photographer']
    keywords = request_json['keywords'] ##list of keywords

    new_stream = SearchStream(
        q=q,
        center=center,
        location=location,
        media_type=media_type,
        photographer=photographer,
        user_id=user.id
    )

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


@events.route('/result/stream/remove', methods=['POST'])
def remove_from_stream():
    request_json = request.get_json()

    auth_token = request_json['auth_token']
    user = User.verify_auth_token(auth_token)

    if user is None:
        return json.dumps({'status': 0, 'error': "User credentials invalid"})

    ss_id = request_json['ss_id']
    ss = SearchStream.query.filter_by(id=ss_id).first()

    if ss is None:
        return json.dumps({'status': 0, 'error': "Incorrect Parameters Provided. Please contact system administrator."})

    if ss.user_id != user.id and not user.isAdmin:
        return json.dumps({'status': 0, 'error': "User Not Authorized"})

    ss.status = False
    db.session.commit()

    return json.dumps({'status': 1})


@events.route('/result/stream', methods=['GET'])
def stream():
    all_ss = SearchStream.query.filter_by(status=True)
    num_adds = 0
    num_stream_sends = 0
    for ss in all_ss:
        map_received = {
            'q': ss.q,
            'center': ss.center,
            'location': ss.location,
            'media_type': ss.media_type,
            'photograph': ss.photograph,
            'keywords': ",".join([Keyword.query.filter_by(id=x.kw_id).first().name
                                  for x in SearchKeywordRel.query.filter_by(ss_id=ss.id)])
        }

        curr_user = ss.user_id

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

        new_adds = []

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
                new_adds.append(new_res)
                db.session.add(new_res)
                num_res += 1
        db.session.commit()

        new_add_str = "\n".join(
            (current_app.config['CURRENT_URL'] + current_app.config['IMG_URL'] + str(x.id)) for x in new_adds
        )

        num_adds += len(new_adds)

        if len(new_adds) != 0:
            num_stream_sends += 1
            msg = Message('Investoreal Login Credentials', sender='rachitbhargava99@gmail.com',
                          recipients=[curr_user.email])
            msg.body = f'''Hi {curr_user.name},

New images matching your query were recently added by NASA.

Below-mentioned are links to the images that were added.
{new_add_str}

Cheers,
Spindler Team'''
            mail.send(msg)

    return json.dumps({'status': 1, 'num_adds': num_adds, 'num_stream_sends': num_stream_sends})
