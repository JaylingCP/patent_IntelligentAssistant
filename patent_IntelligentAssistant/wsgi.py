"""
WSGI config for IntelligentAssistant project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application
from patent_IntelligentAssistant.common import data_update

# profile = os.environ.get('PROJECT_PROFILE', 'test')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'patent_IntelligentAssistant.settings')

application = get_wsgi_application()


def update_data():
    data_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "./common/data")
    path1 = os.path.join(os.path.abspath(data_path), "skill_list.xlsx")
    data_update.skillUpdate(data_path=path1)

    path3 = os.path.join(os.path.abspath(data_path), "./patent_data/company_data.xlsx")
    data_update.departmentUpdate(data_path=path3)

    path4 = os.path.join(os.path.abspath(data_path), "./patent_data/tooltip_data.xlsx")
    data_update.tooltipUpdate(data_path=path4)


update_data()
