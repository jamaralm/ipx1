import sys
from datetime import timedelta
from django.core.management.base import BaseCommand
# Importe o modelo do seu app (confirme que 'roundRobin' é o nome do app)
from roundRobin.models import Player  

class Command(BaseCommand):
    help = 'Executa um teste de criação e atualização no modelo Player (Versão 2).'

    def handle(self, *args, **options):
        
        self.stdout.write("Iniciando limpeza de jogadores de teste...")
        Player.objects.filter(username__in=["Tester_FB", "Tester_Farm"]).delete()
        
        # ---
        # 1. SETUP: Criar jogador e verificar estado inicial
        # ---
        p = Player.objects.create(username="Tester_FB")
        
        self.stdout.write(f"--- 🚀 Jogador Criado ---")
        self.stdout.write(f"Jogador: {p.username}")
        self.stdout.write(f"Partidas: {p.total_matches_played} (W: {p.wins}, L: {p.loses})")
        self.stdout.write(f"Winrate: {p.winrate:.2f}%") # Testando o fix do ZeroDivisionError
        self.stdout.write(f"Média de Vitória: {p.average_win_time}")
        self.stdout.write(f"Farm: {p.total_farm}, Kills: {p.total_kills}, Deaths: {p.total_deaths}")
        self.stdout.write(f"Tipos de Vitória (FB: {p.first_blood_wins}, Farm: {p.farm_wins})")
        self.stdout.write("-" * 30)

        # ---
        # 2. Partida 1: Vitória Rápida (First Blood Win, < 12 min)
        # ---
        self.stdout.write(self.style.HTTP_INFO("Simulando Partida 1 (Vitória Rápida, 10 min, 50 farm)"))
        p.add_match_result(match_duration=timedelta(minutes=10), did_win=True, farm=50)

        self.stdout.write(f"Partidas: {p.total_matches_played} (W: {p.wins}, L: {p.loses})")
        self.stdout.write(f"Winrate: {p.winrate:.2f}%")
        self.stdout.write(f"Média de Vitória: {p.average_win_time}")
        self.stdout.write(f"Farm: {p.total_farm}, Kills: {p.total_kills}, Deaths: {p.total_deaths}")
        self.stdout.write(self.style.SUCCESS(f"Tipos de Vitória (FB: {p.first_blood_wins}, Farm: {p.farm_wins}) <-- FB deve ser 1, Kills 1"))
        self.stdout.write("-" * 30)

        # ---
        # 3. Partida 2: Vitória Longa (Farm Win, >= 12 min)
        # ---
        self.stdout.write(self.style.HTTP_INFO("Simulando Partida 2 (Vitória Longa, 15 min, 120 farm)"))
        p.add_match_result(match_duration=timedelta(minutes=15), did_win=True, farm=120)

        self.stdout.write(f"Partidas: {p.total_matches_played} (W: {p.wins}, L: {p.loses})")
        self.stdout.write(f"Winrate: {p.winrate:.2f}%")
        self.stdout.write(f"Média de Vitória: {p.average_win_time} (Esperado: 12m 30s)")
        self.stdout.write(f"Farm: {p.total_farm} (Esperado: 170), Kills: {p.total_kills}, Deaths: {p.total_deaths}")
        self.stdout.write(self.style.SUCCESS(f"Tipos de Vitória (FB: {p.first_blood_wins}, Farm: {p.farm_wins}) <-- Farm deve ser 1, Kills não muda (1)"))
        self.stdout.write("-" * 30)
        
        # ---
        # 4. Partida 3: Derrota Rápida ( < 12 min)
        # ---
        self.stdout.write(self.style.HTTP_INFO("Simulando Partida 3 (Derrota Rápida, 5 min, 30 farm)"))
        p.add_match_result(match_duration=timedelta(minutes=5), did_win=False, farm=30)
        
        self.stdout.write(f"Partidas: {p.total_matches_played} (W: {p.wins}, L: {p.loses})")
        self.stdout.write(f"Winrate: {p.winrate:.2f}% (Esperado: 66.67%)")
        self.stdout.write(f"Média de Vitória: {p.average_win_time} (Não deve mudar: 12m 30s)")
        self.stdout.write(f"Farm: {p.total_farm} (Esperado: 200), Kills: {p.total_kills}, Deaths: {p.total_deaths}")
        self.stdout.write(self.style.WARNING(f"Tipos de Vitória (FB: {p.first_blood_wins}, Farm: {p.farm_wins}) <-- Deaths deve ser 1"))
        self.stdout.write("-" * 30)

        # ---
        # 5. Partida 4: Derrota Longa ( >= 12 min)
        # ---
        self.stdout.write(self.style.HTTP_INFO("Simulando Partida 4 (Derrota Longa, 20 min, 150 farm)"))
        p.add_match_result(match_duration=timedelta(minutes=20), did_win=False, farm=150)
        
        self.stdout.write(f"Partidas: {p.total_matches_played} (W: {p.wins}, L: {p.loses})")
        self.stdout.write(f"Winrate: {p.winrate:.2f}% (Esperado: 50.00%)")
        self.stdout.write(f"Média de Vitória: {p.average_win_time} (Não deve mudar: 12m 30s)")
        self.stdout.write(f"Farm: {p.total_farm} (Esperado: 350), Kills: {p.total_kills}, Deaths: {p.total_deaths}")
        self.stdout.write(self.style.WARNING(f"Tipos de Vitória (FB: {p.first_blood_wins}, Farm: {p.farm_wins}) <-- Deaths não deve mudar (1)"))
        self.stdout.write("-" * 30)


        self.stdout.write(self.style.SUCCESS("\n--- ✅ Teste Concluído ---"))