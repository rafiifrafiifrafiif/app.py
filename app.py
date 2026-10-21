import hashlib
import sqlite3
import pandas as pd
import streamlit as st


# --- INISIALISASI DATABASE ---
def init_db():
  conn = sqlite3.connect("attendance.db")
  cursor = conn.cursor()

  # Tabel Users
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            role TEXT
        )
    """)

  # Tabel Classes
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_name TEXT UNIQUE
        )
    """)

  # Tabel Students
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            class_name TEXT
        )
    """)

  # Tabel Attendance
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT,
            class_name TEXT,
            date TEXT,
            status TEXT
        )
    """)

  # Insert default admin dan user jika belum ada
  cursor.execute("SELECT * FROM users WHERE username = ?", ("admin",))
  if not cursor.fetchone():
    hashed_admin_pw = hashlib.sha256("admin123".encode()).hexdigest()
    cursor.execute(
        "INSERT INTO users VALUES (?, ?, ?)", ("admin", hashed_admin_pw, "Admin")
    )

  cursor.execute("SELECT * FROM users WHERE username = ?", ("teacher",))
  if not cursor.fetchone():
    hashed_teacher_pw = hashlib.sha256("teacher123".encode()).hexdigest()
    cursor.execute(
        "INSERT INTO users VALUES (?, ?, ?)",
        ("teacher", hashed_teacher_pw, "Teacher"),
    )

  conn.commit()
  conn.close()


# --- FUNGSI AUTENTIKASI & ENKRIPSI ---
def make_hashes(password):
  return hashlib.sha256(str(password).encode()).hexdigest()


def login_user(username, password):
  conn = sqlite3.connect("attendance.db")
  cursor = conn.cursor()
  cursor.execute(
      "SELECT password, role FROM users WHERE username = ?", (username,)
  )
  data = cursor.fetchone()
  conn.close()
  if data:
    stored_password, role = data
    if stored_password == make_hashes(password):
      return role
  return None


# --- FUNGSI MANIPULASI DATA ---
def add_class(class_name):
  conn = sqlite3.connect("attendance.db")
  cursor = conn.cursor()
  try:
    cursor.execute("INSERT INTO classes (class_name) VALUES (?)", (class_name,))
    conn.commit()
    success = True
  except sqlite3.IntegrityError:
    success = False
  conn.close()
  return success


def get_classes():
  conn = sqlite3.connect("attendance.db")
  df = pd.read_sql("SELECT class_name FROM classes", conn)
  conn.close()
  return df["class_name"].tolist() if not df.empty else []


def add_student(name, class_name):
  conn = sqlite3.connect("attendance.db")
  cursor = conn.cursor()
  cursor.execute(
      "INSERT INTO students (name, class_name) VALUES (?, ?)",
      (name, class_name),
  )
  conn.commit()
  conn.close()


def get_students_by_class(class_name):
  conn = sqlite3.connect("attendance.db")
  df = pd.read_sql(
      "SELECT name FROM students WHERE class_name = ?",
      conn,
      params=(class_name,),
  )
  conn.close()
  return df["name"].tolist() if not df.empty else []


def save_attendance(student_name, class_name, date, status):
  conn = sqlite3.connect("attendance.db")
  cursor = conn.cursor()
  cursor.execute(
      "SELECT id FROM attendance WHERE student_name = ? AND date = ?",
      (student_name, date),
  )
  existing = cursor.fetchone()
  if existing:
    cursor.execute(
        "UPDATE attendance SET status = ? WHERE id = ?", (status, existing[0])
    )
  else:
    cursor.execute(
        "INSERT INTO attendance (student_name, class_name, date, status) VALUES"
        " (?, ?, ?, ?)",
        (student_name, class_name, date, status),
    )
  conn.commit()
  conn.close()


def get_attendance_data():
  conn = sqlite3.connect("attendance.db")
  df = pd.read_sql("SELECT * FROM attendance", conn)
  conn.close()
  return df


def delete_attendance(record_id):
  conn = sqlite3.connect("attendance.db")
  cursor = conn.cursor()
  cursor.execute("DELETE FROM attendance WHERE id = ?", (record_id,))
  conn.commit()
  conn.close()


# --- APLIKASI UTAMA STREAMLIT ---
def main():
  st.set_page_config(
      page_title="Student Attendance App", page_icon="📚", layout="wide"
  )
  init_db()

  st.sidebar.title("🔐 Login Sistem")
  if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.session_state["role"] = ""

  if not st.session_state["logged_in"]:
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
      role = login_user(username, password)
      if role:
        st.session_state["logged_in"] = True
        st.session_state["username"] = username
        st.session_state["role"] = role
        st.success(f"Berhasil login sebagai {role}")
        st.rerun()
      else:
        st.sidebar.error("Username atau Password salah")

    st.title("📚 Student Attendance App")
    st.info(
        "Silakan login melalui sidebar untuk mulai menggunakan aplikasi."
    )
    st.markdown("""
        ### Akun Default untuk Pengujian:
        - **Admin**: username `admin`, password `admin123`
        - **Teacher**: username `teacher`, password `teacher123`
        """)
    return

  # Sidebar Informasi User & Logout
  st.sidebar.write(f"Halo, **{st.session_state['username']}**")
  st.sidebar.write(f"Role: **{st.session_state['role']}**")
  if st.sidebar.button("Logout"):
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.session_state["role"] = ""
    st.rerun()

  st.title("📚 Student Attendance Application")

  menu = ["Dashboard", "Input Absensi", "Rekap & Laporan"]
  if st.session_state["role"] == "Admin":
    menu.append("Master Data & Kontrol")

  choice = st.sidebar.selectbox("Navigasi Menu", menu)

  if choice == "Dashboard":
    st.subheader("📊 Dashboard Kehadiran")
    df = get_attendance_data()
    if not df.empty:
      st.metric("Total Catatan Kehadiran", len(df))
      st.dataframe(df.tail(10), use_container_width=True)
    else:
      st.info("Belum ada data absensi tercatat.")

  elif choice == "Input Absensi":
    st.subheader("📝 Input Absensi Siswa")
    classes = get_classes()
    if not classes:
      st.warning(
          "Belum ada kelas yang terdaftar. Hubungi Admin untuk menambah kelas."
      )
    else:
      selected_class = st.selectbox("Pilih Kelas", classes)
      attendance_date = st.date_input("Tanggal Absensi")

      students = get_students_by_class(selected_class)
      if not students:
        st.warning(f"Belum ada siswa terdaftar di kelas {selected_class}.")
      else:
        with st.form("attendance_form"):
          st.write(
              f"Absensi Kelas **{selected_class}** - Tanggal:"
              f" **{attendance_date}**"
          )
          statuses = {}
          for student in students:
            statuses[student] = st.selectbox(
                f"Status: {student}",
                ["Present", "Excused", "Sick", "Absent"],
                key=student,
            )

          submitted = st.form_submit_button("Simpan Absensi")
          if submitted:
            for student, status in statuses.items():
              save_attendance(
                  student, selected_class, str(attendance_date), status
              )
            st.success("Data absensi berhasil disimpan!")

  elif choice == "Rekap & Laporan":
    st.subheader("📈 Rekap dan Laporan Kehadiran")
    df = get_attendance_data()
    if not df.empty:
      class_filter = st.selectbox(
          "Filter Berdasarkan Kelas", ["Semua"] + get_classes()
      )
      if class_filter != "Semua":
        df = df[df["class_name"] == class_filter]
      st.dataframe(df, use_container_width=True)
    else:
      st.info("Belum ada data untuk ditampilkan.")

  elif choice == "Master Data & Kontrol" and st.session_state["role"] == "Admin":
    st.subheader("⚙️ Panel Kontrol Admin & Master Data")

    tab1, tab2, tab3 = st.tabs(
        ["Tambah Kelas", "Tambah Siswa", "Kelola/Hapus Data Absensi"]
    )

    with tab1:
      new_class = st.text_input("Nama Kelas Baru (Contoh: 10A)")
      if st.button("Simpan Kelas"):
        if new_class:
          if add_class(new_class):
            st.success(f"Kelas {new_class} berhasil ditambahkan!")
          else:
            st.error("Kelas tersebut sudah ada.")
        else:
          st.warning("Nama kelas tidak boleh kosong.")

    with tab2:
      classes = get_classes()
      if classes:
        student_name = st.text_input("Nama Lengkap Siswa")
        student_class = st.selectbox("Pilih Kelas Siswa", classes, key="stu_class")
        if st.button("Simpan Siswa"):
          if student_name:
            add_student(student_name, student_class)
            st.success(f"Siswa {student_name} berhasil ditambahkan!")
          else:
            st.warning("Nama siswa tidak boleh kosong.")
      else:
        st.warning("Tambahkan kelas terlebih dahulu pada tab sebelumnya.")

    with tab3:
      st.write("Manajemen / Penghapusan Data Absensi")
      df = get_attendance_data()
      if not df.empty:
        st.dataframe(df, use_container_width=True)
        record_id_to_delete = st.number_input(
            "Masukkan ID Record yang ingin dihapus", min_value=1, step=1
        )
        if st.button("Hapus Data"):
          delete_attendance(record_id_to_delete)
          st.success(f"Data dengan ID {record_id_to_delete} berhasil dihapus!")
          st.rerun()
      else:
        st.info("Tidak ada data untuk dikelola.")


if __name__ == "__main__":
  main()

