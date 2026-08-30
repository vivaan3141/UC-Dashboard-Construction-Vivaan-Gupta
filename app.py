import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(
    page_title="UC Major Selectivity & GPA Explorer (Fall 2025)",
    page_icon="🎓",
    layout="wide"
)

# Gemini API Integration
gemini_available = False
try:
    from google import genai
    api_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
    if api_key:
        client = genai.Client(api_key=api_key)
        gemini_available = True
except Exception:
    gemini_available = False

@st.cache_data
def load_data():
    paths = ['uc_freshman_admission_by_discipline.csv', 'Data/uc_freshman_admission_by_discipline.csv']
    df = None
    for p in paths:
        if os.path.exists(p):
            df = pd.read_csv(p)
            break
    if df is None:
        st.error("Missing dataset: uc_freshman_admission_by_discipline.csv")
        st.stop()

    campus_c = [c for c in df.columns if 'camp' in c.lower()][0]
    disc_c = [c for c in df.columns if any(k in c.lower() for k in ['disc', 'major', 'broad'])][0]
    app_c = [c for c in df.columns if 'app' in c.lower() and 'gpa' not in c.lower()][0]
    adm_c = [c for c in df.columns if 'adm' in c.lower() and 'gpa' not in c.lower() and 'rate' not in c.lower()][0]
    p25_c = [c for c in df.columns if '25' in c and any(k in c.lower() for k in ['adm', 'gpa'])][0]
    p75_c = [c for c in df.columns if '75' in c and any(k in c.lower() for k in ['adm', 'gpa'])][0]

    df = df.rename(columns={
        campus_c: 'campus',
        disc_c: 'discipline',
        app_c: 'applicants',
        adm_c: 'admits',
        p25_c: 'gpa_25th',
        p75_c: 'gpa_75th'
    })

    for col in ['applicants', 'admits', 'gpa_25th', 'gpa_75th']:
        if col in df.columns and df[col].dtype == object:
            df[col] = df[col].astype(str).str.replace(',', '').str.strip().astype(float)
            
    df = df[~df['discipline'].str.lower().str.contains('all disciplines|total', na=False)]
    df = df[~df['campus'].str.contains('systemwide|universitywide', case=False, na=False)].copy()
    
    df['admit_rate'] = df['admits'] / df['applicants']
    df['iqr_gpa'] = df['gpa_75th'] - df['gpa_25th']
    return df

df = load_data()

# Sidebar: View Mode Switcher
st.sidebar.title("🛠️ Navigation & Mode")
view_mode = st.sidebar.radio(
    "Select Dashboard Mode:",
    ["📊 Compare All Campuses", "🔍 Single Campus Deep-Dive"]
)

# Mode 1: Compare All Campuses
if view_mode == "📊 Compare All Campuses":
    st.title("🎓 Cross-Campus UC Major Selectivity Comparison (Fall 2025)")
    st.markdown("""
    **Multi-School Comparison Mode:** Directly benchmark admission rates, GPA thresholds, and selectivity across all 9 UC undergraduate campuses simultaneously.
    """)

    # Overview Metrics Row
    total_apps = df['applicants'].sum()
    total_adms = df['admits'].sum()
    sys_rate = total_adms / total_apps if total_apps > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Campuses Compared", df['campus'].nunique())
    c2.metric("Academic Disciplines", df['discipline'].nunique())
    c3.metric("Total Applications Analyzed", f"{int(total_apps):,}")
    c4.metric("Aggregate System Admit Rate", f"{sys_rate:.1%}")

    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs([
        "🗺️ Selectivity Heatmap", 
        "📊 Major-by-Major Comparison", 
        "🎯 Cross-Campus GPA Floors", 
        "🤖 Systemwide AI Briefing"
    ])

    with tab1:
        st.subheader("Admit Rate Heatmap: All Campuses vs. All Disciplines")
        pivot_rates = df.pivot_table(index='discipline', columns='campus', values='admit_rate')
        
        fig_heat = px.imshow(
            pivot_rates,
            labels=dict(x="UC Campus", y="Academic Discipline", color="Admit Rate"),
            x=pivot_rates.columns,
            y=pivot_rates.index,
            color_continuous_scale='Blues_r',
            aspect="auto",
            text_auto=".1%"
        )
        fig_heat.update_layout(height=550)
        st.plotly_chart(fig_heat, use_container_width=True)

    with tab2:
        st.subheader("Compare a Specific Major Across Every UC Campus")
        selected_disc = st.selectbox(
            "Select an Academic Discipline to Compare:", 
            sorted(df['discipline'].unique()),
            index=sorted(df['discipline'].unique()).index('Computer Science') if 'Computer Science' in df['discipline'].values else 0
        )
        
        comp_df = df[df['discipline'] == selected_disc].sort_values('admit_rate', ascending=True)
        fig_comp = px.bar(
            comp_df,
            x='campus',
            y='admit_rate',
            color='admit_rate',
            color_continuous_scale='Reds_r',
            text_auto='.1%',
            labels={'admit_rate': 'Admit Rate', 'campus': 'UC Campus'},
            title=f"Admit Rate for '{selected_disc}' Across All 9 Campuses"
        )
        st.plotly_chart(fig_comp, use_container_width=True)

    with tab3:
        st.subheader("25th Percentile GPA Floors vs. Admit Rate (All Campuses & Majors)")
        fig_scatter = px.scatter(
            df,
            x='gpa_25th',
            y='admit_rate',
            color='campus',
            hover_data=['discipline', 'applicants', 'gpa_75th'],
            labels={
                'gpa_25th': '25th Percentile Admit GPA Floor', 
                'admit_rate': 'Admit Rate',
                'campus': 'Campus'
            },
            title="Admit GPA Floor vs. Admit Rate (Hover for Discipline Details)"
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    with tab4:
        st.subheader("Automated Cross-Campus AI Analysis")
        if not gemini_available:
            st.warning("Configure `GEMINI_API_KEY` in Streamlit Secrets to enable live Gemini insights.")
            st.info("Cross-Campus Insight: Top-tier campuses (UCB, UCLA) have near-universal GPA floors above 4.20, while access campuses (UCR, UCSC, UCM) provide significant acceptance margins for STEM applicants.")
        else:
            if st.button("Generate Systemwide AI Report"):
                with st.spinner("Analyzing systemwide metrics..."):
                    summary_data = df.groupby(['campus', 'discipline'])[['admit_rate', 'gpa_25th']].mean().reset_index().to_dict(orient='records')
                    prompt = f"""
                    You are a senior admissions analyst for the University of California.
                    Analyze this Fall 2025 dataset across all 9 UC campuses:
                    {summary_data[:30]}

                    Provide 3 concise takeaways:
                    1. Selectivity differences across top, mid, and access UC campuses.
                    2. Majors showing the highest variance across schools.
                    3. Actionable guidance for prospective applicants.
                    """
                    resp = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt
                    )
                    st.markdown(resp.text)

# Mode 2: Single Campus Deep-Dive
else:
    campuses = sorted(df['campus'].unique())
    selected_campus = st.sidebar.selectbox("Choose a UC Campus to Explore:", campuses, index=0)

    st.title(f"🔍 Deep-Dive Analysis: {selected_campus} (Fall 2025)")
    st.markdown(f"Detailed view of **all academic disciplines** and GPA distributions for **{selected_campus}**.")

    camp_data = df[df['campus'] == selected_campus].sort_values('admit_rate', ascending=True)
    overall_camp_rate = camp_data['admits'].sum() / camp_data['applicants'].sum() if camp_data['applicants'].sum() > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Selected Campus", selected_campus)
    col2.metric("Overall Campus Admit Rate", f"{overall_camp_rate:.1%}")
    col3.metric("Total Applicants", f"{int(camp_data['applicants'].sum()):,}")
    col4.metric("Disciplines Evaluated", len(camp_data))

    st.divider()

    tab1, tab2, tab3 = st.tabs([
        "📊 Major Selectivity vs. Campus Baseline", 
        "🎯 GPA Distribution by Major", 
        "🤖 Campus-Specific AI Analyst"
    ])

    with tab1:
        st.subheader(f"Admit Rates Across ALL Disciplines: {selected_campus}")
        fig_bar = px.bar(
            camp_data,
            x='admit_rate',
            y='discipline',
            orientation='h',
            color='admit_rate',
            color_continuous_scale='Blues_r',
            text_auto='.1%',
            labels={'admit_rate': 'Admit Rate', 'discipline': 'Academic Discipline'},
            title=f"All Disciplines Ranked by Selectivity ({selected_campus})"
        )
        fig_bar.add_vline(x=overall_camp_rate, line_dash="dash", line_color="red", annotation_text="Campus Overall Average")
        st.plotly_chart(fig_bar, use_container_width=True)

    with tab2:
        st.subheader(f"Admit GPA Floors (25th Percentile) for {selected_campus}")
        fig_gpa = px.scatter(
            camp_data,
            x='gpa_25th',
            y='discipline',
            size='applicants',
            color='admit_rate',
            color_continuous_scale='Viridis',
            hover_data=['gpa_75th', 'iqr_gpa'],
            labels={'gpa_25th': '25th Percentile Admit GPA Floor', 'discipline': 'Discipline'},
            title=f"GPA Floor vs. Applicant Volume ({selected_campus})"
        )
        st.plotly_chart(fig_gpa, use_container_width=True)

    with tab3:
        st.subheader(f"AI Admissions Briefing for {selected_campus}")
        if not gemini_available:
            st.warning("Configure `GEMINI_API_KEY` in Streamlit Secrets to enable live AI analysis.")
            st.info(f"Summary: At {selected_campus}, high-demand disciplines experience notable admission penalties relative to the campus baseline of {overall_camp_rate:.1%}.")
        else:
            if st.button(f"Generate {selected_campus} Major Analysis"):
                with st.spinner(f"Analyzing {selected_campus}..."):
                    sample_rows = camp_data[['discipline', 'admit_rate', 'gpa_25th', 'gpa_75th']].to_dict(orient='records')
                    prompt = f"""
                    You are an admissions advisor.
                    Analyze the admissions metrics for {selected_campus} (Fall 2025):
                    Overall Campus Admit Rate: {overall_camp_rate:.1%}
                    Discipline Data: {sample_rows}

                    Provide 3 concise takeaways:
                    1. The disciplines with the steepest admission penalty.
                    2. Disciplines with higher acceptance opportunities.
                    3. GPA threshold takeaways for applicants.
                    """
                    resp = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt
                    )
                    st.markdown(resp.text)
