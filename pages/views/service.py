from django.shortcuts import render

def service_view(request):
    return render(request, 'pages/service.html')