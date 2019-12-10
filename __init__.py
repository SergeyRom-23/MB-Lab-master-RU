# MB-Lab
#
# Сайт ветки MB-Lab: https://github.com/animate1978/MB-Lab
#
# ##### НАЧАЛО ЛИЦЕНЗИОННОГО БЛОКА GPL #####
#
# Эта программа является свободным программным обеспечением; Вы можете распространять его и / или
# изменить его в соответствии с условиями GNU General Public License
# как опубликовано Фондом свободного программного обеспечения; либо версия 3
# Лицензии или (по вашему выбору) любой более поздней версии.
#
# Эта программа распространяется в надежде, что она будет полезна,
# но БЕЗ КАКИХ-ЛИБО ГАРАНТИЙ; даже без подразумеваемой гарантии
# ИЗДЕЛИЯ или ПРИГОДНОСТЬ ДЛЯ ОСОБЫХ ЦЕЛЕЙ. Смотрите
# GNU General Public License для более подробной информации.
#
# Вам надо принять Стандартнуюй общественную лицензию GNU
# вместе с этой программой; если нет, напишите в Фонд свободного программного обеспечения,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### КОНЕЦ ЛИЦЕНЗИОННОГО БЛОКА GPL #####
#
# ManuelbastioniLAB - Авторские права (C) 2015-2018 Manuel Bastioni
# Перевод (C) 2019 Сергей Ром 23


import logging

import time
import json
import os
from pathlib import Path

import bpy
from bpy.app.handlers import persistent
from bpy_extras.io_utils import ExportHelper, ImportHelper

from . import facerig
from . import humanoid, animationengine, proxyengine
from . import utils
from . import algorithms
from . import preferences
from . import addon_updater_ops
from . import humanoid_rotations

logger = logging.getLogger(__name__)

bl_info = {
    "name": "MB-Lab",
    "author": "Manuel Bastioni, MB-Lab Community",
    "version": (1, 7, 6),
    "blender": (2, 80, 74),
    "location": "View3D > Tools > MB-Lab",
    "description": "лаборатория для создания персонажей",
    "warning": "",
    'wiki_url': "https://github.com/animate1978/MB-Lab/wiki",
    'tracker_url': 'https://github.com/animate1978/MB-Lab/issues',
    "category": "Characters"
}

mblab_humanoid = humanoid.Humanoid(bl_info["version"])
mblab_retarget = animationengine.RetargetEngine()
mblab_shapekeys = animationengine.ExpressionEngineShapeK()
mblab_proxy = proxyengine.ProxyEngine()

gui_status = "NEW_SESSION"
gui_err_msg = ""
gui_active_panel = None
gui_active_panel_fin = None


def start_lab_session():
    global mblab_humanoid
    global gui_status, gui_err_msg

    logger.info("Start_the lab session...")
    scn = bpy.context.scene
    character_identifier = scn.mblab_character_name
    rigging_type = "base"
    if scn.mblab_use_ik:
        rigging_type = "ik"
    if scn.mblab_use_muscle:
        rigging_type = "muscle"
    if scn.mblab_use_muscle and scn.mblab_use_ik:
        rigging_type = "muscle_ik"

    lib_filepath = algorithms.get_blendlibrary_path()

    obj = None
    is_existing = False
    is_obj = algorithms.looking_for_humanoid_obj()

    if is_obj[0] == "ERROR":
        gui_status = "ERROR_SESSION"
        gui_err_msg = is_obj[1]
        return

    if is_obj[0] == "NO_OBJ":
        base_model_name = mblab_humanoid.characters_config[character_identifier]["template_model"]
        obj = algorithms.import_object_from_lib(lib_filepath, base_model_name, character_identifier)
        obj["manuellab_vers"] = bl_info["version"]
        obj["manuellab_id"] = character_identifier
        obj["manuellab_rig"] = rigging_type

    if is_obj[0] == "FOUND":
        obj = algorithms.get_object_by_name(is_obj[1])
        character_identifier = obj["manuellab_id"]
        rigging_type = obj["manuellab_rig"]
        is_existing = True

    if not obj:
        logger.critical("Инициализация неудачна...")
        gui_status = "ERROR_SESSION"
        gui_err_msg = "Инициализация неудачна. Смотрите логи файл"
    else:
        mblab_humanoid.init_database(obj, character_identifier, rigging_type)
        if mblab_humanoid.has_data:
            gui_status = "ACTIVE_SESSION"

            if scn.mblab_use_cycles or scn.mblab_use_eevee:
                if scn.mblab_use_cycles:
                    scn.render.engine = 'CYCLES'
                else:
                    scn.render.engine = 'BLENDER_EEVEE'
                if scn.mblab_use_lamps:

                    algorithms.import_object_from_lib(lib_filepath, "Light_Key")
                    algorithms.import_object_from_lib(lib_filepath, "Light_Fill")
                    algorithms.import_object_from_lib(lib_filepath, "Light_Backlight")

            else:
                scn.render.engine = 'BLENDER_WORKBENCH'

            logger.info("Движок рендера %s", scn.render.engine)
            init_morphing_props(mblab_humanoid)
            init_categories_props(mblab_humanoid)
            init_measures_props(mblab_humanoid)
            init_restposes_props(mblab_humanoid)
            init_presets_props(mblab_humanoid)
            init_ethnic_props(mblab_humanoid)
            init_metaparameters_props(mblab_humanoid)
            init_material_parameters_props(mblab_humanoid)
            mblab_humanoid.update_materials()

            if is_existing:
                logger.info("Пересоздать персонаж %s", obj.name)
                mblab_humanoid.store_mesh_in_cache()
                mblab_humanoid.reset_mesh()
                mblab_humanoid.recover_prop_values_from_obj_attr()
                mblab_humanoid.restore_mesh_from_cache()
            else:
                mblab_humanoid.reset_mesh()
                mblab_humanoid.update_character(mode="update_all")

            algorithms.deselect_all_objects()


@persistent
def check_manuelbastionilab_session(dummy):
    global mblab_humanoid
    global gui_status, gui_err_msg
    scn = bpy.context.scene
    if mblab_humanoid:
        # init_femaleposes_props()
        # init_maleposes_props()
        gui_status = "NEW_SESSION"
        is_obj = algorithms.looking_for_humanoid_obj()
        if is_obj[0] == "FOUND":
            # gui_status = "RECOVERY_SESSION"
            # if scn.do_not_ask_again:
            start_lab_session()
        if is_obj[0] == "ERROR":
            gui_status = "ERROR_SESSION"
            gui_err_msg = is_obj[1]
            return


bpy.app.handlers.load_post.append(check_manuelbastionilab_session)


def sync_character_to_props():
    # It's important to avoid problems with Blender undo system
    global mblab_humanoid
    mblab_humanoid.sync_character_data_to_obj_props()
    mblab_humanoid.update_character()


def realtime_update(self, context):
    """
    Update the character while the prop slider moves.
    """
    global mblab_humanoid
    if mblab_humanoid.bodydata_realtime_activated:
        # time1 = time.time()
        scn = bpy.context.scene
        mblab_humanoid.update_character(category_name=scn.morphingCategory, mode="update_realtime")
        mblab_humanoid.sync_gui_according_measures()
        # print("realtime_update: {0}".format(time.time()-time1))


def age_update(self, context):
    global mblab_humanoid
    time1 = time.time()
    if mblab_humanoid.metadata_realtime_activated:
        time1 = time.time()
        mblab_humanoid.calculate_transformation("AGE")


def mass_update(self, context):
    global mblab_humanoid
    if mblab_humanoid.metadata_realtime_activated:
        mblab_humanoid.calculate_transformation("FAT")


def tone_update(self, context):
    global mblab_humanoid
    if mblab_humanoid.metadata_realtime_activated:
        mblab_humanoid.calculate_transformation("MUSCLE")


def modifiers_update(self, context):
    sync_character_to_props()


def set_cycles_render_engine(self, context):
    if context.scene.mblab_use_cycles:
        context.scene.mblab_use_eevee = False


def set_eevee_render_engine(self, context):
    if context.scene.mblab_use_eevee:
        context.scene.mblab_use_cycles = False


def preset_update(self, context):
    """
    Update the character while prop slider moves
    """
    scn = bpy.context.scene
    global mblab_humanoid
    obj = mblab_humanoid.get_object()
    filepath = os.path.join(
        mblab_humanoid.presets_path,
        "".join([obj.preset, ".json"]))
    mblab_humanoid.load_character(filepath, mix=scn.mblab_mix_characters)


def ethnic_update(self, context):
    scn = bpy.context.scene
    global mblab_humanoid
    obj = mblab_humanoid.get_object()
    filepath = os.path.join(
        mblab_humanoid.phenotypes_path,
        "".join([obj.ethnic, ".json"]))
    mblab_humanoid.load_character(filepath, mix=scn.mblab_mix_characters)


def material_update(self, context):
    global mblab_humanoid
    if mblab_humanoid.material_realtime_activated:
        mblab_humanoid.update_materials(update_textures_nodes=False)


def measure_units_update(self, context):
    global mblab_humanoid
    mblab_humanoid.sync_gui_according_measures()


def human_expression_update(self, context):
    global mblab_shapekeys
    scn = bpy.context.scene
    mblab_shapekeys.sync_expression_to_gui()


def restpose_update(self, context):
    global mblab_humanoid
    armature = mblab_humanoid.get_armature()
    filepath = os.path.join(
        mblab_humanoid.restposes_path,
        "".join([armature.rest_pose, ".json"]))
    mblab_retarget.load_pose(filepath, armature)


def malepose_update(self, context):
    global mblab_retarget
    armature = utils.get_active_armature()
    filepath = os.path.join(
        mblab_retarget.maleposes_path,
        "".join([armature.male_pose, ".json"]))
    mblab_retarget.load_pose(filepath, use_retarget=True)


def femalepose_update(self, context):
    global mblab_retarget
    armature = utils.get_active_armature()
    filepath = os.path.join(
        mblab_retarget.femaleposes_path,
        "".join([armature.female_pose, ".json"]))
    mblab_retarget.load_pose(filepath, use_retarget=True)


def init_morphing_props(humanoid_instance):
    for prop in humanoid_instance.character_data:
        setattr(
            bpy.types.Object,
            prop,
            bpy.props.FloatProperty(
                name=prop,
                min=-5.0,
                max=5.0,
                soft_min=0.0,
                soft_max=1.0,
                precision=3,
                default=0.5,
                update=realtime_update))


def init_measures_props(humanoid_instance):
    for measure_name, measure_val in humanoid_instance.morph_engine.measures.items():
        setattr(
            bpy.types.Object,
            measure_name,
            bpy.props.FloatProperty(
                name=measure_name, min=0.0, max=500.0,
                default=measure_val))
    humanoid_instance.sync_gui_according_measures()


def init_categories_props(humanoid_instance):
    categories_enum = []
    for category in mblab_humanoid.get_categories():
        categories_enum.append(
            (category.name, category.name, category.name))

    bpy.types.Scene.morphingCategory = bpy.props.EnumProperty(
        items=categories_enum,
        update=modifiers_update,
        name="Категории морфинга")


def init_restposes_props(humanoid_instance):
    if humanoid_instance.exists_rest_poses_database():
        restpose_items = algorithms.generate_items_list(humanoid_instance.restposes_path)
        bpy.types.Object.rest_pose = bpy.props.EnumProperty(
            items=restpose_items,
            name="Статичные позы",
            default=restpose_items[0][0],
            update=restpose_update)


def init_maleposes_props():
    global mblab_retarget
    if mblab_retarget.maleposes_exist:
        if not hasattr(bpy.types.Object, 'male_pose'):
            malepose_items = algorithms.generate_items_list(mblab_retarget.maleposes_path)
            bpy.types.Object.male_pose = bpy.props.EnumProperty(
                items=malepose_items,
                name="Мужские позы",
                default=malepose_items[0][0],
                update=malepose_update)


def init_femaleposes_props():
    global mblab_retarget
    if mblab_retarget.femaleposes_exist:
        if not hasattr(bpy.types.Object, 'female_pose'):
            femalepose_items = algorithms.generate_items_list(mblab_retarget.femaleposes_path)
            bpy.types.Object.female_pose = bpy.props.EnumProperty(
                items=femalepose_items,
                name="Женские позы",
                default=femalepose_items[0][0],
                update=femalepose_update)


def init_expression_props():
    for expression_name in mblab_shapekeys.expressions_labels:
        if not hasattr(bpy.types.Object, expression_name):
            setattr(
                bpy.types.Object,
                expression_name,
                bpy.props.FloatProperty(
                    name=expression_name,
                    min=0.0,
                    max=1.0,
                    precision=3,
                    default=0.0,
                    update=human_expression_update))


def init_presets_props(humanoid_instance):
    if humanoid_instance.exists_preset_database():
        preset_items = algorithms.generate_items_list(humanoid_instance.presets_path)
        bpy.types.Object.preset = bpy.props.EnumProperty(
            items=preset_items,
            name="Типы",
            update=preset_update)


def init_ethnic_props(humanoid_instance):
    if humanoid_instance.exists_phenotype_database():
        ethnic_items = algorithms.generate_items_list(humanoid_instance.phenotypes_path)
        bpy.types.Object.ethnic = bpy.props.EnumProperty(
            items=ethnic_items,
            name="Фенотипы",
            update=ethnic_update)


def init_metaparameters_props(humanoid_instance):
    for meta_data_prop in humanoid_instance.character_metaproperties.keys():
        upd_function = None

        if "age" in meta_data_prop:
            upd_function = age_update
        if "mass" in meta_data_prop:
            upd_function = mass_update
        if "tone" in meta_data_prop:
            upd_function = tone_update
        if "last" in meta_data_prop:
            upd_function = None

        if "last_" not in meta_data_prop:
            setattr(
                bpy.types.Object,
                meta_data_prop,
                bpy.props.FloatProperty(
                    name=meta_data_prop, min=-1.0, max=1.0,
                    precision=3,
                    default=0.0,
                    update=upd_function))


def init_material_parameters_props(humanoid_instance):
    for material_data_prop, value in humanoid_instance.character_material_properties.items():
        setattr(
            bpy.types.Object,
            material_data_prop,
            bpy.props.FloatProperty(
                name=material_data_prop,
                min=0.0,
                max=1.0,
                precision=2,
                update=material_update,
                default=value))


def angle_update_0(self, context):
    global mblab_retarget
    scn = bpy.context.scene
    value = scn.mblab_rot_offset_0
    mblab_retarget.correct_bone_angle(0, value)


def angle_update_1(self, context):
    global mblab_retarget
    scn = bpy.context.scene
    value = scn.mblab_rot_offset_1
    mblab_retarget.correct_bone_angle(1, value)


def angle_update_2(self, context):
    global mblab_retarget
    scn = bpy.context.scene
    value = scn.mblab_rot_offset_2
    mblab_retarget.correct_bone_angle(2, value)


def get_character_items(self, context):
    items = []
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            if algorithms.get_template_model(obj) is not None:
                items.append((obj.name, obj.name, obj.name))
    return items


def get_proxy_items(self, context):
    items = []
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            if algorithms.get_template_model(obj) is None:
                items.append((obj.name, obj.name, obj.name))
    if len(items) == 0:
        items = [("NO_PROXY_FOUND", "Прокси не найден", "Прокси не найден")]
    return items


def get_proxy_items_from_library(self, context):
    items = mblab_proxy.assets_models
    return items


def update_proxy_library(self, context):
    mblab_proxy.update_assets_models()


def load_proxy_item(self, context):
    scn = bpy.context.scene
    mblab_proxy.load_asset(scn.mblab_assets_models)


# init_expression_props()

bpy.types.Scene.mblab_proxy_library = bpy.props.StringProperty(
    name="Каталог библиотек",
    description="Каталог с активами blend файлов",
    default="",
    maxlen=1024,
    update=update_proxy_library,
    subtype='DIR_PATH')

bpy.types.Scene.mblab_fitref_name = bpy.props.EnumProperty(
    items=get_character_items,
    name="Персонажи")

bpy.types.Scene.mblab_proxy_name = bpy.props.EnumProperty(
    items=get_proxy_items,
    name="Прокси")

bpy.types.Scene.mblab_final_prefix = bpy.props.StringProperty(
    name="Префикс",
    description="Префикс имен для доработанной модели, каркаса и материалов. Если нет, он будет создан автоматически",
    default="")

bpy.types.Scene.mblab_rot_offset_0 = bpy.props.FloatProperty(
    name="Поворот по X",
    min=-1,
    max=1,
    precision=2,
    update=angle_update_0,
    default=0.0)

bpy.types.Scene.mblab_rot_offset_1 = bpy.props.FloatProperty(
    name="Поворот по Y",
    min=-1,
    max=1,
    precision=2,
    update=angle_update_1,
    default=0.0)

bpy.types.Scene.mblab_rot_offset_2 = bpy.props.FloatProperty(
    name="Поворот по Z",
    min=-1,
    max=1,
    precision=2,
    update=angle_update_2,
    default=0.0)

bpy.types.Scene.mblab_proxy_offset = bpy.props.FloatProperty(
    name="Смещение",
    min=0,
    max=100,
    default=0)

bpy.types.Scene.mblab_proxy_threshold = bpy.props.FloatProperty(
    name="Влияние",
    min=0,
    max=1000,
    default=20)

bpy.types.Scene.mblab_use_ik = bpy.props.BoolProperty(
    name="Обратная кинематика",
    default=False,
    description="Использование обратной кинематической арматуры")

bpy.types.Scene.mblab_use_muscle = bpy.props.BoolProperty(
    name="Базовые мыщцы",
    default=False,
    description="Использование арматуры базовых мышц")

bpy.types.Scene.mblab_remove_all_modifiers = bpy.props.BoolProperty(
    name="Удаление модификаторов",
    default=False,
    description="Если установлен этот флажок, будут удалены все модификаторы, кроме арматуры (смещение, подразделение, корректирующее сглаживание и т. Д.)")

bpy.types.Scene.mblab_use_cycles = bpy.props.BoolProperty(
    name="Рендер Cycles",
    default=True,
    update=set_cycles_render_engine,
    description="Это необходимо для использования редактора скинов и шейдеров (настоятельно рекомендуется)")

bpy.types.Scene.mblab_use_eevee = bpy.props.BoolProperty(
    name="Рендер EEVEE",
    default=False,
    update=set_eevee_render_engine,
    description="Это необходимо для того, чтобы использовать редактор скинов и шейдеры")

bpy.types.Scene.mblab_use_lamps = bpy.props.BoolProperty(
    name="Студийное освещение портрета",
    default=False,
    description="Добавьте набор источников света, оптимизированных для портрета. Полезно при оформлении кожи (рекомендуется)")

bpy.types.Scene.mblab_show_measures = bpy.props.BoolProperty(
    name="Размеры",
    description="Показывать размеры",
    update=modifiers_update)

bpy.types.Scene.mblab_measure_filter = bpy.props.StringProperty(
    name="Фильтр размеров",
    default="",
    description="Фильтр видимости размеров")

bpy.types.Scene.mblab_expression_filter = bpy.props.StringProperty(
    name="Фильтр выразительности",
    default="",
    description="Фильтр видимости выражений")

bpy.types.Scene.mblab_mix_characters = bpy.props.BoolProperty(
    name="Смешать с текущим",
    description="Смешивание шаблонов")

bpy.types.Scene.mblab_template_name = bpy.props.EnumProperty(
    items=mblab_humanoid.template_types,
    name="Выбор",
    default="human_female_base")

bpy.types.Scene.mblab_character_name = bpy.props.EnumProperty(
    items=mblab_humanoid.humanoid_types,
    name="Выбор",
    default="f_af01")

bpy.types.Scene.mblab_assets_models = bpy.props.EnumProperty(
    items=get_proxy_items_from_library,
    update=load_proxy_item,
    name="Активы моделей")

bpy.types.Scene.mblab_transfer_proxy_weights = bpy.props.BoolProperty(
    name="Перенос значений одежды с тела на прокси (заменить существующий)",
    description="Если у прокси уже есть одежда, она будут заменена значениями, спроецированными из тела персонажа.",
    default=True)

bpy.types.Scene.mblab_save_images_and_backup = bpy.props.BoolProperty(
    name="Сохранение изображения и резервной копии персонажа",
    description="Сохранение изображений из шейдера скина и создание резервной копии персонажа в формате json",
    default=True)

bpy.types.Object.mblab_use_inch = bpy.props.BoolProperty(
    name="Дюйм",
    update=measure_units_update,
    description="Использование дюймов вместо cm")

bpy.types.Scene.mblab_export_proportions = bpy.props.BoolProperty(
    name="Include proportions",
    description="Include proportions in the exported character file")

bpy.types.Scene.mblab_export_materials = bpy.props.BoolProperty(
    name="Включить пропорции",
    default=True,
    description="Включить материалы в экспортированный файл персонажа")

bpy.types.Scene.mblab_show_texture_load_save = bpy.props.BoolProperty(
    name="Импорт-экспорт изображений",
    description="Показать элементы управления для импорта и экспорта изображений текстуры")

bpy.types.Scene.mblab_add_mask_group = bpy.props.BoolProperty(
    name="Добавить маску вершин",
    description="Создайте новую группу вершин и используйте ее как маску для тела под прокси.",
    default=False)

bpy.types.Scene.mblab_preserve_mass = bpy.props.BoolProperty(
    name="Масса",
    description="Сохранить текущий относительный массовый процент")

bpy.types.Scene.mblab_preserve_height = bpy.props.BoolProperty(
    name="Рост",
    description="Сохранить текущую высоту объекта")

bpy.types.Scene.mblab_preserve_tone = bpy.props.BoolProperty(
    name="Тонус",
    description="Сохранить текущий процент тонуса тела")

bpy.types.Scene.mblab_preserve_fantasy = bpy.props.BoolProperty(
    name="Фэнтези",
    description="Сохранить текущее количество модификаций")

bpy.types.Scene.mblab_preserve_body = bpy.props.BoolProperty(
    name="Тело",
    description="Сохранить размеры тела")

bpy.types.Scene.mblab_preserve_face = bpy.props.BoolProperty(
    name="Лицо",
    description="Сохранять черты лица, но не форму головы")

bpy.types.Scene.mblab_preserve_phenotype = bpy.props.BoolProperty(
    name="Фенотип",
    description="Сохранять характерные черты принадлежности к расе")

bpy.types.Scene.mblab_set_tone_and_mass = bpy.props.BoolProperty(
    name="Использовать фиксированные значения тонуса и массы",
    description="Включить настройку для массы и тонуса значениям со слайдера")

bpy.types.Scene.mblab_body_mass = bpy.props.FloatProperty(
    name="Масса тела",
    min=0.0,
    max=1.0,
    default=0.5,
    description="Сохранить текущую массу тела персонажа")

bpy.types.Scene.mblab_body_tone = bpy.props.FloatProperty(
    name="Тонус тела",
    min=0.0,
    max=1.0,
    default=0.5,
    description="Сохранить текущий тонус тела персонажа")

bpy.types.Scene.mblab_random_engine = bpy.props.EnumProperty(
    items=[("LI", "Легкие", "Небольшие отклонения от стандарта"),
           ("RE", "Реалистичные", "Реалистичные персонажи"),
           ("NO", "Заметные", "Очень заметная персонажность"),
           ("CA", "Карикатуры", "генератор карикатур"),
           ("EX", "Экстремальность", "Экстремальные персонажи")],
    name="Генератор",
    default="LI")

bpy.types.Scene.mblab_facs_rig = bpy.props.BoolProperty(
    name="Import FACS Rig")

class ButtonParametersOff(bpy.types.Operator):
    bl_label = 'Размеры тела'
    bl_idname = 'mbast.button_parameters_off'
    bl_description = 'Видимость панели'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = None
        return {'FINISHED'}


class ButtonParametersOn(bpy.types.Operator):
    bl_label = 'Размеры тела'
    bl_idname = 'mbast.button_parameters_on'
    bl_description = 'Открыть панель детализации (голова, нос, руки, и т.д....)'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = "parameters"
        sync_character_to_props()
        return {'FINISHED'}


class ButtonUtilitiesOff(bpy.types.Operator):
    bl_label = 'Инструменты'
    bl_idname = 'mbast.button_utilities_off'
    bl_description = 'Закрыть панель инструментов'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel_fin
        gui_active_panel_fin = None
        return {'FINISHED'}


class ButtonUtilitiesOn(bpy.types.Operator):
    bl_label = 'Инструменты'
    bl_idname = 'mbast.button_utilities_on'
    bl_description = 'Открыть панель инструментов'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel_fin
        gui_active_panel_fin = "utilities"
        return {'FINISHED'}


class ButtonExpressionsOff(bpy.types.Operator):
    bl_label = 'Выражения лица'
    bl_idname = 'mbast.button_expressions_off'
    bl_description = 'Закрыть панель выражений лица'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel_fin
        gui_active_panel_fin = None
        return {'FINISHED'}


class ButtonExpressionOn(bpy.types.Operator):
    bl_label = 'Выражения лица'
    bl_idname = 'mbast.button_expressions_on'
    bl_description = 'Открыть панель выражений лица'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel_fin
        gui_active_panel_fin = "expressions"
        # sync_character_to_props()
        init_expression_props()
        return {'FINISHED'}


class ButtonRandomOff(bpy.types.Operator):
    bl_label = 'Случайный генератор'
    bl_idname = 'mbast.button_random_off'
    bl_description = 'Закрыть панель случайного генератора'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = None
        return {'FINISHED'}


class ButtonRandomOn(bpy.types.Operator):
    bl_label = 'Случайный генератор'
    bl_idname = 'mbast.button_random_on'
    bl_description = 'Открыть панель случайного генератора'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = 'random'
        sync_character_to_props()
        return {'FINISHED'}


class ButtonAutomodellingOff(bpy.types.Operator):
    bl_label = 'Инструменты для автомоделирования'
    bl_idname = 'mbast.button_automodelling_off'
    bl_description = 'Закрыть панель автомоделирования'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = None
        return {'FINISHED'}


class ButtonAutomodellingOn(bpy.types.Operator):
    bl_label = 'Инструменты для автомоделирования'
    bl_idname = 'mbast.button_automodelling_on'
    bl_description = 'Открыть панель автомоделирования'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = 'automodelling'
        return {'FINISHED'}


class ButtoRestPoseOff(bpy.types.Operator):
    bl_label = 'Позы'
    bl_idname = 'mbast.button_rest_pose_off'
    bl_description = 'Закрыть панель статичных поз'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = None
        return {'FINISHED'}


class ButtonRestPoseOn(bpy.types.Operator):
    bl_label = 'Позы'
    bl_idname = 'mbast.button_rest_pose_on'
    bl_description = 'Открыть панель статичных поз'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = 'rest_pose'
        return {'FINISHED'}


class ButtoPoseOff(bpy.types.Operator):
    bl_label = 'Позы и анимация'
    bl_idname = 'mbast.button_pose_off'
    bl_description = 'Закрыть панель поз и анимации'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel_fin
        gui_active_panel_fin = None
        return {'FINISHED'}


class ButtonAssetsOn(bpy.types.Operator):
    bl_label = 'Позы и анимация'
    bl_idname = 'mbast.button_assets_on'
    bl_description = 'Открыть панель поз и анимации'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel_fin
        gui_active_panel_fin = 'assets'
        return {'FINISHED'}


class ButtoAssetsOff(bpy.types.Operator):
    bl_label = 'Библиотека активов'
    bl_idname = 'mbast.button_assets_off'
    bl_description = 'Закрыть панель с библиотекой активов'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel_fin
        gui_active_panel_fin = None
        return {'FINISHED'}


class ButtonPoseOn(bpy.types.Operator):
    bl_label = 'Позы и анимация'
    bl_idname = 'mbast.button_pose_on'
    bl_description = 'Открыть панель поз'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel_fin
        init_femaleposes_props()
        init_maleposes_props()
        gui_active_panel_fin = 'pose'
        return {'FINISHED'}


class ButtonSkinOff(bpy.types.Operator):
    bl_label = 'Редактор скинов'
    bl_idname = 'mbast.button_skin_off'
    bl_description = 'Закрыть панель редактора скинов'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = None
        return {'FINISHED'}


class ButtonSkinOn(bpy.types.Operator):
    bl_label = 'Редактор скинов'
    bl_idname = 'mbast.button_skin_on'
    bl_description = 'Открыть панель редактора скинов'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = 'skin'
        return {'FINISHED'}


class ButtonViewOptOff(bpy.types.Operator):
    bl_label = 'Опции просмотра'
    bl_idname = 'mbast.button_display_off'
# Примечание ##### Почему то опции просмотра и описание закрыть панель редактора скинов #####
    bl_description = 'Закрыть панель редактора скинов'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = None
        return {'FINISHED'}


class ButtonViewOptOn(bpy.types.Operator):
    bl_label = 'Опции просмотра'
    bl_idname = 'mbast.button_display_on'
    bl_description = 'Закрыть панель редактора скинов'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = 'display_opt'
        return {'FINISHED'}


class ButtonProxyFitOff(bpy.types.Operator):
    bl_label = 'Установки PROXY'
    bl_idname = 'mbast.button_proxy_fit_off'
    bl_description = 'Закрыть proxy панель'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel_fin
        gui_active_panel_fin = None
        return {'FINISHED'}


class ButtonProxyFitOn(bpy.types.Operator):
    bl_label = 'Установки PROXY'
    bl_idname = 'mbast.button_proxy_fit_on'
    bl_description = 'Открыть proxy панель'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel_fin
        gui_active_panel_fin = 'proxy_fit'
        return {'FINISHED'}


class ButtonFilesOff(bpy.types.Operator):
    bl_label = 'Файловые инструменты'
    bl_idname = 'mbast.button_file_off'
    bl_description = 'Закрыть панель файлов'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = None
        return {'FINISHED'}


class ButtonFilesOn(bpy.types.Operator):
    bl_label = 'Файловые инструменты'
    bl_idname = 'mbast.button_file_on'
    bl_description = 'Открыть панель файлов'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = 'file'
        return {'FINISHED'}


class ButtonFinalizeOff(bpy.types.Operator):
    bl_label = 'Финализация'
    bl_idname = 'mbast.button_finalize_off'
    bl_description = 'Закрыть панель финализации'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = None
        return {'FINISHED'}


class ButtonFinalizeOn(bpy.types.Operator):
    bl_label = 'Финализация'
    bl_idname = 'mbast.button_finalize_on'
    bl_description = 'Открыть панель финализации'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = 'finalize'
        return {'FINISHED'}


class ButtonLibraryOff(bpy.types.Operator):
    bl_label = 'Библиотека персонажей'
    bl_idname = 'mbast.button_library_off'
    bl_description = 'Закрыть панель персонажей'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = None
        return {'FINISHED'}


class ButtonLibraryOn(bpy.types.Operator):
    bl_label = 'Библиотека персонажей'
    bl_idname = 'mbast.button_library_on'
    bl_description = 'Открыть панель персонажей'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = 'library'
        return {'FINISHED'}


class ButtonFinalizedCorrectRot(bpy.types.Operator):
    bl_label = 'Регулировка выбранной кости'
    bl_idname = 'mbast.button_adjustrotation'
    bl_description = 'Исправление смещения угла кости анимации'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        scn = bpy.context.scene
        mblab_retarget.get_bone_rot_type()

        if mblab_retarget.rot_type in ["EULER", "QUATERNION"]:
            offsets = mblab_retarget.get_offset_values()
            scn.mblab_rot_offset_0 = offsets[0]
            scn.mblab_rot_offset_1 = offsets[1]
            scn.mblab_rot_offset_2 = offsets[2]
            mblab_retarget.correction_is_sync = True
        return {'FINISHED'}


class UpdateSkinDisplacement(bpy.types.Operator):
    """
    Calculate and apply the skin displacement
    """
    bl_label = 'Обновить смещение'
    bl_idname = 'mbast.skindisplace_calculate'
    bl_description = 'Рассчитать и применить детали скина, используя модификатор смещения'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        """
        Calculate and apply the skin displacement
        """
        global mblab_humanoid
        scn = bpy.context.scene
        mblab_humanoid.update_displacement()
        mblab_humanoid.update_materials()
        return {'FINISHED'}


class DisableSubdivision(bpy.types.Operator):
    """
    Disable subdivision surface
    """
    bl_label = 'Отключить в пред просмотре модификатор subdivision'
    bl_idname = 'mbast.subdivision_disable'
    bl_description = 'Отключить модификатор subdivision'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global mblab_humanoid
        scn = bpy.context.scene

        if mblab_humanoid.get_subd_visibility() == True:
            mblab_humanoid.set_subd_visibility(False)
        return {'FINISHED'}


class EnableSubdivision(bpy.types.Operator):
    """
    Enable subdivision surface
    """
    bl_label = 'Включить в пред просмотре модификатор subdivision'
    bl_idname = 'mbast.subdivision_enable'
    bl_description = 'Включить модификатор subdivision (Внимание: это замедлит морфинг)'
# Примечание #морфинг# можно заменить на #прорисовку#
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global mblab_humanoid
        scn = bpy.context.scene

        if mblab_humanoid.get_subd_visibility() == False:
            mblab_humanoid.set_subd_visibility(True)
        return {'FINISHED'}


class DisableSmooth(bpy.types.Operator):
    bl_label = 'Отключить корректирующее сглаживание'
    bl_idname = 'mbast.corrective_disable'
    bl_description = 'Отключить в пред просмотре корректирующее сглаживание'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global mblab_humanoid
        scn = bpy.context.scene

        if mblab_humanoid.get_smooth_visibility() == True:
            mblab_humanoid.set_smooth_visibility(False)
        return {'FINISHED'}


class EnableSmooth(bpy.types.Operator):
    bl_label = 'Включить корректирующее сглаживание'
    bl_idname = 'mbast.corrective_enable'
    bl_description = 'Включить в пред просмотре корректирующее сглаживание'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global mblab_humanoid
        scn = bpy.context.scene

        if mblab_humanoid.get_smooth_visibility() == False:
            mblab_humanoid.set_smooth_visibility(True)
        return {'FINISHED'}


class DisableDisplacement(bpy.types.Operator):
    """
    Disable displacement modifier
    """
    bl_label = 'Отключить в пред просмотре смещение'
    bl_idname = 'mbast.displacement_disable'
    bl_description = 'Отключить в пред просмотре модификатор смещение'
# Примечание смещение можно заменить на сглаживание
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global mblab_humanoid
        scn = bpy.context.scene

        if mblab_humanoid.get_disp_visibility() == True:
            mblab_humanoid.set_disp_visibility(False)
        return {'FINISHED'}


class EnableDisplacement(bpy.types.Operator):
    """
    Enable displacement modifier
    """
    bl_label = 'Включить в пред просмотре смещение'
    bl_idname = 'mbast.displacement_enable'
    bl_description = 'Включить в пред просмотре модификатор смещение(Внимание: это замедлит морфинг)'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global mblab_humanoid
        scn = bpy.context.scene

        if mblab_humanoid.get_disp_visibility() == False:
            mblab_humanoid.set_disp_visibility(True)
        return {'FINISHED'}


class ButtonAddParticleHair(bpy.types.Operator):
    bl_label = 'Инструменты'
    bl_idname = 'mbast.button_utilities_on'
    bl_description = 'Открыть панель инструментов'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel_fin
        gui_active_panel_fin = "utilities"
        return {'FINISHED'}


class FinalizeCharacterAndImages(bpy.types.Operator, ExportHelper):
    """
        Convert the character in a standard Blender model
    """
    bl_label = 'Финализация с текстурами и резервным копированием'
    bl_idname = 'mbast.finalize_character_and_images'
    filename_ext = ".png"
    filter_glob: bpy.props.StringProperty(default="*.png", options={'HIDDEN'},)
    bl_description = 'Завершение, сохранение всех текстур и преобразование параметров в ключи формы. Предупреждение: после преобразования персонаж больше не будет изменяться с помощью инструментов MB-Lab'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):

        global mblab_humanoid
        global gui_status
        # TODO unique function in humanoid class
        scn = bpy.context.scene
        armature = mblab_humanoid.get_armature()

        mblab_humanoid.correct_expressions(correct_all=True)

        if not utils.is_ik_armature(armature):
            mblab_humanoid.set_rest_pose()
        if scn.mblab_remove_all_modifiers:
            mblab_humanoid.remove_modifiers()

        mblab_humanoid.sync_internal_data_with_mesh()
        mblab_humanoid.update_displacement()
        mblab_humanoid.update_materials()
        mblab_humanoid.save_backup_character(self.filepath)
        mblab_humanoid.save_all_textures(self.filepath)

        mblab_humanoid.morph_engine.convert_all_to_blshapekeys()
        mblab_humanoid.delete_all_properties()
        mblab_humanoid.rename_materials(scn.mblab_final_prefix)
        mblab_humanoid.update_bendy_muscles()
        mblab_humanoid.rename_obj(scn.mblab_final_prefix)
        mblab_humanoid.rename_armature(scn.mblab_final_prefix)
        gui_status = "NEW_SESSION"
        return {'FINISHED'}


class FinalizeCharacter(bpy.types.Operator):
    """
    Convert the character in a standard Blender model
    """
    bl_label = 'Финализация'
    bl_idname = 'mbast.finalize_character'
    bl_description = 'Завершить преобразование параметров в ключах формы. Предупреждение: после преобразования персонаж больше не будет изменяться с помощью инструментов MB-Lab'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):

        global mblab_humanoid
        global gui_status
        scn = bpy.context.scene
        armature = mblab_humanoid.get_armature()

        mblab_humanoid.correct_expressions(correct_all=True)

        if not utils.is_ik_armature(armature):
            mblab_humanoid.set_rest_pose()
        if scn.mblab_remove_all_modifiers:
            mblab_humanoid.remove_modifiers()

        mblab_humanoid.sync_internal_data_with_mesh()

        mblab_humanoid.morph_engine.convert_all_to_blshapekeys()
        mblab_humanoid.update_displacement()
        mblab_humanoid.update_materials()

        mblab_humanoid.delete_all_properties()
        mblab_humanoid.rename_materials(scn.mblab_final_prefix)
        mblab_humanoid.update_bendy_muscles()
        mblab_humanoid.rename_obj(scn.mblab_final_prefix)
        mblab_humanoid.rename_armature(scn.mblab_final_prefix)

        gui_status = "NEW_SESSION"
        return {'FINISHED'}


class ResetParameters(bpy.types.Operator):
    """Reset all morphings."""
    bl_label = 'Сброс персонажа'
    bl_idname = 'mbast.reset_allproperties'
    bl_description = 'Сброс всех параметров персонажа'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    def execute(self, context):
        global mblab_humanoid
        mblab_humanoid.reset_character()
        return {'FINISHED'}


class ResetExpressions(bpy.types.Operator):
    """Reset all morphings."""
    bl_label = 'Сброс выражений'
    bl_idname = 'mbast.reset_expression'
    bl_description = 'Сброс выражий персонажа'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    def execute(self, context):
        global mblab_shapekeys
        mblab_shapekeys.reset_expressions_gui()
        return {'FINISHED'}


# class LoadAssets(bpy.types.Operator):
# """
# Load assets from library
# """
# bl_label = 'Load model from assets library'
# bl_idname = 'mbast.load_assets_element'
# bl_description = 'Load the element selected from the assets library'
# bl_context = 'objectmode'
# bl_options = {'REGISTER', 'INTERNAL','UNDO'}

# def execute(self, context):
# scn = bpy.context.scene
# mblab_proxy.load_asset(scn.mblab_assets_models)
# return {'FINISHED'}


class InsertExpressionKeyframe(bpy.types.Operator):
    """Reset all morphings."""
    bl_label = 'Вставить ключевой кадр'
    bl_idname = 'mbast.keyframe_expression'
    bl_description = 'Вставить выражение в текущее время ключевого кадра'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    def execute(self, context):
        global mblab_shapekeys
        mblab_shapekeys.keyframe_expression()
        return {'FINISHED'}


class Reset_category(bpy.types.Operator):
    """Reset the parameters for the currently selected category"""
    bl_label = 'Сбросить категорию'
    bl_idname = 'mbast.reset_categoryonly'
    bl_description = 'Сбросить все параметры текущей категории'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    def execute(self, context):
        global mblab_humanoid
        scn = bpy.context.scene
        mblab_humanoid.reset_category(scn.morphingCategory)
        return {'FINISHED'}


class CharacterGenerator(bpy.types.Operator):
    """Generate a new character using the specified parameters"""
    bl_label = 'Генератор'
    bl_idname = 'mbast.character_generator'
    bl_description = 'Генерация нового персонажа по параметрам.'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    def execute(self, context):
        global mblab_humanoid
        scn = bpy.context.scene
        rnd_values = {"LI": 0.05, "RE": 0.1, "NO": 0.2, "CA": 0.3, "EX": 0.5}
        rnd_val = rnd_values[scn.mblab_random_engine]
        p_face = scn.mblab_preserve_face
        p_body = scn.mblab_preserve_body
        p_mass = scn.mblab_preserve_mass
        p_tone = scn.mblab_preserve_tone
        p_height = scn.mblab_preserve_height
        p_phenotype = scn.mblab_preserve_phenotype
        set_tone_mass = scn.mblab_set_tone_and_mass
        b_tone = scn.mblab_body_tone
        b_mass = scn.mblab_body_mass
        p_fantasy = scn.mblab_preserve_fantasy

        mblab_humanoid.generate_character(rnd_val, p_face, p_body, p_mass, p_tone,
                                          p_height, p_phenotype, set_tone_mass, b_mass, b_tone, p_fantasy)
        return {'FINISHED'}


class ExpDisplacementImage(bpy.types.Operator, ExportHelper):
    """Export texture maps for the character"""
    bl_idname = "mbast.export_dispimage"
    bl_label = "Сохранить карту нормалий (смещений)"
    filename_ext = ".png"
    filter_glob: bpy.props.StringProperty(
        default="*.png",
        options={'HIDDEN'},
    )
    bl_context = 'objectmode'

    def execute(self, context):
        global mblab_humanoid
        mblab_humanoid.save_body_displacement_texture(self.filepath)
        return {'FINISHED'}


class ExpDermalImage(bpy.types.Operator, ExportHelper):
    """Export texture maps for the character"""
    bl_idname = "mbast.export_dermimage"
    bl_label = "Сохранить карту кожи"
    filename_ext = ".png"
    filter_glob: bpy.props.StringProperty(
        default="*.png",
        options={'HIDDEN'},
    )
    bl_context = 'objectmode'

    def execute(self, context):
        global mblab_humanoid
        mblab_humanoid.save_body_dermal_texture(self.filepath)
        return {'FINISHED'}


class ExpAllImages(bpy.types.Operator, ExportHelper):
    """Export all texture maps for the character"""
    bl_idname = "mbast.export_allimages"
    bl_label = "Экспорт всех карт"
    filename_ext = ".png"
    filter_glob: bpy.props.StringProperty(
        default="*.png",
        options={'HIDDEN'},
    )
    bl_context = 'objectmode'

    def execute(self, context):
        global mblab_humanoid
        mblab_humanoid.save_all_textures(self.filepath)
        return {'FINISHED'}


class ExpCharacter(bpy.types.Operator, ExportHelper):
    """Export parameters for the character"""
    bl_idname = "mbast.export_character"
    bl_label = "Экспорт персонажа"
    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(
        default="*.json",
        options={'HIDDEN'},
    )
    bl_context = 'objectmode'

    def execute(self, context):
        global mblab_humanoid
        scn = bpy.context.scene
        mblab_humanoid.save_character(self.filepath, scn.mblab_export_proportions, scn.mblab_export_materials)
        return {'FINISHED'}


class ExpMeasures(bpy.types.Operator, ExportHelper):
    """Export parameters for the character"""
    bl_idname = "mbast.export_measures"
    bl_label = "Экспорт размеров"
    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(
        default="*.json",
        options={'HIDDEN'},
    )
    bl_context = 'objectmode'

    def execute(self, context):
        global mblab_humanoid
        mblab_humanoid.export_measures(self.filepath)
        return {'FINISHED'}


class ImpCharacter(bpy.types.Operator, ImportHelper):
    """Import parameters for the character"""
    bl_idname = "mbast.import_character"
    bl_label = "Импорт персонажа"
    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(
        default="*.json",
        options={'HIDDEN'},
    )
    bl_context = 'objectmode'

    def execute(self, context):
        global mblab_humanoid

        char_data = mblab_humanoid.load_character(self.filepath)
        return {'FINISHED'}


class ImpMeasures(bpy.types.Operator, ImportHelper):
    """Import parameters for the character"""
    bl_idname = "mbast.import_measures"
    bl_label = "Импорт размеров"
    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(
        default="*.json",
        options={'HIDDEN'},
    )
    bl_context = 'objectmode'

    def execute(self, context):
        global mblab_humanoid
        mblab_humanoid.import_measures(self.filepath)
        return {'FINISHED'}


class LoadDermImage(bpy.types.Operator, ImportHelper):
    """Import texture maps for the character"""
    bl_idname = "mbast.import_dermal"
    bl_label = "Загрузить карту кожи"
    filename_ext = ".png"
    filter_glob: bpy.props.StringProperty(
        default="*.png",
        options={'HIDDEN'},
    )
    bl_context = 'objectmode'

    def execute(self, context):
        global mblab_humanoid
        mblab_humanoid.load_body_dermal_texture(self.filepath)
        return {'FINISHED'}


class LoadDispImage(bpy.types.Operator, ImportHelper):
    """Import texture maps for the character"""
    bl_idname = "mbast.import_displacement"
    bl_label = "Загрузить карту нормалей"
    filename_ext = ".png"
    filter_glob: bpy.props.StringProperty(
        default="*.png",
        options={'HIDDEN'},
    )
    bl_context = 'objectmode'

    def execute(self, context):
        global mblab_humanoid
        mblab_humanoid.load_body_displacement_texture(self.filepath)
        return {'FINISHED'}


class FitProxy(bpy.types.Operator):
    bl_label = 'Выбрать прокси'
    bl_idname = 'mbast.proxy_fit'
    bl_description = 'Установить выбранный прокси для персонажа'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        scn = bpy.context.scene
        offset = scn.mblab_proxy_offset / 1000
        threshold = scn.mblab_proxy_threshold / 1000
        mblab_proxy.fit_proxy_object(offset, threshold, scn.mblab_add_mask_group, scn.mblab_transfer_proxy_weights)
        return {'FINISHED'}


class RemoveProxy(bpy.types.Operator):
    bl_label = 'Удалить фитинг'
    bl_idname = 'mbast.proxy_removefit'
    bl_description = 'Снятие фитинга, чтобы прокси-сервер можно было изменить, а затем снова установить.'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        scn = bpy.context.scene
        mblab_proxy.remove_fitting()
        return {'FINISHED'}


class ApplyMeasures(bpy.types.Operator):
    """Fit the character to the measures"""

    bl_label = 'Обновить персонажа'
    bl_idname = 'mbast.measures_apply'
    bl_description = 'Подгоняет персонаж к размерам'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global mblab_humanoid
        mblab_humanoid.automodelling(use_measures_from_GUI=True)
        return {'FINISHED'}


class AutoModelling(bpy.types.Operator):
    """Fit the character to the measures"""

    bl_label = 'Авто моделирование'
    bl_idname = 'mbast.auto_modelling'
    bl_description = 'Анализ мэша для создания правдоподобности человека'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    def execute(self, context):
        global mblab_humanoid
        mblab_humanoid.automodelling(use_measures_from_current_obj=True)
        return {'FINISHED'}


class AutoModellingMix(bpy.types.Operator):
    """Fit the character to the measures"""

    bl_label = 'Усредненное авто моделирование'
    bl_idname = 'mbast.auto_modelling_mix'
    bl_description = 'Создает правдоподобного человека с несколькими интерполяциями приближенными к средним'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    def execute(self, context):
        global mblab_humanoid
        mblab_humanoid.automodelling(use_measures_from_current_obj=True, mix=True)
        return {'FINISHED'}


class SaveRestPose(bpy.types.Operator, ExportHelper):
    """Export pose"""
    bl_idname = "mbast.restpose_save"
    bl_label = "Сохранить позу покоя"
    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(
        default="*.json",
        options={'HIDDEN'},
    )
    bl_context = 'objectmode'

    def execute(self, context):
        global mblab_humanoid
        armature = mblab_humanoid.get_armature()
        mblab_retarget.save_pose(armature, self.filepath)
        return {'FINISHED'}


class LoadRestPose(bpy.types.Operator, ImportHelper):
    """Import parameters for the character"""
    bl_idname = "mbast.restpose_load"
    bl_label = "Загрузить позу покоя"
    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(
        default="*.json",
        options={'HIDDEN'},
    )
    bl_context = 'objectmode'

    def execute(self, context):
        global mblab_humanoid, mblab_retarget
        armature = mblab_humanoid.get_armature()
        mblab_retarget.load_pose(self.filepath, armature, use_retarget=False)
        return {'FINISHED'}


class SavePose(bpy.types.Operator, ExportHelper):
    """Export pose"""
    bl_idname = "mbast.pose_save"
    bl_label = "Сохранить позу"
    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(
        default="*.json",
        options={'HIDDEN'},
    )
    bl_context = 'objectmode'

    def execute(self, context):
        global mblab_humanoid
        armature = utils.get_active_armature()
        mblab_retarget.save_pose(armature, self.filepath)
        return {'FINISHED'}

class ButtonLoadBvhAdjusments(bpy.types.Operator, ImportHelper):
    """Import bvh settings for the character"""
    bl_idname = "mbast.button_load_bvh_adjustments"
    bl_label = "Загрузить BVH конфигурацию костей"
    filename_ext = ".json"
    bl_description = 'Импорт файла json, содержащего настройки анимации bvh'
    filter_glob: bpy.props.StringProperty(
        default="*.json",
        options={'HIDDEN'},
    )
    bl_context = 'objectmode'

    def execute(self, context):
        global mblab_humanoid
        global mblab_retarget
        scn = bpy.context.scene
        armature = utils.get_active_armature()
        matrix_data = algorithms.load_json_data(self.filepath, "BVH config")
        # Loop Through Config Adjustments and Apply Changes
        for bone in matrix_data:
            armature.data.bones[bone].select = True
            rot_x = matrix_data[bone][0]
            rot_y = matrix_data[bone][1]
            rot_z = matrix_data[bone][2]
            mblab_retarget.correct_bone_angle(0, rot_x)
            mblab_retarget.correct_bone_angle(1, rot_y)
            mblab_retarget.correct_bone_angle(2, rot_z)
            armature.data.bones[bone].select = False
        return {'FINISHED'}

class ButtonSaveBvhAdjustments(bpy.types.Operator, ExportHelper):
    bl_idname = 'mbast.button_save_bvh_adjustments'
    bl_label = 'Созранить BVH конфигурацию костей'
    bl_description = 'Сохранить исправления костей в json файл'
    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(
        default="*.json",
        options={'HIDDEN'},
    )
    bl_context = 'objectmode'

    def execute(self, context):
        scn = bpy.context.scene
        selected_bone = mblab_retarget.get_selected_posebone().name

        if mblab_retarget.rot_type in ["EULER", "QUATERNION"]:
            offsets = mblab_retarget.get_offset_values()
            saveBone = []
            saveBone.append(offsets[0])
            saveBone.append(offsets[1])
            saveBone.append(offsets[2])
            dict = { selected_bone: saveBone }

            if os.path.exists(self.filepath):
                with open(self.filepath, 'r+') as f:
                    bones = json.load(f)
                    # Update Json
                    bones[selected_bone] = saveBone
                    f.seek(0)
                    f.truncate()
                    json.dump(bones, f)
            else:
                data = json.dumps(dict, indent=1, ensure_ascii=True)
                with open(self.filepath, 'w') as outfile:
                    outfile.write(data + '\n')

        return {'FINISHED'}


class LoadPose(bpy.types.Operator, ImportHelper):
    """Import parameters for the character"""
    bl_idname = "mbast.pose_load"
    bl_label = "Загрузить позу"
    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(
        default="*.json",
        options={'HIDDEN'},
    )
    bl_context = 'objectmode'

    def execute(self, context):
        global mblab_retarget
        mblab_retarget.load_pose(self.filepath, use_retarget=True)
        return {'FINISHED'}


class ResetPose(bpy.types.Operator):
    """Import parameters for the character"""
    bl_idname = "mbast.pose_reset"
    bl_label = "Сбросить позу"
    bl_context = 'objectmode'
    bl_description = 'Сбросить углы арматурных костей'
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    def execute(self, context):
        global mblab_retarget
        mblab_retarget.reset_pose()
        return {'FINISHED'}


class LoadBvh(bpy.types.Operator, ImportHelper):
    """Import parameters for the character"""
    bl_idname = "mbast.load_animation"
    bl_label = "Загрузить анимацию (bvh)"
    filename_ext = ".bvh"
    bl_description = 'Импортировать анимацию из файла движений bvh'
    filter_glob: bpy.props.StringProperty(
        default="*.bvh",
        options={'HIDDEN'},
    )
    bl_context = 'objectmode'

    def execute(self, context):
        global mblab_retarget
        mblab_retarget.load_animation(self.filepath)
        return {'FINISHED'}


class CreateFaceRig(bpy.types.Operator):
    bl_idname = "mbast.create_face_rig"
    bl_label = "Создать Face Rig (одежду)"
    bl_description = "Создание лица (одежды) персонажа"
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    def execute(self, context):
        mblab_shapekeys.update_expressions_data()
        if mblab_shapekeys.model_type != "NONE":
            obj = algorithms.get_active_body()
            rc = facerig.setup_face_rig(obj)
            if not rc:
                self.report({'ERROR'},
                            "Face Rig creation process failed")
                return {'FINISHED'}
            elif bpy.context.scene.mblab_facs_rig:
                rc = facerig.setup_facs_rig(obj)
                if not rc:
                    self.report({'ERROR'},
                                "FACS Rig creation process failed")
                    return {'FINISHED'}
        else:
            self.report({'ERROR'},
                        "Select finalized MB-Lab character to create face rig")
        return {'FINISHED'}


class DeleteFaceRig(bpy.types.Operator):
    bl_idname = "mbast.delete_face_rig"
    bl_label = "Удаление Face Rig"
    bl_description = "Удаление лица (одежды) персонажа"
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    def execute(self, context):
        mblab_shapekeys.update_expressions_data()
        obj = algorithms.get_active_object()
        if not obj:
            self.report({'ERROR'}, "Select Face Rig to delete")
            return {'FINISHED'}

        if not facerig.delete_face_rig(obj):
            self.report({'ERROR'}, "failed to delete face rig")
        return {'FINISHED'}

class OBJECT_OT_humanoid_rot_limits(bpy.types.Operator):
    """Add Humanoid Rotation Limits to Character"""
    bl_idname = "mbast.humanoid_rot_limits"
    bl_label = "Создать вращение человека"
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    def execute(self, context):
        armature = humanoid_rotations.get_skeleton()
        pb = armature.pose.bones
        humanoid_rotations.limit_bone_rotation(humanoid_rotations.ragdoll_dict, pb)
        humanoid_rotations.limit_finger_rotation(humanoid_rotations.fd, pb)
        return {'FINISHED'}

class OBJECT_OT_delete_rotations(bpy.types.Operator):
    """Delete Humanoid Rotation Limits for Character"""
    bl_idname = "mbast.delete_rotations"
    bl_label = "Удалить вращение человека"
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    def execute(self, context):
        armature = humanoid_rotations.get_skeleton()
        pb = armature.pose.bones
        humanoid_rotations.remove_bone_constraints('LIMIT_ROTATION', pb)
        return {'FINISHED'}

class StartSession(bpy.types.Operator):
    bl_idname = "mbast.init_character"
    bl_label = "Создание персонажа"
    bl_description = 'Создание персонажа, выбранного выше'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    def execute(self, context):
        start_lab_session()
        return {'FINISHED'}


class LoadTemplate(bpy.types.Operator):
    bl_idname = "mbast.load_base_template"
    bl_label = "Импорт шаблона"
    bl_description = 'Импорт шаблона гуманоида для ссылки на прокси'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    def execute(self, context):
        global mblab_humanoid
        scn = bpy.context.scene
        lib_filepath = algorithms.get_blendlibrary_path()
        base_model_name = mblab_humanoid.characters_config[scn.mblab_template_name]["template_model"]
        obj = algorithms.import_object_from_lib(lib_filepath, base_model_name, scn.mblab_template_name)
        if obj:
            obj["manuellab_proxy_reference"] = mblab_humanoid.characters_config[scn.mblab_template_name][
                "template_model"]
        return {'FINISHED'}


class VIEW3D_PT_tools_ManuelbastioniLAB(bpy.types.Panel):
    bl_label = "MB-Lab {0}.{1}.{2}".format(bl_info["version"][0], bl_info["version"][1], bl_info["version"][2])
    bl_idname = "OBJECT_PT_characters01"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    # bl_context = 'objectmode'
    bl_category = "MB-Lab"

    @classmethod
    def poll(cls, context):
        return context.mode in {'OBJECT', 'POSE'}

    def draw(self, context):

        global mblab_humanoid, gui_status, gui_err_msg, gui_active_panel
        scn = bpy.context.scene
        icon_expand = "DISCLOSURE_TRI_RIGHT"
        icon_collapse = "DISCLOSURE_TRI_DOWN"

        box_info = self.layout.box()
        box_info.label(text="https://github.com/animate1978/MB-Lab")

        if gui_status == "ERROR_SESSION":
            box_err = self.layout.box()
            box_err.label(text=gui_err_msg, icon="INFO")

        if gui_status == "NEW_SESSION":

            self.layout.label(text="Опции создания", icon='RNA_ADD')
            box_new_opt = self.layout.box()
            box_new_opt.prop(scn, 'mblab_character_name')

            if mblab_humanoid.is_ik_rig_available(scn.mblab_character_name):
                box_new_opt.prop(scn, 'mblab_use_ik', icon='BONE_DATA')
            if mblab_humanoid.is_muscle_rig_available(scn.mblab_character_name):
                box_new_opt.prop(scn, 'mblab_use_muscle', icon='BONE_DATA')

            box_new_opt.prop(scn, 'mblab_use_cycles', icon='SHADING_RENDERED')
            box_new_opt.prop(scn, 'mblab_use_eevee', icon='SHADING_RENDERED')
            if scn.mblab_use_cycles or scn.mblab_use_eevee:
                box_new_opt.prop(scn, 'mblab_use_lamps', icon='LIGHT_DATA')
            box_new_opt.operator('mbast.init_character', icon='ARMATURE_DATA')

        if gui_status != "ACTIVE_SESSION":
            self.layout.label(text=" ")
            self.layout.label(text="Инструменты после создания", icon='MODIFIER_ON')

            box_post_opt = self.layout.box()
            # Face Rig
            box_face_rig = box_post_opt.box()
            box_face_rig.label(text="Face Rig")
            box_face_rig.operator('mbast.create_face_rig', icon='USER')
            box_face_rig.operator('mbast.delete_face_rig', icon='CANCEL')
            box_face_rig.prop(scn, "mblab_facs_rig")

            # Humanoid Rotation Limits
            box = self.layout.box()
            box.label(text="Вращения персонажа")
            box.operator("mbast.humanoid_rot_limits", icon='USER')
            box.operator('mbast.delete_rotations', icon='CANCEL')
            box = self.layout.box()


            if gui_active_panel_fin != "expressions":
                box_post_opt.operator('mbast.button_expressions_on', icon=icon_expand)
            else:
                box_post_opt.operator('mbast.button_expressions_off', icon=icon_collapse)
                box_exp = box_post_opt.box()
                mblab_shapekeys.update_expressions_data()
                if mblab_shapekeys.model_type != "NONE":
                    box_exp.enabled = True
                    box_exp.prop(scn, 'mblab_expression_filter')
                    box_exp.operator("mbast.keyframe_expression", icon="ACTION")
                    if mblab_shapekeys.expressions_data:
                        obj = algorithms.get_active_body()
                        for expr_name in sorted(mblab_shapekeys.expressions_data.keys()):
                            if hasattr(obj, expr_name):
                                if scn.mblab_expression_filter in expr_name:
                                    box.prop(obj, expr_name)
                    box_exp.operator("mbast.reset_expression", icon="RECOVER_LAST")
                else:
                    box_exp.enabled = False
                    box_exp.label(text="No express. shapekeys", icon='INFO')

            if gui_active_panel_fin != "assets":
                box_post_opt.operator('mbast.button_assets_on', icon=icon_expand)
            else:
                box_post_opt.operator('mbast.button_assets_off', icon=icon_collapse)
                # assets_status = mblab_proxy.validate_assets_fitting()
                box_asts = box_post_opt.box()

                box_asts.prop(scn, 'mblab_proxy_library')
                box_asts.prop(scn, 'mblab_assets_models')
                # box.operator('mbast.load_assets_element')
                box_asts.label(text="To adapt the asset, use the proxy fitting tool", icon='INFO')


            if gui_active_panel_fin != "proxy_fit":
                box_post_opt.operator('mbast.button_proxy_fit_on', icon=icon_expand)
            else:
                box_post_opt.operator('mbast.button_proxy_fit_off', icon=icon_collapse)
                fitting_status, proxy_obj, reference_obj = mblab_proxy.get_proxy_fitting_ingredients()

                box_prox = box_post_opt.box()
                box_prox.label(text="Прокси фиттинг")
                box_prox.label(text="Выберите персонажа и прокси:")
                box_prox.prop(scn, 'mblab_fitref_name')
                box_prox.prop(scn, 'mblab_proxy_name')
                if fitting_status == "NO_REFERENCE":
                    # box_prox.enabled = False
                    box_prox.label(text="Персонаж не валиден.", icon="ERROR")
                    box_prox.label(text="Возможные причины:")
                    box_prox.label(text="- Персонаж, создан в другой версии лаборатории")
                    box_prox.label(text="- Топология персонажа, изменена с помощью пользовательского моделирования")
                    box_prox.label(text="- Топология персонажа, изменена модификаторами ..)")
                if fitting_status == "SAME_OBJECTS":
                    box_prox.label(text="Прокси и персонаж не могут быть одним и тем же объектом", icon="ERROR")
                if fitting_status == "CHARACTER_NOT_FOUND":
                    box_prox.label(text="Персонаж не найден", icon="ERROR")
                if fitting_status == "PROXY_NOT_FOUND":
                    box_prox.label(text="Прокси не найден", icon="ERROR")
                if fitting_status == 'OK':
                    box_prox.label(text="Прокси готов к установке.", icon="INFO")
                    proxy_compatib = mblab_proxy.validate_assets_compatibility(proxy_obj, reference_obj)

                    if proxy_compatib == "WARNING":
                        box_prox.label(text="Прокси, похоже, не предназначен для выбранного персонажа.", icon="ERROR")

                    box_prox.prop(scn, 'mblab_proxy_offset')
                    box_prox.prop(scn, 'mblab_proxy_threshold')
                    box_prox.prop(scn, 'mblab_add_mask_group')
                    box_prox.prop(scn, 'mblab_transfer_proxy_weights')
                    box_prox.operator("mbast.proxy_fit", icon="MOD_CLOTH")
                    box_prox.operator("mbast.proxy_removefit", icon="MOD_CLOTH")
                if fitting_status == 'WRONG_SELECTION':
                    box_prox.enabled = False
                    box_prox.label(text="Пожалуйста, выберите только два объекта: гуманоид и прокси", icon="INFO")
                if fitting_status == 'NO_REFERENCE_SELECTED':
                    box_prox.enabled = False
                    box_prox.label(text="Не правильно выбран шаблон гуманоида", icon="INFO")
                if fitting_status == 'NO_MESH_SELECTED':
                    box_prox.enabled = False
                    box_prox.label(text="Выбранный прокси не является сеткой", icon="INFO")

            if gui_active_panel_fin != "pose":
                box_post_opt.operator('mbast.button_pose_on', icon=icon_expand)
            else:
                box_post_opt.operator('mbast.button_pose_off', icon=icon_collapse)
                box_pose = box_post_opt.box()

                armature = utils.get_active_armature()
                if armature is not None and not utils.is_ik_armature(armature):
                    box_pose.enabled = True
                    sel_gender = algorithms.get_selected_gender()
                    if sel_gender == "FEMALE":
                        if mblab_retarget.femaleposes_exist:
                            box_pose.prop(armature, "female_pose")
                    if sel_gender == "MALE":
                        if mblab_retarget.maleposes_exist:
                            box_pose.prop(armature, "male_pose")
                    box_pose.operator("mbast.pose_load", icon='IMPORT')
                    box_pose.operator("mbast.pose_save", icon='EXPORT')
                    box_pose.operator("mbast.pose_reset", icon='ARMATURE_DATA')
                    box_pose.operator("mbast.load_animation", icon='IMPORT')
                else:
                    box_pose.enabled = False
                    box_pose.label(text="Please select the lab character (IK not supported)", icon='INFO')

            if gui_active_panel_fin != "utilities":
                box_post_opt.operator('mbast.button_utilities_on', icon=icon_expand)
            else:
                box_post_opt.operator('mbast.button_utilities_off', icon=icon_collapse)

                box_util_prox = box_post_opt.box()
                box_util_prox.label(text="Выберите ссылку на прокси")
                box_util_prox.prop(scn, 'mblab_template_name')
                box_util_prox.operator('mbast.load_base_template')

                box_util_bvh = box_post_opt.box()
                box_util_bvh.label(text="Не правильные кости персонажа")
                box_util_bvh.operator('mbast.button_adjustrotation', icon='BONE_DATA')
                box_util_bvh.operator('mbast.button_save_bvh_adjustments', icon='EXPORT')
                box_util_bvh.operator('mbast.button_load_bvh_adjustments', icon='IMPORT')
                mblab_retarget.check_correction_sync()
                if mblab_retarget.is_animated_bone == "VALID_BONE":
                    if mblab_retarget.correction_is_sync:
                        box_util_bvh.prop(scn, 'mblab_rot_offset_0')
                        box_util_bvh.prop(scn, 'mblab_rot_offset_1')
                        box_util_bvh.prop(scn, 'mblab_rot_offset_2')
                else:
                    box_util_bvh.label(text=mblab_retarget.is_animated_bone)

        if gui_status == "ACTIVE_SESSION":
            obj = mblab_humanoid.get_object()
            armature = mblab_humanoid.get_armature()
            if obj and armature:
                self.layout.label(text="Инструменты создания", icon="RNA")
                box_act_opt = self.layout.box()

                if mblab_humanoid.exists_transform_database():
                    x_age = getattr(obj, 'character_age', 0)
                    x_mass = getattr(obj, 'character_mass', 0)
                    x_tone = getattr(obj, 'character_tone', 0)
                    age_lbl = round((15.5 * x_age ** 2) + 31 * x_age + 33)
                    mass_lbl = round(50 * (x_mass + 1))
                    tone_lbl = round(50 * (x_tone + 1))
                    lbl_text = "Age : {0} yr.  Mass : {1}%  Tone : {2}% ".format(age_lbl, mass_lbl, tone_lbl)
                    box_act_opt.label(text=lbl_text)

                    for meta_data_prop in sorted(mblab_humanoid.character_metaproperties.keys()):
                        if "last" not in meta_data_prop:
                            box_act_opt.prop(obj, meta_data_prop)
                    box_act_opt.operator("mbast.reset_allproperties", icon="RECOVER_LAST")

                    #if mblab_humanoid.get_subd_visibility() == True:
                        #self.layout.label(text="Совет: для медленного ПК отключите подразделы в опциях ниже", icon='INFO')

                if gui_active_panel != "library":
                    box_act_opt.operator('mbast.button_library_on', icon=icon_expand)
                else:
                    box_act_opt.operator('mbast.button_library_off', icon=icon_collapse)
                    box_lib = box_act_opt.box()

                    box_lib.label(text="Библиотека персонажей", icon='ARMATURE_DATA')
                    if mblab_humanoid.exists_preset_database():
                        box_lib.prop(obj, "preset")
                    if mblab_humanoid.exists_phenotype_database():
                        box_lib.prop(obj, "ethnic")
                    box_lib.prop(scn, 'mblab_mix_characters', icon='FORCE_CHARGE')

                if gui_active_panel != "random":
                    box_act_opt.operator('mbast.button_random_on', icon=icon_expand)
                else:
                    box_act_opt.operator('mbast.button_random_off', icon=icon_collapse)

                    box_rand = box_act_opt.box()
                    box_rand.prop(scn, "mblab_random_engine")
                    box_rand.prop(scn, "mblab_set_tone_and_mass")
                    if scn.mblab_set_tone_and_mass:
                        box_rand.prop(scn, "mblab_body_mass")
                        box_rand.prop(scn, "mblab_body_tone")

                    box_rand.label(text="Ограничения:")
                    box_rand.prop(scn, "mblab_preserve_mass")
                    box_rand.prop(scn, "mblab_preserve_height")
                    box_rand.prop(scn, "mblab_preserve_tone")
                    box_rand.prop(scn, "mblab_preserve_body")
                    box_rand.prop(scn, "mblab_preserve_face")
                    box_rand.prop(scn, "mblab_preserve_phenotype")
                    box_rand.prop(scn, "mblab_preserve_fantasy")

                    box_rand.operator('mbast.character_generator', icon="FILE_REFRESH")

                if gui_active_panel != "parameters":
                    box_act_opt.operator('mbast.button_parameters_on', icon=icon_expand)
                else:
                    box_act_opt.operator('mbast.button_parameters_off', icon=icon_collapse)

                    box_param = box_act_opt.box()
                    mblab_humanoid.bodydata_realtime_activated = True
                    if mblab_humanoid.exists_measure_database():
                        box_param.prop(scn, 'mblab_show_measures', icon='SNAP_INCREMENT')
                    split = box_param.split()

                    col = split.column()
                    col.label(text="Парметры")
                    col.prop(scn, "morphingCategory")

                    for prop in mblab_humanoid.get_properties_in_category(scn.morphingCategory):
                        if hasattr(obj, prop):
                            col.prop(obj, prop)

                    if mblab_humanoid.exists_measure_database() and scn.mblab_show_measures:
                        col = split.column()
                        col.label(text="Размеры")
                        #col.label(text="Экспериментальное", icon='ERROR')
                        col.prop(obj, 'mblab_use_inch')
                        col.prop(scn, 'mblab_measure_filter')
                        col.operator("mbast.measures_apply", icon='FILE_REFRESH')

                        if obj.mblab_use_inch:
                            a_inch = getattr(obj, "body_height_Z", 0)
                            m_feet = int(a_inch / 12)
                            m_inch = int(a_inch % 12)
                            col.label(text="Высота (рост): {0}ft {1}in ({2}in)".format(m_feet, m_inch, round(a_inch, 3)))
                        else:
                            col.label(text="Высота (рост): {0} cm".format(round(getattr(obj, "body_height_Z", 0), 3)))
                        for measure in sorted(mblab_humanoid.measures.keys()):
                            if measure != "body_height_Z":
                                if hasattr(obj, measure):
                                    if scn.mblab_measure_filter in measure:
                                        col.prop(obj, measure)

                        col.operator("mbast.export_measures", icon='EXPORT')
                        col.operator("mbast.import_measures", icon='IMPORT')

                    sub = box_param.box()
                    sub.label(text="Сброс")
                    sub.operator("mbast.reset_categoryonly", icon="RECOVER_LAST")

                if mblab_humanoid.exists_measure_database():
                    if gui_active_panel != "automodelling":
                        box_act_opt.operator('mbast.button_automodelling_on', icon=icon_expand)
                    else:
                        box_act_opt.operator('mbast.button_automodelling_off', icon=icon_collapse)
                        box_auto = box_act_opt.box()
                        box_auto.operator("mbast.auto_modelling", icon='OUTLINER_DATA_MESH')
                        box_auto.operator("mbast.auto_modelling_mix", icon='OUTLINER_OB_MESH')
                else:
                    box_auto = box_act_opt.box()
                    box_auto.enabled = False
                    box_auto.label(text="Автомоделирование не поддерживается этим персонажем", icon='INFO')

                if mblab_humanoid.exists_rest_poses_database():
                    if gui_active_panel != "rest_pose":
                        box_act_opt.operator('mbast.button_rest_pose_on', icon=icon_expand)
                    else:
                        box_act_opt.operator('mbast.button_rest_pose_off', icon=icon_collapse)
                        box_act_pose = box_act_opt.box()

                        if utils.is_ik_armature(armature):
                            box_act_pose.enabled = False
                            box_act_pose.label(text="Позы покоя недоступны для IK арматуры", icon='INFO')
                        else:
                            box_act_pose.enabled = True
                            box_act_pose.prop(armature, "rest_pose")

                            box_act_pose.operator("mbast.restpose_load", icon='IMPORT')
                            box_act_pose.operator("mbast.restpose_save", icon='EXPORT')

                if gui_active_panel != "skin":
                    box_act_opt.operator('mbast.button_skin_on', icon=icon_expand)
                else:
                    box_act_opt.operator('mbast.button_skin_off', icon=icon_collapse)

                    box_skin = box_act_opt.box()
                    box_skin.enabled = True
                    if scn.render.engine != 'CYCLES' and scn.render.engine != 'BLENDER_EEVEE':
                        box_skin.enabled = False
                        box_skin.label(text="Редактор скинов требует Cycles или EEVEE", icon='INFO')

                    if mblab_humanoid.exists_displace_texture():
                        box_skin.operator("mbast.skindisplace_calculate", icon='MOD_DISPLACE')
                        box_skin.label(text="Включить обновления при предосмотре", icon='INFO')

                    for material_data_prop in sorted(mblab_humanoid.character_material_properties.keys()):
                        box_skin.prop(obj, material_data_prop)

                if gui_active_panel != "finalize":
                    box_act_opt.operator('mbast.button_finalize_on', icon=icon_expand)
                else:
                    box_act_opt.operator('mbast.button_finalize_off', icon=icon_collapse)
                    box_fin = box_act_opt.box()
                    box_fin.prop(scn, 'mblab_save_images_and_backup', icon='EXPORT')
                    box_fin.prop(scn, 'mblab_remove_all_modifiers', icon='CANCEL')
                    box_fin.prop(scn, 'mblab_final_prefix')
                    if scn.mblab_save_images_and_backup:
                        box_fin.operator("mbast.finalize_character_and_images", icon='FREEZE')
                    else:
                        box_fin.operator("mbast.finalize_character", icon='FREEZE')

                if gui_active_panel != "file":
                    box_act_opt.operator('mbast.button_file_on', icon=icon_expand)
                else:
                    box_act_opt.operator('mbast.button_file_off', icon=icon_collapse)
                    box_file = box_act_opt.box()
                    box_file.prop(scn, 'mblab_show_texture_load_save', icon='TEXTURE')
                    if scn.mblab_show_texture_load_save:

                        if mblab_humanoid.exists_dermal_texture():
                            box_file_drtx = box_file.box()
                            box_file_drtx.label(text="Ткстуры кожи")
                            box_file_drtx.operator("mbast.export_dermimage", icon='EXPORT')
                            box_file_drtx.operator("mbast.import_dermal", icon='IMPORT')

                        if mblab_humanoid.exists_displace_texture():
                            box_file_dstx = box_file.box()
                            box_file_dstx.label(text="Текстуры смещения")
                            box_file_dstx.operator("mbast.export_dispimage", icon='EXPORT')
                            box_file_dstx.operator("mbast.import_displacement", icon='IMPORT')

                        box_file_exp = box_file.box()
                        box_file_exp.label(text="Экспортировать все изображения, используемые в шейдере скина")
                        box_file_exp.operator("mbast.export_allimages", icon='EXPORT')
                    box_file.prop(scn, 'mblab_export_proportions', icon='PRESET')
                    box_file.prop(scn, 'mblab_export_materials', icon='MATERIAL')
                    box_file.operator("mbast.export_character", icon='EXPORT')
                    box_file.operator("mbast.import_character", icon='IMPORT')


                if gui_active_panel != "display_opt":
                    box_act_opt.operator('mbast.button_display_on', icon=icon_expand)
                else:
                    box_act_opt.operator('mbast.button_display_off', icon=icon_collapse)
                    box_disp = box_act_opt.box()

                    if mblab_humanoid.exists_displace_texture():
                        if mblab_humanoid.get_disp_visibility() == False:
                            box_disp.operator("mbast.displacement_enable", icon='MOD_DISPLACE')
                        else:
                            box_disp.operator("mbast.displacement_disable", icon='X')
                    if mblab_humanoid.get_subd_visibility() == False:
                        box_disp.operator("mbast.subdivision_enable", icon='MOD_SUBSURF')
                        box_disp.label(text="Предварительный просмотр (модификатор subdivision) сильно загружает CPU", icon='INFO')
                    else:
                        box_disp.operator("mbast.subdivision_disable", icon='X')
                        box_disp.label(text="Отключить модификатор subdivision для повышения производительности", icon='ERROR')
                    if mblab_humanoid.get_smooth_visibility() == False:
                        box_disp.operator("mbast.corrective_enable", icon='MOD_SMOOTH')
                    else:
                        box_disp.operator("mbast.corrective_disable", icon='X')

                self.layout.label(text=" ")
                self.layout.label(text="Утилиты после создания", icon="MODIFIER_ON")
                self.layout.label(
                    text="FINALIZED characters ONLY", icon="INFO")

            else:
                gui_status = "NEW_SESSION"


classes = (
    ButtonParametersOff,
    ButtonParametersOn,
    ButtonUtilitiesOff,
    ButtonUtilitiesOn,
    ButtonExpressionsOff,
    ButtonExpressionOn,
    ButtonRandomOff,
    ButtonRandomOn,
    ButtonAutomodellingOff,
    ButtonAutomodellingOn,
    ButtoRestPoseOff,
    ButtonRestPoseOn,
    ButtoPoseOff,
    ButtonAssetsOn,
    ButtoAssetsOff,
    ButtonPoseOn,
    ButtonSkinOff,
    ButtonSkinOn,
    ButtonViewOptOff,
    ButtonViewOptOn,
    ButtonProxyFitOff,
    ButtonProxyFitOn,
    ButtonFilesOff,
    ButtonFilesOn,
    ButtonFinalizeOff,
    ButtonFinalizeOn,
    ButtonLibraryOff,
    ButtonLibraryOn,
    ButtonFinalizedCorrectRot,
    ButtonSaveBvhAdjustments,
    ButtonLoadBvhAdjusments,
    UpdateSkinDisplacement,
    DisableSubdivision,
    EnableSubdivision,
    DisableSmooth,
    EnableSmooth,
    DisableDisplacement,
    EnableDisplacement,
    FinalizeCharacterAndImages,
    FinalizeCharacter,
    ResetParameters,
    ResetExpressions,
    InsertExpressionKeyframe,
    Reset_category,
    CharacterGenerator,
    ExpDisplacementImage,
    ExpDermalImage,
    ExpAllImages,
    ExpCharacter,
    ExpMeasures,
    ImpCharacter,
    ImpMeasures,
    LoadDermImage,
    LoadDispImage,
    FitProxy,
    RemoveProxy,
    ApplyMeasures,
    AutoModelling,
    AutoModellingMix,
    SaveRestPose,
    LoadRestPose,
    SavePose,
    LoadPose,
    ResetPose,
    LoadBvh,
    StartSession,
    CreateFaceRig,
    DeleteFaceRig,
    LoadTemplate,
    preferences.MBPreferences,
    VIEW3D_PT_tools_ManuelbastioniLAB,
    OBJECT_OT_humanoid_rot_limits,
    OBJECT_OT_delete_rotations,
)

def register():
    # addon updater code and configurations
    # in case of broken version, try to register the updater first
    # so that users can revert back to a working version
    addon_updater_ops.register(bl_info)

    # register the example panel, to show updater buttons
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    # addon updater unregister
    addon_updater_ops.unregister()

    # register the example panel, to show updater buttons
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
