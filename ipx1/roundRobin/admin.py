from django.contrib import admin, messages
from .models import Player, Match

# 1. Configuração do Admin para o Modelo 'Player'
@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    """
    Configuração do Admin para Jogadores.
    As estatísticas são "somente leitura" (readonly) porque são
    calculadas automaticamente a partir das partidas.
    """
    
    # --- O que mostrar na lista principal ---
    list_display = (
        'username', 
        'winrate', 
        'wins', 
        'losses', 
        'total_matches_played', 
        'kill_death_balance',
        'average_win_time_display' # Usando a propriedade formatada
    )
    
    # --- Permitir busca pelo nome ---
    search_fields = ('username',)
    
    # --- Campos que aparecem no formulário de edição/criação ---
    # Campos "readonly" não podem ser editados manualmente, protegendo os dados
    readonly_fields = (
        'wins', 'losses', 'first_blood_wins', 'farm_wins', 
        'total_farm', 'total_kills', 'total_deaths', 'total_win_time',
        'total_matches_played', 'average_win_time_display', 
        'winrate', 'kill_death_balance'
    )
    
    # --- Organiza os campos no painel de edição ---
    fieldsets = (
        (None, {
            'fields': ('username',) # Único campo editável
        }),
        ('Estatísticas de Jogo (Calculadas)', {
            'classes': ('collapse',), # Começa "fechado"
            'fields': (
                ('wins', 'losses', 'total_matches_played'),
                ('winrate', 'kill_death_balance'),
                ('first_blood_wins', 'farm_wins'),
                ('total_farm', 'total_kills', 'total_deaths'),
                ('total_win_time', 'average_win_time_display'),
            )
        }),
    )

# 2. Configuração do Admin para o Modelo 'Match'
@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = (
        '__str__',
        'status', # NOVO
        'round_number',
        'winner',
        'win_condition',
        'scheduled_time',
    )
    list_filter = ('status', 'round_number', 'scheduled_time')
    autocomplete_fields = ('player1', 'player2', 'winner')
    
    # Define quais campos aparecem no admin dependendo do status
    def get_fieldsets(self, request, obj=None):
        if obj is None: # Criando uma nova partida
            return (
                ('Agendamento', {
                    'fields': ('round_number', 'player1', 'player2', 'scheduled_time')
                }),
            )
        elif obj.status == Match.STATUS_SCHEDULED or obj.status == Match.STATUS_LIVE:
            return (
                ('Partida', {
                    'fields': ('status', ('player1', 'player2'), 'round_number', 'scheduled_time')
                }),
                ('Resultado (Preencha para Concluir)', {
                    'fields': ('winner', 'duration', 'player1_farm', 'player2_farm')
                })
            )
        else: # Partida Concluída
            return (
                ('Partida (Concluída)', {
                    'fields': ('status', ('player1', 'player2'), 'round_number')
                }),
                ('Resultado (Processado)', {
                    'fields': ('winner', 'duration', 'win_condition', 'player1_farm', 'player2_farm')
                })
            )

    # Torna os campos de resultado "somente leitura" após a conclusão
    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status == Match.STATUS_COMPLETED:
            # Trava tudo exceto o status (caso precise reverter)
            return ('player1', 'player2', 'round_number', 'scheduled_time', 
                    'winner', 'duration', 'win_condition', 'player1_farm', 'player2_farm')
        return ('win_condition',) # win_condition é sempre automático

    # --- ESTA É A MÁGICA ---
    def save_model(self, request, obj: Match, form, change):
        """
        Chamado quando o admin clica em "Salvar".
        """
        # Salva o objeto primeiro (especialmente o 'status' e 'winner' que o admin mudou)
        super().save_model(request, obj, form, change)
        
        # 'change' é True se for uma edição
        # Verificamos se a partida foi movida para "Concluída" E se já tem um vencedor
        # E se a 'win_condition' ainda não foi definida (para não rodar duas vezes)
        if (change and 
            obj.status == Match.STATUS_COMPLETED and 
            obj.winner and 
            not obj.win_condition):
            
            try:
                # Chama sua função para atualizar as estatísticas do Player
                obj.process_match_results()
                
                self.message_user(request, 
                                  "Partida Concluída e estatísticas dos jogadores atualizadas.", 
                                  messages.SUCCESS)
            except Exception as e:
                self.message_user(request, 
                                  f"ERRO ao processar resultados: {e}", 
                                  messages.ERROR)