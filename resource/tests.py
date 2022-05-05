from django.test import TestCase
import os
import json
import sys

from elasticsearch import Elasticsearch
from elasticsearch import helpers
import datetime, time

ES = Elasticsearch(hosts={'172.28.5.33'})


# Create your tests here.
def data_post(text_data):
    if not ES.indices.exists(index='patent'):
        patent_doc = {
            "mappings": {
                "properties": {
                    "timestamp": {
                        "type": "date"
                    },
                    "category": {
                        "type": "text",
                        "analyzer": "ik_smart"
                    },
                    "question": {
                        "type": "text",
                        "analyzer": "ik_smart"
                    },
                    "resVoice": {
                        "type": "text",
                        "analyzer": "ik_smart"
                    },
                    "resText": {
                        "type": "text",
                        "analyzer": "ik_smart"
                    },
                    "res_picture": {
                        "type": "text",
                        "analyzer": "ik_smart"
                    },
                    "res_video": {
                        "type": "text",
                        "analyzer": "ik_smart"
                    },
                    "res_form": {
                        "type": "text",
                        "analyzer": "ik_smart"
                    }
                }
            }
        }
        create_index = ES.indices.create(index='patent', body=patent_doc)
        print(create_index)

    action_data = []

    p_dict = {"patent_events": "e", "patent_knowledge": "k", "patent_wall": "w"}
    category_name = text_data.get('category', '')

    total = int(time.time())
    # print("res_num:%d,total:%d" % (res_num.get('count', 0), total))
    id_data = p_dict.get(category_name) + str(total)

    p_name = []
    v_name = []
    file_name = category_name + str(total)
    if p_name:
        p_name = [file_name + '/' + p for p in p_name]
    if v_name:
        v_name = [file_name + '/' + v for v in v_name]

    f_data = text_data.get('resForm', {})
    if f_data:
        try:
            form_data = json.loads(f_data)
        except:
            form_data = {}
    else:
        form_data = {}

    action_data.append({
        "_index": 'patent',
        "_id": id_data,
        "_source": {
            "timestamp": datetime.datetime.now(),
            "category": category_name,
            "question": text_data.get('question', ''),
            "resVoice": text_data.get('resVoice', ''),
            "resText": text_data.get('resText', ''),
            "resPicture": p_name,
            "resVideo": v_name,
            "resForm": form_data
        }
    })
    response_data = {}
    try:
        helpers.bulk(ES, action_data, index='patent')
        ES.indices.flush()
        response_data['code'] = 200
        response_data['data'] = {"recipientId": '000', "questionId": id_data}
        response_data['msg'] = 'data post success'
    except:
        response_data['code'] = 500
        response_data['data'] = {"recipientId": '000'}
        response_data['msg'] = 'data post error'
    return response_data


if __name__ == '__main__':
    res = data_post(text_data={'userId': '000', 'category': 'patent_knowledge', 'question': '1111', 'resVoice': 'cccc',
                               'resText': 'cccc'})
    print(res)
