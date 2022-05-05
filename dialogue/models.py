from django_redis import get_redis_connection
import os
import sys
import json
import cocoNLP.extractor
import chinese2digits as c2d
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'patent_IntelligentAssistant.settings')

import jieba
from django.conf import settings
from elasticsearch import Elasticsearch
import random
from datetime import datetime
from django.db import connections
import asyncio
from rasa.core.agent import Agent
from rasa.utils.endpoints import EndpointConfig
import dialogue.nlutest as NLU
from patent_IntelligentAssistant.common import logger

dict_path = os.path.join(os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "./patent/dict")),
                         "patent-dict.txt")

# 本地ES配置
ES = Elasticsearch(
    [{"host": settings.ES_HOST, "port": settings.ES_PORT, "http_auth": (settings.ES_USERNAME, settings.ES_PASSWORD)}])

# 服务器ES配置
# ES = Elasticsearch(
#     [{"host": settings.ES_HOST, "port": settings.ES_PORT, "http_auth": (settings.ES_USERNAME, settings.ES_PASSWORD),
#       "use_ssl": True, "ca_cert": settings.ES_CERT}])


endpoint = EndpointConfig(url=settings.RASA_URL)
agent = Agent.load(
    settings.RASA_MODEL,
    action_endpoint=endpoint
)


async def nlu_agent(message):
    result = await agent.parse_message_using_nlu_interpreter(message_data=message)
    # print(result)
    return result


loop = asyncio.get_event_loop()

root_log_path = settings.LOGS_DIR

jieba.initialize()
jieba.load_userdict(dict_path)


# 数据存储类
class Dialogue:
    def __init__(self, user_id):
        self.user_id = user_id
        redis_skill = get_redis_connection('default')
        if redis_skill.hexists('online_skill', 'text_skill'):
            self.text_skill = json.loads(redis_skill.hget(name='online_skill', key='text_skill').decode('utf-8'))
        else:
            self.text_skill = {}

        if redis_skill.hexists('online_skill', 'nlu_skill'):
            self.nlu_skill = json.loads(redis_skill.hget(name='online_skill', key='nlu_skill').decode('utf-8'))
        else:
            self.nlu_skill = {}

        if redis_skill.hexists('online_skill', 'dialogue_skill'):
            self.dialogue_skill = json.loads(
                redis_skill.hget(name='online_skill', key='dialogue_skill').decode('utf-8'))
        else:
            self.dialogue_skill = {}

    def dialogueProcess(self, mess_data, skill_list):
        # print(mess_data)
        # print(skill_list)
        response_data = {}
        text_list = skill_list.get('text')
        nlu_list = skill_list.get('nlu')
        dia_list = skill_list.get('dialogue')
        if text_list:
            response_data['text'] = {}
            for t in text_list:
                if t in self.text_skill.keys() and t == 'c2d':
                    res1_data = {}
                    try:
                        res1_data['code'] = 200
                        res1_data['data'] = self.chineseToDigits(text=mess_data)
                        res1_data['msg'] = 'KA c2d work'
                    except:
                        res1_data['code'] = 400
                        res1_data['data'] = {}
                        res1_data['msg'] = 'KA c2d error'
                    response_data['text'].update({'c2d': res1_data})
                elif t in self.text_skill.keys() and t == 'gNER':
                    res2_data = {}
                    try:
                        res2_data['code'] = 200
                        res2_data['data'] = {'slots': self.generalEntity(text=mess_data).get('entities', [])}
                        res2_data['msg'] = 'KA gNER work'
                    except:
                        res2_data['code'] = 400
                        res2_data['data'] = {}
                        res2_data['msg'] = 'KA gNER error'
                    response_data['text'].update({'gNER': res2_data})
        if nlu_list:
            response_data['nlu'] = self.nluTranslate(mess_data, nlu_list)
        if dia_list:
            response_data['dialogue'] = self.dialogueTranslate(mess_data, dia_list)

        return response_data

    # 数据预处理模块
    def chineseToDigits(self, text):
        f_text = c2d.takeNumberFromString(text)['replacedText'].replace('.0', '')
        return f_text

    # 通用实体提取
    def generalEntity(self, text):
        entity_data = {}
        ex = cocoNLP.extractor.extractor()

        l_list = ex.extract_locations(text)
        location_list = [p.replace("今天", "").replace("天气", "") for p in l_list]

        time_dict = json.loads(ex.extract_time(text))

        name_list = ex.extract_name(text)

        entity_data['slots'] = []
        filter_text = text
        if location_list:
            loc_entites = []
            num_l = len(location_list)
            for i in range(num_l):
                loc = location_list[i]
                if i < num_l - 1 and location_list[i + 1] in loc:
                    continue
                # filter_text = filter_text.replace(loc, 'LOC')
                filter_text = filter_text.replace(loc, 'LOC')
                loc_entites.append({'name': 'LOC', 'orgin': loc, 'norm': loc})
            if loc_entites:
                entity_data['slots'] = entity_data['slots'] + loc_entites
        if time_dict.get('entity') and time_dict.get('type'):
            # print(time_dict)
            time_entites = []
            t_type = time_dict.get('type')

            if not isinstance(time_dict[t_type], list):
                time_dict[t_type] = [time_dict[t_type]]
            else:
                time_dict[t_type] = time_dict[t_type]
            for e, t in zip(time_dict['entity'], time_dict[t_type]):
                filter_text = filter_text.replace(e, 'DATE')
                if t_type == 'timedelta':
                    for tp in t.keys():
                        tp_v = t.get(tp)
                        if tp_v and tp_v != 0:
                            timestamp_dict = {"year": "年", "month": "月", "day": "天", "hour": "小时", "minute": "分钟",
                                              "second": "秒"}
                            time_entites.append(
                                {'name': 'DATE' + '.' + tp, 'orgin': str(tp_v) + timestamp_dict.get(tp, ''),
                                 'norm': str(tp_v)})
                else:
                    time_entites.append({'name': 'DATE' + '.' + t_type, 'orgin': e, 'norm': t})
            if time_entites:
                entity_data['slots'] = entity_data['slots'] + time_entites
        if name_list:
            name_entites = []
            for per in name_list:
                filter_text = filter_text.replace(per, 'PER')
                name_entites.append({'name': 'PER', 'orgin': per, 'norm': per})
            if name_entites:
                entity_data['slots'] = entity_data['slots'] + name_entites
        entity_data['filter_text'] = filter_text
        return entity_data

    # 实体字典查询
    def entityDict(self, text, skill_id):
        redis_cn = get_redis_connection('default')
        entity_data = {}

        entity_data['slots'] = []
        filter_text = text
        if skill_id == 'patent':
            seg_list = jieba.lcut(text, cut_all=False)
            if seg_list:
                # print(seg_list)
                department_entities = []
                patent_entities = []
                patent_dict = {'专利': 'class', '提案': 'class', '外观': 'type', '实用新型': 'type', '发明': 'type',
                               '申请': 'process', '授权': 'process', '授权率': 'process', '驳回率': 'process', '通过率': 'process'}
                for t in seg_list:
                    department_dict = {}
                    department_dict = json.loads(redis_cn.hget(name='company_data', key='department').decode('utf-8'))
                    d_value = department_dict.get(t, '')
                    if d_value and not department_entities:
                        department_entities.append({'name': 'department', 'orgin': d_value, 'norm': d_value})
                        filter_text = filter_text.replace(t, '')
                    p_value = patent_dict.get(t, '')
                    if p_value:
                        patent_entities.append({'name': p_value, 'orgin': t, 'norm': t})

                entity_data['slots'] = entity_data['slots'] + department_entities + patent_entities

        entity_data['filter_text'] = filter_text
        # print(entity_data)
        return entity_data

    # nlu接口协议转换
    def nluTranslate(self, mess_data, skill_list):
        response_data = {}
        if self.user_id and mess_data:
            try:
                s_data = {'user_id': self.user_id, 'text': self.chineseToDigits(text=mess_data)}
                gner_enti = {}
                patent_enti = {}
                res = {}
                # print(s_data['text'])
                for n in skill_list:
                    if n == 'patent':
                        patent_data = self.entityDict(text=mess_data, skill_id=n)
                        s_data['text'] = patent_data.pop('filter_text')
                        # print(s_data['text'])

                        patent_enti = patent_data.get('slots')
                        gner_data = self.generalEntity(text=s_data.get('text', ''))
                        s_data['text'] = gner_data.pop('filter_text')
                        gner_enti = gner_data.get('slots')
                        # print(s_data)

                        res = loop.run_until_complete(nlu_agent(message=s_data['text']))
                res_data = {}
                confid_num = 0
                if res:
                    # print(d)
                    c = res.get('intent', {}).get('confidence', -1)
                    if c > confid_num:
                        res_data = res
                        confid_num = c
                response_data['code'] = 200
                data_dict = {}
                data_dict['recipientId'] = self.user_id
                dt_dict = res_data.get('intent', {})
                entites_list = res_data.get('entities', {})
                confid_num = dt_dict.get('confidence', 0)

                if confid_num > 0.95:
                    name_list = dt_dict.get('name', '').split('-')
                    data_dict['semantic'] = {'domain': name_list[0], 'intent': name_list[-1]}
                    entites_data = []
                    if entites_list:
                        for et in entites_list:
                            if et.get('entity') != 'datetime':
                                entites_data.append(
                                    {'name': et.get('entity'), 'orgin': et.get('value'), 'norm': et.get('value')})
                    en_d = entites_data.copy()
                    for p in en_d:
                        if p in patent_enti:
                            entites_data.remove(p)
                    if gner_enti:
                        entites_data = entites_data + gner_enti
                    if patent_enti:
                        entites_data = entites_data + patent_enti
                    # if not entites_data:
                    #     response_data['code'] = 202
                    if entites_data:
                        data_dict['semantic'].update({'slots': entites_data})
                    data_dict['semantic'].update({'sessionComplete': True})
                    response_data['data'] = data_dict
                    response_data['msg'] = 'IA nlu work'
                else:
                    response_data['code'] = 201
                    data_dict['semantic'] = {}
                    response_data['data'] = data_dict
                    response_data['msg'] = 'IA nlu not support'

            except (Exception, BaseException) as e:
                logger.Logger(project_name="patent_intelligent-assistant", server_name='dialogue',
                              logger_path=root_log_path).error(
                    json.dumps({"request": mess_data, "response": str(e), "error": "nlu"}, ensure_ascii=False))
                response_data['code'] = 500
                response_data['data'] = {}
                response_data['msg'] = 'IA nlu error'
        elif not self.user_id and mess_data:
            response_data['code'] = 501
            response_data['data'] = {}
            response_data['msg'] = 'user id is miss'
        elif self.user_id and not mess_data:
            response_data['code'] = 502
            response_data['data'] = {}
            response_data['msg'] = 'message data is miss'

        return response_data

    # 对话交互接口协议转换
    def dialogueTranslate(self, mess_data, skill_list):
        response_data = {}
        if self.user_id and mess_data:
            try:
                s_data = {'sender': self.user_id, 'message': self.chineseToDigits(text=mess_data)}
                res_data = {}
                res = {}
                gner_enti = {}
                if mess_data == 'voice-wakeup0':
                    server_start = ServerStart(user_id=self.user_id)
                    res_data['recipientId'] = self.user_id
                    l_data = server_start.dialogueStart(mess_data=mess_data, skill_list=['patent'])
                    l_data['speechStatus'] = 0
                    res_data['semantic'] = {"domain": "", "intent": "", 'sessionComplete': True}
                    res_data['response'] = l_data
                elif mess_data == 'voice-wakeup1':
                    res_data['recipientId'] = self.user_id
                    res_data['semantic'] = {"domain": "", "intent": "", 'sessionComplete': True}
                    res_data['response'] = {"resVoice": "您好！我在！", "resText": "", "resPicture": [], "resVideo": [],
                                            "resForm": {}, "speechStatus": 1}
                elif mess_data == 'voice-end':
                    res_data['recipientId'] = self.user_id
                    res_data['semantic'] = {"domain": "", "intent": "", 'sessionComplete': True}
                    res_data['response'] = {"resVoice": "voice-end", "resText": "", "resPicture": [], "resVideo": [],
                                            "resForm": {}, "speechStatus": 4}
                else:
                    # gner_data = self.generalEntity(text=s_data.get('message', ''))
                    # gner_enti = gner_data.get('slots')
                    # s_data['message'] = gner_data.pop('filter_text')
                    for n in skill_list:
                        # if n in self.dialogue_skill.keys() and n == 'patent':
                        if n == 'patent':
                            # s_data = {'sender': self.user_id,
                            #           'message': c2d.takeNumberFromString(s_data['text'])['replacedText']}
                            semantic_dict = self.nluTranslate(mess_data=mess_data, skill_list=['patent'])
                            data_search = DataSearch(message=mess_data)
                            res_data['recipientId'] = self.user_id
                            if semantic_dict.get('code') == 200:
                                sem_data = semantic_dict.get('data', {}).get('semantic', {"domain": "", "intent": "",
                                                                                          'sessionComplete': True})
                            else:
                                sem_data = {"domain": "", "intent": "", 'sessionComplete': True}
                            res_data['semantic'] = sem_data
                            if sem_data.get('intent') == 'goodbye':
                                res_data['response'] = {"resVoice": "好的，再见！", "resText": "", "resPicture": [],
                                                        "resVideo": [],
                                                        "resForm": {}, "speechStatus": 2}
                            elif sem_data.get('intent') == 'return':
                                res_data['response'] = {"resVoice": "嗯，好的！", "resText": "", "resPicture": [],
                                                        "resVideo": [],
                                                        "resForm": {}, "speechStatus": 2}
                            else:
                                res_data['response'] = data_search.dataSearch(semantic_data=semantic_dict)
                            break

                if res_data:
                    response_data['code'] = 200
                    response_data['data'] = res_data
                    response_data['msg'] = 'IA dialogue work'
                else:
                    response_data['code'] = 201
                    response_data['data'] = {'recipientId': self.user_id}
                    response_data['msg'] = 'IA dialogue not support'

            except (Exception, BaseException) as e:
                logger.Logger(project_name="patent_intelligent-assistant", server_name='dialogue',
                              logger_path=root_log_path).error(
                    json.dumps({"request": mess_data, "response": str(e)}, ensure_ascii=False))
                response_data['code'] = 500
                response_data['data'] = {}
                response_data['msg'] = 'IA dialogue error'
        elif not self.user_id and mess_data:
            response_data['code'] = 501
            response_data['data'] = {}
            response_data['msg'] = 'user id is miss'
        elif self.user_id and not mess_data:
            response_data['code'] = 502
            response_data['data'] = {}
            response_data['msg'] = 'message data is miss'

        return response_data


# 文本搜索模块
class DataSearch:
    def __init__(self, message):
        self.mess_data = message

    def dataSearch(self, semantic_data):
        s_code = semantic_data.get('code')
        t_data, t_score = self.textSearch()

        if s_code == 200 and '奖' not in self.mess_data:
            try:
                p_data = self.semanticSearch(semantic_dict=semantic_data.get('data', {}))
            except (Exception, BaseException) as e:
                logger.Logger(project_name="patent_intelligent-assistant", server_name='dialogue',
                              logger_path=root_log_path).error(
                    json.dumps({"request": self.mess_data, "response": str(e)}, ensure_ascii=False))
                p_data = {}
            if p_data:
                patent_data = p_data
            elif t_score >= 5:
                patent_data = t_data
            else:
                patent_data = self.defaultData()
        elif t_score >= 5:
            patent_data = t_data
        else:
            patent_data = self.defaultData()

        return patent_data

    def semanticSearch(self, semantic_dict):
        # print(semantic_dict)

        s_data = semantic_dict.get('semantic', {})
        res_data = {}

        domain_value = s_data.get('domain', '')

        intent_value = s_data.get('intent', '')

        s_entities = s_data.get('slots', [])

        if domain_value == 'patent':
            department_value = ''
            time_value = ''
            class_value = ''
            type_value = ''
            process_value = ''
            top_value = ''

            sql = ''
            sql2 = ''

            for ent_dict in s_entities:
                e_v = ent_dict.get('name')
                v_v = ent_dict.get('norm')
                if e_v == 'class':
                    class_value = v_v
                elif e_v == 'type':
                    type_value = v_v
                elif e_v == 'process':
                    process_value = v_v
                elif e_v == 'top':
                    top_value = v_v.replace('.0', '')
                elif e_v == 'department':
                    department_value = v_v
                elif e_v == 'DATE.timestamp':
                    time_value = v_v
            if not department_value:
                return {}
            if not class_value:
                class_value = '专利'
            if not time_value and process_value:
                time_value = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            res_text = ''
            apply_dict = {'发明': 'invention_apply_num', '实用新型': 'model_apply_num', '外观': 'design_apply_num'}
            author_dict = {'发明': 'invention_authorize_num', '实用新型': 'model_authorize_num', '外观': 'design_authorize_num'}
            if class_value in ['专利', '提案'] and '申请' in process_value:
                sql = 'select datetime, %s from patent_data_tb ' % apply_dict.get(type_value,
                                                                                  'invention_apply_num,model_apply_num,'
                                                                                  'design_apply_num')
                if top_value:
                    sql = 'select datetime, rank_apply from patent_data_tb '

            elif class_value in ['专利', '提案'] and '驳回率' in process_value:
                sql = 'select datetime, reject_rate from patent_data_tb '

            elif class_value in ['专利', '提案'] and '授权率' in process_value:
                sql = 'select datetime, authorize_rate from patent_data_tb '

            elif class_value in ['专利', '提案'] and '授权' in process_value:
                sql = 'select datetime, %s from patent_data_tb ' % author_dict.get(type_value,
                                                                                   'invention_authorize_num,'
                                                                                   'model_authorize_num,design_authorize_num ')
                if top_value:
                    sql = 'select datetime,rank_authorize from patent_data_tb '

            elif class_value in ['专利', '提案']:
                if type_value:
                    sql = 'select datetime,%s,%s from patent_data_tb ' % (
                        apply_dict.get(type_value), author_dict.get(type_value))
                else:
                    sql = 'select datetime,invention_apply_num,model_apply_num,design_apply_num,' \
                          'invention_authorize_num,model_authorize_num,design_authorize_num from patent_data_tb '
                if top_value:
                    sql = 'select datetime,rank_authorize from patent_data_tb '

            if sql:
                sql_list = []
                for d in reversed(range(5)):
                    sql_list.append(
                        '(select max(datetime) as datetime from patent_data_tb where department_id=%d and year('
                        'datetime)=year(now())-%d)' % (int(department_value), d))
                if sql_list:
                    sql2 = ','.join(sql_list)
                # if time_value:
                #     ti_list = time_value.split('-')
                #     if ti_list:
                #         res_text = ti_list[0] + '年' + res_text
                # else:
                #     res_text = '截止目前，' + res_text

                if department_value:
                    sql = sql + 'where department_id=%s ' % department_value

                sql2 = sql + 'and datetime in (%s) order by datetime desc' % sql2

                if time_value:
                    if 'where' in sql:
                        sql = sql + "and year(datetime)=year('%s') " % time_value
                    else:
                        sql = sql + "where year(datetime)=year('%s') " % time_value
                else:
                    if 'where' in sql:
                        sql = sql + "and year(datetime)=year(now()) "
                    else:
                        sql = sql + "where year(datetime)=year(now()) "

                sql = sql + ' order by datetime desc limit 1'
                sql = sql.replace('%s', '')
                # print(sql)
                with connections['default'].cursor() as cursor:
                    if sql2 and not top_value:
                        m_sql = '(' + sql + ') union all (' + sql2 + ')'
                        cursor.execute(m_sql)
                    else:
                        cursor.execute(sql)

                    result = cursor.fetchall()
                    name = cursor.description
                    connections['default'].commit()
                res_chart = {}
                if result and result[0]:
                    dep_name = ''
                    if department_value:
                        redis_cn = get_redis_connection('default')
                        department_dict = {}
                        department_dict = json.loads(
                            redis_cn.hget(name='company_data', key='department').decode('utf-8'))
                        for k in department_dict.keys():
                            if department_dict[k] == department_value:
                                res_text = k + res_text
                                dep_name = k
                                break

                    if not top_value:
                        name_dict = {'invention_apply_num': '发明专利申请数量为%s', 'model_apply_num': '实用新型专利申请数量为%s',
                                     'design_apply_num': '外观专利申请数量为%s', 'invention_authorize_num': '发明专利授权数量为%s',
                                     'model_authorize_num': '实用新型专利授权数量为%s', 'design_authorize_num': '外观专利授权数量为%s',
                                     'reject_rate': '驳回率为%s', 'authorize_rate': '授权率为%s'}
                        date_value = datetime.strptime(time_value, "%Y-%m-%d %H:%M:%S")
                        d_year = result[0][0].year
                        if date_value.year != d_year:
                            res_text = '抱歉，未找到%s%s年的专利数据' % (res_text, date_value.strftime("%Y"))
                        else:
                            res_text = '%s-01-01至%s,' % (
                                result[0][0].strftime("%Y"), result[0][0].strftime("%Y-%m-%d") + res_text)
                            res_text = res_text + ','.join(
                                [name_dict.get(n_t[0]) for n_t in name[1:] if n_t[0] in name_dict.keys()])
                            res_text = res_text % result[0][1:]

                            # if type_value:
                            #     if process_value:
                            #         res_text = res_text + type_value + class_value + process_value + '数量为%s'
                            #     else:
                            #         res_text = res_text + type_value + class_value + '申请数量为%s,授权数量为%s'
                            # elif process_value == '授权率' or process_value == '驳回率':
                            #     res_text = res_text + '专利' + process_value + '为%s,'
                            # elif class_value and process_value:
                            #     for t in ['发明', '实用新型', '外观']:
                            #         res_text = res_text + t + class_value + process_value + '数量为%s,'
                            # elif class_value:
                            #     for t in ['发明', '实用新型', '外观']:
                            #         res_text = res_text + t + class_value + '申请数量为%s,授权数量为%s,'

                        label_dict = {'datetime': '时间', 'invention_apply_num': '发明专利申请', 'model_apply_num': '实用新型专利申请',
                                      'design_apply_num': '外观专利申请', 'invention_authorize_num': '发明专利授权',
                                      'model_authorize_num': '实用新型专利授权', 'design_authorize_num': '外观专利授权',
                                      'reject_rate': '驳回率', 'authorize_rate': '授权率'}
                        y_name_list = [label_dict.get(n_t[0]) for n_t in name if n_t[0] in label_dict.keys()]

                        chart_result = result[1:]
                        chart_result = sorted(chart_result)

                        x_data = []
                        y_data = []
                        x_name = y_name_list[0]
                        for ch_t in chart_result:
                            x_data.append(ch_t[0].strftime("%Y"))

                        for n in range(1, len(y_name_list)):
                            yn_d = []
                            yn_n = y_name_list[n]
                            for ch_t in chart_result:
                                yn_d.append(ch_t[n])
                            y_data.append({'name': yn_n, 'data': yn_d})
                        res_chart['name'] = '%s-%s年%s专利情况' % (x_data[0], x_data[-1], dep_name)
                        res_chart['xAxis'] = [{'name': x_name, 'data': x_data}]
                        res_chart['yAxis'] = y_data

                    elif top_value:
                        for row in result:
                            t_row = row[-1]
                            if t_row and isinstance(t_row, str):
                                row_list = t_row.split(',')
                                if row_list:
                                    num_list = re.findall(r'\d+', top_value)
                                    if num_list:
                                        num = int(num_list[0])
                                        t_list = []
                                        if num > len(row_list):
                                            t_list = row_list
                                        else:
                                            t_list = row_list[0:num]
                                        if t_list:
                                            t_str = ','.join(t_list)
                                        else:
                                            t_str = ''
                                        if len(t_list) == num:
                                            res_text = res_text + class_value + process_value + '数量' + top_value + '的同事为' + t_str
                                        else:
                                            res_text = res_text + class_value + process_value + '数量仅查询到排名前' + str(
                                                len(t_list)) + '的同事:' + t_str
                                        break
                                else:
                                    res_text = '不好意思,' + res_text + class_value + process_value + '数量' + top_value + '的同事未找到'
                            else:
                                res_text = '不好意思,' + res_text + class_value + process_value + '数量' + top_value + '的同事未找到'
                    else:
                        res_text = res_text % result
                if not res_text:
                    res_text = '抱歉,未查询到相关数据!'
                res_data['resVoice'] = res_text
                res_data['resText'] = res_text
                res_data['resPicture'] = []
                res_data['resVideo'] = []
                res_data['resForm'] = {}
                res_data['resChart'] = res_chart
                res_data['speechStatus'] = 2

        return res_data

    def textSearch(self):

        # ques_str = ''.join(patent_actions.preprocess_data(self.mess_data.replace(' ', '')))
        ques_str = self.mess_data
        # print(ques_str)
        # body_data = {'query': {'match': {'question': {"query": self.mess_data, 'analyzer': 'ik_smart'}}}}
        body_data = {'query': {'match': {'question': ques_str}}}
        res_data = ES.search(index=settings.INDEX_NAME, body=body_data)
        shards_data = res_data.get('_shards')
        if shards_data and shards_data.get('successful', 0) > 0:
            hits_data = res_data.get('hits', {}).get('hits', [])
            # print(hits_data)
            if hits_data:
                data_dict = hits_data[0]
            else:
                data_dict = {}
        else:
            data_dict = {}
        p_score = data_dict.get('_score', 0)
        # print(p_score)
        if data_dict:
            video_dict = {}

            patent_dict = data_dict.get('_source', {})
            patent_dict.pop('timestamp')
            picture_list = patent_dict.get('resPicture', [])
            if picture_list:
                picture_list = [os.path.join(settings.PICTURES_URL, p) for p in picture_list]
                patent_dict['resPicture'] = picture_list

            video_list = patent_dict.get('resVideo', [])
            if video_list:
                video_list = [os.path.join(settings.VIDEOS_URL, p) for p in video_list]
                video_dict['resVideo'] = video_list
            if patent_dict.get('question'):
                patent_dict.pop('question')
            if patent_dict.get('resVoice'):
                patent_dict['resVoice'] = patent_dict['resVoice'].replace('$', '')
            patent_dict['speechStatus'] = 2
        else:
            patent_dict = {}

        logger.Logger(project_name="patent_intelligent-assistant", server_name='dialogue',
                      logger_path=root_log_path).info(
            json.dumps({"request": self.mess_data, "response": {"data": patent_dict, "score": p_score}},
                       ensure_ascii=False))
        return patent_dict, p_score

    def defaultData(self):
        redis_skill = get_redis_connection('default')
        if redis_skill.hexists('company_data', 'default'):
            tooltip_list = json.loads(redis_skill.hget(name='company_data', key='default').decode('utf-8'))
        else:
            tooltip_list = {}
        default_data = random.choice(tooltip_list)
        picture_list = default_data.get('resPicture', [])
        if picture_list:
            picture_list = [os.path.join(settings.PICTURES_URL, p) for p in picture_list]
            default_data['resPicture'] = picture_list
        default_data['speechStatus'] = 3
        return default_data


# 服务启动模块
class ServerStart:
    def __init__(self, user_id):
        self.user_id = user_id
        # redis_skill = get_redis_connection('default')
        # if redis_skill.hexists('online_skill', 'text_skill'):
        #     self.text_skill = json.loads(redis_skill.hget(name='online_skill', key='text_skill').decode('utf-8'))
        # else:
        #     self.text_skill = {}
        #
        # if redis_skill.hexists('online_skill', 'nlu_skill'):
        #     self.nlu_skill = json.loads(redis_skill.hget(name='online_skill', key='nlu_skill').decode('utf-8'))
        # else:
        #     self.nlu_skill = {}

        # if redis_skill.hexists('online_skill', 'dialogue_skill'):
        #     self.dialogue_skill = json.loads(
        #         redis_skill.hget(name='online_skill', key='dialogue_skill').decode('utf-8'))
        # else:
        #     self.dialogue_skill = {}

    def startData(self):
        redis_skill = get_redis_connection('default')
        if redis_skill.hexists('company_data', 'start'):
            tooltip_list = json.loads(redis_skill.hget(name='company_data', key='start').decode('utf-8'))
        else:
            tooltip_list = {}
        start_data = random.choice(tooltip_list)
        picture_list = start_data.get('resPicture', [])
        if picture_list:
            picture_list = [os.path.join(settings.PICTURES_URL, p) for p in picture_list]
            start_data['resPicture'] = picture_list
        start_data['speechStatus'] = 0
        return start_data

    def dialogueStart(self, mess_data, skill_list):
        response_data = {}
        for n in skill_list:
            # if n in self.dialogue_skill.keys():
            if n == 'patent':
                response_data = self.startData()
                continue
        return response_data


# 数据存储类
class SkillTest:
    def __init__(self, user_id):
        self.user_id = user_id

    def dialogueProcess(self, mess_data, skill_list):
        # print(mess_data)
        # print(skill_list)
        response_data = {}

        dia_list = skill_list.get('dialogue')

        if dia_list:
            response_data['dialogue'] = self.dialogueTranslate(mess_data, dia_list)

        return response_data

    # 数据预处理模块
    def chineseToDigits(self, text):
        f_text = c2d.takeNumberFromString(text)['replacedText'].replace('.0', '')
        return f_text

    # 通用实体提取
    def generalEntity(self, text):
        entity_data = {}
        ex = cocoNLP.extractor.extractor()

        l_list = ex.extract_locations(text)
        location_list = [p.replace("今天", "").replace("天气", "") for p in l_list]

        time_dict = json.loads(ex.extract_time(text))

        name_list = ex.extract_name(text)

        entity_data['slots'] = []
        filter_text = text
        if location_list:
            loc_entites = []
            num_l = len(location_list)
            for i in range(num_l):
                loc = location_list[i]
                if i < num_l - 1 and location_list[i + 1] in loc:
                    continue
                # filter_text = filter_text.replace(loc, 'LOC')
                filter_text = filter_text.replace(loc, 'LOC')
                loc_entites.append({'name': 'LOC', 'orgin': loc, 'norm': loc})
            if loc_entites:
                entity_data['slots'] = entity_data['slots'] + loc_entites
        if time_dict.get('entity'):
            # print(time_dict)
            time_entites = []
            t_type = time_dict.get('type')

            if not isinstance(time_dict[t_type], list):
                time_dict[t_type] = [time_dict[t_type]]
            else:
                time_dict[t_type] = time_dict[t_type]
            for e, t in zip(time_dict['entity'], time_dict[t_type]):
                filter_text = filter_text.replace(e, 'DATE')
                if t_type == 'timedelta':
                    for tp in t.keys():
                        tp_v = t.get(tp)
                        if tp_v and tp_v != 0:
                            timestamp_dict = {"year": "年", "month": "月", "day": "天", "hour": "小时", "minute": "分钟",
                                              "second": "秒"}
                            time_entites.append(
                                {'name': 'DATE' + '.' + tp, 'orgin': str(tp_v) + timestamp_dict.get(tp, ''),
                                 'norm': str(tp_v)})
                else:
                    time_entites.append({'name': 'DATE' + '.' + t_type, 'orgin': e, 'norm': t})
            if time_entites:
                entity_data['slots'] = entity_data['slots'] + time_entites
        if name_list:
            name_entites = []
            for per in name_list:
                filter_text = filter_text.replace(per, 'PER')
                name_entites.append({'name': 'PER', 'orgin': per, 'norm': per})
            if name_entites:
                entity_data['slots'] = entity_data['slots'] + name_entites
        entity_data['filter_text'] = filter_text
        return entity_data

    # 实体字典查询
    def entityDict(self, text, skill_id):
        redis_cn = get_redis_connection('default')
        entity_data = {}

        entity_data['slots'] = []
        filter_text = text
        if skill_id == 'patent':
            seg_list = jieba.lcut(text, cut_all=False)
            if seg_list:
                # print(seg_list)
                department_entities = []
                patent_entities = []
                patent_dict = {'专利': 'class', '提案': 'class', '外观': 'type', '实用新型': 'type', '发明': 'type',
                               '申请': 'process', '授权': 'process', '授权率': 'process', '驳回率': 'process', '通过率': 'process'}
                for t in seg_list:
                    department_dict = {}
                    department_dict = json.loads(redis_cn.hget(name='company_data', key='department').decode('utf-8'))
                    d_value = department_dict.get(t, '')
                    if d_value and not department_entities:
                        department_entities.append({'name': 'department', 'orgin': d_value, 'norm': d_value})
                        filter_text = filter_text.replace(t, '')
                    p_value = patent_dict.get(t, '')
                    if p_value:
                        patent_entities.append({'name': p_value, 'orgin': t, 'norm': t})
                if department_entities:
                    entity_data['slots'] = entity_data['slots'] + department_entities
                if patent_entities:
                    entity_data['slots'] = entity_data['slots'] + patent_entities

        entity_data['filter_text'] = filter_text
        # print(entity_data)
        return entity_data

    # 对话交互接口协议转换
    def dialogueTranslate(self, mess_data, skill_list):
        response_data = {}
        if self.user_id and mess_data:
            # try:
            s_data = {'sender': self.user_id, 'message': self.chineseToDigits(text=mess_data)}
            res_data = {}
            res = {}
            gner_enti = {}
            if mess_data == 'voice-wakeup0':
                server_start = ServerStart(user_id=self.user_id)
                res_data['recipientId'] = self.user_id
                l_data = server_start.dialogueStart(mess_data=mess_data, skill_list=['patent'])
                l_data['speechStatus'] = 0
                res_data['semantic'] = {"domain": "", "intent": "", 'sessionComplete': True}
                res_data['response'] = l_data
            elif mess_data == 'voice-wakeup1':
                res_data['recipientId'] = self.user_id
                res_data['semantic'] = {"domain": "", "intent": "", 'sessionComplete': True}
                res_data['response'] = {"resVoice": "您好！我在！", "resText": "", "resPicture": [], "resVideo": [],
                                        "resForm": {}, "speechStatus": 1}
            elif mess_data == 'voice-end':
                res_data['recipientId'] = self.user_id
                res_data['semantic'] = {"domain": "", "intent": "", 'sessionComplete': True}
                res_data['response'] = {"resVoice": "voice-end", "resText": "", "resPicture": [], "resVideo": [],
                                        "resForm": {}, "speechStatus": 4}
            else:
                # gner_data = self.generalEntity(text=s_data.get('message', ''))
                # gner_enti = gner_data.get('slots')
                # s_data['message'] = gner_data.pop('filter_text')
                for n in skill_list:
                    # if n in self.dialogue_skill.keys() and n == 'patent':
                    if n == 'patent':
                        # s_data = {'sender': self.user_id,
                        #           'message': c2d.takeNumberFromString(s_data['text'])['replacedText']}
                        res_data['recipientId'] = self.user_id
                        host = "ntrans.xfyun.cn"
                        gClass = NLU.get_result(host)
                        response_d = gClass.call_url(text=mess_data)
                        res_text = response_d.get('dst', '')
                        res_data['semantic'] = {"domain": "", "intent": "", 'sessionComplete': True}
                        res_data['response'] = {"resVoice": res_text, "resText": res_text, "resPicture": [],
                                                "resVideo": [],
                                                "resForm": {}, "speechStatus": 3}

            if res_data:
                response_data['code'] = 200
                response_data['data'] = res_data
                response_data['msg'] = 'IA dialogue work'
            else:
                response_data['code'] = 201
                response_data['data'] = {'recipientId': self.user_id}
                response_data['msg'] = 'IA dialogue not support'

            # except Exception as e:
            #     print("kitchen assistant error type: %s" % str(e))
            #     response_data['code'] = 500
            #     response_data['data'] = {}
            #     response_data['msg'] = 'IA dialogue error'
        elif not self.user_id and mess_data:
            response_data['code'] = 501
            response_data['data'] = {}
            response_data['msg'] = 'user id is miss'
        elif self.user_id and not mess_data:
            response_data['code'] = 502
            response_data['data'] = {}
            response_data['msg'] = 'message data is miss'

        return response_data


if __name__ == '__main__':
    # data_storage = DataStorage()
    # print(data_storage.skillManage(data={'8021': 'kitchen', '8031': 'shopping'}, action_type='put'))

    # data_storage = DataStorage()
    # path = os.path.join(os.path.abspath(
    #     os.path.join(os.path.dirname(os.path.realpath(__file__)), "../IntelligentAssistant/common/data")),
    #     "skill_list.xlsx")
    # data_storage.skillUpdate(data_path=path)

    # sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")))

    # SS = ServerStart(user_id='000')
    # res = SS.dialogueStart(mess_data='start', skill_list=["patent"])
    # print(res)

    # DD = DataSearch(message='什么是专利权')
    # print(DD.textSearch())

    DP = Dialogue(user_id='000')
    # text='物联网院外观专利数量查询'
    text = '格力电器第1件专利申请'
    res_data = DP.dialogueProcess(mess_data=text, skill_list={"dialogue": ["patent"]})
    print(res_data)

    # DD = DataSearch(message='家技部专利申请情况')
    # # sem_data = {'recipientId': '000', 'semantic': {'domain': 'patent', 'intent': 'search_state', 'slots': [
    # #     {'name': 'DATE.timestamp', 'orgin': '2020年', 'norm': '2020-01-01 00:00:00'},
    # #     {'name': 'department', 'orgin': '1', 'norm': '1'}, {'name': 'type', 'orgin': '外观', 'norm': '外观'},
    # #     {'name': 'class', 'orgin': '专利', 'norm': '专利'}], 'sessionComplete': True}}
    # sem_data = {'recipientId': '000', 'semantic': {'domain': 'patent', 'intent': 'search_state', 'slots': [
    #     {'name': 'department', 'orgin': '1', 'norm': '1'}, {'name': 'process', 'orgin': '申请', 'norm': '申请'},
    #     {'name': 'class', 'orgin': '专利', 'norm': '专利'}], 'sessionComplete': True}}
    # print(DD.semanticSearch(sem_data))

    # DD1 = DataSearch(message='关于家用空调的相关专利')
    # print(DD1.textSearch())

    # intran = InterfaceTranslate(user_id='001', message='苹果存储', skill=['80201'])
    # DP = Dialogue(user_id='000')
    # text_enti = DP.generalEntity(text='珠海今天和明天的天气')
    # print(text_enti)
    # print(patent_actions.preprocess_data('专利申请情况'))

    # ex = cocoNLP.extractor.extractor()
    # print(ex.extract_time('当前专利数量'))

    # import arrow
    # now=arrow.now()
    # print(now.weekday())
    # import jieba
    #

    # print(jieba.lcut('格力电器第1件专利申请'))
