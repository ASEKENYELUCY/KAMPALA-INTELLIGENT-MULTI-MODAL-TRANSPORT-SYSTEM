import random

class MultiStopRouter:
    def __init__(self, graph):
        self.graph = graph
        from shortest_path import ShortestPath
        self.sp = ShortestPath(graph)
    
    def greedy_tsp(self, stops):
        if len(stops) < 2:
            return stops, 0
        
        unvisited = set(stops[1:])  # Keep first as starting point
        current = stops[0]
        route = [current]
        total_time = 0
        
        while unvisited:
            nearest = None
            min_time = float('inf')
            
            for stop in unvisited:
                _, time = self.sp.a_star(current, stop)
                if time < min_time:
                    min_time = time
                    nearest = stop
            
            if nearest:
                route.append(nearest)
                total_time += min_time
                unvisited.remove(nearest)
                current = nearest
        
        return route, total_time