from django.http import HttpResponse
from django.shortcuts import render, redirect


# Create your views here.
def my_view(request):
    return HttpResponse("hello world")
def my_view1(request):
    return render(request,'index.html',{'name':1})
def my_view2(request):
    return redirect('https://www.baidu.com/')
def form(request):
    if request.method == "POST":
        print(request.POST)
        return HttpResponse("hello world")

    else:
        return render(request,'index1.html')
