from django.contrib import admin

from .models import Circle, CircleMember


@admin.register(Circle)
class CircleAdmin(admin.ModelAdmin):
    list_display = ('name', 'invite_code', 'admin', 'contribution_amount', 'penalty_rate', 'created_at')
    search_fields = ('name', 'invite_code')


@admin.register(CircleMember)
class CircleMemberAdmin(admin.ModelAdmin):
    list_display = ('circle', 'user', 'position', 'joined_at')
    list_filter = ('circle',)
