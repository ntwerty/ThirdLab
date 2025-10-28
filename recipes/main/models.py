from django.db import models
from django.utils.crypto import salted_hmac
from django.core.validators import MinValueValidator
import json


class Recipe(models.Model):
    title = models.CharField(max_length=200, verbose_name='Название рецепта')
    ingredients = models.JSONField(verbose_name='Ингредиенты')
    instructions = models.TextField(verbose_name='Инструкции')
    servings = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='Порции'
    )
    cook_minutes = models.PositiveIntegerField(
        validators=[MinValueValidator(0)],
        verbose_name='Время готовки (мин)'
    )
    signature = models.CharField(max_length=64, unique=True, editable=False, null=True, blank=True, verbose_name='Сигнатура дубликата')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_ingredients_list(self):
        """Возвращает список ингредиентов как список строк"""
        if isinstance(self.ingredients, list):
            return self.ingredients
        return []

    def set_ingredients_list(self, ingredients_list):
        """Устанавливает ингредиенты из списка строк"""
        self.ingredients = ingredients_list

    def to_dict(self):
        """Преобразует модель в словарь для совместимости с XML форматом"""
        return {
            'title': self.title,
            'ingredients': self.get_ingredients_list(),
            'instructions': self.instructions,
            'servings': self.servings,
            'cook_minutes': self.cook_minutes,
        }

    @classmethod
    def from_dict(cls, data):
        """Создает экземпляр модели из словаря"""
        return cls(
            title=data['title'],
            ingredients=data['ingredients'],
            instructions=data['instructions'],
            servings=data['servings'],
            cook_minutes=data['cook_minutes'],
        )

    def _compute_signature(self) -> str:
        # Нормализуем ингредиенты (сортируем и обрезаем пробелы)
        ingredients_list = self.get_ingredients_list()
        normalized_ingredients = [x.strip().lower() for x in ingredients_list if isinstance(x, str)]
        normalized_ingredients.sort()
        payload = {
            'title': (self.title or '').strip().lower(),
            'instructions': (self.instructions or '').strip().lower(),
            'servings': int(self.servings or 0),
            'cook_minutes': int(self.cook_minutes or 0),
            'ingredients': normalized_ingredients,
        }
        # Используем стабильный HMAC для короткой строки-сигнатуры
        # Ключ фиксированный на уровне кода, так как цель — детекция дубликатов, а не безопасность
        return salted_hmac('recipe-dup', str(payload)).hexdigest()

    def save(self, *args, **kwargs):
        # Перед сохранением обновляем сигнатуру
        try:
            self.signature = self._compute_signature()
        except Exception:
            # В крайнем случае не блокируем сохранение, но лучше дать предсказуемое значение
            self.signature = ''
        super().save(*args, **kwargs)
