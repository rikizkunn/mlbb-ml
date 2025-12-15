import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA
import warnings
warnings.filterwarnings('ignore')

# Page configuration
st.set_page_config(
    page_title="MLBB Hero Clustering Analysis",
    page_icon="🎮",
    layout="wide"
)

# Title
st.title("🎮 Mobile Legends Hero Clustering Analysis")
st.markdown("---")

# File uploader
uploaded_file = st.file_uploader("Upload MLBB Heroes Dataset (CSV)", type=['csv'])

if uploaded_file is not None:
    # Load dataset
    df = pd.read_csv(uploaded_file)
    
    # Calculate additional metrics
    df['total_matches'] = df['total_picks'] + df['total_bans']
    df['ban_rate'] = df['total_bans'] / df['total_matches'] * 100
    
    # Sidebar
    st.sidebar.header("📊 Analysis Settings")
    show_elbow = st.sidebar.checkbox("Show Elbow Method Analysis", value=True)
    n_clusters = 3  # Fixed to 5
    st.sidebar.info(f"**Number of Clusters: {n_clusters}** (Fixed)")
    show_labels = st.sidebar.checkbox("Show Hero Labels on Cluster Plot", value=True)
    
    # Dataset Overview
    st.header("📋 Dataset Overview")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Heroes", len(df))
    with col2:
        st.metric("Total Roles", df['Primary_Role'].nunique())
    with col3:
        st.metric("Avg Win Rate", f"{df['overall_win_rate'].mean():.2f}%")
    
    with st.expander("View Raw Data"):
        st.dataframe(df.head(10))
    
    st.markdown("---")
    
    # Role Distribution
    st.header("🎯 Role Distribution Analysis")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Hero Count by Role")
        fig1, ax1 = plt.subplots(figsize=(8, 6))
        role_counts = df['Primary_Role'].value_counts()
        ax1.pie(role_counts.values, labels=role_counts.index, autopct='%1.1f%%', 
                startangle=90, colors=plt.cm.Set3.colors)
        ax1.set_title('Hero Role Distribution')
        st.pyplot(fig1)
    
    with col2:
        st.subheader("Average Win Rate by Role")
        fig2, ax2 = plt.subplots(figsize=(8, 6))
        role_avg_winrate = df.groupby('Primary_Role')['overall_win_rate'].mean()
        ax2.pie(role_avg_winrate.values, labels=role_avg_winrate.index, autopct='%1.1f%%',
                startangle=90, colors=plt.cm.Paired.colors)
        ax2.set_title('Average Win Rate by Role')
        st.pyplot(fig2)
    
    st.markdown("---")
    
    # Top Heroes
    st.header("⭐ Top 10 Heroes Analysis")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Most Picked Heroes")
        fig3, ax3 = plt.subplots(figsize=(8, 6))
        top_10_picks = df.nlargest(10, 'total_picks').sort_values('total_picks')
        ax3.plot(top_10_picks['hero'], top_10_picks['total_picks'], 
                marker='o', linewidth=2, color='#1f77b4')
        ax3.set_xlabel('Hero')
        ax3.set_ylabel('Total Picks')
        ax3.tick_params(axis='x', rotation=45)
        ax3.grid(True, alpha=0.3)
        plt.tight_layout()
        st.pyplot(fig3)
    
    with col2:
        st.subheader("Most Banned Heroes")
        fig4, ax4 = plt.subplots(figsize=(8, 6))
        top_10_bans = df.nlargest(10, 'total_bans').sort_values('total_bans')
        ax4.plot(top_10_bans['hero'], top_10_bans['total_bans'], 
                marker='s', linewidth=2, color='orange')
        ax4.set_xlabel('Hero')
        ax4.set_ylabel('Total Bans')
        ax4.tick_params(axis='x', rotation=45)
        ax4.grid(True, alpha=0.3)
        plt.tight_layout()
        st.pyplot(fig4)
    
    st.markdown("---")
    
    # Distribution Analysis
    st.header("📦 Distribution Analysis")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Win Rate Distribution by Role")
        fig5, ax5 = plt.subplots(figsize=(8, 6))
        sns.boxplot(data=df, x='Primary_Role', y='overall_win_rate', ax=ax5)
        ax5.set_xlabel('Role')
        ax5.set_ylabel('Win Rate (%)')
        ax5.tick_params(axis='x', rotation=45)
        ax5.axhline(y=50, color='r', linestyle='--', alpha=0.5, label='50% baseline')
        ax5.legend()
        plt.tight_layout()
        st.pyplot(fig5)
    
    with col2:
        st.subheader("Pick Rate Distribution by Role")
        fig6, ax6 = plt.subplots(figsize=(8, 6))
        sns.boxplot(data=df, x='Primary_Role', y='total_picks', ax=ax6)
        ax6.set_xlabel('Role')
        ax6.set_ylabel('Total Picks')
        ax6.tick_params(axis='x', rotation=45)
        ax6.set_yscale('log')
        plt.tight_layout()
        st.pyplot(fig6)
    
    st.markdown("---")
    
    # Scatter Plot
    st.header("🔍 Pick Rate vs Win Rate Analysis")
    fig7, ax7 = plt.subplots(figsize=(12, 8))
    scatter = ax7.scatter(df['total_picks'], df['overall_win_rate'],
                         c=pd.Categorical(df['Primary_Role']).codes,
                         cmap='tab10',
                         s=df['total_bans']/10 + 30,
                         alpha=0.7,
                         edgecolors='black')
    ax7.set_xlabel('Total Picks')
    ax7.set_ylabel('Win Rate (%)')
    ax7.axhline(y=50, color='r', linestyle='--', alpha=0.5)
    ax7.grid(True, alpha=0.3)
    ax7.set_title('Pick Rate vs Win Rate (Bubble Size = Ban Count)')
    plt.tight_layout()
    st.pyplot(fig7)
    
    st.markdown("---")
    
    # Correlation Matrix
    st.header("🔗 Correlation Analysis")
    corr_matrix = df[['total_picks', 'total_bans', 'overall_win_rate', 'ban_rate']].corr()
    fig8, ax8 = plt.subplots(figsize=(8, 6))
    sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='coolwarm', ax=ax8)
    ax8.set_title('Correlation Matrix')
    st.pyplot(fig8)
    
    st.markdown("---")
    
    # K-Means Clustering
    st.header("🤖 K-Means Clustering Analysis")
    
    with st.spinner("Performing K-Means clustering..."):
        # Prepare features
        features = ['total_picks', 'total_bans', 'overall_win_rate', 'ban_rate']
        X = df[features].copy()
        
        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Show Elbow Method if enabled
        if show_elbow:
            st.subheader("📈 Elbow Method Analysis")
            st.info("Finding optimal K using Elbow Method and Silhouette Score (using K=5)")
            
            wcss = []
            silhouette_scores = []
            k_range = range(2, 11)
            
            for k in k_range:
                kmeans_temp = KMeans(n_clusters=k, random_state=42, n_init=10)
                kmeans_temp.fit(X_scaled)
                wcss.append(kmeans_temp.inertia_)
                silhouette_scores.append(silhouette_score(X_scaled, kmeans_temp.labels_))
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig_elbow, ax_elbow = plt.subplots(figsize=(8, 6))
                ax_elbow.plot(k_range, wcss, marker='o', linewidth=2, markersize=8)
                ax_elbow.axvline(x=5, color='r', linestyle='--', alpha=0.7, linewidth=2, label='K=5 (Selected)')
                ax_elbow.set_title('Elbow Method', fontsize=12, fontweight='bold')
                ax_elbow.set_xlabel('Number of Clusters (K)')
                ax_elbow.set_ylabel('WCSS (Within-Cluster Sum of Squares)')
                ax_elbow.grid(True, alpha=0.3)
                ax_elbow.legend()
                plt.tight_layout()
                st.pyplot(fig_elbow)
            
            with col2:
                fig_sil, ax_sil = plt.subplots(figsize=(8, 6))
                ax_sil.plot(k_range, silhouette_scores, marker='s', linewidth=2, 
                           markersize=8, color='green')
                ax_sil.axvline(x=5, color='r', linestyle='--', alpha=0.7, linewidth=2, label='K=5 (Selected)')
                ax_sil.set_title('Silhouette Scores', fontsize=12, fontweight='bold')
                ax_sil.set_xlabel('Number of Clusters (K)')
                ax_sil.set_ylabel('Silhouette Score')
                ax_sil.grid(True, alpha=0.3)
                ax_sil.legend()
                plt.tight_layout()
                st.pyplot(fig_sil)
            
            st.markdown("---")
        
        # Apply K-Means with K=5
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(X_scaled)
        df['cluster'] = clusters
        
        # Define category color map
        category_color_map = {
            "META": "#FF4444",
            "PRIORITY BAN": "#FF8800",
            "POPULAR BUT WEAK": "#FFDD00",
            "HIGH WIN RATE": "#44FF44",
            "SITUATIONAL": "#4444FF"
        }
        
        # Determine category for each cluster
        cluster_categories = {}
        cluster_colors = {}
        
        for cluster_id in sorted(df['cluster'].unique()):
            cluster_data = df[df['cluster'] == cluster_id]
            
            avg_picks = cluster_data['total_picks'].mean()
            avg_bans = cluster_data['total_bans'].mean()
            avg_winrate = cluster_data['overall_win_rate'].mean()
            avg_banrate = cluster_data['ban_rate'].mean()
            
            # Determine cluster category
            if avg_picks > 1000 and avg_winrate > 52:
                category = "META"
            elif avg_bans > 500 and avg_banrate > 40:
                category = "PRIORITY BAN"
            elif avg_picks > 500 and avg_winrate < 48:
                category = "POPULAR BUT WEAK"
            elif avg_winrate > 54:
                category = "HIGH WIN RATE"
            else:
                category = "SITUATIONAL"
            
            cluster_categories[cluster_id] = category
            cluster_colors[cluster_id] = category_color_map[category]
        
        # Add category to dataframe
        df['category'] = df['cluster'].map(cluster_categories)
        df['category_color'] = df['cluster'].map(cluster_colors)
        
        # PCA for visualization
        pca = PCA(n_components=2)
        X_pca = pca.fit_transform(X_scaled)
        df['pca1'] = X_pca[:, 0]
        df['pca2'] = X_pca[:, 1]
        
        # Calculate metrics
        silhouette_avg = silhouette_score(X_scaled, clusters)
        
        # Display metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Number of Clusters", n_clusters)
        with col2:
            st.metric("Silhouette Score", f"{silhouette_avg:.3f}")
        with col3:
            st.metric("PCA Variance Explained", f"{pca.explained_variance_ratio_.sum():.1%}")
        
        st.markdown("---")
        
        # Cluster Visualization with Category Colors
        st.subheader("🎨 Cluster Visualization (Colored by Category)")
        
        fig9, ax9 = plt.subplots(figsize=(18, 13))
        
        # Plot each category with its color
        for category, color in category_color_map.items():
            mask = df['category'] == category
            if mask.any():
                ax9.scatter(df[mask]['pca1'], df[mask]['pca2'], 
                           c=color, 
                           label=category,
                           s=100, 
                           alpha=0.6,
                           edgecolors='black',
                           linewidth=0.5)
        
        # Add hero labels if enabled
        if show_labels:
            for idx, row in df.iterrows():
                ax9.annotate(row['hero'], 
                            (row['pca1'], row['pca2']),
                            fontsize=7,
                            alpha=0.9,
                            ha='center',
                            color=row['category_color'],
                            fontweight='bold')
        
        # Plot cluster centers
        centers_pca = pca.transform(kmeans.cluster_centers_)
        ax9.scatter(centers_pca[:, 0], centers_pca[:, 1], 
                   c='white', s=400, marker='X',
                   edgecolors='black', linewidths=3,
                   label='Cluster Centers', zorder=5)
        
        ax9.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.1%} variance)', fontsize=12)
        ax9.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]:.1%} variance)', fontsize=12)
        ax9.set_title(f'PCA Visualization of Hero Clusters (K={n_clusters}) - Colored by Category', 
                     fontsize=14, fontweight='bold')
        ax9.grid(True, alpha=0.3)
        ax9.legend(fontsize=11, loc='best', framealpha=0.9)
        plt.tight_layout()
        st.pyplot(fig9)
        
        st.markdown("---")
        
        # Category Distribution
        st.subheader("📊 Category Distribution")
        category_counts = df['category'].value_counts()
        
        col1, col2 = st.columns([1, 2])
        with col1:
            for category, count in category_counts.items():
                color = category_color_map[category]
                st.markdown(f"<div style='background-color: {color}; padding: 10px; margin: 5px; border-radius: 5px; color: black; font-weight: bold;'>{category}: {count} heroes</div>", unsafe_allow_html=True)
        
        with col2:
            fig_cat, ax_cat = plt.subplots(figsize=(8, 6))
            colors_list = [category_color_map[cat] for cat in category_counts.index]
            ax_cat.bar(category_counts.index, category_counts.values, color=colors_list, edgecolor='black', linewidth=1.5)
            ax_cat.set_xlabel('Category', fontsize=12)
            ax_cat.set_ylabel('Number of Heroes', fontsize=12)
            ax_cat.set_title('Heroes per Category', fontsize=14, fontweight='bold')
            ax_cat.tick_params(axis='x', rotation=45)
            plt.tight_layout()
            st.pyplot(fig_cat)
        
        st.markdown("---")
        
        # Cluster Analysis
        st.subheader("📊 Detailed Cluster Analysis")
        
        for cluster_id in sorted(df['cluster'].unique()):
            cluster_data = df[df['cluster'] == cluster_id]
            
            avg_picks = cluster_data['total_picks'].mean()
            avg_bans = cluster_data['total_bans'].mean()
            avg_winrate = cluster_data['overall_win_rate'].mean()
            avg_banrate = cluster_data['ban_rate'].mean()
            
            category = cluster_categories[cluster_id]
            color = cluster_colors[cluster_id]
            
            # Emoji mapping
            emoji_map = {
                "META": "🔴",
                "PRIORITY BAN": "🟠",
                "POPULAR BUT WEAK": "🟡",
                "HIGH WIN RATE": "🟢",
                "SITUATIONAL": "🔵"
            }
            
            with st.expander(f"{emoji_map[category]} Cluster {cluster_id} - {category} ({len(cluster_data)} heroes)"):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Avg Picks", f"{avg_picks:.0f}")
                with col2:
                    st.metric("Avg Bans", f"{avg_bans:.0f}")
                with col3:
                    st.metric("Avg Win Rate", f"{avg_winrate:.2f}%")
                with col4:
                    st.metric("Avg Ban Rate", f"{avg_banrate:.2f}%")
                
                st.write("**Heroes in this cluster:**")
                st.write(", ".join(sorted(cluster_data['hero'].tolist())))
        
        st.markdown("---")
        
        # Download results
        st.subheader("💾 Download Results")
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download Clustered Data as CSV",
            data=csv,
            file_name="mlbb_heroes_clustered.csv",
            mime="text/csv"
        )

else:
    st.info("👆 Please upload the MLBB Heroes dataset (CSV file) to begin the analysis.")
    st.markdown("""
    ### Expected CSV Format:
    The CSV should contain the following columns:
    - `hero`: Hero name
    - `Primary_Role`: Hero role (Tank, Fighter, Assassin, Mage, Marksman)
    - `total_picks`: Total number of picks
    - `total_wins`: Total wins
    - `total_losses`: Total losses
    - `total_bans`: Total bans
    - `overall_win_rate`: Win rate percentage
    
    ### Categories:
    - 🔴 **META**: High picks (>1000) and high win rate (>52%)
    - 🟠 **PRIORITY BAN**: High bans (>500) and high ban rate (>40%)
    - 🟡 **POPULAR BUT WEAK**: High picks (>500) but low win rate (<48%)
    - 🟢 **HIGH WIN RATE**: Win rate >54%
    - 🔵 **SITUATIONAL**: Other heroes
    """)