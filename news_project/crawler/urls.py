from django.urls import path
from . import views

urlpatterns = [
    path('ycrawl/', views.youtube_crawling, name='crawl'),
    path('ncrawl', views.naver_crawling),
]