"""
Simple tests for the transport system
"""

import time
from main import create_kampala_graph
from shortest_path import ShortestPath
from parallel import ParallelProcessor

def test_performance():
    """Test the performance of different algorithms"""
    graph, _ = create_kampala_graph()
    
    # Test Dijkstra vs A*
    sp = ShortestPath(graph)
    
    start_time = time.time()
    for _ in range(100):
        sp.dijkstra(0, 6)
    dijkstra_time = time.time() - start_time
    
    start_time = time.time()
    for _ in range(100):
        sp.a_star(0, 6)
    astar_time = time.time() - start_time
    
    print(f"Dijkstra 100 runs: {dijkstra_time:.3f}s")
    print(f"A* 100 runs: {astar_time:.3f}s")
    print(f"A* is {dijkstra_time/astar_time:.1f}x faster")
    
    # Test parallel speedup
    print("\nTesting parallel speedup:")
    pp = ParallelProcessor(num_workers=4)
    
    # Create many requests
    requests = [(i % 8, (i + 3) % 8) for i in range(20)]
    
    start_time = time.time()
    results = pp.simple_parallel(graph, requests)
    parallel_time = time.time() - start_time
    
    print(f"Parallel processing: {parallel_time:.3f}s for 20 requests")
    print(f"Average: {parallel_time/20:.3f}s per request")

def test_correctness():
    """Test that algorithms return correct results"""
    graph, _ = create_kampala_graph()
    sp = ShortestPath(graph)
    
    # Test 1: Route to itself should be 0
    path, dist = sp.dijkstra(0, 0)
    assert dist == 0, f"Self-route failed: {dist}"
    
    # Test 2: Route should exist between connected nodes
    path, dist = sp.dijkstra(0, 1)
    assert path, "No path found between connected nodes"
    assert dist > 0, "Distance should be positive"
    
    # Test 3: Path should start and end correctly
    assert path[0] == 0, "Path should start at source"
    assert path[-1] == 1, "Path should end at destination"
    
    print("All correctness tests passed!")

if __name__ == "__main__":
    print("Running tests...")
    test_correctness()
    test_performance()