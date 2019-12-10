# MB-Lab
#
# Сайт ветки MB-Lab: https://github.com/animate1978/MB-Lab
# Сайт ветки перевода на русский язык MB-Lab: https://github.com/SergeyRom-23/MB-Lab-master-RU

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

import bpy


logger = logging.getLogger(__name__)


def get_object_parent(obj):
    if not obj:
        return None
    return getattr(obj, "parent", None)


def get_deforming_armature(obj):
    if obj.type == 'MESH':
        for modf in obj.modifiers:
            if modf.type == 'ARMATURE':
                return modf.object
    return None


def get_active_armature():
    active_obj = bpy.context.view_layer.objects.active
    parent_object = get_object_parent(active_obj)
    if active_obj:
        if active_obj.type == 'ARMATURE':
            return active_obj
        if active_obj.type == 'MESH':
            if parent_object:
                if parent_object.type == 'ARMATURE':
                    return parent_object
            else:
                deforming_armature = get_deforming_armature(active_obj)
                if deforming_armature:
                    return deforming_armature
    return None


def is_ik_armature(armature=None):
    if not armature:
        armature = get_active_armature()
        if armature and armature.type == 'ARMATURE':
            for b in armature.data.bones:
                if 'IK' in b.name:
                    return True
        elif armature and armature.type != 'ARMATURE':
            logger.warning("Cannot get the bones because the obj is not an armature")
            return False
    return False
