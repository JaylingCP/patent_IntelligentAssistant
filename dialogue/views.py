from rest_framework.response import Response
from rest_framework.views import APIView
from patent_IntelligentAssistant.common import logger
import json
import time
import dialogue.models
from django.conf import settings

root_log_path = settings.LOGS_DIR


# Create your views here.

class Dialogue(APIView):
    def post(self, request):
        start_time = time.time()
        interface_translate = dialogue.models.Dialogue(user_id=request.data.get('userId'))
        response_data = interface_translate.dialogueProcess(mess_data=request.data.get('message'),
                                                            skill_list=request.data.get('skill'))
        end_time = time.time()
        logger.Logger(project_name="patent_intelligent-assistant", server_name='dialogue',
                      logger_path=root_log_path).info(
            json.dumps({"request": request.data, "response": response_data, "costTime": (end_time - start_time)},
                       ensure_ascii=False))
        return Response(response_data)


class Test(APIView):
    def post(self, request):
        start_time = time.time()
        interface_translate = dialogue.models.SkillTest(user_id=request.data.get('userId'))
        response_data = interface_translate.dialogueProcess(mess_data=request.data.get('message'),
                                                            skill_list=request.data.get('skill'))
        end_time = time.time()
        logger.Logger(project_name="patent_intelligent-assistant", server_name='test',
                      logger_path=root_log_path).info(
            json.dumps({"request": request.data, "response": response_data, "costTime": (end_time - start_time)},
                       ensure_ascii=False))
        return Response(response_data)
