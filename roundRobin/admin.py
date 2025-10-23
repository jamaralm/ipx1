from django.contrib import admin, messages
from django.db import transaction

# --- IMPORTS CORRIGIDOS ---
from .models import Player, Match, Game 
from .models import MATCH_FARM_LIMIT, WIN_CONDITION_FARM, WIN_CONDITION_FIRST_BLOOD

# --- ADMIN DO PLAYER (O SEU ORIGINAL, SEM 'is_approved') ---
@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('username', 'wins', 'losses', 'winrate')
    search_fields = ('username',)
    # (Removido 'is_approved' do list_display e list_filter)


# --- O "EDITOR DE JOGOS" (MD3) ---
class GameInline(admin.TabularInline):
    model = Game
    fields = ('game_number', 'winner', 'duration', 'player1_farm', 'player2_farm')
    readonly_fields = ('win_condition', 'is_processed')
    extra = 3
    max_num = 3
    autocomplete_fields = ('winner',)

    def get_formset(self, request, obj=None, **kwargs):
        if obj:
            # Passa o 'obj' (o Match) para o formfield_callback
            kwargs['formfield_callback'] = lambda field: self.formfield_for_dbfield(field, request, obj=obj)
        return super().get_formset(request, obj, **kwargs)

    def formfield_for_dbfield(self, db_field, request, obj=None, **kwargs):
        """
        Altera o rótulo (label) dos campos de farm para 
        mostrar o nome do jogador correto.
        """
        field = super().formfield_for_dbfield(db_field, request, **kwargs)
        if obj: # obj é o 'Match'
            # --- CORREÇÃO IMPORTANTE AQUI ---
            # (Usando player.username, não player.user.username)
            if db_field.name == 'player1_farm':
                field.label = f"Farm ({obj.player1.username})"
            if db_field.name == 'player2_farm':
                field.label = f"Farm ({obj.player2.username})"
        return field


# --- O "ADMIN DO CONFRONTO" (MD3) ---
@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    
    # (Corrigido para usar 'series_winner' e remover 'win_condition')
    list_display = (
        '__str__',
        'status',
        'round_number',
        'series_winner', 
        'scheduled_time',
    )
    list_filter = ('status', 'round_number', 'scheduled_time')
    inlines = [GameInline]
    
    # (Corrigido para usar 'series_winner')
    autocomplete_fields = ('player1', 'player2', 'series_winner')
    
    # --- LÓGICA DE EXIBIÇÃO ---
    def get_fieldsets(self, request, obj=None):
        if obj is None: # Criando
            return (
                ('Agendamento', {
                    'fields': ('round_number', 'player1', 'player2', 'scheduled_time')
                }),
            )
        else: # Editando
             return (
                ('Confronto', {
                    'fields': ('status', ('player1', 'player2'), 'round_number')
                }),
                ('Resultado da Série (MD3)', {
                    'fields': ('series_winner',) 
                })
            )

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status == Match.STATUS_COMPLETED:
            return ('player1', 'player2', 'round_number', 'scheduled_time', 'series_winner')
        
        # O Vencedor da Série é sempre somente leitura, pois é calculado
        return ('series_winner',)


    # --- A LÓGICA DE PROCESSAMENTO (MD3) ---
    @transaction.atomic
    def save_related(self, request, form, formsets, change):
        """
        Chamado quando o admin clica em "Salvar" e os 'inlines' (Games) 
        também precisam ser salvos.
        """
        # Salva o Match e os Games primeiro
        super().save_related(request, form, formsets, change)

        obj: Match = form.instance 
        
        if obj.status != Match.STATUS_COMPLETED:
            return 

        # Filtra jogos que têm vencedor E que ainda não foram processados
        games_to_process = obj.games.filter(winner__isnull=False, is_processed=False)

        if not games_to_process.exists() and not change:
             # Se não há novos jogos para processar e é uma nova criação, sai
            return

        # --- AQUI É ONDE RECALCULAMOS TUDO ---
        # 1. Zera as estatísticas ANTES de reprocessar
        # (Para evitar duplicatas se o admin salvar de novo)
        
        # (Esta é uma lógica complexa de "reversão". Por enquanto,
        # vamos confiar no 'is_processed=False' para evitar reprocessamento)
        
        # Loop pelos jogos *novos*
        for game in games_to_process:
            game: Game 
            
            loser = game.match.player2 if game.winner == game.match.player1 else game.match.player1
            winner_farm = game.player1_farm if game.winner == game.match.player1 else game.player2_farm
            loser_farm = game.player2_farm if game.winner == game.match.player1 else game.player1_farm

            # Define a Win Condition do JOGO
            if game.duration >= MATCH_FARM_LIMIT:
                game.win_condition = WIN_CONDITION_FARM
            else:
                game.win_condition = WIN_CONDITION_FIRST_BLOOD

            # ATUALIZA ESTATÍSTICAS DO VENCEDOR
            game.winner.add_match_result(
                match_duration=game.duration,
                did_win=True,
                farm=winner_farm
            )
            
            # ATUALIZA ESTATÍSTICAS DO PERDEDOR
            loser.add_match_result(
                match_duration=game.duration,
                did_win=False,
                farm=loser_farm
            )
            
            game.is_processed = True
            game.save() 
            
        # --- FIM DO LOOP DE GAMES ---
            
        # Recalcula o VENCEDOR DA SÉRIE (MD3)
        p1_wins = obj.games.filter(winner=obj.player1).count()
        p2_wins = obj.games.filter(winner=obj.player2).count()

        if p1_wins >= 2:
            obj.series_winner = obj.player1
        elif p2_wins >= 2:
            obj.series_winner = obj.player2
        else:
            obj.series_winner = None 

        obj.save() 
        
        if games_to_process.exists():
            self.message_user(request, 
                              "Resultados dos jogos processados e estatísticas atualizadas.", 
                              messages.SUCCESS)