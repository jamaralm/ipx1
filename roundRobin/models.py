from django.db import models
from django.db.models import F
from datetime import timedelta
from django.db import transaction # Necessário para o @transaction.atomic

# Define o tempo limite que diferencia uma vitória "rápida" de uma "longa"
MATCH_FARM_LIMIT = timedelta(minutes=12)
TOTAL_ROUNDS = 10
ROUND_CHOICES = [ (i, f"Rodada {i}") for i in range(1, TOTAL_ROUNDS + 1) ]

MATCH_FARM_LIMIT = timedelta(minutes=12) # Coloque seu limite aqui

WIN_CONDITION_FIRST_BLOOD = 'first_blood'
WIN_CONDITION_FARM = 'farm'
WIN_CONDITION_CHOICES = [
    (WIN_CONDITION_FIRST_BLOOD, "First Blood"),
    (WIN_CONDITION_FARM, "Farm"),
]

class Player(models.Model):

    # --- CAMPOS ARMAZENADOS NO BANCO DE DADOS ---
    username = models.CharField(
        verbose_name = "Nome de Usuario",
        max_length=50, 
        null=False,
        blank=False,
        unique=True 
        )

    wins = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    first_blood_wins = models.IntegerField(default=0)
    farm_wins = models.IntegerField(default=0)
    total_farm = models.IntegerField(default=0)
    total_kills = models.IntegerField(default=0)
    total_deaths = models.IntegerField(default=0)
    total_win_time = models.DurationField(
        default=timedelta(0),
        help_text="Tempo total de vitória acumulado."
    )

    # --- MÉTODOS E PROPRIEDADES (CÁLCULOS) ---
    def __str__(self):
        # (Este é seu __str__ original, que está correto)
        return f"{self.username} ({self.winrate:.1f}%)"

    @property
    def total_matches_played(self):
        return self.wins + self.losses

    @property
    def average_win_time(self):
        if self.wins == 0:
            return timedelta(0) 
        return self.total_win_time / self.wins

    @property
    def winrate(self):
        total = self.total_matches_played
        if total == 0:
            return 0.0
        rate = (self.wins / total) * 100
        return rate
    
    @property
    def kill_death_balance(self):
        return self.total_kills - self.total_deaths

    @property
    def average_win_time_display(self):
        duration = self.average_win_time
        if not duration:
            return "00:00"
        total_seconds = int(duration.total_seconds())
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes:02}:{seconds:02}"

    @transaction.atomic 
    def add_match_result(self, match_duration: timedelta, did_win: bool, farm: int):
        update_fields = {}
        if did_win:
            update_fields['wins'] = F('wins') + 1
            update_fields['total_win_time'] = F('total_win_time') + match_duration
            if match_duration >= MATCH_FARM_LIMIT:
                update_fields['farm_wins'] = F('farm_wins') + 1
            else: 
                update_fields['first_blood_wins'] = F('first_blood_wins') + 1
                update_fields['total_kills'] = F('total_kills') + 1
            update_fields['total_farm'] = F('total_farm') + farm
        else:
            update_fields['losses'] = F('losses') + 1
            update_fields['total_farm'] = F('total_farm') + farm
            if match_duration < MATCH_FARM_LIMIT:
                update_fields['total_deaths'] = F('total_deaths') + 1
        Player.objects.filter(pk=self.pk).update(**update_fields)
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
    series_winner = models.ForeignKey(
        Player, 
        on_delete=models.SET_NULL, 
        related_name="won_matches", # 'won_matches' agora significa séries ganhas
        null=True, 
        blank=True,
        verbose_name="Vencedor da Série (MD3)"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['round_number', 'scheduled_time']
        verbose_name = "Confronto (MD3)" # Mudei o nome para ficar claro
        verbose_name_plural = "Confrontos (MD3)"

    def __str__(self):
        if self.status == self.STATUS_COMPLETED and self.series_winner:
            return f"[R{self.round_number}] {self.series_winner.username} venceu"
        elif self.status == self.STATUS_SCHEDULED:
            return f"[R{self.round_number}] {self.player1.username} vs {self.player2.username} (Agendada)"
        else:
            return f"[R{self.round_number}] {self.player1.username} vs {self.player2.username} ({self.get_status_display()})"

class Game(models.Model):
    """
    Representa UMA Partida (Jogo) dentro de um Confronto (Match) MD3.
    """
    
    # Link para o "Confronto" (MD3) ao qual este jogo pertence
    match = models.ForeignKey(
        Match, 
        on_delete=models.CASCADE, 
        related_name="games", # Permite fazer match.games.all()
        null = True,
        blank = True
    )
    
    # Número do jogo (1, 2, ou 3)
    game_number = models.IntegerField(
        verbose_name="Nº do Jogo",
        choices=[(1, 'Jogo 1'), (2, 'Jogo 2'), (3, 'Jogo 3')]
    ) 

    # Quem venceu ESTE jogo
    winner = models.ForeignKey(
        Player, 
        on_delete=models.SET_NULL, 
        null=True, blank=True
    )
    
    # Dados deste jogo específico
    duration = models.DurationField(
        verbose_name="Duração", 
        null=True, # Permite que o campo seja NULO no banco
        blank=True # Permite que o campo seja VAZIO no formulário
    )
    player1_farm = models.IntegerField(default=0)
    player2_farm = models.IntegerField(default=0)

    # Condição de vitória (calculado)
    win_condition = models.CharField(
        max_length=20, 
        choices=WIN_CONDITION_CHOICES, # Reutiliza as choices do Match
        null=True, blank=True,
        editable=False # Será sempre calculado
    )

    # Nosso "lacre" de segurança para não processar duas vezes
    is_processed = models.BooleanField(default=False, editable=False)
    
    class Meta:
        unique_together = ('match', 'game_number')
        ordering = ['game_number']
        verbose_name = "Partida (Jogo)"
        verbose_name_plural = "Partidas (Jogos)"

    def __str__(self):
        return f"{self.match} - Jogo {self.game_number}"