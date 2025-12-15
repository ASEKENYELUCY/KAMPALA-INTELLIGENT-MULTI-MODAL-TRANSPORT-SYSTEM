import heapq

class ShortestPath:
    def __init__(self, graph):
        self.graph = graph
    
    def dijkstra(self, start, end):
        pq = [(0, start)]
        distances = {start: 0}
        previous = {}
        
        while pq:
            current_dist, current = heapq.heappop(pq)
            
            if current == end:
                break
            
            if current_dist > distances.get(current, float('inf')):
                continue
            
            for neighbor, travel_time in self.graph.get_neighbors(current):
                new_dist = current_dist + travel_time
                
                if new_dist < distances.get(neighbor, float('inf')):
                    distances[neighbor] = new_dist
                    previous[neighbor] = current
                    heapq.heappush(pq, (new_dist, neighbor))
        
        path = []
        current = end
        while current in previous:
            path.append(current)
            current = previous[current]
        path.append(start)
        
        return list(reversed(path)), distances.get(end, float('inf'))
    
    def a_star(self, start, end):
        g_score = {start: 0}
        f_score = {start: 0}
        
        pq = [(f_score[start], 0, start)]
        previous = {}
        
        while pq:
            current_f, current_g, current = heapq.heappop(pq)
            
            if current == end:
                break
            
            if current_g > g_score.get(current, float('inf')):
                continue
            
            for neighbor, travel_time in self.graph.get_neighbors(current):
                tentative_g = current_g + travel_time
                
                if tentative_g < g_score.get(neighbor, float('inf')):
                    previous[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g
                    heapq.heappush(pq, (f_score[neighbor], tentative_g, neighbor))
        
        path = []
        current = end
        while current in previous:
            path.append(current)
            current = previous[current]
        path.append(start)
        
        return list(reversed(path)), g_score.get(end, float('inf'))