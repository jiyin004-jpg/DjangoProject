from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Announcement, Vocabulary, WordCategory, VocabularyCategory

# Register your models here.

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'is_active', 'created_by', 'created_at', 'updated_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'content']
    readonly_fields = ['created_at', 'updated_at']
    
    def save_model(self, request, obj, form, change):
        if not change:  # 如果是新建
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Vocabulary)
class VocabularyAdmin(admin.ModelAdmin):
    list_display = ['word', 'translation', 'level', 'frequency', 'is_active', 'created_at']
    list_filter = ['level', 'is_active', 'created_at']
    search_fields = ['word', 'translation', 'meaning']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['is_active', 'frequency']
    list_per_page = 50
    
    fieldsets = (
        ('基本信息', {
            'fields': ('word', 'translation', 'meaning', 'level')
        }),
        ('详细信息', {
            'fields': ('pronunciation', 'example_sentence', 'example_translation', 'frequency'),
            'classes': ('collapse',)
        }),
        ('状态', {
            'fields': ('is_active',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['make_active', 'make_inactive', 'export_words']
    
    def make_active(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f'已启用 {queryset.count()} 个单词')
    make_active.short_description = '启用选中的单词'
    
    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f'已禁用 {queryset.count()} 个单词')
    make_inactive.short_description = '禁用选中的单词'


@admin.register(WordCategory)
class WordCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'description']


@admin.register(VocabularyCategory)
class VocabularyCategoryAdmin(admin.ModelAdmin):
    list_display = ['vocabulary', 'category']
    list_filter = ['category']
    search_fields = ['vocabulary__word', 'category__name']

# 自定义管理员站点标题
admin.site.site_header = '英语学习平台管理后台'
admin.site.site_title = '管理后台'
admin.site.index_title = '欢迎使用英语学习平台管理系统'
