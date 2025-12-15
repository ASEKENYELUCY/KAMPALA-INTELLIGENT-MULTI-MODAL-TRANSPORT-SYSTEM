class CongestionHandler:
    def __init__(self, graph):
        self.graph = graph
        
    def find_alternative_routes(self, congested_edge, vehicles_to_redirect):
        start, end = congested_edge
        alternatives = []
        
        # Simple alternative: any path that doesn't use the congested edge
        from shortest_path import ShortestPath
        sp = ShortestPath(self.graph)
        
        # Try to find 2-3 alternatives
        import random
        for i in range(3):
            # Simulate finding alternative path
            # In real system, this would use actual graph search
            path = [start, random.choice([n for n in range(15) if n != end]), end]
            time = len(path) * 2 + random.uniform(1, 5)
            alternatives.append({
                'path': path,
                'time': time,
                'capacity': vehicles_to_redirect // (i + 2)
            })
        
        return alternatives
