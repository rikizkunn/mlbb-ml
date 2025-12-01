import requests
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

def scrape_mlbb_data():
    """
    Scrape Mobile Legends hero statistics data from the API
    """
    url = 'https://mlbb.io/api/hero/filtered-statistics?rankId=6&timeframeId=5'
    
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.9,id;q=0.8,ga;q=0.7',
        'priority': 'u=1, i',
        'referer': 'https://mlbb.io/hero-statistics',
        'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        'x-client-secret': '259009191be734535393edc59e865dce'
    }
    
    cookies = {
        'locale': 'en',
        '__Host-next-auth.csrf-token': 'd1c994b1e4f940c46de8c79e8ffb04802fa5ab7a6837ba9d9e27f229eeeb4668%7C457f92ce86ec05a3782929593882a5276721a5c4ccfa4c35acb2ef11076eb38d',
        '__Secure-next-auth.callback-url': 'https%3A%2F%2Fmlbb.io',
        '_pk_id.1.cb63': '4efe70aa70b5b9d6.1764512705.',
        '_pk_ref.1.cb63': '%5B%22%22%2C%22%22%2C1764523742%2C%22https%3A%2F%2Fwww.google.com%2F%22%5D',
        '_pk_ses.1.cb63': '1'
    }
    
    try:
        response = requests.get(url, headers=headers, cookies=cookies, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('success'):
            return data['data']
        else:
            print("API returned unsuccessful response")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

def create_dataset(hero_data):
    """
    Create dataset from scraped hero data
    """
    heroes = []
    
    for hero in hero_data:
        hero_info = {
            'hero_id': hero['hero_id'],
            'hero_name': hero['hero_name'],
            'role': hero['role'][0] if hero['role'] else 'Unknown',
            'lane': hero['lane'][0] if hero['lane'] else 'Unknown',
            'pick_rate': hero['pick_rate'],
            'win_rate': hero['win_rate'],
            'ban_rate': hero['ban_rate'],
            'speciality': ', '.join(hero['speciality']) if hero['speciality'] else 'Unknown'
        }
        heroes.append(hero_info)
    
    df = pd.DataFrame(heroes)
    return df

def preprocess_data(df, weights=None):
    if weights is None:
        weights = {'pick_rate': 1, 'win_rate': 2, 'ban_rate': 3}
    
    # Select features for clustering
    features = ['pick_rate', 'win_rate', 'ban_rate']
    X = df[features].copy()
    
    # Apply weights as mentioned in the paper
    X_weighted = X.copy()
    for feature, weight in weights.items():
        X_weighted[feature] = X[feature] * weight
    
    # Remove outliers using Z-score (optional)
    z_scores = stats.zscore(X_weighted)
    abs_z_scores = np.abs(z_scores)
    filtered_entries = (abs_z_scores < 3).all(axis=1)
    X_clean = X_weighted[filtered_entries]
    df_clean = df[filtered_entries].copy()
    
    print(f"Original data: {len(X)} heroes")
    print(f"After outlier removal: {len(X_clean)} heroes")
    
    # Normalize data using Min-Max scaling (as mentioned in paper)
    scaler = MinMaxScaler()
    X_normalized = scaler.fit_transform(X_clean)
    
    return X_normalized, df_clean, scaler

def perform_kmeans_clustering(X, n_clusters=3, random_state=42):
    """
    Perform K-Means clustering
    """
    kmeans = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    clusters = kmeans.fit_predict(X)
    
    # Calculate silhouette score
    silhouette_avg = silhouette_score(X, clusters)
    
    return clusters, kmeans, silhouette_avg

def visualize_clusters(X, clusters, hero_names, algorithm_name="K-Means"):
    """
    Visualize clusters using PCA (2D visualization)
    """
    # Apply PCA for 2D visualization
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X)
    
    # Create visualization
    plt.figure(figsize=(12, 8))
    
    # Create scatter plot
    scatter = plt.scatter(X_pca[:, 0], X_pca[:, 1], c=clusters, 
                         cmap='viridis', alpha=0.7, s=60)
    
    # Add hero names as annotations
    for i, hero_name in enumerate(hero_names):
        plt.annotate(hero_name, (X_pca[i, 0], X_pca[i, 1]), 
                    xytext=(5, 5), textcoords='offset points',
                    fontsize=8, alpha=0.7)
    
    plt.colorbar(scatter, label='Cluster')
    plt.title(f'{algorithm_name} Clustering Visualization (PCA)')
    plt.xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.2%} variance)')
    plt.ylabel(f'PC2 ({pca.explained_variance_ratio_[1]:.2%} variance)')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()
    
    return X_pca

def analyze_clusters(df, clusters):
    """
    Analyze and interpret the clusters
    """
    df_clustered = df.copy()
    df_clustered['cluster'] = clusters
    
    # Map clusters to categories based on paper
    cluster_mapping = {
        0: 'Hero Non-META',
        1: 'Hero Situasional', 
        2: 'Hero META'
    }
    
    df_clustered['category'] = df_clustered['cluster'].map(cluster_mapping)
    
    # Calculate cluster statistics
    cluster_stats = df_clustered.groupby('category').agg({
        'pick_rate': ['mean', 'std'],
        'win_rate': ['mean', 'std'], 
        'ban_rate': ['mean', 'std'],
        'hero_name': 'count'
    }).round(2)
    
    print("=" * 60)
    print("CLUSTER ANALYSIS RESULTS")
    print("=" * 60)
    print(f"\nCluster Distribution:")
    print(df_clustered['category'].value_counts())
    
    print(f"\nCluster Statistics:")
    print(cluster_stats)
    
    return df_clustered

def find_optimal_k(X, max_k=10):
    """
    Find optimal number of clusters using Elbow method and Silhouette scores
    """
    wcss = []  # Within-Cluster Sum of Square
    silhouette_scores = []
    
    k_range = range(2, max_k + 1)
    
    for k in k_range:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(X)
        
        wcss.append(kmeans.inertia_)
        silhouette_scores.append(silhouette_score(X, clusters))
    
    # Plot Elbow method
    plt.figure(figsize=(15, 5))
    
    plt.subplot(1, 2, 1)
    plt.plot(k_range, wcss, 'bo-')
    plt.xlabel('Number of Clusters (k)')
    plt.ylabel('Within-Cluster Sum of Squares (WCSS)')
    plt.title('Elbow Method for Optimal k')
    plt.grid(True, alpha=0.3)
    
    plt.subplot(1, 2, 2)
    plt.plot(k_range, silhouette_scores, 'ro-')
    plt.xlabel('Number of Clusters (k)')
    plt.ylabel('Silhouette Score')
    plt.title('Silhouette Scores for Different k')
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()
    
    # Find optimal k based on silhouette score
    optimal_k = k_range[np.argmax(silhouette_scores)]
    print(f"Optimal number of clusters based on silhouette score: {optimal_k}")
    
    return optimal_k

def main():
    """
    Main function to execute the complete pipeline
    """
    print("Mobile Legends Hero Clustering Analysis")
    print("=" * 50)
    
    # Step 1: Scrape data
    print("Step 1: Scraping data from MLBB API...")
    hero_data = scrape_mlbb_data()
    
    if hero_data is None:
        print("Failed to fetch data. Using sample data for demonstration.")
        # Create sample data for demonstration
        hero_data = [
            {
                "hero_id": 109, "hero_name": "Aamon", "role": ["Assassin"], 
                "lane": ["Jungle"], "speciality": ["Chase", "Magic Damage"],
                "pick_rate": 0.99, "win_rate": 54.05, "ban_rate": 54.1
            },
            {
                "hero_id": 9, "hero_name": "Akai", "role": ["Tank"], 
                "lane": ["Roam"], "speciality": ["Guard", "Crowd Control"],
                "pick_rate": 0.49, "win_rate": 48.93, "ban_rate": 0.57
            },
            # Add more sample data as needed
        ]
    
    # Step 2: Create dataset
    print("Step 2: Creating dataset...")
    df = create_dataset(hero_data)
    print(f"Dataset created with {len(df)} heroes")
    
    # Step 3: Preprocess data with weights from paper
    print("Step 3: Preprocessing data...")
    weights = {'pick_rate': 1, 'win_rate': 2, 'ban_rate': 3}  # From paper
    X, df_clean, scaler = preprocess_data(df, weights)
    
    # Step 4: Find optimal k
    print("Step 4: Finding optimal number of clusters...")
    optimal_k = find_optimal_k(X, max_k=8)
    
    # Step 5: Perform K-Means clustering with k=3 (as in paper)
    print("Step 5: Performing K-Means clustering...")
    clusters, kmeans_model, silhouette_avg = perform_kmeans_clustering(X, n_clusters=4)
    
    print(f"K-Means Silhouette Score: {silhouette_avg:.3f}")
    
    # Step 6: Analyze clusters
    print("Step 6: Analyzing clusters...")
    df_result = analyze_clusters(df_clean, clusters)
    
    # Step 7: Visualize results
    print("Step 7: Visualizing clusters...")
    X_pca = visualize_clusters(X, clusters, df_result['hero_name'].tolist())
    
    # Display top heroes in each cluster
    print("\n" + "=" * 60)
    print("TOP HEROES IN EACH CATEGORY")
    print("=" * 60)
    
    for category in ['Hero META', 'Hero Situasional', 'Hero Non-META']:
        category_heroes = df_result[df_result['category'] == category]
        
        # Sort by a combined score (pick_rate + win_rate + ban_rate)
        category_heroes = category_heroes.copy()
        category_heroes['combined_score'] = (category_heroes['pick_rate'] + 
                                           category_heroes['win_rate'] + 
                                           category_heroes['ban_rate'])
        
        top_heroes = category_heroes.nlargest(5, 'combined_score')[['hero_name', 'pick_rate', 'win_rate', 'ban_rate']]
        
        print(f"\n{category}:")
        print(top_heroes.to_string(index=False))
    
    # Save results to CSV
    output_file = 'mlbb_hero_clustering_results.csv'
    df_result.to_csv(output_file, index=False)
    print(f"\nResults saved to: {output_file}")
    
    return df_result, kmeans_model, silhouette_avg

if __name__ == "__main__":
    df_result, model, score = main()