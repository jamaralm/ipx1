import sys
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.db import transaction

# Importe ambos os modelos do seu app
# (Ajuste 'roundRobin' se o nome do app for outro)
from roundRobin.models import Player, Match, MATCH_FARM_LIMIT

# --- Funções Auxiliares de Impressão (para o teste ficar bonito) ---
def print_header(title, stdout, style):
    stdout.write("\n" + "=" * 50)
    stdout.write(style.HTTP_INFO(f"\n{title.upper()}"))
    stdout.write("\n" + "=" * 50)

def print_player_stats(player, stdout, style):
    # Recarrega o jogador do banco para garantir que os dados estão 100%
    player.refresh_from_db() 
    
    stdout.write(f"\n--- Estatísticas de: {style.SUCCESS(player.username)} ---")
    stdout.write(f"  Partidas: {player.total_matches_played} (W: {player.wins}, L: {player.losses})")
    stdout.write(f"  Winrate: {player.winrate:.2f}%")
    stdout.write(f"  Média Tempo de Vitória: {player.average_win_time}")
    stdout.write(f"  Tipos de Vitória (FB/Farm): {player.first_blood_wins} / {player.farm_wins}")
    stdout.write(f"  Farm Total: {player.total_farm}")
    stdout.write(f"  K/D (em partidas rápidas): {player.total_kills} / {player.total_deaths}")
    stdout.write("-" * 50)

def print_match_info(match, stdout, style):
    stdout.write(f"\n+++ Detalhes da Partida (ID: {match.pk}) +++")
    stdout.write(f"  {match.player1.username} (Farm: {match.player1_farm}) vs {match.player2.username} (Farm: {match.player2_farm})")
    stdout.write(f"  Duração: {match.duration}")
    stdout.write(f"  Vencedor: {style.SUCCESS(match.winner.username)}")
    # get_win_condition_display() pega o texto "bonito" do choices
    stdout.write(f"  Condição: {style.SUCCESS(match.get_win_condition_display())}") 
    stdout.write("-" * 50)


# --- Classe Principal do Comando ---
class Command(BaseCommand):
    help = 'Executa um teste completo nos modelos Player e Match.'

    @transaction.atomic # Garante que todo o teste rode dentro de uma transação
    def handle(self, *args, **options):
        
        # --- 1. SETUP: Limpar e Criar Jogadores ---
        print_header("1. SETUP - Limpando e Criando Jogadores", self.stdout, self.style)
        
        # Limpa dados de testes anteriores
        Player.objects.filter(username__in=["Player_A", "Player_B"]).delete()
        Match.objects.all().delete() # Apaga partidas antigas
        
        pA = Player.objects.create(username="Player_A")
        pB = Player.objects.create(username="Player_B")
        
        self.stdout.write(f"Jogadores {pA.username} e {pB.username} criados.")
        print_player_stats(pA, self.stdout, self.style)
        print_player_stats(pB, self.stdout, self.style)

        # --- 2. TESTE: Partida 1 (Vitória Rápida - Player A) ---
        print_header("2. TESTE - Partida 1: Player A vence (First Blood)", self.stdout, self.style)
        
        match1 = Match.objects.create(
            player1 = pA,
            player2 = pB,
            winner = pA, # pA Venceu
            duration = timedelta(minutes=10), # < 12 min (First Blood)
            player1_farm = 50,
            player2_farm = 30
        )
        
        # Esta é a função mais importante a ser testada
        match1.process_match_results()
        
        self.stdout.write("Resultados processados pela Partida 1.")
        print_match_info(match1, self.stdout, self.style)
        self.stdout.write(self.style.WARNING("VERIFICAR: Player A (Wins=1, FB_Wins=1, Kills=1) | Player B (Losses=1, Deaths=1)"))
        print_player_stats(pA, self.stdout, self.style)
        print_player_stats(pB, self.stdout, self.style)

        # --- 3. TESTE: Partida 2 (Vitória Longa - Player B) ---
        print_header("3. TESTE - Partida 2: Player B vence (Farm)", self.stdout, self.style)
        
        match2 = Match.objects.create(
            player1 = pA,
            player2 = pB,
            winner = pB, # pB Venceu
            duration = timedelta(minutes=15), # >= 12 min (Farm)
            player1_farm = 100,
            player2_farm = 150
        )
        
        match2.process_match_results()
        
        self.stdout.write("Resultados processados pela Partida 2.")
        print_match_info(match2, self.stdout, self.style)
        self.stdout.write(self.style.WARNING("VERIFICAR: Player A (Losses=2, Deaths=1) | Player B (Wins=1, Farm_Wins=1, Kills=0)"))
        print_player_stats(pA, self.stdout, self.style)
        print_player_stats(pB, self.stdout, self.style)
        
        # --- 4. TESTE: Partida 3 (Vitória Longa - Player A) ---
        print_header("4. TESTE - Partida 3: Player A vence (Farm)", self.stdout, self.style)
        
        match3 = Match.objects.create(
            player1 = pB, # Invertendo P1 e P2 para teste
            player2 = pA,
            winner = pA, # pA Venceu
            duration = timedelta(minutes=20), # >= 12 min (Farm)
            player1_farm = 130, # Farm do P1 (pB)
            player2_farm = 200  # Farm do P2 (pA)
        )
        
        match3.process_match_results()
        
        self.stdout.write("Resultados processados pela Partida 3.")
        print_match_info(match3, self.stdout, self.style)
        self.stdout.write(self.style.WARNING("VERIFICAR: Player A (Wins=2, Farm_Wins=1) | Player B (Losses=2, Deaths=0 - derrota longa)"))
        
        self.stdout.write("\n\n--- RESULTADO FINAL ---")
        print_player_stats(pA, self.stdout, self.style)
        print_player_stats(pB, self.stdout, self.style)
        
        self.stdout.write(self.style.SUCCESS("\n--- ✅ Teste Completo Concluído ---"))
        self.stdout.write("Verifique os valores de Winrate, Média de Tempo e Farm Total.")