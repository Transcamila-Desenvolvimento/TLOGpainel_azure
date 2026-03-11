# usuarios/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, Filial

# Admin para Filial
@admin.register(Filial)
class FilialAdmin(admin.ModelAdmin):
    list_display = ['nome', 'codigo', 'app_django', 'url_inicial', 'ativa']
    list_filter = ['ativa', 'codigo']
    search_fields = ['nome', 'codigo']
    list_editable = ['ativa']

# Inline para mostrar o UserProfile no admin do User
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Perfil do Usuário'
    filter_horizontal = ['filiais']  # Para seleção fácil de múltiplas filiais

# Custom User Admin que inclui o UserProfile
class CustomUserAdmin(UserAdmin):
    inlines = [UserProfileInline]
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'get_filiais', 'get_filial_selecionada']
    
    def get_filiais(self, obj):
        try:
            return ", ".join([f.nome for f in obj.userprofile.filiais.all()])
        except:
            return "Nenhuma"
    get_filiais.short_description = 'Filiais com Acesso'
    
    def get_filial_selecionada(self, obj):
        try:
            return obj.userprofile.filial_selecionada.nome if obj.userprofile.filial_selecionada else "Nenhuma"
        except:
            return "Nenhuma"
    get_filial_selecionada.short_description = 'Filial Selecionada'

# Re-registre o User admin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Admin para UserProfile (opcional, já que está como inline)
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_filiais', 'filial_selecionada']
    list_filter = ['filial_selecionada', 'filiais']
    filter_horizontal = ['filiais']
    search_fields = ['user__username', 'user__email']
    
    def get_filiais(self, obj):
        return ", ".join([f.nome for f in obj.filiais.all()])
    get_filiais.short_description = 'Filiais com Acesso'