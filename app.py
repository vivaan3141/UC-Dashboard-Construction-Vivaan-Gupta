import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

st.set_page_config(
    page_title="UC CS Major Selectivity & GPA Thresholds (Fall 2025)",
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
def load_and_process_data():
    paths = ['uc_freshman_admission_by_discipline.csv', 'Data/uc_freshman_admission_by_discipline.csv']
    df = None
    for p in paths:
        if os.path.exists(p):
            df = pd.read_csv(p)
            break
    if df is None:
        st.error("Missing dataset: uc_freshman_admission_by_discipline.csv")
        st.stop()

    # Normalize column names
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
    df_campuses = df[~df['campus'].str.contains('systemwide|universitywide', case=False, na=False)].copy()
    
    df_campuses['admit_rate'] = df_campuses['admits'] / df_campuses['applicants']
    df_campuses['iqr_gpa'] = df_campuses['gpa_75th'] - df_campuses['gpa_25th']
    
    # Calculate Overall Campus Rates
    campus_totals = df_campuses.groupby('campus')[['admits', 'applicants']].sum()
    campus_overall = (campus_totals['admits'] / campus_totals['applicants']).rename('overall_admit_rate')
    
    # Isolate Computer Science
    cs_df = df_campuses[df_campuses['discipline'].str.contains('Computer Science', case=False, na=False)].set_index('campus')
    
    # Build complete 9-campus comparison table
    all_campuses = sorted(df_campuses['campus'].unique())
    comp_table = pd.DataFrame(index=all_campuses)
    comp_table.index.name = 'campus'
    comp_table['overall_admit_rate'] = campus_overall
    comp_table['cs_admit_rate'] = cs_df['admit_rate']
    comp_table['cs_penalty'] = comp_table['overall_admit_rate'] - comp_table['cs_admit_rate']
    comp_table['cs_gpa_25th'] = cs_df['gpa_25th']
    comp_table['cs_gpa_75th'] = cs_df['gpa_75th']
    comp_table['cs_iqr'] = comp_table['cs_gpa_75th'] - comp_table['cs_gpa_25th']
    comp_table['cs_applicants'] = cs_df['applicants']
    comp_table['cs_admits'] = cs_df['admits']
    
    return df_campuses, comp_table.reset_index()

df_campuses, cs_summary = load_and_process_data()

# Header & Fall 2025 Verification
st.title("🎓 UC Admissions: Computer Science Selectivity & GPA Thresholds")
st.caption("📅 Dataset Term: **Fall 2025 Admissions Cycle** | Entrant Level: **Freshman** | Population: **All 9 UC Undergraduate Campuses**")

st.info("""
**Core Research Question:** *In Fall 2025, how significantly do 25th percentile admit GPA thresholds and admit rate penalties vary for Computer Science across all 9 UC undergraduate campuses compared to overall campus averages?*
""")

with st.expander("ℹ️ Click here to understand the Research Question & Metrics"):
    st.markdown("""
    ### 🎯 Research Question Breakdown
    > *"In Fall 2025, how significantly do 25th percentile admit GPA thresholds and admit rate penalties vary for Computer Science across all 9 UC undergraduate campuses compared to overall campus averages?"*

    ---

    #### 1. What is the Computer Science "Admit Rate Penalty"?
    * **Campus Overall Admit Rate:** The baseline percentage of all applicants admitted across all majors combined at that UC.
    * **CS Admit Rate:** The percentage of applicants admitted specifically to the Computer Science program.
    * **The Penalty ($\Delta$):** $\text{Overall Admit Rate} - \text{CS Admit Rate}$. 
      * A **large positive penalty** means applying to CS makes acceptance much harder than the campus average.
      * A **low/zero penalty** means CS selectivity is close to the general campus baseline.

    #### 2. What is the 25th Percentile GPA Floor?
    * If you lined up 100 admitted CS students from lowest to highest GPA, the **25th Percentile** is student #25.
    * **75% of admitted CS students had a GPA higher than this number.** It represents the practical minimum academic floor for competitive consideration.

    #### 3. What is GPA Compression?
    * When the 25th percentile GPA is near the upper limit of high school GPAs (~4.20+), the spread between the 25th and 75th percentiles (IQR) shrinks to almost zero. This means near-perfect grades become the baseline requirement for applicants.
    """)

# Top-level KPI Callouts
highest_penalty_row = cs_summary.dropna(subset=['cs_penalty']).sort_values('cs_penalty', ascending=False).iloc[0]
lowest_cs_rate_row = cs_summary.dropna(subset=['cs_admit_rate']).sort_values('cs_admit_rate', ascending=True).iloc[0]
highest_gpa_row = cs_summary.dropna(subset=['cs_gpa_25th']).sort_values('cs_gpa_25th', ascending=False).iloc[0]

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Highest CS Admit Penalty", f"{highest_penalty_row['campus']}", f"-{highest_penalty_row['cs_penalty']:.2%}")
kpi2.metric("Lowest CS Admit Rate", f"{lowest_cs_rate_row['campus']}", f"{lowest_cs_rate_row['cs_admit_rate']:.2%}")
kpi3.metric("Highest 25th% GPA Floor", f"{highest_gpa_row['campus']}", f"{highest_gpa_row['cs_gpa_25th']:.2f}")
kpi4.metric("Campuses Evaluated", "9 of 9 (1 Not Reported)")

st.divider()

# Primary Comparison Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 Complete 9-Campus CS Benchmark",
    "📉 CS Admit Penalty vs. Campus Baseline",
    "🎯 Visible 25th Percentile GPA Floors",
    "🗺️ All-Majors Heatmap",
    "🤖 Gemini AI Analysis"
])

with tab1:
    st.subheader("Fall 2025 Computer Science Selectivity & GPA Benchmark Table")
    st.markdown("Direct metrics for all 9 campuses. UC Merced is preserved and noted for transparency.")
    
    display_df = cs_summary.copy()
    display_df['overall_admit_rate'] = display_df['overall_admit_rate'].apply(lambda x: f"{x:.2%}" if pd.notna(x) else "N/A")
    display_df['cs_admit_rate'] = display_df['cs_admit_rate'].apply(lambda x: f"{x:.2%}" if pd.notna(x) else "Not Reported")
    display_df['cs_penalty'] = display_df['cs_penalty'].apply(lambda x: f"{x:.2%}" if pd.notna(x) else "Not Reported")
    display_df['cs_gpa_25th'] = display_df['cs_gpa_25th'].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "Not Reported")
    display_df['cs_gpa_75th'] = display_df['cs_gpa_75th'].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "Not Reported")
    display_df['cs_iqr'] = display_df['cs_iqr'].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "Not Reported")
    display_df['cs_applicants'] = display_df['cs_applicants'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "Not Reported")
    
    display_df = display_df.rename(columns={
        'campus': 'UC Campus',
        'overall_admit_rate': 'Overall Campus Admit Rate',
        'cs_admit_rate': 'CS Admit Rate',
        'cs_penalty': 'CS Admission Penalty (Δ)',
        'cs_gpa_25th': 'CS 25th% GPA Floor',
        'cs_gpa_75th': 'CS 75th% GPA Ceiling',
        'cs_iqr': 'CS GPA IQR',
        'cs_applicants': 'CS Applicants'
    })
    
    st.dataframe(
        display_df[['UC Campus', 'Overall Campus Admit Rate', 'CS Admit Rate', 'CS Admission Penalty (Δ)', 'CS 25th% GPA Floor', 'CS 75th% GPA Ceiling', 'CS GPA IQR', 'CS Applicants']], 
        use_container_width=True,
        hide_index=True
    )

with tab2:
    st.subheader("Direct Comparison: Overall Campus Admit Rate vs. Computer Science Admit Rate")
    
    plot_penalty_df = cs_summary.dropna(subset=['cs_admit_rate']).sort_values('cs_penalty', ascending=False)
    
    # Grouped Bar Chart
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        x=plot_penalty_df['campus'],
        y=plot_penalty_df['overall_admit_rate'],
        name='Overall Campus Admit Rate',
        marker_color='#90caf9',
        text=plot_penalty_df['overall_admit_rate'].apply(lambda x: f"{x:.1%}"),
        textposition='outside'
    ))
    fig_bar.add_trace(go.Bar(
        x=plot_penalty_df['campus'],
        y=plot_penalty_df['cs_admit_rate'],
        name='Computer Science Admit Rate',
        marker_color='#ef5350',
        text=plot_penalty_df['cs_admit_rate'].apply(lambda x: f"{x:.1%}"),
        textposition='outside'
    ))
    
    fig_bar.update_layout(
        barmode='group',
        title="Overall Campus Rate vs. CS Rate (Red vs. Blue Gap = Admission Penalty)",
        xaxis_title="UC Campus",
        yaxis_title="Admit Rate",
        yaxis_tickformat='.0%',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    st.divider()

    # Dedicated Penalty Bar Chart
    st.subheader("📊 Net Computer Science Admission Penalty by Campus")
    st.markdown("$$\\text{Admission Penalty} = \\text{Overall Campus Admit Rate} - \\text{CS Admit Rate}$$")

    fig_penalty = px.bar(
        plot_penalty_df,
        x='campus',
        y='cs_penalty',
        text=plot_penalty_df['cs_penalty'].apply(lambda x: f"{x:.2%}"),
        color='cs_penalty',
        color_continuous_scale='Reds',
        labels={'cs_penalty': 'Admission Penalty (Drop in Admit Rate)', 'campus': 'UC Campus'},
        title="Ranked CS Admission Penalty (Higher = Drastically Harder to Enter CS vs. School Baseline)"
    )
    fig_penalty.update_traces(textposition='outside')
    fig_penalty.update_layout(
        yaxis_tickformat='.1%',
        xaxis_title="UC Campus",
        yaxis_title="Admit Rate Penalty (Percentage Points)"
    )
    st.plotly_chart(fig_penalty, use_container_width=True)

with tab3:
    st.subheader("25th Percentile GPA Floors for Computer Science (Labeled Across All Campuses)")
    
    gpa_plot_df = cs_summary.dropna(subset=['cs_gpa_25th']).sort_values('cs_gpa_25th', ascending=False)
    
    fig_gpa = px.bar(
        gpa_plot_df,
        x='campus',
        y='cs_gpa_25th',
        text=gpa_plot_df['cs_gpa_25th'].apply(lambda x: f"{x:.2f}"),
        color='cs_gpa_25th',
        color_continuous_scale='Viridis',
        labels={'cs_gpa_25th': '25th Percentile Admit GPA', 'campus': 'UC Campus'},
        title="25th Percentile Admit GPA by Campus for Computer Science"
    )
    fig_gpa.update_traces(textposition='outside')
    fig_gpa.update_layout(yaxis_range=[3.5, 4.4])
    st.plotly_chart(fig_gpa, use_container_width=True)

with tab4:
    st.subheader("Admit Rate Heatmap Across All Academic Disciplines")
    pivot_rates = df_campuses.pivot_table(index='discipline', columns='campus', values='admit_rate')
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

with tab5:
    st.subheader("🤖 Automated Gemini AI Admissions Briefing")
    st.caption("Powered by `google-genai` SDK & `gemini-3.6-flash`")

    if not gemini_available:
        st.warning("⚠️ `GEMINI_API_KEY` is not detected.")
        st.markdown("""
        **To enable live AI generation:**
        1. Open your app settings on [Streamlit Cloud](https://share.streamlit.io).
        2. Navigate to **Secrets** and add:
           ```toml
           GEMINI_API_KEY = "your_google_ai_studio_api_key"
           ```
        """)
        st.info("**Fallback Insight:** In Fall 2025, UC Davis exhibited the steepest CS admit penalty (-24.97%), while UCLA and UC Berkeley established severe GPA floor saturation at or above 4.20.")
    else:
        # Professional, report-focused briefing selections
        briefing_type = st.radio(
            "Select Institutional Report Type:",
            [
                "📌 Executive Summary & Disciplinary Disparity Report",
                "🎯 Applicant Risk Assessment & Strategic Target Portfolio",
                "📊 GPA Saturation & Quartile Threshold Analysis"
            ],
            horizontal=False
        )

        if st.button("🚀 Generate Formal Admissions Report", type="primary"):
            with st.spinner("Compiling structured institutional report..."):
                try:
                    # Clean data dictionary for grounding
                    data_payload = cs_summary[['campus', 'overall_admit_rate', 'cs_admit_rate', 'cs_penalty', 'cs_gpa_25th', 'cs_gpa_75th']].dropna().to_dict(orient='records')
                    
                    prompt = f"""
                    You are a Lead Institutional Research Director for the University of California System.
                    Generate a formal, publication-grade analytical dossier based on official Fall 2025 Freshman Computer Science Admissions data.

                    ### Grounding Dataset (Fall 2025):
                    {data_payload}

                    ### Report Directive:
                    Generate the following formal brief: "{briefing_type}".

                    ### Formatting & Structural Rules:
                    - DO NOT output a wall of plain text or conversational prose.
                    - Format as a high-level executive memorandum with distinct visual hierarchy.
                    - Structure the report using the following mandatory sections:
                      1. **Executive Key Takeaways** (3 bullet points with bold metrics and specific delta values).
                      2. **Comparative Findings Table** (A clean Markdown comparison table summarizing tier categories).
                      3. **Institutional Insights** (2-3 concise paragraphs evaluating penalty magnitude, GPA compression, or applicant risk).
                      4. **Strategic Recommendations** (Actionable, itemized takeaways for institutional leaders, counselors, and applicants).
                    - Explicitly cite and contrast key benchmark campuses:
                      * **UC Davis:** Highlight the highest net admission penalty (+24.97%).
                      * **UC Berkeley & UCLA:** Highlight sub-10% selectivity and near-total GPA saturation (floors >= 4.20, IQRs <= 0.09).
                      * **UC Riverside & UC Santa Cruz:** Highlight high-yield access pathways (floors <= 3.96, admit rates >= 79%).
                    """

                    response = client.models.generate_content(
                        model='gemini-3.6-flash',
                        contents=prompt
                    )

                    st.success("✅ Formal Report Generated Successfully")
                    st.markdown(response.text)

                except Exception as e:
                    st.error(f"Error communicating with Gemini API: {e}")
