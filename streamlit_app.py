import csv
import io
import re
from collections import Counter
from datetime import date, time, datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit.components.v1 import html as st_html
import base64


def safe_rerun():
    """Try to rerun the Streamlit script in a few compatible ways.

    Some Streamlit releases don't expose `st.experimental_rerun`. In that
    case attempt to raise the internal `RerunException`. If all attempts
    fail, set a session flag and stop to avoid crashing.
    """
    try:
        if hasattr(st, "experimental_rerun"):
            st.experimental_rerun()
            return
    except Exception:
        pass

    try:
        from streamlit.runtime.scriptrunner.script_runner import RerunException

        raise RerunException()
    except Exception:
        try:
            from streamlit.runtime.scriptrunner import RerunException

            raise RerunException()
        except Exception:
            try:
                from streamlit.scriptrunner.script_runner import RerunException

                raise RerunException()
            except Exception:
                # Final fallback: mark session and stop
                st.session_state._rerun = True
                st.stop()


# Background image settings: prefer local file at `assets/login_bg.(jpg|png)` else set URL
BACKGROUND_IMAGE_PATHS = [
    Path(__file__).parent / "assets" / "login_bg.jpg",
    Path(__file__).parent / "assets" / "login_bg.png",
]
BACKGROUND_IMAGE_URL = "https://webcdn.getmidas.com/uploads/2023/09/celebi.jpeg"  # optional: set to a public image URL


def _encode_image_to_base64(path: Path):
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()


def get_background_css():
    img_data_url = None
    for p in BACKGROUND_IMAGE_PATHS:
        if p.exists():
            ext = p.suffix.lower().lstrip(".")
            b64 = _encode_image_to_base64(p)
            img_data_url = f"data:image/{ext};base64,{b64}"
            break

    if not img_data_url and BACKGROUND_IMAGE_URL:
        img_data_url = BACKGROUND_IMAGE_URL

    if not img_data_url:
        return ""

    css = f"""
    <style>
        body {{
            background-image: url('{img_data_url}');
            background-size: cover;
            background-position: center center;
            background-attachment: fixed;
            background-repeat: no-repeat;
        }}
        /* make Streamlit app containers transparent so background is visible */
        .stApp, [data-testid='stAppViewContainer'], .main, .block-container {{
            background: transparent !important;
        }}
    /* dim overlay so login fields remain readable */
        .stApp::before {{
      content: "";
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.45);
      pointer-events: none;
      z-index: 0;
    }}
        /* ensure login card sits above overlay */
        .page-header, .card, .metric-card, form, .stForm {{
            position: relative; z-index: 2;
        }}
    </style>
    """
    return css

DATA_FILE = Path(__file__).parent / "reports.csv"
FIELDNAMES = [
    "Tarih",
    "Vardiya",
    "Önceki vardiyadan devam eden uçuşlar",
    "Gün içerisinde bırakılan ekipman bilgisi",
    "Personel listesi",
    "Erken çıkan personeller",
    "Mesaiye kalan personeller",
    "Extra verilen hizmetler / ekipman takibi",
    "Bilgilendirme",
    "Gelmeyen veya geç gelen personeller",
    "Şoför Devreden",
    "Şoför Devralan",
    "Şoför Devreden Saati",
    "Şoför Devralan Saati",
    "YBT Devreden",
    "YBT Devralan",
    "YBT Devreden Saati",
    "YBT Devralan Saati",
]

st.set_page_config(page_title="Ramp Koordine Nöbet Devir Sistemi", page_icon="🪂", layout="wide")

DIRECTOR_PASSWORD = "chsıst2026++"
COORDINATOR_PASSWORD = "Chs2026++"

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_role = ""

if not st.session_state.authenticated:
    # Inject background CSS (file at assets/login_bg.(jpg|png) or set BACKGROUND_IMAGE_URL)
    bg_css = get_background_css()
    if bg_css:
        st.markdown(bg_css, unsafe_allow_html=True)

    st.markdown("<h1 style='text-align:center;margin-top:8px;'>Nöbet Raporu</h1>", unsafe_allow_html=True)
    st.markdown("## Giriş Yap")
    left_col, right_col = st.columns(2)
    with left_col:
        st.markdown("### Müdür Girişi")
        with st.form(key="login_form_director"):
            director_password = st.text_input("Şifre", type="password", key="director_pass")
            director_button = st.form_submit_button("Müdür Olarak Giriş")
            if director_button:
                if director_password == DIRECTOR_PASSWORD:
                    st.session_state.authenticated = True
                    st.session_state.user_role = "Müdür"
                    safe_rerun()
                else:
                    st.error("Şifre hatalı.")
    with right_col:
        st.markdown("### Kordine Girişi")
        with st.form(key="login_form_coordinator"):
            coordinator_password = st.text_input("Şifre", type="password", key="coord_pass")
            coordinator_button = st.form_submit_button("Kordine Olarak Giriş")
            if coordinator_button:
                if coordinator_password == COORDINATOR_PASSWORD:
                    st.session_state.authenticated = True
                    st.session_state.user_role = "Kordine"
                    safe_rerun()
                else:
                    st.error("Şifre hatalı.")
    st.stop()

menu_options = ["Müdür Paneli", "Devir Raporları"] if st.session_state.user_role == "Müdür" else ["Ana Sayfa", "Yeni Devir Oluştur", "Devir Raporları"]
PAGE = st.sidebar.selectbox(
    "Menü",
    menu_options,
)

st.sidebar.markdown("# ÇELEBİ Yer Hizmetleri")
st.sidebar.markdown("##### Ramp Koordinasyon Sistemi")
st.sidebar.markdown("---")
st.sidebar.write(f"**Yetki:** {st.session_state.user_role}")
st.sidebar.write("**Bölüm:** Ramp Koordinasyon")
if st.sidebar.button("Çıkış Yap"):
    # Clear session state to ensure immediate logout
    keys = list(st.session_state.keys())
    for k in keys:
        del st.session_state[k]
    st.session_state.authenticated = False
    st.session_state.user_role = ""
    safe_rerun()

sidebar_bg = "#020617"
sidebar_text = "#cbd5e1"
app_bg = "#020617"
text_color = "#f8fafc"
card_bg = "linear-gradient(135deg, #111827 0%, #1f2937 100%)"
card_text = "#f8fafc"
metric_bg = "linear-gradient(135deg, #111827 0%, #0f172a 100%)"
report_bg = "#020617"
report_text = "#f8fafc"
widget_bg = "#1f2937"
widget_text = "#f8fafc"
button_bg = "#2563eb"
button_text = "#ffffff"
status_ready = "#16a34a"
status_wait = "#f59e0b"

st.markdown(
    f"""
    <style>
    [data-testid='stSidebar'] {{
        background-color: {sidebar_bg};
        color: {sidebar_text};
    }}
    .sidebar .sidebar-content {{
        padding: 24px 18px;
    }}
    .stApp {{
        background-color: {app_bg} !important;
        color: {text_color} !important;
    }}
    body {{
        background-color: {app_bg} !important;
        color: {text_color} !important;
    }}
    .page-header {{
        border-radius: 24px;
        background: {card_bg};
        padding: 28px;
        margin-bottom: 24px;
        box-shadow: 0 22px 45px rgba(0, 0, 0, 0.22);
        color: {card_text};
    }}
    .page-header h1 {{
        margin: 0;
        font-size: 2.2rem;
    }}
    .page-header p {{
        color: #94a3b8;
        margin-top: 8px;
    }}
    .card {{
        padding: 24px;
        border-radius: 20px;
        background: {card_bg};
        color: {card_text};
        box-shadow: 0 18px 45px rgba(0, 0, 0, 0.18);
        margin-bottom: 18px;
    }}
    .metric-card {{
        padding: 20px;
        border-radius: 18px;
        background: {metric_bg};
        color: {card_text};
        box-shadow: 0 12px 30px rgba(15, 23, 42, 0.25);
        margin-bottom: 16px;
    }}
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectBox>div>div>div>div, .stDateInput>div>div>input, .stTimeInput>div>div>input {{
        background-color: {widget_bg} !important;
        color: {widget_text} !important;
        border-color: #cbd5e1 !important;
    }}
    .metric-card h3 {{
        margin-bottom: 8px;
        font-size: 1rem;
        color: #94a3b8;
    }}
    .metric-value {{
        font-size: 2.2rem;
        font-weight: 700;
        margin: 0;
    }}
    .metric-label {{
        color: #94a3b8;
        margin-top: 8px;
        font-size: 0.9rem;
    }}
    .status-pill {{
        display: inline-flex;
        align-items: center;
        padding: 6px 12px;
        border-radius: 999px;
        font-size: 0.9rem;
        font-weight: 600;
        margin-top: 12px;
    }}
    .status-ready {{background: {status_ready}; color: {card_text};}}
    .status-wait {{background: {status_wait}; color: {app_bg};}}
    .report-block {{
        border-radius: 18px;
        background: {report_bg};
        padding: 20px;
        box-shadow: 0 10px 28px rgba(0, 0, 0, 0.16);
        margin-bottom: 18px;
        color: {report_text};
    }}
    .report-item {{
        border: 1px solid rgba(148, 163, 184, 0.25);
        background: rgba(15, 23, 42, 0.8);
        padding: 14px 18px;
        border-radius: 14px;
        margin-bottom: 14px;
    }}
    .report-item strong {{
        display: block;
        margin-bottom: 8px;
        color: #f8fafc;
        font-size: 0.95rem;
    }}
    .report-item .item-value {{
        color: #cbd5e1;
        white-space: pre-wrap;
        line-height: 1.5;
    }}
    .report-block strong {{
        color: {report_text};
    }}
    .section-title {{
        font-size: 1.25rem;
        font-weight: 700;
        margin-top: 24px;
        margin-bottom: 16px;
        color: {report_text};
    }}
    .stButton>button {{
        border-radius: 999px;
        background-color: {button_bg};
        color: {button_text};
        font-weight: 600;
        padding: 12px 24px;
    }}
    .stButton>button:hover {{
        background-color: #1d4ed8;
    }}
    """,
    unsafe_allow_html=True,
)


FIELD_ALIASES = {
    "Gün içerisinde bırakılan ekipman": "Gün içerisinde bırakılan ekipman bilgisi",
    "Personel listesi": "Personel listesi",
    "Devreden": "Şoför Devreden",
    "Devralan": "Şoför Devralan",
    "Devreden Saati": "Şoför Devreden Saati",
    "Devralan Saati": "Şoför Devralan Saati",
}


def load_reports():
    if not DATA_FILE.exists():
        return []

    with open(DATA_FILE, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        reports = []
        for raw_row in reader:
            row = {}
            for key, value in raw_row.items():
                if key is None:
                    continue
                normalized_key = key.strip()
                normalized_value = value.strip() if isinstance(value, str) else ""
                row[normalized_key] = normalized_value
            for alias, canonical in FIELD_ALIASES.items():
                if alias in row and canonical not in row:
                    row[canonical] = row[alias]
            for field in FIELDNAMES:
                if row.get(field) is None or row[field] == "":
                    row[field] = "NIL"
            reports.append(row)

    return reports


def _read_existing_rows():
    if not DATA_FILE.exists():
        return []
    with open(DATA_FILE, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        return list(reader)


def save_report(report):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        with open(DATA_FILE, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerow(report)
        return

    existing_rows = _read_existing_rows()
    existing_fieldnames = existing_rows[0].keys() if existing_rows else []
    if set(existing_fieldnames) != set(FIELDNAMES):
        converted_rows = []
        for raw_row in existing_rows:
            row = {}
            for key, value in raw_row.items():
                if key is None:
                    continue
                normalized_key = key.strip()
                normalized_value = value.strip() if isinstance(value, str) else ""
                row[normalized_key] = normalized_value
            for alias, canonical in FIELD_ALIASES.items():
                if alias in row and canonical not in row:
                    row[canonical] = row[alias]
            converted_row = {}
            for field in FIELDNAMES:
                field_value = row.get(field, "")
                converted_row[field] = field_value if field_value else "NIL"
            converted_rows.append(converted_row)
        with open(DATA_FILE, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(converted_rows)
        with open(DATA_FILE, "a", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
            writer.writerow(report)
    else:
        with open(DATA_FILE, "a", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
            writer.writerow(report)


def reports_to_dataframe(reports):
    if not reports:
        return pd.DataFrame(columns=FIELDNAMES)
    df = pd.DataFrame(reports)
    return df[FIELDNAMES]


def reports_to_excel(reports):
    df = reports_to_dataframe(reports)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Raporlar")
        workbook = writer.book
        worksheet = writer.sheets["Raporlar"]
        for idx, width in enumerate([18] * len(df.columns)):
            worksheet.set_column(idx, idx, width)
    output.seek(0)
    return output


def reports_to_csv(reports):
    df = reports_to_dataframe(reports)
    return df.to_csv(index=False, encoding="utf-8-sig")


def get_report_value(report, field, default="NIL"):
    value = report.get(field, default)
    return default if value is None else value


reports = load_reports()

shift_times = {
    "Sabah": "08:00 - 17:00",
    "Orta": "14:00 - 00:30",
    "Gece": "23:59 - 08:30",
}

# Personel isimlerini bu listeye ekleyin. Yeni rapor formu bu isimler üzerinden seçim yapacaktır.
PERSONNEL_OPTIONS = [
    "İsmail Hakkı Bayrakçı",
    "Müslüm Kaya",
    "Mehmet Yılmaz",
    "Ferhat Baykal",
    "Samet Avcı",
    "Yalçın Büyükbaş",
    "Mehmet Ali Gülçetin",
    "Hamit AK",
    "Hüseyin Söylemez",
]


def count_non_nil(value):
    return 0 if not value or value.strip().upper() in ["", "NIL"] else 1


def parse_person_entries(value):
    if not value or value.strip().upper() == "NIL":
        return []
    parts = re.split(r"[\n,;]+", value)
    return [p.strip() for p in parts if p.strip()]


def unique_personnel_names(reports, field="Personel listesi"):
    names = set()
    for report in reports:
        names.update(parse_person_entries(get_report_value(report, field, "")))
    return names


def top_persons_by_field(reports, field, top_n=2):
    counter = Counter()
    for report in reports:
        for name in parse_person_entries(get_report_value(report, field, "")):
            counter[name] += 1
    return counter.most_common(top_n)


if PAGE == "Ana Sayfa":
    st.markdown(
        "<div class='page-header'><h1>Ramp Koordine Nöbet Devir Sistemi</h1><p>Güncel devri takip edin, vardiya raporlarını hızlıca görüntüleyin.</p></div>",
        unsafe_allow_html=True,
    )

    today = date.today().isoformat()
    todays_reports = [r for r in reports if get_report_value(r, "Tarih", "") == today]

    overall_today = len(todays_reports)
    total_reports = len(reports)
    pending_reports = len(
        [
            r
            for r in reports
            if get_report_value(r, "Şoför Devralan", "") == ""
            or get_report_value(r, "Şoför Devreden", "") == ""
            or get_report_value(r, "YBT Devralan", "") == ""
            or get_report_value(r, "YBT Devreden", "") == ""
        ]
    )
    person_count_today = len(unique_personnel_names(todays_reports))
    total_person_count = len(unique_personnel_names(reports))

    s1, s2, s3, s4, s5 = st.columns(5)
    s1.markdown(
        f"<div class='metric-card'><h3>Bugünkü Raporlar</h3><p class='metric-value'>{overall_today}</p><p class='metric-label'>Bugün kaydedilen vardiya sayısı</p></div>",
        unsafe_allow_html=True,
    )
    s2.markdown(
        f"<div class='metric-card'><h3>Toplam Rapor</h3><p class='metric-value'>{total_reports}</p><p class='metric-label'>Sistemdeki tüm kayıtlar</p></div>",
        unsafe_allow_html=True,
    )
    s3.markdown(
        f"<div class='metric-card'><h3>Bugünkü Personeller</h3><p class='metric-value'>{person_count_today}</p><p class='metric-label'>Bugüne ait benzersiz personel sayısı</p></div>",
        unsafe_allow_html=True,
    )
    s4.markdown(
        f"<div class='metric-card'><h3>Toplam Personel</h3><p class='metric-value'>{total_person_count}</p><p class='metric-label'>Kayıtlı tüm vardiyalardaki benzersiz personel</p></div>",
        unsafe_allow_html=True,
    )
    s5.markdown(
        f"<div class='metric-card'><h3>Eksik Devir</h3><p class='metric-value'>{pending_reports}</p><p class='metric-label'>Devreden/devralan eksik kayıtlar</p></div>",
        unsafe_allow_html=True,
    )

    top_overtime = top_persons_by_field(todays_reports, "Mesaiye kalan personeller")
    top_early = top_persons_by_field(todays_reports, "Erken çıkan personeller")
    top_overtime_label = ", ".join([f"{name} ({count})" for name, count in top_overtime]) if top_overtime else "Yok"
    top_early_label = ", ".join([f"{name} ({count})" for name, count in top_early]) if top_early else "Yok"

    e1, e2 = st.columns(2)
    e1.markdown(
        f"<div class='metric-card'><h3>En Fazla Mesaiye Kalan</h3><p class='metric-value'>{top_overtime_label}</p><p class='metric-label'>Bugün en fazla mesai kalan kişiler</p></div>",
        unsafe_allow_html=True,
    )
    e2.markdown(
        f"<div class='metric-card'><h3>En Çok Erken Çıkan</h3><p class='metric-value'>{top_early_label}</p><p class='metric-label'>Bugün en çok erken çıkan kişiler</p></div>",
        unsafe_allow_html=True,
    )

    if reports:
        shift_counts = pd.DataFrame(
            [
                {
                    "Vardiya": shift,
                    "Rapor Sayısı": len([r for r in todays_reports if get_report_value(r, "Vardiya", "") == shift]),
                    "Personel Satırı": len(unique_personnel_names([r for r in todays_reports if get_report_value(r, "Vardiya", "") == shift])),
                }
                for shift in ["Sabah", "Orta", "Gece"]
            ]
        )
        chart_col1, chart_col2 = st.columns(2)
        chart_col1.markdown("### Vardiya Bazında Rapor Sayısı")
        chart_col1.bar_chart(shift_counts.set_index("Vardiya")["Rapor Sayısı"])
        chart_col2.markdown("### Vardiya Bazında Personel Satırı")
        chart_col2.bar_chart(shift_counts.set_index("Vardiya")["Personel Satırı"])
    else:
        st.info("Henüz rapor yok, grafik oluşturmak için rapor ekleyin.")

    st.markdown("<div class='section-title'>Bugünkü Vardiya Özetleri</div>", unsafe_allow_html=True)
    card_cols = st.columns(3)
    for col, shift in zip(card_cols, ["Sabah", "Orta", "Gece"]):
        shift_reports = [r for r in todays_reports if r["Vardiya"] == shift]
        status = "Beklemede" if not shift_reports else "Hazır"
        status_class = "status-ready" if shift_reports else "status-wait"
        count = len(shift_reports)
        col.markdown(
            f"<div class='card'><h3>{shift} Vardiyası</h3><p>{shift_times[shift]}</p><div class='status-pill {status_class}'>{status}</div><p><strong>{count}</strong> rapor</p></div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div class='section-title'>Son Devir Raporları</div>", unsafe_allow_html=True)
    if reports:
        recent = reports[-5:][::-1]
        for row in recent:
            with st.expander(
                f"{get_report_value(row, 'Tarih')} | {get_report_value(row, 'Vardiya')} | Şoför: {get_report_value(row, 'Şoför Devreden')} → {get_report_value(row, 'Şoför Devralan')} | YBT: {get_report_value(row, 'YBT Devreden')} → {get_report_value(row, 'YBT Devralan')}"
            ):
                st.markdown("<div class='report-block'>", unsafe_allow_html=True)
                st.write(f"**Önceki vardiyadan devam eden uçuşlar:** {get_report_value(row, 'Önceki vardiyadan devam eden uçuşlar')}")
                st.write(f"**Gün içerisinde bırakılan ekipman bilgisi:** {get_report_value(row, 'Gün içerisinde bırakılan ekipman bilgisi')}")
                st.write(f"**Erken çıkan personeller:** {get_report_value(row, 'Erken çıkan personeller')}")
                st.write(f"**Mesaiye kalan personeller:** {get_report_value(row, 'Mesaiye kalan personeller')}")
                st.write(f"**Bilgilendirme:** {get_report_value(row, 'Bilgilendirme')}")
                st.write(f"**Gelmeyen veya geç gelen personeller:** {get_report_value(row, 'Gelmeyen veya geç gelen personeller')}")
                left_col, right_col = st.columns(2)
                with left_col:
                    st.markdown("<div class='card'><h4>Şoför Tarafı</h4>", unsafe_allow_html=True)
                    st.write(f"**Şoför Devreden:** {get_report_value(row, 'Şoför Devreden')}")
                    st.write(f"**Şoför Devralan:** {get_report_value(row, 'Şoför Devralan')}")
                    st.markdown("</div>", unsafe_allow_html=True)
                with right_col:
                    st.markdown("<div class='card'><h4>YBT Tarafı</h4>", unsafe_allow_html=True)
                    st.write(f"**YBT Devreden:** {get_report_value(row, 'YBT Devreden')}")
                    st.write(f"**YBT Devralan:** {get_report_value(row, 'YBT Devralan')}")
                    st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Henüz kayıtlı rapor yok.")

elif PAGE == "Müdür Paneli":
    st.title("Müdür Paneli")
    st.markdown("##### Müdür için hızlı rapor inceleme, filtreleme ve dışa aktarma paneli")

    manager_left, manager_right = st.columns([2, 1])
    selected_date = manager_left.date_input("Tarih filtrele", value=date.today())
    export_scope = manager_right.selectbox("Gösterim / Dışa Aktarım", ["Tümü", "Bugün", "Eksik Devri Olan"])

    filtered_reports = [
        r
        for r in reports
        if (
            (export_scope != "Bugün" or get_report_value(r, "Tarih", "") == selected_date.isoformat())
            and (export_scope != "Eksik Devri Olan" or (
                get_report_value(r, "Şoför Devralan", "") == "" or
                get_report_value(r, "Şoför Devreden", "") == "" or
                get_report_value(r, "YBT Devralan", "") == "" or
                get_report_value(r, "YBT Devreden", "") == ""
            ))
        )
    ]

    st.markdown("<div class='metric-card'><h3>Rapor Özeti</h3><p>İlgili raporları hızlıca inceleyin ve dışa aktarın.</p></div>", unsafe_allow_html=True)

    total_today = len([r for r in reports if get_report_value(r, "Tarih", "") == selected_date.isoformat()])
    missing_count = len([r for r in reports if get_report_value(r, "Şoför Devralan", "") == "" or get_report_value(r, "Şoför Devreden", "") == "" or get_report_value(r, "YBT Devralan", "") == "" or get_report_value(r, "YBT Devreden", "") == ""])

    metric_cols = st.columns(4)
    metric_cols[0].metric("Toplam Rapor", len(reports))
    metric_cols[1].metric("Bugünkü Rapor", total_today)
    metric_cols[2].metric("Eksik Devri Olan", missing_count)
    metric_cols[3].metric("Filtrelenen", len(filtered_reports))

    download_cols = st.columns(2)
    download_cols[0].download_button(
        label="Excel Olarak Dışa Aktar",
        data=reports_to_excel(filtered_reports),
        file_name="mudur_filtreli_raporlar.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    download_cols[1].download_button(
        label="CSV Olarak Dışa Aktar",
        data=reports_to_csv(filtered_reports),
        file_name="mudur_filtreli_raporlar.csv",
        mime="text/csv",
    )

    if filtered_reports:
        st.markdown("<div class='section-title'>Filtrelenmiş Raporlar</div>", unsafe_allow_html=True)
        for idx, row in enumerate(filtered_reports[::-1], start=1):
            st.markdown(f"<div class='report-block'><h4>{idx}. {row['Tarih']} | {row['Vardiya']} | Şoför: {row['Şoför Devreden']} → {row['Şoför Devralan']} | YBT: {row['YBT Devreden']} → {row['YBT Devralan']}</h4>", unsafe_allow_html=True)
            st.write(f"**Kalan Uçuşlar:** {get_report_value(row, 'Önceki vardiyadan devam eden uçuşlar')}")
            st.write(f"**Ekipman:** {get_report_value(row, 'Gün içerisinde bırakılan ekipman bilgisi')}")
            st.write(f"**Erken çıkan:** {get_report_value(row, 'Erken çıkan personeller')}")
            st.write(f"**Mesaiye kalan:** {get_report_value(row, 'Mesaiye kalan personeller')}")
            st.write(f"**Not:** {get_report_value(row, 'Bilgilendirme')}")
            st.write(f"**Gelmeyen/geç gelen:** {get_report_value(row, 'Gelmeyen veya geç gelen personeller')}")
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Seçilen filtreye uygun rapor bulunamadı.")

elif PAGE == "Yeni Devir Oluştur":
    st.title("Yeni Devir Oluştur")
    st.markdown("##### Basit ve hızlı form — alanlar alt alta sıralandı")

    # Inject small JS to prevent Enter from submitting forms except inside textareas
    prevent_enter_js = """
    <script>
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') {
        const el = document.activeElement;
        if (el && el.tagName !== 'TEXTAREA') {
          e.preventDefault();
          e.stopPropagation();
        }
      }
    }, true);
    </script>
    """
    st_html(prevent_enter_js, height=0)

    with st.form(key="new_report_form_simple"):
        st.markdown("<div class='page-header'><h1>Nöbet Raporu</h1></div>", unsafe_allow_html=True)
        selected_date = st.date_input("Tarih", value=date.today())
        # Vardiya formdan kaldırıldı per kullanıcı isteği; kayıtta 'NIL' olacak
        vardiya = "NIL"
        prev_flights = st.text_area("Önceki vardiyadan devam eden uçuşlar", height=80)
        equipment = st.text_area("Gün içerisinde bırakılan ekipman bilgisi", height=80)
        early_staff = st.text_area("Erken çıkan personeller", height=60)
        overtime_staff = st.text_area("Mesaiye kalan personeller", height=60)
        missing_staff = st.text_area("Gelmeyen veya geç gelen personeller", height=60)

        st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
        # Vardiya kaldırıldığı için varsayılan saatleri mevcut saate göre ayarla
        if vardiya == "NIL":
            default_start_time = datetime.now().time().replace(second=0, microsecond=0)
        else:
            shift_range = shift_times.get(vardiya, "00:00 - 00:00")
            start_str = shift_range.split("-")[0].strip() if "-" in shift_range else shift_range.strip()
            try:
                default_start_time = datetime.strptime(start_str, "%H:%M").time()
            except Exception:
                default_start_time = datetime.now().time().replace(second=0, microsecond=0)
        left_side, right_side = st.columns([1, 1])
        with left_side:
            st.markdown("### YBT Tarafı")
            ## seçimli isim alanları (ön tanımlı listeden)
            name_options = ["NIL"] + PERSONNEL_OPTIONS + ["Diğer"]
            ybt_devreden_sel = st.selectbox("YBT Devreden (isim)", name_options, index=0, key="ybt_devreden_sel")
            if ybt_devreden_sel == "Diğer":
                ybt_devreden = st.text_input("YBT Devreden (diğer isim)", value="", key="ybt_devreden_custom")
            else:
                ybt_devreden = ybt_devreden_sel
            ybt_devreden_saat = st.time_input("YBT Devreden Saati", value=default_start_time, key="ybt_devreden_saat")

            ybt_devralan_sel = st.selectbox("YBT Devralan (isim)", name_options, index=0, key="ybt_devralan_sel")
            if ybt_devralan_sel == "Diğer":
                ybt_devralan = st.text_input("YBT Devralan (diğer isim)", value="", key="ybt_devralan_custom")
            else:
                ybt_devralan = ybt_devralan_sel
            ybt_devralan_saat = st.time_input("YBT Devralan Saati", value=default_start_time, key="ybt_devralan_saat")
        with right_side:
            st.markdown("### Şoför Tarafı")
            name_options = ["NIL"] + PERSONNEL_OPTIONS + ["Diğer"]
            sofor_devreden_sel = st.selectbox("Şoför Devreden (isim)", name_options, index=0, key="sofor_devreden_sel")
            if sofor_devreden_sel == "Diğer":
                sofor_devreden = st.text_input("Şoför Devreden (diğer isim)", value="", key="sofor_devreden_custom")
            else:
                sofor_devreden = sofor_devreden_sel
            sofor_devreden_saat = st.time_input("Şoför Devreden Saati", value=default_start_time, key="sofor_devreden_saat")

            sofor_devralan_sel = st.selectbox("Şoför Devralan (isim)", name_options, index=0, key="sofor_devralan_sel")
            if sofor_devralan_sel == "Diğer":
                sofor_devralan = st.text_input("Şoför Devralan (diğer isim)", value="", key="sofor_devralan_custom")
            else:
                sofor_devralan = sofor_devralan_sel
            sofor_devralan_saat = st.time_input("Şoför Devralan Saati", value=default_start_time, key="sofor_devralan_saat")

        # Personel listesi kaldırıldı (kayda NIL yazılacak)
        note = st.text_area("Notlar / Bilgilendirme", height=80)

        submitted = st.form_submit_button("Kaydet")

        if submitted:
            def normalize_name(v):
                if v is None:
                    return "NIL"
                if isinstance(v, str):
                    s = v.strip()
                    return s if s else "NIL"
                try:
                    return str(v)
                except Exception:
                    return "NIL"

            report = {
                "Tarih": selected_date.isoformat(),
                "Vardiya": vardiya,
                "Önceki vardiyadan devam eden uçuşlar": prev_flights.strip() or "NIL",
                "Gün içerisinde bırakılan ekipman bilgisi": equipment.strip() or "NIL",
                "Personel listesi": "NIL",
                "Erken çıkan personeller": early_staff.strip() or "NIL",
                "Mesaiye kalan personeller": overtime_staff.strip() or "NIL",
                "Gelmeyen veya geç gelen personeller": missing_staff.strip() or "NIL",
                "Extra verilen hizmetler / ekipman takibi": "NIL",
                "Bilgilendirme": note.strip() or "NIL",
                "Şoför Devreden": normalize_name(sofor_devreden),
                "Şoför Devralan": normalize_name(sofor_devralan),
                "Şoför Devreden Saati": sofor_devreden_saat.strftime("%H:%M") if hasattr(sofor_devreden_saat, 'strftime') else (sofor_devreden_saat or "NIL"),
                "Şoför Devralan Saati": sofor_devralan_saat.strftime("%H:%M") if hasattr(sofor_devralan_saat, 'strftime') else (sofor_devralan_saat or "NIL"),
                "YBT Devreden": normalize_name(ybt_devreden),
                "YBT Devralan": normalize_name(ybt_devralan),
                "YBT Devreden Saati": ybt_devreden_saat.strftime("%H:%M") if hasattr(ybt_devreden_saat, 'strftime') else (ybt_devreden_saat or "NIL"),
                "YBT Devralan Saati": ybt_devralan_saat.strftime("%H:%M") if hasattr(ybt_devralan_saat, 'strftime') else (ybt_devralan_saat or "NIL"),
            }
            # Debug: göster hangi değerlerle kaydediliyor
            st.json(report)
            save_report(report)
            st.success("Devir raporu kaydedildi.")
            st.markdown(f"**Kaydedilen:** Şoför: {report['Şoför Devreden']} → {report['Şoför Devralan']}, YBT: {report['YBT Devreden']} → {report['YBT Devralan']}")
            reports = load_reports()

elif PAGE == "Devir Raporları":
    st.title("Devir Raporları")
    st.markdown("##### Tüm kayıtlar ve filtreleme")
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    date_filter = filter_col1.date_input("Tarih filtrele", value=date.today())
    shift_filter = filter_col2.selectbox("Vardiya filtrele", ["Tümü", "Sabah", "Orta", "Gece"])
    search_text = filter_col3.text_input("Ara (Şoför/YBT/Personel)")

    filtered = [
        r
        for r in reports
        if (get_report_value(r, "Tarih", "") == date_filter.isoformat() or not date_filter)
        and (shift_filter == "Tümü" or get_report_value(r, "Vardiya", "") == shift_filter)
        and (
            search_text.lower() in get_report_value(r, "Şoför Devreden", "").lower()
            or search_text.lower() in get_report_value(r, "Şoför Devralan", "").lower()
            or search_text.lower() in get_report_value(r, "YBT Devreden", "").lower()
            or search_text.lower() in get_report_value(r, "YBT Devralan", "").lower()
        )
    ]

    f1, f2, f3 = st.columns(3)
    f1.metric("Filtrelenen Kayıtlar", len(filtered))
    f2.metric("Seçilen Vardiya", shift_filter)
    f3.metric("Arama Terimi", search_text or "Yok")

    st.markdown("<div class='section-title'>Rapor Listesi</div>", unsafe_allow_html=True)

    if filtered:
        st.dataframe(filtered, use_container_width=True)
        st.markdown("<div class='section-title'>Detaylı Kayıtlar</div>", unsafe_allow_html=True)
        for row in filtered[::-1]:
            with st.expander(
                f"{get_report_value(row, 'Tarih')} | {get_report_value(row, 'Vardiya')} | Şoför: {get_report_value(row, 'Şoför Devreden')} → {get_report_value(row, 'Şoför Devralan')} | YBT: {get_report_value(row, 'YBT Devreden')} → {get_report_value(row, 'YBT Devralan')}"
            ):
                st.markdown("<div class='report-block'>", unsafe_allow_html=True)
                st.markdown(
                    f"""
                    <div class='report-item'><strong>Önceki vardiyadan devam eden uçuşlar</strong><div class='item-value'>{get_report_value(row, 'Önceki vardiyadan devam eden uçuşlar')}</div></div>
                    <div class='report-item'><strong>Gün içerisinde bırakılan ekipman bilgisi</strong><div class='item-value'>{get_report_value(row, 'Gün içerisinde bırakılan ekipman bilgisi')}</div></div>
                    <div class='report-item'><strong>Erken çıkan personeller</strong><div class='item-value'>{get_report_value(row, 'Erken çıkan personeller')}</div></div>
                    <div class='report-item'><strong>Mesaiye kalan personeller</strong><div class='item-value'>{get_report_value(row, 'Mesaiye kalan personeller')}</div></div>
                    <div class='report-item'><strong>Bilgilendirme</strong><div class='item-value'>{get_report_value(row, 'Bilgilendirme')}</div></div>
                    <div class='report-item'><strong>Gelmeyen veya geç gelen personeller</strong><div class='item-value'>{get_report_value(row, 'Gelmeyen veya geç gelen personeller')}</div></div>
                    """,
                    unsafe_allow_html=True,
                )
                col_left, col_right = st.columns(2)
                with col_left:
                    st.markdown("<div class='card'><h4>Şoför Tarafı</h4>", unsafe_allow_html=True)
                    st.write(f"**Şoför Devreden:** {get_report_value(row, 'Şoför Devreden')}")
                    st.write(f"**Şoför Devralan:** {get_report_value(row, 'Şoför Devralan')}")
                    st.markdown("</div>", unsafe_allow_html=True)
                with col_right:
                    st.markdown("<div class='card'><h4>YBT Tarafı</h4>", unsafe_allow_html=True)
                    st.write(f"**YBT Devreden:** {get_report_value(row, 'YBT Devreden')}")
                    st.write(f"**YBT Devralan:** {get_report_value(row, 'YBT Devralan')}")
                    st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Bu filtreye uyan kayıt bulunamadı.")
