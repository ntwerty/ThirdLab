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

    def clean_ingredients(self):
        raw = self.cleaned_data['ingredients']
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        if not lines:
            raise forms.ValidationError('Укажите хотя бы один ингредиент.')
        return '\n'.join(lines)


class UploadDataForm(forms.Form):
    file = forms.FileField(label='Файл XML')

    def clean_file(self):
        f = self.cleaned_data['file']
        # Limit size to ~2MB for safety
        max_size = 2 * 1024 * 1024
        if f.size > max_size:
            raise forms.ValidationError('Файл слишком большой (макс. 2MB).')
        return f


