from django.shortcuts import render

def index(request):
    """ポモドーロタイマー & YouTube BGM ワークスペース"""
    context = {
        'title': 'Pomodoro Focus | ポモドーロタイマー & YouTube BGM',
    }
    return render(request, 'pomodoro/index.html', context)
