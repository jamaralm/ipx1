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
    """
    Configuração do Admin para Partidas.
    Contém a lógica para processar os resultados automaticamente
    e travar a partida após ser processada.
    """

    # --- O que mostrar na lista principal ---
    list_display = (
        '__str__', # Mostra o "Player 1 vs Player 2"
        'winner',
        'win_condition',
        'duration',
        'created_at',
    )
    
    # --- Filtros na barra lateral ---
    list_filter = ('win_condition', 'created_at')
    
    # --- Permitir busca pelos nomes dos jogadores ---
    search_fields = ('player1__username', 'player2__username', 'winner__username')
    
    # --- Melhora a seleção de Jogadores (usa busca em vez de dropdown) ---
    autocomplete_fields = ('player1', 'player2', 'winner')

    # --- Organiza os campos no painel de edição ---
    fieldsets = (
        ('Partida', {
            'fields': ('player1', 'player2')
        }),
        ('Resultado (Defina para processar)', {
            'fields': ('winner', 'duration', 'player1_farm', 'player2_farm')
        }),
        ('Metadados (Automático)', {
            'fields': ('win_condition', 'created_at')
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        """
        Torna a partida inteira "somente leitura" se já foi processada.
        """
        if obj and obj.winner:
            # Se o objeto existe e tem um vencedor, trava todos os campos
            # Isso previne que alguém mude o vencedor e corrompa as estatísticas
            return [field.name for field in self.model._meta.fields]
        
        # Se for uma nova partida, apenas os campos automáticos são readonly
        return ['created_at', 'win_condition']

    def save_model(self, request, obj: Match, form, change):
        """
        Sobrescreve o método de salvar.
        Executa 'process_match_results' ao salvar uma nova partida com vencedor.
        """
        
        # Salva o objeto Match primeiro
        super().save_model(request, obj, form, change)
        
        # 'change' é False se for um objeto NOVO
        # Verificamos se tem um vencedor E se ainda não foi processado (win_condition=None)
        if obj.winner and not obj.win_condition:
            try:
                # Esta é a sua função mágica!
                obj.process_match_results()
                
                # Envia uma mensagem de sucesso para o admin
                self.message_user(request, 
                                  "Partida processada com sucesso. As estatísticas dos jogadores foram atualizadas.", 
                                  messages.SUCCESS)
            except Exception as e:
                # Em caso de erro
                self.message_user(request, 
                                  f"ERRO ao processar resultados: {e}. As estatísticas podem estar inconsistentes.", 
                                  messages.ERROR)