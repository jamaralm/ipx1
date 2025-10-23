from django.urls import path
from . import views
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='leaderboard'), name='home'),
    
    path('livestream', views.livestream_view, name="livestream"),
    path('leaderboard/', views.leaderboard_view, name='leaderboard'),
    path('matches/', views.match_list_view, name='match-list'),
]