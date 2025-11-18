# src/clustering/engine.py
from kmedoids import KMedoids
from sklearn.metrics import silhouette_score
import numpy as np
import time

# Sử dụng relative import
from src import config

def analyze_k_and_suggest_optimal(dissimilarity_matrix: np.ndarray):
    """
    Phan tich diem Silhouette cho mot khoang k va goi y gia tri toi uu.
    """
    print("\n--- Analyzing Silhouette Score to find optimal k...")
    start_time = time.time()
    scores_by_k = {}
    
    for k in config.K_CLUSTERS_RANGE:
        print(f"  - Testing with k = {k}...")
        kmedoids = KMedoids(n_clusters=k, metric='precomputed', method='pam', init='build', random_state=config.RANDOM_SEED)
        labels = kmedoids.fit_predict(dissimilarity_matrix)
        
        if len(np.unique(labels)) > 1:
            score = silhouette_score(dissimilarity_matrix, labels, metric='precomputed')
            scores_by_k[k] = score
            print(f"    -> Silhouette Score: {score:.4f}")
        else:
            scores_by_k[k] = -1.0
            print(f"    -> Could not calculate Silhouette Score (only 1 cluster found).")

    if not scores_by_k:
        print("ERROR: No scores calculated. Cannot suggest an optimal k.")
        return None, {}
        
    k_suggested = max(scores_by_k, key=scores_by_k.get)
    
    end_time = time.time()
    print(f"Analysis completed in {end_time - start_time:.2f} seconds.")
    print(f"==> Optimal k suggested: {k_suggested} (with Silhouette Score = {scores_by_k[k_suggested]:.4f})")
    
    return k_suggested, scores_by_k

def run_clustering(dissimilarity_matrix: np.ndarray, n_clusters: int):
    """
    Chay thuat toan K-Medoids voi mot so cum n_clusters cho truoc.
    """
    print(f"\n--- Running final clustering with k = {n_clusters}...")
    start_time = time.time()

    kmedoids = KMedoids(n_clusters=n_clusters, metric='precomputed', method='pam', init='build', random_state=config.RANDOM_SEED)
    labels = kmedoids.fit_predict(dissimilarity_matrix)
    
    end_time = time.time()
    print(f"Clustering completed in {end_time - start_time:.2f} seconds.")
    return labels