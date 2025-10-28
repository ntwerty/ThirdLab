from django import forms


class RecipeForm(forms.Form):
    title = forms.CharField(max_length=200, label='Название рецепта')
    ingredients = forms.CharField(
        widget=forms.Textarea,
        label='Ингредиенты (по одному в строке)'
    )
    instructions = forms.CharField(
        widget=forms.Textarea,
        label='Инструкции'
    )
    servings = forms.IntegerField(min_value=1, label='Порции')
    cook_minutes = forms.IntegerField(min_value=0, label='Время готовки (мин)')
    storage_type = forms.ChoiceField(
        choices=[
            ('file', 'Сохранить в файл'),
            ('database', 'Сохранить в базу данных')
        ],
        label='Способ сохранения',
        initial='file',
        widget=forms.RadioSelect
    )

    def clean_ingredients(self):
        raw = self.cleaned_data['ingredients']
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        if not lines:
            raise forms.ValidationError('Укажите хотя бы один ингредиент.')
        return '\n'.join(lines)


class RecipeEditForm(forms.ModelForm):
    ingredients = forms.CharField(
        widget=forms.Textarea,
        label='Ингредиенты (по одному в строке)'
    )

    class Meta:
        from .models import Recipe
        model = Recipe
        fields = ['title', 'ingredients', 'instructions', 'servings', 'cook_minutes']
        labels = {
            'title': 'Название рецепта',
            'instructions': 'Инструкции',
            'servings': 'Порции',
            'cook_minutes': 'Время готовки (мин)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Преобразуем список ингредиентов в строку для отображения
            ingredients_list = self.instance.get_ingredients_list()
            self.initial['ingredients'] = '\n'.join(ingredients_list)

    def clean_ingredients(self):
        raw = self.cleaned_data['ingredients']
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        if not lines:
            raise forms.ValidationError('Укажите хотя бы один ингредиент.')
        return lines

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.set_ingredients_list(self.cleaned_data['ingredients'])
        if commit:
            instance.save()
        return instance


class UploadDataForm(forms.Form):
    file = forms.FileField(label='Файл XML')

    def clean_file(self):
        f = self.cleaned_data['file']
        # Limit size to ~2MB for safety
        max_size = 2 * 1024 * 1024
        if f.size > max_size:
            raise forms.ValidationError('Файл слишком большой (макс. 2MB).')
        return f


