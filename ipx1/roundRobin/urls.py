from django.urls import path
from . import views # Importa as views do seu app

urlpatterns = [
    # ...outras rotas que você já tenha...
    
    # Adiciona a rota para a sua tabela
    path('leaderboard/', views.leaderboard_view, name='leaderboard'),
    path('matches/', views.match_list_view, name='match-list'),
]