from django.contrib import admin

from .models import Contribution, Round


@admin.register(Round)
class RoundAdmin(admin.ModelAdmin):
    list_display = ('id', 'circle', 'payout_recipient', 'status', 'contribution_amount', 'payout_amount', 'deadline')
    list_filter = ('status', 'circle')


@admin.register(Contribution)
class ContributionAdmin(admin.ModelAdmin):
    list_display = ('id', 'round', 'member', 'amount', 'penalty', 'total_paid', 'is_late')
    list_filter = ('is_late',)
