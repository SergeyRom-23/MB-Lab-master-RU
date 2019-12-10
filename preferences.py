# MB-Lab
#
# Сайт ветки MB-Lab: https://github.com/animate1978/MB-Lab
# Сайт ветки перевода на русский язык MB-Lab: https://github.com/SergeyRom-23/MB-Lab-master-RU
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

import bpy
from bpy.props import BoolProperty, IntProperty, EnumProperty, StringProperty
from . import addon_updater_ops


# demo bare-bones preferences
@addon_updater_ops.make_annotations
class MBPreferences(bpy.types.AddonPreferences):
    '''
    Updater preferences
    '''
    bl_idname = __package__
    # addon updater preferences
    auto_check_update = bpy.props.BoolProperty(
        name="Auto-check for Update",
        description="If enabled, auto-check for updates using an interval",
        default=False,
    )
    updater_intrval_months = bpy.props.IntProperty(
        name='Months',
        description="Number of months between checking for updates",
        default=0,
        min=0
    )
    updater_intrval_days = bpy.props.IntProperty(
        name='Days',
        description="Number of days between checking for updates",
        default=7,
        min=0,
        max=31
    )
    updater_intrval_hours = bpy.props.IntProperty(
        name='Hours',
        description="Number of hours between checking for updates",
        default=0,
        min=0,
        max=23
    )
    updater_intrval_minutes = bpy.props.IntProperty(
        name='Minutes',
        description="Number of minutes between checking for updates",
        default=0,
        min=0,
        max=59
    )

    def draw(self, context):
        layout = self.layout
        # col = layout.column() # works best if a column, or even just self.layout
        mainrow = layout.row()
        col = mainrow.column()

        # updater draw function
        addon_updater_ops.update_settings_ui(self, context)

        # Alternate draw function, which is more condensed and can be
        # placed within an existing draw function. Only contains:
        #   1) check for update/update now buttons
        #   2) toggle for auto-check (interval will be equal to what is set above)
        # addon_updater_ops.update_settings_ui_condensed(self, context, col)

        # Adding another column to help show the above condensed ui as one column
        # col = mainrow.column()
        # col.scale_y = 2
        # col.operator("wm.url_open","Open webpage ").url=addon_updater_ops.updater.website
