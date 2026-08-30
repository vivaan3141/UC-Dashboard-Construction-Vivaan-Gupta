import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(
    page_title="UC Multi-Campus Disciplinary Comparison (Fall 2025)",
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

st.title("🎓 Cross-Campus UC Major Selectivity Comparison (Fall 2025)")
st.markdown("""
**Direct School-to-School Comparison:** Compare admit rates, applicant volumes, and GPA thresholds across all 9 UC undergraduate campuses simultaneously.
""")

# High-Level Metrics Row (System Totals)
total_apps = df['applicants'].sum()
total_adms = df['admits'].sum()
sys_rate = total_adms / total_apps if total_apps > 0 else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total UC Campuses", df['campus'].nunique())
c2.metric("Total Discipline Categories", df['discipline'].nunique())
c3.metric("Total Applications Analyzed", f"{int(total_apps):,}")
c4.metric("Aggregate System Admit Rate", f"{sys_rate:.1%}")

st.divider()

# Core Visual Comparison Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Major Heatmap (All Schools)", 
    "📈 Grouped Admit Rate Comparison", 
    "🎯 GPA Floors (All Campuses)", 
    "🤖 Gemini Cross-Campus Analyst"
])

with tab1:
    st.subheader("Admit Rate Heatmap: Campuses vs. Academic Disciplines")
    st.markdown("Darker blue indicates lower admit rates (higher selectivity).")
    
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
    st.subheader("Side-by-Side Major Comparison Across Campuses")
    selected_disc = st.selectbox(
        "Select a Major to Compare Across All 9 Campuses", 
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
        title=f"Admit Rate for {selected_disc} Across All UC Campuses"
    )
    st.plotly_chart(fig_comp, use_container_width=True)

with tab3:
    st.subheader("25th Percentile GPA Floor Comparison (All Schools)")
    
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
        title="Admit GPA Floor vs. Admit Rate (Hover to view major details)"
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

with tab4:
    st.subheader("Automated Cross-Campus AI Analysis")
    if not gemini_available:
        st.warning("Set up `GEMINI_API_KEY` in Streamlit Secrets to enable live AI analysis.")
        st.info("Systemwide Comparison: UC Berkeley and UCLA show the steepest selectivity barriers across all majors (admit rates < 15%), whereas UC Riverside, UC Santa Cruz, and UC Merced provide wide access routes with GPA floors below 4.00.")
    else:
        if st.button("Run Cross-Campus Comparison Analysis"):
            with st.spinner("Analyzing cross-campus patterns..."):
                summary_data = df.groupby(['campus', 'discipline'])[['admit_rate', 'gpa_25th']].mean().reset_index().to_dict(orient='records')
                prompt = f"""
                You are a senior admissions analyst for the University of California system.
                Analyze this complete Fall 2025 dataset across all 9 UC campuses and disciplines:
                {summary_data[:30]}

                Provide 3 clear, comparative findings:
                1. How selectivity diverges between top-tier (UCB/UCLA), mid-tier (UCSD/UCI/UCD/UCSB), and access-focused campuses (UCR/UCSC/UCM).
                2. Which academic disciplines show the widest admit rate variance across campuses.
                3. Key takeaways for students deciding where to apply for competitive majors.
                """
                resp = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt
                )
                st.markdown(resp.text)
