import io
import os
import tempfile
from datetime import datetime

import matplotlib
import matplotlib.pyplot as plt
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

matplotlib.use('Agg')


def safe_hex_color(color_code):
    """Безопасное создание цвета с дефолтным значением."""
    if not color_code:
        return HexColor('#CCCCCC')
    try:
        return HexColor(color_code)
    except:
        return HexColor('#CCCCCC')


def register_font():
    """Регистрация шрифтов для дашбордов."""
    try:
        font_paths = [
            "arial.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/times.ttf",
            "C:/Windows/Fonts/calibri.ttf",
        ]

        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont("Arial", font_path))
                    pdfmetrics.registerFont(TTFont("Arial-Bold", font_path))
                    print(f"✅ Зарегистрирован шрифт: Arial из {font_path}")
                    return "Arial", "Arial-Bold"
                except Exception as e:
                    print(f"⚠️ Не удалось зарегистрировать шрифт {font_path}: {e}")
                    continue

        print("⚠️ Используются стандартные шрифты Helvetica")
        return "Helvetica", "Helvetica-Bold"
    except Exception as e:
        print(f"⚠️ Ошибка регистрации шрифтов: {e}")
        return "Helvetica", "Helvetica-Bold"


font_normal, font_bold = register_font()


class DashboardGenerator:
    """Класс для создания дашборда."""

    def __init__(self):
        """Инициализация параметров для дашборда."""
        self.width, self.height = A4
        self.colors = {
            'green': '#4CAF50',
            'yellow': '#FFC107',
            'red': '#F44336',
            'background': '#FFFFFF',
            'text': '#333333',
            'light_gray': '#E0E0E0',
            'blue': '#3F51B5',
            'dark_gray': '#666666',
            'border': '#DDDDDD'
        }

    def safe_get(self, data_dict, *keys, default=0):
        """Безопасное получение значения из словаря."""
        current = data_dict
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current if current is not None else default

    def create_statistics_dashboard(self, statistics_data, output_path=None):
        """Создает PDF с дашбордом статистики."""
        if output_path is None:
            temp_file = tempfile.NamedTemporaryFile(
                suffix='.pdf', delete=False
            )
            output_path = temp_file.name

        try:
            print("📊 Начинаю создание дашборда...")

            c = canvas.Canvas(output_path, pagesize=A4)
            width, height = self.width, self.height

            c.setFillColor(HexColor(self.colors['background']))
            c.rect(0, 0, width, height, fill=True, stroke=False)

            c.setFont(font_bold, 24)
            c.setFillColor(HexColor(self.colors['blue']))
            c.drawCentredString(width / 2, height - 50, "ДАШБОРД КАНДИДАТОВ")

            c.setFont(font_normal, 12)
            c.setFillColor(HexColor(self.colors['dark_gray']))
            total = self.safe_get(statistics_data, 'summary', 'total')
            date_str = datetime.now().strftime('%d.%m.%Y')
            c.drawCentredString(
                width / 2, height - 75, f"Всего кандидатов: {
                    total
                } | Дата: {date_str}"
            )

            c.setStrokeColor(HexColor(self.colors['border']))
            c.setLineWidth(1)
            c.line(40, height - 90, width - 40, height - 90)

            current_y = height - 120

            pie_height = self._draw_pie_chart_and_legend(
                c, statistics_data, current_y
            )
            current_y -= pie_height + 30

            criteria_height = self._draw_criteria_section(
                c, statistics_data, current_y
            )
            current_y -= criteria_height + 20

            self._draw_candidates_table(c, statistics_data, current_y)

            c.setFont(font_normal, 10)
            c.setFillColor(HexColor(self.colors['dark_gray']))
            c.drawString(
                40, 30, f"Сгенерировано: {
                    datetime.now().strftime('%d.%m.%Y %H:%M')
                }"
            )
            c.drawRightString(width - 40, 30, "HR Analytics Dashboard")

            c.save()
            print(f"✅ Дашборд успешно создан: {output_path}")
            return output_path

        except Exception as e:
            print(f"❌ Ошибка при создании дашборда: {e}")
            import traceback
            traceback.print_exc()
            if os.path.exists(output_path):
                os.unlink(output_path)
            raise

    def _create_pie_chart_image(self, statistics_data):
        """Создает круговую диаграмму."""
        try:
            green = self.safe_get(statistics_data, 'summary', 'green')
            yellow = self.safe_get(statistics_data, 'summary', 'yellow')
            red = self.safe_get(statistics_data, 'summary', 'red')
            total = green + yellow + red

            if total == 0:
                fig, ax = plt.subplots(figsize=(5, 5), dpi=100)
                ax.text(0.5, 0.5, 'Нет данных',
                        ha='center', va='center',
                        fontsize=14, color='gray')
                ax.set_xlim(0, 1)
                ax.set_ylim(0, 1)
                ax.axis('off')
            else:
                sizes = [green, yellow, red]
                labels = [f'Подходящие\n{green} ({green/total*100:.0f}%)',
                          f'Резерв\n{yellow} ({yellow/total*100:.0f}%)',
                          f'Неподходящие\n{red} ({red/total*100:.0f}%)']
                colors = [
                    self.colors['green'],
                    self.colors['yellow'],
                    self.colors['red']
                ]

                fig, ax = plt.subplots(figsize=(5, 5), dpi=100)

                wedges, texts, autotexts = ax.pie(
                    sizes,
                    labels=labels,
                    colors=colors,
                    autopct='',
                    startangle=90,
                    wedgeprops=dict(width=0.3, edgecolor='w', linewidth=2)
                )

                centre_circle = plt.Circle((0, 0), 0.70, fc='white')
                ax.add_artist(centre_circle)

                ax.text(0, 0, f"{total}\nвсего",
                        ha='center', va='center',
                        fontsize=14, fontweight='bold')

                for text in texts:
                    text.set_fontsize(10)
                    text.set_fontweight('bold')

                ax.axis('equal')

            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
            plt.close(fig)

            buf.seek(0)
            return ImageReader(buf)

        except Exception as e:
            print(f"❌ Ошибка при создании диаграммы: {e}")
            import traceback
            traceback.print_exc()

            fig, ax = plt.subplots(figsize=(5, 5), dpi=100)
            ax.text(0.5, 0.5, 'Ошибка диаграммы',
                    ha='center', va='center',
                    fontsize=12, color='red')
            ax.axis('off')
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
            plt.close(fig)
            buf.seek(0)
            return ImageReader(buf)

    def _draw_pie_chart_and_legend(self, canvas_obj, statistics_data, start_y):
        """Рисует круговую диаграмму и легенду, возвращает высоту секции."""
        pie_image = self._create_pie_chart_image(statistics_data)

        image_x = 50
        image_y = start_y - 180
        image_width = 250
        image_height = 180

        canvas_obj.drawImage(pie_image, image_x, image_y,
                             width=image_width, height=image_height,
                             mask='auto')

        legend_x = image_x + image_width + 20
        legend_y = start_y - 50

        canvas_obj.setFont(font_bold, 14)
        canvas_obj.setFillColor(HexColor(self.colors['text']))
        canvas_obj.drawString(legend_x, legend_y, "Статистика:")

        legend_y -= 25

        green = self.safe_get(statistics_data, 'summary', 'green')
        yellow = self.safe_get(statistics_data, 'summary', 'yellow')
        red = self.safe_get(statistics_data, 'summary', 'red')
        total = green + yellow + red

        green_percent = (green / total * 100) if total > 0 else 0
        yellow_percent = (yellow / total * 100) if total > 0 else 0
        red_percent = (red / total * 100) if total > 0 else 0

        stats_items = [
            {'label': 'Всего кандидатов:', 'value': total, 'color': None},
            {
                'label': 'Подходящие:',
                'value': green,
                'color': self.colors['green'],
                'percent': green_percent
            },
            {
                'label': 'Резерв:',
                'value': yellow,
                'color': self.colors['yellow'],
                'percent': yellow_percent
            },
            {
                'label': 'Неподходящие:',
                'value': red,
                'color': self.colors['red'],
                'percent': red_percent
            },
        ]

        for item in stats_items:
            canvas_obj.setFillColor(HexColor(self.colors['text']))
            canvas_obj.setFont(font_bold, 11)
            canvas_obj.drawString(legend_x, legend_y, item['label'])

            if item['color']:
                canvas_obj.setFillColor(HexColor(item['color']))
                canvas_obj.circle(
                    legend_x - 10, legend_y + 3, 4, fill=True, stroke=False
                )

                value_text = f"{item['value']} ({item['percent']:.1f}%)"
                canvas_obj.setFillColor(HexColor(self.colors['text']))
                canvas_obj.setFont(font_normal, 11)
                text_width = canvas_obj.stringWidth(
                    value_text, font_normal, 11
                )
                canvas_obj.drawString(
                    legend_x + 150 - text_width, legend_y, value_text
                )
            else:
                canvas_obj.setFillColor(HexColor(self.colors['blue']))
                canvas_obj.setFont(font_bold, 11)
                canvas_obj.drawString(
                    legend_x + 150, legend_y, str(item['value'])
                )

            legend_y -= 25

        return 220

    def _draw_criteria_section(self, canvas_obj, statistics_data, start_y):
        """Рисует секцию с критериями анализа, возвращает высоту."""
        section_top = start_y
        y = start_y

        canvas_obj.setFillColor(HexColor(self.colors['blue']))
        canvas_obj.setFont(font_bold, 16)
        canvas_obj.drawString(40, y, "Критерии анализа")

        y -= 30

        canvas_obj.setFillColor(HexColor(self.colors['text']))
        canvas_obj.setFont(font_bold, 12)
        canvas_obj.drawString(40, y, "Топ ВУЗы:")
        canvas_obj.setFont(font_normal, 10)

        universities = self.safe_get(
            statistics_data, 'criteria', 'top_universities', default=[]
        )
        if universities:
            col1_x = 120
            col2_x = 280

            for i, uni in enumerate(universities[:4]):
                if i < 2:
                    canvas_obj.drawString(col1_x, y - (i * 20), f"• {uni}")
                else:
                    canvas_obj.drawString(col2_x, y - ((i-2) * 20), f"• {uni}")

            if len(universities) > 4:
                canvas_obj.drawString(
                    col2_x, y - 40, f"... и еще {len(universities) - 4}"
                )

            y -= max(len(universities[:2]), 1) * 20 + 10
        else:
            canvas_obj.drawString(120, y, "Не заданы")
            y -= 30

        skills_y = y
        canvas_obj.setFont(font_bold, 12)
        canvas_obj.drawString(40, skills_y, "Ключевые навыки:")
        canvas_obj.setFont(font_normal, 10)

        skills = self.safe_get(
            statistics_data, 'criteria', 'key_skills', default=[]
        )
        if skills:
            max_line_length = 60
            lines = []
            current_line = []
            current_length = 0

            for skill in skills:
                if current_length + len(
                    skill
                ) + 2 > max_line_length and current_line:
                    lines.append(', '.join(current_line))
                    current_line = [skill]
                    current_length = len(skill)
                else:
                    current_line.append(skill)
                    current_length += len(skill) + 2

            if current_line:
                lines.append(', '.join(current_line))

            if len(lines) > 3:
                lines = lines[:3]
                lines[-1] = lines[-1][:57] + "..."

            y = skills_y - 20
            for line in lines:
                canvas_obj.drawString(140, y, line)
                y -= 15
        else:
            canvas_obj.drawString(140, skills_y - 20, "Не заданы")
            y = skills_y - 35

        exp_y = y
        canvas_obj.setFont(font_bold, 12)
        canvas_obj.drawString(40, exp_y, "Опыт работы:")
        canvas_obj.setFont(font_normal, 10)

        experience_ranges = self.safe_get(
            statistics_data, 'criteria', 'experience_ranges', default=[]
        )
        if experience_ranges:
            y = exp_y - 20
            for exp in experience_ranges:
                min_age = exp.get('min_age', '')
                max_age = exp.get('max_age', '')
                label = exp.get('label', '')
                canvas_obj.drawString(
                    140, y, f"{min_age}-{max_age} лет: {label}"
                )
                y -= 15
        else:
            canvas_obj.drawString(140, exp_y - 20, "Не заданы")
            y = exp_y - 35

        return section_top - y + 40

    def _draw_candidates_table(self, canvas_obj, statistics_data, start_y):
        """Рисует таблицу с кандидатами."""
        if start_y < 150:
            canvas_obj.showPage()
            canvas_obj.setFillColor(HexColor(self.colors['background']))
            canvas_obj.rect(
                0, 0, self.width, self.height, fill=True, stroke=False
            )
            start_y = self.height - 50

        y = start_y

        canvas_obj.setFillColor(HexColor(self.colors['blue']))
        canvas_obj.setFont(font_bold, 16)
        canvas_obj.drawString(40, y, "Список кандидатов")

        header_y = y - 25
        canvas_obj.setFillColor(HexColor(self.colors['dark_gray']))
        canvas_obj.setFont(font_bold, 10)

        col1_x = 40
        col2_x = 80
        col3_x = 280
        col4_x = 350
        col5_x = 420

        canvas_obj.drawString(col1_x, header_y, "ID")
        canvas_obj.drawString(col2_x, header_y, "ФИО")
        canvas_obj.drawString(col3_x, header_y, "Критерии")
        canvas_obj.drawString(col4_x, header_y, "Категория")
        canvas_obj.drawString(col5_x, header_y, "Совп.")

        canvas_obj.setStrokeColor(HexColor(self.colors['border']))
        canvas_obj.setLineWidth(0.5)
        canvas_obj.line(col1_x, header_y - 5, self.width - 40, header_y - 5)

        y = header_y - 20
        canvas_obj.setFont(font_normal, 9)

        classified_candidates = self.safe_get(
            statistics_data, 'classified', default=[]
        )

        sorted_candidates = sorted(classified_candidates,
                                   key=lambda x: x.get('id', 0),
                                   reverse=True)

        for candidate in sorted_candidates:
            if y < 50:
                canvas_obj.showPage()
                canvas_obj.setFillColor(HexColor(self.colors['background']))
                canvas_obj.rect(
                    0, 0, self.width, self.height, fill=True, stroke=False
                )
                y = self.height - 50

                canvas_obj.setFillColor(HexColor(self.colors['dark_gray']))
                canvas_obj.setFont(font_bold, 10)
                canvas_obj.drawString(col1_x, y, "ID")
                canvas_obj.drawString(col2_x, y, "ФИО")
                canvas_obj.drawString(col3_x, y, "Критерии")
                canvas_obj.drawString(col4_x, y, "Категория")
                canvas_obj.drawString(col5_x, y, "Совп.")
                y -= 25
                canvas_obj.setFont(font_normal, 9)

            candidate_id = candidate.get('id', '')
            category = candidate.get('category', 'unknown')
            matches = candidate.get('matches', 0)

            canvas_obj.setFillColor(HexColor(self.colors['text']))
            canvas_obj.drawString(col1_x, y, f"#{candidate_id}")

            full_name = candidate.get('full_name', 'Неизвестно')
            if len(full_name) > 25:
                full_name = full_name[:22] + "..."
            canvas_obj.drawString(col2_x, y, full_name)

            criteria_text = ""
            if candidate.get('in_top_university', False):
                criteria_text += "В"
            if candidate.get('in_key_skills', False):
                if criteria_text:
                    criteria_text += ","
                criteria_text += "Н"
            if candidate.get('has_experience', False):
                if criteria_text:
                    criteria_text += ","
                criteria_text += "О"

            if not criteria_text:
                criteria_text = "—"

            canvas_obj.drawString(col3_x, y, criteria_text)

            if category == 'green':
                category_text = 'Подх.'
                color = HexColor(self.colors['green'])
            elif category == 'yellow':
                category_text = 'Резерв'
                color = HexColor(self.colors['yellow'])
            elif category == 'red':
                category_text = 'Неподх.'
                color = HexColor(self.colors['red'])
            else:
                category_text = 'Неизв.'
                color = HexColor(self.colors['light_gray'])

            text_width = canvas_obj.stringWidth(category_text, font_normal, 9)
            canvas_obj.setFillColor(color)
            canvas_obj.roundRect(
                col4_x - 3, y - 6, text_width + 6, 14, 3,
                fill=True, stroke=False
            )

            canvas_obj.setFillColor(HexColor('#FFFFFF'))
            canvas_obj.drawString(col4_x, y, category_text)

            canvas_obj.setFillColor(HexColor(self.colors['text']))
            canvas_obj.drawString(col5_x, y, f"{matches}/3")

            y -= 20


def create_statistics_dashboard(statistics_data, output_path=None):
    """Функция для создания дашборда."""
    try:
        print("🎯 Начинаю создание дашборда...")

        generator = DashboardGenerator()
        return generator.create_statistics_dashboard(
            statistics_data, output_path
        )
    except Exception as e:
        print(f"❌ Критическая ошибка при создании дашборда: {e}")
        import traceback
        traceback.print_exc()
        raise
