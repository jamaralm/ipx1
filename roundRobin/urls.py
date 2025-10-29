from django.urls import path
from . import views
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='leaderboard'), name='home'),
    
    # path('admin/approval', views.admin_player_approval_view, name="admin-approval"),

    path('livestream/', views.livestream_view, name='livestream'),
    path('leaderboard/', views.leaderboard_view, name='leaderboard'),
    path('matches/', views.match_list_view, name='match-list'),
    path('playoffs/', views.playoffs_view, name='playoffs'),
]