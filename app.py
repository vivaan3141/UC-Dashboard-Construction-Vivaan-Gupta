with tab2:
    st.subheader("Direct Comparison: Overall Campus Admit Rate vs. Computer Science Admit Rate")
    
    plot_penalty_df = cs_summary.dropna(subset=['cs_admit_rate']).sort_values('cs_penalty', ascending=False)
    
    # 1. Grouped Bar Chart (Overall vs CS)
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

    # 2. Dedicated CS Admission Penalty Bar Graph
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
