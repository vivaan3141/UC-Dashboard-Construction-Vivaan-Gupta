# 🎓 UC Admissions Explorer: Computer Science Selectivity & GPA Thresholds (Fall 2025)

An interactive analytics dashboard evaluating **Computer Science (CS) freshman selectivity, admission rate penalties, and GPA quartile thresholds** across all 9 University of California (UC) undergraduate campuses for the **Fall 2025** admissions cycle.

---

## 📖 Research Question & Objective

> **Core Research Question:**  
> *"In Fall 2025, how significantly do 25th percentile admit GPA thresholds and admit rate penalties vary for Computer Science across all 9 UC undergraduate campuses compared to overall campus averages?"*

While campus-wide acceptance rates give general admissions guidance, capped and high-demand STEM majors like Computer Science face drastically higher selective barriers. This dashboard quantifies and visualizes that disparity directly.

---

## 🔬 Methodology & Metric Definitions

Our data pipeline normalizes institutional freshman admissions figures and computes two core analytical pillars:

### 1. The Computer Science Admission Penalty ($\Delta$)
The **Admission Penalty** measures the gap between a campus's general freshman acceptance rate and its major-specific CS acceptance rate:
$$\text{CS Admission Penalty } (\Delta) = \text{Overall Campus Admit Rate} - \text{CS Admit Rate}$$
* **High Positive Penalty ($\Delta > 0$):** Indicates that applying to Computer Science imposes a severe disadvantage relative to baseline campus admission (e.g., UC Davis at **+24.97%**).
* **Negative Penalty ($\Delta < 0$):** Indicates that Computer Science had a higher acceptance rate than the overall campus average (e.g., UC Santa Cruz at **-6.87%**).

### 2. 25th Percentile GPA Floors & Compression Analysis
* **25th Percentile GPA Floor:** The weighted, capped high school GPA where **75% of admitted applicants scored higher**. This reflects the practical minimum academic floor for competitive consideration.
* **Interquartile Range (IQR Spread):** $\text{IQR} = \text{75th Percentile GPA} - \text{25th Percentile GPA}$.
* **The Ceiling Effect / GPA Saturation:** When 25th percentile floors reach $\ge 4.20$, the score spread shrinks to $\le 0.10$ points (e.g., UCLA's IQR is **0.05**), demonstrating that near-perfect grades are a non-differentiating baseline requirement.

### 3. Data Cleansing & Disciplinary Aggregation
* Non-freshman and systemwide aggregate rows were removed to ensure cross-campus parity.
* Campuses bundling Computer Science under general engineering categories (such as UC Merced) are retained in data tables and transparently labeled as *Not Reported* to preserve 9-campus transparency.

---

## 🚀 Key Dashboard Features

* **📋 9-Campus Benchmark Table:** Direct tabular ranking of overall rates, CS rates, admission penalties, 25th/75th GPA floors, IQRs, and applicant counts.
* **📉 CS Penalty vs. Campus Baseline:** Grouped bar charts contrasting overall baselines against CS admit rates, paired with a ranked penalty graph.
* **🎯 25th Percentile GPA Floors:** Interactive visualization of GPA floors and score spreads across campuses.
* **🗺️ Multi-Major Disciplinary Heatmap:** Cross-campus comparative heatmap across broad academic fields.
* **🤖 Dynamic AI Report & Visual Synthesizer:** Powered by `gemini-3.6-flash`, enabling custom data slices, dynamic chart generation via structured JSON plans, and grounded institutional dossier synthesis.
* **💬 Interactive Gemini Q&A:** Grounded natural-language query interface for querying Fall 2025 admissions metrics.

---

## 🛠️ Tech Stack & Setup

* **Frontend & Web App:** Streamlit
* **Data Processing & Analytics:** Python, Pandas, NumPy
* **Visualizations:** Plotly Express, Plotly Graph Objects
* **Generative AI:** Google GenAI SDK (`google-genai`), `gemini-3.6-flash`

### Installation & Local Run

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/your-username/uc-dashboard.git](https://github.com/your-username/uc-dashboard.git)
   cd uc-dashboard
