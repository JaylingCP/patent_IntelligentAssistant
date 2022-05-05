# encoding: utf-8
'''
@author: limingjie
@file: skill.py
@time: 2020/6/18 下午4:56
@desc:技能上下线
'''

import os
import sys
import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')

from django_redis import get_redis_connection
import json
import pandas as pd
from django.conf import settings
from elasticsearch import Elasticsearch
from elasticsearch import helpers


# import dialogue.patent.actions as patent_actions

def skillUpdate(data_path):
    try:
        redis_skill = get_redis_connection('default')
        for t in ['on', 'off']:
            skill_data = pd.read_excel(data_path, sheet_name=t + 'line_skill', header=0)
            skill_data = skill_data.fillna(value='')
            nlu_dict = {}
            text_dict = {}
            dial_dict = {}
            serv_dict = {}
            for index, row in skill_data.iterrows():
                if row['nlu_skill']:
                    nlu_dict.update(json.loads(row['nlu_skill']))
                if row['text_skill']:
                    text_dict.update(json.loads(row['text_skill']))
                if row['dialogue_skill']:
                    dial_dict.update(json.loads(row['dialogue_skill']))
                if row['service_port']:
                    serv_dict.update(json.loads(row['service_port']))
            redis_skill.hset(name=t + 'line_skill', key='nlu_skill', value=json.dumps(nlu_dict, ensure_ascii=False))
            redis_skill.hset(name=t + 'line_skill', key='text_skill',
                             value=json.dumps(text_dict, ensure_ascii=False))
            redis_skill.hset(name=t + 'line_skill', key='dialogue_skill',
                             value=json.dumps(dial_dict, ensure_ascii=False))
            redis_skill.hset(name=t + 'line_skill', key='service_port',
                             value=json.dumps(serv_dict, ensure_ascii=False))
        print('skill update ok')
    except:
        print('skill update error')


def departmentUpdate(data_path):
    redis_cn = get_redis_connection('default')
    data = pd.read_excel(data_path, sheet_name='department', header=0)
    data = data.fillna(value='')
    depart_dict = {}
    for index, row in data.iterrows():
        depart_dict[row['department_name']] = str(row['department_id'])
        row['nickname'] = row['nickname'].replace('，', ',')
        n_list = row['nickname'].split(',')
        if n_list:
            for d in n_list:
                if d:
                    depart_dict[d] = str(row['department_id'])
    redis_cn.hset(name='company_data', key='department', value=json.dumps(depart_dict, ensure_ascii=False))
    print('department update ok')


def tooltipUpdate(data_path):
    redis_cn = get_redis_connection('default')
    start_data = pd.read_excel(data_path, header=0, sheet_name='start')
    start_data = start_data.fillna(value='')

    action_data = []
    for index, row in start_data.iterrows():
        p_str = row['resPicture']
        if p_str:
            p_str = p_str.replace('\n', '').replace(' ', '')
            p_list = json.loads(p_str)
        else:
            p_list = []

        v_str = row['resVideo']
        if v_str:
            v_str = v_str.replace('\n', '').replace(' ', '')
            v_list = json.loads(v_str)
        else:
            v_list = []

        f_str = row['resForm']
        if f_str:
            f_str = f_str.replace('\n', '').replace(' ', '')
            f_dict = json.loads(f_str)
        else:
            f_dict = {}
        action_data.append({
            "resVoice": row['resVoice'].replace('\n', '').replace(' ', ''),
            "resText": row['resText'].replace('\n', '').replace(' ', ''),
            "resPicture": p_list,
            "resVideo": v_list,
            "resForm": f_dict
        })
    redis_cn.hset(name='company_data', key='start', value=json.dumps(action_data, ensure_ascii=False))

    tooltip_data = pd.read_excel(data_path, header=0, sheet_name='default')
    tooltip_data = tooltip_data.fillna(value='')

    action_data = []
    for index, row in tooltip_data.iterrows():
        p_str = row['resPicture']
        if p_str:
            p_str = p_str.replace('\n', '').replace(' ', '')
            p_list = json.loads(p_str)
        else:
            p_list = []

        v_str = row['resVideo']
        if v_str:
            v_str = v_str.replace('\n', '').replace(' ', '')
            v_list = json.loads(v_str)
        else:
            v_list = []

        f_str = row['resForm']
        if f_str:
            f_str = f_str.replace('\n', '').replace(' ', '')
            f_dict = json.loads(f_str)
        else:
            f_dict = {}
        action_data.append({
            "resVoice": row['resVoice'].replace('\n', '').replace(' ', ''),
            "resText": row['resText'].replace('\n', '').replace(' ', ''),
            "resPicture": p_list,
            "resVideo": v_list,
            "resForm": f_dict
        })
    redis_cn.hset(name='company_data', key='default', value=json.dumps(action_data, ensure_ascii=False))

    print('tooltip update ok')


def patentUpdate(data_path, doc_type):
    ES = Elasticsearch(hosts=[{"host": settings.ES_HOST, "port": settings.ES_PORT}])
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

    if not ES.indices.exists(index=settings.INDEX_NAME):
        create_index = ES.indices.create(index=settings.INDEX_NAME, body=patent_doc)
        print(create_index)
    # else:
    #     ES.indices.delete(index=settings.INDEX_NAME)

    patent_data = pd.read_excel(data_path, header=0)
    patent_data = patent_data.fillna('')
    action_data = []
    for index, row in patent_data.iterrows():
        p_str = row['resPicture']
        p_dict = {"patent_events": "e", "patent_knowledge": "k", "patent_wall": "w"}
        id_data = p_dict.get(doc_type) + str(row['id'])
        name_str = doc_type + str(row['id'])
        if p_str:
            p_str = p_str.replace('\n', '').replace(' ', '')
            p_list = json.loads(p_str)
            p_list = [name_str + '/' + p for p in p_list]
        else:
            p_list = []

        v_str = row['resVideo']
        if v_str:
            v_str = v_str.replace('\n', '').replace(' ', '')
            v_list = json.loads(v_str)
            v_list = [name_str + '/' + v for v in v_list]
        else:
            v_list = []

        f_str = row['resForm']
        if f_str:
            f_str = f_str.replace('\n', '').replace(' ', '')
            f_dict = json.loads(f_str)
        else:
            f_dict = {}
        # stop_word_path = './data/HGDstopwords.txt'
        # stopword_list = [sw.replace('\n', '') for sw in open(stop_word_path, encoding='UTF-8').readlines()]
        # seg_list = patent_actions.preprocess_data(row['question'].replace('\n', '').replace(' ', ''))
        # ques_str = ''.join([x for x in seg_list if x not in stopword_list])
        ques_str = row['question'].replace('\n', '').replace(' ', '')
        action_data.append({
            "_index": settings.INDEX_NAME,
            "_id": id_data,
            "_source": {
                "timestamp": datetime.datetime.now(),
                "category": doc_type,
                "question": ques_str,
                "resVoice": row['resVoice'].replace('\n', '').replace(' ', ''),
                "resText": row['resText'].replace('\n', '').replace(' ', ''),
                "resPicture": p_list,
                "resVideo": v_list,
                "resForm": f_dict
            }
        })
    helpers.bulk(ES, action_data, index=settings.INDEX_NAME)
    print("%s data update ok" % doc_type)
    ES.indices.flush()


if __name__ == '__main__':
    path1 = os.path.join(os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "./data")),
                         "skill_list.xlsx")
    skillUpdate(data_path=path1)

    path3 = os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "./data/patent_data")),
        "company_data.xlsx")
    departmentUpdate(data_path=path3)

    path4 = os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "./data/patent_data")),
        "tooltip_data.xlsx")
    tooltipUpdate(data_path=path4)

    # patentUpdate(data_path='./data/patent_data/patent_knowledge.xlsx', doc_type='patent_knowledge')
    # patentUpdate(data_path='./data/patent_data/patent_events.xlsx', doc_type='patent_events')
    # patentUpdate(data_path='./data/patent_data/patent_wall.xlsx', doc_type='patent_wall')
