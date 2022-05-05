from django.shortcuts import render

# Create your views here.
from rest_framework.response import Response
from rest_framework.views import APIView
from patent_IntelligentAssistant.common import logger
import json
import time
import resource.models
from django.conf import settings

root_log_path = settings.LOGS_DIR


class Resource(APIView):
    def post(self, request):
        start_time = time.time()
        data_post = resource.models.Resource(user_id=request.data.get('userId'))
        response_data = data_post.data_post(request.data)
        end_time = time.time()
        logger.Logger(project_name="patent_intelligent-assistant", server_name='resource',
                      logger_path=root_log_path).info(
            json.dumps({"request": request.query_params.dict(), "response": response_data,
                        "costTime": (end_time - start_time)},
                       ensure_ascii=False))
        return Response(response_data)

    def get(self, request):
        start_time = time.time()
        resq_data = request.query_params.dict()
        data_get = resource.models.Resource(user_id=resq_data.get('userId'))
        response_data = data_get.data_get(category=resq_data.get('category'), text=resq_data.get('text'),
                                          page_size=int(resq_data.get('pageSize')),
                                          page_num=int(resq_data.get('pageNum')))
        end_time = time.time()
        logger.Logger(project_name="patent_intelligent-assistant", server_name='resource',
                      logger_path=root_log_path).info(
            json.dumps({"request": request.data, "response": response_data, "costTime": (end_time - start_time)},
                       ensure_ascii=False))
        return Response(response_data)

    def put(self, request):
        start_time = time.time()
        data_put = resource.models.Resource(user_id=request.data.get('userId'))
        response_data = data_put.data_put(text_data=request.data)
        end_time = time.time()
        logger.Logger(project_name="patent_intelligent-assistant", server_name='resource',
                      logger_path=root_log_path).info(
            json.dumps({"request": request.query_params.dict(), "response": response_data,
                        "costTime": (end_time - start_time)},
                       ensure_ascii=False))
        return Response(response_data)

    def delete(self, request):
        start_time = time.time()
        data_delete = resource.models.Resource(user_id=request.data.get('userId'))
        response_data = data_delete.data_delete(text_data=request.data.get('data'))
        end_time = time.time()
        logger.Logger(project_name="patent_intelligent-assistant", server_name='resource',
                      logger_path=root_log_path).info(
            json.dumps({"request": request.data, "response": response_data, "costTime": (end_time - start_time)},
                       ensure_ascii=False))
        return Response(response_data)


class Category(APIView):
    def get(self, request):
        start_time = time.time()
        resq_data = request.query_params.dict()
        category_data = resource.models.DataDisplay(user_id=resq_data.get('userId'))
        response_data = category_data.category_get()
        end_time = time.time()
        logger.Logger(project_name="patent_intelligent-assistant", server_name='resource',
                      logger_path=root_log_path).info(
            json.dumps({"request": request.data, "response": response_data, "costTime": (end_time - start_time)},
                       ensure_ascii=False))
        return Response(response_data)
