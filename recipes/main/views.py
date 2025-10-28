from uuid import uuid4
from pathlib import Path
import xml.etree.ElementTree as ET
import json

from django.conf import settings
from django.contrib import messages
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.db.models.functions import Cast
from django.db.models import TextField
from django.db import IntegrityError

from .forms import RecipeForm, UploadDataForm, RecipeEditForm
from .models import Recipe


def _generate_safe_filename(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}.xml"


def _validate_recipe_payload(obj):
    # Accept a single recipe object or a list of recipe objects
    def is_valid_recipe(rec):
        required_str_fields = ['title', 'instructions']
        required_int_fields = ['servings', 'cook_minutes']
        for field in required_str_fields:
            if not isinstance(rec.get(field), str) or not rec.get(field).strip():
                return False
        for field in required_int_fields:
            if not isinstance(rec.get(field), int) or rec.get(field) < 0:
                return False
        ings = rec.get('ingredients')
        if not isinstance(ings, list) or not all(isinstance(x, str) and x.strip() for x in ings):
            return False
        return True

    if isinstance(obj, list):
        return len(obj) > 0 and all(is_valid_recipe(x) for x in obj)
    if isinstance(obj, dict):
        return is_valid_recipe(obj)
    return False


def _parse_xml(content: bytes):
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return None
    # Expect <recipes> with multiple <recipe> or a single <recipe>
    def recipe_from_elem(elem):
        def txt(tag):
            node = elem.find(tag)
            return node.text.strip() if node is not None and node.text else ''

        ingredients_parent = elem.find('ingredients')
        ingredients = []
        if ingredients_parent is not None:
            for ing in ingredients_parent.findall('ingredient'):
                if ing.text and ing.text.strip():
                    ingredients.append(ing.text.strip())
        try:
            servings = int(txt('servings'))
            cook_minutes = int(txt('cook_minutes'))
        except ValueError:
            return None
        return {
            'title': txt('title'),
            'ingredients': ingredients,
            'instructions': txt('instructions'),
            'servings': servings,
            'cook_minutes': cook_minutes,
        }

    if root.tag == 'recipe':
        data = recipe_from_elem(root)
        return data if data else None
    if root.tag == 'recipes':
        result = []
        for rec_elem in root.findall('recipe'):
            data = recipe_from_elem(rec_elem)
            if not data:
                return None
            result.append(data)
        return result
    return None


def _to_xml(obj) -> str:
    def recipe_elem(rec):
        r = ET.Element('recipe')
        ET.SubElement(r, 'title').text = rec['title']
        ing_parent = ET.SubElement(r, 'ingredients')
        for ing in rec['ingredients']:
            ET.SubElement(ing_parent, 'ingredient').text = ing
        ET.SubElement(r, 'instructions').text = rec['instructions']
        ET.SubElement(r, 'servings').text = str(rec['servings'])
        ET.SubElement(r, 'cook_minutes').text = str(rec['cook_minutes'])
        return r

    if isinstance(obj, list):
        root = ET.Element('recipes')
        for rec in obj:
            root.append(recipe_elem(rec))
    else:
        root = recipe_elem(obj)
    return ET.tostring(root, encoding='utf-8', xml_declaration=True).decode('utf-8')


def _read_all_recipes_from_single_file():
    path = Path(settings.SINGLE_DATA_FILE)
    if not path.exists():
        return []
    try:
        content = path.read_text(encoding='utf-8')
        parsed = _parse_xml(content.encode('utf-8'))
        if parsed is None:
            return []
        return parsed if isinstance(parsed, list) else [parsed]
    except Exception:
        return []


def _write_all_recipes_to_single_file(recipes_list):
    # recipes_list is a list of recipe dicts
    xml_text = _to_xml(recipes_list)
    Path(settings.SINGLE_DATA_FILE).write_text(xml_text, encoding='utf-8')


def recipe_form_view(request):
    if request.method == 'POST':
        form = RecipeForm(request.POST)
        if form.is_valid():
            recipe_data = {
                'title': form.cleaned_data['title'],
                'ingredients': [x.strip() for x in form.cleaned_data['ingredients'].split('\n') if x.strip()],
                'instructions': form.cleaned_data['instructions'],
                'servings': form.cleaned_data['servings'],
                'cook_minutes': form.cleaned_data['cook_minutes'],
            }
            
            storage_type = form.cleaned_data['storage_type']
            
            if storage_type == 'file':
                # Сохранение в файл (существующая логика)
                all_recipes = _read_all_recipes_from_single_file()
                all_recipes.append(recipe_data)
                _write_all_recipes_to_single_file(all_recipes)
                messages.success(request, f'Рецепт сохранён в файл {Path(settings.SINGLE_DATA_FILE).name}')
            else:
                # Сохранение в базу данных
                try:
                    # Проверка на дубликаты
                    existing_recipe = Recipe.objects.filter(
                        title=recipe_data['title'],
                        instructions=recipe_data['instructions'],
                        servings=recipe_data['servings'],
                        cook_minutes=recipe_data['cook_minutes']
                    ).first()
                    
                    if existing_recipe:
                        # Проверяем ингредиенты
                        existing_ingredients = existing_recipe.get_ingredients_list()
                        if sorted(existing_ingredients) == sorted(recipe_data['ingredients']):
                            messages.warning(request, 'Такой рецепт уже существует в базе данных!')
                            return redirect('main:recipe_form')
                    
                    # Создаем новый рецепт
                    recipe = Recipe.from_dict(recipe_data)
                    recipe.save()
                    messages.success(request, 'Рецепт успешно сохранён в базу данных!')
                except Exception as e:
                    messages.error(request, f'Ошибка при сохранении в БД: {str(e)}')
            
            return redirect('main:recipe_form')
        else:
            messages.error(request, 'Исправьте ошибки формы.')
    else:
        form = RecipeForm()
    upload_form = UploadDataForm()
    return render(request, 'main/recipe_form.html', {'form': form, 'upload_form': upload_form})


def upload_view(request):
    if request.method != 'POST':
        return redirect('main:recipe_form')
    form = UploadDataForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, 'Ошибка загрузки файла.')
        return redirect('main:recipe_form')

    f = form.cleaned_data['file']
    content = f.read()
    # Validate XML only
    try:
        parsed = _parse_xml(content)
        if parsed is None or not _validate_recipe_payload(parsed):
            raise ValueError('XML схема невалидна')
        # Merge parsed data into single consolidated file
        incoming = parsed if isinstance(parsed, list) else [parsed]
        all_recipes = _read_all_recipes_from_single_file()
        all_recipes.extend(incoming)
        _write_all_recipes_to_single_file(all_recipes)
    except Exception as exc:
        messages.error(request, f'Файл отклонён: {exc}')
        return redirect('main:recipe_form')

    messages.success(request, f'Файл загружен и добавлен в {Path(settings.SINGLE_DATA_FILE).name}')
    return redirect('main:files_list')


def files_list_view(request):
    uploads = []
    exports = []
    up_dir = Path(settings.UPLOADS_DIR)
    ex_dir = Path(settings.EXPORTS_DIR)
    def describe(path: Path):
        stat = path.stat()
        return {
            'name': path.name,
            'size': stat.st_size,
            'mtime': stat.st_mtime,
        }
    if up_dir.exists():
        uploads = [describe(p) for p in sorted(up_dir.glob('*.xml'))]
    if ex_dir.exists():
        exports = [describe(p) for p in sorted(ex_dir.glob('*.xml'))]
    # Ensure the single consolidated file appears even if other files are absent
    single_file = Path(settings.SINGLE_DATA_FILE)
    if single_file.exists():
        # Avoid duplicates if it is already listed
        if not any(x['name'] == single_file.name for x in exports):
            exports.append(describe(single_file))
    empty = not uploads and not exports
    return render(request, 'main/files_list.html', {
        'uploads': uploads,
        'exports': exports,
        'empty': empty,
    })


def file_detail_view(request, kind: str, filename: str):
    # Sanitize filename to prevent path traversal
    if '/' in filename or '\\' in filename or filename.startswith('.'):  # basic checks
        raise Http404
    base_dir = settings.UPLOADS_DIR if kind == 'uploads' else settings.EXPORTS_DIR if kind == 'exports' else None
    if base_dir is None:
        raise Http404
    path = Path(base_dir) / filename
    if not path.exists() or not path.is_file():
        raise Http404

    # Get file metadata
    stat = path.stat()
    file_info = {
        'size': stat.st_size,
        'mtime': stat.st_mtime,
        'path': str(path),
    }

    ext = path.suffix.lower()
    raw_text = path.read_text(encoding='utf-8')
    data = None
    error = None
    error_details = None
    
    if ext == '.xml':
        try:
            parsed = _parse_xml(raw_text.encode('utf-8'))
            if parsed is not None and _validate_recipe_payload(parsed):
                data = parsed
            else:
                error = 'XML файл не соответствует ожидаемой схеме рецептов.'
                error_details = 'Файл содержит XML, но структура не соответствует ожидаемому формату рецептов.'
        except Exception as e:
            error = 'Ошибка при парсинге XML файла.'
            error_details = f'Детали ошибки: {str(e)}'
    else:
        error = 'Неподдерживаемое расширение файла.'
        error_details = f'Поддерживаются только XML файлы. Текущий файл: {ext}'

    return render(request, 'main/file_detail.html', {
        'kind': kind,
        'filename': filename,
        'file_info': file_info,
        'raw_text': raw_text,
        'data': data,
        'error': error,
        'error_details': error_details,
    })


def database_recipes_view(request):
    """Отображение рецептов из базы данных"""
    search_query = request.GET.get('search', '')
    recipes = Recipe.objects.all()
    
    if search_query:
        # SQLite не поддерживает icontains по JSONField напрямую — приводим JSON к тексту
        recipes = recipes.annotate(ingredients_text=Cast('ingredients', output_field=TextField())) \
            .filter(
                Q(title__icontains=search_query) |
                Q(instructions__icontains=search_query) |
                Q(ingredients_text__icontains=search_query)
            )
    
    return render(request, 'main/database_recipes.html', {
        'recipes': recipes,
        'search_query': search_query,
    })


def ajax_search_recipes(request):
    """AJAX поиск рецептов"""
    if request.method == 'GET':
        query = request.GET.get('q', '')
        if len(query) < 2:
            return JsonResponse({'recipes': []})
        
        # Аналогично для AJAX-поиска — приводим JSON к тексту
        recipes = Recipe.objects.annotate(ingredients_text=Cast('ingredients', output_field=TextField())) \
            .filter(
                Q(title__icontains=query) |
                Q(instructions__icontains=query) |
                Q(ingredients_text__icontains=query)
            )[:10]
        
        results = []
        for recipe in recipes:
            results.append({
                'id': recipe.id,
                'title': recipe.title,
                'servings': recipe.servings,
                'cook_minutes': recipe.cook_minutes,
                'ingredients_count': len(recipe.get_ingredients_list()),
                'url': f'/recipes/{recipe.id}/'
            })
        
        return JsonResponse({'recipes': results})
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


def recipe_detail_view(request, recipe_id):
    """Детальный просмотр рецепта из БД"""
    recipe = get_object_or_404(Recipe, id=recipe_id)
    return render(request, 'main/recipe_detail.html', {'recipe': recipe})


def recipe_edit_view(request, recipe_id):
    """Редактирование рецепта"""
    recipe = get_object_or_404(Recipe, id=recipe_id)
    
    if request.method == 'POST':
        form = RecipeEditForm(request.POST, instance=recipe)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Рецепт успешно обновлён!')
                return redirect('main:recipe_detail', recipe_id=recipe.id)
            except Exception as e:
                messages.error(request, f'Ошибка при обновлении: {str(e)}')
        else:
            messages.error(request, 'Исправьте ошибки формы.')
    else:
        form = RecipeEditForm(instance=recipe)
    
    return render(request, 'main/recipe_edit.html', {
        'form': form,
        'recipe': recipe,
    })


@require_http_methods(["POST"])
def recipe_delete_view(request, recipe_id):
    """Удаление рецепта"""
    recipe = get_object_or_404(Recipe, id=recipe_id)
    recipe_title = recipe.title
    recipe.delete()
    messages.success(request, f'Рецепт "{recipe_title}" успешно удалён!')
    return redirect('main:database_recipes')


def data_source_choice_view(request):
    """Выбор источника данных"""
    return render(request, 'main/data_source_choice.html')

