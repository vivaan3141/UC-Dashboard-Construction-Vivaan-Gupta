import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os

st.set_page_config(
    page_title="UC CS Major Selectivity & GPA Thresholds (Fall 2025)",
    page_icon="🎓",
    layout="wide"
)

# Gemini API Initialization
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

    # Normalize Column Names
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
    
    # Campus Baselines
    campus_totals = df_campuses.groupby('campus')[['admits', 'applicants']].sum()
    campus_overall = (campus_totals['admits'] / campus_totals['applicants']).rename('overall_admit_rate')
    
    # Isolate Computer Science
    cs_df = df_campuses[df_campuses['discipline'].str.contains('Computer Science', case=False, na=False)].set_index('campus')
    
    # Compile 9-Campus Summary
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

# Header & Context
st.title("🎓 UC Admissions: Computer Science Selectivity & GPA Thresholds")
st.caption("📅 Dataset Term: **Fall 2025 Admissions Cycle** | Level: **Freshman** | Scope: **All 9 UC Undergraduate Campuses**")

with st.expander("ℹ️ Click here to understand the Research Question & Core Metrics"):
    st.markdown("""
    ### 🎯 Research Question Breakdown
    > *"In Fall 2025, how significantly do 25th percentile admit GPA thresholds and admit rate penalties vary for Computer Science across all 9 UC undergraduate campuses compared to overall campus averages?"*

    ---

    #### 1. What is the Computer Science "Admit Rate Penalty"?
    * **Campus Overall Admit Rate:** Percentage of all applicants admitted across every major combined.
    * **CS Admit Rate:** Percentage of applicants admitted specifically into Computer Science.
    * **The Penalty ($\Delta$):** $\\text{Overall Admit Rate} - \\text{CS Admit Rate}$. 
      * A **large positive penalty** indicates that choosing CS imposes a significant barrier relative to the campus average.

    #### 2. What is the 25th Percentile GPA Floor?
    * The high school GPA where **75% of accepted CS students had a higher score**. It serves as the realistic academic floor for admission.

    #### 3. What is GPA Compression?
    * When GPA floors reach $\\ge 4.20$, the score spread (IQR) shrinks drastically, demonstrating that near-perfect grades are a baseline prerequisite.
    """)

# Primary KPI Callouts
highest_penalty_row = cs_summary.dropna(subset=['cs_penalty']).sort_values('cs_penalty', ascending=False).iloc[0]
lowest_cs_rate_row = cs_summary.dropna(subset=['cs_admit_rate']).sort_values('cs_admit_rate', ascending=True).iloc[0]
highest_gpa_row = cs_summary.dropna(subset=['cs_gpa_25th']).sort_values('cs_gpa_25th', ascending=False).iloc[0]

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Highest CS Admit Penalty", f"{highest_penalty_row['campus']}", f"-{highest_penalty_row['cs_penalty']:.2%}")
kpi2.metric("Lowest CS Admit Rate", f"{lowest_cs_rate_row['campus']}", f"{lowest_cs_rate_row['cs_admit_rate']:.2%}")
kpi3.metric("Highest 25th% GPA Floor", f"{highest_gpa_row['campus']}", f"{highest_gpa_row['cs_gpa_25th']:.2f}")
kpi4.metric("Campuses Evaluated", "9 of 9 (1 Not Reported)")

st.divider()

# Primary Visual Tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📋 9-Campus Benchmark Table",
    "📉 CS Admit Penalty vs Baseline",
    "🎯 25th Percentile GPA Floors",
    "🗺️ Multi-Major Heatmap",
    "🤖 Dynamic AI Report & Visuals",
    "💬 Ask Gemini Q&A"
])

# TAB 1: Benchmark Table (Clean Default View)
with tab1:
    st.subheader("Fall 2025 Computer Science Selectivity & GPA Benchmark Table")
    st.caption("Campuses ranked by CS Admission Penalty ($\Delta$)")
    
    t_df = cs_summary.sort_values('cs_penalty', ascending=False).copy()

    t_df['overall_admit_rate'] = t_df['overall_admit_rate'].apply(lambda x: f"{x:.2%}" if pd.notna(x) else "N/A")
    t_df['cs_admit_rate'] = t_df['cs_admit_rate'].apply(lambda x: f"{x:.2%}" if pd.notna(x) else "Not Reported")
    t_df['cs_penalty'] = t_df['cs_penalty'].apply(lambda x: f"{x:.2%}" if pd.notna(x) else "Not Reported")
    t_df['cs_gpa_25th'] = t_df['cs_gpa_25th'].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "Not Reported")
    t_df['cs_gpa_75th'] = t_df['cs_gpa_75th'].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "Not Reported")
    t_df['cs_iqr'] = t_df['cs_iqr'].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "Not Reported")
    t_df['cs_applicants'] = t_df['cs_applicants'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "Not Reported")
    
    t_df = t_df.rename(columns={
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
        t_df[['UC Campus', 'Overall Campus Admit Rate', 'CS Admit Rate', 'CS Admission Penalty (Δ)', 'CS 25th% GPA Floor', 'CS 75th% GPA Ceiling', 'CS GPA IQR', 'CS Applicants']], 
        use_container_width=True,
        hide_index=True
    )

# TAB 2: Penalty Analysis
with tab2:
    st.subheader("Direct Comparison: Overall Campus Admit Rate vs. Computer Science Admit Rate")
    
    sort_pen_order = st.radio(
        "Sort Campuses By:",
        ["Highest Penalty (Drop) First", "Lowest CS Admit Rate First", "Alphabetical"],
        horizontal=True
    )

    valid_p_df = cs_summary.dropna(subset=['cs_admit_rate']).copy()
    if sort_pen_order == "Highest Penalty (Drop) First":
        valid_p_df = valid_p_df.sort_values('cs_penalty', ascending=False)
    elif sort_pen_order == "Lowest CS Admit Rate First":
        valid_p_df = valid_p_df.sort_values('cs_admit_rate', ascending=True)
    else:
        valid_p_df = valid_p_df.sort_values('campus', ascending=True)
    
    # Grouped Bar Chart
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        x=valid_p_df['campus'],
        y=valid_p_df['overall_admit_rate'],
        name='Overall Campus Admit Rate',
        marker_color='#90caf9',
        text=valid_p_df['overall_admit_rate'].apply(lambda x: f"{x:.1%}"),
        textposition='outside'
    ))
    fig_bar.add_trace(go.Bar(
        x=valid_p_df['campus'],
        y=valid_p_df['cs_admit_rate'],
        name='Computer Science Admit Rate',
        marker_color='#ef5350',
        text=valid_p_df['cs_admit_rate'].apply(lambda x: f"{x:.1%}"),
        textposition='outside'
    ))
    fig_bar.update_layout(
        barmode='group',
        title="Overall Campus Baseline vs. CS Admit Rate",
        xaxis_title="UC Campus",
        yaxis_title="Admit Rate",
        yaxis_tickformat='.0%',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    st.divider()

    # Dedicated Penalty Chart
    st.subheader("📊 Net Computer Science Admission Penalty by Campus")
    st.markdown("$$\\text{Admission Penalty} = \\text{Overall Campus Admit Rate} - \\text{CS Admit Rate}$$")

    fig_pen = px.bar(
        valid_p_df,
        x='campus',
        y='cs_penalty',
        text=valid_p_df['cs_penalty'].apply(lambda x: f"{x:.2%}"),
        color='cs_penalty',
        color_continuous_scale='Reds',
        labels={'cs_penalty': 'CS Admission Penalty', 'campus': 'UC Campus'},
        title="Ranked CS Admission Penalty (Drop in Acceptance Rate)"
    )
    fig_pen.update_traces(textposition='outside')
    fig_pen.update_layout(yaxis_tickformat='.1%', yaxis_title="Percentage Point Drop")
    st.plotly_chart(fig_pen, use_container_width=True)

# TAB 3: Interactive GPA Floor Analysis
with tab3:
    st.subheader("Computer Science GPA Distribution & Thresholds")
    
    g_col1, g_col2 = st.columns(2)
    with g_col1:
        gpa_metric = st.selectbox(
            "Select GPA Dimension to Display:",
            ["25th Percentile GPA Floor", "75th Percentile GPA Ceiling", "GPA IQR (Spread / Uncertainty)"]
        )
    with g_col2:
        gpa_sort_dir = st.radio("Sort Order:", ["Highest First", "Lowest First"], horizontal=True)

    gpa_df = cs_summary.dropna(subset=['cs_gpa_25th']).copy()
    
    target_col = 'cs_gpa_25th' if '25th' in gpa_metric else ('cs_gpa_75th' if '75th' in gpa_metric else 'cs_iqr')
    gpa_df = gpa_df.sort_values(target_col, ascending=(gpa_sort_dir == "Lowest First"))

    fig_gpa = px.bar(
        gpa_df,
        x='campus',
        y=target_col,
        text=gpa_df[target_col].apply(lambda x: f"{x:.2f}"),
        color=target_col,
        color_continuous_scale='Viridis',
        labels={target_col: gpa_metric, 'campus': 'UC Campus'},
        title=f"{gpa_metric} Across UC Campuses for Computer Science"
    )
    fig_gpa.update_traces(textposition='outside')
    if target_col in ['cs_gpa_25th', 'cs_gpa_75th']:
        fig_gpa.update_layout(yaxis_range=[3.5, 4.4])
    st.plotly_chart(fig_gpa, use_container_width=True)

# TAB 4: Heatmap
with tab4:
    st.subheader("Systemwide Selectivity Heatmap: All Disciplines & Campuses")
    
    selected_disciplines = st.multiselect(
        "Filter Academic Disciplines to Display:",
        sorted(df_campuses['discipline'].unique()),
        default=sorted(df_campuses['discipline'].unique())[:8]
    )

    if len(selected_disciplines) > 0:
        filtered_heat_df = df_campuses[df_campuses['discipline'].isin(selected_disciplines)]
        pivot_rates = filtered_heat_df.pivot_table(index='discipline', columns='campus', values='admit_rate')
        
        fig_heat = px.imshow(
            pivot_rates,
            labels=dict(x="UC Campus", y="Academic Discipline", color="Admit Rate"),
            x=pivot_rates.columns,
            y=pivot_rates.index,
            color_continuous_scale='Blues_r',
            aspect="auto",
            text_auto=".1%"
        )
        fig_heat.update_layout(height=450)
        st.plotly_chart(fig_heat, use_container_width=True)

# TAB 5: Dynamic AI Visual & Report Synthesizer
with tab5:
    st.subheader("🤖 Dynamic AI Report & Visual Chart Generator")
    st.caption("Powered by official Fall 2025 UC Admissions Data & `gemini-3.6-flash`")

    st.markdown("#### ⚙️ Configure Custom Analysis")
    
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
        placeholder="e.g., Which campuses offer the lowest admission risk for applicants with GPAs near 4.00?"
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
                with st.spinner("Gemini is evaluating dataset and constructing visualizations..."):
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
                            "chart_type": "scatter" | "bar",
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

                        st.markdown("### 📝 Synthesized Institutional Dossier")
                        st.markdown(report_md)

                    except Exception as e:
                        st.error(f"Error compiling AI analysis: {e}")

# TAB 6: Interactive Gemini Q&A
with tab6:
    st.subheader("💬 Ask Gemini About the Fall 2025 Admissions Data")
    st.caption("Direct conversational Q&A grounded in the full 9-campus UC dataset.")

    if not gemini_available:
        st.warning("⚠️ `GEMINI_API_KEY` is not detected in Streamlit Secrets.")
        st.info("Add your API key to Streamlit Secrets to enable interactive questions.")
    else:
        st.markdown("##### 💡 Suggested Questions to Try:")
        q_cols = st.columns(3)
        q1 = q_cols[0].button("Which UC has the lowest CS admission penalty?")
        q2 = q_cols[1].button("Where can an applicant with a 4.05 GPA be competitive for CS?")
        q3 = q_cols[2].button("Compare UC Berkeley vs UCLA in CS GPA floors and admit rates.")

        # Question input field
        user_question = st.text_input(
            "Enter your question about UC admissions, GPA thresholds, or major selectivity:",
            value="Which UC has the lowest CS admission penalty?" if q1 else ("Where can an applicant with a 4.05 GPA be competitive for CS?" if q2 else ("Compare UC Berkeley vs UCLA in CS GPA floors and admit rates." if q3 else ""))
        )

        if st.button("Ask Gemini", type="primary"):
            if not user_question.strip():
                st.warning("Please enter or select a question first.")
            else:
                with st.spinner("Gemini is querying the Fall 2025 dataset..."):
                    try:
                        # Feed the full grounded dataset to Gemini
                        full_cs_payload = cs_summary[['campus', 'overall_admit_rate', 'cs_admit_rate', 'cs_penalty', 'cs_gpa_25th', 'cs_gpa_75th', 'cs_iqr', 'cs_applicants', 'cs_admits']].to_dict(orient='records')
                        
                        qa_prompt = f"""
                        You are an expert University of California Admissions Consultant & Data Scientist.
                        Answer the user's question accurately, concisely, and strictly based on the official Fall 2025 Freshman Computer Science and Disciplinary dataset below:

                        Dataset:
                        {full_cs_payload}

                        User Question:
                        "{user_question}"

                        Guidelines:
                        - Ground all numerical answers (admit rates, penalties, 25th/75th percentile GPAs) directly in the provided dataset.
                        - Use bold text for key figures and school names.
                        - If referencing UC Merced, note that it has a 94.33% overall admit rate and its CS data is bundled into general engineering categories.
                        - Provide a direct, structured answer with bullet points and clear takeaways.
                        """

                        qa_response = client.models.generate_content(
                            model='gemini-3.6-flash',
                            contents=qa_prompt
                        )

                        st.markdown("#### 📋 Gemini Answer:")
                        st.markdown(qa_response.text)

                    except Exception as e:
                        st.error(f"Error querying Gemini: {e}")
