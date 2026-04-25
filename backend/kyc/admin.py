from django.contrib import admin

from .models import Account, KycDocument, KycSubmission, NotificationEvent


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("username", "role", "email", "created_at")
    search_fields = ("username", "email")
    list_filter = ("role",)


class KycDocumentInline(admin.TabularInline):
    model = KycDocument
    extra = 0


@admin.register(KycSubmission)
class KycSubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "merchant", "state", "business_name", "queue_entered_at", "decided_at")
    list_filter = ("state", "business_type")
    search_fields = ("merchant__username", "business_name", "personal_email")
    inlines = [KycDocumentInline]


@admin.register(NotificationEvent)
class NotificationEventAdmin(admin.ModelAdmin):
    list_display = ("merchant", "event_type", "timestamp")
    list_filter = ("event_type",)
    search_fields = ("merchant__username",)

