from django.shortcuts import render
from .models import Player, Match

def leaderboard_view(request):
    
    # Busca todos os jogadores no banco de dados
    # A ordenação é a chave:
    # 1º: Ordena por 'wins' (descendente, quem tem mais vence)
    # 2º: Desempata por 'losses' (ascendente, quem tem menos perde)
    players_list = Player.objects.all().order_by('-wins', 'losses')

    # Envia a lista de jogadores para o template
    context = {
        'players': players_list
    }
    
    # Renderiza o HTML que você pediu
    return render(request, 'roundRobin/leaderboard.html', context)

def match_list_view(request):
    """
    Busca todas as partidas concluídas e as envia para o template.
    """
    # Filtramos por 'winner__isnull=False' para mostrar apenas partidas
    # que já têm um vencedor (ou seja, foram processadas).
    # Ordenamos por '-created_at' para mostrar as mais recentes primeiro.
    matches_list = Match.objects.filter(winner__isnull=False).order_by('-created_at')
    
    context = {
        'matches': matches_list
    }
    
    return render(request, 'roundRobin/match_list.html', context)