import json
import sqlite3
from datetime import datetime


class Database:
    """Определяем базу данных, задаем параметры для такблиц."""

    def __init__(self, db_file="data/database.db"):
        """Инициализируем настройки для базы данных."""
        self.connection = sqlite3.connect(db_file, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()
        self.create_tables()
        self.add_missing_columns()

    def create_tables(self):
        """Создаем таблицу."""
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            full_name TEXT,
            phone TEXT,
            university TEXT,
            desired_salary INTEGER,
            skills TEXT,
            schedule TEXT,
            working_hours TEXT,
            age INTEGER,
            status TEXT DEFAULT 'new',
            created_at TEXT,
            business_trips TEXT,
            commute_time TEXT,
            work_format TEXT,
            employment_type TEXT
        )
        """)
        self.connection.commit()

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS stats_criteria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            value TEXT,
            created_at TEXT
        )
        """)
        self.connection.commit()

    def add_missing_columns(self):
        """Проверяет и добавляет отсутствующие колонки в таблицу resumes."""
        required_columns = [
            'id', 'user_id', 'full_name', 'phone', 'university',
            'desired_salary', 'skills', 'schedule', 'working_hours', 'age',
            'status', 'created_at', 'business_trips', 'commute_time',
            'work_format', 'employment_type'
        ]

        self.cursor.execute("PRAGMA table_info(resumes)")
        existing_columns = [col[1] for col in self.cursor.fetchall()]

        missing = [
            col for col in required_columns if col not in existing_columns
        ]

        if missing:
            print(f"Обнаружены отсутствующие колонки: {missing}. Добавляем...")
            for col in missing:
                try:
                    self.cursor.execute(
                        f"ALTER TABLE resumes ADD COLUMN {col} TEXT"
                    )
                    print(f"Колонка {col} успешно добавлена.")
                except Exception as e:
                    print(f"Ошибка при добавлении колонки {col}: {e}")
            self.connection.commit()
        else:
            print("Все необходимые колонки уже присутствуют.")

    def add_resume(
            self, user_id, full_name, phone, university,
            desired_salary, skills, schedule, working_hours, age,
            business_trips, commute_time, work_format, employment_type
    ):
        """Добавляем резюме."""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute("""
        INSERT INTO resumes (
                            user_id,
                            full_name,
                            phone,
                            university,
                            desired_salary,
                            skills,
                            schedule,
                            working_hours,
                            age,
                            status,
                            created_at,
                            business_trips,
                            commute_time,
                            work_format,
                            employment_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, full_name, phone, university, desired_salary,
            skills, schedule, working_hours, age, 'new', current_time,
            business_trips, commute_time, work_format, employment_type
            ))
        self.connection.commit()
        return self.cursor.lastrowid

    def get_resume(self, resume_id):
        """Получаем резюме."""
        self.cursor.execute("SELECT * FROM resumes WHERE id = ?", (resume_id,))
        return self.cursor.fetchone()

    def get_all_resumes(self, status=None):
        """Получаем все анкеты."""
        if status:
            self.cursor.execute(
                "SELECT * FROM resumes WHERE status = ? ORDER BY id DESC",
                (status,)
            )
        else:
            self.cursor.execute("SELECT * FROM resumes ORDER BY id DESC")
        return self.cursor.fetchall()

    def update_status(self, resume_id, status):
        """Редактируем статус."""
        self.cursor.execute(
            "UPDATE resumes SET status = ? WHERE id = ?", (status, resume_id)
        )
        self.connection.commit()

    def get_statistics(self):
        """Получаем статистику."""
        self.cursor.execute("SELECT COUNT(*) FROM resumes")
        total = self.cursor.fetchone()[0]

        self.cursor.execute(
            "SELECT status, COUNT(*) FROM resumes GROUP BY status"
        )
        by_status = dict(self.cursor.fetchall())

        return {
            "total": total,
            "by_status": by_status
        }

    def safe_int(self, value, default=0):
        """Безопасное преобразование в целое число."""
        try:
            if value is None:
                return default
            return int(value)
        except (ValueError, TypeError):
            return default

    def get_candidate_statistics(self):
        """Получает данные для классификации кандидатов."""
        resumes = self.get_all_resumes()

        criteria = self.get_stats_criteria()

        if not criteria:
            criteria = self.get_default_criteria()
            self.save_stats_criteria(criteria)

        classified_candidates = self._classify_candidates(resumes, criteria)

        return {
            'criteria': criteria,
            'classified': classified_candidates,
            'summary': self._calculate_summary(classified_candidates)
        }

    def _classify_candidates(self, resumes, criteria):
        """Классифицирует кандидатов по 3 спискам."""
        classified = []

        top_universities = criteria.get('top_universities', [])
        key_skills = criteria.get('key_skills', [])
        experience_ranges = criteria.get('experience_ranges', [])

        for resume in resumes:
            university = resume['university'] if resume['university'] else ""
            skills_str = resume['skills'] if resume['skills'] else ""
            age = resume['age']

            in_top_university = False
            if university and top_universities:
                uni_lower = university.lower()
                for top_uni in top_universities:
                    if top_uni.lower() in uni_lower:
                        in_top_university = True
                        break

            in_key_skills = False
            if skills_str and key_skills:
                skills = [s.strip().lower() for s in skills_str.split(',')]
                for skill in skills:
                    if skill in [s.lower() for s in key_skills]:
                        in_key_skills = True
                        break

            has_experience = False
            if age is not None and experience_ranges:
                age_int = self.safe_int(age, 0)

                for exp_range in experience_ranges:
                    min_age = self.safe_int(exp_range.get('min_age'), 0)
                    max_age = self.safe_int(exp_range.get('max_age'), 100)

                    if min_age <= age_int <= max_age:
                        has_experience = True
                        break

            matches = sum([in_top_university, in_key_skills, has_experience])

            if matches == 3:
                category = 'green'
            elif matches >= 1:
                category = 'yellow'
            else:
                category = 'red'

            classified.append({
                'id': self.safe_int(resume['id']),
                'full_name': str(resume['full_name']) if resume['full_name'] else 'Неизвестно',
                'university': str(university),
                'skills': str(skills_str),
                'age': age_int if 'age_int' in locals() else self.safe_int(
                    age
                ),
                'in_top_university': bool(in_top_university),
                'in_key_skills': bool(in_key_skills),
                'has_experience': bool(has_experience),
                'matches': int(matches),
                'category': str(category)
            })

        return classified

    def _calculate_summary(self, classified_candidates):
        """Рассчитывает итоговую статистику."""
        summary = {
            'green': 0,
            'yellow': 0,
            'red': 0,
            'total': len(classified_candidates)
        }

        for candidate in classified_candidates:
            category = candidate.get('category', '')
            if category == 'green':
                summary['green'] += 1
            elif category == 'yellow':
                summary['yellow'] += 1
            elif category == 'red':
                summary['red'] += 1

        total = summary['total']
        if total > 0:
            summary[
                'green_percent'
            ] = round((summary['green'] / total) * 100, 1)
            summary[
                'yellow_percent'
            ] = round((summary['yellow'] / total) * 100, 1)
            summary['red_percent'] = round((summary['red'] / total) * 100, 1)
        else:
            summary['green_percent'] = 0
            summary['yellow_percent'] = 0
            summary['red_percent'] = 0

        return summary

    def get_default_criteria(self):
        """Возвращает дефолтные критерии."""
        return {
            'top_universities': ['МГУ', 'СПбГУ', 'МФТИ', 'ВШЭ', 'МИФИ'],
            'key_skills': [
                'python', 'java', 'sql', 'git', 'docker', 'linux', 'английский'
            ],
            'experience_ranges': [
                {'min_age': 22, 'max_age': 25, 'label': 'младший специалист'},
                {'min_age': 26, 'max_age': 30, 'label': 'средний специалист'},
                {'min_age': 31, 'max_age': 40, 'label': 'старший специалист'}
            ]
        }

    def save_stats_criteria(self, criteria):
        """Сохраняет критерии статистики."""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute("DELETE FROM stats_criteria")
        for category, values in criteria.items():
            values_json = json.dumps(values)
            self.cursor.execute("""
                INSERT INTO stats_criteria
                                (
                                category,
                                value,
                                created_at
                                ) VALUES (?, ?, ?)
            """, (category, values_json, current_time)
            )

        self.connection.commit()

    def get_stats_criteria(self):
        """Получает сохраненные критерии статистики."""
        self.cursor.execute("SELECT category, value FROM stats_criteria")
        rows = self.cursor.fetchall()

        if not rows:
            return None

        criteria = {}
        for row in rows:
            category, values_json = row
            criteria[category] = json.loads(values_json)

        return criteria
