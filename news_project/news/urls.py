from django.urls import path
from .views import *

app_name = 'news'
urlpatterns = [

    path('headline/', HeadlineList.as_view(), name='newslist'),
    path('headline/<int:pk>/', HeadlineDetail.as_view(), name='newsdetail'),
    path('publisher/', PublisherList.as_view(), name='publisherlist'),
    path('publisher/<int:pk>/', PublisherDetail.as_view(), name='publisherdetail'),
    path('wordcloud/', get_wordcloud_data, name='wordclouddata'),
    path('search/', NewsSearchList.as_view(), name='newssearchlist'),
]

