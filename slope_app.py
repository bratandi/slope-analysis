import streamlit as st
from pyslope import Slope, Material, Udl, LineLoad
import plotly.graph_objects as go
import pandas as pd
import math

st.set_page_config(
    page_title="Стійкість лесового схилу",
    page_icon="⛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== CSS =====
st.markdown("""
<style>
/* ---- Metric cards ---- */
.mcard {
    border-radius: 12px;
    padding: 14px 16px;
    text-align: center;
    margin-bottom: 8px;
}
.mcard-green  { background: linear-gradient(145deg,#1b5e20,#2e7d32); border: 1px solid #4caf50; }
.mcard-yellow { background: linear-gradient(145deg,#bf360c,#e64a19); border: 1px solid #ff7043; }
.mcard-red    { background: linear-gradient(145deg,#b71c1c,#c62828); border: 1px solid #f44336; }
.mcard-blue   { background: linear-gradient(145deg,#0d47a1,#1976d2); border: 1px solid #42a5f5; }
.mcard-gray   { background: linear-gradient(145deg,#263238,#37474f); border: 1px solid #78909c; }
.mcard-lbl  { font-size: 0.7rem; color: rgba(255,255,255,0.6); text-transform: uppercase; letter-spacing: 0.7px; margin-bottom: 5px; }
.mcard-val  { font-size: 2.1rem; font-weight: 700; color: #fff; line-height: 1.15; }
.mcard-badge{ font-size: 0.78rem; font-weight: 600; color: rgba(255,255,255,0.92); margin-top: 5px; }
.mcard-sub  { font-size: 0.72rem; color: rgba(255,255,255,0.55); margin-top: 3px; }

/* ---- Header banner ---- */
.hdr-banner {
    background: linear-gradient(135deg,#1a237e 0%,#283593 60%,#1565c0 100%);
    border-radius: 14px;
    padding: 22px 28px;
    margin-bottom: 20px;
    border-left: 5px solid #42a5f5;
}
.hdr-banner h1 { color:#fff; margin:0 0 6px 0; font-size:1.75rem; font-weight:700; }
.hdr-banner p  { color:rgba(255,255,255,0.72); margin:0; font-size:0.88rem; line-height:1.5; }
.hdr-tag {
    display: inline-block;
    background: rgba(255,255,255,0.13);
    border-radius: 20px;
    padding: 3px 11px;
    font-size: 0.76rem;
    color: rgba(255,255,255,0.88);
    margin: 8px 4px 0 0;
    border: 1px solid rgba(255,255,255,0.2);
}

/* ---- Conclusion block ---- */
.conclusion {
    border-radius: 10px;
    padding: 13px 18px;
    margin-top: 16px;
    font-size: 0.92rem;
    line-height: 1.5;
    border-left: 4px solid;
}
.c-ok     { background: rgba(46,125,50,0.18);  border-color: #4caf50; color: #a5d6a7; }
.c-warn   { background: rgba(230,74,25,0.18);  border-color: #ff7043; color: #ffccbc; }
.c-danger { background: rgba(198,40,40,0.18);  border-color: #f44336; color: #ef9a9a; }

/* ---- Tabs ---- */
.stTabs [data-baseweb="tab"] { font-size: 13.5px; padding: 8px 16px; font-weight: 500; }
</style>
""", unsafe_allow_html=True)

# ===== HEADER =====
st.markdown("""
<div class="hdr-banner">
  <h1>⛰️ Аналіз стійкості лесового схилу</h1>
  <p>Розрахунок коефіцієнта стійкості методом спрощеного Бішопа для двошарових лесових схилів
     з оцінкою ефективності природних армуючих матеріалів</p>
  <div>
    <span class="hdr-tag">📐 Метод Бішопа</span>
    <span class="hdr-tag">🪨 Двошарова геологія</span>
    <span class="hdr-tag">🌿 Природне армування</span>
    <span class="hdr-tag">📊 Параметричний аналіз</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ===== САЙДБАР =====
with st.sidebar:
    st.markdown("## ⚙️ Параметри розрахунку")

    with st.expander("📐 Геометрія схилу", expanded=True):
        H = st.slider("Висота H (м)", 2.0, 20.0, 8.0, 0.5,
                      help="Висота схилу від підошви до гребеня (м)")
        beta = st.slider("Кут укосу β (°)", 10.0, 70.0, 30.0, 1.0,
                         help="Кут нахилу укосу до горизонталі. Для лесових схилів типово 20–40°")
        iterations = st.select_slider(
            "Точність розрахунку",
            options=[500, 1000, 2000, 3000],
            value=1000,
            help="Кількість ітерацій при пошуку критичної поверхні ковзання. Більше = точніше, але повільніше"
        )

    with st.expander("🟧 Шар 1 — Лес (верхній)", expanded=True):
        st.caption("Верхній шар ґрунту — лесовий суглинок")
        depth1 = st.slider(
            "Глибина шару 1 (м від поверхні)",
            1.0, H, min(H/2, 5.0), 0.5,
            help="Потужність лесового шару від поверхні до підошви"
        )
        st.markdown("**🌤️ Природний стан:**")
        c1_nat = st.slider("c₁ природний (кПа)", 1.0, 50.0, 25.0, 1.0,
                           help="Питоме зчеплення лесу в природному стані. Типово 20–35 кПа")
        phi1_nat = st.slider("φ₁ природний (°)", 5.0, 40.0, 22.0, 1.0,
                             help="Кут внутрішнього тертя лесу в природному стані. Типово 20–25°")
        g1_nat = st.slider("γ₁ природний (кН/м³)", 14.0, 22.0, 17.0, 0.5,
                           help="Питома вага лесу в природному стані. Типово 16–18 кН/м³")
        st.markdown("**💧 Замочений стан:**")
        c1_wet = st.slider("c₁ замочений (кПа)", 1.0, 30.0, 8.0, 1.0,
                           help="Зчеплення лесу після замочування — зменшується в 2–4 рази!")
        phi1_wet = st.slider("φ₁ замочений (°)", 5.0, 35.0, 14.0, 1.0,
                             help="Кут тертя лесу після замочування — зменшується на 30–40%")
        g1_wet = st.slider("γ₁ замочений (кН/м³)", 15.0, 22.0, 19.0, 0.5,
                           help="Питома вага лесу після насичення водою")

    with st.expander("🟦 Шар 2 — Підстильний (нижній)", expanded=True):
        st.caption("Нижній шар — суглинок або глина")
        layer2_type = st.selectbox("Тип підстильного шару", [
            "Суглинок",
            "Глина тверда",
            "Глина м'яка",
            "Пісок",
            "Власні параметри"
        ], help="Тип підстильного ґрунту під лесовим шаром")
        layer2_presets = {
            "Суглинок":      (15, 18, 19.0),
            "Глина тверда":  (25, 12, 19.5),
            "Глина м'яка":   (10,  8, 18.0),
            "Пісок":         ( 0, 30, 18.5),
            "Власні параметри": (15, 15, 19.0),
        }
        dc2, dp2, dg2 = layer2_presets[layer2_type]
        if layer2_type == "Власні параметри":
            c2_layer = st.slider("c₂ (кПа)", 0.0, 50.0, float(dc2), 1.0)
            phi2_layer = st.slider("φ₂ (°)", 0.0, 40.0, float(dp2), 1.0)
            g2_layer = st.slider("γ₂ (кН/м³)", 15.0, 22.0, float(dg2), 0.5)
        else:
            c2_layer = float(dc2)
            phi2_layer = float(dp2)
            g2_layer = float(dg2)
            st.info(f"c = {c2_layer} кПа | φ = {phi2_layer}° | γ = {g2_layer} кН/м³")

        depth2 = H + st.slider(
            "Глибина шару 2 нижче підошви (м)",
            1.0, 15.0, 5.0, 0.5,
            help="На яку глибину нижче підошви схилу поширюється другий шар"
        )

    with st.expander("💧 Рівень ґрунтових вод", expanded=True):
        wt_mode = st.radio("Режим ГРВ", [
            "Без ГРВ",
            "ГРВ у шарі 1",
            "ГРВ у шарі 2"
        ], help="Положення рівня ґрунтових вод відносно шарів ґрунту")
        if wt_mode == "ГРВ у шарі 1":
            wt = st.slider("Глибина ГРВ (м)", 0.1, depth1, min(depth1*0.5, 2.0), 0.1,
                           help="Глибина ГРВ від поверхні в межах першого (лесового) шару")
        elif wt_mode == "ГРВ у шарі 2":
            wt = st.slider("Глибина ГРВ (м) ", depth1, H, depth1 + 1.0, 0.1,
                           help="Глибина ГРВ від поверхні в межах другого шару")
        else:
            wt = None

    with st.expander("🏗️ Зовнішнє навантаження", expanded=False):
        use_udl = st.checkbox("Рівномірне навантаження (UDL)",
                              help="Рівномірно розподілене навантаження на гребені схилу")
        if use_udl:
            udl_mag = st.slider("Величина (кПа)", 1.0, 200.0, 50.0, 5.0)
            udl_offset = st.slider("Відступ від гребеня (м)", 0.0, 10.0, 0.0, 0.5)
            udl_length = st.slider("Довжина (м)", 1.0, 20.0, 5.0, 0.5)
        use_ll = st.checkbox("Зосереджене навантаження",
                             help="Лінійне зосереджене навантаження (від стіни, дороги тощо)")
        if use_ll:
            ll_mag = st.slider("Величина (кН/м)", 1.0, 500.0, 100.0, 10.0)
            ll_offset = st.slider("Відступ (м)", 0.0, 10.0, 2.0, 0.5)

    with st.expander("🌿 Армуючий матеріал", expanded=True):
        arm_type = st.selectbox("Тип матеріалу", [
            "Кокосове волокно",
            "Джутова геосітка",
            "Бамбукові палі",
            "Фашини (верба)",
            "Власні параметри"
        ], help="Природний армуючий матеріал для зміцнення схилу")
        arm_layer = st.radio("Армується шар", ["Тільки шар 1", "Обидва шари"],
                             help="Який шар зміцнюється армуванням")

        presets = {
            "Кокосове волокно":  (13, 17),
            "Джутова геосітка":  (10, 15),
            "Бамбукові палі":    (15, 18),
            "Фашини (верба)":    (11, 16),
            "Власні параметри":  (12, 16),
        }
        dc, dp = presets[arm_type]
        if arm_type == "Власні параметри":
            c_arm = st.slider("c після армування (кПа)", 1.0, 50.0, float(dc), 1.0)
            phi_arm = st.slider("φ після армування (°)", 5.0, 40.0, float(dp), 1.0)
        else:
            c_arm = float(dc)
            phi_arm = float(dp)
            st.info(f"c = {c_arm} кПа | φ = {phi_arm}°")

    st.markdown("---")
    st.markdown(
        f"<div style='font-size:0.72rem;color:rgba(255,255,255,0.35);text-align:center'>"
        f"H={H:.0f}м | β={beta:.0f}° | {iterations} іт.<br>"
        f"Шар 1: {depth1:.1f}м | Шар 2: {layer2_type}"
        f"</div>",
        unsafe_allow_html=True
    )


# ===== ФУНКЦІЯ ПОБУДОВИ СХИЛУ =====
def build_slope(
    c_top, phi_top, g_top,
    c_bot=None, phi_bot=None, g_bot=None,
    water=None,
    with_load=False
):
    s = Slope(height=H, angle=beta, length=None)
    s.update_analysis_options(slices=50, iterations=iterations)

    s.set_materials(Material(
        unit_weight=g_top,
        friction_angle=phi_top,
        cohesion=c_top,
        depth_to_bottom=depth1
    ))

    _c2 = c_bot if c_bot is not None else c2_layer
    _p2 = phi_bot if phi_bot is not None else phi2_layer
    _g2 = g_bot if g_bot is not None else g2_layer

    s.set_materials(Material(
        unit_weight=_g2,
        friction_angle=_p2,
        cohesion=_c2,
        depth_to_bottom=depth2
    ))

    if water is not None:
        s.set_water_table(water)

    if with_load and use_udl:
        s.set_udls(Udl(magnitude=udl_mag, offset=udl_offset, length=udl_length))
    if with_load and use_ll:
        s.set_lls(LineLoad(magnitude=ll_mag, offset=ll_offset))

    s.set_analysis_limits(
        s.get_top_coordinates()[0] - 3,
        s.get_bottom_coordinates()[0] + 3
    )
    s.analyse_slope()
    return s


# ===== ДОПОМІЖНІ ФУНКЦІЇ =====
def fs_label(fs):
    if fs >= 1.5: return "✅ СТІЙКИЙ"
    elif fs >= 1.2: return "⚠️ ЗАДОВІЛЬНИЙ"
    elif fs >= 1.0: return "🔶 ГРАНИЧНИЙ"
    else: return "❌ ЗСУВ!"

def fs_color(fs):
    if fs >= 1.5: return "normal"
    elif fs >= 1.0: return "off"
    else: return "inverse"

def card_cls(fs):
    if fs >= 1.5: return "mcard-green"
    elif fs >= 1.2: return "mcard-yellow"
    else: return "mcard-red"


# ===== РОЗРАХУНОК =====
try:
    with st.spinner("⏳ Розраховуємо..."):

        s1 = build_slope(c1_nat, phi1_nat, g1_nat)
        fs1 = s1.get_min_FOS()

        s2 = build_slope(c1_wet, phi1_wet, g1_wet, water=wt, with_load=True)
        fs2 = s2.get_min_FOS()

        if arm_layer == "Обидва шари":
            c2_armed = min(c2_layer * 1.3, c2_layer + 5)
            phi2_armed = min(phi2_layer + 2, phi2_layer * 1.1)
        else:
            c2_armed = c2_layer
            phi2_armed = phi2_layer

        s3 = build_slope(
            c_arm, phi_arm, g1_wet,
            c_bot=c2_armed, phi_bot=phi2_armed,
            water=wt, with_load=True
        )
        fs3 = s3.get_min_FOS()

    # ===== ГЕОЛОГІЧНИЙ РОЗРІЗ =====
    st.subheader("🗺️ Геологічний розріз")

    L = H / math.tan(beta * math.pi / 180)
    layer1_bottom = H - depth1
    bottom = -(depth2 - H)
    x_intersect = L * depth1 / H
    platform = L * 0.4

    fig_geo = go.Figure()

    fig_geo.add_trace(go.Scatter(
        x=[-platform, -platform, x_intersect, L, L + platform, L + platform, -platform],
        y=[bottom, layer1_bottom, layer1_bottom, 0, 0, bottom, bottom],
        fill="toself",
        fillcolor="rgba(72, 209, 204, 0.55)",
        line=dict(color="rgba(0,150,150,0.9)", width=1.5),
        name=f"Шар 2 — {layer2_type}",
        mode="lines"
    ))

    fig_geo.add_trace(go.Scatter(
        x=[-platform, -platform, 0, x_intersect, 0, -platform],
        y=[layer1_bottom, H, H, layer1_bottom, layer1_bottom, layer1_bottom],
        fill="toself",
        fillcolor="rgba(250, 160, 122, 0.6)",
        line=dict(color="rgba(200,80,60,0.9)", width=1.5),
        name="Шар 1 — Лес",
        mode="lines"
    ))

    fig_geo.add_trace(go.Scatter(
        x=[-platform, 0, 0, L, L + platform],
        y=[H, H, H, 0, 0],
        mode="lines",
        line=dict(color="white", width=2.5),
        showlegend=False
    ))

    fig_geo.add_trace(go.Scatter(
        x=[-platform, x_intersect],
        y=[layer1_bottom, layer1_bottom],
        mode="lines",
        line=dict(color="#ff6b6b", width=2, dash="dash"),
        name=f"Межа шарів ({depth1} м)"
    ))

    if wt is not None:
        wt_y = H - wt
        x_end = L * (H - wt_y) / H if wt_y >= 0 else L + platform
        fig_geo.add_trace(go.Scatter(
            x=[-platform, x_end],
            y=[wt_y, wt_y],
            mode="lines",
            line=dict(color="#64b5f6", width=2.5, dash="dot"),
            name=f"💧 ГРВ на глиб. {wt} м"
        ))

    fig_geo.add_annotation(
        x=-platform * 0.5, y=(layer1_bottom + H) / 2,
        text=f"<b>Шар 1: Лес</b><br>c={c1_nat} кПа | φ={phi1_nat}°<br>γ={g1_nat} кН/м³",
        showarrow=False,
        font=dict(size=10, color="rgb(255,210,190)"),
        bgcolor="rgba(60,20,10,0.7)",
        bordercolor="rgba(200,80,60,0.6)",
        borderwidth=1, borderpad=4
    )
    fig_geo.add_annotation(
        x=L * 0.6, y=(layer1_bottom + bottom) / 2,
        text=f"<b>Шар 2: {layer2_type}</b><br>c={c2_layer} кПа | φ={phi2_layer}°<br>γ={g2_layer} кН/м³",
        showarrow=False,
        font=dict(size=10, color="rgb(180,255,255)"),
        bgcolor="rgba(0,40,40,0.7)",
        bordercolor="rgba(0,150,150,0.6)",
        borderwidth=1, borderpad=4
    )

    fig_geo.update_layout(
        height=330,
        showlegend=True,
        legend=dict(
            x=1.01, y=1.0,
            xanchor="left", yanchor="top",
            bgcolor="rgba(15,15,25,0.85)",
            bordercolor="rgba(255,255,255,0.15)",
            borderwidth=1,
            font=dict(size=11)
        ),
        xaxis=dict(
            title="Відстань (м)",
            range=[-platform - 0.5, L + platform + 0.5],
            gridcolor="rgba(255,255,255,0.07)",
            zeroline=False
        ),
        yaxis=dict(
            title="Позначка (м)",
            range=[bottom - 0.5, H + 1.2],
            gridcolor="rgba(255,255,255,0.07)",
            zeroline=True,
            zerolinecolor="rgba(255,255,255,0.2)",
            zerolinewidth=1
        ),
        margin=dict(t=10, b=20, l=55, r=170),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(20,25,40,0.6)"
    )
    st.plotly_chart(fig_geo, use_container_width=True)

    # ===== МЕТРИКИ =====
    st.markdown("---")
    st.subheader("📊 Результати розрахунку")

    col1, col2, col3 = st.columns(3)
    wt_info = f"ГРВ = {wt} м" if wt else "без ГРВ"

    with col1:
        st.markdown(f"""
        <div class="mcard {card_cls(fs1)}">
            <div class="mcard-lbl">Fs природний</div>
            <div class="mcard-val">{fs1:.3f}</div>
            <div class="mcard-badge">{fs_label(fs1)}</div>
            <div class="mcard-sub">двошаровий · без ГРВ</div>
        </div>""", unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="mcard {card_cls(fs2)}">
            <div class="mcard-lbl">Fs замочений</div>
            <div class="mcard-val">{fs2:.3f}</div>
            <div class="mcard-badge">{fs_label(fs2)}</div>
            <div class="mcard-sub">{wt_info} · з навантаженням</div>
        </div>""", unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="mcard {card_cls(fs3)}">
            <div class="mcard-lbl">Fs + армування</div>
            <div class="mcard-val">{fs3:.3f}</div>
            <div class="mcard-badge">{fs_label(fs3)}</div>
            <div class="mcard-sub">{arm_type[:18]} · {arm_layer[:10]}</div>
        </div>""", unsafe_allow_html=True)

    col4, col5 = st.columns(2)
    loss_pct = (fs1 - fs2) / fs1 * 100
    gain_pct = (fs3 - fs2) / max(fs2, 0.001) * 100

    with col4:
        st.markdown(f"""
        <div class="mcard mcard-blue">
            <div class="mcard-lbl">Втрата при замочуванні</div>
            <div class="mcard-val">−{fs1-fs2:.3f}</div>
            <div class="mcard-badge">−{loss_pct:.1f}% від природного Fs</div>
        </div>""", unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
        <div class="mcard mcard-gray">
            <div class="mcard-lbl">Ефект армування</div>
            <div class="mcard-val">+{fs3-fs2:.3f}</div>
            <div class="mcard-badge">+{gain_pct:.1f}% до замоченого Fs</div>
        </div>""", unsafe_allow_html=True)

    # ===== ВИСНОВОК =====
    need = max(0, 1.5 - fs3)
    if fs3 >= 1.5:
        c_cls, icon = "c-ok", "✅"
        msg = (f"Схил <b>стійкий</b> в усіх сценаріях. {arm_type} забезпечує "
               f"Fs = {fs3:.3f} ≥ 1.5 — норма ДБН виконана.")
    elif fs3 >= 1.2:
        c_cls, icon = "c-warn", "⚠️"
        msg = (f"Стійкість <b>задовільна</b>, але нижче норми. Після армування Fs = {fs3:.3f}. "
               f"До норми 1.5 бракує ще <b>+{need:.3f}</b>. Рекомендується комплексне зміцнення.")
    elif fs3 >= 1.0:
        c_cls, icon = "c-danger", "🔶"
        msg = (f"Стійкість <b>гранична</b> навіть після армування (Fs = {fs3:.3f}). "
               f"Необхідні додаткові заходи: підпірні стінки, дренаж, терасування.")
    else:
        c_cls, icon = "c-danger", "❌"
        msg = (f"<b>Зсув!</b> Схил нестійкий після замочування (Fs = {fs2:.3f}) та армування "
               f"(Fs = {fs3:.3f}). Потрібне проектування капітальних підпірних конструкцій.")

    st.markdown(f"""
    <div class="conclusion {c_cls}">
    {icon} <b>Висновок:</b> {msg}
    </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ===== ВКЛАДКИ =====
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔄 Поверхні ковзання",
        "📊 Порівняння Fs",
        "📈 Параметричний аналіз",
        "🗺️ Всі поверхні",
        "📋 Таблиця та експорт"
    ])

    with tab1:
        st.markdown("### Критичні поверхні ковзання")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"**Природний** — Fs = {fs1:.3f} {fs_label(fs1)}")
            fig1 = s1.plot_critical()
            fig1.update_layout(height=380, margin=dict(t=20,b=10,l=10,r=10))
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            st.markdown(f"**Замочений** — Fs = {fs2:.3f} {fs_label(fs2)}")
            fig2 = s2.plot_critical()
            fig2.update_layout(height=380, margin=dict(t=20,b=10,l=10,r=10))
            st.plotly_chart(fig2, use_container_width=True)
        with col3:
            st.markdown(f"**З армуванням ({arm_type[:12]})** — Fs = {fs3:.3f} {fs_label(fs3)}")
            fig3 = s3.plot_critical()
            fig3.update_layout(height=380, margin=dict(t=20,b=10,l=10,r=10))
            st.plotly_chart(fig3, use_container_width=True)

        st.markdown("---")
        st.markdown("### Порівняння всіх армуючих матеріалів")
        with st.spinner("Розраховуємо всі матеріали..."):
            all_mats = {
                "🥥 Кокосове волокно": (13, 17),
                "🌾 Джутова геосітка": (10, 15),
                "🎋 Бамбукові палі":   (15, 18),
                "🌿 Фашини (верба)":   (11, 16),
            }
            mat_names, mat_fs = [], []
            for name, (cm, pm) in all_mats.items():
                try:
                    _s = build_slope(cm, pm, g1_wet, water=wt)
                    mat_names.append(name)
                    mat_fs.append(round(_s.get_min_FOS(), 3))
                except:
                    pass

        if mat_fs:
            colors_mat = ["#4caf50" if f >= 1.5 else
                          "#ff9800" if f >= 1.0 else
                          "#f44336" for f in mat_fs]
            fig_mat = go.Figure(go.Bar(
                x=mat_names, y=mat_fs,
                marker_color=colors_mat,
                text=[f"{f:.3f}" for f in mat_fs],
                textposition="outside",
                width=0.5
            ))
            fig_mat.add_hline(y=1.5, line_dash="dash", line_color="#4caf50",
                              annotation_text="Норма Fs = 1.5 (ДБН)", annotation_font_color="#4caf50")
            fig_mat.add_hline(y=1.0, line_dash="dash", line_color="#f44336",
                              annotation_text="Зсув Fs = 1.0", annotation_font_color="#f44336")
            fig_mat.update_layout(
                title="Ефективність природних матеріалів (замочений двошаровий схил)",
                yaxis_title="Fs",
                height=400,
                showlegend=False,
                yaxis=dict(range=[0, max(mat_fs)*1.35]),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(20,25,40,0.5)"
            )
            st.plotly_chart(fig_mat, use_container_width=True)

    with tab2:
        col_a, col_b = st.columns([2, 1])
        with col_a:
            colors = ["#4caf50" if f >= 1.5 else
                      "#ff9800" if f >= 1.0 else
                      "#f44336" for f in [fs1, fs2, fs3]]
            fig_bar = go.Figure(go.Bar(
                x=["🌤️ Природний\n(2 шари)",
                   "💧 Замочений\n(2 шари)",
                   f"🌿 З армуванням\n({arm_type[:14]})"],
                y=[fs1, fs2, fs3],
                marker_color=colors,
                text=[f"{f:.3f}" for f in [fs1, fs2, fs3]],
                textposition="outside",
                width=0.4
            ))
            fig_bar.add_hline(y=1.5, line_dash="dash", line_color="#4caf50",
                              annotation_text="Fs = 1.5 (ДБН)", annotation_font_color="#4caf50")
            fig_bar.add_hline(y=1.0, line_dash="dash", line_color="#f44336",
                              annotation_text="Fs = 1.0 (зсув)", annotation_font_color="#f44336")
            fig_bar.update_layout(
                title="Порівняння Fs — двошарова геологія",
                yaxis_title="Коефіцієнт стійкості Fs",
                height=440,
                showlegend=False,
                yaxis=dict(range=[0, max(fs1, fs2, fs3)*1.35]),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(20,25,40,0.5)"
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_b:
            st.markdown("**📋 Геологія:**")
            st.info(f"Шар 1: Лес ({depth1} м)\nШар 2: {layer2_type}")
            st.markdown("**🎯 Висновок:**")
            if fs3 >= 1.5:
                st.success(f"{arm_type} → Fs = {fs3:.3f} ✅ Норма!")
            elif fs3 >= 1.2:
                st.warning(f"Fs = {fs3:.3f} — є покращення,\nале норма 1.5 не досягнута")
            else:
                st.error(f"Fs = {fs3:.3f} — потрібні\nдодаткові заходи")
            need = max(0, 1.5 - fs3)
            st.metric("До норми Fs 1.5", f"+{need:.3f}" if need > 0 else "✅ Досягнуто")

    with tab3:
        st.markdown("### Параметричний аналіз")
        param = st.selectbox("Залежність від:", [
            "Кут укосу β (°)",
            "Глибина шару 1 (м)",
            "Глибина ГРВ (м)",
            "Зчеплення лесу замоченого c₁ (кПа)",
            "Зчеплення підстильного шару c₂ (кПа)"
        ])

        with st.spinner("Розраховуємо параметричний аналіз..."):
            if param == "Кут укосу β (°)":
                x_vals = list(range(10, 75, 5))
                x_label, x_cur = "Кут β (°)", beta
            elif param == "Глибина шару 1 (м)":
                x_vals = [round(x*0.5,1) for x in range(2, int(H/0.5))]
                x_label, x_cur = "Глибина шару 1 (м)", depth1
            elif param == "Глибина ГРВ (м)":
                x_vals = [round(x*0.5,1) for x in range(0, int(H/0.5)+1)]
                x_label, x_cur = "Глибина ГРВ (м)", wt or 0
            elif param == "Зчеплення лесу замоченого c₁ (кПа)":
                x_vals = list(range(1, 31, 2))
                x_label, x_cur = "c₁ замочений (кПа)", c1_wet
            else:
                x_vals = list(range(1, 31, 2))
                x_label, x_cur = "c₂ підстильного (кПа)", c2_layer

            r1, r2, r3 = [], [], []
            prog = st.progress(0)
            for i, val in enumerate(x_vals):
                _beta = val if param == "Кут укосу β (°)" else beta
                _d1 = val if param == "Глибина шару 1 (м)" else depth1
                _wt = val if param == "Глибина ГРВ (м)" else wt
                _c1w = val if param == "Зчеплення лесу замоченого c₁ (кПа)" else c1_wet
                _c2 = val if param == "Зчеплення підстильного шару c₂ (кПа)" else c2_layer

                for r_list, c_t, p_t, g_t, water in [
                    (r1, c1_nat, phi1_nat, g1_nat, None),
                    (r2, _c1w, phi1_wet, g1_wet, _wt),
                    (r3, c_arm, phi_arm, g1_wet, _wt),
                ]:
                    try:
                        _s = Slope(height=H, angle=_beta, length=None)
                        _s.update_analysis_options(iterations=500)
                        _s.set_materials(Material(
                            unit_weight=g_t, friction_angle=p_t,
                            cohesion=c_t, depth_to_bottom=_d1))
                        _s.set_materials(Material(
                            unit_weight=g2_layer, friction_angle=phi2_layer,
                            cohesion=_c2, depth_to_bottom=depth2))
                        if water is not None and water > 0:
                            _s.set_water_table(water)
                        _s.analyse_slope()
                        r_list.append(round(_s.get_min_FOS(), 3))
                    except:
                        r_list.append(None)
                prog.progress((i+1)/len(x_vals))
            prog.empty()

        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(
            x=x_vals, y=r1, name="🌤️ Природний (2 шари)",
            line=dict(color="#42a5f5", width=2.5), mode="lines+markers",
            marker=dict(size=6)))
        fig_line.add_trace(go.Scatter(
            x=x_vals, y=r2, name="💧 Замочений (2 шари)",
            line=dict(color="#ef5350", width=2.5), mode="lines+markers",
            marker=dict(size=6)))
        fig_line.add_trace(go.Scatter(
            x=x_vals, y=r3, name=f"🌿 З армуванням ({arm_type[:12]})",
            line=dict(color="#66bb6a", width=2.5), mode="lines+markers",
            marker=dict(size=6)))
        fig_line.add_hline(y=1.5, line_dash="dash", line_color="#4caf50",
                           annotation_text="Fs = 1.5 (ДБН)", annotation_font_color="#4caf50")
        fig_line.add_hline(y=1.0, line_dash="dash", line_color="#f44336",
                           annotation_text="Fs = 1.0", annotation_font_color="#f44336")
        if x_cur:
            fig_line.add_vline(x=x_cur, line_dash="dot",
                               line_color="rgba(255,255,255,0.4)",
                               annotation_text="▲ Поточне",
                               annotation_font_color="rgba(255,255,255,0.6)")
        fig_line.update_layout(
            xaxis_title=x_label, yaxis_title="Коефіцієнт стійкості Fs",
            height=500, hovermode="x unified",
            legend=dict(x=0.01, y=0.99,
                        bgcolor="rgba(15,15,25,0.8)",
                        bordercolor="rgba(255,255,255,0.15)",
                        borderwidth=1),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(20,25,40,0.5)",
            xaxis=dict(gridcolor="rgba(255,255,255,0.07)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.07)")
        )
        st.plotly_chart(fig_line, use_container_width=True)

    with tab4:
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            max_fos_show = st.slider("Показати поверхні Fs <", 1.0, 3.0, 2.0, 0.1)
        with col_s2:
            sc4 = st.radio("Сценарій", ["💧 Замочений", "🌿 З армуванням"])
        try:
            _s = s2 if "Замочений" in sc4 else s3
            fig_all = _s.plot_all_planes(max_fos=max_fos_show)
            fig_all.update_layout(height=520)
            st.plotly_chart(fig_all, use_container_width=True)
        except Exception as e:
            st.warning(f"Помилка: {e}")

    with tab5:
        st.markdown("### 📋 Зведена таблиця результатів")
        df = pd.DataFrame({
            "Сценарій": [
                "1. Природний (2 шари)",
                "2. Замочений (2 шари)",
                f"3. З армуванням — {arm_type}"
            ],
            "Шар 1 c (кПа)": [c1_nat, c1_wet, c_arm],
            "Шар 1 φ (°)":   [phi1_nat, phi1_wet, phi_arm],
            "Шар 2 c (кПа)": [c2_layer, c2_layer, c2_armed],
            "Шар 2 φ (°)":   [phi2_layer, phi2_layer, phi2_armed],
            "ГРВ (м)":        ["-", str(wt) if wt else "нема", str(wt) if wt else "нема"],
            "Fs":             [round(fs1,3), round(fs2,3), round(fs3,3)],
            "Статус":         [fs_label(fs1), fs_label(fs2), fs_label(fs3)]
        })
        st.dataframe(df, use_container_width=True, hide_index=True)

        col_e1, col_e2 = st.columns(2)
        with col_e1:
            csv = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button(
                "⬇️ Завантажити CSV",
                csv, "results_2layer.csv", "text/csv",
                use_container_width=True
            )
        with col_e2:
            st.markdown(f"""
            **⚙️ Параметри розрахунку:**
            - H = {H} м, β = {beta}°
            - Шар 1: Лес, глибина {depth1} м
            - Шар 2: {layer2_type}, до {depth2:.1f} м
            - Метод: Спрощений Бішоп
            - Ітерацій: {iterations}
            - Армування: {arm_type} ({arm_layer})
            """)

except Exception as e:
    st.error(f"❌ Помилка розрахунку: {e}")
    st.exception(e)
