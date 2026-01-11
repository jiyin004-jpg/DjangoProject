from word import views
from django.urls import path
urlpatterns = [
    path('', views.home, name='home'),  # 首页
    path('about/', views.about, name='about'),  # 关于页面
    path('contact/', views.contact, name='contact'),  # 联系页面
    path('demo/', views.demo, name='demo'),  # 演示页面
    path('ai/', views.ai_chat, name='ai_chat'),  # AI聊天页面
    path('ai/chat/', views.ai_chat_api, name='ai_chat_api'),  # AI聊天API
    path('vocabulary/', views.vocabulary, name='vocabulary'),  # 单词本
    path('api/vocabulary/', views.get_vocabulary_api, name='api_vocabulary'),
    path('api/check-api-status/', views.check_api_data_status, name='api_check_status'),  # 检查API数据状态
    path('api/search/', views.search_words_api, name='api_search'),
    path('api/quick-lookup/', views.quick_word_lookup_api, name='api_quick_lookup'),  # 快速单词查询
]