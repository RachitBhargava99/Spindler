from flask import Blueprint, request, current_app
from backend.models import User, Result, Fav, SearchStream, Keyword, SearchKeywordRel, Search, SearchKeyRel, \
    StreamResult
from backend import db, mail
import json
import requests
from datetime import datetime
from flask_mail import Message

events = Blueprint('queues', __name__)


# Checker to see whether or not is the server running
@events.route('/event', methods=['GET'])
def checker():
    return "Hello"


# End-point for all the search queries
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
        'year_start': request_json['year_start'] if request_json['year_start'] != '' else 1800,
        'year_end': request_json['year_end'] if request_json['year_end'] != '' else 2050,
        'page': request_json['page'] if request_json['page'] != '' else 1
    }

    new_search = Search(
        q=request_json['q'],
        center=request_json['center'],
        description=request_json['description'],
        description_508=request_json['description_508'],
        location=request_json['location'],
        media_type=request_json['media_type'],
        nasa_id=request_json['nasa_id'],
        photographer=request_json['photographer'],
        secondary_creator=request_json['secondary_creator'],
        title=request_json['title'],
        year_start=request_json['year_start'] if request_json['year_start'] != '' else 1800,
        year_end=request_json['year_end'] if request_json['year_end'] != '' else 2050
    )

    if request_json['user_id'] != -1:
        new_search.user_id = request_json['user_id']

    db.session.add(new_search)

    for keyword in request_json['keywords']:
        key = Keyword.query.filter_by(name=keyword).first()
        key = key if key is not None else Keyword(name=keyword)
        new_search_key_rel = SearchKeyRel(se_id=new_search.id, kw_id=key.id)
        db.session.add(new_search_key_rel)

    map_to_send = {}
    for each in map_received:
        if map_received[each] != '':
            map_to_send[each] = map_received[each]

    query = requests.get(current_app.config['BASE_URL'] + current_app.config['SEARCH_URL'], params=map_to_send)
    result = query.json()
    try:
        received_res = {1: result['collection']['items']}  ##storing search results until all are accumulated
        num_p_extra = result['collection']['metadata']['total_hits'] // 100  ##number of more pages to load data from
    except Exception:
        raise Exception(result)

    # async def add_data(page_num):
    #     map_to_send['page'] = page_num
    #     query = requests.get(current_app.config['BASE_URL'] + current_app.config['SEARCH_URL'], params=map_to_send)
    #     result = query.json()
    #     received_res[page_num] = result['collection']['items']
    #
    # async def data_runner():
    #     tasks = []
    #     for i in range(2, num_p_extra + 2):
    #         tasks.append(asyncio.ensure_future(add_data(i)))
    #     await asyncio.gather(*tasks)
    #
    # loop = asyncio.new_event_loop()
    # asyncio.set_event_loop(loop)
    # loop.run_until_complete(data_runner())
    # loop.close()

    final_res = received_res[1]
    # for i in range(1, num_p_extra + 2):
    #     final_res += received_res[i]

    num_res = 0

    for each in final_res:
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

    for each in final_res:
        curr = Result.query.filter_by(nasa_id=each['data'][0]['nasa_id']).first()
        each['res_id'] = curr.id

    return json.dumps({
        'data': final_res,
        'num_res': num_res,
        'num_ret': result['collection']['metadata']['total_hits']
    }
    )


# End-point to add a result to the user's list of favorites
@events.route('/result/fav', methods=['POST'])
def add_to_favorite():
    request_json = request.get_json()

    auth_token = request_json['auth_token']
    user = User.verify_auth_token(auth_token)

    if user is None:
        return json.dumps({'status': 0, 'error': "User credentials invalid"})

    result_id = request_json['result_id']

    new_fav = Fav(user_id=user.id, res_id=result_id)
    db.session.add(new_fav)
    db.session.commit()

    return json.dumps({'status': 1})


# End-point to remove a result from the user's list of favorites
@events.route('/result/unfav', methods=['POST', 'GET'])
def remove_from_favorite():
    request_json = request.get_json()

    auth_token = request_json['auth_token']
    user = User.verify_auth_token(auth_token)

    if user is None:
        return json.dumps({'status': 0, 'error': "User Not Authenticated"})

    res_id = request_json['res_id']
    res = Result.query.filter_by(id=res_id).first()

    if res is None:
        return json.dumps({'status': 0, 'error': "Incorrect Parameters Provided. Please contact system administrator."})

    fav = Fav.query.filter_by(user_id=user.id, res_id=res_id).first()

    if fav is None:
        return json.dumps({'status': 0, 'error': "Item Not Marked Favorite."})

    fav.status = 0

    db.session.commit()

    return json.dumps({'status': 1, 'fav_id': fav.id})


# End-point to show all results a user has added to their list of favorites
@events.route('/result/fav/show_all', methods=['POST', 'GET'])
def show_all_favorites():
    request_json = request.get_json()

    auth_token = request_json['auth_token']
    user = User.verify_auth_token(auth_token)

    if user is None:
        return json.dumps({'status': 0, 'error': "User Not Authenticated"})

    all_favs = Fav.query.filter_by(user_id=user.id, status=True)

    final_res = []

    for each in all_favs:
        result = Result.query.filter_by(id=each.res_id).first()
        final_res.append({
            'id': result.id,
            'name': result.name,
            'center': result.center,
            'last_updated': result.last_updated.strftime("%B %d, %Y %I:%M %p"),
            'thumb_img': result.thumb_img,
            'description': result.description,
            'nasa_id': result.nasa_id
        })

    return json.dumps({'status': 1, 'data': final_res})


# End-point to start streaming a query
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
    keywords = request_json['keywords']  ##list of keywords

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


# End-point to stop streaming a query
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


# End-point to show all queries a user is currently streaming
@events.route('/result/stream/all', methods=['POST'])
def show_all_streams():
    request_json = request.get_json()

    auth_token = request_json['auth_token']
    user = User.verify_auth_token(auth_token)

    if user is None:
        return json.dumps({'status': 0, 'error': "User credentials invalid"})

    all_ss = SearchStream.query.filter_by(user_id=user.id, status=True)
    final_list = []
    for each in all_ss:
        final_list.append({
            'id': each.id,
            'q': each.q,
            'center': each.center,
            'location': each.location
        })

    return json.dumps({'data': final_list})


# End-point to stream - run periodically
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
            'photographer': ss.photographer,
            'keywords': ",".join([Keyword.query.filter_by(id=x.kw_id).first().name
                                  for x in SearchKeywordRel.query.filter_by(ss_id=ss.id)])
        }

        if not ss.first_time:
            ss.first_time = False
        else:
            curr_user = ss.user_id

            map_to_send = {}
            for each in map_received:
                if map_received[each] != '':
                    map_to_send[each] = map_received[each]

            query = requests.get(current_app.config['BASE_URL'] + current_app.config['SEARCH_URL'], params=map_to_send)
            result = query.json()
            received_res = result['collection']['items']  ##storing search results until all are accumulated
            num_p_extra = result['collection']['metadata'][
                              'total_hits'] // 100  ##number of more pages to load data from

            for i in range(2, num_p_extra + 2):
                map_to_send['page'] = i
                query = requests.get(current_app.config['BASE_URL'] + current_app.config['SEARCH_URL'],
                                     params=map_to_send)
                result = query.json()
                received_res += result['collection']['items']

            new_adds = []

            for each in received_res:
                if (StreamResult.query.filter_by(nasa_id=each['data'][0]['nasa_id'])).first() is None:
                    new_res = StreamResult(
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

            new_add_str = "\n".join(
                [(current_app.config['CURRENT_URL'] + current_app.config['IMG_URL'] + str(x.id)) for x in new_adds]
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

    for ss in all_ss:
        map_received = {
            'q': ss.q,
            'center': ss.center,
            'location': ss.location,
            'media_type': ss.media_type,
            'photographer': ss.photographer,
            'keywords': ",".join([Keyword.query.filter_by(id=x.kw_id).first().name
                                  for x in SearchKeywordRel.query.filter_by(ss_id=ss.id)])
        }

        map_to_send = {}
        for each in map_received:
            if map_received[each] != '':
                map_to_send[each] = map_received[each]

        query = requests.get(current_app.config['BASE_URL'] + current_app.config['SEARCH_URL'],
                             params=map_to_send)
        result = query.json()
        received_res = result['collection']['items']  ##storing search results until all are accumulated
        num_p_extra = result['collection']['metadata'][
                          'total_hits'] // 100  ##number of more pages to load data from

        for i in range(2, num_p_extra + 2):
            map_to_send['page'] = i
            query = requests.get(current_app.config['BASE_URL'] + current_app.config['SEARCH_URL'],
                                 params=map_to_send)
            result = query.json()
            received_res += result['collection']['items']

        num_res = 0

        for each in received_res:
            if (StreamResult.query.filter_by(nasa_id=each['data'][0]['nasa_id'])).first() is None:
                new_res = StreamResult(
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

    return json.dumps({'status': 1, 'num_adds': num_adds, 'num_stream_sends': num_stream_sends})


# End-point to check a user's search history
@events.route('/search/history', methods=['POST'])
def get_search_history():
    request_json = request.get_json()

    auth_token = request_json['auth_token']
    user = User.verify_auth_token(auth_token)

    if user is None:
        return json.dumps({'status': 0, 'error': "User credentials invalid"})

    all_search = Search.query.filter_by(user_id=user.id)
    final_res = []

    for each in all_search:
        final_res.append({'id': each.id, 'q': each.q, 'timestamp': each.timestamp.strftime("%B %d, %Y %H:%M:%S")})

    final_res.reverse()

    return json.dumps({'status': 1, 'data': final_res})


# End-point to check most searched queries
@events.route('/search/most', methods=['GET'])
def get_most_searched():
    all_search = Search.query.all()
    final_dict = {}

    for each in all_search:
        final_dict[each.q.lower()] = final_dict[each.q.lower()] + 1 \
            if final_dict.get(each.q.lower()) is not None else 1

    final_tup = [(final_dict[x], x) for x in final_dict]
    final_tup.sort(reverse=True)

    return json.dumps({'status': 1, 'list': final_tup})
