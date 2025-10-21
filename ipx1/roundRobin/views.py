from django.shortcuts import render
from .models import Player, Match, TOTAL_ROUNDS

def leaderboard_view(request):
    """
    Busca TODAS as partidas (agendadas e completas)
    e as organiza por rodada para exibir no template.
    """
    rounds_data = []

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
    Busca TODAS as partidas e as organiza por rodada.
    """
    
    rounds_data = []
    
    # Apenas UMA consulta em 'Match'
    all_matches = Match.objects.all().order_by('round_number', 'scheduled_time')
    
    for round_num in range(1, TOTAL_ROUNDS + 1):
        # Filtra as partidas em Python (mais rápido do que 10 consultas)
        matches_in_round = [m for m in all_matches if m.round_number == round_num]
        
        if matches_in_round:
            rounds_data.append({
                'round_number': round_num,
                'matches': matches_in_round # Passa a lista de objetos Match direto
            })

    context = {
        'rounds_list': rounds_data,
        
        # NOVO: Passamos as constantes de status para o template
        'STATUS_COMPLETED': Match.STATUS_COMPLETED,
        'STATUS_LIVE': Match.STATUS_LIVE,
        'STATUS_SCHEDULED': Match.STATUS_SCHEDULED,
    }
    
    return render(request, 'roundRobin/match_list.html', context)