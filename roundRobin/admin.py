from django.contrib import admin, messages
from django.db import transaction

from .models import Player, Match, Game 
from .models import MATCH_FARM_LIMIT, WIN_CONDITION_FARM_80, WIN_CONDITION_TIME_FARM, WIN_CONDITION_FIRST_BLOOD
from .models import STATUS_COMPLETED

class MissingWinConditionError(Exception):
    """Raised when a Game is missing its win_condition."""
    pass
    
# --- ADMIN DO PLAYER (O SEU ORIGINAL, SEM 'is_approved') ---
@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('username', 'wins', 'losses', 'winrate')
    search_fields = ('username',)
    # (Removido 'is_approved' do list_display e list_filter)


# --- O "EDITOR DE JOGOS" (MD3) ---
class GameInline(admin.TabularInline):
    model = Game
    fields = ('game_number', 'winner', 'win_condition', 'duration', 'player1_farm', 'player2_farm')
    readonly_fields = ('is_processed',)
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
        'is_wo',
    )
    list_filter = ('status', 'round_number', 'scheduled_time', 'is_wo')
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
                    'fields': ('series_winner', 'is_wo') 
                })
            )

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status == STATUS_COMPLETED and not obj.is_wo:
            # Concluída normalmente (com jogos), trava tudo.
            return ('player1', 'player2', 'round_number', 'scheduled_time', 'series_winner', 'is_wo')
        
        if obj and obj.status == STATUS_COMPLETED and obj.is_wo:
            # Concluída por WO, trava agendamento mas permite mudar vencedor se necessário
            return ('player1', 'player2', 'round_number', 'scheduled_time')
            
        # Se estiver Agendada, permite edição de tudo
        # 'series_winner' pode ser definido para WO, ou será calculado/ignorado
        return ()


    # --- A LÓGICA DE PROCESSAMENTO (MD3) ---
   @transaction.atomic
    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)

        obj: Match = form.instance 
        player1 = obj.player1
        player2 = obj.player2
        
        # --- 1. REVERTER ESTATÍSTICAS ---
        # Sempre reverta primeiro, para o caso de uma partida
        # normal estar sendo convertida para W.O.
        games_to_revert = obj.games.filter(is_processed=True, winner__isnull=False)

        for game in games_to_revert:
            game: Game 
            loser = game.match.player2 if game.winner == game.match.player1 else game.match.player1
            winner_farm = game.player1_farm if game.winner == game.match.player1 else game.player2_farm
            loser_farm = game.player2_farm if game.winner == game.match.player1 else game.player1_farm

            game.winner.remove_match_result(
                did_win=True, farm=winner_farm,
                win_condition=game.win_condition, 
                match_duration=game.duration
            )
            loser.remove_match_result(
                did_win=False, farm=loser_farm,
                win_condition=game.win_condition, 
                match_duration=game.duration
            )

        obj.games.update(is_processed=False)
        
        # --- 2. LÓGICA DE W.O. ---
        if obj.is_wo:
            # Se for W.O., verifique se o admin selecionou um vencedor
            if not obj.series_winner:
                self.message_user(request, "ERRO: Se 'Vitória por W.O.' está marcada, você DEVE selecionar um 'Vencedor da Série'.", messages.ERROR)
                raise transaction.TransactionManagementError("W.O. must have a series_winner.")
            
            # Garanta que o status seja 'Concluída'
            obj.status = STATUS_COMPLETED
            obj.save()
            
            self.message_user(request, f"Partida salva como W.O. para {obj.series_winner.username}. Apenas 3 pontos de série foram dados (sem K/D/Farm).", messages.SUCCESS)
            
            # Pula todo o processamento de jogos
            return

        # --- 3. LÓGICA DE PARTIDA NORMAL (SÓ RODA SE NÃO FOR W.O.) ---
        
        # Reseta o vencedor da série (será recalculado) se não for WO
        obj.series_winner = None
        
        if obj.status != STATUS_COMPLETED:
            obj.save()
            self.message_user(request, "Estatísticas da série foram revertidas (status não 'Concluída').", messages.WARNING)
            return

        all_completed_games = obj.games.filter(winner__isnull=False)

        p1_series_wins = 0
        p2_series_wins = 0

        for game in all_completed_games:
            game: Game

            loser = player2 if game.winner == player1 else player1
            winner_farm = game.player1_farm if game.winner == player1 else game.player2_farm
            loser_farm = game.player2_farm if game.winner == player1 else game.player1_farm
            
            if game.win_condition == None:
                self.message_user(request, f"ERRO: A 'Condição de Vitória' do Jogo {game.game_number} não foi preenchida.", messages.ERROR)
                raise MissingWinConditionError(f"Condição de Vitória obrigatória para o Jogo {game.game_number}.")
            
            game.winner.add_match_result(
                did_win=True, farm=winner_farm,
                win_condition=game.win_condition, 
                match_duration=game.duration
            )

            loser.add_match_result(
                did_win=False, farm=loser_farm,
                win_condition=game.win_condition, 
                match_duration=game.duration
            )
            
            if game.winner == player1:
                p1_series_wins += 1
            else:
                p2_series_wins += 1

            game.is_processed = True
            game.save()

        if p1_series_wins >= 2:
            obj.series_winner = player1
        elif p2_series_wins >= 2:
            obj.series_winner = player2

        obj.save()
        
        self.message_user(request, 
                          "Estatísticas da série (partida normal) foram recalculadas e salvas com sucesso.", 
                          messages.SUCCESS)