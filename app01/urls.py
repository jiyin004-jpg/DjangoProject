from app01 import views
from django.urls import path
urlpatterns = [
    path('index/', views.my_view),
    path('index1/', views.my_view1),
    path('index2/', views.my_view2),
    path('form/', views.form),
]