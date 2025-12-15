class SimpleGraph:
    def __init__(self):
        self.adjacency = {}
        self.positions = {}
        self.grid = [[[] for _ in range(10)] for _ in range(10)]
    
    def add_node(self, node_id, lat, lon):
        self.adjacency[node_id] = []
        self.positions[node_id] = (lat, lon)
        grid_x = int((lat - 0.3) * 20)
        grid_y = int((lon - 32.5) * 20)
        if 0 <= grid_x < 10 and 0 <= grid_y < 10:
            self.grid[grid_x][grid_y].append(node_id)
    
    def add_edge(self, from_node, to_node, travel_time):
        if from_node not in self.adjacency:
            self.adjacency[from_node] = []
        if to_node not in self.adjacency:
            self.adjacency[to_node] = []
        
        self.adjacency[from_node].append((to_node, travel_time))
        self.adjacency[to_node].append((from_node, travel_time))
    
    def get_neighbors(self, node_id):
        return self.adjacency.get(node_id, [])