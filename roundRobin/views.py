from django.shortcuts import render
from .models import Player, Match, TOTAL_ROUNDS, STATUS_COMPLETED, STATUS_SCHEDULED

def leaderboard_view(request):
    """
    Busca todos os jogadores e os ordena pelos critérios de desempate
    (Séries > T.M.V. > Saldo K/D) para exibir na tabela.
    """
    
    # 1. Pega todos os jogadores
    # (Se você já tivesse o 'is_approved', filtraria aqui)
    all_players = Player.objects.all() 

    # 2. Ordena a lista em Python usando sorted()
    #    'key=lambda p:' é uma mini-função que diz ao sorted() como comparar.
    
    sorted_players = sorted(
        all_players, 
        key=lambda p: (
            -p.points,
            -p.series_wins,           
            -p.kill_death_balance,
            -p.total_farm,
            p.average_win_time, 
        )
    )
    
    context = {
        'players': sorted_players
    }
    
    return render(request, 'roundRobin/leaderboard.html', context)

def playoffs_view(request):
    all_players = Player.objects.all()

    sorted_players = sorted(all_players, key=lambda p: (
            -p.points,
            -p.series_wins,           
            -p.kill_death_balance,
            -p.total_farm,
            p.average_win_time, 
        ))

    if len(sorted_players) < 4:
        return render(request, 'roundRobin/playoffs.html', {
            'not_enough_players': True
    })

    context = {
        'first_place': sorted_players[0],
        'second_place': sorted_players[1],
        'third_place': sorted_players[2],
        'fourth_place': sorted_players[3],
        'not_enough_players': False
    }
    
    return render(request, 'roundRobin/playoffs.html', context)

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
        'STATUS_COMPLETED': STATUS_COMPLETED,
        'STATUS_SCHEDULED': STATUS_SCHEDULED,
    }
    
    return render(request, 'roundRobin/match_list.html', context)

def livestream_view(request):
    return render(request, 'roundRobin/livestream.html')