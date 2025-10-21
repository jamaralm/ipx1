from django.db import models
from django.db.models import F
from datetime import timedelta
from django.db import transaction # Necessário para o @transaction.atomic

# Define o tempo limite que diferencia uma vitória "rápida" de uma "longa"
MATCH_FARM_LIMIT = timedelta(minutes=12)
TOTAL_ROUNDS = 10
ROUND_CHOICES = [ (i, f"Rodada {i}") for i in range(1, TOTAL_ROUNDS + 1) ]

class Player(models.Model):

    # --- CAMPOS ARMAZENADOS NO BANCO DE DADOS ---

    # Campo de texto para o nome, que não pode ser nulo/vazio e deve ser único
    username = models.CharField(
        verbose_name = "Nome de Usuario",
        max_length=50, 
        null=False,
        blank=False,
        unique=True # Garante que não existam dois jogadores com o mesmo nome
        )

    # Contadores de vitórias e derrotas
    wins = models.IntegerField(default=0) # Total de vitórias
    losses = models.IntegerField(default=0) # Total de derrotas
    
    # Contadores para tipos específicos de vitória
    first_blood_wins = models.IntegerField(default=0) # Vitórias rápidas (antes do limite)
    farm_wins = models.IntegerField(default=0) # Vitórias longas (depois do limite)

    # Contadores de estatísticas gerais
    total_farm = models.IntegerField(default=0) # Total de farm (em vitórias e derrotas)
    total_kills = models.IntegerField(default=0) # Total de abates (só em vitórias rápidas)
    total_deaths = models.IntegerField(default=0) # Total de mortes (só em derrotas rápidas)

    # Armazena a soma total do tempo de todas as partidas vencidas
    total_win_time = models.DurationField(
        default=timedelta(0),
        help_text="Tempo total de vitória acumulado."
    )

    # --- MÉTODOS E PROPRIEDADES (CÁLCULOS) ---

    def __str__(self):
        # Define como o objeto Player será exibido (ex: "Player1 (75.0%)")
        return f"{self.username} ({self.winrate:.1f}%)"

    @property
    def total_matches_played(self):
        # '@property' faz isso funcionar como um campo (ex: player.total_matches_played)
        # mas é um cálculo feito em Python, não armazenado no banco.
        return self.wins + self.losses

    @property
    def average_win_time(self):
        # Calcula o tempo médio das vitórias
        if self.wins == 0:
            return timedelta(0) # Evita erro de divisão por zero

        # Divide o tempo total de vitórias pelo número de vitórias
        return self.total_win_time / self.wins

    @property
    def winrate(self):
        # Calcula a taxa de vitórias (em porcentagem, ex: 80.0)
        total = self.total_matches_played
        
        if total == 0:
            return 0.0 # Evita erro de divisão por zero
            
        rate = (self.wins / total) * 100
        return rate
    
    @property
    def kill_death_balance(self):
        # Calcula o saldo de Kills - Deaths
        return self.total_kills - self.total_deaths

    @property
    def average_win_time_display(self):
        """
        Retorna o tempo médio de vitória formatado como MM:SS.
        """
        # Pega o timedelta calculado pela outra propriedade
        duration = self.average_win_time
        
        if not duration:
            return "00:00"

        # Converte a duração total para segundos
        total_seconds = int(duration.total_seconds())
        
        # Calcula os minutos e os segundos restantes
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        
        # Formata como "MM:SS" (ex: 05:03)
        return f"{minutes:02}:{seconds:02}"

    # Garante que todas as operações de banco de dados abaixo
    # aconteçam juntas. Se uma falhar, todas são revertidas.
    @transaction.atomic 
    def add_match_result(self, match_duration: timedelta, did_win: bool, farm: int):
        # Este método atualiza as estatísticas do jogador após uma partida.
        # Ele usa F() para fazer as contas no banco de dados, evitando
        # problemas de concorrência (race conditions).
        
        # Cria um dicionário para guardar todas as atualizações
        update_fields = {}

        # --- LÓGICA DE VITÓRIA ---
        if did_win:
            update_fields['wins'] = F('wins') + 1
            update_fields['total_win_time'] = F('total_win_time') + match_duration

            # Verifica se foi uma vitória "longa" (farm) ou "rápida" (first blood)
            if match_duration >= MATCH_FARM_LIMIT:
                update_fields['farm_wins'] = F('farm_wins') + 1
            else: # Vitória rápida
                update_fields['first_blood_wins'] = F('first_blood_wins') + 1
                update_fields['total_kills'] = F('total_kills') + 1 # Só conta kill em vitória rápida

            update_fields['total_farm'] = F('total_farm') + farm
            
        # --- LÓGICA DE DERROTA ---
        else:
            update_fields['losses'] = F('losses') + 1
            update_fields['total_farm'] = F('total_farm') + farm
            
            # Se a derrota foi "rápida", conta uma morte
            if match_duration < MATCH_FARM_LIMIT:
                update_fields['total_deaths'] = F('total_deaths') + 1

        # Aplica todas as atualizações no banco de dados de uma vez só
        Player.objects.filter(pk=self.pk).update(**update_fields)

        # Atualiza o objeto 'self' (em Python) com os novos dados do banco
        self.refresh_from_db()

class Match(models.Model):
    
    # --- NOVOS: Estados da Partida ---
    STATUS_SCHEDULED = 'scheduled'
    STATUS_LIVE = 'live'
    STATUS_COMPLETED = 'completed'
    
    STATUS_CHOICES = [
        (STATUS_SCHEDULED, 'Agendada'),
        (STATUS_LIVE, 'Ao Vivo'),
        (STATUS_COMPLETED, 'Concluída'),
    ]

    # --- NOVO: Campo de Status ---
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_SCHEDULED, # Toda nova partida começa como "Agendada"
        db_index=True # Facilita filtrar por status
    )

    # --- Campos de Relacionamento ---
    player1 = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="matches_as_player1")
    player2 = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="matches_as_player2")
    
    # --- Campos de Agendamento (Antes em ScheduledMatch) ---
    round_number = models.IntegerField(choices=ROUND_CHOICES, default=1, db_index=True)
    scheduled_time = models.DateTimeField(verbose_name="Horário Agendado", null=True, blank=True)
    
    # --- Campos de Resultado (Antes em Match, agora unificados) ---
    winner = models.ForeignKey(
        Player, 
        on_delete=models.SET_NULL, 
        related_name="won_matches",
        null=True, # Partidas agendadas não têm vencedor
        blank=True
    )
    
    duration = models.DurationField(
        verbose_name="Duração da Partida",
        null=True, # Partidas agendadas não têm duração
        blank=True
    )
    
    WIN_CONDITION_FIRST_BLOOD = 'first_blood'
    WIN_CONDITION_FARM = 'farm'
    WIN_CONDITION_CHOICES = [
        (WIN_CONDITION_FIRST_BLOOD, "First Blood"),
        (WIN_CONDITION_FARM, "Farm"),
    ]
    win_condition = models.CharField(
        max_length=20, 
        choices=WIN_CONDITION_CHOICES,
        null=True, # Partidas agendadas não têm condição de vitória
        blank=True
    )

    player1_farm = models.IntegerField(default=0)
    player2_farm = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['round_number', 'scheduled_time']
        verbose_name = "Partida"
        verbose_name_plural = "Partidas"

    def __str__(self):
        if self.status == self.STATUS_COMPLETED and self.winner:
            return f"[R{self.round_number}] {self.winner.username} venceu ({self.get_win_condition_display()})"
        elif self.status == self.STATUS_SCHEDULED:
            return f"[R{self.round_number}] {self.player1.username} vs {self.player2.username} (Agendada)"
        else:
            return f"[R{self.round_number}] {self.player1.username} vs {self.player2.username} ({self.get_status_display()})"
    

    # --- LÓGICA DE PROCESSAMENTO (A mesma de antes) ---
    # (Esta função SÓ deve ser chamada quando a partida é concluída)
    @transaction.atomic
    def process_match_results(self):
        """
        Atualiza as estatísticas dos jogadores e salva a win_condition.
        SÓ DEVE RODAR QUANDO UM VENCEDOR FOR DEFINIDO.
        """
        if not self.winner:
            # Segurança: não faz nada se não houver vencedor
            return

        # 1. Determina Perdedor e Farms
        loser = self.player2 if self.winner == self.player1 else self.player1
        winner_farm = self.player1_farm if self.winner == self.player1 else self.player2_farm
        loser_farm = self.player2_farm if self.winner == self.player1 else self.player1_farm

        # 2. Define a Win Condition
        if self.duration >= MATCH_FARM_LIMIT:
            self.win_condition = self.WIN_CONDITION_FARM
        else:
            self.win_condition = self.WIN_CONDITION_FIRST_BLOOD

        # 3. Atualiza Estatísticas do Vencedor
        self.winner.add_match_result(
            match_duration=self.duration,
            did_win=True,
            farm=winner_farm
        )
        
        # 4. Atualiza Estatísticas do Perdedor
        loser.add_match_result(
            match_duration=self.duration,
            did_win=False,
            farm=loser_farm
        )
        
        # 5. Salva a win_condition na própria partida
        # (O status já foi salvo pelo admin)
        self.save(update_fields=['win_condition'])