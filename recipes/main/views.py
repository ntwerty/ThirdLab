from uuid import uuid4
from pathlib import Path
import xml.etree.ElementTree as ET

from django.conf import settings
from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render

from .forms import RecipeForm, UploadDataForm


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


def recipe_form_view(request):
    if request.method == 'POST':
        form = RecipeForm(request.POST)
        if form.is_valid():
            recipe = {
                'title': form.cleaned_data['title'],
                'ingredients': [x.strip() for x in form.cleaned_data['ingredients'].split('\n') if x.strip()],
                'instructions': form.cleaned_data['instructions'],
                'servings': form.cleaned_data['servings'],
                'cook_minutes': form.cleaned_data['cook_minutes'],
            }
            filename = _generate_safe_filename('recipe')
            target_path = Path(settings.EXPORTS_DIR) / filename
            target_path.write_text(_to_xml(recipe), encoding='utf-8')
            messages.success(request, f'Рецепт сохранён в файл {filename}')
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
        saved_filename = _generate_safe_filename('upload')
        (Path(settings.UPLOADS_DIR) / saved_filename).write_text(
            _to_xml(parsed), encoding='utf-8'
        )
    except Exception as exc:
        messages.error(request, f'Файл отклонён: {exc}')
        return redirect('main:recipe_form')

    messages.success(request, f'Файл загружен и сохранён как {saved_filename}')
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

    ext = path.suffix.lower()
    raw_text = path.read_text(encoding='utf-8')
    data = None
    error = None
    if ext == '.xml':
        parsed = _parse_xml(raw_text.encode('utf-8'))
        if parsed is not None and _validate_recipe_payload(parsed):
            data = parsed
        else:
            error = 'XML файл не соответствует ожидаемой схеме.'
    else:
        error = 'Неподдерживаемое расширение файла.'

    return render(request, 'main/file_detail.html', {
        'kind': kind,
        'filename': filename,
        'raw_text': raw_text,
        'data': data,
        'error': error,
    })

