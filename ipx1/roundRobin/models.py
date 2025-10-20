from django.db import models, transaction
from django.db.models import F
from datetime import timedelta

MATCH_FARM_LIMIT = timedelta(minutes=12)

class Player(models.Model):

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

    def __str__(self):
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