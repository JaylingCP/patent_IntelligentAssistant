# encoding: utf-8
'''
@author: limingjie
@file: logger.py
@time: 2020/3/11 上午10:07
@desc: 服务日志模块
'''

import logging, datetime
import os


def Logger(project_name, server_name, logger_path):
    # project_name: 项目名称
    # server_name: 服务名称
    # logger_path: 日志存储地址

    logger_name = server_name + '.' + project_name
    logger = logging.getLogger(logger_name)
    logger.handlers = []

    # 创建一个handler，用于写入日志文件
    time_str = str(datetime.datetime.now().strftime("%Y%m%d"))
    logger_path = os.path.join(logger_path, project_name)
    if not os.path.exists(logger_path):
        os.makedirs(logger_path)
    l_path = os.path.join(logger_path, server_name + time_str + '.log')

    fh = logging.FileHandler(filename=l_path, mode='a', encoding='utf-8')
    logger_level = logging.DEBUG
    fh.setLevel(logger_level)

    # 定义handler的输出格式
    formatter = logging.Formatter(
        '{"time":"%(asctime)s.%(msecs)06d","appName":"%(name)s","tag":"%(module)s.%(funcName)s","level":"%(levelname)s","msg":%(message)s}',
        '%Y/%m/%d %H:%M:%S')
    fh.setFormatter(formatter)

    logger.addHandler(fh)
    logger.setLevel(logger_level)

    logging.shutdown()
    # logger.removeHandler(fh)

    return logger


if __name__ == '__main__':
    Logger(project_name='intelligent-assistant', server_name='dialogue', logger_path='./').info('')
