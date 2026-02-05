from django.shortcuts import render

def usage_view(request):
    return render(request, 'pages/usage.html')