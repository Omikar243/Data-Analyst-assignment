import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(page_title="Resource Sustainability Dashboard", layout="wide")
st.markdown(
    """
    <style>
    .dataframe-container {
        display: block;
        max-height: 500px;
        overflow-y: auto;
        overflow-x: auto;
        border: 1px solid #ddd;
        margin-bottom: 20px;
    }
    table {
        width: 100%;
        border-collapse: collapse;
    }
    table, th, td {
        border: 1px solid #ddd;
    }
    th, td {
        padding: 8px;
        text-align: center;
    }
    th {
        background-color: #f2f2f2;
        position: sticky;
        top: 0;
        z-index: 1;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

def normalize_series(series, new_min=1, new_max=1000, inverse=True):
    """Normalize series with option to inverse (higher values = lower score)"""
    if series.max() == series.min():
        return pd.Series(new_min if inverse else new_max, index=series.index)
    
    if inverse:
        norm = (series.max() - series) / (series.max() - series.min())
    else:
        norm = (series - series.min()) / (series.max() - series.min())
    
    return norm * (new_max - new_min) + new_min

def generate_feature_data(n, dist_type, params):
    if dist_type == "Uniform":
        low, high = int(params['min']), int(params['max'])
        data = np.random.randint(low, high+1, size=n)
    elif dist_type == "Normal":
        mean, std = params['mean'], params['std']
        data = np.random.normal(mean, std, size=n)
    elif dist_type == "Poisson":
        lam = params['lambda']
        data = np.random.poisson(lam, size=n)
    elif dist_type == "Exponential":
        scale = params['scale']
        data = np.random.exponential(scale, size=n)
    elif dist_type == "Binomial":
        n_trials = int(params.get('n_trials', 10))
        p = params.get('p', 0.5)
        data = np.random.binomial(n_trials, p, size=n)
    elif dist_type == "Lognormal":
        mean, sigma = params['mean'], params['sigma']
        data = np.random.lognormal(mean, sigma, size=n)
    else:
        low, high = int(params['min']), int(params['max'])
        data = np.random.randint(low, high+1, size=n)
    data = np.clip(data, params['min'], params['max'])
    return np.round(data).astype(int)

def generate_synthetic_data(n, feature_settings):
    data = {}
    for feature, (dist_type, params) in feature_settings.items():
        data[feature] = generate_feature_data(n, dist_type, params)
    df = pd.DataFrame(data)
    df.insert(0, "ID", range(1, n+1))
    return df

def compute_feature_stats(df):
    """Compute statistics for each feature for baseline comparison"""
    feature_stats = {}
    for col in df.columns:
        if col not in ["ID", "Weighted_Score", "Rank", "Z_Score"]:
            feature_stats[col] = {
                'mean': df[col].mean(),
                'median': df[col].median(),
                'std': df[col].std(),
                'min': df[col].min(),
                'max': df[col].max()
            }
    return feature_stats

def compute_weighted_score(raw_df, weights, inverse=True):
    """Compute weighted score with option for inverse relationship"""
    df = raw_df.copy()
    
    norm_values = {}
    z_scores = {}
    for col in df.columns:
        if col not in ["ID", "Weighted_Score", "Rank", "Z_Score"]:
            norm_values[col] = normalize_series(df[col], 1, 1000, inverse=inverse)
            z_scores[col] = (df[col] - df[col].mean()) / df[col].std()
            if inverse:
                z_scores[col] = -z_scores[col]
            df[f"{col}_normalized"] = norm_values[col]
            df[f"{col}_z_score"] = z_scores[col]
    
    weighted_sum = 0
    feature_contributions = {}
    for key, weight in weights.items():
        if key in norm_values:
            contribution = norm_values[key] * weight
            weighted_sum += contribution
            feature_contributions[key] = contribution
            df[f"{key}_contribution"] = contribution
    
    df['Weighted_Score'] = weighted_sum
    df['Z_Score'] = sum(z_scores[key] * weights[key] for key in weights if key in z_scores)
    df['Rank'] = df['Weighted_Score'].rank(method='min', ascending=False).astype(int)
    
    df.sort_values('Rank', inplace=True)
    
    return df, feature_contributions

def render_html_table(df):
    df_round = df.copy()
    numeric_cols = df_round.select_dtypes(include=['number']).columns
    df_round[numeric_cols] = df_round[numeric_cols].round(2)
    html_table = df_round.to_html(index=False, classes="dataframe", border=0)
    return f'<div class="dataframe-container">{html_table}</div>'

def feature_distribution_ui(feature_name, default_min=1, default_max=1000):
    st.markdown(f"#### {feature_name} Settings")
    dist_type = st.selectbox(
        f"Select Distribution for {feature_name}",
        options=["Uniform", "Normal", "Poisson", "Exponential", "Binomial", "Lognormal"],
        key=f"dist_{feature_name}"
    )
    params = {}
    if dist_type == "Uniform":
        params['min'] = st.number_input(f"{feature_name} Minimum", value=default_min, key=f"{feature_name}_min")
        params['max'] = st.number_input(f"{feature_name} Maximum", value=default_max, key=f"{feature_name}_max")
    elif dist_type == "Normal":
        params['mean'] = st.number_input(f"{feature_name} Mean", value=(default_min+default_max)//2, key=f"{feature_name}_mean")
        params['std'] = st.number_input(f"{feature_name} Std Deviation", value=100, key=f"{feature_name}_std")
        params['min'] = st.number_input(f"{feature_name} Minimum", value=default_min, key=f"{feature_name}_min")
        params['max'] = st.number_input(f"{feature_name} Maximum", value=default_max, key=f"{feature_name}_max")
    elif dist_type == "Poisson":
        params['lambda'] = st.number_input(f"{feature_name} Lambda", value=(default_min+default_max)//2, key=f"{feature_name}_lambda")
        params['min'] = st.number_input(f"{feature_name} Minimum", value=default_min, key=f"{feature_name}_min")
        params['max'] = st.number_input(f"{feature_name} Maximum", value=default_max, key=f"{feature_name}_max")
    elif dist_type == "Exponential":
        params['scale'] = st.number_input(f"{feature_name} Scale", value=100, key=f"{feature_name}_scale")
        params['min'] = st.number_input(f"{feature_name} Minimum", value=default_min, key=f"{feature_name}_min")
        params['max'] = st.number_input(f"{feature_name} Maximum", value=default_max, key=f"{feature_name}_max")
    elif dist_type == "Binomial":
        params['n_trials'] = st.number_input(f"{feature_name} Number of Trials", value=10, key=f"{feature_name}_n_trials")
        params['p'] = st.number_input(f"{feature_name} Probability", min_value=0.0, max_value=1.0, value=0.5, key=f"{feature_name}_p")
        params['min'] = st.number_input(f"{feature_name} Minimum", value=default_min, key=f"{feature_name}_min")
        params['max'] = st.number_input(f"{feature_name} Maximum", value=default_max, key=f"{feature_name}_max")
    elif dist_type == "Lognormal":
        params['mean'] = st.number_input(f"{feature_name} Mean", value=4, key=f"{feature_name}_mean")
        params['sigma'] = st.number_input(f"{feature_name} Sigma", value=0.5, key=f"{feature_name}_sigma")
        params['min'] = st.number_input(f"{feature_name} Minimum", value=default_min, key=f"{feature_name}_min")
        params['max'] = st.number_input(f"{feature_name} Maximum", value=default_max, key=f"{feature_name}_max")
    return dist_type, params

st.title("Resource Sustainability Consumption Dashboard")
st.markdown("Enhance your synthetic data and rank users based on weighted resource consumption.")

st.sidebar.markdown("## Data Configuration")
data_source = st.sidebar.radio("Select Data Source", ["Generate Synthetic Data", "Upload CSV Data"], key="data_source")

scoring_method = st.sidebar.radio(
    "Scoring Method",
    ["Inverse (Higher usage = Lower score)", "Direct (Higher usage = Higher score)"],
    key="scoring_method"
)
inverse_scoring = scoring_method == "Inverse (Higher usage = Lower score)"

if data_source == "Generate Synthetic Data":
    n_users = st.sidebar.number_input("Number of Individuals", min_value=1, value=100, step=1)
    
    st.sidebar.markdown("## Set Feature Distributions")
    st.sidebar.markdown("### Electricity Consumption")
    dist_elec, params_elec = feature_distribution_ui("Electricity", default_min=100, default_max=1000)
    
    st.sidebar.markdown("### Water Consumption")
    dist_water, params_water = feature_distribution_ui("Water", default_min=200, default_max=600)
    
    optional_features_settings = {}
    include_f1 = st.sidebar.checkbox("Include Feature-1", value=True, key="include_f1")
    if include_f1:
        custom_name_f1 = st.sidebar.text_input("Rename Feature-1", value="Feature-1", key="name_f1")
        dist_f1, params_f1 = feature_distribution_ui(custom_name_f1, default_min=1, default_max=100)
        optional_features_settings[custom_name_f1] = (dist_f1, params_f1)
    
    include_f2 = st.sidebar.checkbox("Include Feature-2", value=True, key="include_f2")
    if include_f2:
        custom_name_f2 = st.sidebar.text_input("Rename Feature-2", value="Feature-2", key="name_f2")
        dist_f2, params_f2 = feature_distribution_ui(custom_name_f2, default_min=1, default_max=100)
        optional_features_settings[custom_name_f2] = (dist_f2, params_f2)
    
    include_f3 = st.sidebar.checkbox("Include Feature-3", value=True, key="include_f3")
    if include_f3:
        custom_name_f3 = st.sidebar.text_input("Rename Feature-3", value="Feature-3", key="name_f3")
        dist_f3, params_f3 = feature_distribution_ui(custom_name_f3, default_min=1, default_max=100)
        optional_features_settings[custom_name_f3] = (dist_f3, params_f3)
    
    include_f4 = st.sidebar.checkbox("Include Feature-4", value=True, key="include_f4")
    if include_f4:
        custom_name_f4 = st.sidebar.text_input("Rename Feature-4", value="Feature-4", key="name_f4")
        dist_f4, params_f4 = feature_distribution_ui(custom_name_f4, default_min=1, default_max=100)
        optional_features_settings[custom_name_f4] = (dist_f4, params_f4)
    
    feature_settings = {
        "Electricity": (dist_elec, params_elec),
        "Water": (dist_water, params_water)
    }
    feature_settings.update(optional_features_settings)
    
    if st.sidebar.button("Generate Synthetic Data"):
        raw = generate_synthetic_data(n_users, feature_settings)
        st.session_state.synth_data_raw = raw
        
        feature_constraints = {}
        for feat, setting in feature_settings.items():
            params = setting[1]
            feature_constraints[feat] = (params['min'], params['max'])
        st.session_state.feature_constraints = feature_constraints
        
        
        st.session_state.feature_stats = compute_feature_stats(raw)
        
        st.sidebar.success("Synthetic data generated successfully!")

elif data_source == "Upload CSV Data":
    st.sidebar.markdown("### Upload your CSV file")
    uploaded_file = st.sidebar.file_uploader("Choose a CSV file", type="csv", key="uploaded_csv")
    
    if st.sidebar.button("Load Data"):
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
            st.session_state.synth_data_raw = df
            
            
            constraints = {}
            for col in df.columns:
                if col != "ID":
                    constraints[col] = (df[col].min(), df[col].max())
            st.session_state.feature_constraints = constraints
            
            st.session_state.feature_stats = compute_feature_stats(df)
            
            st.sidebar.success("Data loaded successfully!")
        else:
            st.sidebar.error("Please upload a CSV file.")
    template_df = pd.DataFrame(columns=["ID", "Electricity", "Water", "Feature-1", "Feature-2", "Feature-3", "Feature-4"])
    csv_template = template_df.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button("Download CSV Template", data=csv_template, file_name="template.csv", mime="text/csv")

if "synth_data_raw" in st.session_state:
    st.markdown("## Data Preview")
    html_table = render_html_table(st.session_state.synth_data_raw)
    st.markdown(html_table, unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("## Weighted Score Settings")
    features_for_weight = {col: None for col in st.session_state.synth_data_raw.columns if col not in ["ID"]}
    default_weight = round(1 / len(features_for_weight), 4)
    weight_inputs = {}
    for feat in features_for_weight:
        weight_inputs[feat] = st.number_input(f"Weight: {feat}", value=default_weight, step=0.01, format="%.4f", key=f"weight_{feat}")
    weights = weight_inputs
    total_weight = sum(weights.values())
    st.markdown(f"**Total Weight:** {total_weight:.2f}")
    if abs(total_weight - 1.0) > 0.001:
        st.error("Weights must sum exactly to 1!")
    else:
        if st.button("Generate Weighted Score"):
            final_df, feature_contributions = compute_weighted_score(st.session_state.synth_data_raw, weights, inverse=inverse_scoring)
            st.session_state.scored_data = final_df
            st.session_state.weights = weights
            st.success("Weighted score and ranking generated!")
            st.markdown("## Ranked Individuals Based on Weighted Score")
            final_html = render_html_table(st.session_state.scored_data.reset_index(drop=True))
            st.markdown(final_html, unsafe_allow_html=True)
    if st.checkbox("Show Distribution Graphs"):
        for col in st.session_state.synth_data_raw.columns:
            if col != "ID":
                fig, ax = plt.subplots()
                sns.histplot(st.session_state.synth_data_raw[col], bins=30, kde=True, ax=ax)
                ax.set_title(f"Distribution of {col}")
                st.pyplot(fig)
        if "scored_data" in st.session_state:
            fig, ax = plt.subplots()
            sns.histplot(st.session_state.scored_data["Weighted_Score"], bins=30, kde=True, ax=ax)
            ax.set_title("Distribution of Weighted Score")
            st.pyplot(fig)
    st.markdown("## Test New Customer")
    test_mode = st.radio("Select Input Mode for New Customer", ["Manual Entry", "CSV Upload"], key="test_mode")
    features = [col for col in st.session_state.synth_data_raw.columns if col not in ["ID", "Weighted_Score", "Rank"]]
    if test_mode == "Manual Entry":
        st.markdown("### Enter Customer Feature Values")
        new_customer = {}
        for feat in features:
            if "feature_constraints" in st.session_state and feat in st.session_state.feature_constraints:
                constraint_min, constraint_max = st.session_state.feature_constraints[feat]
            else:
                constraint_min = st.session_state.synth_data_raw[feat].min()
                constraint_max = st.session_state.synth_data_raw[feat].max()
            new_customer[feat] = st.number_input(f"{feat} (Allowed range: {constraint_min} - {constraint_max})", 
                                                value=constraint_min, key=f"test_{feat}")
            
        if st.button("Evaluate Customer"):
            norm_values = {}
            for feat in features:
                if "feature_constraints" in st.session_state and feat in st.session_state.feature_constraints:
                    constraint_min, constraint_max = st.session_state.feature_constraints[feat]
                else:
                    constraint_min = st.session_state.synth_data_raw[feat].min()
                    constraint_max = st.session_state.synth_data_raw[feat].max()
                
                val = new_customer[feat]
                if val < constraint_min:
                    st.info(f"{feat} value is below the allowed minimum of {constraint_min}.")
                elif val > constraint_max:
                    st.info(f"{feat} value is above the allowed maximum of {constraint_max}.")
                
                if constraint_max == constraint_min:
                    norm_val = 1000 if not inverse_scoring else 1
                    norm_values[feat] = norm_val
                else:
                    if inverse_scoring:
                        norm_val = (constraint_max - val) / (constraint_max - constraint_min) * 999 + 1
                    else:
                        norm_val = (val - constraint_min) / (constraint_max - constraint_min) * 999 + 1
                    norm_values[feat] = norm_val
                    
            if "weights" not in st.session_state:
                st.error("Please generate weighted scores first.")
            else:
                weights = st.session_state.weights
                score = sum(norm_values[feat] * weights.get(feat, 0) for feat in features)
                if "scored_data" not in st.session_state:
                    st.error("Please generate weighted scores first.")
                existing_scores = st.session_state.scored_data["Weighted_Score"]
                rank = (existing_scores > score).sum() + 1
                st.success(f"Customer Score: {score:.2f} (Estimated Rank: {rank})")
                
                
                contributions = {feat: norm_values[feat] * weights.get(feat, 0) for feat in features}
                sorted_contrib = sorted(contributions.items(), key=lambda x: x[1], reverse=True)
                
                st.markdown("**Feature Contributions:**")
                for feat, contrib in sorted_contrib:
                    percentage = (contrib / score * 100) if score != 0 else 0
                    st.write(f"{feat}: {contrib:.2f} ({percentage:.2f}%)")
                
                
                fig, ax = plt.subplots()
                labels = list(contributions.keys())
                sizes = list(contributions.values())
                ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
                ax.axis('equal')
                st.pyplot(fig)
                
    else:
        new_user_template_df = pd.DataFrame(columns=features)
        csv_new_user_template = new_user_template_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download New Customer Template", data=csv_new_user_template, file_name="new_customer_template.csv", mime="text/csv")

        uploaded_test = st.file_uploader("Upload CSV for New Customers", type="csv", key="test_csv")
        if st.button("Evaluate Test Customers"):
            if uploaded_test is not None:
                test_df = pd.read_csv(uploaded_test)
                scores = []
                ranks = []
                for i, row in test_df.iterrows():
                    norm_values = {}
                    for feat in features:
                        if "feature_constraints" in st.session_state and feat in st.session_state.feature_constraints:
                            constraint_min, constraint_max = st.session_state.feature_constraints[feat]
                        else:
                            constraint_min = st.session_state.synth_data_raw[feat].min()
                            constraint_max = st.session_state.synth_data_raw[feat].max()
                        val = row[feat]
                        if val < constraint_min:
                            st.info(f"{feat} value in row {i+1} is below the allowed minimum of {constraint_min}.")
                        elif val > constraint_max:
                            st.info(f"{feat} value in row {i+1} is above the allowed maximum of {constraint_max}.")
                        if constraint_max == constraint_min:
                            norm_val = 1
                        else:
                            norm_val = (val - constraint_min) / (constraint_max - constraint_min) * (1000 - 1) + 1
                        norm_values[feat] = norm_val
                    score = sum(norm_values[feat] * st.session_state.weights.get(feat, 0) for feat in features)
                    scores.append(score)
                    existing_scores = st.session_state.scored_data["Weighted_Score"]
                    rank_val = (existing_scores > score).sum() + 1
                    ranks.append(rank_val)
                test_df["Weighted_Score"] = scores
                test_df["Estimated Rank"] = ranks
                st.write("Evaluated Customer Data", test_df)
            else:
                st.error("Please upload a CSV file.")
