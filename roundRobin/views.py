from django.shortcuts import render
from .models import Player, Match, TOTAL_ROUNDS, STATUS_COMPLETED, STATUS_LIVE, STATUS_SCHEDULED

def leaderboard_view(request):
    """
    Busca TODAS as partidas (agendadas e completas)
    e as organiza por rodada para exibir no template.
    """
    all_players = Player.objects.all()

    sorted_players = sorted(
        all_players, 
        key=lambda p: (p.series_wins, -p.series_losses, p.kill_death_balance), 
        reverse=True # Ordena pelo primeiro critério (series_wins) do maior para o menor
    )

    context = {
        'players': sorted_players,
        # (Passe as constantes de status para o template, se necessário)
        'STATUS_COMPLETED': STATUS_COMPLETED, 
    }
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
        'STATUS_COMPLETED': STATUS_COMPLETED,
        'STATUS_LIVE': STATUS_LIVE,
        'STATUS_SCHEDULED': STATUS_SCHEDULED,
    }
    
    return render(request, 'roundRobin/match_list.html', context)

def livestream_view(request):
    return render(request, 'roundRobin/livestream.html')