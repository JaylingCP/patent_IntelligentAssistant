# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/core/actions/#custom-actions/


# This is a simple example for a custom action which utters "Hello World!"

# from typing import Any, Text, Dict, List
#
# from rasa_sdk import Action, Tracker
# from rasa_sdk.executor import CollectingDispatcher
#
#

import os
import jieba


path1 = os.path.join(os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "./dict")),
                     "patent-dict.txt")
jieba.load_userdict(path1)


# 文本预处理
def preprocess_data(text):
    f_text = ''.join(filter(lambda x: x.isalpha(), text))
    segs = jieba.lcut(f_text, cut_all=False)

    m1_segs = [s for s in segs if len(s) >= 1]  # 去掉长度小于1的词
    # l_text = [x for x in m1_segs if x not in stopword_list]  # 去除停用词词
    return m1_segs


# class ActionHelloWorld(Action):
#
#     def name(self) -> Text:
#         return "action_hello_world"
#
#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#
#         dispatcher.utter_message(text="Hello World!")
#
#         return []

if __name__ == '__main__':
    print(preprocess_data('家技部专利排名前十的同事'))
