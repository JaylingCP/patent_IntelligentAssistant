# from django.test import TestCase
# from dialogue.models import DataStorage
# from dialogue.models import Dialogue
# from dialogue.models import InterfaceTranslate
#
#
# # Create your tests here.
#
# class DataStorageTestCase(TestCase):
#     def setUp(self):
#         self.skill_data = {'skill': {'8031': 'shopping'}}
#         self.dataStorage = DataStorage()
#
#     def testSkillManage(self):
#         # self.assertEqual(self.dataStorage.skillManage(data=self.skill_data, action_type='put'),
#         #                  ({}, {'8031': 'shopping'}))
#         self.assertEqual(self.dataStorage.skillManage(data=self.skill_data, action_type='delete'),
#                          ({}, {'8031': 'shopping'}))
#
#
# class InterfaceTranslateTestCase(TestCase):
#     def setUp(self):
#         self.user_id = '000'
#         self.mess_data = '物联网研究院专利申请情况'
#         self.skill_list = ['kitchen']
#         self.dialogue = Dialogue(self.user_id)
#
#     def testNluTranslate(self):
#         self.assertIsNotNone(self.dialogue.nluTranslate())
#
#     def testCommonEntity(self):
#         print(self.interfaceTranslate.commonEntity(text="珠海今天天气怎么样"))
#         self.assertIsNone(self.interfaceTranslate.commonEntity(text="珠海今天天气怎么样"))

import asyncio
from rasa.core.agent import Agent
from rasa.utils.endpoints import EndpointConfig

# async def test_agent():
#     endpoint = EndpointConfig(url="http://localhost:18024/webhook")
#     agent = Agent.load(
#         "./patent/models/nlu-20200930-161421.tar.gz",
#         action_endpoint=endpoint
#     )
#     result = await agent. parse_message_using_nlu_interpreter(message_data="专利申请情况")
#     # print(result)
#     return result
#
# loop = asyncio.get_event_loop()
# result=loop.run_until_complete(test_agent())
# print(result)
import os, sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'patent_IntelligentAssistant.settings')
from dialogue.models import DataSearch
from dialogue.models import Dialogue


def test_mysql(semantic_data):
    data_search = DataSearch(message='物联院的专利申请数量')
    data = data_search.semanticSearch(semantic_dict=semantic_data)
    return data


def test_generalEntity(text):
    dialogue = Dialogue(user_id='0000')
    re_text = dialogue.generalEntity(text=text)
    return re_text


if __name__ == '__main__':
    print(test_mysql(semantic_data={'recipientId': '000', 'semantic': {'domain': 'patent', 'intent': 'search_state',
                                                                       'slots': [
                                                                           {'name': 'department', 'orgin': '39',
                                                                            'norm': '39'},
                                                                           {'name': 'class', 'orgin': '专利',
                                                                            'norm': '专利'},
                                                                           {'name': 'process', 'orgin': '申请',
                                                                            'norm': '申请'}],
                                                                       'sessionComplete': True}}))
    sem_data = {'recipientId': '000', 'semantic': {'domain': 'patent', 'intent': 'search_state', 'slots': [
        {'name': 'DATE.timestamp', 'orgin': '2020年', 'norm': '2020-01-01 00:00:00'},
        {'name': 'department', 'orgin': '1', 'norm': '1'}, {'name': 'type', 'orgin': '外观', 'norm': '外观'},
        {'name': 'class', 'orgin': '专利', 'norm': '专利'}], 'sessionComplete': True}}
    print(test_mysql(semantic_data=sem_data))

    # print(test_generalEntity('2018年物联网研究院专利数量'))
