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

import json

with tab5:
    st.subheader("🤖 Dynamic AI Report & Visual Chart Generator")
    st.caption("Powered by official Fall 2025 UC Admissions Data & `gemini-3.6-flash`")

    st.markdown("#### ⚙️ Configure Your Custom Analysis")
    
    rep_col1, rep_col2 = st.columns([1, 1])
    
    with rep_col1:
        available_campuses = sorted(cs_summary['campus'].unique())
        report_campuses = st.multiselect(
            "1. Select Campuses to Include:",
            available_campuses,
            default=available_campuses
        )
        
    with rep_col2:
        report_theme = st.selectbox(
            "2. Select Analytical Focus:",
            [
                "Comprehensive Disciplinary Gap Analysis",
                "Admission Penalty & Selectivity Barrier",
                "25th Percentile GPA Floor & Saturation Analysis"
            ]
        )

    custom_inquiry = st.text_input(
        "3. Custom Analytical Query (Optional):",
        placeholder="e.g., Which campuses pose the highest admission risk for applicants with GPAs under 4.10?"
    )

    custom_df = cs_summary[cs_summary['campus'].isin(report_campuses)].copy()
    valid_custom_df = custom_df.dropna(subset=['cs_admit_rate']).sort_values('cs_penalty', ascending=False)

    st.divider()

    if not gemini_available:
        st.warning("⚠️ `GEMINI_API_KEY` is not detected in Streamlit Secrets.")
        st.info("Set up your API key in Streamlit Secrets to enable dynamic AI chart and report generation.")
    else:
        if st.button("🚀 Generate AI Report & Dynamic Charts", type="primary"):
            if len(report_campuses) == 0:
                st.error("Please select at least one campus above to compile the report.")
            else:
                with st.spinner("Gemini is analyzing dataset and constructing dynamic visualizations..."):
                    try:
                        data_slice = valid_custom_df[['campus', 'overall_admit_rate', 'cs_admit_rate', 'cs_penalty', 'cs_gpa_25th', 'cs_gpa_75th', 'cs_iqr']].to_dict(orient='records')
                        
                        prompt = f"""
                        You are the Lead Institutional Data Scientist for the University of California.
                        Analyze the official Fall 2025 Freshman Computer Science admissions dataset slice provided below.

                        Dataset Slice:
                        {data_slice}

                        Configuration:
                        - Theme: {report_theme}
                        - Custom Query: {custom_inquiry if custom_inquiry else "Standard Fall 2025 Disciplinary Assessment"}

                        Return a strict JSON object with EXACTLY two root keys: "visual_plan" and "report_markdown".
                        Do NOT include any markdown code fences (like ```json) outside the JSON object.

                        JSON Structure:
                        {{
                          "visual_plan": {{
                            "chart_type": "scatter" | "bar" | "grouped_bar",
                            "chart_title": "Descriptive, insight-driven chart title",
                            "x_metric": "campus" | "cs_gpa_25th" | "overall_admit_rate",
                            "y_metric": "cs_penalty" | "cs_admit_rate" | "cs_gpa_25th",
                            "color_metric": "cs_penalty" | "cs_gpa_25th" | "campus",
                            "explanation": "1-2 sentences explaining why this specific visualization best illustrates the user inquiry."
                          }},
                          "report_markdown": "A formal, structured Markdown report featuring: 1. Executive Findings with bold percentages/GPAs, 2. A concise comparison table, and 3. Strategic Recommendations addressing the research inquiry."
                        }}
                        """

                        response = client.models.generate_content(
                            model='gemini-3.6-flash',
                            contents=prompt
                        )

                        raw_text = response.text.strip()
                        if raw_text.startswith("```json"):
                            raw_text = raw_text.replace("```json", "", 1)
                        if raw_text.startswith("```"):
                            raw_text = raw_text.replace("```", "", 1)
                        if raw_text.endswith("```"):
                            raw_text = raw_text[:-3]
                        raw_text = raw_text.strip()

                        result = json.loads(raw_text)
                        vplan = result.get("visual_plan", {})
                        report_md = result.get("report_markdown", "")

                        # Render Dynamic Visualization instructed by Gemini
                        st.markdown("### 📊 AI-Designed Dynamic Visualization")
                        st.caption(f"**AI Chart Rationale:** {vplan.get('explanation', '')}")

                        chart_type = vplan.get('chart_type', 'bar')
                        x_col = vplan.get('x_metric', 'campus')
                        y_col = vplan.get('y_metric', 'cs_penalty')
                        color_col = vplan.get('color_metric', 'cs_penalty')
                        title = vplan.get('chart_title', 'Admissions Comparison')

                        # Fallback validation to prevent missing column errors
                        if x_col not in valid_custom_df.columns: x_col = 'campus'
                        if y_col not in valid_custom_df.columns: y_col = 'cs_penalty'
                        if color_col not in valid_custom_df.columns: color_col = y_col

                        if chart_type == 'scatter':
                            fig_ai = px.scatter(
                                valid_custom_df,
                                x=x_col,
                                y=y_col,
                                color=color_col,
                                size='cs_penalty',
                                hover_name='campus',
                                title=title,
                                labels={x_col: x_col.replace('_', ' ').title(), y_col: y_col.replace('_', ' ').title()}
                            )
                        else:
                            fig_ai = px.bar(
                                valid_custom_df,
                                x=x_col,
                                y=y_col,
                                color=color_col,
                                text=valid_custom_df[y_col].apply(lambda x: f"{x:.2%}" if "rate" in y_col or "penalty" in y_col else f"{x:.2f}"),
                                title=title,
                                labels={x_col: x_col.replace('_', ' ').title(), y_col: y_col.replace('_', ' ').title()}
                            )
                            fig_ai.update_traces(textposition='outside')
                            if "rate" in y_col or "penalty" in y_col:
                                fig_ai.update_layout(yaxis_tickformat='.1%')

                        st.plotly_chart(fig_ai, use_container_width=True)

                        st.divider()

                        # Render Markdown Report
                        st.markdown("### 📝 Synthesized Institutional Dossier")
                        st.markdown(report_md)

                    except Exception as e:
                        st.error(f"Error compiling AI analysis: {e}")
