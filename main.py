from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
import sqlite3
import json
import os
import hashlib
import secrets

DB = os.path.join(os.path.dirname(__file__), "data.db")


def database():
    return sqlite3.connect(DB)


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def initialize_database():
    db = database()
    cur = db.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY,
            password_hash TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS fields (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            field_key TEXT UNIQUE,
            field_name TEXT NOT NULL,
            active INTEGER DEFAULT 1
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS records (
            mobile TEXT PRIMARY KEY,
            data TEXT NOT NULL
        )
    """)

    if cur.execute("SELECT COUNT(*) FROM fields").fetchone()[0] == 0:

        default_fields = [
            ("mobile", "شماره موبایل"),
            ("first_name", "نام"),
            ("last_name", "نام خانوادگی"),
            ("national_id", "کد ملی"),
            ("address", "آدرس"),
            ("notes", "توضیحات"),
        ]

        cur.executemany(
            """
            INSERT INTO fields(field_key, field_name)
            VALUES (?, ?)
            """,
            default_fields
        )

    db.commit()
    db.close()


def get_fields():
    db = database()

    rows = db.execute("""
        SELECT field_key, field_name
        FROM fields
        WHERE active=1
        ORDER BY id
    """).fetchall()

    db.close()

    return rows


class LoginScreen(Screen):

    def check_password(self):

        password = self.ids.password.text

        db = database()

        row = db.execute(
            "SELECT password_hash FROM settings WHERE id=1"
        ).fetchone()

        db.close()

        if row is None:

            self.manager.current = "main"

            db = database()

            db.execute(
                """
                INSERT OR REPLACE INTO settings
                (id,password_hash)
                VALUES (1,?)
                """,
                (hash_password(password),)
            )

            db.commit()
            db.close()

            return

        if hash_password(password) == row[0]:

            self.ids.error.text = ""
            self.manager.current = "main"

        else:

            self.ids.error.text = "رمز عبور اشتباه است."


class MainScreen(Screen):

    def search(self):

        mobile = self.ids.mobile.text.strip()

        if not mobile:

            self.ids.result.text = (
                "شماره موبایل را وارد کنید."
            )

            return

        db = database()

        row = db.execute(
            "SELECT data FROM records WHERE mobile=?",
            (mobile,)
        ).fetchone()

        db.close()

        if not row:

            self.ids.result.text = (
                "اطلاعاتی برای این شماره وجود ندارد."
            )

            return

        data = json.loads(row[0])

        result = []

        for key, name in get_fields():

            result.append(
                f"{name}: {data.get(key, '')}"
            )

        self.ids.result.text = "\n".join(result)


class EntryScreen(Screen):

    def on_pre_enter(self):

        from kivy.uix.label import Label
        from kivy.uix.textinput import TextInput

        self.ids.form.clear_widgets()

        self.inputs = {}

        for key, name in get_fields():

            self.ids.form.add_widget(
                Label(
                    text=name,
                    size_hint_y=None,
                    height=35
                )
            )

            field = TextInput(
                multiline=key in ("address", "notes"),
                size_hint_y=None,
                height=45
            )

            self.ids.form.add_widget(field)

            self.inputs[key] = field


    def save_record(self):

        data = {}

        for key, field in self.inputs.items():

            data[key] = field.text


        mobile = data.get("mobile", "").strip()

        if not mobile:

            self.ids.status.text = (
                "شماره موبایل الزامی است."
            )

            return


        db = database()

        db.execute(
            """
            INSERT OR REPLACE INTO records
            (mobile,data)
            VALUES (?,?)
            """,
            (
                mobile,
                json.dumps(
                    data,
                    ensure_ascii=False
                )
            )
        )

        db.commit()
        db.close()

        self.ids.status.text = (
            "اطلاعات با موفقیت ذخیره شد."
        )


class FieldsScreen(Screen):

    def on_pre_enter(self):

        self.refresh()


    def refresh(self):

        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.textinput import TextInput
        from kivy.uix.button import Button

        self.ids.field_list.clear_widgets()

        db = database()

        rows = db.execute("""
            SELECT id, field_key, field_name
            FROM fields
            WHERE active=1
            ORDER BY id
        """).fetchall()

        db.close()


        for field_id, key, name in rows:

            row = BoxLayout(
                size_hint_y=None,
                height=50
            )

            text = TextInput(
                text=name
            )

            button = Button(
                text="ذخیره",
                size_hint_x=.25
            )


            def save_name(
                instance,
                fid=field_id,
                inp=text
            ):

                db = database()

                db.execute(
                    """
                    UPDATE fields
                    SET field_name=?
                    WHERE id=?
                    """,
                    (
                        inp.text,
                        fid
                    )
                )

                db.commit()
                db.close()


            button.bind(
                on_release=save_name
            )

            row.add_widget(text)
            row.add_widget(button)

            self.ids.field_list.add_widget(row)


    def add_field(self):

        key = (
            self.ids.new_key.text
            .strip()
            .lower()
            .replace(" ", "_")
        )

        name = self.ids.new_name.text.strip()

        if not key or not name:
            return


        db = database()

        try:

            db.execute(
                """
                INSERT INTO fields
                (field_key,field_name)
                VALUES (?,?)
                """,
                (
                    key,
                    name
                )
            )

            db.commit()

        except sqlite3.IntegrityError:

            pass

        db.close()

        self.ids.new_key.text = ""
        self.ids.new_name.text = ""

        self.refresh()


KV = """

ScreenManager:

    LoginScreen:
    MainScreen:
    EntryScreen:
    FieldsScreen:


<LoginScreen>:

    name: "login"

    BoxLayout:

        orientation: "vertical"

        padding: 30
        spacing: 15

        Label:
            text: "مدیریت اطلاعات"
            font_size: 30

        Label:
            text: "رمز عبور"

        TextInput:
            id: password
            password: True
            multiline: False
            size_hint_y: None
            height: 50

        Button:
            text: "ورود"
            size_hint_y: None
            height: 50
            on_release: root.check_password()

        Label:
            id: error
            text: ""


<MainScreen>:

    name: "main"

    BoxLayout:

        orientation: "vertical"

        padding: 20
        spacing: 12

        Label:
            text: "جستجوی اطلاعات"
            font_size: 28

        TextInput:
            id: mobile
            hint_text: "شماره موبایل"
            multiline: False
            size_hint_y: None
            height: 50

        Button:
            text: "جستجو"
            size_hint_y: None
            height: 50
            on_release: root.search()

        Label:
            id: result
            text: ""
            halign: "right"
            valign: "top"
            text_size: self.width, None

        Button:
            text: "ورود اطلاعات"
            size_hint_y: None
            height: 50
            on_release: app.root.current = "entry"

        Button:
            text: "مدیریت فیلدها"
            size_hint_y: None
            height: 50
            on_release: app.root.current = "fields"


<EntryScreen>:

    name: "entry"

    BoxLayout:

        orientation: "vertical"

        padding: 15
        spacing: 8

        ScrollView:

            GridLayout:

                id: form

                cols: 1

                spacing: 6

                size_hint_y: None

                height: self.minimum_height


        Label:

            id: status

            text: ""

            size_hint_y: None

            height: 35


        BoxLayout:

            size_hint_y: None

            height: 50

            Button:
                text: "ذخیره"
                on_release: root.save_record()

            Button:
                text: "بازگشت"
                on_release: app.root.current = "main"


<FieldsScreen>:

    name: "fields"

    BoxLayout:

        orientation: "vertical"

        padding: 15
        spacing: 8


        Label:

            text: "مدیریت فیلدها"

            font_size: 24

            size_hint_y: None

            height: 45


        ScrollView:

            GridLayout:

                id: field_list

                cols: 1

                spacing: 6

                size_hint_y: None

                height: self.minimum_height


        TextInput:

            id: new_key

            hint_text: "نام داخلی فیلد، مثال: company"

            multiline: False

            size_hint_y: None

            height: 45


        TextInput:

            id: new_name

            hint_text: "عنوان فیلد، مثال: شرکت"

            multiline: False

            size_hint_y: None

            height: 45


        Button:

            text: "افزودن فیلد"

            size_hint_y: None

            height: 50

            on_release: root.add_field()


        Button:

            text: "بازگشت"

            size_hint_y: None

            height: 50

            on_release: app.root.current = "main"

"""


class MobileDataApp(App):

    def build(self):

        initialize_database()

        return Builder.load_string(KV)


if __name__ == "__main__":

    MobileDataApp().run()
