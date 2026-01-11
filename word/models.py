from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Announcement(models.Model):
    """首页公告模型"""
    title = models.CharField(max_length=200, verbose_name='公告标题')
    content = models.TextField(verbose_name='公告内容')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='创建者')
    
    class Meta:
        verbose_name = '首页公告'
        verbose_name_plural = '首页公告'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title


class Vocabulary(models.Model):
    """词汇模型"""
    LEVEL_CHOICES = [
        ('CET-4', 'CET-4'),
        ('CET-6', 'CET-6'),
        ('Academic', '学术词汇'),
        ('Business', '商务词汇'),
        ('Technology', '科技词汇'),
        ('Daily', '日常词汇'),
        ('Advanced', '高级词汇'),
        ('TOEFL', '托福词汇'),
        ('IELTS', '雅思词汇'),
        ('Professional', '专业词汇'),
        ('Science', '科学词汇'),
        ('Medical', '医学词汇'),
        ('Legal', '法律词汇'),
        ('Engineering', '工程词汇'),
        ('Finance', '金融词汇'),
        ('Education', '教育词汇'),
    ]
    
    word = models.CharField(max_length=100, unique=True, verbose_name='单词', db_index=True)
    translation = models.CharField(max_length=200, verbose_name='中文翻译')
    meaning = models.TextField(verbose_name='详细含义')
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, verbose_name='词汇级别', db_index=True)
    pronunciation = models.CharField(max_length=100, blank=True, verbose_name='音标')
    example_sentence = models.TextField(blank=True, verbose_name='例句')
    example_translation = models.TextField(blank=True, verbose_name='例句翻译')
    frequency = models.IntegerField(default=0, verbose_name='使用频率')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '词汇'
        verbose_name_plural = '词汇库'
        ordering = ['level', 'word']
        indexes = [
            models.Index(fields=['word']),
            models.Index(fields=['level']),
            models.Index(fields=['word', 'level']),
        ]
    
    def __str__(self):
        return f"{self.word} ({self.level})"


class WordCategory(models.Model):
    """词汇分类模型"""
    name = models.CharField(max_length=50, unique=True, verbose_name='分类名称')
    description = models.TextField(blank=True, verbose_name='分类描述')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    
    class Meta:
        verbose_name = '词汇分类'
        verbose_name_plural = '词汇分类'
    
    def __str__(self):
        return self.name


class VocabularyCategory(models.Model):
    """词汇与分类的关联模型"""
    vocabulary = models.ForeignKey(Vocabulary, on_delete=models.CASCADE, verbose_name='词汇')
    category = models.ForeignKey(WordCategory, on_delete=models.CASCADE, verbose_name='分类')
    
    class Meta:
        verbose_name = '词汇分类关联'
        verbose_name_plural = '词汇分类关联'
        unique_together = ['vocabulary', 'category']
    
    def __str__(self):
        return f"{self.vocabulary.word} - {self.category.name}"
