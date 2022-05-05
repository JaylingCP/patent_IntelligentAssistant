# encoding: utf-8
'''
@author: limingjie
@file: logger.py
@time: 2020/10/31 上午10:07
@desc:问答数据维护接口模块
'''

import os
import json
import re, sys
import time
from elasticsearch import Elasticsearch
from elasticsearch import helpers
from django.conf import settings
import datetime

# Create your models here.

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'patent_IntelligentAssistant.settings')

# 本地ES配置
# ES = Elasticsearch(
#     [{"host": settings.ES_HOST, "port": settings.ES_PORT, "http_auth": (settings.ES_USERNAME, settings.ES_PASSWORD)}])


# 服务器ES配置
ES = Elasticsearch(
    [{"host": settings.ES_HOST, "port": settings.ES_PORT, "http_auth": (settings.ES_USERNAME, settings.ES_PASSWORD),
      "use_ssl": True, "ca_cert": settings.ES_CERT}])

# 数据接口类
class Resource:
    def __init__(self, user_id):
        self.user_id = user_id

    def data_get(self, category, text, page_num, page_size):
        if category and text:
            body_data = {"query": {"bool": {"must": [{"term": {"category": category}}, {"match": {"question": text}}]}}}

            body2_data = {
                "query": {"bool": {"must": [{"term": {"category": category}}, {"match": {"question": text}}]}}}
        elif not category and text:
            body_data = {'query': {'match': {'question': text}}}

            body2_data = {'query': {'match': {'question': text}}}
        elif category and not text:
            body_data = {'query': {'term': {'category': category}}}

            body2_data = {'query': {'term': {'category': category}}}
        else:
            # body_data = {'query': {'match_all': {}}, "sort": [{"@timestamp": {"order": "desc"}}],
            #              "from": (page_num - 1) * page_size, "size": page_size}
            body_data = {'query': {'match_all': {}}}
            body2_data = {'query': {'match_all': {}}}
        res_data = ES.search(index=settings.INDEX_NAME, body=body_data, from_=(page_num - 1) * page_size,
                             size=page_size, sort="_score:desc,timestamp:desc")

        shards_data = res_data.get('_shards')
        if shards_data and shards_data.get('successful', 0) > 0:
            data_dict = res_data.get('hits', {}).get('hits', [])
        else:
            data_dict = {}
        res_num = ES.count(index=settings.INDEX_NAME, body=body2_data)
        total = res_num.get('count', 0)
        m_p = total / page_size
        if m_p > int(m_p):
            pages = int(m_p) + 1
        else:
            pages = int(m_p)

        list_data = []
        response_data = {}
        if data_dict:
            for d in data_dict:
                video_dict = {}
                num_str = d.get('_id', '')
                patent_dict = {'id': num_str}
                patent_dict['score'] = d.get('_score', 0)
                patent_dict.update(d.get('_source', {}))
                patent_dict.pop('timestamp')
                picture_list = patent_dict.get('resPicture', [])
                if picture_list:
                    picture_list = [os.path.join(settings.PICTURES_URL, p) for p in picture_list]
                    patent_dict['resPicture'] = picture_list

                video_list = patent_dict.get('resVideo', [])
                if video_list:
                    video_list = [os.path.join(settings.VIDEOS_URL, p) for p in video_list]
                    video_dict['resVideo'] = video_list
                list_data.append(patent_dict)

        header_data = [{'key': 'category', 'value': '类型'}, {'key': 'question', 'value': '问题'},
                       {'key': 'resVoice', 'value': '播报文本'}, {'key': 'resText', 'value': '答案文本'},
                       {'key': 'resPicture', 'value': '答案图片'}, {'key': 'resVideo', 'value': '答案视频'},
                       {'key': 'resForm', 'value': '答案表格'}]
        if list_data:
            code_int = 200
            msg_str = 'data get success'
            res_data = {"recipientId": self.user_id,
                        "list": {"header": header_data, "list": list_data, "page_num": page_num,
                                 "page_size": page_size, "pages": pages, "total": total}}
        else:
            code_int = 200
            res_data = {"recipientId": self.user_id,
                        "list": {"header": header_data, "list": list_data, "page_num": page_num,
                                 "page_size": page_size, "pages": 0, "total": 0}}
            msg_str = 'data get error'
        response_data['code'] = code_int
        response_data['data'] = res_data
        response_data['msg'] = msg_str
        return response_data

    def data_post(self, text_data):
        if not ES.indices.exists(index=settings.INDEX_NAME):
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
                            "analyzer": "ik_max_word"
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
            create_index = ES.indices.create(index=settings.INDEX_NAME, body=patent_doc)
            print(create_index)

        action_data = []

        p_dict = {"patent_events": "e", "patent_knowledge": "k", "patent_wall": "w"}
        category_name = text_data.get('category', '')

        total = int(time.time())
        id_data = p_dict.get(category_name) + str(total)

        p_name = text_data.getlist("resPicture", [])
        v_name = text_data.getlist("resVideo", [])

        if p_name:
            p_name = [id_data + '/' + p for p in p_name]
        if v_name:
            v_name = [id_data + '/' + v for v in v_name]

        f_data = text_data.get('resForm', {})
        if f_data:
            try:
                form_data = json.loads(f_data)
            except:
                form_data = {}
        else:
            form_data = {}

        action_data.append({
            "_index": settings.INDEX_NAME,
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
            helpers.bulk(ES, action_data, index=settings.INDEX_NAME)
            ES.indices.flush()
            response_data['code'] = 200
            response_data['data'] = {"recipientId": self.user_id, "questionId": id_data}
            response_data['msg'] = 'data post success'
        except:
            response_data['code'] = 500
            response_data['data'] = {"recipientId": self.user_id}
            response_data['msg'] = 'data post error'
        return response_data

    def data_put(self, text_data):
        response_data = {}
        action_data = []

        id_num = text_data.get('id')
        p_name = text_data.getlist("resPicture", [])
        v_name = text_data.getlist("resVideo", [])

        if p_name:
            p_name = [id_num + '/' + p for p in p_name]
        if v_name:
            v_name = [id_num + '/' + v for v in v_name]

        f_data = text_data.get('resForm', {})
        if f_data:
            try:
                form_data = json.loads(f_data)
            except:
                form_data = {}
        else:
            form_data = {}

        action_data.append({
            "_index": settings.INDEX_NAME,
            "_id": id_num,
            "_source": {
                "timestamp": datetime.datetime.now(),
                "category": text_data.get('category', ''),
                "question": text_data.get('question', ''),
                "resVoice": text_data.get('resVoice', ''),
                "resText": text_data.get('resText', ''),
                "resPicture": p_name,
                "resVideo": v_name,
                "resForm": form_data
            }
        })

        try:
            helpers.bulk(ES, action_data, index=settings.INDEX_NAME)
            ES.indices.flush()
            response_data['code'] = 200
            response_data['data'] = {"recipientId": self.user_id, "questionId": id_num}
            response_data['msg'] = 'data put success'
        except:
            response_data['code'] = 500
            response_data['data'] = {"recipientId": self.user_id}
            response_data['msg'] = 'data put error'

        return response_data

    def data_delete(self, text_data):
        id_list = []
        for t_d in text_data:
            id_list.append(t_d.get('id', ''))

        data_body = {
            "query": {
                "ids": {
                    "values": id_list
                }
            }
        }

        response_data = {}
        try:
            ES.delete_by_query(index=settings.INDEX_NAME, body=data_body)
            response_data['code'] = 200
            response_data['data'] = {"recipientId": self.user_id}
            response_data['msg'] = 'data delete success'
        except:
            response_data['code'] = 500
            response_data['data'] = {"recipientId": self.user_id}
            response_data['msg'] = 'data delete error'
        return response_data


class DataDisplay:
    def __init__(self, user_id):
        self.user_id = user_id

    def category_get(self):
        response_data = {}
        if self.user_id:
            response_data['code'] = 200
            l_d = [{"key": "patent_knowledge", "value": "常见专利知识"}, {"key": "patent_events", "value": "公司专利事件"}, {
                "key": "patent_wall", "value": "上墙专利信息"}]
            list_data = {"header": [{"key": "category", "value": "问题类型"}], "list": l_d}
            response_data['data'] = {"recipientId": self.user_id, "list": list_data}
            response_data['msg'] = 'category get success'
        else:
            response_data['code'] = 201
            response_data['data'] = {"recipientId": self.user_id}
            response_data['msg'] = 'userId error'

        return response_data


def mappingUpdate(new_index_name, old_index_name):
    if not ES.indices.exists(index=new_index_name):
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
                        "analyzer": "ik_max_word"
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
        create_index = ES.indices.create(index=new_index_name, body=patent_doc)
        print(create_index)
    print("create %s index is ok" % (new_index_name))
    reBody = {
        "source": {
            "index": old_index_name,
        },
        "dest": {
            "index": new_index_name,
        }
    }
    ES.reindex(body=reBody)
    print("%s to %s data migrate is ok" % (old_index_name, new_index_name))


if __name__ == '__main__':
    # res = Resource(user_id='000')
    # data = res.data_get(category="", page_num=1, page_size=4, text='')
    #
    # data = res.data_post(text_data={"category": "patent_knowledge", "question": "xxx", "resVioce": "cccc", "resText": "oooo",
    #            "resPicture": [], "resVideo": [],"resForm": []})
    #
    # res.data_put({"category": "patent_knowledge", "id": 0, "question": "常见专利知识", "resVioce": "cccc", "resText": "oooo",
    #            "resPicture": [], "resVideo": [],
    #            "resForm": []})

    # data = res.data_delete(text_data=[{"id": "k21", "category": "patent_knowledge"}])
    mappingUpdate(new_index_name='patent_v2', old_index_name='patent')

    # ds = DataDisplay(user_id='000')
    # data = ds.categoryGet()
